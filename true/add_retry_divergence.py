"""Ajoute retryOnFail au noeud 'Bougies M1' du workflow 'Divergence RSI'
pour absorber les ECONNRESET transitoires (pattern identique au workflow
Breakeven & Trailing : retryOnFail=true, maxTries=3, waitBetweenTries=4000).

Methode identique aux scripts n8n-stagger/* : UPDATE workflow_entity.nodes
direct + toggle active pour forcer n8n a recharger le workflow.
"""
import subprocess, re, json, sys, psycopg2

WID = 's3mB3XZazLE6vlV4'          # QuantLive - Divergence RSI
NODE_NAME = 'Bougies M1'

r = subprocess.run(['systemctl', '--user', 'cat', 'n8n.service'], capture_output=True, text=True)
pgpw = re.search(r'DB_POSTGRESDB_PASSWORD=(\S+)', r.stdout).group(1)

c = psycopg2.connect(host='127.0.0.1', port=5435, user='quantlive', password=pgpw, dbname='n8n')
c.autocommit = True
cur = c.cursor()

cur.execute("SELECT name, active, nodes FROM workflow_entity WHERE id=%s", (WID,))
row = cur.fetchone()
if row is None:
    print('ERREUR: workflow introuvable')
    sys.exit(1)
name, active, nodes = row[0], row[1], row[2]
nodes = nodes if isinstance(nodes, list) else json.loads(nodes)

found = False
for node in nodes:
    if node.get('name') == NODE_NAME:
        found = True
        before = dict(node)
        node['retryOnFail'] = True
        node['maxTries'] = 3
        node['waitBetweenTries'] = 4000
        print(f'Noeud trouve: {node.get("type")} v{node.get("typeVersion")}')
        print(f'  avant : retryOnFail={before.get("retryOnFail")} maxTries={before.get("maxTries")}')
        print(f'  apres : retryOnFail={node.get("retryOnFail")} maxTries={node.get("maxTries")} waitBetweenTries={node.get("waitBetweenTries")}')

if not found:
    print(f'ERREUR: noeud "{NODE_NAME}" introuvable dans le workflow {name}')
    sys.exit(1)

cur.execute("UPDATE workflow_entity SET nodes=%s WHERE id=%s", (json.dumps(nodes), WID))
# Toggle pour forcer n8n a recharger le workflow actif
cur.execute("UPDATE workflow_entity SET active=false WHERE id=%s", (WID,))
cur.execute("UPDATE workflow_entity SET active=true WHERE id=%s", (WID,))
print(f'  Workflow "{name}" mis a jour + toggled OK')

# Verification
print('\n=== VERIFICATION ===')
cur.execute("SELECT active, nodes FROM workflow_entity WHERE id=%s", (WID,))
active, nodes = cur.fetchone()
nodes = nodes if isinstance(nodes, list) else json.loads(nodes)
for node in nodes:
    if node.get('name') == NODE_NAME:
        ok = (node.get('retryOnFail') is True
              and node.get('maxTries') == 3
              and node.get('waitBetweenTries') == 4000)
        print(f'  retryOnFail={node.get("retryOnFail")} maxTries={node.get("maxTries")} '
              f'waitBetweenTries={node.get("waitBetweenTries")} -> {"OK" if ok else "ECHEC"}')
        print(f'  active={active}')

c.close()
print('\nDONE')
