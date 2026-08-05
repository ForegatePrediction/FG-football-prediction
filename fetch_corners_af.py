import os,json,urllib.request,time,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
KEY=os.environ["AF"]; B="https://v3.football.api-sports.io"; ROOT=os.path.dirname(os.path.abspath(__file__))
LEAGUES=[int(x) for x in sys.argv[1:]] or [253,169,292,98,307,262,71,128]; SEASONS=[2024,2025]
def get(u,t=8):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"x-apisports-key":KEY}),timeout=t))
def corners_of(fid):
    try: st=get(f"{B}/fixtures/statistics?fixture={fid}")
    except Exception: return fid,None
    d={}
    for team in st.get("response",[]):
        tid=team["team"]["id"]
        for s in team["statistics"]:
            if s["type"]=="Corner Kicks": d[tid]=s["value"] or 0
    return fid,d
t0=time.time()
for af in LEAGUES:
    dd=os.path.join(ROOT,"games",str(af),"data"); os.makedirs(dd,exist_ok=True)
    cf=os.path.join(dd,"corners.json")
    corners=json.load(open(cf)) if os.path.exists(cf) else []
    donef={c.get("fid") for c in corners}
    fixmap={}
    for s in SEASONS:
        fc=os.path.join(dd,f"_fix{s}.json")
        if os.path.exists(fc): fl=json.load(open(fc))
        else:
            try: fl=[{"fid":m["fixture"]["id"],"date":m["fixture"]["date"][:10],"home":m["teams"]["home"]["name"],
                      "away":m["teams"]["away"]["name"],"hid":m["teams"]["home"]["id"],"aid":m["teams"]["away"]["id"],
                      "ft":m["fixture"]["status"]["short"]} for m in get(f"{B}/fixtures?league={af}&season={s}",15)["response"]]
            except Exception: fl=[]
            json.dump(fl,open(fc,"w"))
        for x in fl:
            if x["ft"]=="FT": fixmap[x["fid"]]=x
    todo=[fid for fid in fixmap if fid not in donef]
    if not todo: continue
    cnt=0
    with ThreadPoolExecutor(max_workers=14) as ex:
        futs={ex.submit(corners_of,fid):fid for fid in todo}
        for fu in as_completed(futs):
            fid,d=fu.result()
            if d:
                x=fixmap[fid]; hc=d.get(x["hid"]); ac=d.get(x["aid"])
                if hc is not None and ac is not None:
                    corners.append({"fid":fid,"date":x["date"],"home":x["home"],"away":x["away"],"hc":hc,"ac":ac,"season":x["date"][:4]})
            cnt+=1
            if cnt%40==0: json.dump(corners,open(cf,"w"))
            if time.time()-t0>28: break
    json.dump(corners,open(cf,"w"))
    print(f"af {af}: 角球 {len(corners)} 场 (剩 {len(todo)-cnt})")
    if time.time()-t0>28: break
