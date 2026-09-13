import re, esprima
f = "app/api/config_app.py"
s = open(f, encoding="utf-8").read()
si = s.rindex("<script>", 0, s.index("function apiQs"))
ei = s.index("</script>", si)
script = s[si+len("<script>"):ei]

# Split by top-level "function NAME(" boundaries
func_starts = [m.start() for m in re.finditer(r"\nfunction\s+\w+\s*\(", "\n"+script)]
func_starts = [m-1 for m in func_starts]
func_starts.append(len(script))
funcs = []
for k in range(len(func_starts)-1):
    seg = script[func_starts[k]:func_starts[k+1]]
    name = re.match(r"\n?function\s+(\w+)", seg)
    funcs.append((name.group(1) if name else "?", seg))

for nm, seg in funcs:
    try:
        esprima.parseScript(seg)
    except esprima.Error as e:
        print(f"BROKEN FUNCTION: {nm} -> {e}")
print("scan done, total", len(funcs))
