#!/usr/bin/env python3
"""Synthetic renderer benchmark: terminal I/O and FFmpeg are not measured."""
import argparse
import time
from renderer import FrameRenderer


def frames(width, height, count):
    for i in range(count):
        frame = bytearray(width * height)
        left = 1 + i % max(1, width - width // 4 - 2)
        for y in range(height // 5, height // 2):
            for x in range(left, left + width // 4):
                frame[y * width + x] = 255
        yield bytes(frame)


def measure(source, width, height, mode, full):
    renderer = FrameRenderer(width, height, mode=mode)
    bytes_out = 0
    start = time.perf_counter()
    for frame in source:
        if full:
            renderer.reset()
        bytes_out += len(renderer.render(frame))
    return bytes_out, (time.perf_counter() - start) * 1000


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--width", type=int, default=100)
    p.add_argument("--height", type=int, default=60)
    p.add_argument("--frames", type=int, default=180)
    p.add_argument("--mode", choices=("truecolor", "gray256", "mono"), default="truecolor")
    args = p.parse_args()
    if args.width < 1 or args.height < 2 or args.height % 2 or args.frames < 1:
        p.error("Invalid frame dimensions/count")
    source = list(frames(args.width, args.height, args.frames))
    full = measure(source, args.width, args.height, args.mode, True)
    diff = measure(source, args.width, args.height, args.mode, False)
    print(f"{args.mode}: {args.width}x{args.height} / {args.frames} frames")
    print(f"full: {full[0]:,} bytes / {full[1]:.1f} ms CPU")
    print(f"diff: {diff[0]:,} bytes / {diff[1]:.1f} ms CPU")
    print(f"output reduction: {100 * (1 - diff[0] / full[0]):.1f}%")
    print("Synthetic output generation only; real terminal FPS not measured.")


if __name__ == "__main__":
    main()
