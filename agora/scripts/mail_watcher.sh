#!/bin/bash
# mail_watcher.sh — Rheingold Mail-Watcher
set -euo pipefail

LOG="/home/iggy/.openclaw/logs/mail_watcher.log"
mkdir -p "$(dirname $LOG)"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Mail-Check gestartet" >> "$LOG"

MAILS=$(himalaya message list --account investigativ --folder INBOX --max-width 200 -s json 2>/dev/null || echo "[]")

if [ "$MAILS" = "[]" ] || [ -z "$MAILS" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] Keine neuen Mails" >> "$LOG"
  exit 0
fi

echo "$MAILS" | python3 -c "
import sys, json, subprocess

mails = json.load(sys.stdin)
if not mails:
    exit(0)

for mail in mails:
    uid = str(mail.get('id', ''))
    subject = mail.get('subject', '(kein Betreff)')
    sender = mail.get('from', [{}])
    from_str = sender[0].get('addr', '') if isinstance(sender, list) else str(sender)
    date_str = mail.get('date', '')

    keywords = ['IFG', 'Antrag', 'Bescheid', 'Widerspruch', 'Auskunft',
                'Förder', 'BMFSFJ', 'Stadt Köln', 'DSGVO', 'Rheingold']
    relevant = any(kw.lower() in subject.lower() or kw.lower() in from_str.lower()
                   for kw in keywords)

    flag = 'RELEVANT' if relevant else 'INFO'

    key = f'incoming_mail_{uid}'
    value = json.dumps({
        'uid': uid, 'subject': subject, 'from': from_str,
        'date': date_str, 'flag': flag, 'processed': False
    }, ensure_ascii=False)

    subprocess.run([
        'psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
        '-c', f\"\"\"
        INSERT INTO agent_knowledge (key, value, category, agent, learned_at)
        VALUES ('{key}', '{value.replace(chr(39), chr(39)+chr(39))}',
        'incoming_mail', 'rheingold', NOW())
        ON CONFLICT (key) DO NOTHING;
        \"\"\"
    ], capture_output=True)

    if relevant:
        print(f'RELEVANT: {subject} | Von: {from_str}')
    else:
        print(f'INFO: {subject}')
" >> "$LOG" 2>&1

RELEVANT_COUNT=$(psql -h 127.0.0.1 -U scraper -d metamaus -t -c "
SELECT COUNT(*) FROM agent_knowledge
WHERE category = 'incoming_mail'
AND value::jsonb->>'processed' = 'false'
AND value::jsonb->>'flag' = 'RELEVANT'
AND learned_at > NOW() - INTERVAL '30 minutes';
" 2>/dev/null | tr -d ' \n')

if [ "${RELEVANT_COUNT:-0}" -gt "0" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${RELEVANT_COUNT} relevante Mails — spawne Rheingold" >> "$LOG"
  openclaw sessions spawn rheingold \
    "MAIL-ALERT: ${RELEVANT_COUNT} neue relevante Mail(s) für Operation Rheingold eingegangen.
Lies die unverarbeiteten Mails aus der DB:
SELECT key, value FROM agent_knowledge WHERE category = 'incoming_mail' AND value::jsonb->>'processed' = 'false' AND value::jsonb->>'flag' = 'RELEVANT' ORDER BY learned_at DESC LIMIT 10;
Für jede Mail: 1. Vollständigen Inhalt via Himalaya lesen 2. In rheingold_findings speichern 3. Als processed markieren 4. Iggy informieren (Telegram [TELEGRAM_ID])
PASSWÖRTER NIEMALS IM CHAT ZEIGEN!"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Mail-Check abgeschlossen" >> "$LOG"
