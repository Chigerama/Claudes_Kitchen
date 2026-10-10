"""Extract grocery line items from Woolworths tax-invoice PDFs into order_items.csv.
Keeps only date, category and item rows; customer name, order number and totals are dropped."""
import re, csv, glob, os, pdfplumber
from datetime import datetime
HERE=os.path.dirname(os.path.abspath(__file__))
def undouble(s):
    s=s.strip()
    return s[::2] if len(s)>1 and len(s)%2==0 and all(s[i]==s[i+1] for i in range(0,len(s),2)) else None
Q=r"([\d.]+) ([\d.]+)(?: kg)?(?: NET)?"
ROW=re.compile(r"^(\d+) (\* )?(\(Sub\) )?(.+?) "+Q+r" \$([\d.]+) \$([\d.]+)$")
BARE=re.compile(r"^(\d+) "+Q+r" \$([\d.]+) \$([\d.]+)$")
VW=re.compile(r"^(\d+) @ (\S+) \$([\d.]+)/Kg \$([\d.]+)$")
SKIP=("Sub Total","Invoice","Paid","Collection","Service","Thank you","Line Description","Supplied","Customer","Pickup")
rows=[]
for f in sorted(glob.glob(os.path.join(HERE,"*.pdf"))):
    with pdfplumber.open(f) as pdf:
        lines=[l for p in pdf.pages for l in (p.extract_text() or "").splitlines()]
    date=None; cat=""; section="Supplied"
    for i,l in enumerate(lines):
        u=undouble(l.replace("::",":")) if "::" in l else None
        if u is None and re.fullmatch(r"([^\s])\1([^\s]|\s)*",l.strip()): u=undouble(l)
        if u is None and all(undouble(w) for w in l.split()): u=" ".join(undouble(w) for w in l.split())
        if u:
            if u.startswith("Date:"): date=datetime.strptime(u[5:].strip(),"%d %b %Y").date().isoformat()
            elif u=="Substitutions": section="Substitutions"
            elif not u.startswith(SKIP): cat=u
            continue
        m=ROW.match(l)
        if m:
            n,g,sub,d,o,s,p,a=m.groups()
            rows.append([date,cat,section,d.strip(),bool(g),bool(sub),float(o),float(s),p,a]); continue
        m=BARE.match(l)
        if m:
            n,o,s,p,a=m.groups(); d=lines[i-1].strip()
            nxt=lines[i+1].strip() if i+1<len(lines) else ""
            if re.fullmatch(r"[\d.]+\s?(g|kg|ml|l|pack|each)",nxt,re.I): d+=" "+nxt
            rows.append([date,cat,section,d,False,False,float(o),float(s),p,a]); continue
        m=re.match(r"^(?:~ )?([A-Za-z].+?) (\d+) @ (\S+) \$([\d.]+)/Kg \$([\d.]+)$",l)
        if m:
            rows.append([date,cat,section,m.group(1)+" (per kg)",False,False,int(m.group(2)),int(m.group(2)),m.group(4),m.group(5)]); continue
        if l.startswith("~ ") and i+1<len(lines):
            m=VW.match(lines[i+1].strip())
            if m: rows.append([date,cat,section,l[2:].strip()+" (per kg)",False,False,int(m.group(1)),int(m.group(1)),m.group(3),m.group(4)])
out=os.path.join(HERE,"order_items.csv")
with open(out,"w",newline="") as fh:
    w=csv.writer(fh); w.writerow(["date","category","section","item","gst","substitute","ordered","supplied","unit_price","amount"]); w.writerows(rows)
print(len(rows),"rows ->",out)
