P = "/home/redou/QuantLive/app/api/config_app.py"
s = open(P, encoding="utf-8").read()

old = '''    # 2) Fallback shared secret (admin direct browser access)
    provided = request.query_params.get("k") or request.headers.get("x-miniapp-key")
    if MINIAPP_SECRET and provided == MINIAPP_SECRET:
        return True
    raise_forbidden()'''

new = '''    # 2) Fallback shared secret — DESACTIVE par defaut (verrouillage total sur Telegram).
    # Reactivable ponctuellement pour du debug navigateur en posant MINIAPP_ALLOW_SECRET=true dans .env.
    import os as _os
    if _os.environ.get("MINIAPP_ALLOW_SECRET", "false").strip().lower() in ("1", "true", "yes", "on"):
        provided = request.query_params.get("k") or request.headers.get("x-miniapp-key")
        if MINIAPP_SECRET and provided == MINIAPP_SECRET:
            return True
    raise_forbidden()'''

if old in s:
    s = s.replace(old, new, 1)
    open(P, "w", encoding="utf-8").write(s)
    print("PATCHED: fallback secret desactive (initData seul)")
else:
    print("BLOC NON TROUVE — inspection manuelle requise")

import ast
ast.parse(open(P, encoding="utf-8").read())
print("SYNTAX OK")
