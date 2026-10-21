"""Regression tests for differential ANSI rendering."""
import unittest
from renderer import FrameRenderer


class RendererTests(unittest.TestCase):
    def test_identical_frame(self):
        renderer = FrameRenderer(6, 4)
        frame = bytes(range(24))
        assert renderer.render(frame)
        self.assertEqual(renderer.render(frame), b"")
        self.assertEqual(renderer.stats.bytes_written, 0)

    def test_sparse_changes(self):
        renderer = FrameRenderer(80, 48)
        original = bytes(80 * 48)
        next_frame = bytearray(original)
        next_frame[100] = 255
        renderer.render(original)
        partial = renderer.render(bytes(next_frame))
        full = FrameRenderer(80, 48).render(bytes(next_frame))
        self.assertLess(len(partial), len(full) // 5)
        self.assertEqual(renderer.stats.painted_cells, 1)

    def test_dense_changes(self):
        renderer = FrameRenderer(8, 2)
        renderer.render(bytes(16))
        result = renderer.render(bytes([255] * 16))
        self.assertTrue(result.startswith(b"\x1b[1;1H"))
        self.assertEqual(renderer.stats.full_rows, 1)

    def test_mono_threshold(self):
        frame = bytes([0, 255, 0, 0, 0, 255, 255, 255])
        r = FrameRenderer(4, 2, mode="mono", threshold=128)
        self.assertEqual(r.render(frame).decode(), "\x1b[1;1H █▄▄")
        self.assertEqual(r.render(frame), b"")
        inverse = FrameRenderer(4, 2, mode="mono", invert=True)
        self.assertEqual(inverse.render(frame).decode(), "\x1b[1;1H█ ▀▀")

    def test_palette_equivalent(self):
        r = FrameRenderer(3, 2, mode="gray256")
        r.render(bytes([100] * 6))
        self.assertEqual(r.render(bytes([101] * 6)), b"")

    def test_reset(self):
        r = FrameRenderer(2, 2)
        old = r.render(bytes(4))
        r.reset()
        self.assertEqual(r.render(bytes(4)), old)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            FrameRenderer(2, 3)
        with self.assertRaises(ValueError):
            FrameRenderer(2, 2, mode="bad")
        with self.assertRaises(ValueError):
            FrameRenderer(2, 2).render(bytes(3))


if __name__ == "__main__":
    unittest.main()
