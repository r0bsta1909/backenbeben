"""Explicit experimental coupled-friction host mode; coefficient is prototype tuning."""
from moving_head_replay import simulate as moving_simulate

def simulate(scored,braced=False):
    return moving_simulate(scored,braced,spatial=True,friction_coefficient=.2)
