"""Compare lateral cage embeddings with real legal hand contacts."""
import sys,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from side_cage import build_side_cage
from contact_embedding import embed_side
from contact_v3 import score
cases=[]
for y in [.4,.5,.6,.7]:
 for tilt in [-30,-15,0,15,30]:
  s=score({'version':3,'points':[[.19+.34*i/40,y,800*i/40,0,tilt,0] for i in range(41)]})
  if s['hit']:cases.append((y,tilt,s))
results={}
for nx,ny in [(9,7),(17,17),(33,25)]:
 c=build_side_cage(nx,ny);rows=[]
 for y,tilt,s in cases:
  errors=[];missing=0
  for p in s['footprint']:
   actual=np.array(p[:3])/4;e=embed_side(actual,c['nodes'],c['triangles'])
   if e is None:missing+=1
   else:errors.append(float(np.linalg.norm(e['position']-actual)))
  rows.append({'height':y,'tilt':tilt,'class':s['contact_class'],'contacts':len(s['footprint']),'missing':missing,'max_error_m':max(errors) if errors else None})
 results[f'{nx}x{ny}']={'nodes':len(c['nodes']),'tetrahedra':len(c['tetrahedra']),'y_bounds':c['y_bounds'],'z_bounds':c['z_bounds'],'cases':rows,'missing':sum(r['missing'] for r in rows),'max_error_m':max(r['max_error_m'] for r in rows if r['max_error_m'] is not None)}
(ROOT/'docs/validation/side-cage-multicase.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{a:b for a,b in v.items() if a!='cases'} for k,v in results.items()},indent=2))
