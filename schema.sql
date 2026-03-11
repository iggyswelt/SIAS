-- SIAS v2.0 Blank Database Schema
-- Created by Orpheus | iggyswelt/SIAS

-- CORE: Knowledge Layer
CREATE TABLE IF NOT EXISTS agent_knowledge (
 id SERIAL PRIMARY KEY,
 key TEXT UNIQUE NOT NULL,
 value TEXT NOT NULL,
 category TEXT DEFAULT 'general',
 source_file TEXT,
 learned_at TIMESTAMP DEFAULT NOW(),
 updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_ak_category ON agent_knowledge(category);
CREATE INDEX idx_ak_learned ON agent_knowledge(learned_at DESC);

-- CORE: Agent Registry
CREATE TABLE IF NOT EXISTS agent_registry (
 agent_name TEXT PRIMARY KEY,
 description TEXT,
 cron_schedule TEXT,
 cron_source TEXT DEFAULT 'openclaw',
 script_path TEXT,
 backup_own BOOLEAN DEFAULT false,
 status TEXT DEFAULT 'active',
 last_hardened DATE,
 notes TEXT
);

SELECT 'SIAS v2.0 Schema installed ✅' as status;
