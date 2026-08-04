import os,json,urllib.request,time,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
KEY=os.environ["AF"]; B="https://v3.football.api-sports.io"
ROOT=os.path.dirname(os.path.abspath(__file__))
POOLS=set(sys.argv[1:]) or {"B","C"}
rows=json.load(open("master_mapping.json"))
afids=list(dict.fromkeys([r["af_id"] for r in rows if r["pool"] in POOLS]))
SEASONS=[2021,2022,2023,2024,2025]
def get(af,s):
    try:
        req=urllib.request.Request(B+f"/fixtures?league={af}&season={s}",headers={"x-apisports-key":KEY})
        r=json.load(urllib.request.urlopen(req,timeout=12))
    except Exception: return af,s,None
    out=[]
    for m in r.get("response",[]):
        if m["fixture"]["status"]["short"]!="FT": continue
        g=m["goals"]
        if g["home"] is None or g["away"] is None: continue
        out.append({"date":m["fixture"]["date"][:10],"season":s,"home":m["teams"]["home"]["name"],
            "away":m["teams"]["away"]["name"],"hg":g["home"],"ag":g["away"]})
    return af,s,out
tasks=[]
for af in afids:
    f=os.path.join(ROOT,"games",str(af),"data","matches.json")
    have=set()
    if os.path.exists(f):
        try: have={m["season"] for m in json.load(open(f))}
        except: pass
    for s in SEASONS:
        if s not in have: tasks.append((af,s))
if not tasks: print("已全部抓取完"); sys.exit()
t0=time.time(); wrote=0
with ThreadPoolExecutor(max_workers=12) as ex:
    futs={ex.submit(get,af,s):(af,s) for af,s in tasks}
    for fu in as_completed(futs):
        af,s,out=fu.result()
        if out:
            d=os.path.join(ROOT,"games",str(af),"data"); os.makedirs(d,exist_ok=True)
            f=os.path.join(d,"matches.json")
            data=json.load(open(f)) if os.path.exists(f) else []
            if s not in {m["season"] for m in data}:
                data+=out; json.dump(data,open(f,"w")); wrote+=1
        if time.time()-t0>36: break
print("本轮落盘:",wrote)
