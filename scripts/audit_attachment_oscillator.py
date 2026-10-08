"""Isolate attachment integration damping against independent closed forms."""
import json
import sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))
from contact_constraint import project_attachment


def run(rate, duration=.0125):
    dt = 1 / rate
    steps = round(duration * rate)
    mh, ma, compliance = .18, 2., 2e-5
    reduced = mh * ma / (mh + ma)
    omega2 = 1 / (compliance * reduced)
    omega = np.sqrt(omega2)
    x0, v0 = .001, -.2
    rest = np.array([.3, 0., 0.])
    hand = rest + np.array([x0, 0., 0.]) * ma / (mh + ma)
    arm = -np.array([x0, 0., 0.]) * mh / (mh + ma)
    vh = np.array([v0, 0., 0.]) * ma / (mh + ma)
    va = -np.array([v0, 0., 0.]) * mh / (mh + ma)
    com0 = (mh * hand + ma * arm) / (mh + ma)
    # Complex closed form of backward Euler; no projection recurrence reused.
    z0 = complex(x0, v0 / omega)
    factor = 1 / complex(1, omega * dt)
    e0 = .5 * reduced * v0**2 + .5 * x0**2 / compliance
    max_discrete_error = max_momentum = max_com_error = max_energy_error = 0.
    for step in range(1, steps + 1):
        oldh, olda = hand.copy(), arm.copy()
        hand, arm, _ = project_attachment(hand + dt * vh, arm + dt * va,
            1 / mh, 1 / ma, rest, dt, compliance, np.zeros(3))
        vh, va = (hand - oldh) / dt, (arm - olda) / dt
        x, v = (hand - arm - rest)[0], (vh - va)[0]
        expected = z0 * factor**step
        max_discrete_error = max(max_discrete_error, abs(x - expected.real), abs(v / omega - expected.imag))
        max_momentum = max(max_momentum, float(np.linalg.norm(mh * vh + ma * va)))
        max_com_error = max(max_com_error, float(np.linalg.norm((mh * hand + ma * arm) / (mh + ma) - com0)))
        energy = .5 * reduced * v**2 + .5 * x**2 / compliance
        max_energy_error = max(max_energy_error, abs(energy - e0 * (1 + omega2 * dt**2)**(-step)))
    exact = z0 * np.exp(-1j * omega * steps * dt)
    return dict(rate_hz=rate, duration_s=steps * dt, angular_frequency_rad_s=float(omega),
        max_discrete_state_error_m=max_discrete_error, max_momentum_error_ns=max_momentum,
        max_com_error_m=max_com_error, max_discrete_energy_error_j=max_energy_error,
        energy_retained_fraction=energy/e0, continuous_position_error_m=abs(x-exact.real),
        continuous_phase_state_error_m=abs(complex(x,v/omega)-exact))


if __name__ == "__main__":
    report = {"scope": "Two free masses, linear compliant attachment, no contacts or explicit damping. Not anatomical calibration.",
              "expected": "Backward Euler: E_n/E_0=(1+omega^2*dt^2)^(-n). Continuous oscillator conserves energy.",
              "runs": [run(rate) for rate in (960, 1920, 3840, 7680, 15360)]}
    target = ROOT / "docs/validation/attachment-oscillator.json"
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
