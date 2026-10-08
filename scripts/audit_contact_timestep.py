"""Refine timestep with fixed initial state; reports evidence, not a physics certificate."""
import json
from pathlib import Path
import numpy as np
from run_side_contact_lab import run,rotation_vector
ROOT=Path(__file__).resolve().parents[1]
results=[]
for fps in [960,1920,3840]:
 result=run(fps=fps,duration=.0125,attached=True,iterations=384)
 results.append(result)
 (ROOT/'logs'/f'timestep-{fps}.json').write_text(json.dumps(result))
 print(json.dumps({k:result[k] for k in ['fps','unconverged_steps','peak_deformation_m','maximum_penetration_m','solve_ms']}),flush=True)
comparisons=[]
for coarse,fine in zip(results,results[1:]):
 for key in ['initial_velocity','initial_angular_velocity','initial_joint_velocity']:
  np.testing.assert_array_equal(coarse[key],fine[key])
 a,b=coarse['frames'][-1],fine['frames'][-1]
 assert abs(a['time']-b['time'])<1e-12
 delta=(np.asarray(a['offsets'])-b['offsets']).reshape(-1,3)/4
 comparisons.append({'rates':[coarse['fps'],fine['fps']],
  'end_tissue_max_difference_m':float(np.max(np.linalg.norm(delta,axis=1))),
  'end_tissue_rms_difference_m':float(np.sqrt(np.mean(np.sum(delta*delta,axis=1)))),
  'end_hand_center_difference_m':float(np.linalg.norm(np.asarray(a['center'])-b['center'])),
  'end_hand_rotation_difference_rad':float(np.linalg.norm(rotation_vector(np.asarray(a['rotation'])@np.asarray(b['rotation']).T))),
  'end_hand_velocity_difference_m_s':float(np.linalg.norm(np.asarray(coarse['final_velocity'])-fine['final_velocity']))})
report={'duration_s':.0125,'initial_state_identical':True,'samples':results[0]['hand_samples'],
 'runs':[{k:r[k] for k in r if k not in ['frames','side_cage','hand_local']} for r in results],
 'comparisons':comparisons,'limits':['Short single impact, not full clip convergence','No muscle drive, diagonal joint inertia, no friction','Laboratory only, not active in matches']}
(ROOT/'docs/validation/contact-timestep.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(comparisons,indent=2))
