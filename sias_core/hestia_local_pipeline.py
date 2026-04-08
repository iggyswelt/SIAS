#!/usr/bin/env python3
"""
Hestia Local Pipeline — YouTube Shorts Workflow (Plan B)
Vollständig lokal auf Cronos (192.168.23.80)
Keine externen API-Keys nötig.

Usage:
    python3 hestia_local_pipeline.py --video-id VIDEO_ID --mode once
    python3 hestia_local_pipeline.py --mode daemon --channel UC... --interval 600

Pipeline Steps:
    1. yt-dlp: Download original video
    2. whisper: Transkription mit Timestamps
    3. Ollama: Segment-Scoring (qwen3.5:2b)
    4. ffmpeg: Clip-Schnitt (9:16, 30-90s)
    5. Ollama: Titel + Tags + Description
    6. DB: Ergebnisse speichern + Status-Updates
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path("/home/iggy/shorts_temp")
LOG_FILE = Path("/home/iggy/sias-core/logs/hestia_pipeline.log")
DB_HOST = "192.168.23.170"       # metamaus server (Cronos → metamaus DB)
DB_USER = "scraper"
DB_NAME = "metamaus"
DB_PASSWORD = os.environ.get("PGPASSWORD", "scraper")

OLLAMA_MODEL = "qwen3.5:2b"
OLLAMA_BASE = "http://localhost:11434"
WHISPER_MODEL = "turbo"  # ~3.1 GB VRAM — fits in 4.3 GB free
# Fallback: WHISPER_MODEL = "base"  # ~1.5 GB VRAM

CLIP_MIN_SEC = 30
CLIP_MAX_SEC = 90
CLIP_WIDTH = 1080
CLIP_HEIGHT = 1920
TOP_N_SEGMENTS = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("hestia_pipeline")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
import psycopg2

def db_execute(sql: str, fetch: bool = False):
    """Run a single SQL statement via psycopg2. Returns rows if fetch=True."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST, user=DB_USER, dbname=DB_NAME,
            password=DB_PASSWORD, connect_timeout=10
        )
        cur = conn.cursor()
        cur.execute(sql)
        if fetch:
            rows = cur.fetchall()
            conn.close()
            return rows if rows else None
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.warning("DB exception (non-blocking): %s", e)
        return None if fetch else True   # non-blocking: return True so pipeline continues

OLLAMA_MODEL = "qwen3.5:2b"
OLLAMA_BASE = "http://localhost:11434"
WHISPER_MODEL = "turbo"  # ~3.1 GB VRAM — fits in 4.3 GB free
# Fallback: WHISPER_MODEL = "base"  # ~1.5 GB VRAM

CLIP_MIN_SEC = 30
CLIP_MAX_SEC = 90
CLIP_WIDTH = 1080
CLIP_HEIGHT = 1920
TOP_N_SEGMENTS = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("hestia_pipeline")

# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def db_update_status(video_id: str, step: str, status: str, detail: str = ""):
    """Update pipeline status in agent_knowledge."""
    key = f"hestia_pipeline_{video_id}"
    value = json.dumps({
        "video_id": video_id,
        "step": step,
        "status": status,
        "detail": detail,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })
    sql = f"""
        INSERT INTO agent_knowledge (key, value, category, learned_at)
        VALUES ('{key}', '{json.dumps(value).replace("'", "''")}', 'hestia_local_pipeline', NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, learned_at = NOW();
    """
    db_execute(sql)


def db_save_shorts(video_id: str, shorts_data: list):
    """Save generated shorts metadata to agent_knowledge."""
    key = f"hestia_shorts_{video_id}"
    value = json.dumps({
        "video_id": video_id,
        "shorts": shorts_data,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    sql = f"""
        INSERT INTO agent_knowledge (key, value, category, learned_at)
        VALUES ('{key}', '{json.dumps(value).replace("'", "''")}', 'hestia_local_pipeline', NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
    """
    db_execute(sql)

# ---------------------------------------------------------------------------
# Step 1: yt-dlp Download
# ---------------------------------------------------------------------------
def step_download(video_id: str, work_dir: Path) -> dict:
    """Download video via yt-dlp. Returns metadata dict."""
    logger.info("[STEP 1] Downloading video %s …", video_id)
    db_update_status(video_id, "download", "running")

    url = f"https://www.youtube.com/watch?v={video_id}"
    output_path = work_dir / "original.mp4"

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(output_path),
        "--write-info-json",
        "--no-playlist",
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp failed: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("yt-dlp download timed out (600s)")

    # Load info json for metadata
    info_path = work_dir / "original.info.json"
    meta = {}
    if info_path.exists():
        with open(info_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

    duration = meta.get("duration", 0)
    title = meta.get("title", video_id)
    logger.info("[STEP 1] Downloaded: %s (%.1f min)", title, duration / 60)
    db_update_status(video_id, "download", "done", f"Title: {title}, Duration: {duration}s")
    return {"duration": duration, "title": title, "meta": meta}

# ---------------------------------------------------------------------------
# Step 2: Whisper Transcription
# ---------------------------------------------------------------------------
def step_transcribe(video_id: str, work_dir: Path) -> dict:
    """Transcribe video with whisper. Returns transcript with timestamps."""
    logger.info("[STEP 2] Transcribing video %s (model=%s) …", video_id, WHISPER_MODEL)
    db_update_status(video_id, "transcribe", "running")

    input_file = work_dir / "original.mp4"
    output_json = work_dir / "transcript.json"

    # whisper CLI — use full path from openai-whisper package
    whisper_bin = "/home/iggy/.local/bin/whisper"
    cmd = [
        whisper_bin,
        str(input_file),
        "--model", WHISPER_MODEL,
        "--language", "de",
        "--output_format", "json",
        "--output_dir", str(work_dir),
        "--word_timestamps", "True",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        if result.returncode != 0:
            raise RuntimeError(f"whisper failed: {result.stderr[:500]}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("whisper transcription timed out (1800s)")

    # whisper outputs to {input_stem}.json
    whisper_json = work_dir / "original.json"
    if not whisper_json.exists():
        whisper_json = output_json

    if not whisper_json.exists():
        raise RuntimeError("whisper output JSON not found")

    with open(whisper_json, "r", encoding="utf-8") as f:
        transcript = json.load(f)

    segments = transcript.get("segments", [])
    logger.info("[STEP 2] Transcribed %d segments", len(segments))
    db_update_status(video_id, "transcribe", "done", f"{len(segments)} segments")
    return {"segments": segments, "full_text": transcript.get("text", "")}

# ---------------------------------------------------------------------------
# Step 3: Ollama Segment Scoring
# ---------------------------------------------------------------------------
def step_score_segments(video_id: str, work_dir: Path, transcript: dict, video_duration: float) -> list:
    """Score transcript segments via Ollama for Shorts potential. Returns top N."""
    logger.info("[STEP 3] Scoring segments with %s …", OLLAMA_MODEL)
    db_update_status(video_id, "scoring", "running")

    segments = transcript["segments"]
    if not segments:
        raise RuntimeError("No segments to score")

    # Build windows of 30-90s
    windows = _build_windows(segments, video_duration)

    # Score each window via Ollama
    scored = []
    if not windows:
        logger.warning("[STEP 3] No windows built (video too short? <30s?)")
        return []

    logger.info("[STEP 3] %d windows to score (min 30s, max 90s, step 15s)", len(windows))
    for i, window in enumerate(windows):
        text_preview = window["text"][:80].replace('\n', ' ')
        logger.info("  Window %d: %.1fs–%.1fs (%ds) text=%s…",
                     i, window["start"], window["end"],
                     window["end"]-window["start"], text_preview)
        prompt = _build_scoring_prompt(window)
        raw_result = _call_ollama(prompt)
        if raw_result:
            total = raw_result.get("total", raw_result.get("score", 0))
            score = dict(raw_result)
            score["window_index"] = i
            score["start"] = window["start"]
            score["end"] = window["end"]
            scored.append(score)
            logger.info("  → scored: total=%.1f reason=%s",
                         total, raw_result.get("reason", "")[:40])
        else:
            logger.warning("  → no valid score (Ollama returned None)")

    # Sort by total score, take top N
    scored.sort(key=lambda x: x.get("total", 0), reverse=True)
    top = scored[:TOP_N_SEGMENTS]

    logger.info("[STEP 3] Top %d segments selected", len(top))
    db_update_status(video_id, "scoring", "done", f"Top {len(top)} of {len(windows)} windows")
    return top

def _build_windows(segments, video_duration, min_s=30, max_s=90, step_s=15):
    """Build overlapping time windows from transcript segments."""
    windows = []
    t = 0
    while t + min_s <= video_duration:
        end = min(t + max_s, video_duration)
        # Find segments within window
        window_segments = []
        for seg in segments:
            seg_start = seg["start"]
            seg_end = seg["end"]
            if seg_start >= t and seg_end <= end + 2:  # 2s tolerance
                window_segments.append(seg)
        if window_segments:
            text = " ".join(s["text"].strip() for s in window_segments)
            windows.append({
                "start": t,
                "end": end,
                "text": text,
                "segment_count": len(window_segments),
            })
        t += step_s
    return windows

def _build_scoring_prompt(window: dict) -> str:
    return f"""Du bist ein YouTube Shorts Experte. Bewerte dieses Transkript-Segment für das Potenzial als YouTube Short auf dem Kanal "Iggy's Welt" (Politik & Popkultur).

Zeitraum: {window['start']:.1f}s — {window['end']:.1f}s ({window['end']-window['start']:.0f}s)

Text:
{window['text']}

Bewerte JEDEN Kriterium 1-10:
1. emotion: Emotionale Intensität (Wut, Freude, Schock)
2. conflict: Konflikt-Potential / kontroverse Aussage
3. surprise: Überraschungsmoment / unerwartete Wendung
4. thesis: Starke These / klare Aussage
5. hook: Aufmerksamkeitsfang in den ersten 3 Sekunden

Antworte NUR als JSON (kein Markdown, keine Erklärung):
{{"emotion": N, "conflict": N, "surprise": N, "thesis": N, "hook": N, "total": N, "reason": "kurze Begruendung"}}"""

def _call_ollama(prompt: str, max_retries: int = 2) -> dict | None:
    """Call Ollama API and parse JSON response. Handles qwen3 thinking-mode JSON-in-thinking."""
    import urllib.request
    import urllib.error

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.3},
    }).encode("utf-8")

    def _parse_ollama_response(data: dict) -> dict | None:
        """Extract JSON from Ollama response. Handles qwen3 thinking-mode JSON-in-thinking."""
        import re
        raw = data.get("response", "").strip()

        # Strategy 1: response field contains clean JSON (for qwen3.5:2b or non-thinking models)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass

        # Strategy 2: qwen3 thinking block — JSON is embedded in markdown/narrative
        # Use raw_decode to extract the first valid JSON object starting from any '{'
        for field in ("thinking", "thought", "response"):
            text = data.get(field, "") or ""
            if not text:
                continue
            try:
                decoder = json.JSONDecoder()
                # Find the first '{' and try to decode from there
                first_brace = text.find('{')
                if first_brace == -1:
                    continue
                result, end_idx = decoder.raw_decode(text[first_brace:])
                if isinstance(result, dict) and result:
                    # Sanity check: must have at least one value that's int/float or string
                    vals = list(result.values())
                    if any(isinstance(v, (int, float, str)) for v in vals):
                        return result
            except Exception:
                pass

        return None

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(
                f"{OLLAMA_BASE}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                result = _parse_ollama_response(data)
                if result:
                    return result
                logger.warning("Ollama: no valid JSON parsed, raw: %s", str(data)[:200])
        except (urllib.error.URLError, json.JSONDecodeError, Exception) as e:
            logger.warning("Ollama attempt %d failed: %s", attempt + 1, e)
            if attempt < max_retries:
                time.sleep(5)
    return None

# ---------------------------------------------------------------------------
# Step 4: ffmpeg Clip Cutting
# ---------------------------------------------------------------------------
def step_cut_clips(video_id: str, work_dir: Path, top_segments: list) -> list:
    """Cut top segments into 9:16 Shorts using ffmpeg."""
    logger.info("[STEP 4] Cutting %d clips with ffmpeg …", len(top_segments))
    db_update_status(video_id, "cutting", "running")

    input_file = work_dir / "original.mp4"
    clips = []

    for i, seg in enumerate(top_segments):
        start = seg["start"]
        duration = seg["end"] - start
        # Clamp to 30-90s
        duration = max(CLIP_MIN_SEC, min(CLIP_MAX_SEC, duration))

        clip_path = work_dir / f"clip_{i+1}.mp4"

        # Step 4a: Extract segment, scale to 9:16, crop center
        # For widescreen source: crop width = height * 9/16, then scale
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-t", str(duration),
            "-i", str(input_file),
            "-vf", (
                f"scale={CLIP_HEIGHT}*ih/ih:{CLIP_HEIGHT},"
                f"crop={CLIP_WIDTH}:{CLIP_HEIGHT},"
                f"setsar=1"
            ),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            str(clip_path),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                logger.error("ffmpeg clip %d failed: %s", i+1, result.stderr[:300])
                continue
        except subprocess.TimeoutExpired:
            logger.error("ffmpeg clip %d timed out", i+1)
            continue

        if clip_path.exists():
            file_size = clip_path.stat().st_size
            clips.append({
                "clip_index": i + 1,
                "path": str(clip_path),
                "start": start,
                "duration": duration,
                "file_size_mb": round(file_size / (1024 * 1024), 1),
                "resolution": f"{CLIP_WIDTH}x{CLIP_HEIGHT}",
            })
            logger.info("  Clip %d: %.1fs-%.1fs (%.1f MB)",
                         i+1, start, start+duration, file_size / (1024*1024))

    logger.info("[STEP 4] %d/%d clips created", len(clips), len(top_segments))
    db_update_status(video_id, "cutting", "done", f"{len(clips)} clips created")
    return clips

# ---------------------------------------------------------------------------
# Step 5: SEO Metadata (Ollama local)
# ---------------------------------------------------------------------------
def step_generate_seo(video_id: str, work_dir: Path, clips: list, original_title: str) -> list:
    """Generate title, tags, description for each clip via Ollama."""
    logger.info("[STEP 5] Generating SEO metadata for %d clips …", len(clips))
    db_update_status(video_id, "seo", "running")

    results = []
    for clip in clips:
        # Read transcript for this clip's time range
        transcript_path = work_dir / "original.json"
        clip_text = ""
        if transcript_path.exists():
            with open(transcript_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for seg in data.get("segments", []):
                if seg["start"] >= clip["start"] and seg["end"] <= clip["start"] + clip["duration"] + 2:
                    clip_text += seg["text"] + " "

        prompt = f"""Du bist YouTube SEO Experte für den Kanal "Iggy's Welt" (Politik & Popkultur, deutschsprachig).

Original-Video-Titel: {original_title}

Transkript des Clips:
{clip_text.strip()[:2000]}

Erstelle für diesen YouTube Short:
1. title: Clickbait-Titel auf Deutsch, max 60 Zeichen
2. tags: 10 SEO-Tags als komma-separierte Liste
3. description: 2 Sätze auf Deutsch + Link zum Originalvideo

Antworte NUR als JSON (kein Markdown):
{{"title": "...", "tags": "tag1, tag2, ...", "description": "..."}}"""

        seo = _call_ollama(prompt)
        if seo:
            clip["seo"] = seo
            results.append(clip)
            logger.info("  Clip %d SEO: %s", clip["clip_index"], seo.get("title", "N/A"))
        else:
            # Fallback
            clip["seo"] = {
                "title": f"🔥 {original_title[:50]}",
                "tags": "Iggy, Politik, Shorts, iggyswelt",
                "description": f"Clip aus: {original_title}\nhttps://www.youtube.com/watch?v={video_id}",
            }
            results.append(clip)

    logger.info("[STEP 5] SEO metadata generated for %d clips", len(results))
    db_update_status(video_id, "seo", "done", f"{len(results)} clips with SEO")
    return results

# ---------------------------------------------------------------------------
# Step 6: Finalize — save to DB
# ---------------------------------------------------------------------------
def step_finalize(video_id: str, clips_with_seo: list, original_meta: dict):
    """Save final results to DB."""
    logger.info("[STEP 6] Finalizing — saving to DB …")
    db_update_status(video_id, "finalize", "running")

    shorts_data = []
    for clip in clips_with_seo:
        shorts_data.append({
            "clip_index": clip["clip_index"],
            "path": clip["path"],
            "start": clip["start"],
            "duration": clip["duration"],
            "file_size_mb": clip["file_size_mb"],
            "resolution": clip["resolution"],
            "title": clip["seo"].get("title", ""),
            "tags": clip["seo"].get("tags", ""),
            "description": clip["seo"].get("description", ""),
            "status": "ready_for_review",
        })

    db_save_shorts(video_id, shorts_data)

    # Also save the full concept as a summary
    summary = {
        "video_id": video_id,
        "original_title": original_meta.get("title", ""),
        "original_duration": original_meta.get("duration", 0),
        "clips_generated": len(shorts_data),
        "pipeline_version": "1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "workflow": "local_plan_b",
        "tools_used": ["yt-dlp", "whisper", "ollama", "ffmpeg"],
    }
    summary_json = json.dumps(summary, ensure_ascii=False).replace("'", "''")

    sql = f"""
        INSERT INTO agent_knowledge (key, value, category, learned_at)
        VALUES ('hestia_pipeline_summary_{video_id}', '{summary_json}', 'hestia_local_pipeline', NOW())
        ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
    """
    db_execute(sql)

    db_update_status(video_id, "finalize", "done", f"{len(shorts_data)} clips ready")
    logger.info("[STEP 6] Pipeline complete for %s — %d clips ready for review",
                video_id, len(shorts_data))

# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------
def run_pipeline(video_id: str):
    """Execute the full 6-step pipeline for a single video."""
    work_dir = BASE_DIR / video_id
    work_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("HESTIA LOCAL PIPELINE — video_id=%s", video_id)
    logger.info("=" * 60)

    try:
        # Step 1: Download
        meta = step_download(video_id, work_dir)
        duration = meta["duration"]
        title = meta["title"]

        # Step 2: Transcribe
        transcript = step_transcribe(video_id, work_dir)

        # Step 3: Score segments
        top_segments = step_score_segments(video_id, work_dir, transcript, duration)
        if not top_segments:
            logger.warning("No segments scored — skipping cutting")
            db_update_status(video_id, "pipeline", "done", "No suitable segments found")
            return

        # Step 4: Cut clips
        clips = step_cut_clips(video_id, work_dir, top_segments)
        if not clips:
            logger.warning("No clips created — skipping SEO")
            db_update_status(video_id, "pipeline", "done", "Cutting failed")
            return

        # Step 5: SEO metadata
        clips_with_seo = step_generate_seo(video_id, work_dir, clips, title)

        # Step 6: Finalize
        step_finalize(video_id, clips_with_seo, meta)

        logger.info("✅ PIPELINE COMPLETE — %d clips in %s", len(clips_with_seo), work_dir)

    except Exception as e:
        logger.error("❌ PIPELINE FAILED: %s", e, exc_info=True)
        db_update_status(video_id, "pipeline", "error", str(e)[:500])
        raise

# ---------------------------------------------------------------------------
# Daemon Mode (RSS polling)
# ---------------------------------------------------------------------------
def run_daemon(channel_id: str, interval: int = 600):
    """Poll YouTube RSS feed for new videos and pipeline them."""
    import urllib.request
    import xml.etree.ElementTree as ET

    logger.info("DAEMON mode started — channel=%s, interval=%ds", channel_id, interval)
    db_update_status("daemon", "status", "running", f"channel={channel_id}")

    seen_videos = set()
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

    while True:
        try:
            req = urllib.request.Request(rss_url, headers={"User-Agent": "Hestia-Pipeline/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                xml_data = resp.read()

            root = ET.fromstring(xml_data)
            ns = {"atom": "http://www.w3.org/2005/Atom"}

            for entry in root.findall("atom:entry", ns):
                video_id = entry.find("atom:videoId", ns)
                if video_id is None:
                    # Try yt:videoId
                    video_id = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId")
                if video_id is None:
                    continue
                video_id = video_id.text

                if video_id not in seen_videos:
                    seen_videos.add(video_id)
                    logger.info("NEW VIDEO detected: %s", video_id)
                    run_pipeline(video_id)

        except Exception as e:
            logger.error("Daemon loop error: %s", e)

        logger.info("Sleeping %ds …", interval)
        time.sleep(interval)

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Hestia Local Pipeline — YouTube Shorts Workflow (Plan B)"
    )
    parser.add_argument("--video-id", help="YouTube video ID to process")
    parser.add_argument("--mode", choices=["once", "daemon"], default="once",
                        help="Run once or as daemon polling RSS")
    parser.add_argument("--channel", help="YouTube channel ID (for daemon mode)")
    parser.add_argument("--interval", type=int, default=600,
                        help="RSS poll interval in seconds (daemon mode)")
    # Capture defaults locally BEFORE global declaration
    _default_whisper = "turbo"
    _default_ollama = "qwen3.5:2b"
    parser.add_argument("--whisper-model", default=_default_whisper,
                        help=f"Whisper model (default: {_default_whisper})")
    parser.add_argument("--ollama-model", default=_default_ollama,
                        help=f"Ollama model (default: {_default_ollama})")

    args = parser.parse_args()

    # Override globals from CLI (for daemon sub-functions)
    globals()['WHISPER_MODEL'] = args.whisper_model
    globals()['OLLAMA_MODEL'] = args.ollama_model

    if args.mode == "daemon":
        if not args.channel:
            parser.error("--channel required for daemon mode")
        run_daemon(args.channel, args.interval)
    else:
        if not args.video_id:
            parser.error("--video-id required for once mode")
        run_pipeline(args.video_id)


if __name__ == "__main__":
    main()
