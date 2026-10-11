"""Measure real production contact outcomes across a declared input grid."""
import sys,json,itertools
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'server'))
from contact_v3 import score
from coupled_contact import simulate_contact
from contact_outcome import resolve
from rules import DEFAULTS
fine='--fine' in sys.argv
rows=[]
grid=((.62,.64,.66),(-15,-12,-9),(350,450,600)) if fine else ((.56,.60,.64),(-24,-18,-12),(250,500,800))
for height,tilt,duration in itertools.product(*grid):
 data={'version':3,'points':[[.19+.34*i/40,height,duration*i/40,0,tilt,0] for i in range(41)]}
 scored=score(data);row={'height':height,'tilt':tilt,'duration_ms':duration,'class':scored['contact_class'],'geometric_quality':scored['quality']}
 if scored['hit']:
  contact=simulate_contact(scored,attached=True,moving_head=True,translate_head=True,spatial_head=True,friction_coefficient=.2)
  result=resolve(scored,contact);row.update(normal_impulse_ns=result['normal_impulse_ns'],quality=result['score_update']['quality'])
 else:row.update(normal_impulse_ns=0.,quality=0.)
 rows.append(row);print(json.dumps(row),flush=True)
result={'settings':DEFAULTS,'grid':rows,'limits':'Healthy geometry input grid; repeated real strikes must recompute injury geometry. Not a proof of a global maximum.'}
(root/('logs/default-balance-fine.json' if fine else 'logs/default-balance-grid.json')).write_text(json.dumps(result,indent=2))
