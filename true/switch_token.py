p = "/home/redou/QuantLive/app/services/_invisible_controller.py"
s = open(p).read()

# [V 2026-07-17] CORRECTIF CONFLIT TOKEN: utiliser le bot de signaux (token TELEGRAM_BOT_TOKEN)
# au lieu du token Hermes (qui est pollé par l'agent et capte /options avant nous).
# Le bot de signaux est deja dans le groupe ORUSDTrade => il peut poster + supprimer.
s = s.replace('getattr(get_settings(), "hermes_bot_token", "") or ""',
              'getattr(get_settings(), "telegram_bot_token", "") or ""')

remaining = s.count('hermes_bot_token')
print("hermes_bot_token restantes:", remaining)
assert remaining == 0

open(p, "w").write(s)
print("controller: bascule sur token bot de signaux")
