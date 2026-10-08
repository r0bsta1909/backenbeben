"""Inspect wrist edge distortion on the same posed mesh used by contact validation."""
import runpy,json,math
from pathlib import Path
ns=runpy.run_path(str(Path(__file__).with_name('validate_contact_skinning.py')))
globals().update({k:v for k,v in ns.items() if not k.startswith('__')})
w=Vector(meta['bones']['hand.R']['head']);axis=(Vector(meta['bones']['hand.R']['tail'])-w).normalized()
along=[(p-w).dot(axis) for p in rest]
edges=[tuple(e.vertices) for e in arm.data.edges if all(-.080<along[i]<.070 for i in e.vertices)]
report=[]
for case in cases:
 for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
 bpy.context.view_layer.update()
 elbow=Vector(case['pose']['elbow']);wrist=Vector(case['pose']['wrist']);normal=Vector(case['normal']);finger=Vector(case['finger'])
 place('forearm.R',elbow,elbow.lerp(wrist,.5),normal)
 place('forearm_twist.R',elbow.lerp(wrist,.5),wrist,normal)
 place('hand.R',wrist,wrist+finger*.1,normal)
 evaluated=arm.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
 ratios=[]
 for a,b in edges:
  length=(rest[a]-rest[b]).length
  if length>.0005:ratios.append((mesh.vertices[a].co-mesh.vertices[b].co).length/length)
 ratios.sort();report.append({'edges':len(ratios),'max_edge_stretch':max(ratios),'p95_edge_stretch':ratios[int(.95*len(ratios))]})
 evaluated.to_mesh_clear()
print(json.dumps(report,indent=2));(ROOT/'logs/wrist-distortion.json').write_text(json.dumps(report,indent=2))

assert max(r['max_edge_stretch'] for r in report)<3.,'Wrist skinning has a local stretch spike'
assert max(r['p95_edge_stretch'] for r in report)<1.5,'Wrist distortion regressed broadly'
print('WRIST_DISTORTION_VALIDATION_PASS')
