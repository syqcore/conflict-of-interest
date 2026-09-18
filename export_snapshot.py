"""Export a clearly labelled snapshot of actual simulation output for sharing."""
import json
from pathlib import Path
import urllib.request
import zipfile

root = Path(__file__).resolve().parent
with urllib.request.urlopen('http://127.0.0.1:8767/api/state', timeout=10) as response:
    state = json.load(response)
assert state['status'] == 'ready' and state['step'] > 0
state['running'] = False
html = (root / 'dashboard.html').read_text()
needle = 'refresh();setInterval(refresh,1000);'
assert needle in html
replacement = 'render(' + json.dumps(state).replace('<', '\\u003c') + ');' + """
$('notice').textContent='RECORDED SNAPSHOT of an actual full-brain run. This file is not a live simulation.';
$('toggle').hidden=true;$('reset').hidden=true;$('speed').hidden=true;
$('brainstate').textContent='RECORDED';
"""
out = root / 'artifacts'
out.mkdir(exist_ok=True)
(out / 'snapshot.html').write_text(html.replace(needle, replacement))
(out / 'snapshot.json').write_text(json.dumps(state, indent=2))
with zipfile.ZipFile(out / 'conflict-of-interest.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for name in ('exterminator.py','fetch_rol.py','verify_runtime.py','export_snapshot.py','dashboard.html','PROTOTYPE.md','LICENSE','THIRD_PARTY.md','AGENTS.md','pyproject.toml','README.md','requirements-paper.txt'):
        z.write(root / name, name)
    for folder in ('stonkfly','tests','docs','assets'):
        for path in (root / folder).rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts:
                z.write(path,path.relative_to(root))
    z.write(root / 'data/rol.json','data/rol.json')
    z.write(out / 'snapshot.html', 'snapshot.html')
print(json.dumps({'snapshot':str(out/'snapshot.html'),'zip':str(out/'conflict-of-interest.zip'),
                  'step':state['step'],'trades':state['trade_count'],'food':state['food'],
                  'equity':state['equity'],'baseline':state['baseline']}))
