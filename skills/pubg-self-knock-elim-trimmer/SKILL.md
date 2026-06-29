---
name: pubg-self-knock-elim-trimmer
description: Organize and trim PUBG/NVIDIA Highlight mp4 clips that show the player themselves being knocked down or eliminated into concise self-death montage clips. Use when Codex needs to process PUBG highlight folders, move or select files named 淘汰, exclude opponent replay files such as 淘汰画面 or 击倒画面, detect the player's knocked/direct-eliminated moment, keep the seconds before the event plus a short visible aftermath, and merge the result in chronological order with ffmpeg.
---

# PUBG Self Knock/Elimination Trimmer

Use this skill to turn PUBG highlight folders into concise clips of the player themselves being knocked down or eliminated.

## Core Rules

- Treat `.淘汰.DVR.mp4` as the player's own elimination/knock highlight.
- Exclude `淘汰画面`, `击倒画面`, `单次淘汰`, `双次淘汰`, and other `xx淘汰` files unless the user explicitly asks for them; `淘汰画面/击倒画面` are usually the killer/opponent replay perspective.
- Sort source clips by filename; NVIDIA highlight names include timestamps, so lexical sort preserves time order.
- For the final usable montage, keep the player's event context: default to 5 seconds before the player's knock/direct elimination plus 1 second after the event so the knock/elimination is visible.
- Do not use only the gray death screen if a red knocked/eliminated health bar is present earlier; gray screen can be several seconds too late.
- If the clip starts with the player's character already downed, skip it; the clip has already missed the "before knock" context. Also skip a direct-elimination crop if the proposed crop start is already red/downed.

## Preferred Script

Use `scripts/pubg_highlight_trimmer.py` for repeatable processing:

```powershell
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_highlight_trimmer.py "C:\path\to\PLAYERUNKNOWN'S BATTLEGROUNDS"
```

Useful options:

```powershell
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_highlight_trimmer.py "C:\path\to\folder" --seconds-before 5 --seconds-after 1
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_highlight_trimmer.py "C:\path\to\folder" --output-dir "C:\path\to\clips" --final "C:\path\to\final.mp4"
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_highlight_trimmer.py "C:\path\to\folder" --ffmpeg "C:\Program Files\Shutter Encoder\app\Library\ffmpeg.exe" --ffprobe "C:\Program Files\Shutter Encoder\app\Library\ffprobe.exe"
```

The script finds `ffmpeg.exe`/`ffprobe.exe` from PATH or common Shutter Encoder locations.

## PaddleOCR Text Script

Use `scripts/pubg_paddleocr_text_trimmer.py` when the desired cut point is the lower-screen kill text such as `xxx击倒了你` / `xxx淘汰了你`:

```powershell
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_paddleocr_text_trimmer.py "C:\path\to\淘汰" --seconds-before 4 --seconds-after 1
```

Useful options:

```powershell
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_paddleocr_text_trimmer.py "C:\path\to\淘汰" --candidate-csv "C:\path\to\检测记录.csv"
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_paddleocr_text_trimmer.py "C:\path\to\淘汰" --dry-run
python skills/pubg-self-knock-elim-trimmer/scripts/pubg_paddleocr_text_trimmer.py "C:\path\to\淘汰" --priority-window 28:36 --priority-window 44:52
```

The PaddleOCR script:

- Requires Python with `paddlepaddle==3.2.2`, `paddleocr==3.7.0`, and `opencv-contrib-python`.
- Uses PaddleOCR only as final truth for `击倒了你` / `淘汰了你`; candidate CSV files are only scan hints.
- Continues scanning if it sees non-self text like `你用...击倒了xxx`, so later true self-knock events are not skipped.
- Scans common PUBG highlight windows first (`28:36`, `44:52`) and then falls back to a full scan unless `--no-full-scan` is passed.
- Writes a CSV and `summary.json` with included/skipped clips, OCR text, event seconds, keep ranges, and output paths.

## Detection Heuristic

The script samples each video at 10 fps and scales to 384x240 for speed.

1. Detect the player's own bottom-center red knocked/eliminated health bar. This is preferred because it corresponds to the player's knock/direct elimination.
2. Do not inspect the left team list for red bars; teammates create false positives.
3. If the player is already downed at the source start or at the proposed crop start, skip the clip instead of keeping post-knock footage.
4. If no player red health bar is found, detect the fixed health bar UI disappearing and not returning for direct elimination/wipe cases.
5. If the event happens before 5 seconds into the source clip, keep only from the start through the event plus the aftermath; do not include unrelated post-event footage just to force a 5-second clip.

## Manual QA and Corrections

- If the user says a specific clip is wrong, inspect the original around the claimed event time with ffmpeg frame extraction and compare it with the trimmed clip's end frame.
- If a clip stops just before the visible knock/elimination, extend `--seconds-after` or recut that row from `检测与裁剪记录.csv`.
- If a clip starts too late, manually override `EventSec` in the record or recut from the original with `event - 5` as the start.
- Keep a CSV record with `EventSec`, `KeepStartSec`, `KeepEndSec`, detection method, and output path.

## File Organization Pattern

When asked to move 淘汰 videos first:

- Create a sibling/subfolder named `淘汰`.
- Move only exact `.淘汰.DVR.mp4` and, if requested, `.淘汰画面.DVR.mp4` files.
- If the user says not to include `xx淘汰`, move `单次淘汰`, `双次淘汰`, etc. back out of the folder.

## Validation

After processing, report:

- Number of source clips included and replay files excluded.
- Final merged output path.
- Single-clip output directory.
- CSV detection record path.
- Final duration and approximate size.
- Counts by detection method, especially `own-knock-or-elim-red-healthbar` vs `direct-elim-grayscale`.


