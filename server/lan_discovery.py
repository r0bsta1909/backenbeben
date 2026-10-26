"""Small, versioned LAN request/reply protocol; no third-party dependencies."""
import asyncio
import ipaddress
import json
import secrets
import socket
import time

PORT = 8766
PROTOCOL = 'backenbeben-lan-v1'


def local_address(address):
    try:
        ip = ipaddress.IPv4Address(address)
        return ip.is_loopback or any(ip in net for net in (
            ipaddress.IPv4Network('10.0.0.0/8'), ipaddress.IPv4Network('172.16.0.0/12'),
            ipaddress.IPv4Network('192.168.0.0/16'), ipaddress.IPv4Network('169.254.0.0/16')))
    except ipaddress.AddressValueError:
        return False


class DiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, http_port, summary):
        self.http_port, self.summary = http_port, summary
        self.recent = {}
        self.host_id = secrets.token_hex(16)

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if len(data) > 256 or not local_address(addr[0]):
            return
        try:
            request = json.loads(data)
            nonce = request.get('nonce', '')
            if request.get('protocol') != PROTOCOL or request.get('type') != 'discover':
                return
            if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
                return
        except (ValueError, AttributeError, UnicodeError):
            return
        now = time.monotonic()
        if now - self.recent.get(addr[0], -10) < .2:
            return
        self.recent = {ip: at for ip, at in self.recent.items() if now - at < 2}
        self.recent[addr[0]] = now
        response = dict(protocol=PROTOCOL, type='host', nonce=nonce, port=self.http_port,
                        name=socket.gethostname()[:60], host_id=self.host_id, **self.summary())
        self.transport.sendto(json.dumps(response).encode(), addr)


async def serve(http_port, summary, port=PORT):
    transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
        lambda: DiscoveryProtocol(http_port, summary), local_addr=('0.0.0.0', port))
    return transport


def discover(timeout=2.5, port=PORT, targets=None):
    """Reply source is authoritative: never navigate to a packet-provided URL."""
    nonce = secrets.token_hex(16)
    packet = json.dumps(dict(protocol=PROTOCOL, type='discover', nonce=nonce)).encode()
    hosts = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('0.0.0.0', 0))
        deadline = time.monotonic() + timeout
        next_send = 0
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_send:
                for target in targets or ['255.255.255.255', '127.0.0.1']:
                    try: sock.sendto(packet, (target, port))
                    except OSError: pass
                next_send = now + .7
            sock.settimeout(min(.2, max(.001, deadline - now)))
            try: data, addr = sock.recvfrom(2048)
            except (socket.timeout, ConnectionResetError): continue
            if not local_address(addr[0]) or addr[1]!=port: continue
            try:
                reply = json.loads(data)
                if reply.get('protocol') != PROTOCOL or reply.get('type') != 'host' or reply.get('nonce') != nonce: continue
                http_port = reply.get('port')
                if type(http_port) is not int or not 1 <= http_port <= 65535: continue
                name = ''.join(c for c in str(reply.get('name', 'HOST')) if c.isprintable())[:60]
                identity=reply.get('host_id','')
                if not isinstance(identity,str) or len(identity)!=32 or any(c not in '0123456789abcdef' for c in identity):identity=''
                if len(hosts)>=64 and (addr[0],http_port) not in hosts:continue
                hosts[(addr[0], http_port)] = dict(address=addr[0], port=http_port, name=name, host_id=identity,
                    url=f'http://{addr[0]}:{http_port}')
            except (ValueError, AttributeError, UnicodeError): pass
    return sorted(hosts.values(), key=lambda h: (h['name'], h['address'], h['port']))
