#!/usr/bin/env python3
"""Smart Reporting System - Consolidates all checks into 3 daily reports"""
import subprocess
import json
from datetime import datetime, timedelta

def run_sql(sql):
    """Run SQL via subprocess"""
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'demo_scraper', '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def save_status(component, status, details):
    """Save status to DB, update if exists"""
    details_json = json.dumps(details).replace("'", "''")
    sql = f"""
        INSERT INTO system_status (component, status, details, timestamp)
        VALUES ('{component}', '{status}', '{details_json}', NOW())
    """
    run_sql(sql)

def check_vault():
    """Check vault status"""
    secrets = run_sql("SELECT COUNT(*) FROM secrets")
    save_status('vault', 'ok', {'secrets': int(secrets) if secrets else 0})
    return {'secrets': int(secrets) if secrets else 0}

def check_pki():
    """Check PKI certificates"""
    count = run_sql("SELECT COUNT(*) FROM orpheus_certificates WHERE expires_at < NOW() + INTERVAL '7 days'")
    count = int(count) if count else 0
    status = 'error' if count > 0 else 'ok'
    save_status('pki', status, {'expiring_7d': count})
    return {'expiring_7d': count}

def check_athene():
    """Check ATHENE trades"""
    trades = run_sql("SELECT COUNT(*) FROM athene_trades WHERE timestamp > NOW() - INTERVAL '24 hours'")
    trades = int(trades) if trades else 0
    save_status('athene', 'ok', {'trades_24h': trades})
    return {'trades_24h': trades}

def check_hestia():
    """Check HESTIA YouTube comments"""
    result = run_sql("SELECT reply_status, COUNT(*) FROM yt_comments GROUP BY reply_status")
    pending = 0
    replied = 0
    if result:
        for line in result.split('\n'):
            if 'pending' in line:
                pending = int(line.split('|')[1].strip())
            if 'replied' in line:
                replied = int(line.split('|')[1].strip())
    save_status('hestia', 'ok', {'pending': pending, 'replied': replied})
    return {'pending': pending, 'replied': replied}

def check_security():
    """Check security (failed logins)"""
    try:
        result = subprocess.run(
            ['sudo', 'grep', '-c', 'Failed password', '/var/log/auth.log'],
            capture_output=True, text=True, timeout=5
        )
        failed = int(result.stdout.strip()) if result.returncode == 0 else 0
        save_status('security', 'ok', {'failed_logins': failed})
        return {'failed_logins': failed}
    except:
        save_status('security', 'ok', {'failed_logins': 0})
        return {'failed_logins': 0}

def check_learnings():
    """Check learnings today"""
    count = run_sql("SELECT COUNT(*) FROM learnings WHERE created_at::date = CURRENT_DATE")
    count = int(count) if count else 0
    total = run_sql("SELECT COUNT(*) FROM learnings")
    total = int(total) if total else 0
    save_status('learnings', 'ok', {'today': count, 'total': total})
    return {'today': count, 'total': total}

def check_tokens():
    """Check token usage from token_snapshot"""
    result = run_sql("""
        SELECT SUM(tokens_total), COUNT(*) 
        FROM token_usage_history 
        WHERE timestamp::date = CURRENT_DATE AND agent_name = 'overall'
    """)
    tokens = 0
    snapshots = 0
    if result and '|' in result:
        parts = result.split('|')
        tokens = int(parts[0]) if parts[0] else 0
        snapshots = int(parts[1]) if parts[1] else 0
    save_status('tokens', 'ok', {'today_total': tokens, 'snapshots': snapshots})
    return {'today_total': tokens, 'snapshots': snapshots}

def run_all_checks():
    """Run all system checks and save to DB"""
    print(f"🔍 Smart Check - {datetime.now()}")
    
    checks = {
        'vault': check_vault(),
        'pki': check_pki(),
        'athene': check_athene(),
        'hestia': check_hestia(),
        'security': check_security(),
        'learnings': check_learnings(),
        'tokens': check_tokens()
    }
    
    print("  ✅ All checks saved to system_status")
    return checks

def generate_report(report_type='morning'):
    """Generate formatted report"""
    now = datetime.now()
    
    # Get unreported statuses since last report
    if report_type == 'morning':
        since = now.replace(hour=7, minute=0) - timedelta(days=1)
    elif report_type == 'noon':
        since = now.replace(hour=12, minute=0)
    else:  # evening
        since = now.replace(hour=19, minute=0)
    
    # Fetch current status
    vault = check_vault()
    pki = check_pki()
    athene = check_athene()
    hestia = check_hestia()
    security = check_security()
    learnings = check_learnings()
    tokens = check_tokens()
    
    report = f"📊 **{report_type.upper()} REPORT** - {now.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    if report_type == 'morning':
        report += f"🔐 **Security:** {security['failed_logins']} failed logins\n"
        report += f"🔑 **PKI:** {pki['expiring_7d']} certs expiring (7d)\n"
        report += f"📈 **ATHENE:** {athene['trades_24h']} trades (24h)\n"
        report += f"🔥 **HESTIA:** {hestia['pending']} pending, {hestia['replied']} replied\n"
        report += f"🧠 **Learnings:** {learnings['today']} heute, {learnings['total']} total\n"
        report += f"💰 **Tokens:** {tokens['today_total']:,} heute\n"
        report += f"🔐 **Vault:** {vault['secrets']} secrets\n"
    elif report_type == 'noon':
        report += f"🔥 **HESTIA:** {hestia['pending']} pending\n"
        report += f"📈 **ATHENE:** {athene['trades_24h']} trades\n"
        report += f"💰 **Tokens:** {tokens['today_total']:,} heute\n"
    else:  # evening
        report += f"🧠 **Learnings:** {learnings['today']} heute\n"
        report += f"💰 **Tokens:** {tokens['today_total']:,} heute\n"
        report += f"🔥 **HESTIA:** {hestia['pending']} pending\n"
    
    return report

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == 'check':
            run_all_checks()
        elif sys.argv[1] == 'report':
            report_type = sys.argv[2] if len(sys.argv) > 2 else 'morning'
            print(generate_report(report_type))
    else:
        run_all_checks()
