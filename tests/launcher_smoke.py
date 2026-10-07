import subprocess,time,urllib.request,json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
log=(root/'logs/launcher.log').open('w')
p=subprocess.Popen(['cmd','/c',str(root/'START_HOST.bat'),'--no-browser','--no-console','--port','8766'],cwd=root,stdout=log,stderr=log)
try:
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://localhost:8766/health',timeout=1) as r:
                assert json.load(r)['ok'];break
        except OSError:time.sleep(.2)
    else:raise RuntimeError('BAT did not start the host')
    for file in ['index.html','index.js','index.pck','index.wasm']:
        with urllib.request.urlopen('http://localhost:8766/'+file,timeout=4) as r:assert r.status==200
    try:urllib.request.urlopen('http://localhost:8766/server/host.py',timeout=2)
    except urllib.error.HTTPError as e:assert e.code==404
    else:raise AssertionError('Source files exposed')
    output=(root/'logs/launcher.log').read_text(errors='replace')
    assert 'LAN: http://' in output and '<IP dieses PCs>' not in output,output
    print('BAT cold start, real LAN address, HTTP, build files, restricted static root: PASS')
finally:
    subprocess.run(['taskkill','/PID',str(p.pid),'/T','/F'],capture_output=True)
    log.close()
