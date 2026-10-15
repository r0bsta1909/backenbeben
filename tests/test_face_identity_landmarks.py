"""Silhouette requirements for the shipped contact geometry, in game metres."""
import json
import unittest
from pathlib import Path


class FaceIdentityLandmarks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = json.loads((Path(__file__).resolve().parents[1] /
                                  'game/assets/face_customizable_collision.json').read_text())['faces']

    def delta(self, identity, selection, axis, width=False):
        base = self.profiles[0]
        indices = [i for i, point in enumerate(base) if selection(point)]
        self.assertGreater(len(indices), 50, 'Landmark region lost its surface')
        def coordinate(point):
            return abs(point[axis]) if width else point[axis]
        return sum(coordinate(self.profiles[identity][i]) - coordinate(base[i])
                   for i in indices) / len(indices)

    def test_angular_and_narrow_jaws_read_as_distinct_silhouettes(self):
        jaw = lambda p: .18 < abs(p[0]) < .32 and -.22 < p[1] < -.07 and p[2] > .1
        self.assertGreater(self.delta(1, jaw, 0, True), .025)
        self.assertLess(self.delta(3, jaw, 0, True), -.035)

    def test_soft_face_has_full_cheeks_and_shorter_chin(self):
        cheek = lambda p: .15 < abs(p[0]) < .30 and .05 < p[1] < .20 and p[2] > .1
        chin = lambda p: abs(p[0]) < .08 and -.23 < p[1] < -.13 and p[2] > .1
        self.assertGreater(self.delta(2, cheek, 0, True), .010)
        self.assertGreater(self.delta(2, chin, 1), .030)
        self.assertLess(self.delta(3, chin, 1), -.025)


if __name__ == '__main__':
    unittest.main()
