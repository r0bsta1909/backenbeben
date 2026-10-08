"""Compare identical full strikes at increasing iteration caps; does not change defaults."""
import sys,json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'server'))
from contact_v3 import score
from coupled_contact import simulate_contact
from contact_outcome import resolve
scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
rows=[]
for coefficient in [0.,.2]:
 for iterations in [64,128,256]:
  c=simulate_contact(scored,attached=True,moving_head=True,translate_head=True,spatial_head=True,iterations=iterations,friction_coefficient=coefficient)
  outcome=resolve(scored,c)
  row={'coefficient':coefficient,'iterations':iterations,'normal_impulse_ns':outcome['normal_impulse_ns'],'quality':outcome['score_update']['quality'],'final_energy_j':c['final_energy_j']['total'],'material_residual_m':c['maximum_material_residual_m'],'friction_residual_m':max(f['friction_residual_m'] for f in c['frames']),'penetration_m':c['maximum_penetration_m'],'wrist_error_m':c['maximum_wrist_separation_m'],'unconverged_steps':c['unconverged_steps'],'solve_ms':c['solve_ms'],'maximum_used_iterations':max(c['iteration_counts'])}
  assert all(np.isfinite(f['offsets']).all() for f in c['frames'])
  assert max(f['friction_cone_error'] for f in c['frames'])<=1e-12
  rows.append(row);print(json.dumps(row),flush=True)
for row in rows:
 reference=next(r for r in rows if r['coefficient']==row['coefficient'] and r['iterations']==256)
 row['impulse_relative_to_256_percent']=100*(row['normal_impulse_ns']/reference['normal_impulse_ns']-1)
(root/'logs/friction-convergence.json').write_text(json.dumps(rows,indent=2))
