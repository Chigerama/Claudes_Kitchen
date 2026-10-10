"""Weekly Woolworths helper.
  python3 smart/friday.py refresh                 re-read invoices, rebuild rankings + stats
  python3 smart/friday.py watchlist               JSON: product codes to price-check + names still needing codes
  python3 smart/friday.py codes <codes.json>      merge {name: {s: code, d: display, m: exact|guess}} into catalog
  python3 smart/friday.py propose <prices.json> <cart.json> <outof.json>   build this week's proposal
  python3 smart/friday.py record <approved.json> <cart_after.json>        log the run and learn from edits
"""
import sys, os, json, csv, re, math, glob, subprocess, datetime as dt, statistics as st, collections
S=os.path.dirname(os.path.abspath(__file__)); H=os.path.dirname(S)
J=lambda p,d=None: json.load(open(p)) if os.path.exists(p) else d
def W(p,o): json.dump(o,open(p,"w"),indent=1,ensure_ascii=False)
RULES=J(os.path.join(S,"rules.json")); CAT_P=os.path.join(S,"catalog.json"); LEARN_P=os.path.join(S,"learned.json")
def _today():
    tz=(RULES or {}).get("timezone") or ""
    try:
        from zoneinfo import ZoneInfo
        if tz: return dt.datetime.now(ZoneInfo(tz)).date()
    except Exception: pass
    return dt.date.today()
TODAY=_today()  # household's local date (rules.json "timezone", IANA name)
STOCK={k:v for k,v in J(os.path.join(S,"stock.json"),{}).items() if not k.startswith("_")}
RUN=os.path.join(S,"runs",TODAY.isoformat()); 
clean=lambda s: re.sub(r"\s+"," ",s.replace(" pdm","").replace(" (per kg)","")).strip().lstrip("* ").strip()
nz=lambda s: re.sub(r"[^a-z0-9]+"," ",s.lower()).replace(" each","").strip()

def groups():
    R=[(re.compile(r["pattern"],re.I),r["group"]) for r in csv.DictReader(open(os.path.join(H,"item_groups.csv")))]
    def g(s):
        for rx,n in R:
            if rx.search(s): return n
        return clean(s)
    return g

def stats():
    rows=list(csv.DictReader(open(os.path.join(H,"order_items.csv")))); g=groups()
    dates=sorted({r["date"] for r in rows}); D=[dt.date.fromisoformat(d) for d in dates]
    G=collections.defaultdict(lambda:{"orders":{}, "var":collections.Counter(), "prices":collections.defaultdict(list), "cat":collections.Counter()})
    for r in rows:
        if float(r["ordered"])<=0: continue
        k=g(r["item"]); a=G[k]; a["orders"][r["date"]]=a["orders"].get(r["date"],0)+float(r["ordered"])
        v=clean(r["item"]); a["var"][v]+=1; a["prices"][v].append(float(r["unit_price"])); a["cat"][r["category"]]+=1
    # purchases from cart runs not yet covered by an invoice
    latest=dates[-1] if dates else "0000"
    rd=os.path.join(S,"runs")
    for run in (sorted(os.listdir(rd)) if os.path.isdir(rd) else []):
        if run<=latest: continue
        for fn in ("approved.json","meals_approved.json"):
            a=J(os.path.join(rd,run,fn),{})
            if a.get("status")!="added": continue
            for ln in a.get("lines",[]):
                k=ln.get("group") or g(ln.get("name",""))
                G[k]["orders"][run]=G[k]["orders"].get(run,0)+float(ln.get("qty",1))
                if ln.get("name"): G[k]["var"][clean(ln["name"])]+=0
    out={}
    for k,a in G.items():
        ds=sorted(dt.date.fromisoformat(d) for d in a["orders"]); gaps=sorted((b-x).days for x,b in zip(ds,ds[1:]))
        out[k]={"orders":len(ds),"gap":gaps[len(gaps)//2] if gaps else None,"last":ds[-1].isoformat(),
                "since":(TODAY-ds[-1]).days,"qty":max(1,round(st.median(a["orders"].values()))),"qty_raw":round(st.median(a["orders"].values()),3),
                "variants":[v for v,_ in a["var"].most_common()],"usual":{v:st.median(p) for v,p in a["prices"].items()},"prange":{v:[min(p),max(p),len(p)] for v,p in a["prices"].items()},
                "category":(a["cat"].most_common(1) or [("Other",0)])[0][0]}
    return out,dates

WEB_D=os.path.join(S,"web_orders")
def merge_web_orders():
    """Append orders read from the Woolworths website to order_items.csv, unless a PDF invoice for that order exists."""
    if not os.path.isdir(WEB_D): return 0
    oi=os.path.join(H,"order_items.csv"); rows=list(csv.DictReader(open(oi)))
    pdf_ids={f.split("-")[0] for f in os.listdir(H) if f.lower().endswith(".pdf")}
    cat=catalog(); rev={}; catg={}
    for r in rows:
        c=code_for(clean(r["item"]),cat)
        if c: rev.setdefault(str(c),r["item"])
        catg.setdefault(r["item"],r["category"])
    n=0; out=[]
    for fn in sorted(os.listdir(WEB_D)):
        oid=fn.split(".")[0]
        if not fn.endswith(".json") or oid in pdf_ids: continue
        o=J(os.path.join(WEB_D,fn),{})
        for l in o.get("lines",[]):
            name=rev.get(str(l["code"])) or l["name"][:1].upper()+l["name"][1:].lower()+(" (per kg)" if l.get("kg") else "")
            out.append([o["date"],catg.get(name,l.get("cat") or "Other"),"Substitutions" if l.get("sub") else "Supplied",name,False,bool(l.get("sub")),
                        l["ordered"],l["supplied"],f'{l["price"]:.2f}',f'{l["amount"]:.2f}'])
        n+=1
    if out:
        with open(oi,"a",newline="") as fh: csv.writer(fh).writerows(out)
    return n

def cmd_web_orders(p):
    """p: JSON {order_id: {date, status, lines:[{code,name,ordered,supplied,price,amount,kg?,sub?}]}} read from the website. Saves new ones."""
    os.makedirs(WEB_D,exist_ok=True); new=[]
    for oid,o in J(p,{}).items():
        f=os.path.join(WEB_D,f"{oid}.json")
        if not os.path.exists(f) or J(f,{}).get("lines")!=o.get("lines"):
            W(f,{"date":o["date"],"status":o.get("status",""),"lines":o["lines"]}); new.append({"id":oid,"date":o["date"],"items":len(o["lines"])})
    print(json.dumps({"new":new}))

def cmd_known_orders():
    """Order ids already held (PDF invoices or website copies)."""
    ids={f.split("-")[0] for f in os.listdir(H) if f.lower().endswith(".pdf")}
    if os.path.isdir(WEB_D): ids|={f.split(".")[0] for f in os.listdir(WEB_D) if f.endswith(".json")}
    print(json.dumps(sorted(ids)))

def cmd_refresh():
    subprocess.run([sys.executable,os.path.join(H,"extract_orders.py")],check=True,stdout=subprocess.DEVNULL)
    merge_web_orders()
    subprocess.run([sys.executable,os.path.join(H,"build_ranking.py")],check=True,stdout=subprocess.DEVNULL)
    s,dates=stats(); W(os.path.join(S,"stats.json"),s); export_dashboard()
    seen=J(os.path.join(S,"seen_invoices.json"),[]); pdfs=sorted(f for f in os.listdir(H) if f.lower().endswith(".pdf"))
    new=[f for f in pdfs if f not in seen]; W(os.path.join(S,"seen_invoices.json"),pdfs)
    learn_from_invoice(dates[-1])
    print(json.dumps({"orders":len(dates),"latest_order":dates[-1],"new_invoices":len(new),"groups":len(s)}))

def export_dashboard():
    rows=list(csv.DictReader(open(os.path.join(H,"order_items.csv")))); g=groups(); dates=sorted({r["date"] for r in rows})
    P=collections.defaultdict(lambda:{"d":{},"p":[],"cat":collections.Counter(),"vp":collections.defaultdict(list),"s":0.0})
    for r in rows:
        if float(r["ordered"])<=0: continue
        k=g(r["item"]); a=P[k]; i=str(dates.index(r["date"])); a["d"][i]=round(a["d"].get(i,0)+float(r["ordered"]),2)
        a["p"].append(float(r["unit_price"])); a["cat"][r["category"]]+=1; a["vp"][clean(r["item"])].append(float(r["unit_price"])); a["s"]+=float(r["amount"])
    items=[{"n":k[0].upper()+k[1:],"c":a["cat"].most_common(1)[0][0],"d":a["d"],"p":a["p"],"v":sorted(a["vp"]),"vp":a["vp"],"s":round(a["s"],2)} for k,a in P.items()]
    json.dump({"dates":dates,"items":items},open(os.path.join(H,"dashboard_data.json"),"w"),separators=(",",":"))

def learn_from_invoice(latest):
    """Compare the most recent approved run with what was actually bought."""
    runs=sorted(d for d in os.listdir(os.path.join(S,"runs")) if os.path.exists(os.path.join(S,"runs",d,"approved.json")))
    if not runs: return
    r=runs[-1]; L=J(LEARN_P,{})
    if L.get("_invoice_checked")==r or latest<r: return
    appr=J(os.path.join(S,"runs",r,"approved.json"),{}).get("lines",[])
    rows=[x for x in csv.DictReader(open(os.path.join(H,"order_items.csv"))) if x["date"]==latest]; g=groups()
    bought={g(x["item"]) for x in rows if float(x["supplied"])>0}
    for ln in appr:
        e=L.setdefault(ln["group"],{"accepted":0,"declined":0,"removed_after":0,"notes":[]})
        if ln["group"] not in bought: e["removed_after"]+=1
    L["_invoice_checked"]=r; W(LEARN_P,L)

def match_outof(text,s,g):
    k=g(text)
    if k in s: return k
    q=set(nz(text).split()); best,bs=None,0
    for gk,v in s.items():
        toks=set(nz(gk).split())
        for vn in v["variants"][:3]: toks|=set(nz(vn).split())
        sc=len(q&toks)/len(q) if q else 0
        sc+= v["orders"]/1000
        if sc>bs: best,bs=gk,sc
    return best if bs>=0.6 else k

def pack_kg(name):
    """Pack weight in kg parsed from a product name ('650g', '1.1kg', '1.4kg - 2.2kg' -> lower bound); None if unknown."""
    m=re.findall(r"(\d+(?:\.\d+)?)\s?(kg|g)\b",(name or "").lower())
    if not m: return None
    v,u=m[0]; v=float(v); return v if u=="kg" else v/1000
def is_kg(p): return bool(p) and p.get("unit")=="KG"
def kg_qty(p,want):
    """Round a weight in kg to the product's selling step (e.g. 0.35 kg lots)."""
    step=p.get("step") or 0.1
    n=max(1,round((want or step)/step)); return round(n*step,3)

def catalog(): return J(CAT_P,{})

OUTOF_P=os.path.join(S,"outof_map.json")
GENERIC={"cheese","milk","bread","meat","chicken","beef","fruit","veg","vegetables","snacks","drinks","sauce","chips","biscuits","juice","yoghurt","pasta","rice","tea","coffee","soap","cleaner"}

def rank_search(text,hits):
    """Choose the most suitable Woolworths product for a free-text out-of item."""
    q=set(nz(text).split()); out=[]
    for i,h in enumerate(hits):
        if not h.get("s") or h.get("mkt"): continue
        name=h.get("d",""); toks=set(nz(name).split())
        sc=len(q&toks)/max(1,len(q))*2 - i*0.08
        if not h.get("av",True): sc-=5
        if h.get("was") and h.get("pr") and h["was"]>h["pr"]: sc+=0.3
        if nz(name).startswith("woolworths"): sc+=0.05
        out.append((round(sc,3),h))
    out.sort(key=lambda x:-x[0]); return [h for _,h in out]

def outof_lines(outof,s,g,cat,P,search,cart,have=None,pick=None):
    """Turn free-text out-of entries into proposal lines. Returns (lines, notes, statuses{doc_id:{...}})."""
    M=J(OUTOF_P,{}); lines=[]; notes=[]; st={}; have=set(have or [])
    for o in outof:
        text=o.get("text","").strip(); key=nz(text); did=o.get("id")
        if not text: continue
        # 1) remembered pick
        if key in M and M[key]["s"] not in NEVER and P.get(M[key]["s"],{}).get("av",True):
            m=M[key]; p=P.get(m["s"]) or {"pr":m.get("pr",0),"was":None,"d":m["d"],"av":True}
            lines.append(outline(text,m["s"],p,m.get("q",1),[],True,"remembered",cart)); st[did]={"status":"matched","match":p.get("d",m["d"])}; continue
        # 2) something bought before
        k=match_outof(text,s,g); v=s.get(k)
        if v and key not in GENERIC:
            chosen,fl=pick(k,v) if pick else (None,[])
            if chosen:
                n,c,p=chosen; q=kg_qty(p,v.get("qty_raw")) if is_kg(p) else v["qty"]
                if k in have: st[did]={"status":"matched","match":p["d"]+" (already on this week's list)"}; continue
                lines.append(outline(text,c,p,q,[],True,"usual",cart)); have.add(k); st[did]={"status":"matched","match":p["d"]}; continue
        # 3) search Woolworths
        hits=[h for h in rank_search(text,search.get(text,[])) if h.get("s") not in NEVER]
        if not hits:
            notes.append(f"Out-of list: nothing found on Woolworths for \"{text}\" - add it yourself"); st[did]={"status":"not found"}; continue
        best=hits[0]; alts=[{"code":h["s"],"name":h["d"],"price":h.get("pr")} for h in hits[1:4]]
        generic=key in GENERIC or len(key.split())<=1 and len(hits)>1 and nz(hits[0]["d"]).split()[:2]!=nz(hits[1]["d"]).split()[:2]
        p={"pr":best.get("pr"),"was":best.get("was"),"d":best["d"],"av":best.get("av",True),"cupStr":best.get("cupStr",""),"unit":best.get("unit",""),"step":best.get("step")}
        q=kg_qty(p,p.get("step")) if is_kg(p) else 1
        ln=outline(text,best["s"],p,q,alts,not generic,"search",cart)
        if generic: ln["flags"].append("Your note is broad - pick the product you meant")
        lines.append(ln); st[did]={"status":"needs a pick" if generic else "matched","match":best["d"]}
    return lines,notes,st

def outline(text,c,p,q,alts,tick,how,cart):
    l=line("out-of: "+text,c,p,q,["out-of list"],5,[],tick,cart,
           round(100*(p["was"]-p["pr"])/p["was"]) if p.get("was") and p.get("pr") and p["was"]>p["pr"] else 0)
    l.update({"outof_text":text,"alts":alts,"match_how":how}); return l
PH_P=os.path.join(S,"price_history.json")
def log_prices(P):
    """Keep one price observation per product per run date: {code: [[date, price, was], ...]}."""
    H_=J(PH_P,{}); d=TODAY.isoformat()
    for c,p in P.items():
        if not p.get("pr"): continue
        h=H_.setdefault(str(c),[]); h[:]=[x for x in h if x[0]!=d]+[[d,p["pr"],p.get("was") or p["pr"]]]; h.sort(); del h[:-52]
    W(PH_P,H_); return H_
def special_check(c,p,usual,prange,PH):
    """Is this 'special' real? Returns (is_special, flag-or-None). Also notes items that are rarely discounted."""
    pr,was=p.get("pr"),p.get("was"); disc=round(100*(was-pr)/was) if was and pr and was>pr else 0
    h=PH.get(str(c),[]) if c else []; on=[x for x in h if x[2]>x[1]]
    if disc>=R_MIN_SPECIAL():
        if len(h)>=4 and len(on)/len(h)>=0.6 and pr>=st.median(x[1] for x in on)*0.98:
            return False,f"On 'special' most weeks — ${pr:.2f} is effectively its normal price"
        return True,None
    if len(h)>=6 and not on:
        return False,"Rarely discounted — no point waiting for a special"
    return False,None
def R_MIN_SPECIAL(): return RULES.get("min_special_pct",20)
NEVER={int(k) for k in J(os.path.join(S,"never.json"),{})}
def code_for(name,cat): e=cat.get(nz(name)); return e and e.get("s")

def cmd_watchlist():
    s=J(os.path.join(S,"stats.json")); cat=catalog(); names=set()
    for k,v in s.items():
        if v["orders"]>=3 or k in RULES["core"]: names.update(v["variants"][:3])
    for lst in list(RULES["alternatives"].values())+list(RULES["rotate"].values()): names.update(lst)
    for r in J(os.path.join(S,"recipes.json"),{"recipes":[]})["recipes"]:
        for i in r["ing"]:
            if "any" in i: names.update(i["any"])
            elif "p" in i: names.add(i["p"])
            elif i.get("g") in s: names.update(s[i["g"]]["variants"][:1])
            elif i.get("fb"): names.add(i["fb"])
    codes=sorted({code_for(n,cat) for n in names if code_for(n,cat)}); missing=sorted(n for n in names if nz(n) not in cat)
    print(json.dumps({"codes":codes,"missing":missing}))

def cmd_codes(p):
    cat=catalog()
    for n,e in J(p).items():
        if e.get("s"): cat[nz(n)]={"name":n,**e}
    W(CAT_P,cat); print(len(cat),"catalog entries")

def cmd_propose(pp,cp,op,sp=None):
    s=J(os.path.join(S,"stats.json")); cat=catalog(); P={int(k):v for k,v in J(pp).items()}; cart={int(k):v for k,v in J(cp,{}).items()}
    outof=J(op,[]); L=J(LEARN_P,{}); R=RULES; g=groups(); lines=[]; notes=[]
    PH=log_prices(P)
    def price(code): return P.get(code) if code and code not in NEVER else None
    def pick(k,v):
        """Choose the product for a group: usual product, approved alternatives if unavailable, cheaper-per-unit alternative within approved list."""
        opts=v["variants"][:1]+R["alternatives"].get(k,[])+v["variants"][1:3]
        cands=[]
        for n in opts:
            c=code_for(n,cat); p=price(c)
            if c and p and p.get("av"): cands.append((n,c,p))
        if not cands: return None,["No approved product available"]
        if k in R.get("cheapest",[]): cands.sort(key=lambda x:(x[2].get("cup") or 9e9, x[2].get("pr") or 9e9))
        n,c,p=cands[0]; fl=[]
        if n!=v["variants"][0] and nz(n)!=nz(v["variants"][0]) and k not in R.get("cheapest",[]): fl.append(f"Usual product unavailable, using {p['d']}")
        if k in R["alternatives"]:
            cheaper=[x for x in cands[1:] if x[2].get("cup") and p.get("cup") and x[2]["cup"]<p["cup"]*(1-R["cheaper_per_unit_pct"]/100) and x[2].get("cm")==p.get("cm")]
            if cheaper: fl.append(f"Cheaper per {p.get('cm','unit')}: {cheaper[0][2]['d']} at ${cheaper[0][2]['cup']:.2f} vs ${p['cup']:.2f}")
        if cat.get(nz(n),{}).get("m")=="guess": fl.append("Product matched by name search - check it's right")
        return (n,c,p),fl
    fresh=set(R["fresh_categories"])
    for k,v in s.items():
        if k in R["never"] or k in R.get("dinner_groups",[]) or (v["orders"]<(2 if (k in R.get("staples_policy",{}).get("drink_groups",[]) or any(p in k.lower() for p in R.get("staples_policy",{}).get("drink_patterns",[]))) else 3) and k not in R["core"] and k not in R.get("staples_policy",{}).get("cycle_days",{})): continue
        chosen,fl=pick(k,v)
        if not chosen:
            if k in R["core"] or (v["gap"] and v["since"]>=v["gap"]): notes.append(f"{k}: {fl[0]}")
            continue
        cyc=R.get("staples_policy",{}).get("cycle_days",{}).get(k)
        if cyc: v=dict(v,gap=cyc)
        n,c,p=chosen; disc=round(100*(p["was"]-p["pr"])/p["was"]) if p.get("was") and p["was"]>p["pr"] else 0
        ratio=v["since"]/v["gap"] if v["gap"] else 0; isfresh=v["category"] in fresh
        stk=STOCK.get(k)
        if stk and v["gap"] and not isfresh and v["last"]<=stk["as_of"]:
            per=v["gap"]/max(v.get("qty_raw") or 1,0.5); left=stk["count"]*per-(TODAY-dt.date.fromisoformat(stk["as_of"])).days
            buf=R.get("stock_buffer_days",10)
            ratio=1 if left<=buf else 0.5 if left<=v["gap"] else 0
            if ratio==0: continue
            fl.append(f"Stock check: {stk['count']} on hand since {stk['as_of']}, about {max(0,round(left))} days left")
        usual=v["usual"].get(n) or st.median(list(v["usual"].values()))
        le=L.get(k,{}); penalty=le.get("declined",0)*0.15+le.get("removed_after",0)*0.1
        reasons=[]; qty=R["core"].get(k,v["qty"]); tick=True
        special,sfl=special_check(c,p,usual,v.get("prange",{}).get(n),PH)
        if not special: disc=0
        SP=R.get("staples_policy")
        kind="core" if k in R["core"] else "drink" if SP and (k in SP.get("drink_groups",[]) or any(p in k.lower() for p in SP.get("drink_patterns",[]))) else "utility" if SP and k in SP.get("rhythm_staples",[]) else ("utility" if SP and v["category"] in SP["utility_categories"] else "snack" if SP and v["category"] in SP["snack_categories"] else "other")
        if SP and kind=="other": continue
        if kind=="core": reasons.append("core")
        if kind=="drink": reasons.append("drinks")
        if kind=="snack":
            if not (special and ratio>=SP["snack_min_ratio"]): continue
            reasons.append("special")
        else:
            if ratio>=1: reasons.append("due")
            if special and (ratio>=(0.8 if isfresh else 0.5)): reasons.append("special")
        if kind!="snack" and special and not isfresh and disc>=R["stockup_special_pct"] and v["gap"] and ratio>=0.5:
            want=math.ceil(R["stockup_weeks"]*7/v["gap"]*v["qty"]); qty=max(qty,min(want,v["qty"]*R["stockup_max_multiple"])); reasons.append("stock-up")
        if not [x for x in reasons if x!="drinks"]: continue
        if sfl: fl.append(sfl)
        if is_kg(p): qty=kg_qty(p, v.get("qty_raw") if v.get("qty_raw",9)<5 else None)
        score=round(min(ratio,3)*0.5+disc/100*1.5+(1 if "core" in reasons else 0)-penalty,2)
        if usual and not re.search(r"per \d|\d+g? ?- ?\d|kg -|bulk",n.lower()) and p["pr"]>usual*(1+R["price_jump_pct"]/100): fl.append(f"Price jump: ${p['pr']:.2f} vs usual ${usual:.2f}"); tick=False
        if k in R["rotate"]:
            codes=[(x,code_for(x,cat)) for x in R["rotate"][k]]; codes=[(x,y) for x,y in codes if y and price(y) and price(y)["av"]]
            for i,(x,y) in enumerate(codes[:max(1,qty)]):
                lines.append(line(k,y,price(y),1,reasons,score,fl,tick,cart,disc))
            continue
        lines.append(line(k,c,p,qty,reasons,score,fl,tick,cart,disc))
    have={l["group"] for l in lines}
    search=J(sp,{}) if sp else {}
    ol,on,ost=outof_lines(outof,s,g,cat,P,search,cart,have,pick)
    for l in ol:
        if l["match_how"]=="usual":
            for x in lines:
                if x["code"]==l["code"]: x["reasons"].append("out-of list"); x["outof_text"]=l["outof_text"]; break
            else: lines.append(l)
        else: lines.append(l)
    notes+=on; W(os.path.join(RUN,"outof_status.json"),ost)
    for cname,members in ({} if R.get("dinner_groups") else R["clusters"]).items():
        hit=[m for m in members if m in have and any("special" in l["reasons"] for l in lines if l["group"]==m)]
        if not hit: continue
        for m in members:
            if m in have or m not in s: continue
            chosen,fl=pick(m,s[m])
            if chosen: n,c,p=chosen; lines.append(line(m,c,p,s[m]["qty"],[f"goes with {hit[0]} ({cname})"],0,fl,False,cart,0)); have.add(m)
    for l in lines: l["qty"]=round(l["qty"],3)
    incart=[l["name"] for l in lines if l["qty"]<=0]; lines=[l for l in lines if l["qty"]>0]
    if incart: notes.append(f"{len(incart)} due or special items are already in your cart at the usual quantity: "+", ".join(incart))
    lines.sort(key=lambda l:(-("core" in l["reasons"]),-l["score"]))
    os.makedirs(RUN,exist_ok=True)
    prop={"date":TODAY.isoformat(),"lines":lines,"notes":notes,"cart_existing":len(cart),
          "total_ticked":round(sum(l["price"]*l["qty"] for l in lines if l["tick"]),2)}
    W(os.path.join(RUN,"proposal.json"),prop); print(json.dumps(prop,ensure_ascii=False))

def line(k,c,p,qty,reasons,score,fl,tick,cart,disc):
    inc=cart.get(c,0)
    f=list(fl)+([f"Already {inc} in cart - adding {max(0,qty-inc)} more"] if inc else [])
    return {"group":k,"code":c,"name":p["d"],"qty":max(0,qty-inc) if inc else qty,"price":p["pr"],"was":p.get("was"),"disc":disc,
            "cup":p.get("cupStr"),"reasons":list(reasons),"score":score,"flags":f,"tick":tick and not (inc and inc>=qty),
            "unit":"kg" if is_kg(p) else "","step":p.get("step") if is_kg(p) else 1}

def cmd_outof_update(pp,cp,op,sp=None):
    """Saturday 10am: build lines for out-of entries added since the proposal. Prints {lines,notes,status}."""
    s=J(os.path.join(S,"stats.json")); cat=catalog(); P={int(k):v for k,v in J(pp).items()}; cart={int(k):v for k,v in J(cp,{}).items()}
    g=groups(); R=RULES
    def pick(k,v):
        opts=v["variants"][:1]+R["alternatives"].get(k,[])+v["variants"][1:3]
        for n in opts:
            c=code_for(n,cat); p=P.get(c) if c else None
            if c and c not in NEVER and p and p.get("av"): return (n,c,p),[]
        return None,["No approved product available"]
    lines,notes,st=outof_lines(J(op,[]),s,g,cat,P,J(sp,{}) if sp else {},cart,[],pick)
    print(json.dumps({"lines":lines,"notes":notes,"status":st},ensure_ascii=False))

def cmd_record(ap,cp):
    os.makedirs(RUN,exist_ok=True); L=J(LEARN_P,{}); done=L.setdefault("_recorded_runs",[])
    if TODAY.isoformat() in done: print("already recorded"); return
    a=J(ap); W(os.path.join(RUN,"approved.json"),{**a,"status":"added"}); W(os.path.join(RUN,"cart_after.json"),J(cp,{}))
    prop=J(os.path.join(RUN,"proposal.json"),{"lines":[]}); ok={l["code"] for l in a.get("lines",[])}
    M=J(OUTOF_P,{})
    for l in a.get("lines",[]):
        if l.get("outof_text"): M[nz(l["outof_text"])]={"s":l["code"],"d":l.get("name",""),"q":l.get("qty",1)}
    W(OUTOF_P,M)
    for l in prop["lines"]:
        e=L.setdefault(l["group"],{"accepted":0,"declined":0,"removed_after":0,"notes":[]})
        if l["code"] in ok: e["accepted"]+=1
        elif l["tick"]: e["declined"]+=1
    done.append(TODAY.isoformat()); W(LEARN_P,L); print("recorded")

def cmd_ingest(raw_prices,raw_cart):
    """raw_prices: 'code,price,was,avail,cup,cupMeasure;...'  raw_cart: 'code:qty code:qty ...' (text files)"""
    os.makedirs(RUN,exist_ok=True); byc={v["s"]:v.get("name") for v in catalog().values()}; P={}
    for part in open(raw_prices).read().replace("\n","").split(";"):
        f=part.strip().split(",")
        if len(f)<4 or not f[0].isdigit(): continue
        c=int(f[0]); fl=lambda x: float(x) if x not in ("",None) else None
        P[c]={"pr":fl(f[1]),"was":fl(f[2]),"av":f[3]=="1","cup":fl(f[4]) if len(f)>4 else None,"cm":f[5] if len(f)>5 else "",
              "cupStr":f"${f[4]} / {f[5]}" if len(f)>5 and f[4] else "","d":byc.get(c) or str(c),
              "unit":(f[6] if len(f)>6 else "").upper(),"step":fl(f[7]) if len(f)>7 and f[7] else None}
    cart={int(a):int(b) for a,b in (x.split(":") for x in open(raw_cart).read().split() if ":" in x)}
    W(os.path.join(RUN,"prices.json"),P); W(os.path.join(RUN,"cart.json"),cart); print(len(P),"prices,",len(cart),"cart lines")

def meal_fit(weight,d):
    M=RULES["meal_weather"]; ev=d["evening"]
    fit=next(v for lim,v in M[weight] if ev<=lim)
    if d["max"]>=M["hot_day_max"]:
        if weight=="hearty": fit=min(fit,M["hot_day_hearty_cap"])
        if weight=="light": fit=max(fit,M["hot_day_light_min"])
    if d["rain"]>=M["rain_mm"] and weight in ("hearty","medium"): fit=min(1,fit+M["rain_bonus_hearty_medium"])
    return fit

def cmd_meals(fp,pp,cp):
    """fp: open-meteo daily forecast JSON; pp/cp: prices.json / cart.json from ingest (may be {})."""
    s=J(os.path.join(S,"stats.json")); cat=catalog(); P={int(k):v for k,v in J(pp,{}).items()}; cart={int(k):v for k,v in J(cp,{}).items()}
    R=J(os.path.join(S,"recipes.json"))["recipes"]; hist=J(os.path.join(S,"meal_history.json"),[])
    F=J(fp); f=F["daily"]; ev=collections.defaultdict(list)
    for t,v in zip(F.get("hourly",{}).get("time",[]),F.get("hourly",{}).get("temperature_2m",[])):
        if 17<=int(t[11:13])<=20: ev[t[:10]].append(v)
    days=[{"date":d,"max":mx,"min":mn,"rain":r,"evening":round(st.mean(ev[d]),1) if ev[d] else round((mx+mn)/2,1)} for d,mx,mn,r in zip(f["time"],f["temperature_2m_max"],f["temperature_2m_min"],f["precipitation_sum"])]
    avg=st.mean(d["evening"] for d in days)
    sched={d:x for d,x in J(os.path.join(S,"schedule.json"),{}).items() if x.get("recipe") and d<TODAY.isoformat()}
    recent={h["id"] for h in hist if (TODAY-dt.date.fromisoformat(h["date"])).days<=14}|{x["recipe"] for d,x in sched.items() if (TODAY-dt.date.fromisoformat(d)).days<=14}
    cooked=collections.Counter(x["recipe"] for x in sched.values()); chosen=collections.Counter(h["id"] for h in hist)+cooked
    offered=collections.Counter()
    for fn in glob.glob(os.path.join(S,"runs","*","meals.json")):
        if TODAY.isoformat() in fn: continue
        offered.update({o["id"] for o in J(fn,{}).get("options",[])})
    def taste(rid):
        """Learned household preference: meals you plan and cook rise; ones repeatedly offered and never chosen sink."""
        if chosen[rid]: return min(chosen[rid],3)*0.15, ("a household favourite" if chosen[rid]>=3 else None)
        if offered[rid]>=3: return -min(0.1*(offered[rid]-2),0.4), "offered often, not chosen lately"
        return 0,None
    rhythm=set(RULES.get("staples_policy",{}).get("rhythm_staples",[]))
    staple_qty=collections.Counter({l["code"]:l["qty"] for l in J(os.path.join(RUN,"proposal.json"),{"lines":[]})["lines"] if l.get("tick")})
    def resolve(i):
        if (i.get("p") in rhythm) or (i.get("g") in rhythm):
            return {"name":(i.get("p") or i.get("g"))+" (pantry staple)","code":None,"qty":i.get("q",1),"price":None,"was":None,"special":False,"available":True,"in_cart":0,"group":i.get("g"),"optional":False,"note":"bought with staples on its usual cycle","pantry":True}
        if "any" in i:
            opts=[]
            for n in i["any"]:
                c=code_for(n,cat); p0=P.get(c) if c else None
                if c and c not in NEVER and p0 and p0.get("av",True) and p0.get("pr"):
                    sp_=special_check(c,p0,USUAL.get(nz(n)),None,PHM)[0]
                    opts.append((0 if sp_ else 1, p0.get("cup") or 9e9, n))
            name=sorted(opts)[0][2] if opts else i["any"][0]
        elif "p" in i: name=i["p"]
        else:
            v=s.get(i["g"])
            if not v:
                if not i.get("fb"): return None
                v={"variants":[i["fb"]]}
            opts=v["variants"][:1]+RULES["alternatives"].get(i["g"],[])+v["variants"][1:3]; name=opts[0]
            for n in opts:
                c=code_for(n,cat)
                if c and c not in NEVER and P.get(c,{}).get("av",True): name=n; break
        c=code_for(name,cat); nv=c in NEVER; c=None if nv else c; p=P.get(c,{}) if c else {}
        q=round((p.get("step") or 0.1)*i.get("q",1),3) if is_kg(p) else i.get("q",1)
        if i.get("kg") and p:
            if is_kg(p): st_=p.get("step") or 0.1; q=round(math.ceil(i["kg"]/st_-0.05)*st_,3)
            else:
                pw=(round(p["pr"]/p["cup"],3) if p.get("cm")=="1KG" and p.get("cup") and p.get("pr") else None) or pack_kg(p.get("d") or name)
                if pw: q=max(1,math.ceil(i["kg"]/pw-0.08))
        return {"name":p.get("d") or name,"code":c,"qty":q,"unit":"kg" if is_kg(p) else "","step":p.get("step") if is_kg(p) else 1,"price":p.get("pr"),"was":p.get("was"),
                "special":bool(c and p.get("pr") and special_check(c,p,USUAL.get(nz(name)),None,PHM)[0]),"available":p.get("av",True) if c else False,
                "in_cart":cart.get(c,0) if c else 0,"group":i.get("g"),"optional":bool(i.get("opt")),"key":i.get("g") or i.get("p"),
                "need":i.get("kg"),"pack":(((round(p["pr"]/p["cup"],3) if p.get("cm")=="1KG" and p.get("cup") and p.get("pr") else None) or pack_kg(p.get("d") or name)) if p and not is_kg(p) else None),"note":("on your never-order list" if nv else "") or i.get("note","") or ("also on this week's staples list" if c in staple_qty else ""),"in_staples":bool(c in staple_qty)}
    PAN=[set(w for w in nz(x).split() if len(w)>2) for x in J(os.path.join(S,"pantry.json"),[])]; PAN=[x for x in PAN if x]
    def in_pantry(*names):
        ws=set(nz(" ".join(n for n in names if n)).split())
        return any(pw<=ws for pw in PAN)
    PHM=J(PH_P,{}); USUAL={nz(vn):up for g_ in s.values() for vn,up in g_.get("usual",{}).items()}
    sname,season=next((k,v) for k,v in RULES["meal_seasons"].items() if not k.startswith("_") and TODAY.month in v["months"])
    opts=[]
    for r in R:
        wfit=st.mean(meal_fit(r["weight"],d) for d in days); ww=season["weather_weight"]
        fit=ww*wfit+(1-ww)*season["prefer"][r["weight"]]
        ings=[x for x in (resolve(i) for i in r["ing"]) if x]
        for i,x in zip([i for i in r["ing"] if resolve(i)],ings):
            if not x.get("pantry") and in_pantry(x["name"],i.get("g"),i.get("p")):
                x["in_pantry"]=True; x["note"]=(x["note"]+"; " if x["note"] else "")+"you have this in the pantry"
        ex_have=[e for e in r["extras"] if in_pantry(e)]; npan=sum(1 for x in ings if x.get("in_pantry"))+len(ex_have)
        sp=sum(x["special"] for x in ings); miss=[x["name"] for x in ings if (not x["code"] or not x["available"]) and not x.get("pantry")]
        score=round(fit*2+sp*0.25-(1.5 if r["id"] in recent else 0)-len(miss)*0.3+(0.2 if r["source"] in ("usual","paprika") else 0)+min(npan,3)*0.1+taste(r["id"])[0],2)
        why=[f"suits {avg:.0f}°C {sname} evenings" if fit>=.8 else "ok for this week's evenings" if fit>=.5 else ("better for warmer evenings" if r["weight"]=="light" else "better for cooler evenings")]
        if sp: why.append(f"{sp} ingredient{'s' if sp>1 else ''} on special")
        if r["id"] in recent: why.append("cooked in the last 2 weeks")
        if taste(r["id"])[1]: why.append(taste(r["id"])[1])
        if npan: why.append(f"uses {npan} thing{'s' if npan>1 else ''} from your pantry")
        cost=round(sum((x["price"] or 0)*x["qty"] for x in ings if not x["in_cart"] and not x["optional"] and not x.get("in_pantry")),2)
        opts.append({"id":r["id"],"name":r["name"],"source":r["source"],"weight":r["weight"],"mins":r["mins"],"score":score,"why":why,
                     "ingredients":ings,"extras":r["extras"],"extras_have":ex_have,"missing":miss,"cost":cost,"cooked":int(chosen[r["id"]]),"recent":r["id"] in recent})
    opts.sort(key=lambda o:-o["score"]); top=opts[:12]
    picks=[]; w=collections.Counter(); src=collections.Counter()
    for o in opts:
        if len(picks)>=5: break
        if w[o["weight"]]>=season["max_picks"][o["weight"]]: continue
        if src["new" if o["source"]=="new" else "yours"]>=3: continue
        picks.append(o["id"]); w[o["weight"]]+=1; src["new" if o["source"]=="new" else "yours"]+=1
    top+= [o for o in opts if o["id"] in picks and o not in top]
    for o in top: o["pick"]=o["id"] in picks
    out={"date":TODAY.isoformat(),"season":sname,"forecast":days,"avg_evening":round(avg,1),"options":top}
    os.makedirs(RUN,exist_ok=True); W(os.path.join(RUN,"meals.json"),out)
    W(os.path.join(RUN,"meals_all.json"),{o["id"]:{k:v for k,v in o.items() if k not in ("pick",)} for o in opts})
    print(json.dumps({"avg_evening":out["avg_evening"],"options":[(o["name"],o["weight"],o["score"],o["cost"],o["pick"],o["missing"]) for o in top]},ensure_ascii=False))

def cmd_meals_record(ap):
    a=J(ap); h=J(os.path.join(S,"meal_history.json"),[])
    if any(x.get("date")==a.get("date") and x["id"] in a.get("recipes",[]) for x in h): print("already recorded"); return
    os.makedirs(RUN,exist_ok=True); W(os.path.join(RUN,"meals_approved.json"),{**a,"status":"added"})
    h+= [{"id":i,"date":a.get("date",TODAY.isoformat())} for i in a.get("recipes",[])]; W(os.path.join(S,"meal_history.json"),h); print("recorded",len(a.get("recipes",[])))

def cmd_book():
    """Print the recipe book JSON embedded in the page (__BOOK__)."""
    R=J(os.path.join(S,"recipes.json"))["recipes"]
    print(json.dumps([{k:r[k] for k in ("id","name","weight","source","mins","serves","prep","cook","total","amounts","optional","method","extras","shares","paprika_uid","origin","origin_url","paprika_notes") if k in r}|{"optkeys":[i.get("g") or i.get("p") for i in r["ing"] if i.get("opt")]} for r in R if "method" in r],ensure_ascii=False,separators=(",",":")))

def cmd_recipe_removal(meals_p,mappr_p,sappr_p,cart_p,remove_ids):
    """Work out cart changes for removing recipe(s), keeping what other chosen recipes and staples still need.
    remove_ids: comma list of ALL recipes removed so far this week (including earlier removals). Prints [{code,name,from,to,why}]."""
    m=J(meals_p); ma=J(mappr_p); sa=J(sappr_p,{"lines":[]}); cart={int(k):v for k,v in J(cart_p).items()}
    rm=set(remove_ids.split(",")); skip=set(ma.get("skip",[])); chosen=[r for r in ma.get("recipes",[])]
    O={o["id"]:o for o in m["options"]}
    def need(ids):
        n=collections.Counter()
        for rid in ids:
            for i in O.get(rid,{}).get("ingredients",[]):
                k=f"{rid}|{i.get('code')}"
                if i.get("code") and not i.get("pantry") and k not in skip: n[i["code"]]+=i["qty"]
        return n
    staples=collections.Counter({l["code"]:l["qty"] for l in sa.get("lines",[])})
    remaining=[r for r in chosen if r not in rm]
    after=need(remaining)+staples; gone=need([r for r in chosen if r in rm])
    out=[]
    for code,q in gone.items():
        cur=cart.get(code,0); target=min(cur,max(cur-q,after.get(code,0)))
        why="still needed by "+", ".join(O[r]["name"] for r in remaining if any(i.get("code")==code for i in O[r]["ingredients"]))+(" / staples" if code in staples else "") if target>0 and after.get(code,0) else ""
        name=next((i["name"] for r in rm for i in O.get(r,{}).get("ingredients",[]) if i.get("code")==code),str(code))
        out.append({"code":code,"name":name,"from":cur,"to":target,"why":why})
    print(json.dumps(out,ensure_ascii=False))

def _sing(w):
    if len(w)>4 and w.endswith("ies"): return w[:-3]+"y"
    if len(w)>4 and w.endswith("oes"): return w[:-2]
    if len(w)>3 and w.endswith("s") and not w.endswith("ss"): return w[:-1]
    return w
def cmd_pantry_clean(p):
    """Read [{id,text,added?}] -> print plan {delete:[ids],update:{id:text},add:[texts],final:[texts]}.
    Deterministic tidy: lowercase, trim, split comma/semicolon/newline lists, drop exact and plural/word-order duplicates."""
    docs=sorted(J(p,[]),key=lambda d:(d.get("added") or "",d.get("id") or ""))
    seen={}; delete=[]; update={}; add=[]; final=[]
    def key(t): return " ".join(sorted(_sing(w) for w in nz(t).split()))
    for d in docs:
        raw=str(d.get("text") or ""); parts=[re.sub(r"\s+"," ",x).strip(" .-\u2022*\t").lower() for x in re.split(r"[,;\n]+",raw)]
        parts=[x for x in parts if key(x)]
        keep=[]
        for x in parts:
            k=key(x)
            if k in seen: continue
            seen[k]=x; keep.append(x)
        if not keep: delete.append(d["id"]); continue
        if keep[0]!=raw: update[d["id"]]=keep[0]
        final.append(keep[0])
        for x in keep[1:]: add.append(x); final.append(x)
    print(json.dumps({"delete":delete,"update":update,"add":add,"final":sorted(final)},ensure_ascii=False))


def cmd_recipe_delete(*ids):
    """Move recipes out of recipes.json into recipes_deleted.json (backup). Prints what moved."""
    P=os.path.join(S,"recipes.json"); B=os.path.join(S,"recipes_deleted.json")
    d=J(P); bk=J(B,[]); moved=[]
    keep=[]
    for r in d["recipes"]:
        if r["id"] in ids: bk.append({**r,"deleted":TODAY.isoformat()}); moved.append(r["id"])
        else: keep.append(r)
    d["recipes"]=keep; W(P,d); W(B,bk); print(json.dumps({"moved":moved,"missing":[i for i in ids if i not in moved]}))

if __name__=="__main__":
    c=sys.argv[1]; {"refresh":cmd_refresh,"watchlist":cmd_watchlist,"codes":cmd_codes,"propose":cmd_propose,"record":cmd_record,"ingest":cmd_ingest,"meals":cmd_meals,"meals_record":cmd_meals_record,"book":cmd_book,"recipe_removal":cmd_recipe_removal,"outof_update":cmd_outof_update,"web_orders":cmd_web_orders,"known_orders":cmd_known_orders,"pantry_clean":cmd_pantry_clean,"recipe_delete":cmd_recipe_delete}[c](*sys.argv[2:])
