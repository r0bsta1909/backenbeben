/* Explicit fictional snapshots for the design preview; never loaded by the game. */
(() => {
 let stage='waiting';
 const roster=['SVEN','ROBSTA','MIRA','KALLE','NADJA','BRUNO','TONI','KNOX','JULE','BEN','LEO','IDA','NILS','MATS','LINA','FINN','ANNA','OTTO','EMIL','THEO'];
 function draw(){
  const count=+$('previewCount').value,entries=roster.slice(0,count).map((name,i)=>({id:'p'+i,name,active:true,connected:true}));
  const size=2**Math.ceil(Math.log2(count)),byes=size-count,pairs=[];let cursor=0;
  for(let i=0;i<byes;i++)pairs.push([entries[cursor++].id,null]);
  while(cursor<count)pairs.push([entries[cursor++].id,entries[cursor++].id]);
  const first=pairs.map((players,i)=>({id:'r1m'+(i+1),players,status:players[1]===null?'done':i%3===0?'playing':i%3===1?'done':'ready',winner:players[1]===null||i%3===1?players[0]:null,reason:players[1]===null?'bye':i%3===1?'ko':'',room:null}));
  const t={id:'BB2026',owner:'p0',status:stage,entries,rounds:stage==='waiting'?[]:[first],champion:null,capacity:20,extra_pairs:3,cancel_reason:''};
  if(stage==='finished'){
   let previous=first;previous.forEach(m=>{m.status='done';m.winner=m.players[0];m.reason=m.players[1]===null?'bye':'points';});
   while(previous.length>1){const next=[];for(let i=0;i<previous.length;i+=2){const players=[previous[i].winner,previous[i+1].winner];next.push({id:`r${t.rounds.length+1}m${i/2+1}`,players,status:'done',winner:players[0],reason:i===0?'ko':'points',room:null});}t.rounds.push(next);previous=next;}
   t.champion=previous[0].winner;
  }
  if(stage==='cancelled'){t.cancel_reason='Der Veranstalter hat das Turnier beendet.';first.forEach(m=>{if(m.status!=='done'){m.status='cancelled';m.reason='cancelled';}});}
  window.onTournament({type:'tournament',you:'p0',in_match:false,tournament:t});
  document.querySelectorAll('[data-preview]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.preview===stage)));
 }
 document.querySelectorAll('[data-preview]').forEach(b=>b.onclick=()=>{stage=b.dataset.preview;draw();});$('previewCount').onchange=draw;draw();
})();
