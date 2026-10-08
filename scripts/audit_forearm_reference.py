"""Compare visible forearm roll with the solver arm-plane reference.
Input: actual browser audit; this diagnoses reference drift, not anatomical ROM.
"""
import argparse,json,math
from pathlib import Path
import numpy as np

def frame(pose):
    a=np.asarray(pose['wrist'])-pose['elbow'];a/=np.linalg.norm(a)
    n=np.cross(a,np.asarray(pose['elbow'])-pose['shoulder']);n/=np.linalg.norm(n)
    return np.column_stack((np.cross(a,n),a,n))

def rendered_normal(pose):
    a=frame(pose)[:,1];n=np.asarray(pose['palm_normal']);n=n-a*(n@a)
    return n/np.linalg.norm(n)

def audit(records):
    records=[r for r in records if r['camera']=='front']
    contact=next(r for r in records if r['moment']=='contact')['frame']['arm']['pose']
    local=frame(contact).T@rendered_normal(contact)
    result=[]
    for row in records:
        pose=row['frame']['arm']['pose'];basis=frame(pose)
        carried=basis@local;actual=rendered_normal(pose)
        angle=math.degrees(math.atan2(basis[:,1]@np.cross(carried,actual),carried@actual))
        result.append({'moment':row['moment'],'time':row['frame']['time'],'roll_difference_deg':angle})
    return {'samples':result,'reference':'Arm-plane frame, calibrated to rendered forearm at sampled contact','limits':['Sparse replay samples, not a full time-series bound','Reference difference is not an anatomical joint angle','Carried reference assumes no independent pronation motor; recovery may intentionally change orientation']}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('input');parser.add_argument('--output',required=True);args=parser.parse_args()
    result=audit(json.loads(Path(args.input).read_text(encoding='utf-8')))
    Path(args.output).write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
