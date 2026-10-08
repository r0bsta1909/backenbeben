// Input, recorded host physics and replay transport. Never evaluates damage locally.
(() => {
const canvas=document.getElementById('canvas');
const panel=document.createElement('aside');panel.id='posePanel';panel.className='panel';
panel.innerHTML='<div id="poseSteps"><span id="practiceStep">1 · PROBE</span><span id="strikeStep">2 · SCHLAG</span></div><h3 id="poseTitle">PROBESCHWUNG</h3><p id="gestureCue"><b>LINKE MAUSTASTE HALTEN</b><br>Dann nach links ziehen und loslassen.</p><p>↑ ↓ Maus: Treffhöhe<br>↕ Mausrad: Handfläche kippen</p><div id="poseReadout"></div><p id="contactVerdict">Nach links ziehen: Die rechte Hand schwingt seitlich zur Wange.</p><button id="poseCamera" aria-pressed="false">HAND VON DER SEITE ANSEHEN</button><p id="poseCameraHint" hidden>Auch hier: nach links ziehen. Die Ansicht ändert nur die Kamera.</p><button id="repeatPractice" hidden>NOCH EINMAL OHNE SCHADEN ÜBEN</button><button id="resetPose">HALTUNG ZURÜCKSETZEN</button>';
document.body.append(panel);
const replayPanel=document.createElement('aside');replayPanel.id='replayPanel';replayPanel.className='panel';
replayPanel.innerHTML='<div class="row"><strong>REPLAY · KONTAKTLABOR</strong><span id="replayTime"></span></div><input id="replaySeek" aria-label="Replay-Zeit" type="range" min="0" max="2.8" step="0.008333" value="0"><div class="row"><button id="replayPlay">PAUSE</button><button id="replayStep">+ EIN BILD</button><select id="replaySpeed" aria-label="Replay-Geschwindigkeit"><option value="0.1">0,1×</option><option value="0.25" selected>0,25×</option><option value="1">1×</option></select><select id="replayCamera" aria-label="Replay-Kamera"><option value="front">FRONT</option><option value="side">DREIVIERTEL</option><option value="wide">TV · TOTALE</option></select><button id="replayImpact">ZUM TREFFER</button><button id="replayContact">PUNKTE AN</button><button id="replaySkip">WEITER</button></div><p id="replayVerdict"></p><div id="contactLegend" hidden><span style="color:#59dfbe">● Handfläche</span> · <span style="color:#ffd078">● Finger</span> · <span style="color:#ee93b3">● Handballen</span></div>';
document.body.append(replayPanel);
const style=document.createElement('style');style.textContent=`#posePanel{position:fixed;left:25px;top:25%;width:220px;padding:18px;z-index:4;border-left:3px solid #e8c167}#posePanel small{color:#e8c167;font-size:10px;letter-spacing:1px}#posePanel h3{margin:10px 0}#poseSteps{display:flex;gap:6px;font-size:11px;font-weight:bold}#poseSteps span{padding:7px;border:1px solid #626872;color:#949ba6}#poseSteps [aria-current="step"]{background:#e8c167;color:#151920;border-color:#e8c167}#posePanel[data-mode="strike"] #poseSteps [aria-current="step"]{background:#f29a83;border-color:#f29a83}#posePanel #gestureCue{font-size:13px;color:#fff;border-top:1px solid #50545a;padding-top:12px}#posePanel[data-dragging="true"] #gestureCue{color:#e8c167}#posePanel p{font-size:12px;line-height:1.65;color:#bec6d0}#poseReadout{font:12px/1.8 monospace;color:#e8c167}#contactVerdict{min-height:40px}#replayPanel{position:fixed;bottom:162px;left:50%;transform:translateX(-50%);width:min(760px,90vw);padding:16px;z-index:6}#replayPanel strong{font-size:12px;color:#e8c167}#replayPanel .row{align-items:center;justify-content:space-between}#replayPanel input{padding:0;width:100%;accent-color:#e8c167}#replayPanel select{width:auto;font-size:10px}#replayPanel button{font-size:10px;padding:10px}#replayPanel p{font-size:12px;margin-bottom:0;color:#e8c167}#posePanel{max-height:calc(75vh - 100px);overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin}#replayPanel .row{flex-wrap:wrap}@media(max-height:800px){#posePanel{top:215px;left:16px;width:215px;max-height:calc(100vh - 295px);padding:12px}#posePanel h3{font-size:16px;margin:8px 0}#posePanel p{line-height:1.4;margin:8px 0}#posePanel button{padding:8px;font-size:10px}#replayPanel{bottom:125px;padding:12px}}#posePanel[hidden],#replayPanel[hidden]{display:none}`;document.head.append(style);
let originX=.8,inspectPose=false,repeatPractice=false;
let yaw=0,pitch=-15,depth=0,mouse=[.19,.60],points=[],drag=false,rotate=false,start=0,length=0,previous=mouse.slice(),lastSend=0;
let phaseKey='',phaseStart=0,clip=null,loading='',replayT=0,playing=true,speed=.25,showContact=true,camera='front',lastFrame=performance.now(),hitSound=false;
window.physicsFrame='{}';window.handPose='{}';window.combatDiagnostics={};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const ownTurn=()=>state?.phase==='aim'&&state.turn===you;
function xy(e){const r=canvas.getBoundingClientRect();return [clamp((e.clientX-r.left)/r.width,0,1),clamp((e.clientY-r.top)/r.height,0,1)];}
function sample(){if(points.length>=179)return;const t=performance.now()-start;points.push([...mouse,Math.round(t),yaw,pitch,depth]);}
canvas.addEventListener('pointerdown',e=>{
 if(e.button===2){if(!ownTurn())sendAction({action:'brace'});return;}
 if(e.button!==0||!ownTurn())return;e.preventDefault();canvas.setPointerCapture(e.pointerId);
 const pointer=xy(e);originX=pointer[0];mouse=[.19,pointer[1]];previous=mouse.slice();length=0;points=[];start=performance.now();lastSend=0;drag=true;sample();sendAction({action:"pose",x:mouse[0],y:mouse[1],progress:0,tilt:pitch,restart:true});
});
canvas.addEventListener('pointermove',e=>{
 if(!ownTurn())return;
 if(rotate){yaw=clamp(yaw+e.movementX*.30,-65,65);pitch=clamp(pitch+e.movementY*.30,-55,55);}
 const pointer=xy(e);mouse=[drag?clamp(.19+(originX-pointer[0])*1.5,0,1):.19,pointer[1]];
 if(drag){length+=Math.hypot(mouse[0]-previous[0],mouse[1]-previous[1]);previous=mouse.slice();if(performance.now()-lastSend>12){sample();lastSend=performance.now();}}
});
window.addEventListener('pointerup',e=>{
 if(e.button===2)rotate=false;
 if(e.button!==0||!drag)return;sample();drag=false;
 if(ownTurn()){sendAction({action:state.practice_done&&!repeatPractice?'slap':'practice',points,turn_id:state.turn_id,version:3});repeatPractice=false;}
});
canvas.addEventListener('wheel',e=>{if(!ownTurn())return;e.preventDefault();pitch=clamp(pitch+Math.sign(e.deltaY)*3,-45,45);},{passive:false});
window.addEventListener('blur',()=>{drag=false;rotate=false;});
document.getElementById('repeatPractice').onclick=()=>{if(ownTurn()&&!drag)repeatPractice=true;canvas.focus();};
document.getElementById('poseCamera').onclick=()=>{if(ownTurn()&&!drag)inspectPose=!inspectPose;canvas.focus();};
document.getElementById('resetPose').onclick=()=>{yaw=0;pitch=-15;depth=0;canvas.focus();};
document.getElementById('replayPlay').onclick=()=>playing=!playing;
document.getElementById('replayStep').onclick=()=>{playing=false;replayT=clamp(replayT+1/120,0,2.8);};
document.getElementById('replaySeek').oninput=e=>{playing=false;replayT=+e.target.value;};
document.getElementById('replaySpeed').onchange=e=>speed=+e.target.value;
document.getElementById('replayCamera').onchange=e=>camera=e.target.value;
document.getElementById('replayContact').onclick=()=>showContact=!showContact;
document.getElementById('replayImpact').onclick=()=>{if(!clip)return;playing=false;replayT=clip.contact;showContact=true;camera='side';document.getElementById('replayCamera').value=camera;};
document.getElementById('replaySkip').onclick=()=>sendAction({action:'skip_replay'});
let lastInspection=0;
function keepReplayForInspection(e){
 if(state?.phase!=='replay'||!clip||e.target.id==='replaySkip')return;
 const now=performance.now();if(now-lastInspection<500)return;lastInspection=now;
 sendAction({action:'inspect_replay',replay_id:state.replay_id});
}
for(const event of ['input','change','click'])replayPanel.addEventListener(event,keepReplayForInspection);
function armAt(t){
 const path=clip.arm_path;if(!path?.length)return null;
 const time=clip.contact_time+(t-clip.contact);
 let a=path[0],b=a;for(let i=1;i<path.length;i++){b=path[i];if(b.time>=time)break;a=b;}
 const f=clamp((time-a.time)/Math.max(.000001,b.time-a.time),0,1),pose={};
 for(const k of ['root','shoulder','elbow','wrist','angles','finger_direction','palm_normal'])pose[k]=a.pose[k].map((v,i)=>v+(b.pose[k][i]-v)*f);
 pose.finger_relax=(a.pose.finger_relax||0)+((b.pose.finger_relax||0)-(a.pose.finger_relax||0))*f;
 pose.torso_yaw=(a.pose.torso_yaw||0)+((b.pose.torso_yaw||0)-(a.pose.torso_yaw||0))*f;
 return {pose,tilt:a.tilt+(b.tilt-a.tilt)*f};
}
function handAt(t){
 const path=clip.path;if(!path?.length)return [1,-.8,1.1,-18,0];
 const pathTime=clip.contact_time+(t-clip.contact);
 let a=path[0],b=a;for(let i=1;i<path.length;i++){b=path[i];if(b[0]>=pathTime)break;a=b;}
 const f=clamp((pathTime-a[0])/Math.max(.00001,b[0]-a[0]),0,1);
 const pose=a.slice(1).map((v,i)=>v+(b[i+1]-v)*f);
 // Contact stops the driven hand; afterwards withdraw, never pass through the skull.
 if(t>clip.contact){pose[2]+=Math.min(.8,(t-clip.contact)*2.2);pose[0]+=(t-clip.contact)*.55;}
 return pose;
}
async function fetchClip(id){
 loading=id;try{const response=await fetch('/api/replay/'+id);if(!response.ok)throw Error('Replay nicht verfügbar');const data=await response.json();if(state?.replay_id===id){clip=data;window.combatDiagnostics.clipId=id;window.combatDiagnostics.frameCount=data.frames.length;window.combatDiagnostics.peak=data.peak;}}
 catch(e){toast(e.message);window.combatDiagnostics.error=e.message;}finally{loading='';}
}
function frame(now){
 const dt=Math.min(.1,(now-lastFrame)/1000);lastFrame=now;
 const active=!!state&&document.body.classList.contains('playing');
 panel.hidden=!active||!ownTurn();replayPanel.hidden=!active||state.phase!=='replay';
 if(active){
   const clock=document.getElementById('scoreClock');if(clock){const seconds=Math.max(0,Math.ceil(state.remaining));const label=state.phase==='replay'?'ZEITLUPE':state.phase==='over'?'ENTSCHEIDUNG':Math.floor(seconds/60)+':'+String(seconds%60).padStart(2,'0');if(clock.textContent!==label)clock.textContent=label;}
   const key=state.match_id+':'+state.turn_id+':'+state.phase;
   if(key!==phaseKey){phaseKey=key;phaseStart=now;drag=false;rotate=false;if(state.phase==='aim'){repeatPractice=false;length=0;mouse=[.19,.60];window.netArm=null;inspectPose=false;}if(state.phase==='impact'){phaseStart=now-(2.8-state.remaining)*1000;hitSound=false;}if(state.phase==='replay'){replayT=0;playing=true;}}
   if(state.replay_id&&clip?.id!==state.replay_id&&loading!==state.replay_id)fetchClip(state.replay_id);
   if(ownTurn()){
      const strikes=state.practice_done&&!repeatPractice;
      panel.dataset.mode=strikes?'strike':'practice';panel.dataset.dragging=String(drag);
      document.getElementById('practiceStep').setAttribute('aria-current',strikes?'false':'step');
      document.getElementById('strikeStep').setAttribute('aria-current',strikes?'step':'false');
      document.getElementById('poseTitle').textContent=strikes?'NÄCHSTER ZUG ZÄHLT':'ÜBEN · OHNE SCHADEN';
      document.getElementById('gestureCue').innerHTML=drag?'<b>← WEITER NACH LINKS ZIEHEN</b><br>Loslassen '+(strikes?'führt den Schlag aus.':'wertet nur die Probe aus.'):'<b>LINKE MAUSTASTE HALTEN</b><br>Dann nach links ziehen und loslassen.';
      document.getElementById('poseReadout').textContent=window.netArm?.pose?.wrist_limited?'HANDGELENK AM ANSCHLAG':'Handneigung: '+pitch+'° · Start: −15°';
      const repeatButton=document.getElementById('repeatPractice');repeatButton.hidden=!state.practice_done;repeatButton.disabled=drag||repeatPractice;repeatButton.textContent=repeatPractice?'NÄCHSTER SCHWUNG: NUR PROBE':'NOCH EINMAL OHNE SCHADEN ÜBEN';
      const viewButton=document.getElementById('poseCamera');viewButton.textContent=inspectPose?'ZURÜCK ZUR EGOANSICHT':'HAND VON DER SEITE ANSEHEN';viewButton.setAttribute('aria-pressed',String(inspectPose));viewButton.disabled=drag;
      document.getElementById('poseCameraHint').hidden=!inspectPose;
      document.getElementById('contactVerdict').textContent=state.diagnosis||'Ziel: die ganze Handfläche seitlich an die Wange. Die Probe zeigt, welcher Teil zuerst trifft.';
      document.getElementById('phaseTitle').textContent=state.practice_done&&!repeatPractice?'ZWEI. SCHLAG.':'EINS. PROBE.';
      document.getElementById('phaseHint').textContent=state.practice_done&&!repeatPractice?'Nächster Zug nach links zählt als Schlag. Oder nochmals üben.':'Linke Maustaste halten, nach links ziehen, loslassen. Ohne Schaden.';
   }
   if(state.phase==='resolving'){document.getElementById('phaseTitle').textContent='KONTAKT WIRD BERECHNET';document.getElementById('phaseHint').textContent='Der Host prüft Handkontakt und Gewebe.';}
   if(state.phase==='impact'){document.getElementById('phaseTitle').textContent='';document.getElementById('phaseHint').textContent=state.diagnosis;}
   if(state.phase==='replay'){
      document.getElementById('phaseTitle').textContent='DER KONTAKT ENTSCHEIDET';document.getElementById('phaseHint').textContent='Gespeicherte Physik · beide Spieler sehen denselben Treffer';
      if(playing)replayT=Math.min(2.8,replayT+dt*speed);
      if(replayT>=2.8)playing=false;
      document.getElementById('replaySeek').value=replayT;
      document.getElementById('replayPlay').textContent=playing?'PAUSE':'ABSPIELEN';
      document.getElementById('replayTime').textContent=replayT.toFixed(2)+' s · noch '+Math.ceil(state.remaining)+' s';
      document.getElementById('replayVerdict').textContent=state.diagnosis;
      document.getElementById('contactLegend').hidden=!(showContact&&clip&&Math.abs(replayT-clip.contact)<.025&&clip.footprint?.length);
      document.getElementById('replayContact').textContent=showContact?'PUNKTE AN':'PUNKTE AUS';
      document.getElementById('replaySkip').textContent=state.replay_skip.includes(you)?'WARTE AUF GEGNER':'WEITER';
   }
 }
 const progress=drag?Math.min(1,length/.23):0;
 if(ownTurn()&&now-(window.lastPoseSent||0)>80){window.lastPoseSent=now;sendAction({action:'pose',x:mouse[0],y:mouse[1],progress,tilt:pitch});}
 window.handPose=JSON.stringify({active:ownTurn(),arm:window.netArm||null,dragging:drag,camera:inspectPose?'side':'front'});
 if(active&&clip?.id===state.replay_id&&(['impact','replay'].includes(state.phase)||(state.phase==='over'&&clip.ko))){
   const t=state.phase==='over'?2.8:state.phase==='replay'?replayT:clamp((now-phaseStart)/1000,0,2.8);
   const fi=Math.min(clip.frames.length-1,t*clip.fps),i=Math.floor(fi),j=Math.min(i+1,clip.frames.length-1),f=fi-i;
   const values=clip.frames[i].map((v,k)=>v+(clip.frames[j][k]-v)*f);
   const headOffset=clip.head_positions?clip.head_positions[i].map((v,k)=>v+(clip.head_positions[j][k]-v)*f):[0,0,0];
   const headRotation=clip.head_rotations?clip.head_rotations[i].map((v,k)=>v+(clip.head_rotations[j][k]-v)*f):[0,values[0],0];
   window.physicsFrame=JSON.stringify({head_rotation:headRotation,head_offset:headOffset,id:clip.id,time:t,contact:clip.contact,crowd_hit:clip.contact_class!=='miss'&&(clip.impact_speed_m_s||0)>.05,side_cage:clip.side_cage||{},head:values[0],jaw:values[1],offsets:values.slice(2).map(v=>v*clip.scale),ko:!!clip.ko,body:clip.body_frames?.[Math.min(clip.body_frames.length-1,Math.floor(t*clip.fps))]||[0,0,0,0,0],target:clip.target,players:t<clip.contact?clip.before:clip.after,hand:handAt(t),arm:armAt(t),replay:state.phase==='replay',camera,footprint:showContact&&state.phase==='replay'&&Math.abs(t-clip.contact)<.025?clip.footprint:[]});
   window.combatDiagnostics.time=t;window.combatDiagnostics.frame=i;window.combatDiagnostics.deformation=Math.max(...values.slice(2).map(Math.abs))*clip.scale;
   if(state.phase==='impact'&&t>=clip.contact&&!hitSound&&clip.contact_class!=='miss'){hitSound=true;window.contactSound=true;}
 }else window.physicsFrame='{}';
 requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
})();
