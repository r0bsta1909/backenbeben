"""Reproduce coupled contact friction candidate; does not enable match friction."""
import sys,json,argparse
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'server'))
from contact_v3 import score
from coupled_contact import simulate_contact
parser=argparse.ArgumentParser();parser.add_argument('--duration',type=float,default=.0125);parser.add_argument('--iterations',type=int,default=32);parser.add_argument('--compare-reference',action='store_true');args=parser.parse_args()
scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
kwargs=dict(attached=True,moving_head=True,translate_head=True,spatial_head=True,duration=args.duration,iterations=args.iterations)
base=simulate_contact(scored,**kwargs);zero=simulate_contact(scored,friction_coefficient=0,**kwargs)
assert base['frames']==zero['frames']
r=simulate_contact(scored,friction_coefficient=.2,**kwargs)
assert all(np.isfinite(f['offsets']).all() for f in r['frames'])
assert max(f['friction_cone_error'] for f in r['frames'])<1e-12
out={'zero_identical':True,'duration':r['duration'],'steps':len(r['frames']),'coefficient':.2,'friction_impulse_sum_ns':np.sum([f['friction_impulse_ns'] for f in r['frames']],axis=0).tolist(),'maximum_friction_residual_m':max(f['friction_residual_m'] for f in r['frames']),'maximum_penetration_m':r['maximum_penetration_m'],'wrist_error_m':r['maximum_wrist_separation_m'],'unconverged_steps':r['unconverged_steps'],'solve_ms':r['solve_ms'],'final_energy_without_friction_j':base['final_energy_j']['total'],'final_energy_with_friction_j':r['final_energy_j']['total']}
if args.compare_reference:
 reference=simulate_contact(scored,friction_coefficient=.2,friction_compiled=False,**kwargs)
 errors={}
 for key in ['offsets','center','rotation','friction_impulse_ns']:
  errors[key]=max(float(np.max(np.abs(np.asarray(a[key])-np.asarray(b[key])))) for a,b in zip(reference['frames'],r['frames']))
  assert errors[key]<1e-8,(key,errors[key])
 out['reference_errors']=errors;out['reference_ms']=reference['solve_ms']
(root/'logs/friction-coupling.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
