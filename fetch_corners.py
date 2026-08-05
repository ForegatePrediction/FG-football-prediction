import os,csv,json,urllib.request,io,time
from concurrent.futures import ThreadPoolExecutor
ROOT=os.path.dirname(os.path.abspath(__file__))
FDMAP={39:"E0",40:"E1",140:"SP1",141:"SP2",135:"I1",78:"D1",79:"D2",61:"F1",88:"N1",94:"P1",179:"SC0"}
SEASONS=["1819","1920","2021","2122","2223","2324","2425"]
def dl(code,season):
    u=f"https://www.football-data.co.uk/mmz4281/{season}/{code}.csv"
    try:
        raw=urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=12).read().decode("latin-1")
    except Exception: return []
    out=[]
    for r in csv.DictReader(io.StringIO(raw)):
        hc,ac=r.get("HC"),r.get("AC")
        if not r.get("HomeTeam") or hc in("","NA",None) or ac in("","NA",None): continue
        try: hc=int(float(hc));ac=int(float(ac))
        except: continue
        out.append({"date":r.get("Date"),"home":r["HomeTeam"],"away":r["AwayTeam"],"hc":hc,"ac":ac,"season":season})
    return out
t0=time.time()
for af,code in FDMAP.items():
    p=os.path.join(ROOT,"games",str(af),"data","corners.json")
    if os.path.exists(p): continue
    if time.time()-t0>36: print("time-stop"); break
    data=[]
    with ThreadPoolExecutor(max_workers=7) as ex:
        for out in ex.map(lambda s:dl(code,s),SEASONS): data+=out
    if data:
        os.makedirs(os.path.dirname(p),exist_ok=True); json.dump(data,open(p,"w"))
        print(f"af {af} ({code}): {len(data)} 场")
