"""Refine timestep with fixed initial state; reports evidence, not a physics certificate."""
import json,argparse,math
from pathlib import Path
import numpy as np
from run_side_contact_lab import run,rotation_vector
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--tolerance',type=float,default=1e-6)
parser.add_argument('--iterations',type=int,default=384)
parser.add_argument('--rates',type=int,nargs='+',default=[960,1920,3840])
parser.add_argument('--label',default='contact-timestep')
args=parser.parse_args()
if not math.isfinite(args.tolerance) or args.tolerance<=0 or args.iterations<1:parser.error('Positive tolerance and iteration limit required')
if not args.label.replace('-','').isalnum():parser.error('Use an alphanumeric label with hyphens')
if len(args.rates)<2 or any(r<=0 for r in args.rates) or args.rates!=sorted(set(args.rates)):parser.error("Provide at least two increasing positive rates")
results=[]
for fps in args.rates:
 result=run(fps=fps,duration=.0125,attached=True,iterations=args.iterations,residual_tolerance=args.tolerance)
 results.append(result)
 (ROOT/'logs'/f'{args.label}-{fps}.json').write_text(json.dumps(result))
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
(ROOT/'docs/validation'/f'{args.label}.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(comparisons,indent=2))
