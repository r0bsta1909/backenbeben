"""Recorded, constrained KO fall. Stylized powered-body approximation, not ragdoll.
Feet stay planted; knees absorb the fall, then catchers arrest hip descent.
All samples are host-owned and replayed verbatim in either direction.
"""
import math

def collapse_track(ko, fps=120, duration=2.8):
    frames=[];drop=0.;velocity=0.
    for i in range(round(duration*fps)+1):
        t=i/fps-.5
        if ko and t>.12:
            # Gravity before the catch; damped support arrests the descent.
            support=max(0.,drop-.24)*180+max(0.,velocity)*14*min(1.,max(0.,(drop-.16)/.06))
            velocity+=(1.9-support)/fps
            drop=max(0.,min(.31,drop+velocity/fps))
        progress=min(1.,drop/.25)
        frames.append([round(drop,6),round(progress*.085,6),round(progress*.34,6),round(progress*.07,6),round(max(0.,min(1.,(t-.22)/.5)) if ko else 0.,6)])
    return frames
