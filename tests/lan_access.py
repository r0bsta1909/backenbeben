import json,socket,urllib.request,urllib.error
from pathlib import Path
ips=sorted(set(i[4][0] for i in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET)))
ip=next(x for x in ips if not x.startswith(('127.','169.254.')))
base='http://'+ip+':8765'
info=json.load(urllib.request.urlopen(base+'/api/info'))
assert info['admin'] is False
request=urllib.request.Request(base+'/api/admin',data=json.dumps({'command':'get'}).encode(),headers={'Content-Type':'application/json','Origin':base})
try:
    urllib.request.urlopen(request)
    raise AssertionError('Guest received admin access')
except urllib.error.HTTPError as e:
    assert e.code==403
result={'lan_url':base,'same_host_lan_interface':True,'guest_admin':False,'guest_admin_post_status':403,'physical_second_pc_tested':False}
Path('logs/lan-access.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
