"""Bounded inspection time for a shared replay."""
REPLAY_SECONDS=12.
MAX_REPLAY_SECONDS=45.

def extend_inspection(room,replay_id,now):
    if room.get('phase')!='replay' or room.get('replay_id')!=replay_id:
        return False
    if now>=room['deadline']:
        return False
    deadline=min(room.get('replay_limit',room['deadline']),now+REPLAY_SECONDS)
    if deadline<=room['deadline']:
        return False
    room['deadline']=deadline
    return True
