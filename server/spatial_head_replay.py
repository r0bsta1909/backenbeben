"""Explicit experimental host entry point for three-axis head rotation."""
from moving_head_replay import simulate as moving_simulate
def simulate(scored,braced=False):
    return moving_simulate(scored,braced,spatial=True)
