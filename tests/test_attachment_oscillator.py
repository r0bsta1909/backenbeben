import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_attachment_oscillator import run


class AttachmentOscillatorTests(unittest.TestCase):
    def test_projection_matches_closed_form_and_conserves_momentum(self):
        for rate in (960, 1920, 3840):
            result = run(rate)
            self.assertLess(result["max_discrete_state_error_m"], 1e-11)
            self.assertLess(result["max_discrete_energy_error_j"], 1e-10)
            self.assertLess(result["max_momentum_error_ns"], 1e-9)
            self.assertLess(result["max_com_error_m"], 1e-10)

    def test_refinement_reduces_undamped_oscillator_error(self):
        results = [run(rate) for rate in (960, 1920, 3840, 7680, 15360)]
        for coarse, fine in zip(results, results[1:]):
            self.assertLess(fine["continuous_phase_state_error_m"], coarse["continuous_phase_state_error_m"])
            self.assertGreater(fine["energy_retained_fraction"], coarse["energy_retained_fraction"])
            self.assertLessEqual(fine["energy_retained_fraction"], 1.)
