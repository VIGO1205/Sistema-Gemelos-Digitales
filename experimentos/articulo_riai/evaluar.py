"""Experimentos aislados del manuscrito; nunca escribe artefactos de produccion."""
from pathlib import Path
import sys, os, json, csv, time, platform, hashlib
from datetime import datetime, timezone
from importlib.metadata import version
from collections import defaultdict
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'backend/scripts'))
from copper_creek_samples import load_study_samples, source_hashes, read_csv, number, trace_position
from benchmark_copper_creek import centered_xyz, candidate, idw3_from_independent_holes
OUT = ROOT / 'entrega/articulo_RIAI'
for part in ['evidencia','tablas','figuras','qa']:
    (OUT/part).mkdir(parents=True, exist_ok=True)

def save(name, obj):
    (OUT/'evidencia'/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2),encoding='utf-8')

start = time.perf_counter()
protected = [ROOT/'motor_ia_m6/model_artifacts/copper_creek_winner.joblib',ROOT/'motor_ia_m6/model_artifacts/copper_creek_winner.metadata.json',ROOT/'backend/data/copper_creek_mammoth.json']
hash_before = {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
collars, surveys, points, by_hole, invalid = load_study_samples()
xyz = centered_xyz(points)
y = np.array([p[3] for p in points])
holes = np.array([p[5] for p in points])
samples = pd.DataFrame(points,columns=['x','y','z','cu_pct','au_ppm','hole'])
samples.to_csv(OUT/'tablas/composites.csv',index=False)

# Audit interval support without changing the implementation under study.
bins = defaultdict(float)
intervals = defaultdict(list)
raw_counts = {}
for pat in ['*collars*csv','*surveys*csv','*assays*csv','*lithology*csv']:
    raw_counts[pat] = sum(1 for _ in read_csv(pat))
for row in read_csv('*assays*csv'):
    h=row['Hole ID']
    if h not in collars: continue
    a,b,g=(number(row[k]) for k in ['From (m)','To (m)','Cu (%)'])
    if None in (a,b,g) or not 0<=g<=20 or b<=a: continue
    intervals[h].append((a,b))
    for k in range(int(a//6),int((b-1e-8)//6)+1):
        bins[(h,k)]+=max(0,min(b,(k+1)*6)-max(a,k*6))
lengths=[]
for (h,k),l in bins.items():
    if l<1: continue
    x0,y0,z0=trace_position(collars[h],surveys[h],min(6*k+3,collars[h]['depth']))
    if 547950<=x0<=548990 and 3623410<=y0<=3624430 and 1120<=z0<=1350: lengths.append(l)
overlaps=0
for h,ii in intervals.items():
    end=-float('inf')
    for a,b in sorted(ii):
        overlaps+=int(a < end-1e-7)
        end=max(end,b)
quality={'raw_rows':raw_counts,'eligible_collars':len(collars),'study_holes':len(by_hole),'samples':len(y),'invalid_assay_rows_in_collar_window':invalid,'interval_overlaps_in_collar_window':overlaps,'partial_composites':sum(l<6-1e-6 for l in lengths),'overfull_composites':sum(l>6+1e-6 for l in lengths),'support_length_min':min(lengths),'support_length_max':max(lengths),'cu':{k:float(v) for k,v in samples.cu_pct.describe(percentiles=[.25,.5,.75,.9,.95,.99]).items()},'duplicate_xyz':int(samples.duplicated(['x','y','z']).sum()),'duplicate_hole_xyz':int(samples.duplicated(['hole','x','y','z']).sum())}
save('calidad.json',quality)

metrics=[]; oof=[]; masks=[]
# Spatial grouping keeps every drillhole intact and groups its sample centroid.
centroids=samples.groupby('hole')[['x','y']].mean()
spatial={h:f'{int(np.floor((r.x-548000)/200))}_{int(np.floor((r.y-3623400)/200))}' for h,r in centroids.iterrows()}
spatial_groups=np.array([spatial[h] for h in holes])
pd.DataFrame({'hole':holes,'cell_200m':spatial_groups}).drop_duplicates().to_csv(OUT/'tablas/grupos_espaciales.csv',index=False)
for protocol,groups,seeds in [('sondajes',holes,[42,43,44,45,46]),('celdas_200m',spatial_groups,[42])]:
    for fold,(tr,te) in enumerate(GroupKFold(5).split(xyz,y,groups),1):
        assert not (set(holes[tr]) & set(holes[te]))
        idw=idw3_from_independent_holes(xyz[tr],y[tr],holes[tr],xyz[te])
        supported=np.isfinite(idw)
        tree=cKDTree(xyz[tr])
        dist=tree.query(xyz[te],k=1)[0]
        # Full-radius support audit against production serving implementation.
        all_support=np.array([len(set(holes[tr][idx]))>=3 for idx in tree.query_ball_point(xyz[te],120)])
        masks.append({'protocol':protocol,'fold':fold,'test_samples':len(te),'supported_samples':int(supported.sum()),'support_full_radius':int(all_support.sum()),'support_mask_disagreement':int((all_support!=supported).sum()),'test_holes':len(set(holes[te]))})
        for seed in seeds:
            preds={}
            if seed==42:
                preds['IDW3']=idw
                preds['Media']=np.full(len(te),y[tr].mean())
            for name in ['Random Forest','XGBoost']:
                model=candidate(name).set_params(random_state=seed)
                t=time.perf_counter(); model.fit(xyz[tr],y[tr]); pred=model.predict(xyz[te]); secs=time.perf_counter()-t
                preds[name]=pred
            for name,pred in preds.items():
                a,b=y[te][supported],pred[supported]
                metrics.append({'protocol':protocol,'seed':seed,'fold':fold,'model':name,'n':len(a),'rmse':float(mean_squared_error(a,b)**.5),'mae':float(mean_absolute_error(a,b)),'r2':float(r2_score(a,b)),'bias':float(np.mean(b-a))})
                if seed==42:
                    for j,i in enumerate(te): oof.append({'protocol':protocol,'fold':fold,'sample':int(i),'hole':holes[i],'model':name,'actual':y[i],'predicted':pred[j],'supported':bool(supported[j]),'nearest_train_m':dist[j]})
        print(protocol,fold,'support',int(supported.sum()),flush=True)
df=pd.DataFrame(metrics)
df.to_csv(OUT/'tablas/metricas_pliegues.csv',index=False)
oo=pd.DataFrame(oof); oo.to_csv(OUT/'tablas/predicciones_fuera_muestra.csv',index=False)
pd.DataFrame(masks).to_csv(OUT/'tablas/cobertura.csv',index=False)
means=df.groupby(['protocol','seed','model'])[['rmse','mae','r2','bias']].mean().reset_index()
means.to_csv(OUT/'tablas/medias_semillas.csv',index=False)
summary=means.groupby(['protocol','model'])[['rmse','mae','r2']].agg(['mean','std'])
summary.to_csv(OUT/'tablas/resumen_semillas.csv')
pooled=[]
for (protocol,name),g in oo[oo.supported].groupby(['protocol','model']):
    pooled.append({'protocol':protocol,'model':name,'n':len(g),'rmse':mean_squared_error(g.actual,g.predicted)**.5,'mae':mean_absolute_error(g.actual,g.predicted),'r2':r2_score(g.actual,g.predicted)})
pd.DataFrame(pooled).to_csv(OUT/'tablas/metricas_agrupadas.csv',index=False)

# Paired descriptive resampling at drillhole level, fixed OOF predictions.
base=oo[(oo.protocol=='sondajes') & oo.supported]
wide=base.pivot(index=['sample','hole','actual'],columns='model',values='predicted').reset_index()
rng=np.random.default_rng(42); boot=[]
for rival in ['IDW3','XGBoost','Media']:
    errs=wide.assign(rf_sq=(wide['Random Forest']-wide.actual)**2,other_sq=(wide[rival]-wide.actual)**2).groupby('hole').agg(n=('actual','size'),rf=('rf_sq','sum'),other=('other_sq','sum'))
    vals=errs.to_numpy(); inds=rng.integers(0,len(vals),size=(2000,len(vals))); sums=vals[inds].sum(axis=1)
    delta=np.sqrt(sums[:,1]/sums[:,0])-np.sqrt(sums[:,2]/sums[:,0])
    boot.append({'comparison':'Random Forest - '+rival,'delta_pooled_rmse':float(np.sqrt(vals[:,1].sum()/vals[:,0].sum())-np.sqrt(vals[:,2].sum()/vals[:,0].sum())),'p025':float(np.quantile(delta,.025)),'p975':float(np.quantile(delta,.975)),'replicates':2000,'holes':len(vals)})
pd.DataFrame(boot).to_csv(OUT/'tablas/bootstrap_pareado.csv',index=False)
meta=json.loads(protected[1].read_text(encoding='utf-8'))
diff={}
for name,score in meta['comparison'].items():
    cur=means[(means.protocol=='sondajes')&(means.seed==42)&(means.model==name)].iloc[0]
    diff[name]={m:float(cur[m]-score['mean_'+m]) for m in ['rmse','mae','r2']}
save('reproduccion_metadata.json',diff)
save('ejecucion.json',{'utc':datetime.now(timezone.utc).isoformat(),'command':r'motor_ia_m6\venv\Scripts\python.exe experimentos\articulo_riai\evaluar.py','seeds':[42,43,44,45,46],'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'logical_cpus':os.cpu_count(),'versions':{p:version(p) for p in ['numpy','pandas','scipy','scikit-learn','xgboost','joblib']},'duration_seconds':time.perf_counter()-start,'source_hashes':source_hashes(),'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'protected_before':hash_before,'protected_after':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},'spatial_cells':len(set(spatial_groups))})
print(summary.to_string()); print(json.dumps(quality,indent=2)); print('FINISHED',flush=True)
