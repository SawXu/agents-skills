#!/usr/bin/env python3
"""Trim PUBG self knock/elimination highlights using lower-screen OCR text.

This script looks for text like "xxx击倒了你" / "xxx淘汰了你", then keeps the
seconds before and after that first self-event. It deliberately continues
scanning after non-self messages such as "你用...击倒了xxx".
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

try:
    import cv2
    from paddleocr import PaddleOCR
except Exception as exc:  # pragma: no cover - useful when run from wrong Python.
    raise SystemExit(
        "Missing OCR dependencies. Run this with a Python 3.13 environment that has:\n"
        "  python -m pip install paddlepaddle==3.2.2 paddleocr==3.7.0\n"
        f"Import error: {exc}"
    ) from exc


SELF_STRICT_RE = re.compile(r"(击倒了你|淘汰了你)")
SELF_ZONE_DOWNED_RE = re.compile(r"(你在安全区外倒地了|安全区外倒地了|安全区外倒地)")
SELF_FUZZY_RE = re.compile(r"(击倒.{0,2}你|淘.{0,2}了?你|倒了你)")

# Scaled fixed player-health-bar ROI. This mirrors pubg_highlight_trimmer.py and
# is used only to reject clips that already start in the downed red-bar state.
HEALTH_W, HEALTH_H = 384, 240
HEALTH_X0, HEALTH_X1 = 145, 245
HEALTH_Y0, HEALTH_Y1 = 225, 238


@dataclass
class OcrResult:
    text: str
    scores: str
    seconds: float
    method: str


@dataclass
class EventResult:
    event_sec: float | None
    method: str
    text: str
    scores: str
    ocr_seconds: float
    sampled_count: int


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def classify_self_text(text: str) -> str | None:
    text = normalize_text(text)
    if SELF_STRICT_RE.search(text):
        return "paddle-strict-self-text"
    if SELF_ZONE_DOWNED_RE.search(text):
        return "paddle-zone-self-downed-text"
    if SELF_FUZZY_RE.search(text):
        return "paddle-fuzzy-self-text"
    return None


def parse_roi(value: str) -> tuple[float, float, float, float]:
    parts = [float(p.strip()) for p in value.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("ROI must be x1,y1,x2,y2")
    x1, y1, x2, y2 = parts
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise argparse.ArgumentTypeError("ROI values must be ratios in ascending order, between 0 and 1")
    return x1, y1, x2, y2


def parse_window(value: str) -> tuple[float, float]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("Window must be start:end seconds")
    start, end = (float(p.strip()) for p in value.split(":", 1))
    if start < 0 or end <= start:
        raise argparse.ArgumentTypeError("Window must satisfy 0 <= start < end")
    return start, end


def find_tool(name: str, explicit: str | None = None) -> str:
    if explicit and Path(explicit).exists():
        return explicit
    found = shutil.which(name)
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files\Shutter Encoder\app\Library") / name,
        Path(r"C:\Program Files\Shutter Encoder\Library") / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"Could not find {name}; pass --{name[:-4]}")


def run_stdout(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.PIPE).strip()


def duration_sec(path: Path, ffprobe: str) -> float:
    return float(
        run_stdout(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=nw=1:nk=1",
                str(path),
            ]
        )
    )


def health_state(buf: bytes) -> str:
    red = red_soft = white = yellow = blue = bright = total = 0
    for y in range(HEALTH_Y0, HEALTH_Y1):
        base = y * HEALTH_W * 3
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
            total += 1
    red_ratio = red / total
    red_soft_ratio = red_soft / total
    white_ratio = white / total
    yellow_ratio = yellow / total
    blue_ratio = blue / total
    bright_ratio = bright / total
    # Strong red catches normal downed bars. The muted-red branch catches
    # low-saturation starts where the red bar itself is still visible.
    if red_ratio > 0.075 or (red_soft_ratio > 0.055 and yellow_ratio < 0.02 and bright_ratio < 0.05):
        return "red"
    if white_ratio > 0.018 or yellow_ratio > 0.018 or blue_ratio > 0.018 or bright_ratio > 0.045:
        return "present"
    return "absent"


def opening_already_downed(
    path: Path,
    ffmpeg: str,
    check_start: float,
    check_end: float,
    fps: float,
    red_threshold: float,
) -> tuple[bool, float, int]:
    proc = subprocess.Popen(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-t",
            f"{check_end:.3f}",
            "-vf",
            f"fps={fps},scale={HEALTH_W}:{HEALTH_H}",
            "-pix_fmt",
            "rgb24",
            "-f",
            "rawvideo",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    frame_size = HEALTH_W * HEALTH_H * 3
    idx = 0
    states: list[str] = []
    try:
        while True:
            buf = proc.stdout.read(frame_size) if proc.stdout else b""
            if len(buf) < frame_size:
                break
            t = idx / fps
            idx += 1
            if check_start <= t < check_end:
                states.append(health_state(buf))
    finally:
        try:
            proc.kill()
        except Exception:
            pass

    if not states:
        return False, 0.0, 0
    red_ratio = sum(1 for state in states if state == "red") / len(states)
    return red_ratio >= red_threshold, red_ratio, len(states)


def iter_source_files(folder: Path, include_view_replays: bool) -> list[Path]:
    files: list[Path] = []
    for path in sorted(folder.glob("*.mp4")):
        name = path.name
        if include_view_replays:
            if ("淘汰" in name or "击倒" in name) and re.search(r"\.DVR(?:_\d+)?\.mp4$", name):
                files.append(path)
        elif re.search(r"\.(?:被击倒|淘汰)\.DVR(?:_\d+)?\.mp4$", name):
            files.append(path)
    return files


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique path for {path}")


def unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(1, 1000):
        candidate = path.with_name(f"{path.name}_{i}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create unique directory for {path}")


def time_range(start: float, end: float, step: float) -> list[float]:
    out: list[float] = []
    t = start
    while t <= end + 1e-6:
        out.append(round(t, 3))
        t += step
    return out


def read_candidate_csv(path: Path | None) -> dict[str, list[float]]:
    if not path or not path.exists():
        return {}
    out: dict[str, list[float]] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            name = row.get("Name", "")
            value = row.get("OcrEventSec") or row.get("EventSec") or ""
            if not name or not value:
                continue
            try:
                out.setdefault(name, []).append(float(value))
            except ValueError:
                pass
    return out


def build_scan_times(
    duration: float,
    candidate_times: list[float],
    priority_windows: list[tuple[float, float]],
    scan_start: float,
    scan_end: float | None,
    coarse_step: float,
    full_scan: bool,
) -> list[float]:
    times: list[float] = []
    end = min(duration, scan_end if scan_end is not None else duration)

    for candidate in candidate_times:
        lo = max(scan_start, candidate - 1.0)
        hi = min(end, candidate + 1.0)
        times.extend(time_range(lo, hi, min(0.5, coarse_step)))

    for start, stop in priority_windows:
        lo = max(scan_start, start)
        hi = min(end, stop)
        if hi >= lo:
            times.extend(time_range(lo, hi, coarse_step))

    if full_scan:
        times.extend(time_range(scan_start, end, coarse_step))

    # Keep order while de-duplicating close duplicate timestamps.
    seen: set[int] = set()
    ordered: list[float] = []
    for t in times:
        key = int(round(t * 1000))
        if key in seen:
            continue
        seen.add(key)
        ordered.append(t)
    return ordered


def build_text_priority_scan_times(
    duration: float,
    candidate_times: list[float],
    priority_windows: list[tuple[float, float]],
    scan_start: float,
    scan_end: float | None,
    coarse_step: float,
    full_scan: bool,
    lookback: float,
    lookahead: float,
    step: float,
) -> list[float]:
    """Scan self-event text first; health-bar/candidate times only add scan windows."""
    end_limit = min(duration, scan_end if scan_end is not None else duration)
    times: set[int] = set()

    if full_scan:
        times.update(int(round(t * 1000)) for t in time_range(scan_start, end_limit, coarse_step))

    for start, stop in priority_windows:
        lo = max(scan_start, 0.0, start)
        hi = min(end_limit, stop)
        if hi >= lo:
            times.update(int(round(t * 1000)) for t in time_range(lo, hi, step))

    for candidate in candidate_times:
        lo = max(scan_start, 0.0, candidate - lookback)
        hi = min(end_limit, candidate + lookahead)
        if hi >= lo:
            times.update(int(round(t * 1000)) for t in time_range(lo, hi, step))

    return [key / 1000 for key in sorted(times)]


def ocr_at(
    cap: cv2.VideoCapture,
    ocr: PaddleOCR,
    sec: float,
    roi: tuple[float, float, float, float],
    ocr_width: int,
) -> OcrResult:
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, sec) * 1000)
    ok, frame = cap.read()
    if not ok or frame is None:
        return OcrResult("", "", 0.0, "frame-read-failed")

    h, w = frame.shape[:2]
    x1, y1, x2, y2 = roi
    crop = frame[int(h * y1) : int(h * y2), int(w * x1) : int(w * x2)]
    if ocr_width > 0 and crop.shape[1] > ocr_width:
        scale = ocr_width / crop.shape[1]
        crop = cv2.resize(crop, (ocr_width, max(1, int(crop.shape[0] * scale))), interpolation=cv2.INTER_AREA)

    started = time.time()
    raw = ocr.predict(crop)
    elapsed = time.time() - started

    texts: list[str] = []
    scores: list[str] = []
    for item in raw:
        data = item.json.get("res", {}) if hasattr(item, "json") else item
        texts.extend(data.get("rec_texts", []) or [])
        for score in data.get("rec_scores", []) or []:
            try:
                scores.append(f"{float(score):.3f}")
            except Exception:
                scores.append(str(score))
    text = normalize_text("".join(texts))
    method = classify_self_text(text) or "paddle-not-self-text"
    return OcrResult(text, ";".join(scores), elapsed, method)


def refine_event(
    cap: cv2.VideoCapture,
    ocr: PaddleOCR,
    coarse_sec: float,
    duration: float,
    roi: tuple[float, float, float, float],
    ocr_width: int,
    refine_before: float,
    refine_after: float,
    refine_step: float,
) -> tuple[float, OcrResult, int]:
    lo = max(0.0, coarse_sec - refine_before)
    hi = min(duration, coarse_sec + refine_after)
    sampled = 0
    best: tuple[float, OcrResult] | None = None

    rough_step = max(refine_step, 0.5)
    rough_hit: tuple[float, OcrResult] | None = None
    for t in time_range(lo, hi, rough_step):
        sampled += 1
        result = ocr_at(cap, ocr, t, roi, ocr_width)
        if classify_self_text(result.text):
            rough_hit = (t, result)
            break
        if result.text and best is None:
            best = (t, result)
    if rough_hit:
        fine_lo = max(lo, rough_hit[0] - rough_step)
        fine_hi = min(hi, rough_hit[0] + refine_step)
        for t in time_range(fine_lo, fine_hi, refine_step):
            sampled += 1
            result = ocr_at(cap, ocr, t, roi, ocr_width)
            if classify_self_text(result.text):
                return t, result, sampled
            if result.text and best is None:
                best = (t, result)
        return rough_hit[0], rough_hit[1], sampled
    if best:
        return best[0], best[1], sampled
    return coarse_sec, OcrResult("", "", 0.0, "paddle-refine-missed"), sampled


def detect_event(
    path: Path,
    ocr: PaddleOCR,
    duration: float,
    candidate_times: list[float],
    args: argparse.Namespace,
) -> EventResult:
    cap = cv2.VideoCapture(str(path))
    sampled_count = 0
    total_ocr_seconds = 0.0
    last_text = ""
    last_scores = ""
    last_method = "not-scanned"
    try:
        # Text evidence is the top priority. "击倒了你"/"淘汰了你"/"你在安全区外倒地了"
        # stays on screen for several seconds, so coarse-scan text first and
        # then refine backward to the first frame where the text appears.
        for sec in build_text_priority_scan_times(
            duration,
            candidate_times,
            args.priority_window,
            args.scan_start,
            args.scan_end,
            args.coarse_step,
            not args.no_full_scan,
            args.candidate_lookback,
            args.candidate_lookahead,
            args.candidate_step,
        ):
            sampled_count += 1
            result = ocr_at(cap, ocr, sec, args.roi, args.ocr_width)
            total_ocr_seconds += result.seconds
            if result.text:
                last_text, last_scores, last_method = result.text, result.scores, result.method
            if classify_self_text(result.text):
                event_sec, refined, refined_count = refine_event(
                    cap,
                    ocr,
                    sec,
                    duration,
                    args.roi,
                    args.ocr_width,
                    args.refine_before,
                    args.refine_after,
                    args.refine_step,
                )
                sampled_count += refined_count
                total_ocr_seconds += refined.seconds
                method = classify_self_text(refined.text) or result.method
                return EventResult(event_sec, method, refined.text or result.text, refined.scores or result.scores, total_ocr_seconds, sampled_count)
    finally:
        cap.release()

    return EventResult(None, last_method if last_method != "not-scanned" else "paddle-no-self-text-found", last_text, last_scores, total_ocr_seconds, sampled_count)


def trim_clip(src: Path, out: Path, start: float, length: float, ffmpeg: str) -> str:
    out.parent.mkdir(parents=True, exist_ok=True)
    nvenc_cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(src),
        "-t",
        f"{length:.3f}",
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p4",
        "-rc",
        "vbr",
        "-cq",
        "22",
        "-b:v",
        "0",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(out),
    ]
    try:
        subprocess.run(nvenc_cmd, check=True)
        return "h264_nvenc"
    except Exception:
        fallback = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(src),
            "-t",
            f"{length:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out),
        ]
        subprocess.run(fallback, check=True)
        return "libx264"


def concat_clips(clips: list[Path], final: Path, ffmpeg: str) -> Path:
    list_path = final.with_suffix(".concat.txt")
    with list_path.open("w", encoding="utf-8") as f:
        for clip in clips:
            escaped = str(clip).replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", "-movflags", "+faststart", str(final)],
        check=True,
    )
    return list_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Trim PUBG self knock/elimination clips using PaddleOCR lower-screen text.")
    parser.add_argument("folder", type=Path, help="Folder containing PUBG highlight mp4 files")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--final", type=Path, default=None)
    parser.add_argument("--seconds-before", type=float, default=5.0)
    parser.add_argument("--seconds-after", type=float, default=1.0)
    parser.add_argument("--include-view-replays", action="store_true")
    parser.add_argument("--candidate-csv", type=Path, default=None, help="Optional prior OCR/healthbar CSV; only used as scan hints, not as final truth")
    parser.add_argument("--priority-window", type=parse_window, action="append", default=[(28.0, 42.0), (44.0, 52.0)], help="Scan this window first; repeatable, default 28:42 and 44:52")
    parser.add_argument("--scan-start", type=float, default=0.0)
    parser.add_argument("--scan-end", type=float, default=None)
    parser.add_argument("--coarse-step", type=float, default=3.0)
    parser.add_argument("--candidate-lookback", type=float, default=8.0, help="Scan this many seconds before candidate CSV hints to find the first persistent self text")
    parser.add_argument("--candidate-lookahead", type=float, default=0.5, help="Scan this many seconds after candidate CSV hints")
    parser.add_argument("--candidate-step", type=float, default=3.0, help="OCR step for candidate hint windows")
    parser.add_argument("--refine-before", type=float, default=6.0)
    parser.add_argument("--refine-after", type=float, default=0.4)
    parser.add_argument("--refine-step", type=float, default=0.1)
    parser.add_argument("--refine-candidates", action="store_true", help="Refine candidate CSV hits with PaddleOCR; slower")
    parser.add_argument("--allow-starts-downed", action="store_true", help="Do not skip clips whose opening already has a red downed health bar")
    parser.add_argument("--opening-check-start", type=float, default=0.5)
    parser.add_argument("--opening-check-end", type=float, default=3.0)
    parser.add_argument("--opening-check-fps", type=float, default=5.0)
    parser.add_argument("--opening-red-threshold", type=float, default=0.65)
    parser.add_argument("--no-full-scan", action="store_true", help="Only scan candidate/priority windows; faster but can miss unusual event times")
    parser.add_argument("--roi", type=parse_roi, default=(0.22, 0.62, 0.78, 0.84), help="OCR crop ratios x1,y1,x2,y2")
    parser.add_argument("--ocr-width", type=int, default=1152, help="Downscale OCR ROI to this width; 0 disables")
    parser.add_argument("--dry-run", action="store_true", help="Detect and write CSV/summary without trimming or merging")
    parser.add_argument("--no-merge", action="store_true", help="Create individual clips but skip final concat")
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--ffprobe", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ffmpeg = find_tool("ffmpeg.exe", args.ffmpeg)
    ffprobe = find_tool("ffprobe.exe", args.ffprobe)

    folder = args.folder
    files = iter_source_files(folder, args.include_view_replays)
    if not files:
        raise SystemExit("No matching .被击倒.DVR*.mp4 or .淘汰.DVR*.mp4 source files found")

    outdir = args.output_dir or folder / "被击倒或淘汰前5秒_PaddleOCR自动"
    final = args.final or folder / "淘汰_被击倒或淘汰前5秒_PaddleOCR自动合成.mp4"
    outdir = unique_dir(outdir)
    final = unique_path(final)
    outdir.mkdir(parents=True, exist_ok=True)

    print(f"sources={len(files)}", flush=True)
    print(f"output_dir={outdir}", flush=True)
    print(f"final={final}", flush=True)
    print("initializing PaddleOCR...", flush=True)
    ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)

    candidates = read_candidate_csv(args.candidate_csv)
    records: list[dict[str, str]] = []
    clips: list[Path] = []
    methods: Counter[str] = Counter()
    encoders: Counter[str] = Counter()

    for idx, src in enumerate(files, 1):
        dur = duration_sec(src, ffprobe)
        opening_red_ratio = 0.0
        opening_samples = 0
        if not args.allow_starts_downed:
            starts_downed, opening_red_ratio, opening_samples = opening_already_downed(
                src,
                ffmpeg,
                args.opening_check_start,
                min(args.opening_check_end, dur),
                args.opening_check_fps,
                args.opening_red_threshold,
            )
            if starts_downed:
                method = "skipped-starts-already-downed"
                methods[method] += 1
                print(
                    f"[{idx:02d}/{len(files)}] SKIP {method} opening_red={opening_red_ratio:.3f} samples={opening_samples} | {src.name}",
                    flush=True,
                )
                records.append(
                    {
                        "Index": str(idx),
                        "Name": src.name,
                        "DurationSec": f"{dur:.3f}",
                        "Status": "skipped",
                        "EventSec": "",
                        "KeepStartSec": "",
                        "KeepEndSec": "",
                        "KeepDurationSec": "",
                        "Method": method,
                        "PaddleText": "",
                        "PaddleScores": "",
                        "OpeningRedRatio": f"{opening_red_ratio:.3f}",
                        "OcrSeconds": "0.000",
                        "SampledFrames": str(opening_samples),
                        "Output": "",
                    }
                )
                continue

        event = detect_event(src, ocr, dur, candidates.get(src.name, []), args)
        event_sec = event.event_sec
        if event_sec is None:
            methods[event.method] += 1
            print(f"[{idx:02d}/{len(files)}] SKIP {event.method} samples={event.sampled_count} | {src.name} | {event.text[:80]}", flush=True)
            records.append(
                {
                    "Index": str(idx),
                    "Name": src.name,
                    "DurationSec": f"{dur:.3f}",
                    "Status": "skipped",
                    "EventSec": "",
                    "KeepStartSec": "",
                    "KeepEndSec": "",
                    "KeepDurationSec": "",
                    "Method": event.method,
                    "PaddleText": event.text,
                    "PaddleScores": event.scores,
                    "OpeningRedRatio": f"{opening_red_ratio:.3f}",
                    "OcrSeconds": f"{event.ocr_seconds:.3f}",
                    "SampledFrames": str(event.sampled_count),
                    "Output": "",
                }
            )
            continue

        start = max(0.0, event_sec - args.seconds_before)
        end = min(dur, event_sec + args.seconds_after)
        keep = max(0.1, end - start)
        output = ""
        encoder = ""
        if not args.dry_run:
            output_path = outdir / f"{len(clips) + 1:03d}_{src.name}"
            encoder = trim_clip(src, output_path, start, keep, ffmpeg)
            encoders[encoder] += 1
            clips.append(output_path)
            output = str(output_path)
        methods[event.method] += 1
        print(
            f"[{idx:02d}/{len(files)}] INCLUDE {event_sec:.3f}s {start:.3f}-{end:.3f} {event.method} samples={event.sampled_count} | {src.name}",
            flush=True,
        )
        records.append(
            {
                "Index": str(idx),
                "Name": src.name,
                "DurationSec": f"{dur:.3f}",
                "Status": "included",
                "EventSec": f"{event_sec:.3f}",
                "KeepStartSec": f"{start:.3f}",
                "KeepEndSec": f"{end:.3f}",
                "KeepDurationSec": f"{keep:.3f}",
                "Method": event.method,
                "PaddleText": event.text,
                "PaddleScores": event.scores,
                "OpeningRedRatio": f"{opening_red_ratio:.3f}",
                "OcrSeconds": f"{event.ocr_seconds:.3f}",
                "SampledFrames": str(event.sampled_count),
                "Output": output,
            }
        )

    csv_path = outdir / "检测与裁剪记录_PaddleOCR自动.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)

    concat_list = None
    final_duration = 0.0
    final_size = 0.0
    if clips and not args.no_merge and not args.dry_run:
        concat_list = concat_clips(clips, final, ffmpeg)
        final_duration = duration_sec(final, ffprobe)
        final_size = final.stat().st_size / 1024 / 1024

    summary = {
        "source_count": len(files),
        "included_count": sum(1 for row in records if row["Status"] == "included"),
        "skipped_count": sum(1 for row in records if row["Status"] == "skipped"),
        "dry_run": args.dry_run,
        "output_dir": str(outdir),
        "final": "" if args.dry_run or args.no_merge else str(final),
        "concat_list": "" if concat_list is None else str(concat_list),
        "csv": str(csv_path),
        "final_duration_sec": round(final_duration, 3),
        "final_size_mb": round(final_size, 1),
        "methods": dict(methods),
        "encoders": dict(encoders),
    }
    summary_path = outdir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUMMARY " + json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
