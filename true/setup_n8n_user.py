import bcrypt, sqlite3, secrets, datetime, json

pw = b"QuantLive2026!"
h = bcrypt.hashpw(pw, bcrypt.gensalt(10)).decode()

db = "/home/redou/.n8n/database.sqlite"
con = sqlite3.connect(db)
cur = con.cursor()

# check utilisateur existant
cur.execute("SELECT id, email FROM user")
users = cur.fetchall()
print("users before:", users)

uid = secrets.token_hex(16)
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
if users:
    uid = users[0][0]
    cur.execute("UPDATE user SET email=?, password=?, firstName=?, lastName=?, roleSlug=? WHERE id=?",
                ("quantlive@local.dev", h, "Quant", "Live", "global:owner", uid))
else:
    cur.execute("INSERT INTO user (id, email, password, firstName, lastName, roleSlug, createdAt, updatedAt) VALUES (?,?,?,?,?,?,?,?)",
                (uid, "quantlive@local.dev", h, "Quant", "Live", "global:owner", now, now))
con.commit()

# api key (supprime les anciennes du meme user/label)
cur.execute("DELETE FROM user_api_keys WHERE userId=? AND label=?", (uid, "quantlive"))
key = "nk_" + secrets.token_hex(24)
cur.execute("INSERT INTO user_api_keys (id, userId, label, apiKey, createdAt, updatedAt, scopes, audience) VALUES (?,?,?,?,?,?,?,?)",
            (secrets.token_hex(8), uid, "quantlive", key, now, now, "[\"*\"]", "quanthost"))
con.commit()
con.close()
print("KEY:", key)
print("user set:", uid)
