import os,json,time,sys,requests
from concurrent.futures import ThreadPoolExecutor,as_completed
KEY=os.environ["AF"]; B="https://v3.football.api-sports.io"; ROOT=os.path.dirname(os.path.abspath(__file__))
TARGETS=[253,71,128,262,169,170,292,293,98,99,307,323,188]; SEASONS=[2024,2025]
S=requests.Session()
S.mount("https://",requests.adapters.HTTPAdapter(pool_connections=24,pool_maxsize=24,max_retries=1))
S.headers.update({"x-apisports-key":KEY})
def corners_of(fid):
    try: r=S.get(f"{B}/fixtures/statistics?fixture={fid}",timeout=12).json()
    except Exception: return fid,None
    d={}
    for team in r.get("response",[]):
        for s in team["statistics"]:
            if s["type"]=="Corner Kicks": d[team["team"]["id"]]=s["value"] or 0
    return fid,(d or None)
def cache_fixtures():
    for af in TARGETS:
        dd=os.path.join(ROOT,"games",str(af),"data"); os.makedirs(dd,exist_ok=True)
        for s in SEASONS:
            fc=os.path.join(dd,f"_fix{s}.json")
            if os.path.exists(fc): continue
            try: r=S.get(f"{B}/fixtures?league={af}&season={s}",timeout=15).json()["response"]
            except: continue
            json.dump([{"fid":m["fixture"]["id"],"date":m["fixture"]["date"][:10],"home":m["teams"]["home"]["name"],
                 "away":m["teams"]["away"]["name"],"hid":m["teams"]["home"]["id"],"aid":m["teams"]["away"]["id"],
                 "ft":m["fixture"]["status"]["short"]} for m in r],open(fc,"w"))
def run(budget=38):
    t0=time.time()
    for af in TARGETS:
        dd=os.path.join(ROOT,"games",str(af),"data"); cf=os.path.join(dd,"corners.json")
        corners=json.load(open(cf)) if os.path.exists(cf) else []
        done={c["fid"] for c in corners}
        fixmap={}
        for s in SEASONS:
            fc=os.path.join(dd,f"_fix{s}.json")
            if os.path.exists(fc):
                for x in json.load(open(fc)):
                    if x["ft"]=="FT": fixmap[x["fid"]]=x
        todo=[f for f in fixmap if f not in done]
        todo=todo[:max(0,200-len(corners))]
        if not todo: continue
        cnt=0
        with ThreadPoolExecutor(max_workers=16) as ex:
            futs={ex.submit(corners_of,f):f for f in todo}
            for fu in as_completed(futs):
                fid,d=fu.result()
                if d:
                    x=fixmap[fid];hc=d.get(x["hid"]);ac=d.get(x["aid"])
                    if hc is not None and ac is not None:
                        corners.append({"fid":fid,"date":x["date"],"home":x["home"],"away":x["away"],"hc":hc,"ac":ac,"season":str(x["date"][:4])})
                cnt+=1
                if cnt%80==0: json.dump(corners,open(cf,"w"))
                if time.time()-t0>budget: break
        json.dump(corners,open(cf,"w"))
        print(f"af {af}: {len(corners)}/{len(fixmap)}")
        if time.time()-t0>budget: break
cache_fixtures() if sys.argv[1:]==["fix"] else run()
