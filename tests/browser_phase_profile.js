(() => {
                const samples={},segments=[];let last=0,previous='',start=0,mirrorStart=0;
                function tick(t){
                    let phase='loading';
                    try { if(window.gameReady){const view=JSON.parse(renderState),s=view.state;
                        phase=s?.phase||'lobby';
                        if(phase==='impact')phase=s.event?.target===view.you?'impact_receiver':'impact_striker';
                        if(phase==='aim')phase=document.getElementById('posePanel')?.dataset.dragging==='true'?'stroke':'aim_idle';
                        if(phase==='replay')phase=document.getElementById('replayPlay')?.textContent==='PAUSE'?'replay_playing':'replay_paused';
                    }} catch (_) {}
                    if(document.hidden)phase='hidden';
                    if(phase!==previous){const draws=window.godotStats?.mirror_draw_requests||0;if(previous)segments.push({phase:previous,ms:t-start,mirror_draws:draws-mirrorStart});start=t;mirrorStart=draws;}
                    else if(last&&phase!=='loading'&&phase!=='hidden'){
                        const list=samples[phase]||(samples[phase]=[]);if(list.length<20000)list.push(t-last);
                    }
                    previous=phase;last=t;requestAnimationFrame(tick);
                }
                window.phasePerformance=()=>({samples,segments:[...segments,{phase:previous,ms:performance.now()-start}],
                    viewport:[innerWidth,innerHeight],devicePixelRatio,hardwareConcurrency:navigator.hardwareConcurrency});
                requestAnimationFrame(tick);
            })();
