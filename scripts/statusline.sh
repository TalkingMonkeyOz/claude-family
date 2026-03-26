#!/bin/bash
# Claude Code Status Line — persistent context usage display
# Fields: context_window.used_percentage, cost.total_cost_usd, workspace.current_dir, model.display_name

read -r INPUT

echo "$INPUT" | PYTHONUTF8=1 python -c "
import json, sys
try:
    data = json.load(sys.stdin)
    cw = data.get('context_window') or {}
    pct_raw = cw.get('used_percentage')
    pct = int(pct_raw) if pct_raw is not None else 0
    cost = float(data.get('cost', {}).get('total_cost_usd') or 0)
    cwd = (data.get('workspace') or {}).get('current_dir') or ''
    project = cwd.replace(chr(92), '/').rstrip('/').split('/')[-1] if cwd else '?'
    model = (data.get('model') or {}).get('display_name') or '?'
    bar_w = 20
    filled = pct * bar_w // 100
    bar = '#' * filled + '-' * (bar_w - filled)
    if pct >= 70: c = chr(27) + '[31m'
    elif pct >= 50: c = chr(27) + '[33m'
    else: c = chr(27) + '[32m'
    r = chr(27) + '[0m'
    sys.stdout.write(c + 'CTX ' + str(pct) + '%' + r + ' [' + bar + '] ' + project + ' | ' + model + ' | $' + format(cost, '.2f') + chr(10))
except Exception as e:
    sys.stdout.write('CTX err: ' + str(e) + chr(10))
" 2>/dev/null || echo "CTX: fail"
