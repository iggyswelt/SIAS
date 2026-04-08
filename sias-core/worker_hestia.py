#!/usr/bin/env python3
"""
worker_hestia.py — Hestia YouTube Shorts Automation
Phases 1+2: RSS Monitor + Opus Clip Creation

Usage:
  python3 worker_hestia.py --once   # single run (for cron)
  python3 worker_hestia.py           # daemon mode, polls every 30 min

Environment:
  DATABASE_URL=postgresql://scraper:...@127.0.0.1/metamaus
  Opus API keys stored in DB agent_knowledge key='opus_clip_api_config'
"""

import os
import sys
import json
import time
import argparse
import logging
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError

import feedparser
import psycopg2
from psycopg2 import sql, extras

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("worker_hestia")

# ── Opus API ──────────────────────────────────────────────────────────────────
OPUS_API_BASE = os.environ.get("OPUS_API_BASE", "https://api.opus.pro/api")

# ── Known UC-format channel IDs (resolved from @-handles at runtime) ─────────
# Resolved manually — youtube_channels DB stores @-handles but RSS needs UC IDs.
OWN_CHANNEL_UC_IDS = {
    "@iggyswelt": "UCk3QASirweuiFadxh2oB5UA",
}


# ── DB Helpers ────────────────────────────────────────────────────────────────
def get_db_conn():
    return psycopg2.connect(
        host="127.0.0.1",
        user="scraper",
        database="metamaus",
        cursor_factory=extras.RealDictCursor,
    )


def db_upsert_agent_knowledge(conn, key, category, value):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_knowledge (key, category, value, updated_at)
            VALUES (%s, %s, %s::jsonb, NOW())
            ON CONFLICT (key) DO UPDATE
              SET value = EXCLUDED.value, updated_at = NOW()
            """,
            (key, category, json.dumps(value)),
        )
    conn.commit()


def load_opus_config(conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value::text FROM agent_knowledge WHERE key='opus_clip_api_config'"
        )
        row = cur.fetchone()
    if row:
        return json.loads(row["value"])
    return None


def get_own_channel_id(conn):
    """
    Get the own-channel handle from DB, then resolve to real UC-format ID.
    """
    with conn.cursor() as cur:
        cur.execute(
            "SELECT channel_id FROM youtube_channels WHERE type='own' LIMIT 1"
        )
        row = cur.fetchone()
    if row:
        handle = row["channel_id"]
        if handle in OWN_CHANNEL_UC_IDS:
            return OWN_CHANNEL_UC_IDS[handle]
        if handle.startswith("UC"):
            return handle
        return handle
    return OWN_CHANNEL_UC_IDS.get("@iggyswelt")


# ── Ensure DB tables exist ─────────────────────────────────────────────────────
def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS youtube_shorts (
              id              SERIAL PRIMARY KEY,
              video_id        TEXT NOT NULL UNIQUE,
              opus_project_id TEXT,
              clip_url        TEXT,
              clip_status     TEXT DEFAULT 'pending',
              title           TEXT,
              published_at    TIMESTAMP,
              created_at      TIMESTAMP DEFAULT NOW()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_youtube_shorts_video_id "
            "ON youtube_shorts(video_id)"
        )
    conn.commit()
    log.info("DB tables ensured.")


# ── RSS Feed ───────────────────────────────────────────────────────────────────
def fetch_rss(channel_uc_id: str):
    """
    Fetch YouTube RSS feed for a UC-format channel ID.
    """
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_uc_id}"
    log.info(f"Fetching RSS: {url}")
    result = feedparser.parse(url)
    if result.entries:
        log.info(f"RSS OK — {len(result.entries)} entries")
    else:
        log.warning(f"RSS returned no entries for {channel_uc_id}")
    return result


def parse_feed_entry(entry):
    """Extract video_id, title, published from a feedparser entry."""
    video_id = None
    raw_id = getattr(entry, "id", None) or getattr(entry, "yt_videoid", None)
    if raw_id:
        # strip 'yt:video:' prefix if present (YouTube RSS format)
        video_id = raw_id.replace("yt:video:", "").split("/")[-1]

    title = entry.get("title", "Unknown")
    published = None
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        published = datetime(*entry.published_parsed[:6])

    return video_id, title, published


# ── Video tracking ─────────────────────────────────────────────────────────────
def video_exists_in_db(conn, video_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM youtube_videos WHERE video_id = %s LIMIT 1",
            (video_id,)
        )
        return cur.fetchone() is not None


def insert_video_record(conn, video_id: str, title: str, published_at, channel_id: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO youtube_videos (video_id, title, channel_id, published_at, fetched_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (video_id) DO NOTHING
            """,
            (video_id, title, channel_id, published_at),
        )
    conn.commit()


def insert_short_record(conn, video_id: str, title: str, published_at):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO youtube_shorts (video_id, title, published_at, clip_status)
            VALUES (%s, %s, %s, 'pending')
            ON CONFLICT (video_id) DO UPDATE
              SET title = EXCLUDED.title, published_at = EXCLUDED.published_at
            RETURNING id, clip_status
            """,
            (video_id, title, published_at),
        )
        row = cur.fetchone()
    conn.commit()
    return row


# ── Opus Clip Creation ─────────────────────────────────────────────────────────
def create_opus_project(conn, video_id: str, title: str, video_url: str):
    """
    Create an Opus clip project via their REST API.
    Config from DB agent_knowledge key='opus_clip_api_config'.
    Returns (opus_project_id, clip_url) or (None, None) on failure.
    """
    config = load_opus_config(conn)
    if not config:
        log.warning("Opus config missing — skipping clip creation for %s", video_id)
        return None, None

    api_key = config.get("api_key")
    org_id = config.get("org_id")
    base_url = config.get("base_url", OPUS_API_BASE)

    if not api_key or not org_id:
        log.warning("Opus config incomplete — missing api_key or org_id")
        return None, None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "videoUrl": video_url,
        "numClips": 3,
        "clipLength": {"min": 30, "max": 90},
        "title": f"[Hestia] {title}",
    }

    try:
        import urllib.request
        req = urllib.request.Request(
            f"{base_url}/clip-projects",
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            project_id = data.get("id") or data.get("project", {}).get("id")
            clip_url = data.get("clipUrl") or data.get("url")
            log.info(f"Opus project created: video={video_id}, project={project_id}")
            return project_id, clip_url
    except URLError as e:
        log.error(f"Opus API error for {video_id}: {e}")
        return None, None
    except json.JSONDecodeError as e:
        log.error(f"Opus API non-JSON response for {video_id}: {e}")
        return None, None


def update_short_record(conn, video_id: str, opus_project_id: str = None,
                        clip_url: str = None, status: str = None):
    updates = []
    params = []
    if opus_project_id:
        updates.append("opus_project_id = %s")
        params.append(opus_project_id)
    if clip_url:
        updates.append("clip_url = %s")
        params.append(clip_url)
    if status:
        updates.append("clip_status = %s")
        params.append(status)
    if updates:
        params.append(video_id)
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE youtube_shorts SET {', '.join(updates)} WHERE video_id = %s",
                params,
            )
        conn.commit()


# ── Status update ──────────────────────────────────────────────────────────────
def update_hestia_status(conn, phase: int, opus_key_missing: bool, details: str = None):
    value = {
        "phase1": phase >= 1,
        "phase2": phase >= 2,
        "opus_key_missing": opus_key_missing,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if details:
        value["details"] = details
    db_upsert_agent_knowledge(conn, "hestia_youtube_shorts_setup", "youtube", value)
    log.info(f"Status updated: {value}")


# ── Hestia Signal ─────────────────────────────────────────────────────────────
def signal_hestia(conn, video_id: str, title: str, short_id: int):
    """
    Write a signal into agent_tasks table for Hestia to pick up.
    Schema: agent_tasks(agent, task, status, result, created_by, created_at)
    """
    payload = json.dumps({
        "video_id": video_id,
        "title": title,
        "short_id": short_id,
        "source": "worker_hestia",
        "event": "new_short_detected",
    })
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO agent_tasks (agent, task, status, result, created_by, created_at)
                VALUES ('hestia', 'new_short_review', 'pending', %s, 'worker_hestia', NOW())
                """,
                (payload,),
            )
        conn.commit()
        log.info(f"Hestia signalled via agent_tasks: new_short {video_id}")
    except Exception as e:
        log.warning(f"Failed to signal Hestia: {e}")


# ── Main worker ────────────────────────────────────────────────────────────────
def process_new_videos(conn, feed):
    channel_uc_id = get_own_channel_id(conn)
    channel_handle = "@iggyswelt"
    opus_config = load_opus_config(conn)
    opus_key_missing = opus_config is None

    new_count = 0
    for entry in feed.entries:
        video_id, title, published_at = parse_feed_entry(entry)
        if not video_id:
            log.warning("Could not extract video_id from entry: %s", entry.get("id"))
            continue

        if video_exists_in_db(conn, video_id):
            log.debug(f"Already tracked: {video_id}")
            continue

        log.info(f"New video detected: {video_id} — {title}")

        # 1. Insert into youtube_videos (master tracking)
        insert_video_record(conn, video_id, title, published_at, channel_uc_id)

        # 2. Insert into youtube_shorts (shorts-specific)
        row = insert_short_record(conn, video_id, title, published_at)
        short_id = row["id"]

        # 3. Create Opus project (if keys available)
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        if not opus_key_missing:
            project_id, clip_url = create_opus_project(
                conn, video_id, title, video_url
            )
            if project_id:
                update_short_record(
                    conn, video_id,
                    opus_project_id=project_id,
                    clip_url=clip_url,
                    status="processing",
                )
            else:
                update_short_record(conn, video_id, status="opus_error")
        else:
            log.info(f"Opus key missing — short {video_id} queued as pending")
            update_short_record(conn, video_id, status="pending")

        # 4. Signal Hestia
        try:
            signal_hestia(conn, video_id, title, short_id)
        except Exception as e:
            log.error(f"Failed to signal Hestia for {video_id}: {e}")

        new_count += 1

    return new_count, opus_key_missing


def run_once():
    conn = get_db_conn()
    try:
        ensure_tables(conn)
        channel_uc_id = get_own_channel_id(conn)
        log.info(f"Using channel UC ID: {channel_uc_id}")
        feed = fetch_rss(channel_uc_id)
        new_count, opus_missing = process_new_videos(conn, feed)
        update_hestia_status(conn, phase=2, opus_key_missing=opus_missing)
        log.info(
            f"Worker run complete — new videos: {new_count}, "
            f"opus_key_missing: {opus_missing}"
        )
    finally:
        conn.close()


def run_daemon(poll_interval_seconds=1800):
    log.info(
        f"Hestia worker starting in daemon mode "
        f"(poll_interval={poll_interval_seconds}s)"
    )
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Worker error: {e}", exc_info=True)
        log.info(f"Sleeping {poll_interval_seconds}s until next poll...")
        time.sleep(poll_interval_seconds)


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hestia YouTube Shorts Worker")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run a single poll cycle and exit (use with cron)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=1800,
        help="Poll interval in seconds (default: 1800 = 30 min)",
    )
    args = parser.parse_args()

    if args.once:
        run_once()
    else:
        run_daemon(poll_interval_seconds=args.interval)
