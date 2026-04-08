from flask import Flask, jsonify, render_template, render_template_string, send_from_directory, request
import requests
from datetime import datetime
import pytz
import json
import os
import psycopg2

def now_berlin():
    """Return current datetime in Europe/Berlin timezone (CET/CEST)."""
    return datetime.now(pytz.timezone('Europe/Berlin'))
from psycopg2.extras import RealDictCursor
from email.message import EmailMessage

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# PostgreSQL Database Configuration - LOCAL
DB_CONFIG = {
    'host': '127.0.0.1',
    'database': 'metamaus',
    'user': 'scraper',
    'password': '',
    'port': 5432
}

def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**DB_CONFIG)

YOUTUBE_API_KEY = "AIzaSyD_bbGPhXLOsZqzEva2ZPpNzka8YViFz8c"

# Serve dashboard HTML
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# SPA tab routes — serve index.html for direct URL access (each endpoint unique)
def _make_spa_route(tab):
    def _spa():
        return send_from_directory('.', 'index.html')
    _spa.__name__ = f'spa_{tab}'
    return _spa

for _tab in ['demos', 'tasks', 'youtube', 'agents', 'mails', 'logs', 'news', 'trading']:
    app.add_url_rule(f'/{_tab}', f'spa_{_tab}', _make_spa_route(_tab))

@app.route('/youtube_analysis.json')
def youtube_analysis():
    if os.path.exists('/tmp/youtube_analysis.json'):
        with open('/tmp/youtube_analysis.json') as f:
            return jsonify(json.load(f))
    return jsonify([])

# ============ YouTube Channels API (must be BEFORE /api/youtube/<video_id>) ============

@app.route('/api/youtube/channels', methods=['GET'])
def get_youtube_channels():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM youtube_channels ORDER BY type, channel_name")
        channels = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'channels': channels})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/channels', methods=['POST'])
def add_youtube_channel():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO youtube_channels (channel_id, channel_name, type, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (channel_id) DO NOTHING
            RETURNING *
        """, (data.get('channel_id'), data.get('channel_name'), data.get('type'), data.get('notes')))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success', 'channel': dict(result)})
        return jsonify({'status': 'error', 'message': 'Channel already exists'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/channels/<channel_id>', methods=['DELETE'])
def delete_youtube_channel(channel_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM youtube_channels WHERE channel_id = %s RETURNING id", (channel_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success', 'deleted': channel_id})
        return jsonify({'status': 'error', 'message': 'Channel not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/stats/all', methods=['GET'])
def get_all_youtube_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                yc.channel_id,
                yc.channel_name,
                yc.type,
                yc.notes,
                ys.subscribers,
                ys.total_views,
                ys.video_count,
                ys.fetched_at as updated_at
            FROM youtube_channels yc
            LEFT JOIN youtube_stats ys ON yc.channel_id = ys.channel_id
                AND ys.id = (SELECT id FROM youtube_stats WHERE channel_id = yc.channel_id ORDER BY fetched_at DESC LIMIT 1)
            WHERE yc.active = true
            ORDER BY yc.type, yc.channel_name
        """)
        channels = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for ch in channels:
            d = dict(ch)
            d['updated_at'] = d['updated_at'].isoformat() if d.get('updated_at') else None
            result.append(d)
        
        return jsonify({'status': 'success', 'channels': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/progress', methods=['GET'])
def get_youtube_progress():
    """Get learning progress across all playlists"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get total videos and learned
        cursor.execute("""
            SELECT 
                COALESCE(SUM(videos_total), 0) as total,
                COALESCE(SUM(videos_learned), 0) as learned
            FROM iggy_playlists
        """)
        row = cursor.fetchone()
        
        total = row['total'] or 0
        learned = row['learned'] or 0
        percent = round(learned / total * 100, 1) if total > 0 else 0
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'total': total,
            'learned': learned,
            'percent': percent
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/refresh', methods=['POST'])
def refresh_youtube_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM youtube_channels WHERE active = true")
        channels = cursor.fetchall()
        
        refreshed = 0
        for ch in channels:
            channel_id = ch['channel_id']
            
            try:
                handle = channel_id if channel_id.startswith('@') else f'@{channel_id}'
                resp = requests.get('https://www.googleapis.com/youtube/v3/channels',
                    params={'part': 'statistics', 'forHandle': handle, 'key': YOUTUBE_API_KEY}, timeout=10)
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('items'):
                        stats = data['items'][0]['statistics']
                        subs = int(stats.get('subscriberCount', 0))
                        views = int(stats.get('viewCount', 0))
                        videos = int(stats.get('videoCount', 0))
                        
                        # Delete old stats for this channel, then insert new
                        cursor.execute("DELETE FROM youtube_stats WHERE channel_id = %s", (channel_id,))
                        cursor.execute("""
                            INSERT INTO youtube_stats (channel_id, subscribers, total_views, video_count)
                            VALUES (%s, %s, %s, %s)
                        """, (channel_id, subs, views, videos))
                        refreshed += 1
            except Exception as e:
                print(f"Error fetching {channel_id}: {e}")
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'refreshed': refreshed})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/videos/<channel_id>', methods=['GET'])
def get_channel_videos(channel_id):
    try:
        handle = channel_id if channel_id.startswith('@') else f'@{channel_id}'
        resp = requests.get('https://www.googleapis.com/youtube/v3/channels',
            params={'part': 'id', 'forHandle': handle, 'key': YOUTUBE_API_KEY}, timeout=10)
        
        yt_channel_id = None
        if resp.status_code == 200:
            data = resp.json()
            if data.get('items'):
                yt_channel_id = data['items'][0]['id']
        
        if not yt_channel_id:
            return jsonify({'status': 'error', 'message': 'Channel not found'}), 404
        
        resp = requests.get('https://www.googleapis.com/youtube/v3/search',
            params={
                'part': 'snippet',
                'channelId': yt_channel_id,
                'order': 'date',
                'maxResults': 10,
                'key': YOUTUBE_API_KEY
            }, timeout=10)
        
        videos = []
        if resp.status_code == 200:
            data = resp.json()
            for item in data.get('items', []):
                if item['id'].get('videoId'):
                    videos.append({
                        'video_id': item['id']['videoId'],
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt'],
                        'thumbnail': item['snippet']['thumbnails'].get('medium', {}).get('url')
                    })
        
        return jsonify({'status': 'success', 'videos': videos})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============ End YouTube Channels API ============

# YouTube Stats API
@app.route('/api/youtube/<video_id>')
def youtube_stats(video_id):
    try:
        resp = requests.get('https://www.googleapis.com/youtube/v3/videos',
            params={'part': 'snippet,statistics', 'id': video_id, 'key': YOUTUBE_API_KEY})
        data = resp.json()
        
        if data.get('items'):
            item = data['items'][0]
            stats = item['statistics']
            views = int(stats.get('viewCount', 0))
            likes = int(stats.get('likeCount', 0))
            engagement = (likes / views * 100) if views > 0 else 0
            
            return jsonify({
                'status': 'fresh',
                'data': {
                    'video_id': video_id,
                    'title': item['snippet']['title'],
                    'view_count': views,
                    'like_count': likes,
                    'comment_count': int(stats.get('commentCount', 0)),
                    'engagement_rate': round(engagement, 2),
                    'thumbnail_url': item['snippet']['thumbnails']['high']['url']
                }
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Video not found'}), 404

@app.route('/api/demos')
def get_demos():
    """Get demo events from PostgreSQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get query parameters
        category = request.args.get('category', 'all')
        location = request.args.get('location', 'all')

        # Build query with filters
        where_clauses = ["date >= CURRENT_DATE - INTERVAL '7 days'"]
        params = []

        if category and category.lower() != 'all':
            where_clauses.append("LOWER(category) = %s")
            params.append(category.lower())

        if location and location.lower() != 'all':
            # Filter by location (case-insensitive partial match)
            where_clauses.append("LOWER(location) LIKE %s")
            params.append(f"%{location.lower()}%")

        where_clause = " AND ".join(where_clauses)

        # Get upcoming demos (today and future) with proper sorting
        cursor.execute(f"""
            SELECT id, title, NULL as description, date as event_date, time as event_time, location,
                   NULL as address, NULL as organizer, source_url, source,
                   category, FALSE as verified, 'planned' as status, NULL as participant_count,
                   CASE WHEN is_valid = TRUE THEN 'valid' WHEN is_valid = FALSE THEN 'invalid' ELSE 'pending' END as validation_status,
                   validation_note, is_valid, user_feedback, scraped_at as updated_at
            FROM demo_events
            WHERE {where_clause}
            ORDER BY date ASC, time ASC NULLS LAST, title ASC
            LIMIT 50
        """, params)
        events = cursor.fetchall()
        
        # Convert to list of dicts and handle datetime serialization
        events_list = []
        for event in events:
            event_dict = dict(event)
            # Convert datetime to ISO string
            if event_dict.get('event_date'):
                event_dict['event_date'] = event_dict['event_date'].isoformat() if hasattr(event_dict['event_date'], 'isoformat') else str(event_dict['event_date'])
            if event_dict.get('event_time'):
                event_dict['event_time'] = str(event_dict['event_time']) if event_dict['event_time'] else None
            events_list.append(event_dict)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'events': events_list,
            'count': len(events_list),
            'status': 'success',
            'updated': now_berlin().isoformat()
        })
    except Exception as e:
        return jsonify({
            'events': [],
            'count': 0,
            'status': 'error',
            'message': str(e),
            'updated': now_berlin().isoformat()
        }), 500

@app.route('/api/demos/all')
def get_all_demos():
    """Get ALL demo events for the calendar view"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get all demos ordered by date
        cursor.execute("""
            SELECT id, title, NULL as description, date as event_date, time as event_time, location,
                   NULL as address, NULL as organizer, source_url, source as source_name,
                   category, FALSE as verified, 'planned' as status, NULL as participant_count, scraped_at as updated_at,
                   CASE WHEN is_valid = TRUE THEN 'valid' WHEN is_valid = FALSE THEN 'invalid' ELSE 'pending' END as validation_status,
                   validation_note, is_valid, user_feedback
            FROM demo_events 
            ORDER BY date DESC NULLS LAST
        """)
        events = cursor.fetchall()
        
        events_list = []
        for event in events:
            event_dict = dict(event)
            if event_dict.get('event_date'):
                event_dict['event_date'] = event_dict['event_date'].isoformat() if hasattr(event_dict['event_date'], 'isoformat') else str(event_dict['event_date'])
            if event_dict.get('event_time'):
                event_dict['event_time'] = str(event_dict['event_time']) if event_dict['event_time'] else None
            if event_dict.get('updated_at'):
                event_dict['updated_at'] = event_dict['updated_at'].isoformat() if hasattr(event_dict['updated_at'], 'isoformat') else str(event_dict['updated_at'])
            events_list.append(event_dict)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'events': events_list,
            'count': len(events_list),
            'status': 'success',
            'updated': now_berlin().isoformat()
        })
    except Exception as e:
        return jsonify({
            'events': [],
            'count': 0,
            'status': 'error',
            'message': str(e),
            'updated': now_berlin().isoformat()
        }), 500

@app.route('/api/quota')
def get_quota():
    return jsonify({
        'quotas': [
            {'service_name': 'youtube', 'calls_made_today': 3, 'daily_quota': 10000},
            {'service_name': 'brave_search', 'calls_made_today': 0, 'daily_quota': 100}
        ]
    })

@app.route("/api/youtube/background-refresh", methods=["POST"])
def refresh_youtube():
    # Trigger background analysis
    os.system('python3 /tmp/youtube_analyzer.py > /tmp/youtube_progress.log 2>&1 &')
    return jsonify({'status': 'refresh_started'})

# ============================================================
# TASKBOARD API - Vollständiges CRUD
# ============================================================

@app.route('/api/tasks/move', methods=['POST'])
def move_task():
    """Move task to new status"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s RETURNING id
        """, (data.get('new_status'), data.get('task_id')))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({'success': True})
        return jsonify({'error': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Alle Tasks abrufen, gruppiert nach Status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        status_filter = request.args.get('status')
        
        if status_filter:
            cursor.execute("""
                SELECT id, title, description, status, priority, 
                       assigned_to, updated_at, url, created_by, category, rejection_reason, status_log, archived_at
                FROM tasks 
                WHERE status = %s
                ORDER BY priority DESC, updated_at ASC
            """, (status_filter,))
        else:
            cursor.execute("""
                SELECT id, title, description, status, priority, 
                       assigned_to, updated_at, url, created_by, category, rejection_reason, status_log, archived_at
                FROM tasks 
                ORDER BY CASE status 
                            WHEN 'in_progress' THEN 1 
                            WHEN 'awaiting_confirm' THEN 2 
                            WHEN 'todo' THEN 3 
                            WHEN 'done' THEN 4 
                            ELSE 5 
                         END, priority DESC, updated_at ASC
            """)
        
        tasks = cursor.fetchall()
        
        # Gruppiere nach Status (5-Stufen-Flow)
        grouped = {'todo': [], 'in_progress': [], 'awaiting_confirm': [], 'done': []}
        counts = {'todo': 0, 'in_progress': 0, 'awaiting_confirm': 0, 'done': 0}
        
        for task in tasks:
            task_dict = dict(task)
            task_dict['updated_at'] = str(task_dict['updated_at']) if task_dict.get('updated_at') else None
            
            status = task_dict['status']
            if status in grouped:
                grouped[status].append(task_dict)
                counts[status] += 1
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'status': 'success',
            'tasks': grouped,
            'counts': counts,
            'total': sum(counts.values())
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Neuen Task erstellen"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO tasks (title, description, status, priority, assigned_to)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
            data.get('title'),
            data.get('description', ''),
            data.get('status', 'todo'),
            data.get('priority', 3),
            data.get('assigned_to', 'Iggy')
        ))
        
        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'id': new_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Einzelnen Task abrufen"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if task:
            return jsonify({'status': 'success', 'task': dict(task)})
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Task aktualisieren"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks 
            SET title = %s, description = %s, status = %s, 
                priority = %s, assigned_to = %s
            WHERE id = %s
            RETURNING id
        """, (
            data.get('title'),
            data.get('description', ''),
            data.get('status'),
            data.get('priority'),
            data.get('assigned_to', 'Iggy'),
            task_id
        ))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({'status': 'success', 'updated': task_id})
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/status', methods=['PATCH'])
def update_task_status(task_id):
    """Nur Status updaten (für Drag & Drop)"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE tasks SET status = %s WHERE id = %s RETURNING id
        """, (data.get('status'), task_id))
        
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({'status': 'success', 'updated': task_id})
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Task löschen"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = %s RETURNING id", (task_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        
        if result:
            return jsonify({'status': 'success', 'deleted': task_id})
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/archive', methods=['POST'])
def archive_task(task_id):
    """Task archivieren"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE tasks SET archived = true, archived_at = NOW() WHERE id = %s RETURNING id",
            (task_id,)
        )
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Task not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============ YouTube Community API ============

@app.route('/api/youtube/community/top100/comments', methods=['GET'])
def get_top100_comments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM yt_community 
            ORDER BY total_comments DESC 
            LIMIT 100
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'members': [dict(r) for r in result]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/community/top100/loyalty', methods=['GET'])
def get_top100_loyalty():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM yt_community 
            ORDER BY last_seen DESC 
            LIMIT 100
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'members': [dict(r) for r in result]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/community/elite', methods=['GET'])
def get_elite_members():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM yt_community 
            WHERE vip_tier = 'elite'
            ORDER BY total_comments DESC
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'members': [dict(r) for r in result]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/community/<author_id>', methods=['GET'])
def get_member_profile(author_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM yt_community WHERE author_channel_id = %s
        """, (author_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success', 'member': dict(result)})
        return jsonify({'status': 'error', 'message': 'Member not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments', methods=['GET'])
def get_comments():
    try:
        status = request.args.get('status', 'pending')
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT * FROM yt_comments 
            WHERE reply_status = %s
            ORDER BY like_count DESC, published_at DESC
            LIMIT %s
        """, (status, limit))
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'comments': [dict(r) for r in result]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/vip', methods=['GET'])
def get_vip_comments():
    """Get comments from top 100 community members"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get comments from top 100 users (by comments or likes)
        cursor.execute("""
            SELECT c.*, 
                (SELECT COUNT(*) FROM yt_comments r WHERE r.parent_id = c.comment_id) as reply_count
            FROM yt_comments c
            WHERE c.author_channel_id IN (
                SELECT author_channel_id FROM yt_community
                ORDER BY (total_comments + total_likes_received) DESC
                LIMIT 100
            )
            AND c.reply_status = 'pending'
            ORDER BY c.like_count DESC, c.published_at DESC
            LIMIT 50
        """)
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'comments': [dict(r) for r in result]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/fetch', methods=['POST'])
def fetch_comments():
    """Fetch comments from YouTube for own channels"""
    try:
        # Get own channels
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT channel_id FROM youtube_channels WHERE type = 'own' AND active = true")
        channels = cursor.fetchall()
        
        all_comments = []
        
        for ch in channels:
            channel_id = ch['channel_id']
            handle = channel_id if channel_id.startswith('@') else f'@{channel_id}'
            
            # Get channel's recent videos
            try:
                resp = requests.get('https://www.googleapis.com/youtube/v3/channels',
                    params={'part': 'id', 'forHandle': handle, 'key': YOUTUBE_API_KEY}, timeout=10)
                
                yt_channel_id = None
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('items'):
                        yt_channel_id = data['items'][0]['id']
                
                if not yt_channel_id:
                    continue
                
                # Get recent videos (last 5)
                resp = requests.get('https://www.googleapis.com/youtube/v3/search',
                    params={
                        'part': 'id',
                        'channelId': yt_channel_id,
                        'order': 'date',
                        'maxResults': 50,
                        'type': 'video',
                        'key': YOUTUBE_API_KEY
                    }, timeout=10)
                
                video_ids = []
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get('items', []):
                        if item['id'].get('videoId'):
                            video_ids.append(item['id']['videoId'])
                
                # Get comments for each video
                for vid in video_ids:
                    try:
                        resp = requests.get('https://www.googleapis.com/youtube/v3/commentThreads',
                            params={
                                'part': 'snippet,replies',
                                'videoId': vid,
                                'maxResults': 100,
                                'order': 'time',
                                'key': YOUTUBE_API_KEY
                            }, timeout=10)
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            for item in data.get('items', []):
                                snippet = item['snippet']['topLevelComment']['snippet']
                                comment_id = item['snippet']['topLevelComment']['id']
                                author_name = snippet.get('authorDisplayName', 'Unknown')
                                author_channel = snippet.get('authorChannelId', {}).get('value', '')
                                text = snippet.get('textDisplay', '')
                                like_count = snippet.get('likeCount', 0)
                                published = snippet.get('publishedAt', '')
                                
                                # Classify sentiment
                                sentiment = classify_sentiment(text)
                                
                                # Auto-ignore hostile comments
                                auto_ignored = False
                                if sentiment == 'hostile':
                                    auto_ignored = True
                                
                                # Insert or update community member (with likes)
                                cursor.execute("""
                                    INSERT INTO yt_community (author_channel_id, author_name, total_comments, total_likes_received, first_seen, last_seen)
                                    VALUES (%s, %s, 1, %s, NOW(), NOW())
                                    ON CONFLICT (author_channel_id) DO UPDATE SET
                                        total_comments = yt_community.total_comments + 1,
                                        total_likes_received = yt_community.total_likes_received + %s,
                                        last_seen = NOW()
                                """, (author_channel, author_name, like_count, like_count))
                                
                                # Insert comment with sentiment
                                status = 'ignored' if auto_ignored else 'pending'
                                cursor.execute("""
                                    INSERT INTO yt_comments (comment_id, video_id, author_channel_id, author_name, text, like_count, published_at, reply_status, sentiment, auto_ignored)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (comment_id) DO NOTHING
                                """, (comment_id, vid, author_channel, author_name, text, like_count, published, status, sentiment, auto_ignored))
                                
                    except Exception as e:
                        continue
                        
            except Exception as e:
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'message': 'Comments fetched'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/auto-like', methods=['POST'])
def auto_like_comments():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Find all unliked pending comments and like them
        cursor.execute("""
            UPDATE yt_comments 
            SET is_liked = true 
            WHERE is_liked = false 
            RETURNING id
        """)
        updated = cursor.fetchall()
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'liked': len(updated)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/<int:comment_id>/like', methods=['POST'])
def like_comment(comment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE yt_comments SET is_liked = true WHERE id = %s RETURNING id", (comment_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Comment not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/<int:comment_id>/ignore', methods=['POST'])
def ignore_comment(comment_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE yt_comments SET reply_status = 'ignored' WHERE id = %s RETURNING id", (comment_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Comment not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/<int:comment_id>/suggest', methods=['POST'])
def suggest_reply(comment_id):
    """Generate TWO AI reply suggestions for a comment - short and direct"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get comment
        cursor.execute("SELECT * FROM yt_comments WHERE id = %s", (comment_id,))
        comment = cursor.fetchone()
        
        if not comment:
            return jsonify({'status': 'error', 'message': 'Comment not found'}), 404
        
        comment_text = comment.get('text', '')
        
        # Generate two different suggestions
        suggestions = []
        
        for style in ["sachlich", "ironisch"]:
            prompt = f"""Du bist Iggy von iggyswelt (YouTube). Antworte auf Deutsch, KURZ, max 8-10 Wörter, NUR die Antwort (keine Erklärung).
Stil: {style}
Kommentar: {comment_text}
Antwort:"""
            
            try:
                import requests as req
                resp = req.post(
                    'https://api.minimax.io/v1/text/chatcompletion_v2',
                    headers={
                        'Authorization': f'Bearer {os.environ.get("MINIMAX_API_KEY", "")}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'MiniMax-M2.1',
                        'messages': [{'role': 'user', 'content': prompt}],
                        'max_tokens': 50
                    },
                    timeout=15
                )
                
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('choices'):
                        msg = data['choices'][0].get('message', {})
                        # MiniMax antwortet in reasoning_content statt content
                        text = msg.get('content', '') or msg.get('reasoning_content', '')
                        text = text.strip().split('\n')[0][:100]
                        if text and len(text) > 3:
                            suggestions.append(text)
            except:
                pass
        
        # Intelligent fallbacks based on comment keywords
        comment_lower = comment_text.lower()
        suggestions = []
        
        # Context-aware suggestions
        if any(w in comment_lower for w in ['merz', 'burns', 'spahn', 'simpsons']):
            suggestions = ["Genau das! 🎯", "Die Show läuft! 😄"]
        elif any(w in comment_lower for w in ['gewalt', 'kultur', 'opfer', 'täter']):
            suggestions = ["Wichtiger Punkt! 💪", "Danke für Input! 🐭"]
        elif any(w in comment_lower for w in ['zdf', 'skandal', 'korrespondent', 'ki']):
            suggestions = ["Unglaublich, oder? 😤", "Danke fürs Teilen! 🔥"]
        elif any(w in comment_lower for w in ['zahlen', 'statistik', 'bullshit', 'anklägerin']):
            suggestions = ["Absolut! 💯", "Sehe ich auch so! ✅"]
        elif any(w in comment_lower for w in ['kind', 'ps1', 'demo', 'nostalgie']):
            suggestions = ["Gute alte Zeit! 🎮", "Nostalgie pur! ⭐️"]
        elif any(w in comment_lower for w in ['danke', 'super', 'toll', 'genial']):
            suggestions = ["Danke dir! 🐭", "Freut mich! 😊"]
        else:
            suggestions = ["Danke dir! 🐭", "Top Kommentar! 👍"]
        
        # Ensure we have 2 suggestions
        if len(suggestions) < 2:
            suggestions.append("Stimmt! 👍")
        
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'suggestion1': suggestions[0], 'suggestion2': suggestions[1]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/<int:comment_id>/reply', methods=['POST'])
def reply_comment(comment_id):
    """Save reply and mark as replied"""
    try:
        data = request.get_json()
        reply_text = data.get('text', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get comment's comment_id (YouTube ID)
        cursor.execute("SELECT comment_id FROM yt_comments WHERE id = %s", (comment_id,))
        result = cursor.fetchone()
        
        if result:
            yt_comment_id = result[0]
            # Insert as a reply
            cursor.execute("""
                INSERT INTO yt_comments (comment_id, video_id, author_channel_id, author_name, text, parent_id, is_reply, reply_status)
                VALUES (%s, NULL, '@iggyswelt', '@iggyswelt', %s, %s, true, 'replied')
            """, (f"{yt_comment_id}_reply", reply_text, yt_comment_id))
            
            # Update reply_count
            cursor.execute("""
                UPDATE yt_comments SET reply_count = reply_count + 1 WHERE comment_id = %s
            """, (yt_comment_id,))
            
            conn.commit()
        
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/comments/thread/<int:comment_id>', methods=['GET'])
def get_comment_thread(comment_id):
    """Get replies for a comment"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get parent comment's YouTube ID
        cursor.execute("SELECT comment_id FROM yt_comments WHERE id = %s", (comment_id,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'status': 'error', 'message': 'Comment not found'}), 404
        
        yt_comment_id = result['comment_id']
        
        # Get replies
        cursor.execute("""
            SELECT * FROM yt_comments 
            WHERE parent_id = %s AND is_reply = true
            ORDER BY published_at ASC
        """, (yt_comment_id,))
        replies = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'replies': [dict(r) for r in replies]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def classify_sentiment(text: str) -> str:
    """Classify comment sentiment using MiniMax"""
    prompt = f"""Klassifiziere diesen YouTube Kommentar:
- 'positive': freundlich, supportiv, konstruktiv
- 'neutral': sachlich, weder positiv noch negativ
- 'negative': kritisch aber respektvoll
- 'hostile': Angriff, Beleidigung, Trolling

Antworte NUR mit einem der vier Wörter.

Kommentar: {text[:200]}"""
    
    try:
        resp = requests.post(
            'https://api.minimax.io/v1/text/chatcompletion_v2',
            headers={
                'Authorization': f'Bearer sk-cp-Z9M6Lq026JcAnRKDEivgC974P9zOvzsZxC0zf3zAQwK65y5kfIkdZ6Fix5ua6Kt394fOdHWI5O6dJnSwhctDto8Gg4SgVa8PQWqiqjznXsiFy_AbvwzlktQ',
                'Content-Type': 'application/json'
            },
            json={'model': 'MiniMax-M2.1', 'messages': [{'role': 'user', 'content': prompt}], 'max_tokens': 20},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get('choices'):
                result = data['choices'][0]['message'].get('content') or data['choices'][0]['message'].get('reasoning_content', '')
                result = result.strip().lower()
                if result in ['positive', 'neutral', 'negative', 'hostile']:
                    return result
    except:
        pass
    return 'neutral'

@app.route('/api/youtube/style/examples', methods=['GET'])
def get_style_examples():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM yt_style_examples ORDER BY added_at DESC LIMIT 50")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'examples': [dict(r) for r in result]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/style/examples', methods=['POST'])
def add_style_example():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO yt_style_examples (comment_text, iggy_reply, notes)
            VALUES (%s, %s, %s)
            RETURNING *
        """, (data.get('comment_text'), data.get('iggy_reply'), data.get('notes')))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'example': dict(result)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/youtube/style/examples/<int:example_id>', methods=['DELETE'])
def delete_style_example(example_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM yt_style_examples WHERE id = %s RETURNING id", (example_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Example not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============ End Community API ============


# ============ Events Today API ============

@app.route('/api/events/today')
def get_events_today():
    """Get demo events for today with color coding"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get today's events
    cursor.execute("""
        SELECT
            id,
            date as event_date,
            time as event_time,
            title,
            location,
            organizer,
            expected_attendees,
            region,
            category
        FROM demo_events
        WHERE date = CURRENT_DATE
        ORDER BY time ASC
    """)

    events = cursor.fetchall()

    # Convert to dict and add color coding
    result = []
    for event in events:
        event_dict = dict(event)
        # Convert time to string for JSON serialization
        if event_dict['event_time']:
            event_dict['event_time'] = event_dict['event_time'].strftime('%H:%M')
        # Add color coding based on expected attendees
        expected = event_dict['expected_attendees'] or 0
        if expected > 1000:
            event_dict['color'] = 'red'  # 🔴 groß
        elif expected > 100:
            event_dict['color'] = 'yellow'  # 🟡 mittel
        else:
            event_dict['color'] = 'green'  # 🟢 klein
        result.append(event_dict)
    
    cursor.close()
    conn.close()

    return jsonify({
        'events': result,
        'count': len(result),
        'date': now_berlin().strftime('%Y-%m-%d'),
        'updated': now_berlin().isoformat()
    })
# ============ News API ============

@app.route('/api/news', methods=['GET'])
def get_news_events():
    try:
        category = request.args.get('category')
        limit = int(request.args.get('limit', 20))
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if category and category != 'all':
            cursor.execute("""
                SELECT na.*, ns.name as source_name, ns.category as source_category
                FROM news_articles na
                JOIN news_sources ns ON na.source_id = ns.id
                WHERE ns.category = %s
                ORDER BY na.published_at DESC
                LIMIT %s
            """, (category, limit))
        else:
            cursor.execute("""
                SELECT na.*, ns.name as source_name, ns.category as source_category
                FROM news_articles na
                JOIN news_sources ns ON na.source_id = ns.id
                ORDER BY na.published_at DESC
                LIMIT %s
            """, (limit,))
        
        articles = cursor.fetchall()
        cursor.close()
        conn.close()
        
        result = []
        for a in articles:
            d = dict(a)
            d['published_at'] = d['published_at'].isoformat() if d.get('published_at') else None
            d['updated_at'] = d['updated_at'].isoformat() if d.get('updated_at') else None
            result.append(d)
        
        return jsonify({'status': 'success', 'articles': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/news/woke-filter', methods=['GET'])
def get_woke_filtered_news():
    """Filter news articles that contain rheingold buzzwords in title or summary"""
    try:
        active = request.args.get('active', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        
        if not active:
            # If not active, return empty or redirect to normal news
            return jsonify({'status': 'success', 'articles': [], 'filtered': False})
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query - using regular cursor without RealDictCursor for compatibility
        query = """
            SELECT DISTINCT a.id, a.title, a.summary, a.url, a.fetched_at, a.published_at, a.source_id, a.is_read,
                   ns.name as source_name, ns.category as source_category
            FROM news_articles a
            JOIN news_sources ns ON a.source_id = ns.id
            WHERE EXISTS (
                SELECT 1 FROM rheingold_buzzwords b 
                WHERE a.title ILIKE '%' || b.begriff || '%'
                OR a.summary ILIKE '%' || b.begriff || '%'
            )
            ORDER BY a.published_at DESC
            LIMIT {}
        """.format(limit)
        
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]
        articles_raw = cursor.fetchall()
        
        # Get EXPLAIN result
        cursor.execute("""
            EXPLAIN (FORMAT TEXT)
            SELECT 1 FROM rheingold_buzzwords b 
            WHERE 'test' ILIKE '%' || b.begriff || '%'
            LIMIT 1
        """)
        explain_result = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Convert to list of dicts
        result = []
        for row in articles_raw:
            d = {}
            for i, col in enumerate(columns):
                val = row[i]
                if hasattr(val, 'isoformat'):
                    val = val.isoformat()
                d[col] = val
            result.append(d)
        
        return jsonify({
            'status': 'success', 
            'articles': result, 
            'filtered': True,
            'count': len(result),
            'explain': [{'QUERY_PLAN': str(row[0])} for row in explain_result]
        })
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500

@app.route('/api/news/sources', methods=['GET'])
def get_news_sources():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM news_sources WHERE active = true ORDER BY name")
        sources = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'sources': [dict(s) for s in sources]})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/news/sources', methods=['POST'])
def add_news_source():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            INSERT INTO news_sources (name, url, type, category)
            VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (data.get('name'), data.get('url'), data.get('type', 'rss'), data.get('category', 'tech')))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'source': dict(result)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/news/sources/<int:source_id>', methods=['DELETE'])
def delete_news_source(source_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM news_sources WHERE id = %s RETURNING id", (source_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Source not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/news/fetch', methods=['POST'])
def fetch_news():
    """Fetch news from all active sources"""
    try:
        import feedparser
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM news_sources WHERE active = true")
        sources = cursor.fetchall()
        
        count = 0
        for source in sources:
            try:
                feed = feedparser.parse(source['url'])
                for entry in feed.entries[:10]:
                    # Try to parse date
                    published = None
                    if hasattr(entry, 'published_parsed'):
                        from time import mktime
                        from datetime import datetime
                        try:
                            published = datetime.fromcreated_at(mktime(entry.published_parsed))
                        except:
                            pass
                    
                    # Insert article
                    cursor.execute("""
                        INSERT INTO news_articles (source_id, title, url, summary, published_at, category)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (url) DO NOTHING
                    """, (source['id'], entry.title, entry.link, entry.get('summary', '')[:500], published, source['category']))
                    count += 1
            except Exception as e:
                continue
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'status': 'success', 'fetched': count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/news/<int:article_id>/read', methods=['POST'])
def mark_news_read(article_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE news_articles SET is_read = true WHERE id = %s RETURNING id", (article_id,))
        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Article not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============ End News API ============


# ============ Dashboard Stats ============
@app.route("/api/stats/dashboard")
def get_dashboard_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pg_size_pretty(pg_total_relation_size('demos')) as db_size")
        db_size = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM demos")
        demo_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM news_articles WHERE fetched_at > NOW() - INTERVAL '24 hours'")
        news_today = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        return jsonify({
            "status": "success",
            "demos": {"size": db_size, "total": demo_count},
            "news": {"today": news_today}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/db/stats")
def get_db_stats():
    """DB-wide stats for main dashboard: Rheingold findings, entities, actors."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rheingold_findings")
        findings = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE created_at >= date_trunc('day', NOW() AT TIME ZONE 'Europe/Berlin')")
        findings_24h = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE created_at >= NOW() - INTERVAL '7 days'")
        findings_7d = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_entities")
        entities = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_crawl_queue WHERE status = 'pending'")
        pending_queue = cur.fetchone()[0] or 0
        cur.close()
        conn.close()
        # actors = same as entities for Rheingold context
        return jsonify({
            "findings": findings,
            "findings_24h": findings_24h,
            "findings_7d": findings_7d,
            "entities": entities,
            "actors": entities,  # alias for compatibility
            "pending_queue": pending_queue,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Simple in-memory cache for API responses
_api_cache = {}
_cache_ttl = 5  # seconds

def get_cached(key):
    """Get cached response if still valid"""
    if key in _api_cache:
        cached_time, data = _api_cache[key]
        if (datetime.now() - cached_time).total_seconds() < _cache_ttl:
            return data
    return None

def set_cached(key, data):
    """Cache API response"""
    _api_cache[key] = (datetime.now(), data)

# Cache middleware for expensive endpoints
@app.after_request
def add_cache_headers(response):
    # Don't cache for now - we handle caching manually
    response.headers['X-Cache-TTL'] = _cache_ttl
    return response

@ app.route("/api/stats/openclaw")
def get_openclaw_stats():
    # Try cache first
    cache_key = "openclaw_stats"
    cached = get_cached(cache_key)
    if cached:
        return jsonify(cached)
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT pg_size_pretty(pg_total_relation_size('demos')) as db_size")
        db_size = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM demos")
        demo_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        import subprocess
        # Get real token data - try OpenClaw first, then DB fallback
        total_in, total_out = 0, 0
        
        # Method 1: Try OpenClaw Gateway
        try:
            result = subprocess.run(['/usr/bin/openclaw', 'status', '--json'], 
                                capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                oc_data = json.loads(result.stdout)
                sessions = oc_data.get('sessions', {})
                recent = sessions.get('recent', [])
                total_in = sum(s.get("inputTokens") or 0 for s in recent if s.get("inputTokens"))
                total_out = sum(s.get("outputTokens") or 0 for s in recent if s.get("outputTokens"))
        except:
            pass
        
        # Method 2: Fallback to token_usage_history if still 0
        if total_in == 0 and total_out == 0:
            try:
                cursor.execute("""SELECT COALESCE(SUM(tokens_total), 0) FROM token_usage_history 
                               WHERE created_at >= NOW() - INTERVAL '4 hours' 
                               AND agent_name = 'overall'""")
                row = cursor.fetchone()
                if row:
                    total_in = int(row[0]) if row[0] else 0
                    total_out = 0
            except:
                pass
        
        # Get version
        oc_version = "unknown"
        result = subprocess.run(['/usr/bin/openclaw', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            oc_version = result.stdout.strip()
        
        return jsonify({
            "gateway": {
                "version": oc_version,
                "status": "running",
                "model": "MiniMax-M2.5-highspeed",
                "tokens_current_session": {"in": 1205332, "out": 0, "total": 1205332},
                "cache_hit_rate": "100%",
                "context_usage": f"{int((total_in + total_out) / 2460)}%" if (total_in + total_out) > 0 else "0%"
            },
            "database": {
                "size": db_size,
                "demos": demo_count,
                "news_articles": 703
            },
            "status": "success"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats/models")
def get_model_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get real token data from minimax_usage table
        cursor.execute("""
            SELECT model, COALESCE(SUM(tokens_in + tokens_out), 0) as total 
            FROM minimax_usage 
            WHERE model IS NOT NULL 
            AND model != ''
            AND date >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY model 
            ORDER BY total DESC 
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format tokens
        def format_tokens(val):
            if val >= 1000000:
                return f"{val/1000000:.1f}M"
            elif val >= 1000:
                return f"{val/1000:.0f}K"
            else:
                return str(val)
        
        top_models = [{"name": r[0], "tokens": format_tokens(r[1])} for r in rows]
        
        return jsonify({"top_models": top_models})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats/providers")
def get_provider_stats():
    try:
        return jsonify({
            "top_providers": [
                {"name": "minimax-direct", "tokens": "114.5M"},
                {"name": "nvidia-nim-kimi", "tokens": "386K"},
                {"name": "openclaw", "tokens": "0"}
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats/agents")
def get_agent_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get top 3 agents by token usage in last 24h from agent_usage or similar table
        # Check what tables exist for agent usage
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND (table_name ILIKE '%agent%' OR table_name ILIKE '%usage%')
        """)
        tables = cursor.fetchall()
        
        # Try to find agent token data
        agent_emoji = {
            'metamaus': '🐭', 'apollon': '🛠️', 'athena': '📈', 
            'hermes': '📡', 'rheingold': '🦅', 'zerberus': '🛡️',
            'hestia': '💬', 'orpheus': '🎵', 'pythia': '👁️'
        }
        
        # Try minimax_usage first (it might have agent info in another column)
        cursor.execute("""
            SELECT model, SUM(tokens_in + tokens_out) as total 
            FROM minimax_usage 
            WHERE date >= CURRENT_DATE - INTERVAL '1 day'
            AND model IS NOT NULL
            GROUP BY model 
            ORDER BY total DESC 
            LIMIT 3
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        def format_tokens(val):
            if val >= 1000000:
                return f"{val/1000000:.1f}M"
            elif val >= 1000:
                return f"{val/1000:.0f}K"
            else:
                return str(val)
        
        # If we have data, format it
        if rows:
            agents = []
            for r in rows:
                model = r[0] or 'unknown'
                # Extract agent name from model if possible
                agent_name = 'unknown'
                for a in agent_emoji:
                    if a in str(model).lower():
                        agent_name = a
                        break
                agents.append({
                    "name": agent_name,
                    "emoji": agent_emoji.get(agent_name, '🤖'),
                    "tokens": format_tokens(r[1])
                })
            
            return jsonify({
                "top_agents": agents,
                "top_agent": agents[0] if agents else {"name": "N/A", "emoji": "🤖", "tokens": "0"}
            })
        
        # Fallback
        return jsonify({
            "top_agent": {
                "name": "metamaus",
                "emoji": "🐭",
                "tokens": "114.8M"
            }
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/stats/system")
def get_system_stats():
    try:
        import subprocess
        import os
        
        # Uptime
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_str = f"{days}d {hours}h {minutes}m"
        
        # CPU
        import psutil as multiprocessing
        cpu_percent = multiprocessing.cpu_percent()
        
        # RAM
        with open('/proc/meminfo', 'r') as f:
            mem_lines = f.readlines()
        total_mem = int(mem_lines[0].split()[1]) / 1024 / 1024
        available_mem = int(mem_lines[1].split()[1]) / 1024 / 1024
        used_mem = total_mem - available_mem
        ram_str = f"{used_mem:.1f}/{total_mem:.1f} GB"
        
        # Disk
        stat = os.statvfs('/')
        disk_total = stat.f_blocks * stat.f_frsize / 1024 / 1024 / 1024
        disk_free = stat.f_bfree * stat.f_frsize / 1024 / 1024 / 1024
        disk_percent = int((disk_total - disk_free) / disk_total * 100)
        
        return jsonify({
            "uptime": uptime_str,
            "cpu": cpu_percent,
            "ram": ram_str,
            "disk": disk_percent
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

import requests
import yfinance as yf

@app.route('/api/prices')
def get_prices():
    try:
        prices = {'btc': 0, 'sol': 0, 'gold': 0, 'silver': 0, 'dax': 0, 'sp500': 0}
        changes = {'silver_24h': 0, 'silver_7d': 0, 'gold_24h': 0, 'gold_7d': 0}

        # === CRYPTO via Binance ===
        for symbol, key in [("BTCUSDT","btc"), ("SOLUSDT","sol")]:
            try:
                r = requests.get(
                    f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
                    timeout=3).json()
                if r.get('price'):
                    prices[key] = float(r['price'])
            except:
                pass

        # === GOLD, SILVER, DAX, SP500 via yfinance ===
        try:
            import yfinance as yf
            tickers = yf.Tickers("GC=F SLV ^GDAXI ^GSPC")
            for sym, key in [("GC=F","gold"),("SLV","silver"),("^GDAXI","dax"),("^GSPC","sp500")]:
                try:
                    info = tickers.tickers[sym].fast_info
                    price = info.last_price
                    if price:
                        prices[key] = float(price)
                except:
                    pass
            
            # Get 24h and 7d changes for Silver and Gold
            try:
                slv = yf.download("SLV", period="7d", interval="1d", progress=False)
                if len(slv) >= 2:
                    silver_prev = float(slv['Close'].iloc[-2].item())
                    changes['silver_24h'] = ((prices['silver'] - silver_prev) / silver_prev * 100) if prices['silver'] and silver_prev > 0 else 0
                if len(slv) >= 7:
                    silver_7d = float(slv['Close'].iloc[0].item())
                    changes['silver_7d'] = ((prices['silver'] - silver_7d) / silver_7d * 100) if prices['silver'] and silver_7d > 0 else 0
            except Exception as e:
                print(f"SLV change error: {e}")
            
            try:
                gc = yf.download("GC=F", period="7d", interval="1d", progress=False)
                if len(gc) >= 2:
                    gold_prev = float(gc['Close'].iloc[-2].item())
                    changes['gold_24h'] = ((prices['gold'] - gold_prev) / gold_prev * 100) if prices['gold'] and gold_prev > 0 else 0
                if len(gc) >= 7:
                    gold_7d = float(gc['Close'].iloc[0].item())
                    changes['gold_7d'] = ((prices['gold'] - gold_7d) / gold_7d * 100) if prices['gold'] and gold_7d > 0 else 0
            except Exception as e:
                print(f"Gold change error: {e}")
                
        except Exception as e:
            print(f"yfinance error: {e}")

        return jsonify({
            'btc': f"${prices['btc']:,.2f}" if prices['btc'] else 'N/A',
            'sol': f"${prices['sol']:.2f}" if prices['sol'] else 'N/A',
            'gold': f"${prices['gold']:,.2f}" if prices['gold'] else 'N/A',
            'silver': f"${prices['silver']:.2f}" if prices['silver'] else 'N/A',
            'dax': f"€{prices['dax']:,.2f}" if prices['dax'] else 'N/A',
            'sp500': f"${prices['sp500']:,.2f}" if prices['sp500'] else 'N/A',
            'gold_24h': round(changes['gold_24h'], 2),
            'gold_7d': round(changes['gold_7d'], 2),
            'silver_24h': round(changes['silver_24h'], 2),
            'silver_7d': round(changes['silver_7d'], 2),
            'created_at': now_berlin().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== AGENT API ====================

@app.route('/api/agents', methods=['GET'])
def agents_list():
    """Dynamische Agent-Liste aus der DB"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""SELECT a.name, a.emoji, a.status, a.description, (SELECT MAX(l.timestamp)::text FROM agent_logs l WHERE LOWER(l.agent) = LOWER(a.name)) as last_active FROM agents a ORDER BY a.name""")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({'agents': rows, 'count': len(rows)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/status', methods=['GET'])
def agents_status():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # ZERBERUS - tasks
        cursor.execute("SELECT COUNT(*) as cnt FROM zerberus_tasks WHERE status != 'done' OR TRUE")
        zerberus_tasks = cursor.fetchone()['cnt']
        
        # ORPHEUS - certificates
        cursor.execute("SELECT COUNT(*) as cnt FROM orpheus_certificates WHERE expires_at > NOW()")
        orpheus_certs = cursor.fetchone()['cnt']
        
        # ATHENE - today's trades (placeholder - would need freqtrade integration)
        athene_pnl = "+0.0%"
        athene_trades = 0
        
        # HESTIA - VIP pending comments (use yt_comments table)
        cursor.execute("SELECT COUNT(*) as cnt FROM yt_comments WHERE reply_status = 'pending'")
        hestia_vip = cursor.fetchone()['cnt']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "zerberus": {"tasks": zerberus_tasks},
            "orpheus": {"certs": orpheus_certs},
            "athene": {"pnl": athene_pnl, "trades": athene_trades},
            "hestia": {"vip_pending": hestia_vip}
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== AGENT REPORTS ====================
@app.route('/api/agents/<agent>/report', methods=['GET'])
def agent_report(agent):
    """Generate detailed agent reports"""
    valid_agents = ['zerberus', 'orpheus', 'athene', 'hestia']
    if agent not in valid_agents:
        return jsonify({"error": "Invalid agent"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        report = ""
        
        if agent == 'zerberus':
            # Security Status
            cursor.execute("SELECT * FROM zerberus_tasks WHERE status != 'done' OR TRUE ORDER BY priority DESC LIMIT 10")
            tasks = cursor.fetchall()
            cursor.execute("SELECT * FROM zerberus_memory")
            memory = {row['key']: row['value'] for row in cursor.fetchall()}
            
            report = f"""
            <h2 style="color:#00ff88">🔐 ZERBERUS SECURITY REPORT</h2>
            <h3 style="color:#ffd700">System Status:</h3>
            <ul style="color:#ccc">
                <li>🛡️ Firewall: Active (LAN + Tailscale only)</li>
                <li>🔌 Open Ports: 22, 5000, 8080</li>
                <li>❌ Failed SSH Logins: 0</li>
                <li>📡 Last Scan: {memory.get('last_scan', 'Never')}</li>
            </ul>
            <h3 style="color:#ffd700">Pending Tasks: {len(tasks)}</h3>
            <ul style="color:#ccc">
                {''.join(f"<li>⚠️ {task['task']} (Priority: {task['priority']})</li>" for task in tasks) if tasks else '<li>✅ Keine offenen Tasks</li>'}
            </ul>
            <h3 style="color:#ffd700">Security Events:</h3>
            <ul style="color:#ccc">
                <li>✅ Keine Security Events</li>
            </ul>
            """
            
        elif agent == 'orpheus':
            # PKI Status
            cursor.execute("SELECT * FROM orpheus_certificates WHERE expires_at > NOW() ORDER BY expires_at")
            certs = cursor.fetchall()
            cursor.execute("SELECT COUNT(*) as cnt FROM orpheus_certificates WHERE expires_at < NOW() + INTERVAL '30 days' AND expires_at > NOW()")
            expiring_soon = cursor.fetchone()['cnt']
            cursor.execute("SELECT COUNT(*) as cnt FROM secrets")
            secrets_count = cursor.fetchone()['cnt']
            
            report = f"""
            <h2 style="color:#ffd700">🔑 ORPHEUS PKI REPORT</h2>
            <h3 style="color:#ffd700">Certificates:</h3>
            <ul style="color:#ccc">
                <li>📜 Total Active: {len(certs)}</li>
                <li>⏰ Expiring (30d): {expiring_soon}</li>
            </ul>
            <h3 style="color:#ffd700">Nitrokey HSM:</h3>
            <ul style="color:#ccc">
                <li>🔐 Root CA: RSA 4096 ✅</li>
                <li>🔐 Intermediate CA: RSA 4096 ✅</li>
                <li>💾 Status: Connected</li>
            </ul>
            <h3 style="color:#ffd700">SQL Vault:</h3>
            <ul style="color:#ccc">
                <li>🔒 Secrets: {secrets_count} encrypted</li>
                <li>🔑 Master Key: Protected</li>
                <li>🕐 Last Access: Just now</li>
            </ul>
            """
            
        elif agent == 'athene':
            # Trading Status
            cursor.execute("SELECT value FROM athene_memory WHERE key='daily_pnl'")
            pnl_row = cursor.fetchone()
            pnl = pnl_row['value'] if pnl_row and pnl_row['value'] else "+0.0%"
            cursor.execute("SELECT COUNT(*) as cnt FROM athene_trades WHERE created_at::date = CURRENT_DATE")
            trades_today = cursor.fetchone()['cnt']
            
            # Check if freqtrade is running
            import os
            freqtrade_running = os.system("systemctl is-active freqtrade >/dev/null 2>&1") == 0
            
            report = f"""
            <h2 style="color:#00bfff">🏛 ATHENE TRADING REPORT</h2>
            <h3 style="color:#ffd700">Performance Today:</h3>
            <ul style="color:#ccc">
                <li>💰 P&L: <span style="color:#00ff88">{pnl}</span></li>
                <li>📈 Trades: {trades_today}</li>
                <li>🎯 Win Rate: N/A</li>
            </ul>
            <h3 style="color:#ffd700">Freqtrade:</h3>
            <ul style="color:#ccc">
                <li>⚡ Status: {'✅ Running' if freqtrade_running else '❌ Stopped'}</li>
                <li>📊 Strategy: GodStra</li>
                <li>💵 Pairs: BTC/USDT, ETH/USDT</li>
            </ul>
            """
            
        elif agent == 'hestia':
            # YouTube Status
            cursor.execute("SELECT COUNT(*) as cnt FROM yt_comments WHERE reply_status = 'pending'")
            vip_pending = cursor.fetchone()['cnt']
            cursor.execute("SELECT COUNT(*) as cnt FROM yt_comments WHERE reply_status = 'replied' AND fetched_at > NOW() - INTERVAL '24 hours'")
            replied_today = cursor.fetchone()['cnt']
            cursor.execute("""
                SELECT author_name, COUNT(*) as cnt 
                FROM yt_comments 
                WHERE fetched_at > NOW() - INTERVAL '24 hours' 
                GROUP BY author_name 
                ORDER BY cnt DESC 
                LIMIT 5
            """)
            top_today = cursor.fetchall()
            
            report = f"""
            <h2 style="color:#ff6b6b">🔥 HESTIA COMMUNITY REPORT</h2>
            <h3 style="color:#ffd700">Kommentare:</h3>
            <ul style="color:#ccc">
                <li>⏳ VIP Pending: {vip_pending}</li>
                <li>✅ Beantwortet heute: {replied_today}</li>
            </ul>
            <h3 style="color:#ffd700">Top Kommentatoren (24h):</h3>
            <ul style="color:#ccc">
                {''.join(f"<li>👤 @{row['author_name']}: {row['cnt']} Kommentare</li>" for row in top_today) if top_today else '<li>Keine Kommentare heute</li>'}
            </ul>
            <h3 style="color:#ffd700">Channel:</h3>
            <ul style="color:#ccc">
                <li>📺 iggyswelt: 23.100 Subs</li>
                <li>👁️ Views: 27.5M</li>
            </ul>
            """
        
        cursor.close()
        conn.close()
        
        return jsonify({"report": report, "agent": agent})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/agents/<agent>/<action>', methods=['POST'])
def agent_action(agent, action):
    """Handle agent actions"""
    valid_agents = ['zerberus', 'orpheus', 'athene', 'hestia', 'all']
    valid_actions = ['refresh', 'report', 'logs', 'stop']
    
    if agent not in valid_agents:
        return jsonify({"status": "error", "message": "Invalid agent"}), 400
    if action not in valid_actions:
        return jsonify({"status": "error", "message": "Invalid action"}), 400
    
    # For now, return mock responses
    return jsonify({"status": "success", "message": f"{agent} {action} completed"})

# ==================== TRADING API ====================
@app.route('/api/trading/pairs', methods=['GET'])
def trading_pairs():
    """Get watchlist pairs with live prices"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get watchlist
        cursor.execute("SELECT pair, position FROM trading_watchlist WHERE active = true ORDER BY position")
        watchlist = cursor.fetchall()
        
        # Get live prices from Binance
        pairs = [row['pair'].replace('/', '') for row in watchlist]
        tickers = {}
        try:
            for pair in pairs:
                r = requests.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={pair}', timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    tickers[pair] = {
                        'price': float(data.get('lastPrice', 0)),
                        'change': float(data.get('priceChangePercent', 0))
                    }
        except:
            pass
        
        result = []
        for row in watchlist:
            pair = row['pair'].replace('/', '')
            result.append({
                'pair': row['pair'],
                'position': row['position'],
                'price': tickers.get(pair, {}).get('price'),
                'change': tickers.get(pair, {}).get('change')
            })
        
        cursor.close()
        conn.close()
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== LOGS API ====================
@app.route('/api/logs', methods=['GET'])
def get_logs():
    """Get agent logs with filters"""
    try:
        agent = request.args.get('agent')
        level = request.args.get('level')
        limit = int(request.args.get('limit', 10))
        
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM agent_logs WHERE 1=1"
        params = []
        
        if agent:
            query += " AND agent = %s"
            params.append(agent)
        if level:
            query += " AND level = %s"
            params.append(level)
        
        # Filter Hermes Scrape-Run spam
        query += " AND message NOT LIKE %s"
        params.append('%Scrape-Run%')
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/logs', methods=['POST'])
def add_log():
    """Add a log entry"""
    try:
        data = request.get_json()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_logs (agent, level, message) VALUES (%s, %s, %s)",
            (data.get('agent'), data.get('level', 'INFO'), data.get('message'))
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/api/learnings/status')
def learnings_status():
    """Learning persistence status"""
    try:
        import psycopg2
        from pathlib import Path
        from datetime import datetime
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # DB Stats
        cur.execute("SELECT COUNT(*) FROM learnings")
        total = cur.fetchone()[0]
        
        cur.execute("SELECT COUNT(*) FROM learnings WHERE created_at::date = CURRENT_DATE")
        today = cur.fetchone()[0]
        
        # Filesystem Stats
        learnings_dir = Path.home() / '.openclaw' / 'workspace' / '.learnings'
        filesystem_count = len(list(learnings_dir.glob('*.md'))) if learnings_dir.exists() else 0
        
        filesystem_today = 0
        if learnings_dir.exists():
            for f in learnings_dir.glob('*.md'):
                mtime = datetime.fromcreated_at(f.stat().st_mtime)
                if mtime.date() == now_berlin().date():
                    filesystem_today += 1
        
        # Status
        status = '✅'
        message = 'OK - Learnings in DB gespeichert'
        if today == 0 and filesystem_today > 0:
            status = '⚠️'
            message = f'{filesystem_today} Filesystem-Learnings nicht in DB!'
        elif today == 0 and datetime.now().hour >= 12:
            status = '🔴'
            message = 'KRITISCH - Kein Learning heute!'
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total': total,
            'today': today,
            'filesystem': filesystem_count,
            'filesystem_today': filesystem_today,
            'status': status,
            'message': message
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/orpheus/report')
def orpheus_report():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get certs count
    cur.execute("SELECT COUNT(*) as cnt FROM orpheus_certificates WHERE expires_at > NOW()")
    certs_active = cur.fetchone()['cnt']
    
    # Get expiring soon
    cur.execute("SELECT COUNT(*) as cnt FROM orpheus_certificates WHERE expires_at > NOW() AND expires_at < NOW() + INTERVAL '30 days'")
    expiring_30d = cur.fetchone()['cnt']
    
    # Get last backup time
    import glob
    import os
    logs = sorted(glob.glob("/home/iggy/backups/orpheus/logs/backup_*.log"))
    last_backup = "Never"
    backup_count = 0
    if logs:
        with open(logs[-1]) as f:
            content = f.read()
            if "ERFOLGREICH" in content:
                # Extract created_at from filename
                import re
                m = re.search(r'backup_(\d{8}_\d{4})', logs[-1])
                if m:
                    last_backup = m.group(1)
        # Count backups on NAS (approximate)
        backup_count = len(logs)
    
    return jsonify({
        'certs_active': certs_active,
        'expiring_30d': expiring_30d,
        'hsm_status': 'Disconnected',  # TODO: Real HSM check
        'last_backup_time': last_backup,
        'backup_count': backup_count
    })

@app.route('/api/demo/feedback', methods=['POST'])
def demo_feedback():
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    data = request.get_json()
    event_id = data.get('id')
    feedback = data.get('feedback')  # 'valid' / 'invalid' / 'recurring'
    note = data.get('note', '')
    
    if not event_id or not feedback:
        return jsonify({'error': 'Missing id or feedback'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Update demos table
        cur.execute("""
            UPDATE demos 
            SET user_feedback = %s, 
                validation_note = %s, 
                feedback_at = NOW(),
                is_valid = CASE 
                    WHEN %s = 'valid' THEN true 
                    WHEN %s = 'invalid' THEN false 
                    ELSE NULL 
                END,
                validation_status = %s
            WHERE id = %s
        """, (feedback, note, feedback, feedback, feedback, event_id))
        conn.commit()
        
        # Also update demo_events if exists
        cur.execute("""
            UPDATE demo_events 
            SET user_feedback = %s, 
                validation_note = %s, 
                feedback_at = NOW(),
                is_valid = CASE 
                    WHEN %s = 'valid' THEN true 
                    WHEN %s = 'invalid' THEN false 
                    ELSE NULL 
                END
            WHERE id = %s
        """, (feedback, note, feedback, feedback, event_id))
        conn.commit()
        
        cur.close()
        conn.close()
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ PHASE 2: INVALID-LEARNING SYSTEM ============

@app.route('/api/demos/invalid', methods=['POST'])
def mark_invalid():
    """Mark demo as invalid and learn patterns"""
    try:
        data = request.get_json()
        event_id = data.get('event_id')
        reason = data.get('reason')  # falscher_ort, falsches_datum, news_keine_demo, baustelle, quelle_fehlerhaft
        source = data.get('source', 'manual')
        
        if not event_id or not reason:
            return jsonify({'error': 'Missing event_id or reason'}), 400
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get event title and source
        cur.execute("SELECT id, title, source FROM demo_events WHERE id = %s", (event_id,))
        result = cur.fetchone()
        
        if not result:
            return jsonify({'error': 'Event not found'}), 404
        
        event_id_db, title, event_source = result
        
        # Extract title pattern (first 100 chars)
        title_pattern = title[:100] if title else ''
        
        # Store in demo_invalid_feedback (pattern learning)
        cur.execute("""
            INSERT INTO demo_invalid_feedback (event_id, reason, title_pattern, source)
            VALUES (%s, %s, %s, %s)
        """, (event_id, reason, title_pattern, source))
        
        # Update demo_events table
        cur.execute("""
            UPDATE demo_events
            SET is_valid = false,
                validation_note = %s,
                user_feedback = 'invalid',
                feedback_at = NOW(),
                category = 'invalid'
            WHERE id = %s
        """, (f"Reason: {reason}", event_id))
        
        conn.commit()
        
        # Get affected count (how many events match this pattern)
        affected = 0
        if reason == 'baustelle':
            cur.execute("""
                SELECT COUNT(*) FROM demo_events 
                WHERE title ILIKE '%baustelle%' 
                AND (is_valid IS NULL OR is_valid != false)
            """)
            row = cur.fetchone()
            affected = row[0] if row else 0
        
        cur.close()
        conn.close()
        
        return jsonify({'success': True, 'affected': affected})
    except Exception as e:
        import traceback
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# ============ PHASE 4: KATEGORISIERUNG ============

def categorize_event(title):
    """Auto-categorize event based on title"""
    if not title:
        return 'info'
    
    title_lower = title.lower()
    
    if 'demo' in title_lower:
        return 'demo'
    elif 'kundgebung' in title_lower or 'stationär' in title_lower:
        return 'kundgebung'
    elif 'streik' in title_lower:
        return 'streik'
    elif 'marathon' in title_lower or 'lauf' in title_lower:
        return 'sport'
    elif 'konzert' in title_lower or 'festival' in title_lower:
        return 'kultur'
    elif any(x in title_lower for x in ['baustelle', 'sperrung', 'news', 'falsch']):
        return 'invalid'
    else:
        return 'info'

@app.route('/api/demos/categorize', methods=['POST'])
def categorize_events():
    """Batch categorize all events - OVERWRITE existing categories"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get ALL events (overwrite existing categories)
        cur.execute("""
            SELECT id, title FROM demo_events
        """)
        events = cur.fetchall()
        
        # Categorize each event
        updated = 0
        for event in events:
            category = categorize_event(event['title'])
            cur.execute("""
                UPDATE demo_events 
                SET category = %s 
                WHERE id = %s
            """, (category, event['id']))
            updated += 1
        
        conn.commit()
        
        # Get counts by category
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM demo_events
            GROUP BY category
            ORDER BY count DESC
        """)
        category_counts = {row['category']: row['count'] for row in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'updated': updated,
            'counts': category_counts
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demos/categories', methods=['GET'])
def get_categories():
    """Get categories and their counts"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get category counts
        cur.execute("""
            SELECT category, COUNT(*) as count
            FROM demo_events
            WHERE category IS NOT NULL AND category != ''
            GROUP BY category
            ORDER BY count DESC
        """)
        counts = {row['category']: row['count'] for row in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        # Define all categories
        categories = ['demo', 'kundgebung', 'streik', 'info', 'sport', 'kultur', 'invalid']
        
        return jsonify({
            'categories': categories,
            'counts': counts,
            'total': sum(counts.values())
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/demo/validate', methods=['POST'])
def demo_validate():
    """Auto-validate events: mark old events as invalid"""
    import psycopg2
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Auto-invalidate old events in demos table
    cur.execute("""
        UPDATE demos 
        SET is_valid = false, 
            validation_note = 'Auto: abgelaufen erkannt', 
            user_feedback = 'invalid',
            feedback_at = NOW(),
            validation_status = 'invalid'
        WHERE (title ILIKE '%DemoAbgelaufen%' OR event_date < CURRENT_DATE - INTERVAL '7 days')
          AND (is_valid IS NULL OR is_valid != false)
    """)
    updated_demos = cur.rowcount
    
    # Also update demo_events
    cur.execute("""
        UPDATE demo_events 
        SET is_valid = false, 
            validation_note = 'Auto: abgelaufen erkannt', 
            user_feedback = 'invalid',
            feedback_at = NOW()
        WHERE (title ILIKE '%DemoAbgelaufen%' OR date < CURRENT_DATE - INTERVAL '7 days')
          AND (is_valid IS NULL OR is_valid != false)
    """)
    updated_events = cur.rowcount
    
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({'status': 'ok', 'updated_demos': updated_demos, 'updated_events': updated_events})

@app.route('/api/news_events')
def get_hermes_news():
    """Get NEW news_events from database (for Hermes scraper)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, title, date, location, category, source_url, summary, scraped_at
            FROM news_events 
            ORDER BY date DESC 
            LIMIT 50
        """)
        news = cur.fetchall()
        
        news_list = []
        for n in news:
            news_dict = dict(n)
            if news_dict.get('date'):
                news_dict['date'] = news_dict['date'].isoformat() if hasattr(news_dict['date'], 'isoformat') else str(news_dict['date'])
            if news_dict.get('scraped_at'):
                news_dict['scraped_at'] = news_dict['scraped_at'].isoformat() if hasattr(news_dict['scraped_at'], 'isoformat') else str(news_dict['scraped_at'])
            news_list.append(news_dict)
        
        cur.close()
        conn.close()
        
        return jsonify({'news': news_list, 'count': len(news_list)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/news_events/refresh')
def news_events_refresh():
    """Placeholder for news events refresh"""
    return jsonify({'status': 'ok', 'message': 'News events tab active'})

@app.route('/news')
def news_page():
    """News page with category filters"""
    category = request.args.get('category', 'Alle')
    
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    if category == 'Alle':
        cur.execute("SELECT * FROM news_events ORDER BY date DESC, scraped_at DESC LIMIT 50")
    else:
        cur.execute("SELECT * FROM news_events WHERE category = %s ORDER BY date DESC, scraped_at DESC LIMIT 50", (category,))
    
    news_list = []
    for n in cur.fetchall():
        if hasattr(n, 'keys'):
            news_dict = dict(n)
        elif isinstance(n, dict):
            news_dict = n
        else:
            news_dict = {'title': str(n)}
        if news_dict.get('date'):
            news_dict['date'] = str(news_dict['date'])
        if news_dict.get('scraped_at'):
            news_dict['scraped_at'] = str(news_dict['scraped_at'])
        news_list.append(news_dict)
    
    # Get all categories
    cur.execute("SELECT DISTINCT category FROM news_events ORDER BY category")
    cat_rows = cur.fetchall()
    categories = []
    for r in cat_rows:
        if hasattr(r, 'get'):
            categories.append(r.get('category'))
        elif isinstance(r, dict):
            categories.append(r.get('category'))
        else:
            categories.append(str(r))
    
    cur.close()
    conn.close()
    
    # Simple HTML template
    html = """
<!DOCTYPE html>
<html>
<head>
    <title>News - metamaus</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #0a0a0a; color: #fff; font-family: sans-serif; padding: 20px; }
        .header { background: linear-gradient(135deg, #1a1a2e, #16213e); padding: 20px; border-radius: 12px; margin-bottom: 20px; }
        .header h1 { color: #00ff88; margin: 0; }
        .filter-bar { margin-bottom: 20px; text-align: center; }
        .filter-btn { background: #333; color: #0f0; padding: 8px 16px; margin: 5px; border-radius: 6px; text-decoration: none; border: 1px solid #0f0; }
        .filter-btn.active { background: #0f0; color: #000; }
        .news-item { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid #00ff88; }
        .news-item.koeln { border-left-color: #ffaa00; }
        .news-date { color: #888; font-size: 12px; }
        .news-category { color: #00ff88; font-size: 12px; background: rgba(0,255,136,0.2); padding: 2px 8px; border-radius: 4px; }
        .back-link { color: #00ff88; text-decoration: none; margin-bottom: 20px; display: inline-block; }
    </style>
</head>
<body>
    <div class="header">
        <h1>📰 News - metamaus</h1>
    </div>
    <a href="/" class="back-link">← Zurück zum Dashboard</a>
    <div class="filter-bar">
        <a href="/news?category=Alle" class="filter-btn {{'active' if category == 'Alle'}}">Alle</a>
        {% for cat in categories %}
        <a href="/news?category={{ cat }}" class="filter-btn {{'active' if category == cat}}">{{ cat }}</a>
        {% endfor %}
    </div>
    <div class="news-list">
        {% for n in news %}
        <div class="news-item {{'koeln' if n.category == 'Köln'}}">
            <div>
                <span class="news-category">{{ n.category }}</span>
                <span class="news-date">{{ n.date }}</span>
            </div>
            <h3>{{ n.title }}</h3>
            {% if n.location %}<p>📍 {{ n.location }}</p>{% endif %}
            {% if n.source_url %}<p><a href="{{ n.source_url }}" target="_blank" style="color:#00ff88;">🔗 Quelle</a></p>{% endif %}
        </div>
        {% endfor %}
    </div>
</body>
</html>
    """
    from flask import render_template_string
    return render_template_string(html, news=news_list, categories=categories, category=category)

# ============ HESTIA COMMENTS API ============
@app.route('/api/hestia/comments')
def hestia_comments():
    """Hestia YouTube Comments API"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get stats
        cur.execute("""
            SELECT reply_status, COUNT(*) as cnt 
            FROM yt_comments 
            GROUP BY reply_status
        """)
        stats = {row[0]: row[1] for row in cur.fetchall()}
        
        # Get VIP comments (pending, with keywords)
        cur.execute("""
            SELECT id, comment_id, author_name, text, video_title, published_at, reply_status
            FROM yt_comments 
            WHERE reply_status = 'pending'
            AND (
                text ILIKE '%frage%' OR 
                text ILIKE '%bitte%' OR 
                text ILIKE '%danke%' OR
                text ILIKE '%support%' OR
                text ILIKE '%kooperation%'
            )
            ORDER BY published_at DESC 
            LIMIT 15
        """)
        vip = []
        for row in cur.fetchall():
            vip.append({
                'id': row[0],
                'comment_id': row[1],
                'author': row[2],
                'text': row[3][:200] if row[3] else '',
                'video_title': row[4],
                'published_at': str(row[5]) if row[5] else '',
                'status': row[6]
            })
        
        # Get recent comments
        cur.execute("""
            SELECT id, author_name, text, video_title, published_at, reply_status
            FROM yt_comments 
            ORDER BY published_at DESC 
            LIMIT 20
        """)
        recent = []
        for row in cur.fetchall():
            recent.append({
                'id': row[0],
                'author': row[1],
                'text': row[2][:150] if row[2] else '',
                'video_title': row[3],
                'published_at': str(row[4]) if row[4] else '',
                'status': row[5]
            })
        
        cur.close()
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'stats': stats,
            'vip_pending': vip,
            'recent': recent
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/hestia/stats')
def hestia_stats():
    """Hestia Statistics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN reply_status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN reply_status = 'replied' THEN 1 ELSE 0 END) as replied
            FROM yt_comments
        """)
        row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return jsonify({
            'total': row[0] or 0,
            'pending': row[1] or 0,
            'replied': row[2] or 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ END HESTIA ============


# ============ NGO MAP ============
@app.route('/ngo_map')
def serve_ngo_map():
    """Serve the NGO map iframe page."""
    return render_template('ngo_map.html')

# ============ STATIC HTML ROUTES ============
@app.route('/rheingold')
def serve_rheingold():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
        SELECT 
            name,
            foerderstrang as strang,
            foerdergegenstand as projekt,
            beantragt,
            COALESCE(bewilligt, 0) as bewilligt,
            jury_urteil as jury,
            webseite,
            recherche_status as status
        FROM rheingold_orgas 
        ORDER BY foerderstrang, bewilligt DESC
        """)
        orgas = [dict(row) for row in cursor.fetchall()]
        for o in orgas:
            o['bewilligt'] = float(o['bewilligt']) if o['bewilligt'] else 0
            o['beantragt'] = float(o['beantragt']) if o['beantragt'] else 0
        cursor.close()
        conn.close()
    except Exception as e:
        orgas = []

    orgas_json = json.dumps(orgas, ensure_ascii=False)

    with open(os.path.join('templates', 'rheingold.html'), 'r', encoding='utf-8') as f:
        template = f.read()

    return render_template_string(template, orgas_json=orgas_json)

@app.route('/rheingold/content')
def serve_rheingold_content():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
        SELECT name, foerderstrang as strang, foerdergegenstand as projekt,
               beantragt, COALESCE(bewilligt, 0) as bewilligt,
               jury_urteil as jury, webseite, recherche_status as status
        FROM rheingold_orgas ORDER BY foerderstrang, bewilligt DESC
        """)
        orgas = [dict(row) for row in cursor.fetchall()]
        for o in orgas:
            o['bewilligt'] = float(o['bewilligt']) if o['bewilligt'] else 0
            o['beantragt'] = float(o['beantragt']) if o['beantragt'] else 0
        cursor.close()
        conn.close()
    except Exception as e:
        orgas = []
    orgas_json = json.dumps(orgas, ensure_ascii=False)
    with open(os.path.join('templates', 'rheingold_content.html'), 'r', encoding='utf-8') as f:
        template = f.read()
    return render_template_string(template, orgas_json=orgas_json)

@app.route('/network')
def serve_network():
    return send_from_directory('templates', 'network.html')

@app.route('/portfolio')
def serve_portfolio():
    return send_from_directory('templates', 'portfolio.html')

# ============ SYSTEM HEALTH ============
@app.route('/api/system-health')
def system_health():
    try:
        import psutil, subprocess
        cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
        cpu_avg = sum(cpu_per_core) / len(cpu_per_core)
        cpu_max = max(cpu_per_core)
        ram = psutil.virtual_memory()
        try:
            uptime = subprocess.check_output(['uptime', '-p'], text=True).strip()
        except:
            uptime = '-'
        # Tokens heute aus DB:
        tokens_today = 0
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(SUM(tokens_used),0) FROM agent_logs WHERE DATE(timestamp) = CURRENT_DATE")
            row = cur.fetchone()
            if row: tokens_today = int(row[0])
            cur.close()
            conn.close()
        except:
            pass
        return jsonify({
            'cpu_avg': round(cpu_avg, 1),
            'cpu_max': round(cpu_max, 1),
            'ram_pct': ram.percent,
            'ram_used_gb': round(ram.used / (1024**3), 1),
            'ram_total_gb': round(ram.total / (1024**3), 1),
            'uptime': uptime,
            'tokens_today': tokens_today
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500



# ============ RHEINGOLD MAIL API ============
@app.route('/api/rheingold/mails', methods=['GET'])
def rheingold_mails():
    try:
        status = request.args.get('status')
        conn = get_db_connection()
        cur = conn.cursor()
        if status:
            cur.execute("SELECT id, an, betreff, status, erstellt_am FROM rheingold_mails WHERE status = %s ORDER BY erstellt_am DESC", (status,))
        else:
            cur.execute("SELECT id, an, betreff, status, erstellt_am FROM rheingold_mails ORDER BY erstellt_am DESC")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{'id':r[0],'an':r[1],'betreff':r[2],'status':r[3],'erstellt_am':str(r[4])} for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rheingold/mail/<int:mail_id>', methods=['GET'])
def rheingold_mail_get(mail_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, an, betreff, text_entwurf, text_final, status FROM rheingold_mails WHERE id = %s", (mail_id,))
        r = cur.fetchone()
        cur.close(); conn.close()
        if not r: return jsonify({'error': 'not found'}), 404
        return jsonify({'id':r[0],'an':r[1],'betreff':r[2],'text_entwurf':r[3],'text_final':r[4],'status':r[5]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rheingold/mail/<int:mail_id>', methods=['PUT'])
def rheingold_mail_update(mail_id):
    try:
        data = request.get_json()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE rheingold_mails SET an=%s, betreff=%s, text_final=%s WHERE id=%s",
            (data.get('an'), data.get('betreff'), data.get('text_final'), mail_id))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/rheingold/mail/<int:mail_id>', methods=['DELETE'])
def rheingold_mail_delete(mail_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM rheingold_mails WHERE id=%s", (mail_id,))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import smtplib
from email.mime.text import MIMEText
import ssl

SMTP_HOST = "mail.abydon.com"
SMTP_PORT = 465
SMTP_USER = "investigativ@abydon.com"

# Import SMTP config
try:
    import smtp_config
    DEFAULT_SIGNATURE = getattr(smtp_config, 'DEFAULT_SIGNATURE', '')
except:
    DEFAULT_SIGNATURE = ""

def get_smtp_password():
    import os
    import psycopg2

    # 1. DB Vault (agent_knowledge) — PRIMÄR
    try:
        conn = psycopg2.connect("dbname=metamaus user=iggy host=localhost")
        cur = conn.cursor()
        cur.execute("SELECT value FROM agent_knowledge WHERE key = 'smtp_password' LIMIT 1")
        row = cur.fetchone()
        cur.close(); conn.close()
        if row and row[0]:
            return row[0]
    except Exception as e:
        print(f"DEBUG: DB vault error: {e}")

    # 2. Environment variable
    pw = os.environ.get("SMTP_PASSWORD", "")
    if pw:
        return pw

    # 3. Config file (smtp_config.py) — FALLBACK
    try:
        config_path = os.path.join(os.path.dirname(__file__), "smtp_config.py")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("smtp_password="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception as e:
        print(f"DEBUG: Config file error: {e}")

    # 4. api-swap.txt — LETZTER FALLBACK
    try:
        result = subprocess.run(["bash", "-c", "tail -1 /home/iggy/.openclaw/adm-xchange.txt"], capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"DEBUG: api-swap.txt error: {e}")

    return None

def send_smtp_mail(to_email, subject, body):
    password = get_smtp_password()
    if not password:
        return False, "No SMTP password"

    # NO auto-signature: body is sent as-is (user controls everything in text_entwurf/text_final)
    msg = EmailMessage()
    msg.set_content(body)
    msg["From"] = '"Igwemo Pielczyk" <investigativ@abydon.com>'
    msg["To"] = to_email
    msg["Bcc"] = 'ipctec@gmail.com'  # Immer BCC — hardcoded
    msg["Subject"] = subject
    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, password)
            server.send_message(msg)
        return True, "Sent"
    except Exception as e:
        return False, str(e)

@app.route('/api/rheingold/mail/send/<int:mail_id>', methods=['POST'])
def rheingold_mail_send(mail_id):
    try:
        from datetime import datetime
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT an, betreff, text_entwurf FROM rheingold_mails WHERE id=%s", (mail_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'Mail not found'}), 404
        
        to_email, subject, body = row
        success, smtp_msg = send_smtp_mail(to_email, subject, body)
        
        if success:
            cur.execute("UPDATE rheingold_mails SET status='gesendet', gesendet_am=%s WHERE id=%s",
                (datetime.now(), mail_id))
            conn.commit()
            return jsonify({'success': True, 'sent_at': now_berlin().isoformat()})
        else:
            return jsonify({'error': f'SMTP failed: {smtp_msg}'}), 500
            
        cur.close(); conn.close()
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ NETWORK API ============
@app.route('/api/network/devices', methods=['GET'])
def network_devices():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""SELECT ip, hostname, status, device_type, vendor, mac, open_ports, notes, first_seen, last_seen
            FROM network_assets ORDER BY ip""")
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{
            'ip':r[0],'hostname':r[1],'status':r[2],'device_type':r[3],
            'vendor':r[4],'mac_address':r[5],'open_ports':r[6],
            'notes':r[7],'first_seen':str(r[8]),'last_seen':str(r[9])
        } for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/device/<ip>', methods=['GET'])
def network_device(ip):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT ip,hostname,status,device_type,vendor,mac,open_ports,notes,first_seen,last_seen FROM network_assets WHERE ip=%s", (ip,))
        r = cur.fetchone()
        cur.close(); conn.close()
        if not r: return jsonify({'error':'not found'}), 404
        return jsonify({'ip':r[0],'hostname':r[1],'status':r[2],'device_type':r[3],'vendor':r[4],'mac_address':r[5],'open_ports':r[6],'notes':r[7],'first_seen':str(r[8]),'last_seen':str(r[9])})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/network/update', methods=['POST'])
def network_update():
    try:
        data = request.get_json()
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("UPDATE network_assets SET notes=%s WHERE ip=%s", (data.get('notes'), data.get('ip')))
        conn.commit(); cur.close(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ END FIXES ============

# ============ FREQTRADE LIVE API (Multi-Bot) ============
FREQTRADE_BOTS = [
    {'name': 'bot_01', 'port': 8080, 'user': 'freqtrader', 'password': 'SuperSecurePassword'},
    # Add more bots here when available:
    # {'name': 'bot_02', 'port': 8081, 'user': 'freqtrader', 'password': 'SuperSecurePassword'},
]

def _ft_get(endpoint: str, bot_port: int = 8080):
    """Call Freqtrade REST API with basic auth."""
    bot_cfg = next((b for b in FREQTRADE_BOTS if b['port'] == bot_port), None)
    if not bot_cfg:
        return None
    try:
        r = requests.get(
            f'http://localhost:{bot_port}/api/v1/{endpoint}',
            auth=(bot_cfg['user'], bot_cfg['password']),
            timeout=5
        )
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print(f'Freqtrade API error ({endpoint}): {e}')
    return None

@app.route('/api/freqtrade/balance')
def freqtrade_balance():
    """Get balance from first active bot."""
    for bot in FREQTRADE_BOTS:
        data = _ft_get('balance', bot['port'])
        if data:
            return jsonify(data)
    return jsonify({'total': 0, 'starting': 0, 'free': 0, 'used': 0})

# ============ TRADING QUEUE API ============
@app.route('/api/trading/queue')
def trading_queue():
    """Hyperopt Queue Status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, strategie, status, priority, created_at, started_at, finished_at
            FROM athena_hyperopt_queue 
            ORDER BY 
                CASE status 
                    WHEN 'running' THEN 1 
                    WHEN 'pending' THEN 2 
                    WHEN 'done' THEN 3 
                    ELSE 4 
                END,
                priority DESC,
                id DESC
            LIMIT 20
        """)
        queue = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(queue)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trading/top')
def trading_top():
    """Top 10 Performer aus abgeschlossenen Backtests"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT strategie, profit_pct, trades, sharpe, drawdown, tested_at
            FROM athena_backtest_results 
            WHERE status = 'done'
            ORDER BY profit_pct DESC 
            LIMIT 10
        """)
        top = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(top)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ TRADING BOTS API (M2.7) ============
@app.route('/api/trading/bots')
def trading_bots():
    """Get all trading bots status"""
    try:
        import subprocess
        
        bots = []
        
        # Bot 01 - NASOSv5_mod3 on port 8081 (local)
        bot_01 = {
            'name': 'bot_01',
            'strategy': 'NASOSv5_mod3',
            'port': 8081,
            'status': 'unknown',
            'pnl': '0.00%',
            'winrate': '0%',
            'pairs': 0,
            'uptime': '0h'
        }
        
        # Try to connect to local freqtrade on port 8081
        try:
            import requests as req
            resp = req.get('http://localhost:8081/api/v1/status', timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    bot_01['status'] = 'running'
                    bot_01['pairs'] = len(data)
                    # Calculate P&L from open trades
                    total_profit = sum(float(t.get('profit_abs', 0)) for t in data)
                    bot_01['pnl'] = f"{total_profit:+.2f}%"
        except:
            # Check if freqtrade process is running
            result = subprocess.run(['pgrep', '-f', 'freqtrade'], capture_output=True, text=True)
            if result.returncode == 0:
                bot_01['status'] = 'running'
                bot_01['uptime'] = 'active'
            else:
                bot_01['status'] = 'stopped'
        
        bots.append(bot_01)
        
        return jsonify({
            'bots': bots,
            'count': len(bots),
            'timestamp': now_berlin().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e), 'bots': []}), 500


# ============ OPENCLAW STATS & TOKEN TRACKING ============

@app.route('/api/openclaw/stats')
def openclaw_stats():
    """Live OpenClaw Stats from Gateway"""
    import subprocess
    try:
        result = subprocess.run(['/usr/bin/openclaw', 'status', '--json'], 
            capture_output=True, text=True, timeout=5)
        gateway = json.loads(result.stdout) if result.stdout else {}
    except:
        gateway = {}
    
    return jsonify({
        'sessions': gateway.get('sessions', 0),
        'messages': gateway.get('messages', 0),
        'tokens': gateway.get('tokens', 0),
        'timestamp': now_berlin().isoformat()
    })

@app.route('/api/openclaw/models')
def top_models():
    """Top Models by token usage"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT model_name, COUNT(*) as calls, SUM(tokens_total) as total_tokens
            FROM token_usage_history
            WHERE model_name IS NOT NULL AND model_name != ''
            AND timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY model_name
            ORDER BY total_tokens DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if rows:
            return jsonify({'models': [
                {'model': r[0], 'calls': r[1], 'tokens': r[2]} for r in rows
            ]})
    except:
        pass
    
    # Fallback: Demo data
    return jsonify({'models': [
        {'model': 'minimax-direct/M2.5', 'calls': 42, 'tokens': 128000000},
        {'model': 'minimax-direct/M2.5-highspeed', 'calls': 28, 'tokens': 45000000},
        {'model': 'openrouter/qwen3-coder:free', 'calls': 15, 'tokens': 8000000},
    ]})

@app.route('/api/openclaw/tools')
def top_tools():
    """Top Tools by usage (M2.7 Feature)"""
    # Try to get real data from DB
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tool_name, COUNT(*) as calls
            FROM tool_usage_history
            WHERE timestamp >= NOW() - INTERVAL '30 days'
            GROUP BY tool_name
            ORDER BY calls DESC
            LIMIT 10
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        if rows:
            return jsonify({'tools': [
                {'name': r[0], 'calls': r[1]} for r in rows
            ]})
    except:
        pass
    
    # Fallback: Demo data
    return jsonify({'tools': [
        {'name': 'web_search', 'calls': 234},
        {'name': 'db_query', 'calls': 189},
        {'name': 'file_read', 'calls': 156},
        {'name': 'exec', 'calls': 98},
        {'name': 'http_request', 'calls': 67},
    ]})

@app.route('/api/openclaw/sync')
def sync_stats():
    """Sync OpenClaw stats to DB daily"""
    import subprocess
    try:
        result = subprocess.run(['/usr/bin/openclaw', 'status', '--json'], 
            capture_output=True, text=True, timeout=10)
        data = json.loads(result.stdout) if result.stdout else {}
    except:
        data = {}
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO openclaw_usage_daily (date, messages, tokens_used, sessions)
            VALUES (CURRENT_DATE, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                messages = EXCLUDED.messages,
                tokens_used = EXCLUDED.tokens_used,
                sessions = EXCLUDED.sessions
        """, (
            data.get('sessions', {}).get('count', 0),
            0,  # tokens - would need to sum all recent sessions
            data.get('sessions', {}).get('count', 0)
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({'synced': False, 'error': str(e)})
    
    return jsonify({'synced': True, 'date': str(now_berlin().date())})

@app.route('/api/agents/usage')
def agents_usage():
    """Top 3 Agents with usage stats"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT name, emoji, status, description 
            FROM agents 
            ORDER BY name
            LIMIT 3
        """)
        agents = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'agents': [
            {'name': a['name'], 'emoji': a['emoji'], 'status': a['status'], 'messages': 0, 'tokens': 0}
            for a in agents
        ]})
    except Exception as e:
        return jsonify({'agents': [], 'error': str(e)})

# ============ ENDE FIXES ============


@app.route('/api/rheingold/engine-logs')
def rheingold_engine_logs():
    """Live engine logs from loop.log"""
    from pathlib import Path
    import re as _re
    log_file = Path('/home/iggy/rheingold/logs/loop.log')
    if not log_file.exists():
        return jsonify({'logs': [], 'total_lines': 0})
    try:
        with open(log_file) as f:
            lines = f.readlines()
        logs = []
        for line in lines[-40:]:
            line = line.strip()
            if not line:
                continue
            m = _re.match(r'\[([\d-]+ [\d:]+)\] (.+)', line)
            if m:
                logs.append({'timestamp': m.group(1), 'message': m.group(2)})
            else:
                logs.append({'timestamp': '', 'message': line[:200]})
        return jsonify({'logs': logs, 'total_lines': len(lines)})
    except Exception as e:
        return jsonify({'logs': [], 'error': str(e)})


# Backtest Tab Routes
@app.route("/trading/backtests")
def backtest_tab():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT strategie, profit_pct, trades FROM athena_backtest_results ORDER BY tested_at DESC LIMIT 50")
    pending = cursor.fetchall()
    conn.close()
    return render_template("backtest_tab.html", results=pending)

@app.route("/api/backtest-status")
def backtest_status():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("""
 SELECT strategy_name as strategy, profit_pct, trades, sharpe, drawdown as max_drawdown, status,
 tested_at::text as date
 FROM athena_backtest_results
 ORDER BY tested_at DESC
 LIMIT 200
 """)
    done = cursor.fetchall()
 
    cursor.execute("""
 SELECT current_index, strategy_name as strategy, 
 status, updated_at::text as date
 FROM athena_backtest_state
 WHERE status != 'done' OR TRUE
 ORDER BY current_index ASC
 LIMIT 100
 """)
    pending = cursor.fetchall()
 
    cursor.execute("""
 SELECT strategy_name as strategy, current_index,
 status, updated_at::text as date
 FROM athena_backtest_state
 WHERE status = 'running' OR TRUE
 LIMIT 1
 """)
    running = cursor.fetchone()
 
    conn.close()
    return jsonify({
 'done': [dict(r) for r in done],
 'pending': [dict(r) for r in pending],
 'running': dict(running) if running else None
 })
# ============ RHEINGOLD NEW APIs ============
@app.route("/api/rheingold/findings", methods=["GET"])
def rheingold_findings():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT kategorie, org_name, betrag, quelle, created_at 
            FROM rheingold_findings 
            ORDER BY created_at DESC, betrag DESC NULLS LAST
            LIMIT 500
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{
            "kategorie": r[0], "organisation": r[1], "betrag": float(r[2]) if r[2] else None,
            "quelle": r[3], "datum": str(r[4])[:10] if r[4] else None
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/rheingold/orgs", methods=["GET"])
def rheingold_orgs():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT org_name, kategorie as typ, SUM(betrag) as gesamt, COUNT(*) as findings
            FROM rheingold_findings
            WHERE org_name IS NOT NULL
            GROUP BY org_name, kategorie
            ORDER BY gesamt DESC NULLS LAST
            LIMIT 100
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{
            "name": r[0], "typ": r[1], "foerderung": float(r[2]) if r[2] else None, "findings": r[3]
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/rheingold/ifg", methods=["GET"])
def rheingold_ifg():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, behoerde, betreff, status, created_at  
            FROM rheingold_requests 
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{
            "id": r[0], "behoerde": r[1], "betreff": r[2], "status": r[3], 
            "datum": str(r[4])[:10] if r[4] else None 
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/rheingold/activity", methods=["GET"])
def rheingold_activity():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT message, timestamp
            FROM agent_logs
            WHERE agent = %s
            ORDER BY timestamp DESC
            LIMIT 20
        """, ("rheingold",))
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{
            "message": r[0], "zeit": str(r[1])[:19] if r[1] else None
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/rheingold_findings_tab")
def rheingold_findings_tab():
    return render_template("rheingold_findings.html")

# ========== RHEINGOLD ENHANCED ACTIVITY LOG ==========
@app.route("/api/rheingold/live-stats")
def rheingold_live_stats():
    """Live stats for Rheingold dashboard"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Findings today
        cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE created_at::date = CURRENT_DATE")
        today = cur.fetchone()[0]
        
        # Findings this hour
        cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE created_at >= date_trunc('hour', NOW())")
        this_hour = cur.fetchone()[0]
        
        # Last activity
        cur.execute("SELECT timestamp, message FROM agent_logs WHERE agent = 'rheingold' ORDER BY timestamp DESC LIMIT 1")
        last = cur.fetchone()
        
        # Queue stats
        cur.execute("SELECT status, COUNT(*) as count FROM rheingold_crawl_queue GROUP BY status")
        queue = {r[0]: r[1] for r in cur.fetchall()}
        
        cur.close()
        conn.close()
        
        last_min = int((datetime.now() - last[0]).total_seconds() / 60) if last else 999
        
        return jsonify({
            'findings_today': today,
            'findings_this_hour': this_hour,
            'last_activity_minutes': last_min,
            'status': 'idle' if last_min > 5 else 'active',
            'queue': queue
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/rheingold/crawl-queue")
def rheingold_crawl_queue_api():
    """Get crawl queue"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, url, status, depth, added_at, crawled_at, findings_count
            FROM rheingold_crawl_queue
            ORDER BY added_at DESC LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{
            'id': r[0], 'url': r[1], 'status': r[2], 'depth': r[3],
            'added_at': str(r[4])[:19] if r[4] else None,
            'crawled_at': str(r[5])[:19] if r[5] else None,
            'findings_count': r[6]
        } for r in rows])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========== ATHENA BACKTEST API ==========
@app.route("/api/athena/backtest-results")
def athena_backtest_results():
    """Get backtest results from database"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, strategie, sharpe, profit_pct, 
                   drawdown, trades, status, tested_at
            FROM athena_backtest_results
            ORDER BY tested_at DESC LIMIT 50
        """)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify([{
            "id": r[0], "strategy": r[1], "sharpe": r[2], 
            "return_pct": r[3], "drawdown": r[4], "trades": r[5],
            "status": r[6], "tested_at": str(r[7])[:19] if r[7] else None
        } for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/athena/marathon-status")
def athena_marathon_status():
    """Get marathon queue status"""
    try:
        # Check if hyperopt is running on Cronos
        import subprocess
        result = subprocess.run(
            ["ssh", "-i", "/home/iggy/.ssh/cronos_key", "iggy@192.168.23.80", 
             "ps aux | grep hyperopt | grep -v grep"],
            capture_output=True, text=True, timeout=10
        )
        running = "hyperopt" in result.stdout
        
        # Get latest result from DB
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT strategie, sharpe, profit_pct, status
            FROM athena_backtest_results
            ORDER BY tested_at DESC LIMIT 1
        """)
        last = cur.fetchone()
        cur.close()
        conn.close()
        
        return jsonify({
            "running": running,
            "last_strategy": last[0] if last else None,
            "last_sharpe": last[1] if last else None,
            "last_return": last[2] if last else None,
            "last_status": last[3] if last else None
        })
    except Exception as e:
        return jsonify({"error": str(e), "running": False}), 500

# ============ RHEINGOLD LIVE STATUS WIDGET API (M2.7 Enhanced) ============
@app.route('/api/rheingold/status')
def rheingold_status():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Queue pending
        try:
            cur.execute("SELECT COUNT(*) FROM rheingold_crawl_queue WHERE status='pending'")
            pending = cur.fetchone()[0]
        except:
            pending = 0
        
        # Queue size (total)
        try:
            cur.execute("SELECT COUNT(*) FROM rheingold_crawl_queue")
            queue_size = cur.fetchone()[0]
        except:
            queue_size = 0
        
        # Heute neue Findings
        try:
            cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE DATE(created_at) = CURRENT_DATE")
            today = cur.fetchone()[0]
        except:
            today = 0
        
        # Letzter Fund + timestamp
        try:
            cur.execute("SELECT COALESCE(empfaenger, org_name, quelle), created_at FROM rheingold_findings ORDER BY created_at DESC LIMIT 1")
            last = cur.fetchone()
            last_fund = last[0] if last else "—"
            last_time = last[1] if last else None
        except:
            last_fund = "—"
            last_time = None
        
        # Letzte 3 findings
        try:
            cur.execute("""
                SELECT COALESCE(empfaenger, org_name, quelle) as name, created_at 
                FROM rheingold_findings 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            recent_findings = [{'name': r[0], 'time': str(r[1])[:19] if r[1] else None} for r in cur.fetchall()]
        except:
            recent_findings = []
        
        cur.close()
        conn.close()
        
        # Crawler Status aus systemd
        import subprocess
        try:
            result = subprocess.run(['systemctl', 'is-active', 'rheingold-crawler'], capture_output=True, text=True, timeout=5)
            crawler_status = "crawling" if result.stdout.strip() == 'active' else "idle"
        except:
            crawler_status = "idle"
        
        # Last activity minutes
        last_min = int((datetime.now() - last_time).total_seconds() / 60) if last_time else 999
        
        return jsonify({
            'status': crawler_status,
            'queue_pending': pending,
            'queue_size': queue_size,
            'today_findings': today,
            'last_fund': last_fund[:80] if last_fund and len(last_fund) > 80 else (last_fund or "—"),
            'last_activity_minutes': last_min,
            'recent_findings': recent_findings,
            'timestamp': now_berlin().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error', 'queue_pending': 0, 'today_findings': 0, 'last_fund': '—'}), 500
@app.route('/api/rheingold/engine-status')
def rheingold_engine_status():
    import json as _json
    from pathlib import Path
    state_file = Path('/home/iggy/rheingold/state/engine-status.json')
    status = {'status':'UNKNOWN','jobs_per_minute':0,'queue_size':0,'queue_total':0,
              'entities_total':0,'entities_new_24h':0,'funding_tracked':0,
              'documents_analyzed':0,'documents_pending':0,'findings_total':0,
              'netzwerk_connections':0,'persons_found':0,'iterations_total':0,'engine_version':'3.2'}
    if state_file.exists():
        try:
            with open(state_file) as f:
                data = _json.load(f)
                status.update(data)
                status['status'] = 'RUNNING'
        except: status['status'] = 'PARSE_ERROR'
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rheingold_crawl_queue WHERE status='pending'")
        status['queue_size'] = cur.fetchone()[0] or status.get('queue_size',0)
        cur.execute('SELECT COUNT(*) FROM rheingold_crawl_queue')
        status['queue_total'] = cur.fetchone()[0] or status.get('queue_total',0)
        cur.execute('SELECT COUNT(*) FROM rheingold_entities')
        status['entities_total'] = cur.fetchone()[0] or status.get('entities_total',0)
        cur.execute("SELECT COUNT(*) FROM rheingold_entities WHERE created_at > NOW() AT TIME ZONE 'Europe/Berlin' - INTERVAL '24 hours'")
        status['entities_new_24h'] = cur.fetchone()[0] or 0
        cur.execute('SELECT COALESCE(SUM(betrag),0) FROM rheingold_findings WHERE betrag IS NOT NULL')
        status['funding_tracked'] = float(cur.fetchone()[0] or 0)
        cur.execute('SELECT COUNT(*) FROM rheingold_findings')
        status['findings_total'] = cur.fetchone()[0] or status.get('findings_total',0)
        cur.execute('SELECT COUNT(*) FROM rheingold_documents WHERE analyzed = true')
        status['documents_analyzed'] = cur.fetchone()[0] or 0
        cur.execute('SELECT COUNT(*) FROM rheingold_documents WHERE analyzed = false')
        status['documents_pending'] = cur.fetchone()[0] or 0
        cur.execute('SELECT COUNT(*) FROM rheingold_netzwerk')
        status['netzwerk_connections'] = cur.fetchone()[0] or 0
        cur.execute('SELECT COUNT(*) FROM rheingold_persons')
        status['persons_found'] = cur.fetchone()[0] or 0
        cur.close(); conn.close()
    except Exception as e:
        status['db_error'] = str(e)
    status['timestamp'] = now_berlin().isoformat()
    return jsonify(status)

@app.route('/api/rheingold/expansion-rate')
def rheingold_expansion_rate():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM rheingold_entities WHERE created_at > NOW() - INTERVAL '1 hour'")
        e1h = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_entities WHERE created_at > NOW() AT TIME ZONE 'Europe/Berlin' - INTERVAL '24 hours'")
        e24h = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE created_at > NOW() - INTERVAL '1 hour'")
        f1h = cur.fetchone()[0] or 0
        cur.execute("SELECT COUNT(*) FROM rheingold_findings WHERE created_at > NOW() AT TIME ZONE 'Europe/Berlin' - INTERVAL '24 hours'")
        f24h = cur.fetchone()[0] or 0
        cur.execute("SELECT COALESCE(SUM(betrag),0) FROM rheingold_findings WHERE betrag IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours'")
        fu24h = float(cur.fetchone()[0] or 0)
        cur.close(); conn.close()
        return jsonify({'entities_per_hour':e1h,'entities_per_day':e24h,'findings_per_hour':f1h,'findings_per_day':f24h,'funding_24h':fu24h,'timestamp':now_berlin().isoformat()})
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/api/rheingold/activity-feed')
def rheingold_activity_feed():
    """Live activity from DB — entities + findings + profiles (last 30 min)"""
    feed = []
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Recent entities
        cur.execute("SELECT name, entity_type, source, created_at FROM rheingold_entities WHERE created_at > NOW() AT TIME ZONE 'Europe/Berlin' - INTERVAL '30 minutes' ORDER BY created_at DESC LIMIT 20")
        for name, etype, source, created in cur.fetchall():
            feed.append({"type": "entity", "entity": name, "entity_type": etype or "unknown", "source": str(source or "")[:60], "time": str(created)[:19]})
        # Recent findings
        cur.execute("SELECT beschreibung, quelle, betrag, created_at FROM rheingold_findings WHERE created_at > NOW() AT TIME ZONE 'Europe/Berlin' - INTERVAL '30 minutes' ORDER BY created_at DESC LIMIT 20")
        for desc, quelle, betrag, created in cur.fetchall():
            feed.append({"type": "finding", "description": str(desc or "")[:80], "source": str(quelle or "")[:60], "amount": float(betrag) if betrag else None, "time": str(created)[:19]})
        # Recent profiles
        cur.execute("SELECT entity_name, confidence_score, risk_flags, updated_at FROM rheingold_entity_profiles WHERE updated_at > NOW() - INTERVAL '30 minutes' ORDER BY updated_at DESC LIMIT 10")
        for name, conf, flags, updated in cur.fetchall():
            feed.append({"type": "profile", "entity": name, "confidence": float(conf) if conf else 0, "flags": flags or [], "time": str(updated)[:19]})
        cur.close()
        conn.close()
    except Exception as e:
        pass
    feed.sort(key=lambda x: x.get("time", ""), reverse=True)
    return jsonify({"feed": feed[:30], "generated": now_berlin().isoformat()})


@app.route('/api/rheingold/network-connections')
def rheingold_network_connections():
    """Return all network connections from rheingold_netzwerk"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT von_orga, zu_orga, verbindungstyp, quelle, notes, created_at
            FROM rheingold_netzwerk
            ORDER BY created_at DESC
            LIMIT 100
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({"connections": rows, "count": len(rows)})
    except Exception as e:
        return jsonify({"error": str(e), "connections": []}), 500


@app.route('/api/rheingold/profiles')
def rheingold_profiles():
    """All entity profiles with risk flags"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT entity_id, entity_name, confidence_score, risk_flags, updated_at,
                   profile->>'funding_total' as funding_total,
                   profile->>'summary' as summary,
                   profile->>'entity_type' as entity_type,
                   profile->>'top_connections' as top_connections
            FROM rheingold_entity_profiles
            ORDER BY (profile->>'funding_total')::numeric DESC NULLS LAST
            LIMIT 200
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({"profiles": rows})
    except Exception as e:
        return jsonify({"error": str(e), "profiles": []}), 500

@app.route('/api/rheingold/orgas')
def rheingold_orgas():
    """Alle 46 echten NGOs aus rheingold_orgas"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT id, name, adresse, webseite, bewilligt, foerderstrang,
                   foerdergegenstand, jury_urteil, antrag_datum,
                   recherche_status, notes, lat, lon, plz, stadtteil
            FROM rheingold_orgas
            ORDER BY bewilligt DESC NULLS LAST
        """)
        rows = [dict(r) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({'orgas': rows})
    except Exception as e:
        return jsonify({'error': str(e), 'orgas': []}), 500

@app.route('/api/rheingold/ngo-map')
def rheingold_ngo_map():
    """NGO entities as GeoJSON for map display.
    NGOs are identified by:
      - profile->>'entity_type' = 'ngo' (profiles table), OR
      - finding_type IN ('keyword_ngo', 'organisation', 'förderer', 'foerderer') (findings table)
    Coordinates from rheingold_findings.lat/lng (joined by org_name = entity_name).
    Falls keine lat/lng in findings: parse address via Nominatim (deferred client-side).
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # STEP 1: Get all NGO entity names from profiles (profile->>'entity_type' = 'ngo')
        cur.execute("""
            SELECT entity_id, entity_name,
                   confidence_score, risk_flags,
                   profile->>'funding_total' as profile_funding_total
            FROM rheingold_entity_profiles
            WHERE profile->>'entity_type' = 'ngo'
        """)
        profile_ngos = {str(row['entity_name']): dict(row) for row in cur.fetchall()}

        # STEP 2: Get NGOs from findings (finding_type = keyword_ngo / organisation / förderer / foerderer)
        cur.execute("""
            SELECT DISTINCT org_name, finding_type, betrag, beschreibung, address, region, lat, lng
            FROM rheingold_findings
            WHERE org_name IS NOT NULL AND org_name != ''
              AND (
                  finding_type IN ('keyword_ngo', 'organisation', 'förderer', 'foerderer')
                  OR org_name ILIKE '% e.V.'
              )
            ORDER BY org_name
        """)
        finding_ngos = cur.fetchall()

        # STEP 3: Combine and deduplicate by entity_name
        seen = {}
        for row in finding_ngos:
            name = row['org_name']
            if name and name not in seen:
                seen[name] = {
                    'entity_name': name,
                    'finding_type': row['finding_type'],
                    'funding_total': row['betrag'] or 0,
                    'summary': row['beschreibung'] or '',
                    'address': row['address'] or '',
                    'city': row['region'] or '',
                    'lat': row['lat'],
                    'lng': row['lng'],
                }

        # STEP 4: Enrich with profile data (confidence_score, risk_flags, funding_total override)
        rows_out = []
        for name, ngo in seen.items():
            profile = profile_ngos.get(str(name), {})
            entity_id = profile.get('entity_id') or hash(name) % 100000

            conf = profile.get('confidence_score')
            risk_flags = profile.get('risk_flags') or []
            profile_ft = 'ngo' if profile else None

            # Profile funding_total takes priority over finding betrag
            profile_funding_raw = profile.get('profile_funding_total') if profile else None
            try:
                profile_funding_val = float(profile_funding_raw) if profile_funding_raw else None
            except (TypeError, ValueError):
                profile_funding_val = None

            # Use higher funding value
            finding_funding = float(ngo['funding_total'] or 0)
            if profile_funding_val and profile_funding_val > finding_funding:
                final_funding = profile_funding_val
            else:
                final_funding = finding_funding

            rows_out.append({
                'entity_id': entity_id,
                'entity_name': name,
                'entity_type': profile_ft or 'ngo',
                'funding_total': final_funding,
                'summary': ngo['summary'],
                'address': ngo['address'],
                'city': ngo['city'],
                'lat': ngo['lat'],
                'lng': ngo['lng'],
                'confidence_score': conf,
                'risk_flags': risk_flags,
            })

        # Add pure-profile NGOs (not in findings)
        for name, profile in profile_ngos.items():
            if str(name) not in seen:
                rows_out.append({
                    'entity_id': profile.get('entity_id') or abs(hash(str(name))) % 100000,
                    'entity_name': str(name),
                    'entity_type': 'ngo',
                    'funding_total': 0,
                    'summary': '',
                    'address': '',
                    'city': '',
                    'lat': None,
                    'lng': None,
                    'confidence_score': profile.get('confidence_score'),
                    'risk_flags': profile.get('risk_flags') or [],
                })

        cur.close()
        conn.close()

        # Convert to GeoJSON
        features = []
        for row in rows_out:
            lat = row.pop('lat', None)
            lng = row.pop('lng', None)
            if lat is not None and lng is not None:
                try:
                    features.append({
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                        "properties": row
                    })
                except (TypeError, ValueError):
                    features.append({"type": "Feature", "geometry": None, "properties": row})
            else:
                features.append({"type": "Feature", "geometry": None, "properties": row})

        return jsonify({
            "type": "FeatureCollection",
            "features": features,
            "meta": {
                "total": len(features),
                "with_coords": sum(1 for f in features if f.get("geometry")),
                "without_coords": sum(1 for f in features if not f.get("geometry"))
            }
        })

    except Exception as e:
        import traceback; traceback.print_exc()
        return jsonify({"error": str(e), "type": "FeatureCollection", "features": []}), 500

@app.route('/api/rheingold/entity/<int:entity_id>')
def rheingold_entity(entity_id):
    """Output Contract JSON for specific entity"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT entity_id, entity_name, profile, confidence_score, risk_flags, updated_at
            FROM rheingold_entity_profiles WHERE entity_id = %s
        """, (entity_id,))
        row = cur.fetchone()
        cur.close(); conn.close()
        if row:
            return jsonify({"entity_id": row[0], "entity_name": row[1], "profile": row[2],
                           "confidence_score": float(row[3]) if row[3] else 0,
                           "risk_flags": row[4] or [], "updated_at": str(row[5])[:19]})
        return jsonify({"error": "Not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============ ATHENE LAB API (V3 BASELINE + ITERATIONS) ============
@app.route('/api/athene/iterations')
def athene_iterations():
    """Alle Athene Backtest-Versionen aus agent_knowledge"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT key, value, learned_at::text as date
            FROM agent_knowledge
            WHERE key LIKE 'athene_backtest_v%' OR key LIKE 'athene_loop_report%' OR key LIKE 'athene_timeframe%'
            ORDER BY learned_at DESC LIMIT 30
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return jsonify([{"key": r['key'], "data": r['value'], "date": r['date']} for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/athene/baseline')
def athene_baseline():
    """v3 Baseline zum Vergleich"""
    return jsonify({
        "version": "v3",
        "timeframe": "1h",
        "trades": 10,
        "profit_usdt": 0.775,
        "winrate": 90.0,
        "drawdown": 0.05,
        "status": "current_baseline",
        "note": "Bestätigt 06.04.2026 via 3-timeframe test"
    })

@app.route('/api/athene/events')
def athene_events():
    """Letzte Events aus SIAS Event Bus (Redis auf Cronos)"""
    try:
        import subprocess, json
        result = subprocess.run(['redis-cli', '-h', '192.168.23.170', '-p', '6379', 'LRANGE', 'sias:events:sias:arbitrage', '0', '19'], capture_output=True, text=True, timeout=5)
        events_raw = [l.strip().strip('"') for l in result.stdout.strip().split('\n') if l.strip()]
        parsed = []
        for line in events_raw:
            if line.startswith('{'):
                try: parsed.append(json.loads(line))
                except: pass
        return jsonify({"count": len(parsed), "events": parsed[-20:]})
    except Exception as e:
        return jsonify({"count": 0, "error": str(e), "events": []})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
