"""Summarize recorded lab energy at shared physical times without re-simulating."""
import argparse,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--study-label',default='contact-energy-study')
parser.add_argument('--baseline-label',default=None)
args=parser.parse_args()
for label in [args.study_label,args.baseline_label]:
 if label is not None and not label.replace('-','').isalnum():parser.error('Use alphanumeric labels with hyphens')
summary=[]
for rate in [960,1920,3840]:
 r=json.loads((ROOT/'logs'/f'{args.study_label}-{rate}.json').read_text())
 unchanged=None
 if args.baseline_label:
  old=json.loads((ROOT/'logs'/f'{args.baseline_label}-{rate}.json').read_text())
  assert len(r['frames'])==len(old['frames'])
  for a,b in zip(r['frames'],old['frames']):
   for key in ['time','offsets','center','rotation','arm']:assert a[key]==b[key],key
  unchanged=True
 energies=np.array([r['initial_energy_j']['total']]+[f['energy_j']['total'] for f in r['frames']])
 loss=float(energies[0]-energies[-1]);factor=rate//960
 summary.append({'fps':rate,'state_matches_before_instrumentation':unchanged,
  'initial_total_j':float(energies[0]),'final_total_j':float(energies[-1]),'total_loss_j':loss,
  'explicit_damping_loss_j':r['explicit_damping_loss_j'],
  'loss_outside_explicit_damping_j':loss-r['explicit_damping_loss_j'],
  'largest_step_energy_increase_j':float(max(0,np.diff(energies).max())),
  'cumulative_contact_impulse_ns':r['frames'][-1]['cumulative_contact_impulse_ns'],
  'all_embedding_triangle_switches':sum(f['contact_switches'] for f in r['frames']),
  'common_time_samples':[{k:f[k] for k in ['time','energy_j','cumulative_contact_impulse_ns','active_contact_samples']} for f in r['frames'][factor-1::factor]]})
report={'runs':summary,'limits':['Energy of diagonal joint/box hand/edge-volume spring model only','Triangle switch count includes unloaded projected samples','Loss outside explicit damping may include integration and inelastic contact effects']}
(ROOT/'docs/validation/contact-energy-balance.json').write_text(json.dumps(report,indent=2)+'\n')
print('CONTACT_ENERGY_SUMMARY_WRITTEN')
