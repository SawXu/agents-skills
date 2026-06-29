#!/usr/bin/env python3
"""Trim PUBG highlights to confirmed player knock/elimination moments.

This health-bar pass only trusts the player's bottom-center health bar: a
sustained red bar for knock/down, or the fixed health bar UI disappearing and
not returning for direct elimination. It deliberately does not infer events
from grayscale/death-screen color because that can cut unrelated footage.
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

W, H, FPS = 384, 240, 10
# Scaled bottom-center health bar ROI. PUBG highlight sources are commonly 2304x1440;
# after scaling to 384x240 the fixed player health bar sits in this region.
# Focus on the fill area of the fixed bottom-center health bar. Keep this narrow:
# wider regions can include throwables/weapon wheel overlays and false red pixels.
HEALTH_X0, HEALTH_X1 = 145, 245
HEALTH_Y0, HEALTH_Y1 = 225, 238


def find_tool(name: str, explicit: str | None = None) -> str:
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which(name)
    if found:
        return found
    for root in (Path(r"C:\Program Files\Shutter Encoder\app\Library"), Path(r"C:\Program Files\Shutter Encoder\Library")):
        candidate = root / name
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"Could not find {name}; install ffmpeg/ffprobe or pass --{name[:-4]}")


def duration(path: Path, ffprobe: str) -> float:
    out = subprocess.check_output(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        text=True,
        stderr=subprocess.PIPE,
    ).strip()
    return float(out)


def iter_source_files(folder: Path, include_view_replays: bool) -> list[Path]:
    files: list[Path] = []
    for path in sorted(folder.glob("*.mp4")):
        if include_view_replays:
            if ("淘汰" in path.name or "击倒" in path.name) and re.search(r"\.DVR(?:_\d+)?\.mp4$", path.name):
                files.append(path)
        elif re.search(r"\.(?:被击倒|淘汰)\.DVR(?:_\d+)?\.mp4$", path.name):
            files.append(path)
    return files


def health_state(buf: bytes) -> tuple[str, float]:
    red = red_soft = white = yellow = blue = bright = dark = total = 0
    for y in range(HEALTH_Y0, HEALTH_Y1):
        base = y * W * 3
        for x in range(HEALTH_X0, HEALTH_X1):
            off = base + x * 3
            r, g, b = buf[off], buf[off + 1], buf[off + 2]
            mx, mn = max(r, g, b), min(r, g, b)
            if r > 145 and g < 95 and b < 95:
                red += 1
            if r > 95 and r > g + 18 and r > b + 18 and g < 140 and b < 140:
                red_soft += 1
            if r > 185 and g > 185 and b > 185 and mx - mn < 45:
                white += 1
            if r > 165 and g > 125 and b < 145 and r >= g:
                yellow += 1
            if b > 130 and g > 80 and r < 130:
                blue += 1
            if mx > 160 and mx - mn < 95:
                bright += 1
            if mx < 80:
                dark += 1
            total += 1
    red_ratio = red / total
    red_soft_ratio = red_soft / total
    white_ratio = white / total
    yellow_ratio = yellow / total
    blue_ratio = blue / total
    bright_ratio = bright / total
    dark_ratio = dark / total
    # Real downed/eliminated bar is a sustained, broad red bar. Short damage flashes
    # or blue-zone overlay can tint the ROI red, so keep this threshold conservative.
    if red_ratio > 0.075 and yellow_ratio < 0.02 and bright_ratio < 0.05:
        return "red", max(red_ratio, red_soft_ratio)
    # Gray/death overlays desaturate an already-downed red bar. Use this only
    # to reject clips/crops that already start downed, never as an event trigger.
    if red_soft_ratio > 0.055 and yellow_ratio < 0.02 and bright_ratio < 0.05 and dark_ratio > 0.85:
        return "muted-red-downed", red_soft_ratio
    # Alive health can be white, pale yellow, blue-zone tinted, or transparent.
    if white_ratio > 0.018 or yellow_ratio > 0.018 or blue_ratio > 0.018 or bright_ratio > 0.045:
        return "present", max(red_ratio, red_soft_ratio)
    return "absent", max(red_ratio, red_soft_ratio)


def already_downed_window(states: list[tuple[float, str, float]], start: float, end: float) -> bool:
    window = [(state, score) for t, state, score in states if start <= t < end]
    if len(window) < 8:
        return False
    downed_states = {"red", "muted-red-downed"}
    if sum(1 for state, _ in window if state in downed_states) / len(window) > 0.65:
        return True

    scores = [score for _, score in window]
    first = sum(scores[: max(1, len(scores) // 3)]) / max(1, len(scores) // 3)
    last = sum(scores[-max(1, len(scores) // 3) :]) / max(1, len(scores) // 3)
    high_red = sum(1 for score in scores if score > 0.18) / len(scores)
    return high_red > 0.45 and first > last + 0.05


def detect_event(path: Path, ffmpeg: str, ffprobe: str) -> tuple[float, float | None, str]:
    dur = duration(path, ffprobe)
    proc = subprocess.Popen(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-i", str(path), "-vf", f"fps={FPS},scale={W}:{H}", "-pix_fmt", "rgb24", "-f", "rawvideo", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    frame_size = W * H * 3
    idx = 0
    states: list[tuple[float, str, float]] = []
    try:
        while True:
            buf = proc.stdout.read(frame_size) if proc.stdout else b""
            if len(buf) < frame_size:
                break
            t = idx / FPS
            idx += 1
            if t >= 2:
                state, red_score = health_state(buf)
                states.append((t, state, red_score))
    finally:
        try:
            proc.kill()
        except Exception:
            pass

    # If the clip opens with the player already downed, it has missed the
    # pre-knock context the montage is meant to keep. Skip instead of trimming.
    if already_downed_window(states, 2.0, 4.0):
        return dur, None, "skipped-starts-already-downed"

    # Knock/down: the fixed bottom-center health bar turns red. Require sustained red frames.
    red_times = [t for t, state, _ in states if state == "red"]
    for t in red_times:
        if sum(1 for u in red_times if t <= u < t + 1.1) >= 9:
            trim_start = max(0.0, t - 5.0)
            if already_downed_window(states, trim_start, trim_start + 2.0):
                return dur, None, "skipped-trim-starts-already-downed"
            return dur, t, "own-knock-or-elim-red-healthbar"

    # Direct death/elimination: the fixed health bar UI disappears after it was
    # previously visible, and never comes back. This uses UI presence only, not
    # grayscale/death-screen color.
    seen_health = False
    for i, (t, state, _) in enumerate(states):
        if state in {"present", "red", "muted-red-downed"}:
            seen_health = True
            continue
        if not seen_health:
            continue
        window = [s for u, s, _ in states[i:] if t <= u < t + 1.5]
        later = [s for _, s, _ in states[i:]]
        if len(window) >= 12 and all(s == "absent" for s in window) and not any(s in {"present", "red", "muted-red-downed"} for s in later):
            trim_start = max(0.0, t - 5.0)
            if already_downed_window(states, trim_start, trim_start + 2.0):
                return dur, None, "skipped-trim-starts-already-downed"
            return dur, t, "direct-elim-healthbar-disappeared"

    return dur, None, "skipped-healthbar-evidence-not-found"


def trim_clip(src: Path, out: Path, start: float, length: float, ffmpeg: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{length:.3f}",
        "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "h264_nvenc", "-preset", "p4", "-rc", "vbr", "-cq", "19", "-b:v", "0",
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
    ]
    try:
        subprocess.run(cmd, check=True)
    except Exception:
        fallback = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{start:.3f}", "-i", str(src), "-t", f"{length:.3f}",
            "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(out),
        ]
        subprocess.run(fallback, check=True)


def concat_clips(clips: list[Path], final: Path, ffmpeg: str) -> None:
    list_path = final.with_suffix(".concat.txt")
    with list_path.open("w", encoding="utf-8") as f:
        for clip in clips:
            f.write("file '" + str(clip).replace("'", "'\\''") + "'\n")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", str(final)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Trim PUBG highlights to the player's own knock/elimination moments.")
    parser.add_argument("folder", type=Path, help="Folder containing PUBG highlight mp4 files")
    parser.add_argument("--output-dir", type=Path, default=None, help="Directory for trimmed clips")
    parser.add_argument("--final", type=Path, default=None, help="Optional merged output mp4")
    parser.add_argument("--seconds-before", type=float, default=5.0)
    parser.add_argument("--seconds-after", type=float, default=1.0, help="Keep this much after event so the knock/elimination is visible")
    parser.add_argument("--include-view-replays", action="store_true", help="Include 淘汰画面/击倒画面 style replay files; off by default")
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--ffprobe", default=None)
    args = parser.parse_args()

    ffmpeg = find_tool("ffmpeg.exe", args.ffmpeg)
    ffprobe = find_tool("ffprobe.exe", args.ffprobe)
    folder = args.folder
    outdir = args.output_dir or (folder / "被击倒或淘汰前5秒_含倒地瞬间")
    final = args.final or (folder / "淘汰_被击倒或淘汰前5秒_含倒地瞬间_合成.mp4")

    files = iter_source_files(folder, args.include_view_replays)
    if not files:
        raise SystemExit("No matching source files found")
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("*.mp4"):
        old.unlink()

    rows = []
    clips = []
    for i, src in enumerate(files, 1):
        dur, event, method = detect_event(src, ffmpeg, ffprobe)
        out = outdir / f"{i:03d}_{src.name}"
        if event is None:
            print(f"[{i:02d}/{len(files)}] SKIP {method} | {src.name}", flush=True)
            rows.append({"Index": i, "Name": src.name, "DurationSec": f"{dur:.3f}", "EventSec": "", "KeepStartSec": "", "KeepEndSec": "", "KeepDurationSec": "", "Method": method, "Output": ""})
            continue
        start = max(0.0, event - args.seconds_before)
        keep = min(dur - start, (event - start) + args.seconds_after)
        print(f"[{i:02d}/{len(files)}] {method} {start:.2f}-{start + keep:.2f} | {src.name}", flush=True)
        trim_clip(src, out, start, keep, ffmpeg)
        clips.append(out)
        rows.append({"Index": i, "Name": src.name, "DurationSec": f"{dur:.3f}", "EventSec": f"{event:.3f}", "KeepStartSec": f"{start:.3f}", "KeepEndSec": f"{start + keep:.3f}", "KeepDurationSec": f"{keep:.3f}", "Method": method, "Output": str(out)})

    csv_path = outdir / "检测与裁剪记录.csv"
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    if not clips:
        raise SystemExit("No confident clips were produced; inspect the CSV or run the PaddleOCR text trimmer for self-event text")
    concat_clips(clips, final, ffmpeg)
    final_dur = duration(final, ffprobe)
    methods = dict(Counter(row["Method"] for row in rows))
    print("SUMMARY")
    print(f"clips={len(clips)}")
    print(f"final={final}")
    print(f"duration_sec={final_dur:.2f}")
    print(f"csv={csv_path}")
    print(f"methods={methods}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
