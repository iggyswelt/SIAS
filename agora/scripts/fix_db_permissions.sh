#!/bin/bash
# fix_db_permissions.sh - DB Rechte nach OpenClaw Updates wiederherstellen
# Nach jedem OpenClaw Update ausführen!

echo "🔧 Fixe DB Permissions für iggy User..."

sudo -u postgres psql -d metamaus << 'SQL'
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO iggy;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO iggy;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO iggy;
ALTER USER iggy WITH SUPERUSER;
SQL

echo "✅ Permissions wiederhergestellt!"
