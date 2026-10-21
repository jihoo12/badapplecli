"""Efficient half-block terminal renderer for decoded 8-bit grayscale frames.

The renderer keeps the last *displayed* frame and repaints only changed cell
runs. Rows with widespread changes are redrawn in full to avoid many cursor
moves. No third-party packages are required.
"""

from __future__ import annotations

from dataclasses import dataclass


_HALF = "▀".encode("utf-8")
_MONO = tuple(char.encode("utf-8") for char in (" ", "▄", "▀", "█"))


@dataclass(frozen=True)
class RenderStats:
    bytes_written: int = 0
    changed_cells: int = 0
    painted_cells: int = 0
    full_rows: int = 0


class FrameRenderer:
    """Render raw gray8 frames as ANSI updates. ``height`` must be even."""

    def __init__(
        self, width: int, height: int, *, mode: str = "truecolor",
        threshold: int = 128, invert: bool = False,
    ) -> None:
        if width <= 0 or height <= 0 or height % 2:
            raise ValueError("Width must be positive and pixel height must be positive and even")
        if mode not in ("truecolor", "gray256", "mono"):
            raise ValueError(f"Unsupported color mode: {mode}")
        if not 0 <= threshold <= 255:
            raise ValueError("threshold must be between 0 and 255")

        self.width = width
        self.height = height
        self.mode = mode
        self._previous: bytes | None = None
        self._color_codes: dict[int, bytes] = {}
        self.stats = RenderStats()
        if mode == "mono":
            self._lookup = bytes(
                int((255 - i if invert else i) >= threshold) for i in range(256)
            )
        elif mode == "gray256":
            def palette(i: int) -> int:
                value = 255 - i if invert else i
                if value < 5:
                    return 16  # black
                if value >= 250:
                    return 231  # white
                return max(232, min(255, 232 + round((value - 8) / 10)))
            self._lookup = bytes(palette(i) for i in range(256))
        else:
            self._lookup = bytes(255 - i if invert else i for i in range(256))

    def _style(self, upper: int, lower: int) -> bytes:
        key = (upper << 8) | lower
        cached = self._color_codes.get(key)
        if cached is None:
            if self.mode == "truecolor":
                cached = (
                    f"\x1b[38;2;{upper};{upper};{upper};"
                    f"48;2;{lower};{lower};{lower}m"
                ).encode("ascii")
            else:
                cached = f"\x1b[38;5;{upper};48;5;{lower}m".encode("ascii")
            self._color_codes[key] = cached
        return cached

    def _run(self, frame: bytes, row: int, start: int, end: int) -> bytes:
        """A self-contained cursor-positioned run with explicit initial color."""
        width = self.width
        upper_offset = 2 * row * width
        lower_offset = upper_offset + width
        output = bytearray(f"\x1b[{row + 1};{start + 1}H".encode("ascii"))
        if self.mode == "mono":
            for x in range(start, end):
                output.extend(_MONO[(frame[upper_offset + x] << 1) | frame[lower_offset + x]])
        else:
            previous_pair = -1
            for x in range(start, end):
                upper = frame[upper_offset + x]
                lower = frame[lower_offset + x]
                pair = (upper << 8) | lower
                if pair != previous_pair:
                    output.extend(self._style(upper, lower))
                    previous_pair = pair
                output.extend(_HALF)
        return bytes(output)

    def render(self, gray8_frame: bytes) -> bytes:
        """Return bytes for a complete initial frame or a subsequent partial update.

        Callers must write the entire result to the terminal in order, or call
        ``reset()`` if the terminal state is lost or its content is cleared.
        """
        if len(gray8_frame) != self.width * self.height:
            raise ValueError("Frame byte count does not match dimensions")

        current = gray8_frame.translate(self._lookup)
        previous = self._previous
        width = self.width
        output = bytearray()
        changed_cells = painted_cells = full_rows = 0

        for row in range(self.height // 2):
            top = 2 * row * width
            bottom = top + width
            if previous is None:
                output.extend(self._run(current, row, 0, width))
                changed_cells += width
                painted_cells += width
                full_rows += 1
                continue

            # A fast byte comparison skips entirely unchanged rows.
            if (current[top:top + width] == previous[top:top + width]
                    and current[bottom:bottom + width] == previous[bottom:bottom + width]):
                continue

            runs: list[tuple[int, int]] = []
            start = -1
            last_changed = -1
            for x in range(width):
                if (current[top + x] != previous[top + x]
                        or current[bottom + x] != previous[bottom + x]):
                    changed_cells += 1
                    if start < 0:
                        start = x
                    last_changed = x
                elif start >= 0 and x - last_changed > 2:
                    runs.append((start, last_changed + 1))
                    start = -1
            if start >= 0:
                runs.append((start, last_changed + 1))

            dirty_width = sum(end - start for start, end in runs)
            # Heuristic: prefer one full-row write over many cursor movements.
            if dirty_width * 2 >= width or len(runs) > max(3, width // 8):
                output.extend(self._run(current, row, 0, width))
                full_rows += 1
                painted_cells += width
            else:
                for start, end in runs:
                    output.extend(self._run(current, row, start, end))
                    painted_cells += end - start

        self._previous = current
        self.stats = RenderStats(len(output), changed_cells, painted_cells, full_rows)
        return bytes(output)

    def reset(self) -> None:
        """Force the next call to repaint the whole image."""
        self._previous = None
        self.stats = RenderStats()
