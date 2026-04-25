#!/usr/bin/env python3
"""SIAS Dashboard V5 — Control Center"""

import os, subprocess, datetime, json, csv, io, time, threading, re, hashlib
import smtplib, ssl
import requests as req_lib
import psutil
import pytz
import psycopg2
from psycopg2.extras import RealDictCursor
from email.message import EmailMessage
from flask import Flask, render_template, jsonify, request

DB_CONFIG = {
    'host': '127.0.0.1',
    'database': 'metamaus',
    'user': 'scraper',
    'password': '',
    'port': 5432
}

app = Flask(__name__)

def query_db(sql):
    try:
        r = subprocess.run(
            ['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '-t', '-A', '-c', sql],
            capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    except:
        return ""

def query_db_rows(sql):
    try:
        r = subprocess.run(
            ['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '--csv', '-c', sql],
            capture_output=True, text=True, timeout=10)
        if not r.stdout.strip():
            return []
        rows = list(csv.reader(io.StringIO(r.stdout.strip())))
        # Remove header row
        if rows:
            rows = rows[1:]
        return rows
    except:
        return []



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


def get_cached(key):
    """Get cached response if still valid"""
    if key in _api_cache:
        cached_time, data = _api_cache[key]
        if (datetime.now() - cached_time).total_seconds() < _cache_ttl:
            return data
    return None


def get_db_connection():
    """Get PostgreSQL database connection"""
    return psycopg2.connect(**DB_CONFIG)


SMTP_HOST = "mail.abydon.com"
SMTP_PORT = 465
SMTP_USER = "investigativ@abydon.com"

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


@app.route('/')
def index():
    return render_template('dashboard.html', active='dashboard')

@app.route('/tasks')
def tasks():
    agent_filter = request.args.get('agent', '')
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    rows = query_db_rows("SELECT id, agent, task, status, priority, created_at FROM agent_tasks ORDER BY created_at DESC LIMIT 100")
    filtered = rows
    if agent_filter:
        filtered = [r for r in filtered if len(r) > 1 and agent_filter.lower() in (r[1] or '').lower()]
    if status_filter:
        filtered = [r for r in filtered if len(r) > 3 and status_filter.lower() in (r[3] or '').lower()]
    if priority_filter:
        filtered = [r for r in filtered if len(r) > 4 and priority_filter.lower() in (r[4] or '').lower()]
    agents = sorted(set(r[1] for r in rows if len(r) > 1 and r[1]))
    return render_template('tasks.html', active='tasks', tasks=filtered, agents=agents,
                           agent_filter=agent_filter, status_filter=status_filter, priority_filter=priority_filter)

@app.route('/demos')
def demos():
    return render_template('demos.html', active='demos')

@app.route('/youtube')
def youtube():
    videos = query_db_rows("SELECT key, value FROM agent_knowledge WHERE category='iggy_video' ORDER BY key DESC LIMIT 20")
    return render_template('youtube.html', active='youtube', videos=videos)

@app.route('/agents')
def agents():
    ica_log = ""
    try:
        with open('/home/iggy/SIAS/inter_agent_chat.log', 'r') as f:
            lines = f.readlines()[-30:]
        ica_log = ''.join(lines)
    except:
        ica_log = "Log nicht verfügbar"
    return render_template('agents.html', active='agents', ica_log=ica_log)

@app.route('/mail')
def mail():
    return render_template('mail.html', active='mail')

@app.route('/settings')
def settings():
    return render_template('settings.html', active='settings')

@app.route('/imgtools')
def imgtools():
    return render_template('imgtools.html', active='imgtools')

@app.route('/api/dashboard-stats')
def api_stats():
    import shutil
    stats = {
        'token_today': query_db("SELECT COUNT(*) FROM token_usage WHERE \"timestamp\" >= CURRENT_DATE"),
        'token_week': query_db("SELECT COUNT(*) FROM token_usage WHERE \"timestamp\" >= CURRENT_DATE - INTERVAL '7 days'"),
        'token_total': query_db("SELECT COUNT(*) FROM token_usage"),
        'token_last': query_db("SELECT TO_CHAR(MAX(\"timestamp\"), 'DD.MM.YY') FROM token_usage"),
        'tokens_real_today': query_db("SELECT COALESCE(SUM(tokens_total),0) FROM token_usage_history WHERE \"timestamp\" >= CURRENT_DATE"),
        'tokens_real_total': query_db("SELECT COALESCE(SUM(tokens_total),0) FROM token_usage_history"),
        'disk_free_gb': round(shutil.disk_usage('/').free / (1024**3), 1),
        'disk_total_gb': round(shutil.disk_usage('/').total / (1024**3), 1),
        'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    for svc, cmd in [('postgres', 'pg_isready -h 127.0.0.1'), ('redis', 'redis-cli ping')]:
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=3)
            stats[svc] = 'up' if r.returncode == 0 else 'down'
        except:
            stats[svc] = 'unknown'
    try:
        r = subprocess.run('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8080/', shell=True, capture_output=True, text=True, timeout=3)
        stats['gateway'] = 'up' if r.stdout.strip() == '200' else 'down'
    except:
        stats['gateway'] = 'unknown'
    return jsonify(stats)

# ═══════════════════════════════════════════════════════════════════
# F-01: PORTIERTE ROUTES aus V3
# ═══════════════════════════════════════════════════════════════════

def now_berlin():
    return datetime.datetime.now(pytz.timezone('Europe/Berlin'))

# ── Price fetching helpers ────────────────────────────────────────

def _load_cached_prices():
    try:
        with open('/tmp/dashboard_prices_cache.json') as f:
            return json.load(f)
    except Exception:
        return None

def _save_cached_prices(data):
    try:
        with open('/tmp/dashboard_prices_cache.json', 'w') as f:
            json.dump(data, f)
    except Exception:
        pass

def _stooq_fetch(symbol):
    try:
        r = req_lib.get(f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv", timeout=8)
        r.raise_for_status()
        reader = csv.DictReader(io.StringIO(r.text))
        for row in reader:
            close = row.get('Close', '').strip()
            if close and close != 'N/D':
                return float(close)
    except Exception:
        pass
    return 0

def _swissquote_fetch(instrument):
    try:
        r = req_lib.get(f"https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/{instrument}", timeout=8)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            spread = data[0].get('spreadProfilePrices', [])
            if spread:
                bid = spread[0].get('bid', 0)
                ask = spread[0].get('ask', 0)
                if bid and ask:
                    return round((bid + ask) / 2, 3)
    except Exception:
        pass
    return 0

def _fetch_prices_background():
    prices = {'btc': 0, 'sol': 0, 'ada': 0, 'gold': 0, 'silver': 0, 'dax': 0, 'sp500': 0}
    changes = {'btc_24h': 0, 'sol_24h': 0, 'silver_24h': 0, 'silver_7d': 0, 'gold_24h': 0, 'gold_7d': 0}
    api_used = {}
    fetch_success_time = None

    # Crypto via Binance
    for symbol, key in [("BTCUSDT", "btc"), ("SOLUSDT", "sol")]:
        try:
            r = req_lib.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5).json()
            if r.get('price'):
                prices[key] = float(r['price'])
                api_used[key] = 'binance'
        except Exception:
            pass

    for symbol, key in [("BTCUSDT", "btc_24h"), ("SOLUSDT", "sol_24h")]:
        try:
            r = req_lib.get(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}", timeout=5).json()
            pct = r.get('priceChangePercent')
            if pct is not None:
                changes[key] = round(float(pct), 2)
        except Exception:
            pass

    # ADA via CoinPaprika
    try:
        r = req_lib.get("https://api.coinpaprika.com/v1/tickers/ada-cardano", timeout=5).json()
        if r.get('quotes', {}).get('USD', {}).get('price'):
            prices['ada'] = r['quotes']['USD']['price']
            api_used['ada'] = 'coinpaprika'
    except Exception:
        pass

    # DAX
    val = _stooq_fetch('^dax')
    if val:
        prices['dax'] = val
        api_used['dax'] = 'stooq'

    # S&P500
    val = _stooq_fetch('^spx')
    if val:
        prices['sp500'] = val
        api_used['sp500'] = 'stooq'

    # Gold
    val = _stooq_fetch('xauusd')
    if val:
        prices['gold'] = val
        api_used['gold'] = 'stooq'
    if not prices['gold']:
        val = _swissquote_fetch('XAU/USD')
        if val:
            prices['gold'] = val
            api_used['gold'] = 'swissquote'

    # Silver
    val = _stooq_fetch('xagusd')
    if val:
        prices['silver'] = val
        api_used['silver'] = 'stooq'
    if not prices['silver']:
        val = _swissquote_fetch('XAG/USD')
        if val:
            prices['silver'] = val
            api_used['silver'] = 'swissquote'

    # Cache fallback for missing
    cached = _load_cached_prices()
    if cached:
        for key in ['gold', 'silver', 'dax', 'sp500']:
            if not prices[key] and cached.get(key) and cached[key] != 'N/A':
                raw = cached[key].replace('$', '').replace('€', '').replace(',', '')
                try:
                    prices[key] = float(raw)
                    api_used[key] = 'cache'
                except (ValueError, TypeError):
                    pass

    got_real_data = any(k in api_used and api_used[k] != 'cache' for k in ['gold', 'silver', 'dax', 'sp500'])
    if got_real_data:
        fetch_success_time = now_berlin().isoformat()

    result = {
        'btc': f"${prices['btc']:,.2f}" if prices['btc'] else 'N/A',
        'sol': f"${prices['sol']:.2f}" if prices['sol'] else 'N/A',
        'ada': f"${prices['ada']:,.4f}" if prices['ada'] else 'N/A',
        'gold': f"${prices['gold']:,.2f}" if prices['gold'] else 'N/A',
        'silver': f"${prices['silver']:.2f}" if prices['silver'] else 'N/A',
        'dax': f"€{prices['dax']:,.2f}" if prices['dax'] else 'N/A',
        'sp500': f"${prices['sp500']:,.2f}" if prices['sp500'] else 'N/A',
        'btc_24h': changes['btc_24h'],
        'sol_24h': changes['sol_24h'],
        'gold_24h': changes['gold_24h'],
        'gold_7d': changes['gold_7d'],
        'silver_24h': changes['silver_24h'],
        'silver_7d': changes['silver_7d'],
        'created_at': now_berlin().isoformat(),
        'last_updated': fetch_success_time or (cached.get('last_updated') if cached else None),
    }
    _save_cached_prices(result)
    return result


# ── Route 1: /api/stats/dashboard ─────────────────────────────────
@app.route('/api/stats/dashboard')
def get_dashboard_stats():
    try:
        db_size = query_db("SELECT pg_size_pretty(pg_total_relation_size('demos'))")
        demo_count = query_db("SELECT COUNT(*) FROM demos") or '0'
        news_today = query_db("SELECT COUNT(*) FROM news_articles WHERE fetched_at > NOW() - INTERVAL '24 hours'") or '0'
        return jsonify({
            "status": "success",
            "demos": {"size": db_size or 'N/A', "total": int(demo_count)},
            "news": {"today": int(news_today)}
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


# ── Route 2: /api/stats/agents ────────────────────────────────────
# Agent model/fallback registry — V5 UI2
AGENT_REGISTRY = {
    'metamaus':  {'model': 'kimi-k2.5',        'provider': 'moonshot',     'fallbacks': ['qwen3-coder:free','glm-5-turbo'],          'status': 'running'},
    'apollon':   {'model': 'glm-5.1',            'provider': 'zai',          'fallbacks': ['qwen3-coder:free','MiniMax-M2.5'],         'status': 'running'},
    'athene':    {'model': 'glm-5-turbo',         'provider': 'zai',          'fallbacks': ['qwen3-coder:free','kimi-k2.5'],            'status': 'running'},
    'rheingold': {'model': 'qwen3.6-plus',        'provider': 'openrouter',   'fallbacks': ['kimi-k2.5','glm-5-turbo'],                  'status': 'running'},
    'pythia':    {'model': 'glm-5-turbo',         'provider': 'zai',          'fallbacks': ['qwen3-coder:free'],                        'status': 'running'},
    'hermes':    {'model': 'MiniMax-M2.5',        'provider': 'minimax',      'fallbacks': ['qwen3-coder:free','glm-5-turbo'],          'status': 'running'},
    'hestia':    {'model': 'MiniMax-M2.7',        'provider': 'minimax',      'fallbacks': ['qwen3-coder:free','glm-5-turbo'],          'status': 'running'},
    'zerberus':  {'model': 'MiniMax-M2.7',        'provider': 'minimax',      'fallbacks': ['qwen3-coder:free'],                        'status': 'running'},
    'orpheus':   {'model': 'glm-5-turbo',         'provider': 'zai',          'fallbacks': ['qwen3-coder:free'],                        'status': 'running'},
}

@app.route('/api/stats/agents')
def api_stats_agents():
    try:
        rows = query_db_rows("""
            SELECT agent_id,
                   COUNT(*) as task_count,
                   SUM((payload->>'tokens_used')::int) as tokens
            FROM sias_tasks
            WHERE status='done'
            GROUP BY agent_id
            ORDER BY task_count DESC
        """)
        task_map = {r[0]: {'task_count': r[1], 'tokens': r[2]} for r in rows}
        result = []
        for agent_id, reg in AGENT_REGISTRY.items():
            t = task_map.get(agent_id, {'task_count': 0, 'tokens': 0})
            result.append({
                'agent_id': agent_id,
                'task_count': t['task_count'],
                'tokens': t['tokens'],
                'model': reg['model'],
                'provider': reg['provider'],
                'fallbacks': reg['fallbacks'],
                'status': reg['status'],
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Route 3: /api/stats/system ────────────────────────────────────
@app.route('/api/stats/system')
def get_system_stats():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_str = f"{days}d {hours}h {minutes}m"

        cpu_percent = psutil.cpu_percent()

        with open('/proc/meminfo', 'r') as f:
            mem_lines = f.readlines()
        total_mem = int(mem_lines[0].split()[1]) / 1024 / 1024
        available_mem = int(mem_lines[1].split()[1]) / 1024 / 1024
        used_mem = total_mem - available_mem
        ram_str = f"{used_mem:.1f}/{total_mem:.1f} GB"

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


# ── Route 4: /api/prices ─────────────────────────────────────────
_last_price_result = None
_last_price_time = 0

@app.route('/api/prices')
def get_prices():
    global _last_price_result, _last_price_time
    now = time.time()

    if _last_price_result and (now - _last_price_time) < 50:
        return jsonify(_last_price_result)

    if not _last_price_result:
        cached = _load_cached_prices()
        if cached:
            _last_price_result = cached
            _last_price_time = now
            return jsonify(cached)

    result = _fetch_prices_background()
    if result:
        _last_price_result = result
        _last_price_time = time.time()
        return jsonify(result)

    return jsonify({'error': 'price fetch failed'}), 503


# ── Route 5: /api/openclaw/stats ──────────────────────────────────
@app.route('/api/openclaw/stats')
def openclaw_stats():
    try:
        result = subprocess.run(['/usr/bin/openclaw', 'status', '--json'],
            capture_output=True, text=True, timeout=5)
        gateway = json.loads(result.stdout) if result.stdout else {}
    except Exception:
        gateway = {}

    return jsonify({
        'sessions': gateway.get('sessions', 0),
        'messages': gateway.get('messages', 0),
        'tokens': gateway.get('tokens', 0),
        'timestamp': now_berlin().isoformat()
    })


@app.route("/api/stats/openclaw")
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


@app.route('/api/news', methods=['GET'])
def get_news_events():
    try:
        category = request.args.get('category')
        limit = int(request.args.get('limit', 30))
        sortBy = request.args.get('sortBy', 'date')  # 'date' | 'relevance'
        vogueFilter = request.args.get('vogue', 'false').lower() == 'true'

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Relevance scoring: politic-heavy sources on top
        relevance_clause = """CASE ns.category
            WHEN 'politik' THEN 100
            WHEN 'afd' THEN 90
            WHEN 'popkultur' THEN 70
            ELSE 50
        END"""

        if vogueFilter:
            # Inline Vogue keyword filter (no reliance on rheingold_buzzwords table)
            vogue_keywords = [
                'Gendern', 'gendern', 'Gendersprache', 'Diversität', 'Diversity',
                'Quote', 'quotiert', 'Quoten', 'Sensibilisierung',
                'diskriminierend', 'Diskriminierung', 'Sexismus', 'Rassismus',
                'klimaneutral', 'Klimaneutralität', 'nachhaltig', 'Nachhaltigkeit',
                'woke', 'Woke', 'DEI', 'Diversity Equity', 'ESG',
                'Inklusion', 'Inklusiv', 'Barrierefreiheit', 'Teilhabe',
                'Klimaschutz', 'Klimakrise', 'Klimawandel',
                'Transgender', 'transgender', 'nicht-binär', 'nichtbinär',
                'Pronomen', 'geschlechtergerecht', 'geschlechterneutral'
            ]
            vogue_conditions = ' OR '.join([
                f"(na.title ILIKE '%%{kw}%%') OR (na.summary ILIKE '%%{kw}%%')"
                for kw in vogue_keywords
            ])
            cursor.execute(f"""
                SELECT na.*, ns.name as source_name, ns.category as source_category,
                       {relevance_clause} as relevance_score
                FROM news_articles na
                JOIN news_sources ns ON na.source_id = ns.id
                WHERE {vogue_conditions}
                ORDER BY na.published_at DESC NULLS LAST
                LIMIT %s
            """, (limit,))
        elif category and category != 'all':
            if sortBy == 'relevance':
                cursor.execute(f"""
                    SELECT na.*, ns.name as source_name, ns.category as source_category,
                           {relevance_clause} as relevance_score
                    FROM news_articles na
                    JOIN news_sources ns ON na.source_id = ns.id
                    WHERE ns.category = %s
                    ORDER BY {relevance_clause} DESC, na.published_at DESC NULLS LAST
                    LIMIT %s
                """, (category, limit))
            else:
                cursor.execute(f"""
                    SELECT na.*, ns.name as source_name, ns.category as source_category,
                           {relevance_clause} as relevance_score
                    FROM news_articles na
                    JOIN news_sources ns ON na.source_id = ns.id
                    WHERE ns.category = %s
                    ORDER BY na.published_at DESC NULLS LAST
                    LIMIT %s
                """, (category, limit))
        else:
            if sortBy == 'relevance':
                cursor.execute(f"""
                    SELECT na.*, ns.name as source_name, ns.category as source_category,
                           {relevance_clause} as relevance_score
                    FROM news_articles na
                    JOIN news_sources ns ON na.source_id = ns.id
                    ORDER BY {relevance_clause} DESC, na.published_at DESC NULLS LAST
                    LIMIT %s
                """, (limit,))
            else:
                cursor.execute(f"""
                    SELECT na.*, ns.name as source_name, ns.category as source_category,
                           {relevance_clause} as relevance_score
                    FROM news_articles na
                    JOIN news_sources ns ON na.source_id = ns.id
                    ORDER BY na.published_at DESC NULLS LAST
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
            d['relevance_score'] = d.get('relevance_score', 50)
            result.append(d)

        return jsonify({'status': 'success', 'articles': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


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

@app.route('/news')
def news_page():
    """News Monitor — RSS Articles UI3"""
    return render_template('news.html')


@app.route('/api/news/fetch/<int:source_id>', methods=['POST'])
def api_news_fetch_source(source_id):
    """Fetch RSS feed for a specific source and store articles"""
    try:
        import feedparser
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, name, url FROM news_sources WHERE id=%s AND active=true", (source_id,))
        source = cursor.fetchone()
        if not source:
            cursor.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Source not found'}), 404

        feed = feedparser.parse(source['url'])
        count = 0
        for entry in feed.entries[:20]:
            try:
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = ''
                if hasattr(entry, 'summary'):
                    summary = entry.summary[:500]
                elif hasattr(entry, 'description'):
                    summary = entry.description[:500]
                pub = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    from time import mktime
                    from datetime import datetime as _dt
                    try:
                        pub = _dt.fromtimestamp(mktime(entry.published_parsed))
                    except Exception:
                        pass
                cursor.execute("""
                    INSERT INTO news_articles (source_id, title, url, summary, published_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO NOTHING
                """, (source_id, title, link, summary, pub))
                count += 1
            except Exception:
                continue
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'source': source['name'], 'fetched': count})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============ HESTIA COMMENTS API ============

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

# ==================== KNOWLEDGE API ====================


# === F-08: Trading/Athene Routes from V3 ===

@app.route('/api/watchlist')
def api_watchlist():
    """Return watchlist data for dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM watchlist ORDER BY symbol')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== PORTFOLIO ====================

@app.route('/api/portfolio')
def api_portfolio():
    """Return portfolio positions for dashboard"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM portfolio_positions ORDER BY symbol')
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([dict(row) for row in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ==================== PORTFOLIO ADD ====================

@app.route('/api/portfolio/add', methods=['POST'])
def api_portfolio_add():
    """Add a position to portfolio"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        binance_pair = data.get('binance_pair', symbol + 'USDT')
        amount = data.get('amount', 0)
        buy_price = data.get('buy_price', 0)
        note = data.get('note', '')
        if not symbol or amount <= 0 or buy_price <= 0:
            return jsonify({"error": "symbol, amount, buy_price required"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "INSERT INTO portfolio_positions (symbol, binance_pair, amount, buy_price, note) VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (symbol, binance_pair, amount, buy_price, note)
        )
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify(dict(row)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== WATCHLIST ADD ====================

@app.route('/api/watchlist/add', methods=['POST'])
def api_watchlist_add():
    """Add a symbol to watchlist"""
    try:
        data = request.get_json()
        symbol = data.get('symbol', '').upper()
        binance_pair = data.get('binance_pair', symbol + 'USDT')
        note = data.get('note', '')
        if not symbol:
            return jsonify({"error": "symbol required"}), 400
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "INSERT INTO watchlist (symbol, binance_pair, note) VALUES (%s, %s, %s) RETURNING *",
            (symbol, binance_pair, note)
        )
        row = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify(dict(row)), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ==================== AGENT API ====================

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

@app.route('/portfolio')
def serve_portfolio():
    return send_from_directory('templates', 'portfolio.html')

# ============ SYSTEM HEALTH ============

@app.route('/api/freqtrade/profit')
def freqtrade_profit():
    """Aggregate profit across all bots."""
    result = {'profit_closed_coin': 0, 'profit_closed_percent_mean': 0,
              'profit_closed_percent_sum': 0, 'profit_all_coin': 0,
              'profit_all_percent_mean': 0, 'profit_all_percent_sum': 0,
              'trade_count': 0, 'first_trade_date': '',
              'latest_trade_date': '', 'winrate': 0}
    for bot in FREQTRADE_BOTS:
        data = _ft_get('profit', bot['port'])
        if data:
            result['trade_count'] += data.get('trade_count', 0)
            result['profit_closed_percent_sum'] += data.get('profit_closed_percent_sum', 0)
            if not result['first_trade_date'] or data.get('first_trade_date', ''):
                result['first_trade_date'] = data.get('first_trade_date', '')
            if not result['latest_trade_date'] or data.get('latest_trade_date', ''):
                result['latest_trade_date'] = data.get('latest_trade_date', '')
            wr = data.get('winrate', 0)
            if wr:
                result['winrate'] = max(result['winrate'], wr)
    return jsonify(result)

@app.route('/api/freqtrade/status')
def freqtrade_status():
    """Aggregate open trades from all bots."""
    all_trades = []
    for bot in FREQTRADE_BOTS:
        data = _ft_get('status', bot['port'])
        if data and isinstance(data, list):
            for t in data:
                t['_bot'] = bot['name']
            all_trades.extend(data)
    return jsonify(all_trades)

@app.route('/api/freqtrade/balance')
def freqtrade_balance():
    """Get balance from first active bot."""
    for bot in FREQTRADE_BOTS:
        data = _ft_get('balance', bot['port'])
        if data:
            return jsonify(data)
    return jsonify({'total': 0, 'starting': 0, 'free': 0, 'used': 0})

@app.route('/api/freqtrade/performance')
def freqtrade_performance():
    """Aggregate performance from all bots."""
    perf_map = {}
    for bot in FREQTRADE_BOTS:
        data = _ft_get('performance', bot['port'])
        if data and isinstance(data, list):
            for p in data:
                pair = p.get('pair', '')
                if pair not in perf_map:
                    perf_map[pair] = {'pair': pair, 'profit_pct': 0, 'profit_abs': 0, 'count': 0}
                perf_map[pair]['profit_pct'] += p.get('profit_pct', 0)
                perf_map[pair]['profit_abs'] += p.get('profit_abs', 0)
                perf_map[pair]['count'] += p.get('count', 1)
    return jsonify(list(perf_map.values()))

# ============ TRADING QUEUE API ============

@app.route('/api/trading/queue')
def trading_queue():
    """Hyperopt Queue Status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT id, strategie, status, priority, created_at, started_at, finished_at
            FROM v_hyperopt_queue
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

# ============ IFG DASHBOARD API ============



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

# ============ Agent Tasks (Workflow / Task Control Center) ============
# Quelle: sias_tasks Tabelle (task_type='GENERAL') — live aus der metamaus DB


@app.route('/api/db/tasks', methods=['GET'])
def get_agent_tasks():
    """Workflow-Ansicht: Alle sias_tasks (GENERAL) live aus der DB"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        agent_filter = request.args.get('agent')
        status_filter = request.args.get('status')

        where_parts = ["task_type = 'GENERAL'"]
        params = []

        if agent_filter:
            where_parts.append('agent_id = %s')
            params.append(agent_filter)
        if status_filter:
            where_parts.append('status = %s')
            params.append(status_filter)

        where_sql = f"WHERE {' AND '.join(where_parts)}"

        cursor.execute(f"""
            SELECT id, agent_id as agent, task, priority, status,
                   created_at, started_at, completed_at as done_at,
                   result::text as result, created_by
            FROM sias_tasks
            {where_sql}
            ORDER BY
                CASE status
                    WHEN 'pending' THEN 1
                    WHEN 'in_progress' THEN 2
                    WHEN 'stopped' THEN 3
                    WHEN 'done' THEN 4
                    ELSE 5
                END,
                priority DESC,
                created_at DESC
        """, params)

        tasks = cursor.fetchall()
        cursor.close()
        conn.close()

        result_list = []
        counts = {'pending': 0, 'in_progress': 0, 'stopped': 0, 'done': 0, 'total': 0}

        for t in tasks:
            d = dict(t)
            for col in ('created_at', 'started_at', 'done_at'):
                if d.get(col):
                    d[col] = str(d[col])
            # Fortschritt berechnen
            progress = 0
            if d['status'] == 'pending':
                progress = 0
            elif d['status'] == 'in_progress':
                progress = 50
            elif d['status'] in ('done', 'stopped'):
                progress = 100
            d['progress'] = progress
            result_list.append(d)
            status = d['status']
            if status in counts:
                counts[status] += 1
        counts['total'] = len(result_list)

        return jsonify({'status': 'success', 'tasks': result_list, 'counts': counts})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/db/tasks', methods=['POST'])
def create_agent_task():
    """Neuen Task in sias_tasks (GENERAL) einwerfen"""
    try:
        data = request.get_json()
        agent = data.get('agent', 'apollon')
        task = data.get('task', '')
        priority = data.get('priority', 5)
        created_by = data.get('created_by', 'iggy')

        if not task:
            return jsonify({'status': 'error', 'message': 'Task ist leer'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO sias_tasks (task_type, agent_id, task, priority, created_by)
            VALUES ('GENERAL', %s, %s, %s, %s)
            RETURNING id
        """, (agent, task, int(priority), created_by))

        new_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'status': 'success', 'id': new_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/db/tasks/<int:task_id>/stop', methods=['POST'])
def stop_agent_task(task_id):
    """Task stoppen (auf 'stopped' setzen)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE sias_tasks
            SET status = 'stopped', completed_at = NOW(),
                result = to_jsonb(COALESCE(result::text, '') || ' [manuell gestoppt]')
            WHERE id = %s AND status IN ('pending', 'in_progress') AND task_type = 'GENERAL'
            RETURNING id
        """, (task_id,))

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        if result:
            return jsonify({'status': 'success', 'msg': f'Task {task_id} gestoppt'})
        return jsonify({'status': 'error', 'message': 'Task nicht gefunden oder bereits beendet'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/db/tasks/<int:task_id>/status', methods=['PATCH'])
def update_agent_task_status(task_id):
    """Status eines agent_tasks ändern"""
    try:
        data = request.get_json()
        new_status = data.get('status', '')
        if new_status not in ('pending', 'in_progress', 'done', 'stopped', 'failed'):
            return jsonify({'status': 'error', 'message': 'Ungültiger Status'}), 400

        now_cols = []
        now_vals = []
        if new_status == 'in_progress':
            now_cols.append('started_at = NOW()')
        elif new_status in ('done', 'stopped', 'failed'):
            now_cols.append('completed_at = NOW()')

        set_clause = f"status = %s, {', '.join(now_cols)}" if now_cols else 'status = %s'

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"""
            UPDATE sias_tasks SET {set_clause}
            WHERE id = %s AND task_type = 'GENERAL' RETURNING id
        """, (new_status, task_id))

        result = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()

        if result:
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Task nicht gefunden'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============ YouTube Community API ============


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


@app.route('/api/hestia/pipeline', methods=['GET'])
def get_hestia_pipeline():
    """Hestia Pipeline: alle Einträge sortiert nach created_at DESC"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT id, video_id, video_title, short_number, status, file_path, scheduled_release, released_at, youtube_short_id, created_at FROM hestia_pipeline ORDER BY created_at DESC")
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            for col in ('scheduled_release', 'released_at', 'created_at'):
                if d.get(col):
                    d[col] = d[col].isoformat() if hasattr(d[col], 'isoformat') else str(d[col])
            result.append(d)
        cursor.close()
        conn.close()
        return jsonify({'status': 'success', 'items': result, 'count': len(result)})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

YOUTUBE_API_KEY = "AIzaSyD_bbGPhXLOsZqzEva2ZPpNzka8YViFz8c"

# Serve dashboard HTML

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


@app.route('/api/hestia/comments/<int:comment_id>/suggestions', methods=['GET'])
def hestia_comment_suggestions(comment_id):
    """Return 2 hardcoded reply suggestions for a comment (LLM stub)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT text FROM yt_comments WHERE id = %s", (comment_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return jsonify({'status': 'error', 'message': 'Comment not found'}), 404
        comment_text = (row[0] or '').lower()
        # Context-aware stub suggestions
        if any(w in comment_text for w in ['danke', 'super', 'toll', 'genial']):
            suggestions = ["Danke dir! \U0001f42d", "Freut mich! \U0001f60a"]
        elif any(w in comment_text for w in ['merz', 'burns', 'spahn']):
            suggestions = ["Genau das! \U0001f3af", "Die Show l\u00e4uft! \U0001f604"]
        elif any(w in comment_text for w in ['frage', 'bitte', 'wann']):
            suggestions = ["Gute Frage! \U0001f4a1", "Danke f\u00fcrs Fragen! \U0001f42d"]
        else:
            suggestions = ["Danke f\u00fcr deinen Kommentar! \U0001f42d", "Guter Punkt! \U0001f44d"]
        return jsonify({'status': 'success', 'suggestions': suggestions})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/hestia/comments/<int:comment_id>/reply', methods=['POST'])
def hestia_comment_reply(comment_id):
    """Save reply text and mark comment as replied"""
    try:
        data = request.get_json()
        reply_text = data.get('text', '')
        if not reply_text.strip():
            return jsonify({'status': 'error', 'message': 'Empty reply'}), 400
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT comment_id FROM yt_comments WHERE id = %s", (comment_id,))
        row = cur.fetchone()
        if not row:
            cur.close(); conn.close()
            return jsonify({'status': 'error', 'message': 'Comment not found'}), 404
        yt_cid = row[0]
        cur.execute("""
            INSERT INTO yt_comments (comment_id, video_id, author_channel_id, author_name, text, parent_id, is_reply, reply_status)
            VALUES (%s, NULL, '@iggyswelt', '@iggyswelt', %s, %s, true, 'replied')
        """, (yt_cid + '_reply', reply_text, yt_cid))
        cur.execute("UPDATE yt_comments SET reply_status='replied', reply_count = COALESCE(reply_count,0)+1 WHERE id=%s", (comment_id,))
        conn.commit()
        cur.close(); conn.close()
        return jsonify({'status': 'success'})
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

# Himalaya binary & PATH
_HIMALAYA_BIN = '/home/linuxbrew/.linuxbrew/bin/himalaya'
_HIMALAYA_PATH = '/home/linuxbrew/.linuxbrew/bin'

def _himalaya_env() -> dict:
    """Return environment with himalaya binary in PATH."""
    env = dict(os.environ)
    env['PATH'] = _HIMALAYA_PATH + ':' + env.get('PATH', '')
    env['HOME'] = '/home/iggy'
    return env


def _himalaya_list(folder: str, max_count: int = 50) -> list:
    """List envelopes from a given folder via himalaya CLI, return parsed dicts."""
    try:
        result = subprocess.run(
            [_HIMALAYA_BIN, '-o', 'json', 'envelope', 'list', '-f', folder, '--', 'order by date desc'],
            capture_output=True, text=True, timeout=30,
            env=_himalaya_env(),
            cwd='/home/iggy'
        )
        if result.returncode == 0 and result.stdout.strip():
            raw = json.loads(result.stdout)
            if isinstance(raw, list):
                return raw[:max_count]
        return []
    except Exception as e:
        print(f'Himalaya list error ({folder}): {e}')
        return []


def _himalaya_read(env_id: str, folder: str = 'INBOX') -> dict:
    """Read full message body for a given envelope id via himalaya CLI."""
    try:
        result = subprocess.run(
            [_HIMALAYA_BIN, 'message', 'read', '--account', 'abydon', '-f', folder, env_id],
            capture_output=True, text=True, timeout=30,
            env=_himalaya_env(),
            cwd='/home/iggy'
        )
        return {
            'folder': folder,
            'id': env_id,
            'body': result.stdout if result.returncode == 0 else f'Error: {result.stderr}',
        }
    except Exception as e:
        return {'folder': folder, 'id': env_id, 'body': f'Exception: {e}'}

HIMALAYA_FOLDERS = {
    'inbox': 'INBOX',
    'sent': 'INBOX.Sent',
    'drafts': 'INBOX.Drafts',
}


@app.route('/api/mails/himalaya', methods=['GET'])
def himalaya_mails():
    """List emails from himalaya. Query params: folder=inbox|sent|drafts, limit=N"""
    try:
        folder_key = request.args.get('folder', 'inbox').lower()
        folder = HIMALAYA_FOLDERS.get(folder_key, HIMALAYA_FOLDERS['inbox'])
        limit = min(int(request.args.get('limit', 50)), 200)

        envelopes = _himalaya_list(folder, limit)

        # Normalize envelope data for frontend
        normalized = []
        for env in envelopes:
            sender = env.get('from', {})
            sender_name = sender.get('name', '') or sender.get('addr', '')
            recipient = env.get('to', {})
            recipient_name = recipient.get('name', '') or recipient.get('addr', '')
            normalized.append({
                'id': env.get('id', ''),
                'from': sender_name,
                'from_addr': sender.get('addr', ''),
                'to': recipient_name,
                'to_addr': recipient.get('addr', ''),
                'subject': env.get('subject', '(kein Betreff)'),
                'date': env.get('date', ''),
                'flags': env.get('flags', []),
                'has_attachment': env.get('has_attachment', False),
                'folder': folder_key,
            })

        return jsonify({'status': 'success', 'folder': folder_key, 'emails': normalized, 'count': len(normalized)})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route('/api/mails/himalaya/read', methods=['POST'])
def himalaya_mail_read():
    """Read a single email body. Body: {id, folder}"""
    try:
        data = request.json
        env_id = data.get('id', '')
        folder_key = data.get('folder', 'inbox').lower()
        folder = HIMALAYA_FOLDERS.get(folder_key, HIMALAYA_FOLDERS['inbox'])

        mail_data = _himalaya_read(env_id, folder)
        return jsonify({'status': 'success', **mail_data})
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# ============ FREQTRADE LIVE API (Multi-Bot) ============
FREQTRADE_BOTS = [
    {'name': 'bot_01', 'port': 8080, 'user': 'freqtrader', 'password': 'SuperSecurePassword'},
    # Add more bots here when available:
    # {'name': 'bot_02', 'port': 8081, 'user': 'freqtrader', 'password': 'SuperSecurePassword'},
]


def send_smtp_mail(to_email, subject, body):
    password = get_smtp_password()
    if not password:
        return False, "No SMTP password"

    # NO auto-signature: body is sent as-is (user controls everything in text_entwurf/text_final)
    msg = EmailMessage()
    msg.set_content(body)
    msg["From"] = '"Igwemo Pielczyk" <investigativ@abydon.com>'
    msg["To"] = to_email
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

@app.route('/api/news/woke-filter', methods=['GET'])
def get_woke_filtered_news():
    """Vogue-Filter: News mit ideologischen Keywords in title/summary.
    Kombiniert rheingold_buzzwords DB + hardcoded Vogue-Keywords."""
    try:
        active = request.args.get('active', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))

        if not active:
            return jsonify({'status': 'success', 'articles': [], 'filtered': False, 'count': 0})

        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        vogue_keywords = [
            'Gendern', 'gendern', 'Gendersprache', 'Diversität', 'Diversity',
            'Quote', 'quotiert', 'Quoten', 'Sensibilisierung',
            'diskriminierend', 'Diskriminierung', 'Sexismus', 'Rassismus',
            'klimaneutral', 'Klimaneutralität', 'nachhaltig', 'Nachhaltigkeit',
            'woke', 'Woke', 'DEI', 'Diversity Equity', 'ESG',
            'Inklusion', 'Inklusiv', 'Barrierefreiheit', 'Teilhabe',
            'Klimaschutz', 'Klimakrise', 'Klimawandel',
            'Transgender', 'transgender', 'nicht-binär', 'nichtbinär',
            'Pronomen', 'geschlechtergerecht', 'geschlechterneutral'
        ]

        # Build conditions from DB buzzwords AND hardcoded keywords
        conditions = []
        params = []

        # Try rheingold_buzzwords if table exists
        try:
            cursor.execute("SELECT begriff FROM rheingold_buzzwords")
            buzzwords = [row['begriff'] for row in cursor.fetchall()]
            for bw in buzzwords:
                conditions.append("(na.title ILIKE %s OR na.summary ILIKE %s)")
                params.extend([f'%{bw}%', f'%{bw}%'])
        except Exception:
            pass

        # Always add hardcoded keywords as fallback
        for kw in vogue_keywords:
            conditions.append("(na.title ILIKE %s OR na.summary ILIKE %s)")
            params.extend([f'%{kw}%', f'%{kw}%'])

        if not conditions:
            cursor.close(); conn.close()
            return jsonify({'status': 'success', 'articles': [], 'filtered': False, 'count': 0})

        where_clause = ' OR '.join(conditions)

        relevance_clause = """CASE ns.category
            WHEN 'politik' THEN 100
            WHEN 'afd' THEN 90
            WHEN 'popkultur' THEN 70
            ELSE 50
        END"""

        query = f"""
            SELECT DISTINCT ON (na.id) na.*, ns.name as source_name, ns.category as source_category,
                   {relevance_clause} as relevance_score
            FROM news_articles na
            JOIN news_sources ns ON na.source_id = ns.id
            WHERE {where_clause}
            ORDER BY na.id, na.published_at DESC NULLS LAST
            LIMIT %s
        """
        params.append(limit)

        cursor.execute(query, params)
        articles = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for a in articles:
            d = dict(a)
            d['published_at'] = d['published_at'].isoformat() if d.get('published_at') else None
            d['relevance_score'] = d.get('relevance_score', 50)
            result.append(d)

        return jsonify({
            'status': 'success',
            'articles': result,
            'filtered': True,
            'count': len(result),
            'keyword_count': len(vogue_keywords)
        })
    except Exception as e:
        import traceback
        return jsonify({'status': 'error', 'message': str(e), 'trace': traceback.format_exc()}), 500


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


@app.route('/api/gateway/usage')
def gateway_usage():
    """Gateway token usage per agent — scans OpenClaw session files + reads model config."""
    try:
        import glob
        oc_cfg = json.load(open('/home/iggy/.openclaw/openclaw.json'))
        agent_models = {}
        for a in oc_cfg.get('agents', {}).get('list', []):
            aid = a.get('id', '')
            agent_models[aid] = a.get('model', {}).get('primary', 'unknown')

        agents = []
        sessions_base = '/home/iggy/.openclaw/agents'
        for agent_id in agent_models:
            sess_dir = os.path.join(sessions_base, agent_id, 'sessions')
            sess_file = os.path.join(sess_dir, 'sessions.json')
            total_tokens = 0
            session_count = 0
            if os.path.exists(sess_file):
                try:
                    data = json.load(open(sess_file))
                    # Count all session keys
                    session_count = len(data) if isinstance(data, dict) else 0
                    # Sum tokens from each session
                    for key, val in data.items():
                        if isinstance(val, dict):
                            total_tokens += val.get('totalTokens', 0) or val.get('tokensUsed', 0) or 0
                            total_tokens += val.get('inputTokens', 0) or 0
                            total_tokens += val.get('outputTokens', 0) or 0
                except:
                    pass

            agents.append({
                'name': agent_id,
                'model': agent_models[agent_id],
                'sessions': session_count,
                'total_tokens': total_tokens
            })

        return jsonify({'agents': agents, 'count': len(agents)})
    except Exception as e:
        return jsonify({'agents': [], 'error': str(e)}), 500

# ============ ENDE FIXES ============



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


@app.route('/ifg')
def ifg_page():
    """IFG Dashboard — Zeigt alle IFG-Anfragen mit Status, Draft-Vorschau, Senden-Button"""
    return render_template('ifg.html')


@app.route('/api/ifg')
def api_ifg_list():
    """GET: Alle IFG-Anfragen mit zugehörigen Mails"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # IFG requests
        cur.execute("""
            SELECT r.id, r.behoerde, r.titel, r.status, r.frist_am, r.gesendet_am,
                   r.empfaenger_email, r.notizen,
                   (SELECT COUNT(*) FROM rheingold_mails m WHERE m.ifg_request_id = r.id) as mail_count
            FROM rheingold_requests r
            ORDER BY r.id DESC
        """)
        requests = cur.fetchall()
        # Mails for each request
        for req in requests:
            cur.execute("""
                SELECT id, an, betreff, status, erstellt_am, gesendet_am, absender
                FROM rheingold_mails
                WHERE ifg_request_id = %s
                ORDER BY id DESC
            """, (req['id'],))
            req['mails'] = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'status': 'success', 'requests': requests})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



@app.route('/api/ifg/<int:ifg_id>')
def api_ifg_detail(ifg_id):
    """GET: IFG-Detail mit allen Mails und agent_knowledge Daten"""
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        # IFG request
        cur.execute("SELECT * FROM rheingold_requests WHERE id = %s", (ifg_id,))
        ifg = cur.fetchone()
        if not ifg:
            return jsonify({'status': 'error', 'message': 'IFG request not found'}), 404
        # Mails
        cur.execute("""
            SELECT id, an, betreff, text_entwurf, text_final, status, erstellt_am, gesendet_am, kategorie, absender
            FROM rheingold_mails
            WHERE ifg_request_id = %s
            ORDER BY id DESC
        """, (ifg_id,))
        ifg['mails'] = cur.fetchall()
        # agent_knowledge status
        cur.execute("SELECT key, value FROM agent_knowledge WHERE key LIKE 'ifg%_status%' ORDER BY key")
        knowledge_rows = cur.fetchall()
        ifg['knowledge'] = {r['key']: r['value'] for r in knowledge_rows}
        cur.close()
        conn.close()
        return jsonify({'status': 'success', 'ifg': ifg})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500



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
        cur.execute("SELECT COUNT(*) FROM sias_tasks WHERE task_type = 'CRAWL' AND status = 'pending'")
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

# ==================== NEWS RSS READER V3 ====================
import feedparser

RSS_SOURCES = {
    'tichy': 'https://www.tichyseinblick.de/feed/',
    'jf': 'https://jungefreiheit.de/feed/',
    'nius': 'https://www.nius.de/rss/feed',
    'blackout': 'https://blackout-news.de/feed/',
    'tpp': 'https://thatparkplace.com/feed/',
    'kia': 'https://www.reddit.com/r/KotakuInAction/.rss',
    'fandom': 'https://fandompulse.net/feed/',
    'ign': 'https://de.ign.com/feed.xml',
    'insider': 'https://insider-gaming.com/feed/',
}

_news_rss_cache = {}
_news_rss_ts = {}
NEWS_CACHE_TTL = 1800  # 30 minutes


@app.route('/api/news/fetch', methods=['GET'])
def api_news_rss_fetch():
    """Fetch RSS feed by source name (GET ?source=apollo)"""
    source = request.args.get('source', '')
    if source not in RSS_SOURCES:
        return jsonify({'error': 'unknown source'}), 404

    url = RSS_SOURCES[source]
    now = time.time()

    if source in _news_rss_cache and now - _news_rss_ts.get(source, 0) < NEWS_CACHE_TTL:
        return jsonify(_news_rss_cache[source])

    try:
        d = feedparser.parse(url)
        items = []
        for entry in d.entries[:25]:
            title = entry.get('title', '')
            link = entry.get('link', '')
            pub = entry.get('published', '')
            summary = ''
            if hasattr(entry, 'summary'):
                summary = entry.summary[:300]
            elif hasattr(entry, 'description'):
                summary = entry.description[:300]
            items.append({
                'title': title,
                'url': link,
                'published': pub,
                'source': source,
                'summary': summary
            })
        _news_rss_cache[source] = items
        _news_rss_ts[source] = now
        return jsonify(items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === HESTIA YouTube Pin-Comment Routes ===
import pickle as _pickle

# Pin-Kommentar Template
PIN_COMMENT_TEMPLATE = """🎬 {title}

💙 Unterstützung für Iggy's Welt:
├ 💳 PayPal: iggyswelt@abydon.com
├ ₿ BTC: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
├ ◎ SOL: SoM1Yf9YTZB8XhSp3VRe2x3R4M8qN4qtt87ndWbEgFf
├ ☕ Ko-Fi: https://ko-fi.com/iggyswelt
└ 🛒 Shop: http://shop.abydon.com/

🔔 Abo + 🔔 Glocke nicht vergessen!

#IggysWelt #Politik #Popkultur"""

def _load_youtube_oauth_config():
    """Load YouTube OAuth client config from adm directory."""
    import glob
    config_files = glob.glob('/home/iggy/.openclaw/adm/client_secret_*.json')
    if not config_files:
        return None
    with open(config_files[0]) as f:
        data = json.load(f)
    # Support both 'web' and 'installed' key formats
    return data.get('web') or data.get('installed') or data

def _load_youtube_token():
    """Load YouTube OAuth token from pickle file."""
    token_path = '/home/iggy/.secrets/youtube_token.pkl'
    if not os.path.exists(token_path):
        return None
    try:
        with open(token_path, 'rb') as f:
            return _pickle.load(f)
    except Exception as e:
        print(f"ERROR loading YouTube token: {e}")
        return None

def _save_youtube_token(creds):
    """Save YouTube OAuth token to pickle file."""
    token_dir = '/home/iggy/.secrets'
    os.makedirs(token_dir, exist_ok=True)
    token_path = os.path.join(token_dir, 'youtube_token.pkl')
    with open(token_path, 'wb') as f:
        _pickle.dump(creds, f)
    os.chmod(token_path, 0o600)


@app.route('/api/hestia/youtube-auth', methods=['GET'])
def hestia_youtube_auth_status():
    """Zeigt OAuth-Status für YouTube API."""
    config = _load_youtube_oauth_config()
    token = _load_youtube_token()
    result = {
        'config_loaded': config is not None,
        'has_client_id': bool(config and config.get('client_id')) if config else False,
        'token_exists': token is not None,
        'token_valid': False,
    }
    if token:
        try:
            from google.oauth2.credentials import Credentials
            if isinstance(token, Credentials):
                result['token_valid'] = token.valid
                result['token_expired'] = token.expired if hasattr(token, 'expired') else None
                result['has_refresh_token'] = bool(token.refresh_token) if hasattr(token, 'refresh_token') else False
        except ImportError:
            result['token_valid'] = True  # Assume valid if we can't check
    if not result['config_loaded']:
        return jsonify({'status': 'error', 'message': 'YouTube OAuth Config nicht gefunden', **result}), 500
    if not result['token_exists']:
        return jsonify({'status': 'auth_required', 'message': 'YouTube OAuth Token fehlt. Token generieren via /home/iggy/sias-youtube/get_youtube_token.py', **result}), 401
    return jsonify({'status': 'ok', **result})


def _hestia_generate_comment(title: str, description: str) -> str:
    """Generate a pinned comment via OpenClaw Gateway AI."""
    import subprocess, json as _json
    prompt = (
        f"Du bist Iggy von Iggy's Welt (YouTube-Kanal für Politik & Popkultur). "
        f"Schreibe einen authentischen, gepinnten Kommentar für dein eigenes Video.\n"
        f"Titel: {title}\nBeschreibung: {description}\n\n"
        f"Regeln: Beziehe dich INHALTLICH auf das Thema des Videos! "
        f"Kein generisches 'Danke fürs Zuschauen'. "
        f"Analysiere den Video-Titel und schreibe einen Einstieg, der zum Thema passt. "
        f"3-5 Sätze, themenspezifisch, authentischer Ton. "
        f"Am Ende GENAU diese Support-Box (nicht verändern):\n"
        f"\n"
        f"💰 Unterstütze den Channel:\n"
        f"PayPal: iggyswelt@abydon.com\n"
        f"BTC: bc1q3pgg77pcvhg3xqqe7cxzvwpvu9tsnte9xywc8l\n"
        f"SOL: AG2oTNmuniY4LuzQ4ZH5K42ZXMV2d3vQ6AP5GErxGZyi\n"
        f"☕️ Ko-Fi: https://ko-fi.com/iggyswelt\n"
        f"👕 Shop: http://shop.abydon.com/"
    )
    try:
        # Use OpenClaw CLI as AI backend
        result = subprocess.run(
            ['openclaw', 'ask', '--agent', 'hestia', '--no-stream', prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    # Fallback: themenspezifisch basierend auf Video-Titel
    import re
    thema = title.split('|')[0].split('—')[0].strip() if title else 'das Thema'
    return (
        f"In diesem Video geht es um {thema}. "
        f"Was denkt ihr darüber? Schreibt es in die Kommentare!\n\n"
        f"💰 Unterstütze den Channel:\n"
        f"PayPal: iggyswelt@abydon.com\n"
        f"BTC: bc1q3pgg77pcvhg3xqqe7cxzvwpvu9tsnte9xywc8l\n"
        f"SOL: AG2oTNmuniY4LuzQ4ZH5K42ZXMV2d3vQ6AP5GErxGZyi\n"
        f"☕️ Ko-Fi: https://ko-fi.com/iggyswelt\n"
        f"👕 Shop: http://shop.abydon.com/"
    )


@app.route('/api/hestia/write-comment', methods=['POST'])
def hestia_write_comment():
    """Generate a pinned comment for a YouTube video (>4min only)."""
    try:
        data = request.get_json(force=True)
        video_id = data.get('video_id', '')
        title = data.get('title', '')
        duration_seconds = int(data.get('duration_seconds', 0))
        description = data.get('description', '')

        # Shorts filter
        if duration_seconds < 240:
            return jsonify({'status': 'skipped', 'message': 'Short/Video unter 4 Minuten — übersprungen'}), 200

        # Check if comment already exists
        conn = get_db_connection()
        cur = conn.cursor()
        key = f'hestia_comment_{video_id}'
        cur.execute("SELECT value FROM agent_knowledge WHERE key = %s", (key,))
        existing = cur.fetchone()
        if existing:
            cur.close()
            conn.close()
            return jsonify({'status': 'exists', 'comment': existing[0], 'video_id': video_id}), 200

        # Generate comment
        comment_text = _hestia_generate_comment(title, description)

        # Save to DB
        import json as _json
        comment_data = _json.dumps({
            'video_id': video_id,
            'title': title,
            'comment': comment_text,
            'duration_seconds': duration_seconds,
            'posted': False,
            'created_at': datetime.datetime.now().isoformat()
        })
        cur.execute("""
            INSERT INTO agent_knowledge (category, key, value)
            VALUES ('hestia_comment', %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, comment_data))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({'status': 'success', 'comment': comment_text, 'video_id': video_id}), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/hestia/pending-comments', methods=['GET'])
def hestia_pending_comments():
    """Show all comments not yet posted."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT key, value FROM agent_knowledge WHERE key LIKE 'hestia_comment_%' ORDER BY key DESC")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        import json as _json
        pending = []
        for key, value in rows:
            try:
                d = _json.loads(value)
                if not d.get('posted', False):
                    pending.append(d)
            except _json.JSONDecodeError:
                pass
        return jsonify({'status': 'success', 'pending': pending, 'count': len(pending)}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/hestia/mark-posted/<video_id>', methods=['POST'])
def hestia_mark_posted(video_id):
    """Mark a comment as posted."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        key = f'hestia_comment_{video_id}'
        cur.execute("SELECT value FROM agent_knowledge WHERE key = %s", (key,))
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({'status': 'error', 'message': 'Kommentar nicht gefunden'}), 404
        import json as _json
        d = _json.loads(row[0])
        d['posted'] = True
        d['posted_at'] = datetime.datetime.now().isoformat()
        cur.execute("UPDATE agent_knowledge SET value = %s WHERE key = %s", (_json.dumps(d), key))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'status': 'success', 'video_id': video_id}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/hestia/pin-comment', methods=['POST'])
def hestia_pin_comment():
    """Postet und pinnt einen Support-Kommentar unter einem YouTube Video."""
    try:
        data = request.get_json()
        video_id = data.get('video_id', '').strip()
        title = data.get('title', '').strip()
        description = data.get('description', '')

        if not video_id:
            return jsonify({'status': 'error', 'message': 'video_id fehlt'}), 400

        # 1. OAuth Token prüfen
        token = _load_youtube_token()
        if not token:
            return jsonify({
                'status': 'auth_required',
                'message': 'YouTube OAuth Token fehlt. Token generieren via /home/iggy/sias-youtube/get_youtube_token.py'
            }), 401

        # 2. YouTube API Client bauen
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
        except ImportError:
            return jsonify({'status': 'error', 'message': 'google-api-python-client nicht installiert. Pip install benötigt.'}), 500

        # Token refresh falls nötig
        config = _load_youtube_oauth_config()
        if isinstance(token, Credentials) and token.expired and token.refresh_token:
            from google.auth.transport.requests import Request
            token.refresh(Request())
            _save_youtube_token(token)

        youtube = build('youtube', 'v3', credentials=token)

        # 3. Pin-Text generieren
        pin_text = PIN_COMMENT_TEMPLATE.format(title=title or video_id)

        # 4. Kommentar posten (commentThreads.insert)
        comment_body = {
            'snippet': {
                'videoId': video_id,
                'topLevelComment': {
                    'snippet': {
                        'textOriginal': pin_text
                    }
                }
            }
        }
        comment_response = youtube.commentThreads().insert(
            part='snippet',
            body=comment_body
        ).execute()

        comment_id = comment_response['id']

        # 5. Kommentar pinnen (comments.setModerationStatus)
        # YouTube uses commentThreads.setModerationStatus for pinning
        # Actually: comments.setModerationStatus with banStatus='pin'
        # Correct API: commentThreads don't have pin. We need comments.setModerationStatus
        try:
            youtube.comments().setModerationStatus(
                id=comment_id,
                moderationStatus='published'
            ).execute()
            # Pin via commentThreads - set as pinned
            # NOTE: YouTube API doesn't have a direct "pin" endpoint.
            # Pinning must be done manually in YouTube Studio.
            # We post the comment and flag it for manual pinning.
        except Exception as pin_err:
            print(f"Pin warning: {pin_err}")

        # 6. In DB speichern
        conn = get_db_connection()
        cur = conn.cursor()
        key = f'hestia_pin_{video_id}'
        pin_data = json.dumps({
            'video_id': video_id,
            'title': title,
            'comment_id': comment_id,
            'pinned_at': datetime.datetime.now().isoformat(),
            'status': 'posted_manual_pin_required'
        })
        cur.execute("""
            INSERT INTO agent_knowledge (category, key, value)
            VALUES ('hestia_pin', %s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
        """, (key, pin_data))
        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            'status': 'success',
            'message': 'Kommentar gepostet. Pinnen muss manuell in YouTube Studio erfolgen (API unterstützt kein Pinning direkt).',
            'comment_id': comment_id,
            'video_id': video_id,
            'manual_pin_required': True
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ============================================================
# YouTube API Routes (API Key — no OAuth, no pickle, no google-auth)
# ============================================================


def _parse_iso8601_duration(duration: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to total seconds."""
    if not duration:
        return 0
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _format_video_item(item: dict) -> dict:
    """Format a YouTube video item into our standard response format."""
    snippet = item.get('snippet', {})
    content_details = item.get('contentDetails', {})
    statistics = item.get('statistics', {})
    video_id = item.get('id', '')
    if isinstance(video_id, dict):
        video_id = video_id.get('videoId', '')
    duration_seconds = _parse_iso8601_duration(content_details.get('duration', ''))
    thumbnails = snippet.get('thumbnails', {})
    thumbnail = ''
    for quality in ['high', 'medium', 'default']:
        if quality in thumbnails:
            thumbnail = thumbnails[quality].get('url', '')
            break
    return {
        'id': video_id,
        'title': snippet.get('title', ''),
        'description': snippet.get('description', ''),
        'published': snippet.get('publishedAt', ''),
        'thumbnail': thumbnail,
        'duration_seconds': duration_seconds,
        'is_short': duration_seconds > 0 and duration_seconds < 60,
        'views': int(statistics.get('viewCount', 0)),
        'url': f'https://www.youtube.com/watch?v={video_id}',
    }


@app.route('/api/youtube/videos')
def api_youtube_videos():
    """Get the 20 most recent videos from IggysWelt via API Key."""
    try:
        # 1) Resolve channel ID via handle
        chan_resp = req_lib.get(
            'https://www.googleapis.com/youtube/v3/channels',
            params={'part': 'id', 'forHandle': 'IggysWelt', 'key': YOUTUBE_API_KEY},
            timeout=10,
        )
        chan_data = chan_resp.json()
        if not chan_data.get('items'):
            return jsonify({'error': 'Channel IggysWelt nicht gefunden.'}), 404
        channel_id = chan_data['items'][0]['id']

        # 2) Search latest 20 videos
        search_resp = req_lib.get(
            'https://www.googleapis.com/youtube/v3/search',
            params={
                'part': 'snippet',
                'channelId': channel_id,
                'maxResults': 20,
                'order': 'date',
                'type': 'video',
                'key': YOUTUBE_API_KEY,
            },
            timeout=10,
        )
        search_data = search_resp.json()
        video_ids = [
            item['id']['videoId']
            for item in search_data.get('items', [])
            if item.get('id', {}).get('videoId')
        ]
        if not video_ids:
            return jsonify([])

        # 3) Get details (snippet + contentDetails + statistics)
        details_resp = req_lib.get(
            'https://www.googleapis.com/youtube/v3/videos',
            params={
                'part': 'snippet,contentDetails,statistics',
                'id': ','.join(video_ids),
                'key': YOUTUBE_API_KEY,
            },
            timeout=10,
        )
        details_data = details_resp.json()
        videos = [_format_video_item(v) for v in details_data.get('items', [])]
        return jsonify(videos)

    except Exception as e:
        return jsonify({'error': f'YouTube API Fehler: {str(e)}'}), 500


@app.route('/api/youtube/video/<video_id>')
def api_youtube_video_detail(video_id: str):
    """Get details for a single YouTube video by ID via API Key."""
    try:
        resp = req_lib.get(
            'https://www.googleapis.com/youtube/v3/videos',
            params={
                'part': 'snippet,contentDetails,statistics',
                'id': video_id,
                'key': YOUTUBE_API_KEY,
            },
            timeout=10,
        )
        data = resp.json()
        if not data.get('items'):
            return jsonify({'error': f'Video {video_id} nicht gefunden.'}), 404

        return jsonify(_format_video_item(data['items'][0]))

    except Exception as e:
        return jsonify({'error': f'YouTube API Fehler: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=False)