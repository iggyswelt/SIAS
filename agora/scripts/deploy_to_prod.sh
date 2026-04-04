#!/bin/bash
# Auto-Checkpoint vor Deploy
bash /home/iggy/.openclaw/agora/scripts/checkpoint.sh "pre_deploy_$(date +%Y%m%d_%H%M%S)"

echo "🚀 Deploy DEV → PROD"
echo "⚠️ PROD wird überschrieben! Ctrl+C zum Abbrechen..."
sleep 5
cp -r /opt/dashboard-dev/app.py /opt/dashboard/
cp -r /opt/dashboard-dev/index.html /opt/dashboard/
cp -r /opt/dashboard-dev/templates/ /opt/dashboard/
sudo pkill -f "dashboard" && sleep 2 && systemctl start metamaus-dev 2>/dev/null || true
# Restart PROD if it exists
sudo pkill -f "dashboard" && sleep 2 && systemctl start metamaus-dashboard 2>/dev/null || \
  (ps aux | grep "opt/dashboard.*port=5000" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null; \
   sudo -u iggy bash -c "cd /opt/dashboard && nohup /opt/dashboard/venv/bin/python -c 'from app import app; app.run(host=\"0.0.0.0\", port=5000, threaded=True)' > /tmp/dashboard.log 2>&1 &")
echo "✅ PROD deployed!"
