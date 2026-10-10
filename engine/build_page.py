#!/usr/bin/env python3
"""Build smart/page_publish.html from smart/page_template.html.
  python3 smart/build_page.py <YYYY-MM-DD run date>
Fills __BOOK__ (friday.py book), __DATA__ (dashboard_data.json), __PRICED__ (runs/<date>/meals_all.json),
__TODAY__, __COOKS__ (rules.json household_members) and __CART_TRIGGER__ (config.json cart_trigger)."""
import sys, json, subprocess, os
today = sys.argv[1]
S = os.path.dirname(os.path.abspath(__file__))
J = lambda p, d=None: json.load(open(p)) if os.path.exists(p) else d
book = subprocess.run([sys.executable, os.path.join(S, 'friday.py'), 'book'], capture_output=True, text=True).stdout.strip() or '[]'
dp = os.path.join(S, '..', 'dashboard_data.json')
data = open(dp).read().strip() if os.path.exists(dp) else '{}'
pf = os.path.join(S, 'runs', today, 'meals_all.json')
priced = open(pf).read().strip() if os.path.exists(pf) else '{}'
rules = J(os.path.join(S, 'rules.json'), {}) or {}
cfg = J(os.path.join(S, 'config.json'), {}) or {}
cooks = json.dumps(rules.get('household_members') or [], ensure_ascii=False)
t = open(os.path.join(S, 'page_template.html')).read()
for k, v in {'__BOOK__': book, '__DATA__': data, '__PRICED__': priced, '__TODAY__': today,
             '__COOKS__': cooks, '__CART_TRIGGER__': cfg.get('cart_trigger', '')}.items():
    t = t.replace(k, v)
open(os.path.join(S, 'page_publish.html'), 'w').write(t)
print(len(t))
