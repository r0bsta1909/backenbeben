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

    def test_midpoint_preserves_energy_and_converges_in_phase(self):
        results = [run(rate, method="midpoint") for rate in (960, 1920, 3840, 7680)]
        for result in results:
            self.assertAlmostEqual(result["energy_retained_fraction"], 1., places=8)
            self.assertLess(result["max_discrete_state_error_m"], 1e-10)
            self.assertLess(result["max_momentum_error_ns"], 1e-8)
            self.assertLess(result["max_com_error_m"], 1e-10)
        for coarse, fine in zip(results, results[1:]):
            self.assertLess(fine["continuous_phase_state_error_m"],
                            .27 * coarse["continuous_phase_state_error_m"])
        self.assertLess(results[0]["continuous_phase_state_error_m"],
                        run(960)["continuous_phase_state_error_m"])

    def test_midpoint_three_dimensional_time_reversal_and_pinned_anchor(self):
        import numpy as np
        from contact_constraint import advance_attachment_midpoint
        h = np.array([.31, .002, -.003])
        a = np.array([.01, -.002, .001])
        vh = np.array([-.2, .07, .11])
        va = np.array([.01, -.03, .02])
        rest = np.array([.3, 0., 0.])
        args = (1/.18, 1/2., rest, 1/960, 2e-5)
        hn, an, vhn, van = advance_attachment_midpoint(h, a, vh, va, *args)
        hr, ar, vhr, var = advance_attachment_midpoint(hn, an, -vhn, -van, *args)
        for actual, expected in ((hr,h), (ar,a), (vhr,-vh), (var,-va)):
            np.testing.assert_allclose(actual, expected, atol=1e-11, rtol=0)
        result = advance_attachment_midpoint(h,a,vh,np.zeros(3),1/.18,0.,rest,1/960,2e-5)
        np.testing.assert_array_equal(result[1],a)
        np.testing.assert_array_equal(result[3],np.zeros(3))

    def test_midpoint_rejects_invalid_parameters(self):
        import numpy as np
        from contact_constraint import advance_attachment_midpoint
        zero = np.zeros(3)
        for dt, compliance in ((0.,1.),(-1.,1.),(float("nan"),1.),(.01,0.),(.01,-1.)):
            with self.assertRaises(ValueError):
                advance_attachment_midpoint(zero,zero,zero,zero,1.,1.,zero,dt,compliance)
