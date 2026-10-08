"""Reproducible multi-point rigid-hand / lateral-tissue experiment, not a match."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'server'))
from coupled_contact import simulate_contact
from contact_v3 import score

def run(fps=960,duration=.06,attached=False,compiled_embedding=True,iterations=64,residual_tolerance=1e-6):
    scored=score({'version':3,'points':[[.19+.34*i/40,.6,800*i/40,0,-18,0] for i in range(41)]})
    return simulate_contact(scored,fps,duration,attached,compiled_embedding,iterations,residual_tolerance)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--attached',action='store_true');parser.add_argument('--reference-embedding',action='store_true')
    parser.add_argument('--iterations',type=int,default=64);parser.add_argument('--duration',type=float,default=.06)
    args=parser.parse_args();result=run(attached=args.attached,compiled_embedding=not args.reference_embedding,iterations=args.iterations,duration=args.duration)
    name='attached-side-contact' if args.attached else 'side-contact-lab'
    (ROOT/'logs'/f'{name}.json').write_text(json.dumps(result))
    summary={k:v for k,v in result.items() if k not in ['frames','side_cage','hand_local']}
    (ROOT/'docs/validation'/f'{name}.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
