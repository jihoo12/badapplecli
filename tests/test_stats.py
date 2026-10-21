"""Regression tests for stats visibility after the alternate screen closes."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import badapple


class TtyStdout:
    def isatty(self):
        return True


class RecordingStderr(io.StringIO):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def write(self, text):
        self.events.append(("stderr", text))
        return super().write(text)


class StatsDisplayTests(unittest.TestCase):
    def _run(self, interrupted=False):
        events = []
        stderr = RecordingStderr(events)

        @contextlib.contextmanager
        def fake_terminal_mode():
            events.append(("terminal", "enter"))
            try:
                yield
            finally:
                events.append(("terminal", "exit"))

        def fake_play(video, args, reports):
            reports.append("[badapple] frames=1 dropped=0")
            if interrupted:
                raise KeyboardInterrupt
            return False

        with tempfile.TemporaryDirectory() as dirname:
            video = Path(dirname) / "input.mp4"
            video.touch()
            with (
                patch.object(badapple, "terminal_mode", fake_terminal_mode),
                patch.object(badapple, "play_once", side_effect=fake_play),
                patch.object(badapple.sys, "stdout", TtyStdout()),
                patch.object(badapple.sys, "stderr", stderr),
            ):
                code = badapple.main(["--video", str(video), "--stats", "--no-audio"])

        self.assertIn("[badapple] frames=1 dropped=0", stderr.getvalue())
        self.assertEqual(events[0], ("terminal", "enter"))
        self.assertEqual(events[1], ("terminal", "exit"))
        self.assertTrue(all(event[0] == "stderr" for event in events[2:]))
        return code

    def test_stats_print_after_normal_playback(self):
        self.assertEqual(self._run(), 0)

    def test_stats_print_after_ctrl_c(self):
        self.assertEqual(self._run(interrupted=True), 130)


if __name__ == "__main__":
    unittest.main()
