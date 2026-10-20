# badapplecli 🍎

Play **Bad Apple!!** in your terminal as crisp black-and-white half-block animation, with music when `ffplay` is available. Python only; no C# or Java.

## Requirements

- Python **3.9+** (no pip packages)
- **FFmpeg** available on `PATH` (`ffmpeg` required; `ffplay` optional for audio)
- A terminal supporting UTF-8 and ANSI escapes (Windows Terminal, macOS Terminal, most Linux terminals)
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
python badapple.py --fps 30 --width 100       # 30 FPS, max 100 columns
python badapple.py --invert                   # Reverse black/white
python badapple.py --video ./bad_apple.mp4    # Use an existing file
python badapple.py --seek 60 --loop           # Start at 1:00 and repeat
python badapple.py --download-only            # Cache the PV without playing
python badapple.py --help                     # All options
```

The picture automatically fits the terminal size **at playback start**. The player uses two vertical video pixels per character (`▀▄█`), keeps approximately real-time playback by dropping overdue frames, and restores the terminal screen and cursor on exit. Audio is launched by `ffplay` and synchronized on a best-effort basis; exact A/V sync depends on system startup latency. For best results, use a reasonably large terminal with a monospace font.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Credits and media rights

Based on the *Bad Apple!!* shadow-art PV originally published on Niconico (`sm8628149`, 2009). Music: ZUN / Alstroemeria Records (arrangement), vocals by nomico; shadow-art PV by あにら (Anira). This repository's source-code license **does not grant rights to the video or music**. See [NOTICE.md](NOTICE.md) for details.
