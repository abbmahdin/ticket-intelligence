import sqlite3, json
c = sqlite3.connect("/home/redou/.n8n/database.sqlite")
cur = c.cursor()
tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("TABLES:", tabs)
for t in ("webhook", "workflow_entity", "webhook_entity"):
    if t in tabs:
        print("===", t, "===")
        cols = [d[1] for d in cur.execute(f"PRAGMA table_info({t})")]
        print("cols:", cols)
        for r in cur.execute(f"SELECT * FROM {t}"):
            print(r)
