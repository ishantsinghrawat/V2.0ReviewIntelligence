from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date,timedelta
import math,re
from common import load_settings,load_json,save_json

def pct(n,d): return round((n/d*100),1) if d else 0.0

def neg(r): return r.get("sentiment_std")=="Negative" or int(r.get("rating") or 0)<=2

def severity(current,baseline,volume,avg_rating):
    ratio=current/max(baseline,0.5); anomaly=min(100,max(0,(ratio-1)*50)); vol=min(100,volume*12); rating=max(0,min(100,(5-avg_rating)*25))
    return round(.5*anomaly+.3*vol+.2*rating)

def release_health(rows):
    groups=defaultdict(list)
    for r in rows:
        if r.get("app_version"): groups[(r.get("source"),str(r["app_version"]))].append(r)
    out=[]
    for (source,ver),g in groups.items():
        if len(g)<2: continue
        nr=sum(neg(r) for r in g); ar=sum(float(r.get("rating") or 0) for r in g)/len(g)
        score=max(0,round(100-(pct(nr,len(g))*.65+(5-ar)*8)))
        out.append({"source":source,"version":ver,"reviews":len(g),"negative_pct":pct(nr,len(g)),"avg_rating":round(ar,2),"health_score":score,"status":"Healthy" if score>=70 else "Watch" if score>=45 else "Degrading"})
    return sorted(out,key=lambda x:(x["source"],-x["reviews"]))[:20]

def emerging(rows):
    # Lightweight, dependency-free phrase clustering for daily CI reliability.
    stop=set("the a an and or to of is it this that i my me for on in with was are be app can cannot cant not but have has had get got from when at as so just you your they their we our".split())
    phrases=Counter(); examples=defaultdict(list); meta=defaultdict(lambda:Counter())
    for r in rows:
        if not neg(r): continue
        words=[w for w in re.findall(r"[a-z']+",str(r.get("review") or "").lower()) if len(w)>2 and w not in stop]
        toks=[]
        for n in (2,3): toks += [" ".join(words[i:i+n]) for i in range(len(words)-n+1)]
        for p in set(toks):
            phrases[p]+=1
            if len(examples[p])<3: examples[p].append(str(r.get("review") or "")[:220])
            meta[p][f"source:{r.get('source')}"]+=1
            if r.get("app_version"): meta[p][f"version:{r.get('app_version')}"]+=1
    candidates=[]
    used=[]
    for p,c in phrases.most_common(80):
        if c<2 or any(p in u or u in p for u in used): continue
        used.append(p); top_source=next((k.split(':',1)[1] for k,_ in meta[p].most_common() if k.startswith('source:')),None); top_version=next((k.split(':',1)[1] for k,_ in meta[p].most_common() if k.startswith('version:')),None)
        candidates.append({"topic":p.title(),"mentions":c,"top_source":top_source,"top_version":top_version,"examples":examples[p]})
        if len(candidates)>=8: break
    return candidates

def main():
    s=load_settings(); rows=load_json("data_master.json"); settings=s["alerts"]
    dates=[date.fromisoformat(r["review_date"]) for r in rows if r.get("review_date")]
    latest=max(dates) if dates else date.today(); cats=s["categories"]
    anomalies=[]
    for cat in cats:
        def count_day(d): return sum(1 for r in rows if r.get("review_date")==d.isoformat() and neg(r) and (r.get("primary_category")==cat or any(i.get("label")==cat for i in (r.get("issues") or []) if isinstance(i,dict))))
        cur=count_day(latest); vals=[count_day(latest-timedelta(days=i)) for i in range(1,int(settings["baseline_days"])+1)]; base=sum(vals)/len(vals) if vals else 0
        relevant=[r for r in rows if r.get("review_date")==latest.isoformat() and neg(r) and (r.get("primary_category")==cat)]
        ar=sum(float(r.get("rating") or 0) for r in relevant)/len(relevant) if relevant else 5
        sev=severity(cur,base,cur,ar)
        triggered=cur>=settings["min_negative_reviews"] and cur>=max(1,base*settings["ratio_threshold"])
        anomalies.append({"category":cat,"current":cur,"baseline_daily_avg":round(base,2),"ratio":round(cur/max(base,.5),2),"severity":sev,"triggered":triggered})
    anomalies.sort(key=lambda x:(x["triggered"],x["severity"],x["current"]),reverse=True)
    dash=load_json("data.json"); negative=sum(neg(r) for r in dash); avg=sum(float(r.get("rating") or 0) for r in dash)/len(dash) if dash else 0
    summary={"generated_for":latest.isoformat(),"kpis":{"reviews":len(dash),"negative_pct":pct(negative,len(dash)),"avg_rating":round(avg,2),"alerts":sum(a["triggered"] for a in anomalies)},"anomalies":anomalies,"release_health":release_health(dash),"emerging_issues":emerging(dash)}
    save_json("analytics_summary.json",summary)
    print(f"alert={'true' if summary['kpis']['alerts'] else 'false'}")
    print(f"[analytics] alerts={summary['kpis']['alerts']}")

if __name__=="__main__": main()
