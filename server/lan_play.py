"""Find a LAN host and open its game; create a host only when requested."""
import ipaddress
from http.client import HTTPConnection, HTTPException
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
import webbrowser
from lan_discovery import discover


def broadcast_targets():
    targets = {'255.255.255.255', '127.0.0.1'}
    if os.name == 'nt':
        try:
            output = subprocess.check_output(['powershell', '-NoProfile', '-Command',
                'Get-NetIPAddress -AddressFamily IPv4 | Select-Object IPAddress,PrefixLength | ConvertTo-Json -Compress'],
                timeout=8, creationflags=subprocess.CREATE_NO_WINDOW)
            entries = json.loads(output)
            for entry in entries if isinstance(entries, list) else [entries]:
                network = ipaddress.IPv4Network(f"{entry['IPAddress']}/{entry['PrefixLength']}", strict=False)
                if not network.is_loopback and network.prefixlen < 31:
                    targets.add(str(network.broadcast_address))
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError): pass
    return sorted(targets)


def reachable_hosts(hosts):
    def reachable(host):
        connection=HTTPConnection(host['address'],host['port'],timeout=1.2)
        try:
            connection.request('GET','/health')
            response=connection.getresponse()
            data=json.loads(response.read(512))
            return response.status==200 and isinstance(data,dict) and data.get('ok') is True and data.get('game')=='backenbeben'
        except (OSError,ValueError,HTTPException):
            # HTTP protocol errors and sockets failing between UDP and TCP are ordinary misses.
            return False
        finally:connection.close()
    with ThreadPoolExecutor(max_workers=4) as pool:
        verified=[h for h,ok in zip(hosts,pool.map(reachable,hosts)) if ok]
    result={}
    # For a local server use loopback, retaining local admin access. Public instance
    # IDs merge a server's adapters without merging different PCs with equal names.
    for host in sorted(verified,key=lambda h:h['address']!='127.0.0.1'):
        identity=host.get('host_id') or (host['address'],host['port'])
        result.setdefault(identity,host)
    return list(result.values())


def main():
    print('BACKENBEBEN / LAN SPIELEN\nBeide PCs: LAN_SPIELEN.bat starten. Ein PC stellt den Host.')
    targets = broadcast_targets()
    while True:
        print('\nSuche Spiele im lokalen Netzwerk ...', flush=True)
        try:hosts = reachable_hosts(discover(targets=targets))
        except OSError as exc:
            print('Netzwerksuche voruebergehend nicht moeglich: '+str(exc));hosts=[]
        if len(hosts) == 1:
            print('Verbinde mit '+hosts[0]['name']+' / '+hosts[0]['url'])
            webbrowser.open(hosts[0]['url']); return
        for index, host in enumerate(hosts, 1):
            print(f"{index}: {host['name']} / {host['url']}")
        if not hosts: print('Kein Host gefunden. Auf dem ersten PC H waehlen. Firewall: ALLOW_LAN.bat (privates Netz).')
        choice = input('Nummer zum Beitreten, H = Host starten, R = erneut suchen, Q = Ende: ').strip().lower()
        if choice == 'q': return
        if choice == 'h':
            from host import main as start_host
            sys.argv = [sys.argv[0]]
            start_host(); return
        if choice.isdigit() and 1 <= int(choice) <= len(hosts):
            webbrowser.open(hosts[int(choice)-1]['url']); return


if __name__ == '__main__': main()
