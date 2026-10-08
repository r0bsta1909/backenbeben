"""First integration gate: moving yaw during actual contact, not match default."""
import json,sys,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from audit_coupled_variants import CASES
from contact_v3 import score
from coupled_contact import simulate_contact
rows=[]
for name,y,tilt,skin in CASES:
 s=score({'version':3,'points':[[.19+.34*i/40,y,800*i/40,0,tilt,0] for i in range(41)],'_skin_state':skin})
 r=simulate_contact(s,attached=True,moving_head=True)
 row={'case':name,'final_angle_rad':r['frames'][-1]['head_angle'],'final_velocity_rad_s':r['frames'][-1]['head_velocity'],'maximum_pin_error_m':max(f['head_attachment_residual_m'] for f in r['frames']),'maximum_penetration_m':r['maximum_penetration_m'],'initial_energy_j':r['initial_energy_j']['total'],'final_energy_j':r['final_energy_j']['total'],'solve_ms':r['solve_ms'],'unconverged_steps':r['unconverged_steps']}
 assert all(math.isfinite(v) for k,v in row.items() if isinstance(v,(int,float)))
 assert row['maximum_pin_error_m']<1e-6,row
 assert row['maximum_penetration_m']<1e-5,row
 assert row['final_energy_j']<row['initial_energy_j'],row
 rows.append(row);print(json.dumps(row),flush=True)
(ROOT/'docs/validation/moving-head-contact.json').write_text(json.dumps({'cases':rows,'status':'Experimental contact interval only; replay tail and recovery must be integrated before default use.','limits':'Fixed translation and one yaw axis. Calibrated inertia/neck, numerical material residuals remain. No anatomical validation.'},indent=2)+'\n')
