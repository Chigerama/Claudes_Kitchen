"""Rank items from order_items.csv by how often they're ordered -> item_ranking.csv"""
import csv,re,collections,os
from datetime import date
H=os.path.dirname(os.path.abspath(__file__))
rows=list(csv.DictReader(open(os.path.join(H,"order_items.csv"))))
dates=sorted({r["date"] for r in rows}); N=len(dates)
_norm=lambda s: re.sub(r"\s+"," ",re.sub(r"\bpdm\b|\(per kg\)","",s.lower())).strip()
RULES=[(re.compile(r["pattern"],re.I),r["group"]) for r in csv.DictReader(open(os.path.join(H,"item_groups.csv")))]
def norm(s):
    for rx,g in RULES:
        if rx.search(s): return g
    return _norm(s)
agg=collections.defaultdict(lambda:{"orders":set(),"qty":0.0,"spend":0.0,"name":"","cat":"","prices":[]})
for r in rows:
    if float(r["ordered"])<=0: continue          # count what was asked for, not substitutes
    k=norm(r["item"]); a=agg[k]; a["orders"].add(r["date"]); a["qty"]+=float(r["ordered"])
    a["spend"]+=float(r["amount"]); a.setdefault("members",set()).add(r["item"].replace(" pdm","").replace(" (per kg)","")); a["name"]=k if any(k==g for _,g in RULES) else r["item"].replace(" pdm","").replace(" (per kg)",""); a["cat"]=r["category"]; a["prices"].append(float(r["unit_price"]))
out=[]
for k,a in agg.items():
    ds=sorted(a["orders"]); n=len(ds)
    gaps=[(date.fromisoformat(b)-date.fromisoformat(x)).days for x,b in zip(ds,ds[1:])]
    out.append({"item":a["name"],"category":a["cat"],"orders_with_item":n,"of_total_orders":N,"pct_of_orders":round(100*n/N),
      "total_qty":round(a["qty"],2),"avg_qty_per_order":round(a["qty"]/n,2),"typical_days_between":round(sorted(gaps)[len(gaps)//2]) if gaps else "",
      "min_price":min(a["prices"]),"max_price":max(a["prices"]),"total_spend":round(a["spend"],2),"first":ds[0],"last":ds[-1],"variants":len(a["members"]),"includes":" | ".join(sorted(a["members"]))})
out.sort(key=lambda x:(-x["orders_with_item"],-x["total_qty"]))
with open(os.path.join(H,"item_ranking.csv"),"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
print(N,"orders,",len(out),"distinct items")
for x in out[:45]: print(f'[{x["variants"]}] {x["orders_with_item"]:>2}/{N} qty{x["total_qty"]:>5} every~{x["typical_days_between"]}d ${x["min_price"]}-{x["max_price"]}  {x["item"]}')
c=collections.Counter(x["orders_with_item"] for x in out); print("distribution",sorted(c.items()))
