p = "/home/redou/QuantLive/app/main.py"
s = open(p).read()

s = s.replace(
    '        "✅ QuantLive redémarré — Service opérationnel.\\n"\n'
    '        "📡 Les signaux XAU/USD reprennent automatiquement."\n',
    '        "✅ ORUSDTrade redémarré — Service opérationnel.\\n"\n'
    '        "📡 Les signaux XAU/USD reprennent automatiquement."\n',
)
s = s.replace(
    '        "🔧 QuantLive en maintenance — Redémarrage en cours.\\n"\n'
    '        "⏳ Les signaux reprendront dès le service rétabli."\n',
    '        "🔧 ORUSDTrade en maintenance — Redémarrage en cours.\\n"\n'
    '        "⏳ Les signaux reprendront dès le service rétabli."\n',
)
open(p, "w").write(s)
print("nom remplace par ORUSDTrade")
