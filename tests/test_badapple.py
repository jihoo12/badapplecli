import unittest
from unittest.mock import patch

import badapple


class RenderTests(unittest.TestCase):
    def test_half_blocks(self):
        data = bytes([0, 255, 255, 255, 255, 0, 0, 255])
        self.assertEqual(badapple.render_frame(data, 4, 2, 128, False), "\x1b[H▄▀▀█")

    def test_inverted(self):
        data = bytes([0, 255, 255, 0])
        self.assertEqual(badapple.render_frame(data, 2, 2, 128, True), "\x1b[H▀▄")

    def test_terminal_geometry_fits(self):
        for columns, lines in [(80, 24), (120, 40), (12, 6)]:
            w, h = badapple.video_dimensions(columns, lines)
            self.assertLessEqual(w, columns)
            self.assertLessEqual(h // 2, lines - 1)
            self.assertEqual(h % 2, 0)

    def test_narrow_terminal(self):
        with self.assertRaises(ValueError):
            badapple.video_dimensions(10, 4)

    def test_cli_rejects_bad_fps(self):
        with self.assertRaises(SystemExit) as error:
            badapple.main(["--fps", "0", "--download-only"])
        self.assertEqual(error.exception.code, 2)

    def test_download_cache_skips_network(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "video.mp4"
            path.write_bytes(b"cached")
            with patch.object(badapple, "urlopen") as fetch:
                badapple.download_video(path)
            fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
