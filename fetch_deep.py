import os,json,urllib.request,time,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
KEY=os.environ["AF"]; B="https://v3.football.api-sports.io"
ROOT=os.path.dirname(os.path.abspath(__file__))
rows=json.load(open("master_mapping.json"))
afids=list(dict.fromkeys([r["af_id"] for r in rows if r["pool"]=="A"]))
SEASONS=list(range(2016,2023))
TRIED=os.path.join(ROOT,"_deep_tried.json")
tried=set(tuple(x) for x in (json.load(open(TRIED)) if os.path.exists(TRIED) else []))
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
        if s not in have and (af,s) not in tried: tasks.append((af,s))
if not tasks: print("补史完成"); sys.exit()
t0=time.time(); wrote=0
with ThreadPoolExecutor(max_workers=12) as ex:
    futs={ex.submit(get,af,s):(af,s) for af,s in tasks}
    for fu in as_completed(futs):
        af,s,out=fu.result()
        if out is None:  # 请求失败,不标记(下次重试)
            continue
        tried.add((af,s))
        if out:
            d=os.path.join(ROOT,"games",str(af),"data"); f=os.path.join(d,"matches.json")
            data=json.load(open(f)) if os.path.exists(f) else []
            if s not in {m["season"] for m in data}:
                data+=out; json.dump(data,open(f,"w")); wrote+=1
        if time.time()-t0>26: break
json.dump([list(x) for x in tried],open(TRIED,"w"))
print("本轮落盘:",wrote,"| 累计已尝试:",len(tried),"| 待办剩:",len(tasks)-wrote)
