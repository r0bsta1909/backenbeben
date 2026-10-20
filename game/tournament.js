/* Tournament broadcast UI. All pairings and outcomes come from the host. */
(() => {
 let snapshot=null,uid=null,focusTarget=null,viewingMatch=false;
 const names=new Map(),entries=new Map();
 function node(tag,text,cls){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;}
 function initials(name){return name.trim().split(/\s+/).slice(0,2).map(s=>Array.from(s)[0]||'').join('').toUpperCase();}
 window.onTournament=d=>{
  const previousCode=snapshot?.id,previousStage=snapshot?.status,enteringBracket=viewingMatch&&!d.in_match;viewingMatch=!!d.in_match;
  snapshot=d.tournament;uid=d.you;names.clear();entries.clear();snapshot.entries.forEach((p,i)=>{names.set(p.id,p.name);entries.set(p.id,{...p,number:i+1});});
  if(!d.in_match){showLobby();document.body.classList.add('tournament');}
  const t=snapshot,owner=t.owner===uid,me=entries.get(uid),waiting=t.status==='waiting',finished=t.status==='finished',cancelled=t.status==='cancelled';
  const matches=t.rounds.flat(),eliminated=matches.some(m=>m.status==='done'&&m.players.includes(uid)&&m.winner!==uid);
  $('tournamentPanel').dataset.stage=t.status;
  $('tournamentTitle').textContent=waiting?'DEINE LOBBY.':finished?'DER TITEL IST VERGEBEN.':cancelled?'RUNDE BEENDET.':'DER WEG ZUM TITEL.';
  $('tournamentSubtitle').textContent=waiting?'Bring die Runde zusammen. Den Rest regelt der Turnierbaum.':finished?'Ein letzter Treffer. Ein Name ganz oben.':cancelled?'Hier geht es heute nicht weiter. Starte bei Bedarf ein neues Turnier.':'Jede Paarung zählt. Eine Niederlage und du bist raus.';
  $('tournamentCode').textContent=t.id;
  $('tournamentInviteHint').textContent=waiting?'Gleiche LAN-Adresse öffnen & Code eingeben.':finished?'Turnier abgeschlossen · Dein Code zur Zuordnung.':cancelled?'Turnier beendet · Neues Turnier in der Lobby.':'Teilnahme geschlossen · Das Turnier läuft.';
  $('tournamentCount').textContent=`${String(t.entries.length).padStart(2,'0')} / ${t.capacity} SPIELER`;
  $('tournamentSectionLabel').textContent=waiting?'DIE RUNDE WIRD VOLL':finished?'ALLE ENTSCHEIDUNGEN AUF EINEN BLICK':'DIE PAARUNGEN';
  $('tournamentSectionTitle').textContent=waiting?'DAS AUFGEBOT.':'DER TURNIERBAUM.';
  $('tournamentStart').hidden=!(owner&&waiting);
  $('tournamentStart').disabled=t.entries.length<2||socket?.readyState!==1||t.entries.some(p=>!p.connected);
  $('tournamentStartHint').textContent=waiting?(owner?(t.entries.length<2?'Noch ein Gegner, dann kann es losgehen.':t.entries.some(p=>!p.connected)?'Warte, bis alle Spieler wieder verbunden sind.':'Alle da? Du gibst das Startsignal.'):'Der Veranstalter gibt das Startsignal.'):finished?'Zur Lobby zurückkehren und neu antreten.':cancelled?'Zur Lobby zurückkehren und neu starten.':'Dein nächster Kampf startet automatisch.';
  $('tournamentLeave').textContent=finished||cancelled?'ZUR LOBBY →':'TURNIER VERLASSEN';
  $('tournamentStatus').textContent=waiting?(owner?'Teile den Code. Starte, sobald alle dabei sind.':'Warte auf den Start durch den Veranstalter.'):
   finished?`TURNIERSIEGER: ${names.get(t.champion)||'–'}`:cancelled?'Turnier abgebrochen · '+(t.cancel_reason||'Keine verbleibenden Teilnehmer.'):
   !me?.active?'Du hast das Turnier verlassen.':eliminated?'Ausgeschieden · Verfolge den weiteren Turnierverlauf.':
   matches.some(m=>m.status==='done'&&m.winner===uid&&m.reason==='bye')?'Freilos / weitergekommen · Dein nächster Kampf startet automatisch.':'Warte auf die übrigen Kämpfe. Dein nächster Kampf startet automatisch.';
  $('tournamentFocusTitle').textContent=waiting?(owner?'DU GIBST DEN START.':'DEIN PLATZ STEHT.'):finished?(t.champion===uid?'DU BIST CHAMPION.':'DAS WAR EIN BEBEN.'):cancelled?'KEIN SIEGER.':eliminated?'DIESMAL WAR’S DAS.':'BLEIB BEREIT.';
  $('tournamentStateMarker').textContent=waiting?'LOBBY OFFEN':finished?'ABGESCHLOSSEN':cancelled?'ABGEBROCHEN':eliminated?'AUSGESCHIEDEN':'TURNIER LÄUFT';
  const defeated=new Set(matches.filter(m=>m.status==='done').flatMap(m=>m.players.filter(p=>p&&p!==m.winner)));
  $('tournamentActiveCount').textContent=String(cancelled?0:waiting?t.entries.filter(p=>p.connected).length:t.entries.filter(p=>p.active&&!defeated.has(p.id)).length).padStart(2,'0');
  $('tournamentActiveLabel').textContent=waiting?'VERBUNDEN':cancelled?'AKTIVE KÄMPFE':'NOCH IM RENNEN';
  $('tournamentRoundCount').textContent=t.entries.length<2?'–':Math.ceil(Math.log2(t.entries.length));
  $('tournamentChampion').hidden=!finished;$('tournamentChampionName').textContent=names.get(t.champion)||'';
  document.querySelectorAll('.tournamentSteps [data-step]').forEach(el=>{
   const current=el.dataset.step===t.status;el.classList.toggle('current',current);if(current)el.setAttribute('aria-current','step');else el.removeAttribute('aria-current');
   el.classList.toggle('complete',!current&&(finished||(!waiting&&el.dataset.step==='waiting')));
  });
  const bracket=$('tournamentBracket'),left=bracket.scrollLeft,top=bracket.scrollTop;bracket.replaceChildren();focusTarget=null;
  if(waiting){
   const list=node('ol',undefined,'entrantList');
   t.entries.forEach((p,i)=>{
    const item=node('li');item.dataset.own=String(p.id===uid);item.dataset.connected=String(!!p.connected);
    item.append(node('span',initials(p.name),'entrantAvatar'));
    const details=node('div',undefined,'entrantDetails');details.append(node('strong',p.name),node('span',!p.connected?'VERBINDET SICH …':p.id===t.owner?'VERANSTALTER':'VERBUNDEN'));
    item.append(details,node('span',p.id===uid?'DU':String(i+1).padStart(2,'0'),'entrantBadge'));list.append(item);
   });bracket.append(list);
  }else{
   const rounds=t.rounds.map(r=>r.map(m=>({...m})));
   while(rounds.at(-1)?.length>1){const previous=rounds.at(-1),rnd=[];
    for(let i=0;i<previous.length;i+=2)rnd.push({id:`r${rounds.length+1}m${i/2+1}`,players:[previous[i].winner,previous[i+1].winner],status:cancelled?'cancelled':'pending',reason:cancelled?'cancelled':'',winner:null});
    rounds.push(rnd);
   }
   const trackCount=rounds[0]?.length||1;
   rounds.forEach((rnd,i)=>{
    const col=node('section',undefined,'bracketRound');col.style.setProperty('--span',2**i);col.style.setProperty('--tracks',trackCount);
    const heading=node('h3');heading.append(node('span',rnd.length===1?'FINALE':rnd.length===2?'HALBFINALE':`RUNDE ${i+1}`),node('b',String(i+1).padStart(2,'0')));col.append(heading);
    const slots=node('div',undefined,'bracketMatches');
    rnd.forEach(m=>{
     const slot=node('div',undefined,'bracketSlot'),card=node('article',undefined,'bracketMatch');card.dataset.match=m.id;card.dataset.state=m.status;card.dataset.own=String(m.players.includes(uid));
     if(m.players.includes(uid))focusTarget=card;
     m.players.forEach(p=>{
      const row=node('div',undefined,'bracketPlayer');if(p&&m.winner===p)row.classList.add('bracketWinner');
      row.append(node('span',p?String(entries.get(p)?.number||0).padStart(2,'0'):'–','bracketSeed'));
      row.append(node('span',p?(names.get(p)||'SPIELER'):m.status==='pending'?'SIEGER DER VORRUNDE':m.status==='cancelled'?'NICHT BESETZT':'FREILOS','bracketName'));
      if(p===uid)row.append(node('span','DU','bracketSelf'));
      if(p&&m.winner===p)row.append(node('span','✓','bracketCheck'));card.append(row);
     });
     const reason={bye:'Freilos',forfeit:'Aufgabe / Verbindungsabbruch',ko:'KO',points:'Punkte',disqualification:'Disqualifikation',lot:'Los nach 3 Zusatzpaaren',cancelled:'Abgebrochen'};
     card.append(node('small',m.status==='playing'?'KAMPF LÄUFT':m.status==='ready'?'WARTET AUF KAMPFSTART':m.status==='pending'?'WARTET AUF DIE VORRUNDE':reason[m.reason]||'Beendet'));
     slot.append(card);slots.append(slot);
    });col.append(slots);bracket.append(col);
   });
  }
  $('tournamentFocus').hidden=waiting||!focusTarget;$('tournamentScrollHint').hidden=waiting;
  bracket.scrollLeft=previousCode===t.id?left:0;bracket.scrollTop=previousCode===t.id?top:0;
  if(!d.in_match&&(enteringBracket||previousStage!==t.status||previousCode!==t.id))$('tournamentPanel').scrollTop=0;
  if(innerWidth>750&&(previousStage!==t.status||enteringBracket)&&t.status==='running')requestAnimationFrame(()=>focusTarget?.scrollIntoView({block:'nearest',inline:'nearest'}));
 };
 $('tournamentFocus').onclick=()=>focusTarget?.scrollIntoView({block:'center',inline:'center',behavior:'smooth'});
 $('tournamentCopy').onclick=async()=>{
  if(!snapshot)return;
  try{
   if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(snapshot.id);
   else{const input=node('textarea',snapshot.id);input.style.cssText='position:fixed;left:-9999px';document.body.append(input);input.select();const copied=document.execCommand('copy');input.remove();if(!copied)throw Error('copy');}
   toast('Turniercode kopiert.');
  }catch{toast('Dein Turniercode: '+snapshot.id);}
 };
 function enter(action){if(!window.gameReady)return;window.unlockGameAudio();sendAction({...characterPayload(),action,code:$('tournamentJoinCode').value});}
 $('tournamentCreate').onclick=()=>enter('tournament_create');$('tournamentJoin').onclick=()=>enter('tournament_join');
 $('tournamentJoinCode').addEventListener('keydown',e=>{if(e.key==='Enter')enter('tournament_join')});
 $('tournamentStart').onclick=()=>sendAction({action:'tournament_start'});$('tournamentLeave').onclick=()=>sendAction({action:'leave'});
 window.tournamentConnection=connected=>{
  $('tournamentCreate').disabled=!connected||!window.gameReady;$('tournamentJoin').disabled=!connected||!window.gameReady;
  $('tournamentStart').disabled=!connected||(snapshot?.entries.length||0)<2||snapshot?.entries.some(p=>!p.connected);
 };
 window.addEventListener('game-ready',()=>window.tournamentConnection(socket?.readyState===1));window.tournamentConnection(socket?.readyState===1);
})();
