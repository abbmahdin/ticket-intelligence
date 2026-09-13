import json, os
for f in ['wf_lock.json', 'wf_disc.json']:
    p = os.path.expanduser('~/' + f)
    raw = json.load(open(p))
    print("TOP KEYS:", list(raw.keys()))
    w = raw.get('data', raw)
    print("=== NAME:", w.get('name'), "ID:", w.get('id'))
    for n in w.get('nodes', []):
        if n.get('type') == 'n8n-nodes-base.webhook':
            print("  webhook params:", json.dumps(n.get('parameters', {}), ensure_ascii=False))
            print("  webhook full keys:", list(n.keys()))
