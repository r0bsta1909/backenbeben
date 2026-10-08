"""Compare full warmed replay recordings and timing before/after inverse compilation."""
import sys,json,statistics
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'server'))
import moving_head_replay as replay
from contact_v3 import score
s=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-15,0] for i in range(41)]})
optimized=replay.local_offsets_spatial;reference=replay.local_offsets_spatial_reference
replay.simulate(s,spatial=True,friction_coefficient=.2)
rows=[]
try:
 for _ in range(3):
  replay.local_offsets_spatial=reference;a=replay.simulate(s,spatial=True,friction_coefficient=.2)
  replay.local_offsets_spatial=optimized;b=replay.simulate(s,spatial=True,friction_coefficient=.2)
  for key in ['frames','head_positions','head_rotations','arm_path','score_update','friction']:assert a[key]==b[key],key
  rows.append({'reference_ms':a['solve_ms'],'optimized_ms':b['solve_ms'],'recordings_identical':True});print(rows[-1],flush=True)
finally:replay.local_offsets_spatial=optimized
result={'runs':rows,'reference_median_ms':statistics.median(r['reference_ms'] for r in rows),'optimized_median_ms':statistics.median(r['optimized_ms'] for r in rows)}
(root/'logs/spatial-inverse-performance.json').write_text(json.dumps(result,indent=2))
