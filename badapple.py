#!/usr/bin/env python3
"""Play the Bad Apple!! shadow-art video in a terminal (Python + FFmpeg)."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.request import Request, urlopen

# Public mirror of the original Niconico PV (sm8628149); media is NOT part of
# this repository's source-code license. See NOTICE.md.
VIDEO_URL = (
    "https://archive.org/download/nicovideo-sm8628149/"
    "nicovideo-sm8628149_4c8a655c13612a596d6b97c58797d3c622adebddc6436264e47e615fdccb9d21.mp4"
)


def default_video_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME")
    if not base and os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
    return (Path(base) if base else Path.home() / ".cache") / "badapplecli" / "bad_apple.mp4"


def download_video(destination: Path) -> None:
    if destination.is_file() and destination.stat().st_size > 0:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    print(f"Downloading Bad Apple!! to {destination} ...", file=sys.stderr)
    try:
        request = Request(VIDEO_URL, headers={"User-Agent": "badapplecli/1.0"})
        with urlopen(request, timeout=45) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output)
        if temporary.stat().st_size == 0:
            raise OSError("downloaded file is empty")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    print("Download complete.", file=sys.stderr)


def video_dimensions(columns: int, lines: int, requested_width: int = 0) -> tuple[int, int]:
    """Fit 4:3 pixels into 1x2-pixel half-block terminal characters."""
    if columns < 12 or lines < 6:
        raise ValueError("Terminal must be at least 12 columns by 6 lines.")
    max_width = min(columns, requested_width or columns)
    # Keep one terminal line free and use an even number of pixel rows.
    width = min(max_width, int((lines - 1) * 2 * 4 / 3))
    pixel_height = max(2, (int(width * 3 / 4) // 2) * 2)
    return width, pixel_height


_COLOR_CACHE: dict[tuple[int, int], str] = {}


def render_frame(frame: bytes, width: int, height: int, threshold: int, invert: bool) -> str:
    """Render grayscale with truecolor: top pixel = foreground, bottom = background."""
    output = []
    for y in range(0, height, 2):
        top = y * width
        bottom = top + width
        line = []
        prev = None
        for x in range(width):
            u = frame[top + x]
            l = frame[bottom + x]
            if invert:
                u, l = 255 - u, 255 - l
            key = (u, l)
            if key != prev:                      # 색이 바뀔 때만 이스케이프 출력
                code = _COLOR_CACHE.get(key)
                if code is None:
                    code = f"\x1b[38;2;{u};{u};{u};48;2;{l};{l};{l}m"
                    _COLOR_CACHE[key] = code
                line.append(code)
                prev = key
            line.append("▀")
        line.append("\x1b[0m")
        output.append("".join(line))
    return "\x1b[H" + "\n".join(output)


@contextmanager
def terminal_mode():
    """Switch to the alternate screen and optionally enable single-key input."""
    fd = None
    saved = None
    if os.name != "nt" and sys.stdin.isatty():
        try:
            import termios
            import tty

            fd = sys.stdin.fileno()
            saved = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except (OSError, ValueError):
            fd, saved = None, None
    if os.name == "nt":
        # Enable ANSI escape codes in the classic Windows console as well.
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except (AttributeError, OSError):
            pass
    try:
        sys.stdout.write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H\x1b[97;40m")
        sys.stdout.flush()
        yield
    finally:
        sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        sys.stdout.flush()
        if saved is not None and fd is not None:
            import termios

            termios.tcsetattr(fd, termios.TCSADRAIN, saved)


def quit_pressed() -> bool:
    if not sys.stdin.isatty():
        return False
    if os.name == "nt":
        import msvcrt

        return msvcrt.kbhit() and msvcrt.getwch().lower() in ("q", "\x1b")
    import select

    if select.select([sys.stdin], [], [], 0)[0]:
        return os.read(sys.stdin.fileno(), 1) in (b"q", b"Q", b"\x1b")
    return False


def play_once(video: Path, args: argparse.Namespace) -> bool:
    """Return False if the user requested an early exit."""
    columns, lines = shutil.get_terminal_size(fallback=(80, 24))
    width, height = video_dimensions(columns, lines, args.width)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError("ffmpeg is required. Install FFmpeg and add it to PATH.")

    command = [
        ffmpeg, "-hide_banner", "-loglevel", "error",
        "-ss", str(args.seek), "-i", str(video),
        "-vf", f"fps={args.fps},scale={width}:{height}:flags=area,format=gray",
        "-an", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
    ]
    decoder = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    audio = None
    try:
        assert decoder.stdout is not None
        frame_size = width * height
        first = decoder.stdout.read(frame_size)
        if len(first) != frame_size:
            raise RuntimeError("Could not decode the video. Check that the file is a valid video.")

        if not args.no_audio:
            ffplay = shutil.which("ffplay")
            if ffplay:
                audio = subprocess.Popen(
                    [ffplay, "-hide_banner", "-loglevel", "error", "-nodisp",
                     "-autoexit", "-vn", "-ss", str(args.seek), str(video)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                # Never spoil the video just because audio playback is unavailable.
                print("Note: ffplay not found; playing without sound.", file=sys.stderr)

        start = time.monotonic()
        index = 0
        frame = first
        while len(frame) == frame_size:
            if quit_pressed():
                return False
            deadline = start + index / args.fps
            delay = deadline - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            elif delay < -0.15:
                # Drop late frames to stay close to the music clock.
                index += 1
                frame = decoder.stdout.read(frame_size)
                continue
            sys.stdout.write(render_frame(frame, width, height, args.threshold, args.invert))
            sys.stdout.flush()
            index += 1
            frame = decoder.stdout.read(frame_size)
        decoder.wait()
        if decoder.returncode != 0:
            raise RuntimeError("FFmpeg stopped unexpectedly while decoding the video.")
        if audio is not None:
            try:
                audio.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
        return True
    finally:
        if decoder.stdout:
            decoder.stdout.close()
        if decoder.poll() is None:
            decoder.terminate()
        try:
            decoder.wait(timeout=2)
        except subprocess.TimeoutExpired:
            decoder.kill()
            decoder.wait()
        if audio is not None and audio.poll() is None:
            audio.terminate()
            try:
                audio.wait(timeout=2)
            except subprocess.TimeoutExpired:
                audio.kill()
                audio.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Play Bad Apple!! as terminal half-block art.")
    parser.add_argument("--video", type=Path, help="Use a local video instead of downloading the PV")
    parser.add_argument("--download-only", action="store_true", help="Download/cache the PV without playing")
    parser.add_argument("--no-audio", action="store_true", help="Disable audio playback")
    parser.add_argument("--fps", type=int, default=20, help="Playback FPS (1-60; default: 20)")
    parser.add_argument("--width", type=int, default=0, help="Maximum width in terminal columns")
    parser.add_argument("--threshold", type=int, default=128, help="White threshold (0-255)")
    parser.add_argument("--invert", action="store_true", help="Invert black and white")
    parser.add_argument("--seek", type=float, default=0, help="Start at a given time in seconds")
    parser.add_argument("--loop", action="store_true", help="Repeat until q, Esc or Ctrl+C")
    args = parser.parse_args(argv)
    if not 1 <= args.fps <= 60:
        parser.error("--fps must be between 1 and 60")
    if args.width < 0 or (args.width and args.width < 12):
        parser.error("--width must be 0 or at least 12")
    if not 0 <= args.threshold <= 255:
        parser.error("--threshold must be between 0 and 255")
    if not 0 <= args.seek < 86400:
        parser.error("--seek must be between 0 and 86399 seconds")
    if args.download_only and args.video:
        parser.error("--download-only cannot be combined with --video")
    try:
        video = args.video or default_video_path()
        if not args.video:
            download_video(video)
        if args.download_only:
            print(f"Video saved at: {video}")
            return 0
        if not video.is_file():
            raise RuntimeError(f"Video not found: {video}")
        if not sys.stdout.isatty():
            raise RuntimeError("Run this player in an interactive terminal (TTY).")
        with terminal_mode():
            while True:
                if not play_once(video, args) or not args.loop:
                    break
        return 0
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"badapple: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
