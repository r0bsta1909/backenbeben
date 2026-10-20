"""Single elimination bracket; transport and combat live in host.py."""
import secrets

MAX_PLAYERS = 20
EXTRA_PAIRS = 3


class Tournament:
    def __init__(self, code, owner, name):
        self.id = code
        self.owner = owner
        self.status = 'waiting'
        self.entries = {}
        self.rounds = []
        self.champion = None
        self.cancel_reason = ''
        self.add(owner, name)

    def add(self, uid, name):
        if self.status != 'waiting':
            raise ValueError('Dieses Turnier läuft bereits.')
        if uid in self.entries:
            return
        if len(self.entries) >= MAX_PLAYERS:
            raise ValueError('Das Turnier ist voll (maximal 20 Spieler).')
        self.entries[uid] = dict(id=uid, name=name, active=True)

    def start(self, uid):
        if uid != self.owner:
            raise ValueError('Nur der Veranstalter kann das Turnier starten.')
        if self.status != 'waiting':
            raise ValueError('Dieses Turnier wurde bereits gestartet.')
        if len(self.entries) < 2:
            raise ValueError('Mindestens zwei Spieler werden benötigt.')
        seeds = list(self.entries)
        secrets.SystemRandom().shuffle(seeds)
        size = 1 << (len(seeds)-1).bit_length()
        byes = size-len(seeds)
        pairs = [[seeds.pop(), None] for _ in range(byes)]
        pairs += [[seeds.pop(), seeds.pop()] for _ in range((size//2)-byes)]
        secrets.SystemRandom().shuffle(pairs)
        self.status = 'running'
        self._round(pairs)
        self.settle()

    def _round(self, pairs):
        number = len(self.rounds)+1
        self.rounds.append([dict(id=f'r{number}m{i+1}', players=pair,
                                 status='ready', winner=None, reason='', room=None)
                            for i, pair in enumerate(pairs)])

    def match(self, match_id):
        return next(m for rnd in self.rounds for m in rnd if m['id'] == match_id)

    def settle(self):
        """Resolve byes/withdrawals, then create the next round exactly once."""
        while self.status == 'running':
            rnd = self.rounds[-1]
            for m in rnd:
                if m['status'] == 'done':
                    continue
                available = [p for p in m['players'] if p and self.entries[p]['active']]
                if len(available) < 2:
                    m.update(status='done', winner=available[0] if available else None,
                             reason='bye' if None in m['players'] else 'forfeit')
            if any(m['status'] != 'done' for m in rnd):
                return
            winners = [m['winner'] if m['winner'] and self.entries[m['winner']]['active'] else None for m in rnd]
            if len(winners) == 1:
                self.champion = winners[0]
                self.status = 'finished' if self.champion else 'cancelled'
                if not self.champion:self.cancel_reason = 'Keine verbleibenden Teilnehmer.'
                return
            self._round([winners[i:i+2] for i in range(0, len(winners), 2)])

    def finish(self, match_id, winner, reason):
        m = self.match(match_id)
        if m['status'] == 'done':
            return False
        if winner not in m['players'] or winner is None:
            raise ValueError('Ungültiger Turniersieger.')
        m.update(status='done', winner=winner, reason=reason)
        self.settle()
        return True

    def withdraw(self, uid):
        self.withdraw_many([uid])

    def withdraw_many(self, uids):
        """Apply a common expiry batch before awarding any walkovers."""
        uids=set(uids)
        if self.status == 'waiting':
            for uid in uids:self.entries.pop(uid,None)
        elif self.status == 'running':
            for uid in uids:
                if uid in self.entries:self.entries[uid]['active'] = False
            self.settle()
        if self.owner in uids:
            self.owner = next((p for p,e in self.entries.items() if e['active'] and p not in uids), None)

    def public(self):
        # Copy nested mutable structures: snapshots must not change after sending.
        return dict(id=self.id, owner=self.owner, status=self.status,
                    entries=[dict(e) for e in self.entries.values()],
                    rounds=[[dict(m, players=list(m['players'])) for m in rnd] for rnd in self.rounds],
                    champion=self.champion, cancel_reason=self.cancel_reason,
                    capacity=MAX_PLAYERS, extra_pairs=EXTRA_PAIRS)


def decision(room):
    """Return (winner, reason) or None while tournament overtime continues."""
    if room['hits'] < int(room['settings']['max_pairs'])*2 or room['hits'] % 2:
        return None
    a, b = room['players']
    if a['points'] != b['points']:
        return (0 if a['points'] > b['points'] else 1, 'points')
    if not room.get('tournament'):
        return (-1, 'draw')
    if room['hits'] < (int(room['settings']['max_pairs'])+EXTRA_PAIRS)*2:
        return None
    # Predrawn independent fair lot, used only after three tied extra pairs.
    return (room['tie_lot'], 'lot')
