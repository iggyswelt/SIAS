#!/usr/bin/env python3
from flask import Flask, jsonify, request
import imaplib
import email as email_module
import os
from functools import wraps

app = Flask(__name__)
API_TOKEN = os.environ.get('MAIL_API_TOKEN', 'rheingold-secret-token-2026')

def require_token(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if token != API_TOKEN:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def hdr(msg, key):
    v = msg.get(key, '')
    parts = email_module.header.decode_header(v)
    out = []
    for p, e in parts:
        if isinstance(p, bytes):
            out.append(p.decode(e or 'utf-8', errors='replace'))
        else:
            out.append(p)
    return ''.join(out)

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain':
                enc = part.get_content_charset() or 'utf-8'
                try:
                    return part.get_payload(decode=True).decode(enc, errors='replace')
                except:
                    pass
    else:
        enc = msg.get_content_charset() or 'utf-8'
        try:
            return msg.get_payload(decode=True).decode(enc, errors='replace')
        except:
            pass
    return ""

@app.route("/api/mails/inbox")
@require_token
def mails_inbox():
    try:
        pw = os.environ.get('ABYDON_MAIL_PW', 'a4gBH@#oqvbQxnUBWqA62DJ^KGR4YXFKGHy@cm^TUh8%j6oZK9n6wnw')
        m = imaplib.IMAP4_SSL('mail.abydon.com', 993)
        m.login('[EMAIL_PLACEHOLDER]', pw)
        m.select('INBOX')
        status, msgs = m.search(None, 'ALL')
        ids = msgs[0].split()
        result = []
        for eid in ids[-20:]:
            s, d = m.fetch(eid, '(RFC822)')
            msg_obj = email_module.message_from_bytes(d[0][1])
            body = get_body(msg_obj)
            result.append({
                'id': eid.decode(),
                'from': hdr(msg_obj, 'From'),
                'subject': hdr(msg_obj, 'Subject'),
                'date': hdr(msg_obj, 'Date'),
                'body_preview': body[:300]
            })
        m.logout()
        return jsonify({'mails': result, 'total': len(result)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/mails/send", methods=['POST'])
@require_token
def send_mail():
    import smtplib
    from email.mime.text import MIMEText
    data = request.json
    to_email = data.get('to', '')
    subject = data.get('subject', '')
    body = data.get('body', '')
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['From'] = '[EMAIL_PLACEHOLDER]'
    msg['To'] = to_email
    msg['Subject'] = subject
    try:
        pw = os.environ.get('ABYDON_MAIL_PW', 'a4gBH@#oqvbQxnUBWqA62DJ^KGR4YXFKGHy@cm^TUh8%j6oZK9n6wnw')
        with smtplib.SMTP('mail.abydon.com', 587) as server:
            server.ehlo()
            server.starttls()
            server.login('[EMAIL_PLACEHOLDER]', pw)
            server.sendmail('[EMAIL_PLACEHOLDER]', to_email, msg.as_string())
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/health")
def health():
    return jsonify({'status': 'ok'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5051, debug=False)
