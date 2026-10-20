/* Bracket UI uses server snapshots; no client can assign winners or opponents. */
(() => {
 let snapshot=null,uid=null;
 const names=new Map();
 function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el}
 window.onTournament=d=>{
  snapshot=d.tournament;uid=d.you;names.clear();snapshot.entries.forEach(p=>names.set(p.id,p.name));
  if(!d.in_match){showLobby();document.body.classList.add('tournament');}
  const t=snapshot,owner=t.owner===uid,me=t.entries.find(p=>p.id===uid);
  $('tournamentCode').textContent=t.id;
  $('tournamentCount').textContent=`${t.entries.length} / ${t.capacity} SPIELER`;
  $('tournamentStart').hidden=!(owner&&t.status==='waiting');
  $('tournamentStart').disabled=t.entries.length<2;
  $('tournamentStatus').textContent=t.status==='waiting'?(owner?'Teile den Code. Starte, sobald alle dabei sind.':'Warte auf den Start durch den Veranstalter.'):
   t.status==='finished'?`TURNIERSIEGER: ${names.get(t.champion)||'–'}`:
   t.status==='cancelled'?'Turnier abgebrochen · '+(t.cancel_reason||'Keine verbleibenden Teilnehmer.'):
   !me?.active?'Du hast das Turnier verlassen.':
   t.rounds.flat().some(m=>m.status==='done'&&m.players.includes(uid)&&m.winner!==uid)?'Ausgeschieden · Verfolge den weiteren Turnierverlauf.':
   t.rounds.flat().some(m=>m.status==='done'&&m.winner===uid&&m.reason==='bye')?'Freilos / weitergekommen · Dein nächster Kampf startet automatisch.':
   'Warte auf die übrigen Kämpfe. Dein nächster Kampf startet automatisch.';
  const bracket=$('tournamentBracket');bracket.replaceChildren();
  if(t.status==='waiting'){
   const list=node('ol',undefined,'entrantList');
   t.entries.forEach(p=>list.append(node('li',p.name+(p.id===uid?' · DU':'')+(p.id===t.owner?' · VERANSTALTER':'')+(!p.connected?' · VERBINDET SICH …':''))));bracket.append(list);
  }else{
   const rounds=t.rounds.map(r=>r.map(m=>({...m})));
   while(rounds.at(-1)?.length>1){const previous=rounds.at(-1),rnd=[];
    for(let i=0;i<previous.length;i+=2)rnd.push({id:`r${rounds.length+1}m${i/2+1}`,players:[previous[i].winner,previous[i+1].winner],status:t.status==='cancelled'?'cancelled':'pending',reason:t.status==='cancelled'?'cancelled':'',winner:null});
    rounds.push(rnd);
   }
   rounds.forEach((rnd,i)=>{
    const col=node('section',undefined,'bracketRound');
    col.append(node('h3',rnd.length===1?'FINALE':rnd.length===2?'HALBFINALE':`RUNDE ${i+1}`));
    rnd.forEach(m=>{
     const card=node('article',undefined,'bracketMatch');card.dataset.match=m.id;
     m.players.forEach(p=>{const row=node('div',p?(names.get(p)+(p===uid?' · DU':'')):m.status==='pending'?'SIEGER DER VORRUNDE':m.status==='cancelled'?'NICHT BESETZT':'FREILOS');if(p&&m.winner===p)row.className='bracketWinner';card.append(row)});
     const reason={bye:'Freilos',forfeit:'Aufgabe / Verbindungsabbruch',ko:'KO',points:'Punkte',disqualification:'Disqualifikation',lot:'Los nach 3 Zusatzpaaren',cancelled:'Abgebrochen'};
     card.append(node('small',m.status==='playing'?'KAMPF LÄUFT':m.status==='ready'?'WARTET AUF KAMPFSTART':m.status==='pending'?'WARTET AUF DIE VORRUNDE':reason[m.reason]||'Beendet'));col.append(card);
    });bracket.append(col);
   });
  }
 };
 function enter(action){if(!window.gameReady)return;window.unlockGameAudio();sendAction({...characterPayload(),action,code:$('tournamentJoinCode').value});}
 $('tournamentCreate').onclick=()=>enter('tournament_create');
 $('tournamentJoin').onclick=()=>enter('tournament_join');
 $('tournamentJoinCode').addEventListener('keydown',e=>{if(e.key==='Enter')enter('tournament_join')});
 $('tournamentStart').onclick=()=>sendAction({action:'tournament_start'});
 $('tournamentLeave').onclick=()=>sendAction({action:'leave'});
 window.tournamentConnection=connected=>{
  $('tournamentCreate').disabled=!connected||!window.gameReady;
  $('tournamentJoin').disabled=!connected||!window.gameReady;
  $('tournamentStart').disabled=!connected||(snapshot?.entries.length||0)<2;
 };
 window.addEventListener('game-ready',()=>window.tournamentConnection(socket?.readyState===1));
 window.tournamentConnection(socket?.readyState===1);
})();
