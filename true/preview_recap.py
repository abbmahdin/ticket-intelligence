import json, datetime

now = datetime.datetime.now(datetime.timezone.utc)
evs = [
  {"name":"FOMC Rate Decision","currency":"USD","impact":"high","starts_at":(now+datetime.timedelta(days=1, hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),"forecast":"4.50%","previous":"4.50%"},
  {"name":"Core CPI m/m","currency":"USD","impact":"high","starts_at":(now+datetime.timedelta(days=2, hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),"forecast":"0.2%","previous":"0.2%"},
  {"name":"Initial Jobless Claims","currency":"USD","impact":"medium","starts_at":(now+datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),"forecast":"235K","previous":"228K"},
]
mois=["janv.","fevr.","mars","avr.","mai","juin","juil.","aout","sept.","oct.","nov.","dec."]
jours=["lun.","mar.","mer.","jeu.","ven.","sam.","dim."]
def fmt_dt(dt): return f"{jours[dt.weekday()]} {dt.day} {mois[dt.month-1]} {dt.hour:02d}:{dt.minute:02d}"
def contexte(nom):
    n=nom.lower()
    if "fomc" in n or "fed" in n or "rate" in n: return "Decision de taux de la Fed -> fort impact directionnel sur l or."
    if "cpi" in n or "inflation" in n or "ppi" in n: return "Inflation US -> catalyseur majeur de volatilite sur XAU/USD."
    if "nfp" in n or "payroll" in n or "emploi" in n: return "Emploi US -> reevalue les anticipations de taux, impact fort."
    if "gdp" in n: return "Croissance US -> sentiment risk-on/off sur l or."
    if "retail" in n: return "Conso US -> indicateur de sante economique, impact moderne."
    if "jobless" in n or "claims" in n: return "Inscriptions au chomage -> tension sur le dollar, indirect sur l or."
    return "Event USD a surveiller pour les signaux XAU/USD."
lines=[]
for e in evs:
    dt=datetime.datetime.fromisoformat(e["starts_at"].replace("Z","+00:00"))
    badge="ROUGE FORT" if e["impact"]=="high" else "ORANGE MOYEN"
    extra=""
    if e.get("forecast"): extra+=f" | Attendu: {e['forecast']}"
    if e.get("previous"): extra+=f" | Precedent: {e['previous']}"
    lines.append(f"\n{badge} - {e['name']} ({e['currency']})\n   🗓 {fmt_dt(dt)}{extra}\n   💡 {contexte(e['name'])}")
recap=("📅 EVENEMENTS ECONOMIQUES A VENIR (XAU/USD)\n"+
"━━━━━━━━━━━━━━━━━━━━━━━━"+"\n".join(lines)+
"\n━━━━━━━━━━━━━━━━━━━━━━━━\n"+
"⚠️ Le bot penalise la confiance des signaux proches de ces annonces.")
print(recap)
