# badapplecli 🍎

Play **Bad Apple!!** in your terminal as smooth, anti-aliased grayscale half-block animation, with music when `ffplay` is available.

## Requirements

- Python **3.9+** (no pip packages)
- **FFmpeg** available on `PATH` (`ffmpeg` required; `ffplay` optional for audio)
- A terminal supporting UTF-8 and **24-bit truecolor** ANSI escapes (Windows Terminal, iTerm2, kitty, Alacritty, GNOME Terminal, and most modern terminals; legacy `cmd.exe` may not work)
- Internet access for the first run, or provide a local video with `--video`

## Run

```bash
git clone https://github.com/jihoo12/badapplecli.git
cd badapplecli
python badapple.py
```

On macOS/Linux, `python3 badapple.py` may be needed. The first run downloads the original 3:39 Bad Apple!! shadow-art PV from an Internet Archive mirror into your user cache. Later runs reuse it. The source video/audio are **not** committed to this repository. If the mirror is unavailable, supply your own compatible MP4 using `--video`.

Install FFmpeg if needed: `brew install ffmpeg` (macOS), `sudo apt install ffmpeg` (Debian/Ubuntu), or download it from [ffmpeg.org](https://ffmpeg.org/download.html) on Windows and add the executable directory to `PATH`.

## Controls & options

Press **q**, **Esc**, or **Ctrl+C** to stop.

```bash
python badapple.py --no-audio                 # Silent video
python badapple.py --fps 15 --width 100       # 15 FPS, max 100 columns
python badapple.py --invert                   # Reverse black/white
python badapple.py --video ./bad_apple.mp4    # Use an existing file
python badapple.py --seek 60 --loop           # Start at 1:00 and repeat
python badapple.py --download-only            # Cache the PV without playing
python badapple.py --help                     # All options
```

The picture automatically fits the terminal size **at playback start**. The player packs two vertical video pixels into each character using the upper half block (`▀`): the top pixel is drawn as the foreground color and the bottom pixel as the background color, both in 24-bit grayscale. The grayscale values produced when FFmpeg downscales the video are preserved, so edges look smooth instead of jagged. It keeps approximately real-time playback by dropping overdue frames, and restores the terminal screen and cursor on exit. Audio is launched by `ffplay` and synchronized on a best-effort basis; exact A/V sync depends on system startup latency. For best results, use a reasonably large terminal with a monospace font.

## Tips

- **Choppy playback?** Truecolor output sends more data than plain black-and-white. Lower the frame rate (`--fps 15`) or limit the size (`--width 80`).
- **Sharper picture?** Reduce the terminal font size; more columns and rows mean higher resolution.
- **Colors look wrong or garbled?** Your terminal probably lacks truecolor support. Try a modern terminal such as Windows Terminal.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Credits and media rights

Based on the *Bad Apple!!* shadow-art PV originally published on Niconico (`sm8628149`, 2009). Music: ZUN / Alstroemeria Records (arrangement), vocals by nomico; shadow-art PV by あにら (Anira). This repository's source-code license **does not grant rights to the video or music**. See [NOTICE.md](NOTICE.md) for details.

## Renderer performance

The default `truecolor` mode preserves smooth grayscale. The renderer tracks
the previous frame and updates only changed terminal-cell runs; densely changed
rows are repainted in full. `--color-mode gray256` reduces ANSI color payload
size; `--color-mode mono --threshold 128` uses four black/white half-block glyphs.
The `--threshold` setting applies to `mono` mode.

Run `python badapple.py --stats --no-audio` to print decoded-frame, output
and render timing after playback. `python bench_renderer.py` compares full
versus differential output on a synthetic moving shape without requiring FFmpeg
or a TTY. This benchmark cannot establish real terminal FPS: emulator repaint,
font rendering, and stdout buffering are system-dependent. To test actual
terminal responsiveness, compare `--color-mode truecolor`, `gray256`,
and `mono` at the same dimensions and FPS.
