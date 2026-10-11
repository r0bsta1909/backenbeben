"""Five received production strikes, including injury geometry and both recoveries."""
import sys,json,copy
from pathlib import Path
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'server'))
from host import score_contact
from coupled_contact import simulate_contact
from contact_outcome import resolve
from rules import DEFAULTS,apply_hit
samples=[]
for name in ('default-balance-grid.json','default-balance-fine.json'):
 samples.extend(json.loads((root/'logs'/name).read_text())['grid'])
best=max(samples,key=lambda row:row['quality'])
data={'version':3,'points':[[.19+.34*i/40,best['height'],best['duration_ms']*i/40,0,best['tilt'],0] for i in range(41)]}
adaptive='--adapt' in sys.argv
series=[]
for base in ((25,) if adaptive else (25,35,40)):
 for braced in (False,True):
  chosen=copy.deepcopy(data)
  player={'damage':0.,'stun':0.,'zones':{'L':0.,'R':0.}};settings=dict(DEFAULTS,base_damage=base);rows=[];fouls=0
  for strike in range(1,int(settings['max_pairs'])+1):
   before=copy.deepcopy(player);scored=score_contact(chosen,player)
   if adaptive:
    def rank(result):return (2 if result['contact_class']=='flat' else 1 if result['hit'] else 0,result['coverage'])
    for _ in range(2):
     candidates=[(rank(scored),chosen,scored)]
     for delta in (-3,3):
      alternative=copy.deepcopy(chosen)
      for point in alternative['points']:point[4]=max(-45,min(45,point[4]+delta))
      preview=score_contact(alternative,player);candidates.append((rank(preview),alternative,preview))
     _,chosen,scored=max(candidates,key=lambda item:item[0])
   contact=simulate_contact(scored,attached=True,moving_head=True,translate_head=True,spatial_head=True,friction_coefficient=.2,braced=braced)
   outcome=resolve(scored,contact);scored.update(outcome['score_update'])
   damage,ko=apply_hit(player,scored,settings,braced);fouls+=bool(scored.get('foul'))
   rows.append({'strike':strike,'tilt':chosen['points'][0][4],'before':before,'after':copy.deepcopy(player),'damage':damage,'quality':scored['quality'],'class':scored['contact_class'],'normal_impulse_ns':outcome['normal_impulse_ns'],'ko':ko})
   if ko or fouls>=2:break
   # Host reduces stun after each fighter's turn, twice before next received hit.
   for _ in range(2):player['stun']=max(0,player['stun']-settings['recovery'])
  item={'base_damage':base,'braced_every_strike':braced,'ko':ko,'fouls':fouls,'strikes':rows};series.append(item)
  print(json.dumps({'base':base,'braced':braced,'ko':ko,'strikes':len(rows),'damage':player['damage'],'last_quality':rows[-1]['quality']}),flush=True)
(root/('logs/ko-series-adaptive.json' if adaptive else 'logs/ko-series.json')).write_text(json.dumps({'selected_input':best,'series':series,'adaptive_geometric_comparison':adaptive,'limits':'Received-strike series, not a complete network duel. Opponent turns modeled only for defender recovery. Adaptive option simulates up to two explicit three-degree wheel comparisons using geometric coverage, not future solved damage. No automatic aiming correction added to the game.'},indent=2))
