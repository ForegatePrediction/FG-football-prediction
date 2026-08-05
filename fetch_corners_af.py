import os,json,urllib.request,time,sys
from concurrent.futures import ThreadPoolExecutor,as_completed
KEY=os.environ["AF"]; B="https://v3.football.api-sports.io"; ROOT=os.path.dirname(os.path.abspath(__file__))
# 非欧洲(无 football-data)的高价值联赛
TARGETS=[253,71,128,262,169,170,292,293,98,99,307,323,188]
SEASONS=[2024,2025]
def get(u,t=10):
    return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"x-apisports-key":KEY}),timeout=t))
def cache_fixtures():
    for af in TARGETS:
        dd=os.path.join(ROOT,"games",str(af),"data"); os.makedirs(dd,exist_ok=True)
        for s in SEASONS:
            fc=os.path.join(dd,f"_fix{s}.json")
            if os.path.exists(fc): continue
            try: r=get(f"{B}/fixtures?league={af}&season={s}",15)["response"]
            except Exception as e: print("fixerr",af,s,str(e)[:30]); continue
            fl=[{"fid":m["fixture"]["id"],"date":m["fixture"]["date"][:10],"home":m["teams"]["home"]["name"],
                 "away":m["teams"]["away"]["name"],"hid":m["teams"]["home"]["id"],"aid":m["teams"]["away"]["id"],
                 "ft":m["fixture"]["status"]["short"]} for m in r]
            json.dump(fl,open(fc,"w"))
def corners_of(fid):
    try: st=get(f"{B}/fixtures/statistics?fixture={fid}",8)
    except Exception: return fid,None
    d={}
    for team in st.get("response",[]):
        for s in team["statistics"]:
            if s["type"]=="Corner Kicks": d[team["team"]["id"]]=s["value"] or 0
    return fid,d
def run_stats(budget=34):
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
        if not todo: continue
        cnt=0
        with ThreadPoolExecutor(max_workers=20) as ex:
            futs={ex.submit(corners_of,f):f for f in todo}
            for fu in as_completed(futs):
                fid,d=fu.result()
                if d:
                    x=fixmap[fid];hc=d.get(x["hid"]);ac=d.get(x["aid"])
                    if hc is not None and ac is not None:
                        corners.append({"fid":fid,"date":x["date"],"home":x["home"],"away":x["away"],"hc":hc,"ac":ac,"season":str(x["date"][:4])})
                cnt+=1
                if cnt%30==0: json.dump(corners,open(cf,"w"))
                if time.time()-t0>budget: break
        json.dump(corners,open(cf,"w"))
        print(f"af {af}: {len(corners)}/{len(fixmap)} 场")
        if time.time()-t0>budget: break
if __name__=="__main__":
    if sys.argv[1:]==["fix"]: cache_fixtures(); print("fixtures cached")
    else: run_stats()
