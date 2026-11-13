import dataclasses
import math
import unittest

from outer_eye_cube import Eye, FACES, OuterEyeCube, Wire, face_point


class OuterEyeCubeTests(unittest.TestCase):
    def cube(self, **kwargs):
        return OuterEyeCube([
            Wire("centre", "planner", "front", 0, 0),
            Wire("probe", "probe", "front", .65, .45, ("unknown", "safe")),
            Wire("near", "observer", "front", .66, .46),
            Wire("far", "memory", "front", -.8, -.7),
            Wire("top", "helper", "top", .65, .45)], **kwargs)

    def test_face_bases_and_coordinates(self):
        for face, (normal, right, up) in FACES.items():
            self.assertEqual(face_point(face, 0, 0), normal)
            self.assertEqual(sum(a*b for a, b in zip(normal, right)), 0)
            self.assertEqual(sum(a*b for a, b in zip(normal, up)), 0)
            self.assertEqual(sum(a*b for a, b in zip(up, right)), 0)
            self.assertEqual(sum(x*x for x in right), 1)
            self.assertEqual(sum(x*x for x in up), 1)
            self.assertEqual(face_point(face, 1, 1), tuple(n+r+u for n,r,u in zip(normal,right,up)))

    def test_centre_visible_on_every_face(self):
        for face in FACES:
            cube = OuterEyeCube([Wire("w", "t", face, 0, 0)])
            self.assertTrue(cube.visible(face, "w"))

    def test_shaves_work_symmetrically_on_six_faces(self):
        for face in FACES:
            cube = OuterEyeCube([Wire("w", "t", face, .8, -.7)])
            self.assertFalse(cube.visible(face, "w"))
            cube.shave_to(face, "w")
            self.assertTrue(cube.visible(face, "w"))

    def test_shave_preserves_eye_and_prior_view(self):
        cube = self.cube()
        cube.connect("front", "centre")
        positions = {k: v.position for k, v in cube.eyes.items()}
        self.assertFalse(cube.visible("front", "probe"))
        cube.shave_to("front", "probe")
        self.assertEqual(positions, {k: v.position for k, v in cube.eyes.items()})
        self.assertTrue(cube.visible("front", "centre"))
        self.assertIn(("front", "centre"), cube.connections)

    def test_shave_is_a_cone_not_id_whitelist(self):
        cube = self.cube()
        cube.shave_to("front", "probe")
        self.assertTrue(cube.visible("front", "near"))
        self.assertFalse(cube.visible("front", "far"))

    def test_no_through_wall_connections(self):
        cube = self.cube()
        self.assertFalse(cube.visible("front", "top"))
        for action in (cube.shave_to, cube.connect):
            with self.assertRaises(ValueError):
                action("front", "top")
        self.assertEqual(cube.inspect("front", "top")["state"], "wrong_face")

    def test_connection_requires_view_but_view_does_not_connect(self):
        cube = self.cube()
        with self.assertRaises(ValueError):
            cube.connect("front", "probe")
        cube.shave_to("front", "probe")
        self.assertFalse(cube.inspect("front", "probe")["connected"])
        self.assertEqual(cube.inspect("front", "probe")["state"], "needs_connection")

    def test_condition_states_do_not_authorize_execution(self):
        cube = self.cube()
        cube.shave_to("front", "probe")
        cube.connect("front", "probe")
        for facts, state in [({}, "condition_unknown"), ({"safe": False}, "condition_blocked"),
                             ({"safe": True, "unknown": True}, "proposal_ready")]:
            report = cube.inspect("front", "probe", facts)
            self.assertEqual(report["state"], state)
            self.assertFalse(report["execution_authorized"])
        self.assertEqual(cube.inspect("front", "probe")["state"], "condition_unknown")

    def test_idempotence_and_budget(self):
        cube = self.cube(max_shaves=1)
        cube.shave_to("front", "probe")
        self.assertIsNone(cube.shave_to("front", "probe"))
        cube.connect("front", "probe")
        cube.connect("front", "probe")
        self.assertEqual(len(cube.connections), 1)
        with self.assertRaises(ValueError):
            cube.shave_to("front", "far")
        self.assertEqual(len(cube.shaves), 1)

    def test_zero_budget_keeps_base_view(self):
        cube = self.cube(max_shaves=0)
        cube.connect("front", "centre")
        with self.assertRaises(ValueError):
            cube.shave_to("front", "probe")

    def test_public_layout_immutable(self):
        cube = self.cube()
        with self.assertRaises(TypeError):
            cube.wires["probe"] = Wire("other", "t", "top", 0, 0)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cube.eyes["front"].face = "top"

    def test_scope_and_version_in_address(self):
        cube = self.cube(scope="level-2", version="layout-3")
        self.assertEqual(cube.connect("front", "centre"), ("level-2", "layout-3", "front", "centre"))
        fresh = self.cube(scope="level-3", version="layout-4")
        self.assertFalse(fresh.inspect("front", "centre")["connected"])

    def test_invalid_inputs(self):
        for value in (math.nan, math.inf, -1.1, 1.1, True, "0"):
            with self.assertRaises(ValueError):
                Wire("w", "t", "front", value, 0)
        for value in (0, -1, 46, math.nan):
            with self.assertRaises(ValueError):
                self.cube(base_angle=value)
        with self.assertRaises(ValueError):
            OuterEyeCube([Wire("w", "t", "front", 0, 0)] * 2)
        with self.assertRaises(ValueError):
            self.cube().inspect("front", "probe", {"safe": 1})

    def test_exact_aperture_edge(self):
        u = 1.92 * math.tan(math.radians(6))
        cube = OuterEyeCube([Wire("edge", "t", "front", u, 0),
                             Wire("outside", "t", "front", u + .001, 0)])
        self.assertTrue(cube.visible("front", "edge"))
        self.assertFalse(cube.visible("front", "outside"))


if __name__ == "__main__":
    unittest.main()
