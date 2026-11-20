import sqlite3
c = sqlite3.connect("/data/promptlab.db")
pending = c.execute("SELECT COUNT(*) FROM jobs WHERE status='pending'").fetchone()[0]
running = c.execute("SELECT COUNT(*) FROM jobs WHERE status='running'").fetchone()[0]
done = c.execute("SELECT COUNT(*) FROM jobs WHERE status='done'").fetchone()[0]
failed = c.execute("SELECT COUNT(*) FROM jobs WHERE status='failed'").fetchone()[0]
print(f"pending={pending} running={running} done={done} failed={failed}")
# Show the running task
r = c.execute("SELECT id, field_name, model_id, kind, status FROM jobs WHERE status='running'").fetchone()
if r:
    print(f"running: id={r[0]} field={r[1]} model={r[2]} kind={r[3]}")
# Show pending tasks
for row in c.execute("SELECT id, field_name, model_id, kind FROM jobs WHERE status='pending' LIMIT 5").fetchall():
    print(f"pending: id={row[0]} field={row[1]} model={row[2]} kind={row[3]}")
# Count runs
runs = c.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
print(f"total runs: {runs}")
