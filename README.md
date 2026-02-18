<div align="center">

# 🧠 SIAS — Self-Improving Agent System

**Ein persistentes Gedächtnis- und Lern-Framework für AI Agents**  
**A persistent memory & learning framework for AI agents**

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/iggyswelt/SIAS)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![OpenClaw](https://img.shields.io/badge/built%20for-OpenClaw-orange.svg)](https://openclaw.dev)
[![YouTube](https://img.shields.io/badge/YouTube-%40iggyswelt-red.svg)](https://youtube.com/@iggyswelt)

</div>

---

> 🇩🇪 **Deutsch** | 🇬🇧 [**English below**](#-english-version)

---

## 🇩🇪 Deutsche Version

### Was ist SIAS?

SIAS ist ein natives Framework für OpenClaw, das deinem AI-Agent beibringt, **sich selbst zu verbessern** — durch strukturiertes Fehler-Logging, persistentes Gedächtnis und automatische Wissens-Promotion.

Kein externer Service, keine Datenbank, keine API. Nur Markdown-Files und Disziplin.

### 🎯 Das Problem

Jeder kennt es: Du erklärst deinem AI-Agent heute etwas — morgen hat er es vergessen. Er macht denselben Fehler zweimal. Er ignoriert deine Präferenzen. Sessions sind isoliert, Wissen geht verloren.

**SIAS löst das.**

### ✅ Was SIAS kann

- **Fehler merken** — Strukturiertes Error-Log mit WAL-Protokoll (Write-Ahead-Log)
- **Nutzer-Präferenzen speichern** — Korrekturen werden sofort gespeichert, bevor geantwortet wird
- **Wissen promoten** — Temporäre Learnings wandern automatisch ins Langzeit-Gedächtnis
- **Self-Audit** — Regelmäßige Reflexion und Selbstverbesserung
- **Session-Kontinuität** — Nahtloser Übergang zwischen `/compact` und `/new`

### 📁 File-Struktur

```
~/.openclaw/workspace/
├── SOUL.md                    # Agent-Identität & Kern-Regeln (einmalig erstellt)
├── MEMORY.md                  # Permanente Wissensbasis (max. 5 KB)
├── SESSION-STATE.md           # Aktueller Arbeitskontext (häufig aktualisiert)
├── .learnings/                # Temporäre Lern-Logs
│   ├── ERRORS.md              # Fehler-Log
│   ├── LEARNINGS.md           # Best Practices
│   ├── CORRECTIONS.md         # Nutzer-Korrekturen
│   └── FEATURE_REQUESTS.md    # Feature-Todos
└── memory/                    # Tages-Logs (auto-generiert)
    ├── 2026-02-18.md
    └── 2026-02-19.md
```

### 🚀 Quick Start (5 Schritte)

**1. SIAS V1.0 runterladen**
```bash
git clone https://github.com/iggyswelt/SIAS
```

**2. SOUL.md in deinen Workspace kopieren**
```bash
cp SIAS/templates/SOUL.md ~/.openclaw/workspace/SOUL.md
```

**3. Setup-Prompt an deinen Agent schicken**
```
Lies ~/.openclaw/workspace/SOUL.md und richte das komplette 
SIAS-System ein: MEMORY.md, SESSION-STATE.md, .learnings/ Ordner.
Ab jetzt gelten alle Regeln aus SOUL.md!
```

**4. Training Sessions durchlaufen** (5 Sessions, ~30 Minuten)

**5. Fertig** — dein Agent lernt ab jetzt kontinuierlich.

### 🧪 Das WAL-Protokoll erklärt

Das Herzstück von SIAS ist das **Write-Ahead-Log**:

```
Bevor der Agent antwortet → ERST speichern → DANN antworten
```

Konkret: Wenn du sagst "Nutze immer f-Strings in Python" — loggt der Agent das **bevor** er "Verstanden" sagt. Nicht danach. Nicht irgendwann. Sofort.

### 📊 Logging-Format

```markdown
## [COR-20260218-002] CSS Framework Präferenz
- **Area**: user-pref
- **Priority**: critical
- **Status**: active
- **Trigger**: User: "Ich hasse Tailwind"
- **Content**: User nutzt Vanilla CSS + CSS Modules
- **Action**: Niemals Tailwind vorschlagen
```

**Type Codes:**
- `ERR` = Fehler den ich gemacht habe
- `LRN` = Best Practice / Erkenntnis
- `COR` = Nutzer-Korrektur
- `FEAT` = Feature Request / Todo

### 🏆 Promotion-System

Wenn ein Learning **critical** ist oder **3x wiederholt** wurde → automatische Promotion zu `MEMORY.md`:

```
.learnings/CORRECTIONS.md  →  [Promotion]  →  MEMORY.md
     (temporär)                                 (permanent)
```

### 💡 Getestet mit

- OpenClaw 2026.2.17
- MiniMax-M2.5-highspeed (empfohlen: 3-5x schneller)
- PostgreSQL 16 (für erweiterte Projekte)
- Real Production Workloads (~6h Sessions)

---

## 🇬🇧 English Version

### What is SIAS?

SIAS is a native OpenClaw framework that teaches your AI agent to **continuously improve** — through structured error logging, persistent memory, and automatic knowledge promotion.

No external service. No database. No API. Just Markdown files and discipline.

### 🎯 The Problem

You know the drill: you explain something to your AI agent today — tomorrow it's forgotten. It makes the same mistake twice. It ignores your preferences. Sessions are isolated, knowledge is lost.

**SIAS fixes that.**

### ✅ What SIAS Does

- **Remember errors** — Structured error log with WAL protocol (Write-Ahead-Log)
- **Save user preferences** — Corrections are stored immediately, before responding
- **Promote knowledge** — Temporary learnings automatically move to long-term memory
- **Self-audit** — Regular reflection and self-improvement
- **Session continuity** — Seamless transition between `/compact` and `/new`

### 📁 File Structure

```
~/.openclaw/workspace/
├── SOUL.md                    # Agent identity & core rules (created once)
├── MEMORY.md                  # Permanent knowledge base (max 5 KB)
├── SESSION-STATE.md           # Current work context (frequently updated)
├── .learnings/                # Temporary learning logs
│   ├── ERRORS.md              # Error log
│   ├── LEARNINGS.md           # Best practices
│   ├── CORRECTIONS.md         # User corrections
│   └── FEATURE_REQUESTS.md    # Feature todos
└── memory/                    # Daily logs (auto-generated)
    ├── 2026-02-18.md
    └── 2026-02-19.md
```

### 🚀 Quick Start (5 Steps)

**1. Clone the repo**
```bash
git clone https://github.com/iggyswelt/SIAS
```

**2. Copy SOUL.md to your workspace**
```bash
cp SIAS/templates/SOUL.md ~/.openclaw/workspace/SOUL.md
```

**3. Send setup prompt to your agent**
```
Read ~/.openclaw/workspace/SOUL.md and set up the complete 
SIAS system: MEMORY.md, SESSION-STATE.md, .learnings/ folder.
From now on, all rules from SOUL.md apply!
```

**4. Run training sessions** (5 sessions, ~30 minutes)

**5. Done** — your agent now learns continuously.

### 🧪 The WAL Protocol Explained

The core of SIAS is the **Write-Ahead-Log**:

```
Before the agent responds → SAVE FIRST → THEN respond
```

Concretely: if you say "always use f-strings in Python" — the agent logs that **before** saying "understood". Not after. Not eventually. Immediately.

### 📊 Logging Format

```markdown
## [COR-20260218-002] CSS Framework Preference
- **Area**: user-pref
- **Priority**: critical
- **Status**: active
- **Trigger**: User: "I hate Tailwind"
- **Content**: User prefers Vanilla CSS + CSS Modules
- **Action**: Never suggest Tailwind
```

**Type Codes:**
- `ERR` = Error I made
- `LRN` = Best practice / insight
- `COR` = User correction
- `FEAT` = Feature request / todo

### 🏆 Promotion System

When a learning is **critical** or **repeated 3x** → automatic promotion to `MEMORY.md`:

```
.learnings/CORRECTIONS.md  →  [Promotion]  →  MEMORY.md
     (temporary)                                (permanent)
```

### 🎓 Training Sessions Overview

| Session | Goal | Time |
|---------|------|------|
| 1 - Setup | Create folder structure & initialize | ~5 min |
| 2 - WAL Test | Test write-ahead-log with a correction | ~5 min |
| 3 - Error Log | Simulate & log an error | ~5 min |
| 4 - Promotion | Promote learnings to MEMORY.md | ~5 min |
| 5 - Full Workflow | End-to-end test of all rules | ~10 min |

Full prompts for all sessions: [SIAS_V1.0.md](SIAS_V1.0.md)

### ⚠️ Enforcement Strategy

If the agent breaks rules:

```
RULE VIOLATION! You didn't [X] (WAL protocol / logging / etc.)

Immediate correction:
1. Make up for it now (show me the log entries)
2. Log this rule violation in .learnings/ERRORS.md
3. Explain why you forgot
4. How will you ensure it doesn't happen again?

After the 3rd violation of the same type: write a reflection 
and add the learning prominently to MEMORY.md!
```

### 📊 Success Metrics (after 1-2 weeks)

```
Self-Improvement Audit:

1. Show me .learnings/ERRORS.md - how many errors repeat?
2. Show me MEMORY.md - is it current and < 5 KB?
3. Read last 5 days in memory/ - do you see patterns/progress?
4. Did you save and apply my last 3 preferences?

Rate yourself: 1-10 on each criterion!
```

---

## 🗺️ Roadmap

- [ ] **SIAS 1.1** — Automatic weekly reflection cron
- [ ] **SIAS 1.2** — Dashboard integration (track learnings visually)
- [ ] **SIAS 2.0** — Multi-agent support (shared MEMORY.md)
- [ ] **OpenClaw Plugin** — Native SIAS integration

---

## 🤝 Contributing

PRs welcome! Especially:
- Templates for different agent use cases
- Integration examples (other AI tools)
- Translations

---

## 📜 License

MIT — Feel free to adapt for your own agents.

---

## 🙏 Credits

Developed by [@iggyswelt](https://youtube.com/@iggyswelt) in collaboration with Claude (Anthropic) and Grok (xAI).

**Built with real production workloads — not just theory.**

---

<div align="center">

**⭐ Star the repo if SIAS helps you build better agents!**

[YouTube](https://youtube.com/@iggyswelt) · [GitHub](https://github.com/iggyswelt/SIAS) · [Issues](https://github.com/iggyswelt/SIAS/issues)

</div>
