"""
SIAS Core API — Das Gehirn des Systems
OpenClaw ist die Shell, DAS hier ist das Gehirn.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import redis
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import os

app = FastAPI(title="SIAS Core", version="1.0.0")

r = redis.Redis(host="192.168.23.80", port=6379, decode_responses=True)


def get_db():
    return psycopg2.connect(
        host="127.0.0.1",
        user="scraper",
        dbname="metamaus",
        cursor_factory=RealDictCursor,
    )


CHANNELS = {
    "arbitrage": "sias:arbitrage",
    "security": "sias:security",
    "research": "sias:research",
    "tasks": "sias:tasks",
    "alerts": "sias:alerts",
}


class EventIn(BaseModel):
    channel: str
    event_type: str
    agent: str
    data: dict


class TaskIn(BaseModel):
    agent: str
    task: str
    priority: int = 5


@app.post("/event")
def publish_event(event: EventIn):
    ch = CHANNELS.get(event.channel)
    if not ch:
        raise HTTPException(400, f"Unknown channel: {event.channel}")
    payload = {
        "type": event.event_type,
        "agent": event.agent,
        "data": event.data,
        "timestamp": datetime.now().isoformat(),
    }
    r.publish(ch, json.dumps(payload))
    r.lpush(f"sias:events:{ch}", json.dumps(payload))
    r.ltrim(f"sias:events:{ch}", 0, 999)
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
        INSERT INTO agent_knowledge (key, value, category, learned_at)
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
        """,
            (
                f"event_{event.agent}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                json.dumps(payload),
                f"event_{event.channel}",
            ),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error (non-fatal): {e}")
    return {"ok": True, "event": payload}


@app.get("/events/{channel}")
def get_events(channel: str, limit: int = 20):
    ch = CHANNELS.get(channel)
    if not ch:
        raise HTTPException(400, f"Unknown channel: {channel}")
    raw = r.lrange(f"sias:events:{ch}", 0, limit - 1)
    events = [json.loads(e) for e in raw]
    return {"channel": channel, "count": len(events), "events": events}


@app.post("/task")
def create_task(task: TaskIn):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
    INSERT INTO agent_tasks (agent, task, priority, status, created_by)
    VALUES (%s, %s, %s, 'pending', 'sias_api')
    RETURNING id
    """,
        (task.agent, task.task, task.priority),
    )
    task_id = cur.fetchone()["id"]
    conn.commit()
    conn.close()
    r.publish(
        CHANNELS["tasks"],
        json.dumps(
            {
                "type": "task_created",
                "agent": task.agent,
                "data": {
                    "task_id": task_id,
                    "task": task.task,
                    "priority": task.priority,
                },
                "timestamp": datetime.now().isoformat(),
            }
        ),
    )
    return {"ok": True, "task_id": task_id}


@app.get("/tasks")
def get_tasks(status: str = "pending", agent: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    query = "SELECT * FROM agent_tasks WHERE status = %s"
    params = [status]
    if agent:
        query += " AND agent = %s"
        params.append(agent)
    query += " ORDER BY priority DESC, created_at ASC"
    cur.execute(query, params)
    tasks = cur.fetchall()
    conn.close()
    return {"count": len(tasks), "tasks": tasks}


@app.get("/status")
def system_status():
    status = {"timestamp": datetime.now().isoformat()}
    try:
        r.ping()
        status["redis"] = "ok"
        status["redis_events"] = {
            ch: r.llen(f"sias:events:{CHANNELS[ch]}") for ch in CHANNELS
        }
    except Exception:
        status["redis"] = "error"
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE status='pending'"
        )
        status["pending_tasks"] = cur.fetchone()["c"]
        cur.execute(
            "SELECT COUNT(*) as c FROM agent_tasks WHERE status='running'"
        )
        status["running_tasks"] = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) as c FROM agent_knowledge")
        status["knowledge_entries"] = cur.fetchone()["c"]
        conn.close()
        status["postgresql"] = "ok"
    except Exception as e:
        status["postgresql"] = f"error: {e}"
    status["channels"] = list(CHANNELS.keys())
    return status


@app.get("/agents")
def list_agents():
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
    SELECT agent,
    COUNT(*) FILTER (WHERE status='pending') as pending,
    COUNT(*) FILTER (WHERE status='running') as running,
    COUNT(*) FILTER (WHERE status='done') as done,
    COUNT(*) FILTER (WHERE status='failed') as failed,
    MAX(created_at) as last_task
    FROM agent_tasks
    GROUP BY agent
    ORDER BY agent
    """
    )
    agents = cur.fetchall()
    conn.close()
    return {"agents": agents}


if __name__ == "__main__":
    import uvicorn

    print("SIAS Core API starting...")
    print("Redis: 192.168.23.80:6379")
    print("PostgreSQL: 127.0.0.1/metamaus")
    print("API: http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
