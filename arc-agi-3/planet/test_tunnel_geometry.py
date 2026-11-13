import math
import unittest

from tunnel_geometry import TunnelChord
from outer_eye_cube import OuterEyeCube, Wire


class TunnelGeometryTests(unittest.TestCase):
    def test_known_right_angle(self):
        c = TunnelChord(90, 0)
        self.assertEqual(c.direction, 45)
        self.assertEqual(c.half_angle, 45)
        self.assertAlmostEqual(c.depth, 1-math.sqrt(.5))
        self.assertAlmostEqual(c.opening, math.sqrt(.5))

    def test_agrees_with_legacy_non_degenerate_chords(self):
        # chord() is pure; do not call focus() or its config-writing CLI.
        from chord import chord
        for y,x in [(90,0),(120,30),(60,0),(350,10),(10,350),(150,0)]:
            old, new = chord(y,x), TunnelChord(y,x)
            self.assertAlmostEqual(old['direction_deg'], new.direction, places=2)
            self.assertAlmostEqual(old['depth'], new.depth, places=4)
            self.assertAlmostEqual(old['law']['theta_deg'], new.half_angle, places=2)
            self.assertAlmostEqual(old['law']['opening'], new.opening, places=4)

    def test_rotate_both_steers_without_widening(self):
        a,b = TunnelChord(90,0), TunnelChord(120,30)
        self.assertEqual(b.direction-a.direction,30)
        self.assertEqual(a.depth,b.depth)
        self.assertEqual(a.opening,b.opening)

    def test_symmetric_endpoint_change_widens_without_steering(self):
        a,b = TunnelChord(30,10), TunnelChord(40,0)
        self.assertEqual(a.direction,b.direction)
        self.assertGreater(b.opening,a.opening)
        self.assertGreater(b.solid_angle,a.solid_angle)

    def test_wrap_and_endpoint_exchange(self):
        a,b = TunnelChord(350,10), TunnelChord(10,350)
        self.assertEqual(a.direction,0)
        self.assertEqual(a.direction,b.direction)
        self.assertEqual(a.depth,b.depth)
        self.assertEqual(a,TunnelChord(-10,370))

    def test_euler_geometry_closure_not_quality(self):
        for y in range(0,360,7):
            for x in range(0,360,11):
                if abs((y-x+180)%360-180)==180:
                    continue
                c=TunnelChord(y,x)
                self.assertLess(c.closure_residual,1e-14)
                self.assertAlmostEqual(sum(a*b for a,b in zip(c.midpoint,c.half_chord)),0)

    def test_coincident_closed_without_infinite_concentration(self):
        c=TunnelChord(10,370)
        self.assertEqual(c.opening,0)
        self.assertEqual(c.solid_angle,0)
        self.assertIsNone(c.snapshot()['concentration_per_sr'])
        self.assertTrue(c.snapshot()['closed'])

    def test_ambiguous_diameter_rejected(self):
        for a,b in [(180,0),(0,180),(90,270)]:
            with self.assertRaises(ValueError):
                TunnelChord(a,b)

    def test_invalid_angles(self):
        for value in (True,math.nan,math.inf,1e10,'30',None):
            with self.assertRaises(ValueError):
                TunnelChord(value,0)


class TunnelBindingTests(unittest.TestCase):
    def cube(self):
        return OuterEyeCube([Wire('probe','probe','front',.65,.45,('safe',)),
                             Wire('centre','model','front',0,0)])

    def test_stale_binding_stays_stale_even_when_view_returns(self):
        cube=self.cube()
        s=cube.shave_to('front','probe')
        cube.connect('front','probe')
        cube.update_tunnel(s.id,s.chord.theta_y+90,s.chord.theta_x+90)
        self.assertFalse(cube.visible('front','probe'))
        report=cube.inspect('front','probe',{'safe':True})
        self.assertEqual(report['state'],'stale_connection')
        self.assertFalse(report['eligible_for_proposal'])
        cube.update_tunnel(s.id,s.chord.theta_y,s.chord.theta_x)
        self.assertTrue(cube.visible('front','probe'))
        self.assertEqual(cube.inspect('front','probe')['state'],'stale_connection')
        cube.connect('front','probe')
        report=cube.inspect('front','probe',{'safe':True})
        self.assertEqual(report['state'],'proposal_ready')
        self.assertTrue(report['binding_visible'])
        self.assertFalse(report['execution_authorized'])

    def test_other_binding_and_fixed_eye_survive_shift(self):
        cube=self.cube()
        cube.connect('front','centre')
        s=cube.shave_to('front','probe')
        positions={k:e.position for k,e in cube.eyes.items()}
        cube.update_tunnel(s.id,s.chord.theta_y+30,s.chord.theta_x+30)
        self.assertEqual(cube.inspect('front','centre')['state'],'proposal_ready')
        self.assertEqual(positions,{k:e.position for k,e in cube.eyes.items()})
        self.assertEqual(len(cube.shaves),1)

    def test_closed_chord_resolves_nothing(self):
        cube=self.cube()
        s=cube.shave_to('front','probe')
        cube.update_tunnel(s.id,s.chord.direction,s.chord.direction)
        self.assertFalse(cube.visible('front','probe'))

    def test_invalid_update_is_atomic(self):
        cube=self.cube()
        s=cube.shave_to('front','probe')
        cube.connect('front','probe')
        with self.assertRaises(ValueError):
            cube.update_tunnel(s.id,180,0)
        self.assertEqual(cube.shaves,(s,))
        self.assertTrue(cube.inspect('front','probe')['binding_current'])

    def test_equivalent_endpoint_update_is_noop(self):
        cube=self.cube()
        s=cube.add_tunnel('front',30,10)
        self.assertEqual(cube.update_tunnel(s.id,390,370),s)

    def test_no_visibility_bypass_from_another_tunnel(self):
        cube=self.cube()
        s=cube.shave_to('front','probe')
        cube.connect('front','probe')
        cube.add_tunnel('front',s.chord.theta_y,s.chord.theta_x,azimuth=s.azimuth)
        cube.update_tunnel(s.id,s.chord.theta_y+60,s.chord.theta_x+60)
        self.assertTrue(cube.visible('front','probe'))
        self.assertFalse(cube.inspect('front','probe',{'safe':True})['eligible_for_proposal'])


if __name__ == '__main__':
    unittest.main()
