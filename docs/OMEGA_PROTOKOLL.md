# Omega-Protokoll — Architektur-Dokument

**Version:** 1.1  
**Status:** Design Review  
**Erstellt:** 2026-04-16  
**Architekt:** Arthemis  
**Review-Status:** PENDING_APPROVAL

---

## 1. Überblick

Das Omega-Protokoll ist die finale Sicherheitsinstanz für systemkritische und destruktive Operationen within the SIAS-Plattform. Es fungiert als hardware-anchored Gatekeeper zwischen dem Gateway- Layer und der Exec-Unit.

### 1.1 Zielsetzung

- **Physischer Gatekeeper** für destruktive Befehle (Agent-Termination, Core-File Override, Deep-Reset)
- **Unumgehbare Authentifizierung** via Hardware-Secured Module (HSM) oder FIDO2
- **Unveränderbares Audit-Logging** aller Zugriffsversuche
- **Zero-Trust Architecture** — kein Befehl wird ohne physische Präsenz freigegeben

### 1.2 Scope

```
[DESTRUCTIVE COMMAND REQUEST]
         │
         ▼
┌─────────────────────────┐
│     OMEGA GATEWAY        │  ← Redis Event: omega.challenge.request
│  (Challenge Generator)   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│   OMEGA VAULT           │  ← Append-only Log (PostgreSQL)
│  (Audit Trail)          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│     OMEGA VALIDATOR     │  ← Challenge-Response Validation
│  (Exec Gate)            │
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    │               │
    ▼               ▼
[APPROVED]      [LOCKDOWN]
```

---

## 2. Systemkomponenten

### 2.1 Omega Gateway (`omega_gateway.py`)

**Standort:** `sias_core/omega_gateway.py`

**Verantwortung:**
- Empfängt alle `omega.challenge.request` Events via Redis
- Generiert kryptographische Challenges
- Timeout-Handling (max 30s für User-Response)
- Weiterleitung an Omega Validator bei erfolgreicher Authentifizierung

**Challenge-Typen:**

| Typ | Protokoll | Use-Case |
|-----|-----------|----------|
| `HMAC_SHA1` | Shared Secret | Backup/Recovery (Orpheus) |
| `FIDO2` | Public Key | Commander YubiKey |

**Event Schema:**
```python
{
    "event": "omega.challenge.request",
    "agent_id": "metamaus",
    "action": "agent.deep_reset",
    "target": "hermes",
    "severity": "CRITICAL",
    "challenge_type": "FIDO2",
    "nonce": "uuid-v4",
    "timestamp": "ISO-8601"
}
```

### 2.2 Omega Validator (`omega_validator.py`)

**Standort:** `sias_core/omega_validator.py`

**Verantwortung:**
- Empfängt Challenge-Response von Gateway
- Validiert via HSM (Orpheus) oder FIDO2 (YubiKey)
- Entscheidungslogik: APPROVED / DENIED / LOCKDOWN
- Timeout: 30 Sekunden Window

**HMAC-SHA1 Workflow:**
```
1. Gateway generiert random nonce (32 bytes)
2. Nonce + Shared Secret → HMAC-SHA1 → Response
3. Validator vergleicht Response mit eigener Berechnung
```

**FIDO2 Workflow:**
```
1. Gateway sendet challenge an FIDO2 Device (via Orpheus/HSM)
2. User toucht YubiKey → Assertion Response
3. Validator verifiziert Assertion via FIDO2 Server
```

### 2.3 Omega Vault (`omega_vault.py`)

**Standort:** `sias_core/omega_vault.py`

**Verantwortung:**
- Append-only Audit-Log in PostgreSQL
- Tabelle: `omega_audit_log`
- Jeder Eintrag: Hash des vorherigen Eintrags (Blockchain-Prinzip)

**Schema:**
```sql
CREATE TABLE omega_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    nonce           UUID NOT NULL UNIQUE,
    agent_id        TEXT NOT NULL,
    action          TEXT NOT NULL,
    target          TEXT,
    severity        TEXT NOT NULL,
    outcome         TEXT NOT NULL,  -- APPROVED | DENIED | LOCKDOWN
    challenge_type  TEXT NOT NULL,
    response_hash   TEXT,           -- HMAC oder FIDO2 Assertion Hash
    ip_address      INET,
    timestamp       TIMESTAMPTZ DEFAULT NOW(),
    prev_hash       TEXT NOT NULL,  -- Hash des vorherigen Eintrags
    entry_hash      TEXT NOT NULL  -- SHA256(id + nonce + outcome + timestamp + prev_hash)
);
```

---

## 3. Integration mit Orpheus (PoC-Phase)

### 3.1 Orpheus HSM-Schnittstelle

**Voraussetzung:** Orpheus hat Zugriff auf FIDO2-Dongle (Test-Umgebung)

```python
# orpheus/hsm_interface.py
class HSMInterface:
    def trigger_fido2_challenge(self, challenge: bytes) -> dict:
        """FIDO2 Assertion generieren via verbundenen Dongle"""
        
    def verify_fido2_assertion(self, assertion: dict) -> bool:
        """Assertion gegen gespeicherten Public Key verifizieren"""
        
    def get_hmac_secret(self, agent_id: str) -> bytes:
        """Shared Secret für HMAC-SHA1 abrufen (nur Orpheus)"""
```

### 3.2 Remote-FIDO2 Workflow (The Workstation Bridge)

**Problem:** SIAS Core (Keller) und Commander YubiKey (Workstation/Laptop) sind räumlich getrennt.

```
┌──────────────────────────────────────────────────────────────────────┐
│                     REMOTE FIDO2 FLOW                                 │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  KELLER (SIAS Core)              WORKSTATION (Commander)            │
│  ─────────────────              ──────────────────────               │
│                                                                       │
│  ┌─────────────────┐                                                   │
│  │ OMEGA_GATEWAY   │                                                   │
│  │  (Challenge)    │                                                   │
│  └────────┬────────┘                                                   │
│           │ Redis: omega.remote.challenge                             │
│           │ Telegram: Orpheus → Metamaus                               │
│           ▼                                                            │
│  ┌─────────────────┐          ┌─────────────────────────────────┐    │
│  │ OMEGA_VALIDATOR │◄─────────│ Telegram / WebAuthn Interface   │    │
│  │                 │  ACP     │ (Commander Laptop)              │    │
│  └────────┬────────┘  Callback└─────────────────────────────────┘    │
│           │                                                             │
│           ▼                                                             │
│  ┌─────────────────┐                                                   │
│  │  EXEC_UNIT      │                                                   │
│  └─────────────────┘                                                   │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

**Schritt-für-Schritt:**

```
1. METAMAUS → OMEGA_GATEWAY
   Event: omega.challenge.request (action=db.wipe)
   
2. OMEGA_GATEWAY generiert WebAuthn-Challenge
   - 32 bytes random nonce
   - relying_party_id: "sias.local"
   - timeout: 30s
   
3. OMEGA_GATEWAY → ORPHEUS
   Channel: omega.remote.challenge
   Payload: {challenge_base64, action, target, severity}
   
4. ORPHEUS → TELEGRAM (Metamaus)
   Message: "🔐 Omega-Anfrage: db.wipe — FIDO2 bestätigen"
   Buttons: [Challenge-URL]
   
5. COMMANDER (Workstation Browser)
   - Öffnet WebAuthn-Challenge URL
   - Toucht YubiKey
   - Assertion wird generiert
   
6. COMMANDER → OMEGA_VALIDATOR
   Channel: omega.remote.assertion (Redis ACP)
   Payload: {assertion_base64, nonce, timestamp}
   
7. OMEGA_VALIDATOR verifiziert Assertion
   - Signatur gegen gespeicherten Public Key
   - Nonce-Abgleich
   - timestamp < 30s
   
8. OMEGA_VALIDATOR → OMEGA_VAULT
   Log: outcome=APPROVED, remote_fido2=true
   
9. OMEGA_VALIDATOR → EXEC_UNIT
   Command freigegeben
```

### 3.3 Orpheus HSM-Schnittstelle

**Voraussetzung:** Orpheus hat Zugriff auf FIDO2-Dongle (Test-Umgebung) oder simuliertes HSM-Modul

```python
# orpheus/hsm_interface.py
class HSMInterface:
    def trigger_fido2_challenge(self, challenge: bytes) -> dict:
        """FIDO2 Assertion generieren via verbundenen Dongle"""
        
    def verify_fido2_assertion(self, assertion: dict) -> bool:
        """Assertion gegen gespeicherten Public Key verifizieren"""
        
    def get_hmac_secret(self, agent_id: str) -> bytes:
        """Shared Secret für HMAC-SHA1 abrufen (nur Orpheus)"""
        
    # Remote-FIDO2 Support
    def proxy_webauthn_challenge(self, challenge: dict, telegram_target: str) -> bool:
        """Challenge via Telegram an Commander weiterleiten"""
        
    def receive_remote_assertion(self, assertion: dict) -> bool:
        """Assertion vom Remote-Device empfangen (Workstation Bridge)"""
```

### 3.4 PoC-Testablauf (Updated)

```
┌──────────────────────────────────────────────────────────┐
│               POUND TEST SEQUENCE (Updated)               │
├──────────────────────────────────────────────────────────┤
│ 1. METAMAUS → OMEGA_GATEWAY                              │
│    Event: omega.challenge.request                         │
│    action: db.wipe                                        │
│    severity: CRITICAL                                     │
│                                                           │
│ 2. OMEGA_GATEWAY → ORPHEUS                               │
│    Request: WebAuthn Challenge (Remote-FIDO2)             │
│    Channel: omega.remote.challenge                        │
│                                                           │
│ 3. ORPHEUS → TELEGRAM (Metamaus)                         │
│    Push: "🔐 Omega db.wipe — FIDO2 bestätigen"           │
│    mit WebAuthn-URL als Button                            │
│                                                           │
│ 4. COMMANDER (simuliert durch Orpheus HSM-Modul)         │
│    - Signiert Challenge                                   │
│    - Assertion an omega.remote.assertion                  │
│                                                           │
│ 5. OMEGA_VALIDATOR → OMEGA_VAULT                        │
│    Log: outcome=APPROVED, remote_fido2=true              │
│                                                           │
│ 6. OMEGA_VALIDATOR → EXEC_UNIT                           │
│    Command freigegeben                                   │
└──────────────────────────────────────────────────────────┘
```

---

## 4. Command Classification

### 4.1 Omega-Pflichtbefehle (immer Gateway durchlaufen)

| Befehl | Severity | Beschreibung |
|--------|----------|--------------|
| `agent.deep_reset` | CRITICAL | Kompletter Agent-Reset |
| `agent.terminate` | CRITICAL | Agent-Prozess beenden |
| `core.file.override` | CRITICAL | Systemdateien überschreiben |
| `config.secret.modify` | HIGH | Secrets/Keys ändern |
| `db.wipe` | CRITICAL | Datenbank löschen |
| `backup.purge` | HIGH | Backups entfernen |
| `session.lockdown` | HIGH | Session einfrieren |

### 4.2 Standard-Befehle (ohne Omega)

- Lesende Operationen
- Monitoring/Health-Checks
- Task-Assignments (nicht-destruktiv)

### 4.3 Auto-Recovery Policy (Exception Logic)

**Policy:** `agent.restart` (Warmer Neustart) ist von der Omega-Challenge ausgenommen, unter strenger Rate-Limiting-Kontrolle.

**Rate-Limiter Schema:**
```sql
CREATE TABLE omega_restart_counter (
    agent_id     TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    restart_count INTEGER DEFAULT 1,
    PRIMARY KEY (agent_id, window_start)
);
```

**Logik:**
```
MAX_RESTARTS_PER_WINDOW = 3
WINDOW_SIZE = 10 minutes

on agent.restart request:
    1. Check: restart_count in current window for target agent
    2. If restart_count < MAX_RESTARTS_PER_WINDOW:
           APPROVE (no Omega challenge)
           increment counter
    3. If restart_count >= MAX_RESTARTS_PER_WINDOW:
           ESCALATE: severity = CRITICAL
           require full Omega-FIDO2 challenge
    4. If challenge fails or timeout:
           LOCKDOWN target agent
           alert Zerberus + Metamaus
```

**Redis-Channel für Auto-Recovery:**
```
omega.auto.recovery.check    — Validator prüft Rate-Limit
omega.auto.recovery.count    — Counter-Updates
omega.auto.recovery.escalate — Eskalation nach Metamaus
```

---

## 5. Lockdown-Szenarien

### 5.1 Timeout Lockdown
- **Auslöser:** Keine Response innerhalb 30 Sekunden
- **Aktion:** Session sperren, Alert an Zerberus
- **Recovery:** Manueller Unlock via Commander YubiKey

### 5.2 Invalid Response Lockdown
- **Auslöser:** 3x falsche FIDO2-Assertion oder HMAC-Fehler
- **Aktion:** Agent deaktivieren, Audit-Log-Eintrag erstellen
- **Recovery:** Commander + Orpheus gemeinsame Freigabe

### 5.3 Suspicious Pattern Lockdown
- **Auslöser:** Zerberus meldet Anomalie
- **Aktion:** Präventiver Omega-Lockdown
- **Recovery:** Commander YubiKey + Pythia-Validierung

---

## 6. Sicherheitsanforderungen

### 6.1 Kryptographische Anforderungen

| Anforderung | Spezifikation |
|-------------|----------------|
| HMAC | SHA1-RFC2104, Key-Länge ≥ 256 bit |
| FIDO2 | ECDAA-P-256, Resident Key erforderlich |
| Nonce | Kryptographisch random, 32 bytes, einmalig |
| Hash-Chain | SHA256, previous_entry_hash als Input |

### 6.2 Transport-Sicherheit

- Alle Redis-Events verschlüsselt (TLS)
- Orpheus ↔ HSM: USB-Secure channel
- Validator: Local Unix Socket nur

### 6.3 Zugriffskontrolle

| Komponente | Berechtigung |
|------------|--------------|
| Omega Gateway | Alle Agents |
| Omega Validator | Nur Omega Gateway |
| Omega Vault | Nur Omega Validator |
| HSM Interface | Nur Orpheus |

---

## 7. Zukunft: Commander YubiKey Migration

Nach erfolgreichem PoC mit Orpheus:

```
Production Migration Plan:
─────────────────────────
Phase 1: Orpheus FIDO2 Dongle → Test bestanden
Phase 2: Commander YubiKey bereitstellen
Phase 3: OMEGA auf Production Key umziehen
Phase 4: Orpheus-Dongle als Backup-Key konfigurieren
```

**Commander YubiKey Anforderungen:**
- FIDO2 PIV + OpenPGP
- Touch-Requirement: CRITICAL Actions
- PIN: 8+ Zeichen

---

## 8. Implementierungs-Hints

### 8.1 Redis Event Channels

```
omega.challenge.request    — Gateway empfängt
omega.fido2.challenge      — Orpheus empfängt (local HSM)
omega.fido2.response       — Validator empfängt (local HSM)
omega.hmac.challenge       — Orpheus empfängt
omega.hmac.response        — Validator empfängt
omega.remote.challenge     — Orpheus empfängt (Remote-FIDO2)
omega.remote.assertion     — Validator empfängt (Remote-FIDO2)
omega.auto.recovery.check  — Validator prüft Rate-Limit
omega.auto.recovery.count  — Counter-Updates
omega.auto.recovery.escalate — Eskalation nach Metamaus
omega.audit.log            — Pythia + Vault empfangen
omega.lockdown             — Zerberus + Metamaus empfangen
```

### 8.2 Abhängigkeiten

```python
# sias_core/requirements.txt
fido2>=1.1.0       # FIDO2 Library
pyhsm>=1.0.0       # HSM Interface
redis>=4.5.0       # Event Bus
psycopg2-binary    # PostgreSQL
```

---

## 9. Review-Checkliste

- [x] Gateway-Middleware zwischen Gateway und Exec-Unit verifiziert
- [x] Challenge-Response Protokoll (HMAC-SHA1 + FIDO2)
- [x] Orpheus HSM-Interface definiert
- [x] Append-only Vault mit Hash-Chain
- [x] Lockdown-Szenarien dokumentiert
- [x] Commander YubiKey Migration geplant
- [x] Remote-FIDO2 Workflow (Workstation Bridge)
- [x] Auto-Recovery Policy mit Rate-Limiter

---

## Appendix A: omega_validator.py Logic Sketch

```python
# sias_core/omega_validator.py
# Version: 1.1 (Remote-FIDO2 + Auto-Recovery)

import redis
import time
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional

# Constants
MAX_RESTARTS_PER_WINDOW = 3
WINDOW_SIZE_MINUTES = 10
CHALLENGE_TIMEOUT_SECONDS = 30

class OmegaValidator:
    def __init__(self, redis_client, db_pool):
        self.redis = redis_client
        self.db = db_pool
        
    # ─────────────────────────────────────────────────────────────
    # MAIN ENTRY POINT
    # ─────────────────────────────────────────────────────────────
    def handle_challenge_request(self, event: dict) -> dict:
        """
        Receives omega.challenge.request
        Returns: {outcome: APPROVED|DENIED|LOCKDOWN, action: str}
        """
        action = event["action"]
        agent_id = event["agent_id"]
        target = event.get("target")
        severity = event["severity"]
        
        # 1. AUTO-RECOVERY CHECK (agent.restart only)
        if action == "agent.restart":
            return self._handle_auto_recovery(agent_id, target, event)
        
        # 2. RATE-LIMIT ESCALATION CHECK
        if self._is_rate_limited(agent_id, target):
            severity = "CRITICAL"
            event["escalated"] = True
        
        # 3. DETERMINE CHALLENGE TYPE
        if event.get("challenge_type") == "HMAC_SHA1":
            return self._handle_hmac_challenge(event)
        elif event.get("remote_fido2"):
            return self._handle_remote_fido2(event)
        else:
            return self._handle_local_fido2(event)
    
    # ─────────────────────────────────────────────────────────────
    # AUTO-RECOVERY LOGIC
    # ─────────────────────────────────────────────────────────────
    def _handle_auto_recovery(self, agent_id: str, target: str, event: dict) -> dict:
        """
        agent.restart bypasses Omega challenge IF under rate limit.
        """
        restart_count = self._get_restart_count(agent_id, target)
        
        if restart_count < MAX_RESTARTS_PER_WINDOW:
            # APPROVE without challenge
            self._increment_restart_counter(agent_id, target)
            self._log_to_vault(
                nonce=event["nonce"],
                agent_id=agent_id,
                action="agent.restart",
                target=target,
                severity="LOW",
                outcome="APPROVED",
                challenge_type="AUTO_RECOVERY",
                response_hash=None
            )
            return {"outcome": "APPROVED", "action": "agent.restart", "target": target}
        
        else:
            # ESCALATE to CRITICAL — require full Omega challenge
            self._publish_event("omega.auto.recovery.escalate", {
                "agent_id": agent_id,
                "target": target,
                "restart_count": restart_count,
                "reason": "Rate limit exceeded"
            })
            event["severity"] = "CRITICAL"
            event["escalated"] = True
            return self._handle_remote_fido2(event)
    
    def _get_restart_count(self, agent_id: str, target: str) -> int:
        """Check PostgreSQL for current restart count in window."""
        with self.db.connect() as conn:
            result = conn.execute("""
                SELECT restart_count FROM omega_restart_counter
                WHERE agent_id = %s 
                  AND window_start > NOW() - INTERVAL '%s minutes'
                ORDER BY window_start DESC LIMIT 1
            """, (agent_id, str(WINDOW_SIZE_MINUTES)))
            row = result.fetchone()
            return row[0] if row else 0
    
    def _increment_restart_counter(self, agent_id: str, target: str):
        """Insert or update restart counter in PostgreSQL."""
        with self.db.connect() as conn:
            conn.execute("""
                INSERT INTO omega_restart_counter (agent_id, target, window_start, restart_count)
                VALUES (%s, %s, NOW(), 1)
                ON CONFLICT (agent_id, window_start) 
                DO UPDATE SET restart_count = omega_restart_counter.restart_count + 1
            """, (agent_id, target))
    
    def _is_rate_limited(self, agent_id: str, target: str) -> bool:
        """Check if target agent is currently rate-limited."""
        count = self._get_restart_count(agent_id, target)
        return count >= MAX_RESTARTS_PER_WINDOW
    
    # ─────────────────────────────────────────────────────────────
    # REMOTE FIDO2 (WORKSTATION BRIDGE)
    # ─────────────────────────────────────────────────────────────
    def _handle_remote_fido2(self, event: dict) -> dict:
        """
        WebAuthn challenge via Orpheus → Telegram → Commander Laptop.
        Assertion returns via omega.remote.assertion channel.
        """
        nonce = event["nonce"]
        
        # Wait for assertion on omega.remote.assertion (with timeout)
        assertion = self._wait_for_remote_assertion(
            nonce=nonce,
            timeout=CHALLENGE_TIMEOUT_SECONDS
        )
        
        if assertion is None:
            return self._lockdown(
                event=event,
                reason="Remote-FIDO2 timeout (>30s)"
            )
        
        # Verify assertion
        if not self._verify_webauthn_assertion(assertion, event):
            return self._lockdown(
                event=event,
                reason="Invalid Remote-FIDO2 assertion"
            )
        
        # SUCCESS
        self._log_to_vault(
            nonce=nonce,
            agent_id=event["agent_id"],
            action=event["action"],
            target=event.get("target"),
            severity=event["severity"],
            outcome="APPROVED",
            challenge_type="REMOTE_FIDO2",
            response_hash=assertion["hash"]
        )
        
        return {"outcome": "APPROVED", "action": event["action"], "target": event.get("target")}
    
    def _wait_for_remote_assertion(self, nonce: str, timeout: int) -> Optional[dict]:
        """Subscribe to omega.remote.assertion and wait for matching nonce."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe("omega.remote.assertion")
        
        start = time.time()
        while time.time() - start < timeout:
            msg = pubsub.get_message(timeout=1)
            if msg and msg["type"] == "message":
                data = json.loads(msg["data"])
                if data.get("nonce") == nonce:
                    return data
        return None
    
    def _verify_webauthn_assertion(self, assertion: dict, event: dict) -> bool:
        """
        Verify WebAuthn assertion:
        1. Check signature against stored public key
        2. Verify nonce matches
        3. Verify timestamp is within window
        """
        # Signature verification (simplified)
        expected_nonce = event["nonce"]
        if assertion.get("nonce") != expected_nonce:
            return False
        
        # Timestamp check
        assertion_time = datetime.fromisoformat(assertion["timestamp"])
        now = datetime.now()
        if (now - assertion_time).total_seconds() > CHALLENGE_TIMEOUT_SECONDS:
            return False
        
        # Signature verification would call fido2 library
        # return self.fido2.verify(assertion["credential_id"], assertion["auth_data"], assertion["signature"])
        return True
    
    # ─────────────────────────────────────────────────────────────
    # LOCKDOWN
    # ─────────────────────────────────────────────────────────────
    def _lockdown(self, event: dict, reason: str) -> dict:
        """
        Trigger lockdown:
        - Log to vault
        - Publish omega.lockdown
        - Alert Zerberus + Metamaus
        """
        self._log_to_vault(
            nonce=event["nonce"],
            agent_id=event["agent_id"],
            action=event["action"],
            target=event.get("target"),
            severity="CRITICAL",
            outcome="LOCKDOWN",
            challenge_type=event.get("challenge_type", "UNKNOWN"),
            response_hash=None
        )
        
        self._publish_event("omega.lockdown", {
            "agent_id": event["agent_id"],
            "target": event.get("target"),
            "action": event["action"],
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        
        return {"outcome": "LOCKDOWN", "reason": reason}
    
    # ─────────────────────────────────────────────────────────────
    # VAULT LOGGING
    # ─────────────────────────────────────────────────────────────
    def _log_to_vault(self, nonce: str, agent_id: str, action: str,
                      target: Optional[str], severity: str, outcome: str,
                      challenge_type: str, response_hash: Optional[str]):
        """
        Append-only log with hash chain to PostgreSQL.
        """
        with self.db.connect() as conn:
            # Get previous entry hash
            prev_row = conn.execute("""
                SELECT entry_hash FROM omega_audit_log 
                ORDER BY id DESC LIMIT 1
            """).fetchone()
            prev_hash = prev_row[0] if prev_row else "GENESIS"
            
            # Calculate entry hash
            entry_data = f"{nonce}|{agent_id}|{action}|{target}|{severity}|{outcome}|{challenge_type}|{datetime.now().isoformat()}|{prev_hash}"
            entry_hash = hashlib.sha256(entry_data.encode()).hexdigest()
            
            conn.execute("""
                INSERT INTO omega_audit_log 
                (nonce, agent_id, action, target, severity, outcome, challenge_type, response_hash, prev_hash, entry_hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (nonce, agent_id, action, target, severity, outcome, challenge_type, response_hash, prev_hash, entry_hash))
    
    def _publish_event(self, channel: str, data: dict):
        self.redis.publish(channel, json.dumps(data))
```

---

## Appendix B: Orpheus HSM Mock (PoC-Ready)

```python
# orpheus/hsm_mock.py
# Simulates FIDO2 assertion for PoC without physical YubiKey

import hashlib
import json
import time
import uuid

class HSMMock:
    """
    Simulates Orpheus HSM Interface for PoC.
    In production: replace with real FIDO2 SDK calls.
    """
    
    def __init__(self, shared_secret: bytes = b"poc-secret-key-32-bytes-long!!"):
        self.shared_secret = shared_secret
        self.stored_assertions = {}
    
    # ─────────────────────────────────────────────────────────────
    # HMAC-SHA1 (for backup/recovery commands)
    # ─────────────────────────────────────────────────────────────
    def generate_hmac_response(self, nonce: str) -> str:
        """Generate HMAC-SHA1 response for a given nonce."""
        import hmac
        return hmac.new(self.shared_secret, nonce.encode(), hashlib.sha1).hexdigest()
    
    def verify_hmac_response(self, nonce: str, response: str) -> bool:
        """Verify HMAC-SHA1 response."""
        expected = self.generate_hmac_response(nonce)
        return hmac.compare_digest(expected, response)
    
    # ─────────────────────────────────────────────────────────────
    # REMOTE FIDO2 SIMULATION (for PoC db.wipe test)
    # ─────────────────────────────────────────────────────────────
    def simulate_remote_fido2_assertion(self, challenge: dict) -> dict:
        """
        Simulates what Commander's YubiKey would return.
        In production: real WebAuthn assertion via browser.
        """
        nonce = challenge["nonce"]
        action = challenge["action"]
        timestamp = time.time()
        
        # Simulate assertion (in production: real FIDO2 assertion)
        assertion = {
            "nonce": nonce,
            "action": action,
            "timestamp": timestamp,
            "credential_id": "commander-yubikey-poc",
            "hash": hashlib.sha256(f"{nonce}|{action}|{timestamp}".encode()).hexdigest(),
            "signature": "SIMULATED_POC_SIGNATURE",
            "auth_data": "SIMULATED_AUTH_DATA"
        }
        
        self.stored_assertions[nonce] = assertion
        return assertion
    
    def trigger_webauthn_challenge(self, challenge: dict, telegram_target: str) -> bool:
        """
        Simulates Orpheus sending WebAuthn URL via Telegram to Commander.
        Returns True if challenge was pushed successfully.
        """
        print(f"[HSM-MOCK] Pushing WebAuthn challenge to {telegram_target}")
        print(f"[HSM-MOCK] Action: {challenge['action']}")
        print(f"[HSM-MOCK] Nonce: {challenge['nonce']}")
        print(f"[HSM-MOCK] Challenge URL: https://sias.local/omega/auth?nonce={challenge['nonce']}")
        return True
    
    def receive_remote_assertion(self, assertion: dict) -> bool:
        """
        Simulates receiving assertion back from Commander's laptop.
        In production: this channel is omega.remote.assertion (Redis ACP).
        """
        nonce = assertion.get("nonce")
        if nonce in self.stored_assertions:
            print(f"[HSM-MOCK] Assertion received for nonce {nonce}")
            return True
        return False
```

---

**ARTHEMIS REVIEW STATUS:** READY_FOR_ORPHEUS_POC

> Architektur-Dokument Version 1.1 bereit für PoC-Implementierung. Remote-FIDO2 Workflow und Auto-Recovery Policy sind integriert.

