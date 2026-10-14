"""Cinco implementaciones originales y dos referencias, sin publicar modelos.

Replica las particiones de V1, hace explicitos los limites de los hibridos y
registra cada ajuste. Reanudable solo con huellas/configuracion identicas.
"""
from pathlib import Path
import os,sys,time,json,hashlib,platform,contextlib,io
from datetime import datetime,timezone
from importlib.metadata import version
sys.dont_write_bytecode=True
import numpy as np
import pandas as pd
import torch
from scipy.spatial import cKDTree
from sklearn.model_selection import GroupKFold,GroupShuffleSplit
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'backend/scripts'),str(ROOT/'motor_ia_m6')]
from copper_creek_samples import load_study_samples,source_hashes
from benchmark_copper_creek import centered_xyz,candidate,idw3_from_independent_holes
from models.baseline_kriging import KrigingModel
from models.stacking_ensemble import StackingEnsemble
from models.nn_bayesian import NNBayesianKriging
OUT=ROOT/'entrega/articulo_RIAI';T=OUT/'tablas';E=OUT/'evidencia';CACHE=E/'ajustes_cinco';CACHE.mkdir(exist_ok=True)
PRINCIPAL=['Ordinary Kriging','Random Forest','XGBoost','Stacking Ensemble','NN + Bayesian Kriging']
REFERENCES=['IDW3','Media'];NAMES=PRINCIPAL+REFERENCES
VERSIONS={p:version(p) for p in ['numpy','pandas','scipy','scikit-learn','xgboost','joblib','pykrige','torch']}
SOURCE=[ROOT/'motor_ia_m6/models'/f for f in ['baseline_kriging.py','stacking_ensemble.py','nn_bayesian.py','random_forest.py','xgboost_model.py']]+[ROOT/'backend/scripts/benchmark_copper_creek.py',Path(__file__)]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
configuration={'versions':VERSIONS,'source_hashes':source_hashes(),'code_hashes':{str(p.relative_to(ROOT)):sha(p) for p in SOURCE},'seeds':[42,43,44,45,46],'spatial_seed':42,'epochs':100,'torch_threads':1,'blas_threads':1,'kriging_max_training_points':500,'kriging_neighbors':64}
fingerprint=hashlib.sha256(json.dumps(configuration,sort_keys=True).encode()).hexdigest()
protected=[ROOT/'motor_ia_m6/model_artifacts/copper_creek_winner.joblib',ROOT/'motor_ia_m6/model_artifacts/copper_creek_winner.metadata.json',ROOT/'backend/data/copper_creek_mammoth.json']
before={str(p.relative_to(ROOT)):sha(p) for p in protected}
began=time.perf_counter();utc_start=datetime.now(timezone.utc).isoformat()
torch.set_num_threads(1);torch.set_num_interop_threads(1);torch.use_deterministic_algorithms(True)
_,_,points,by_hole,_=load_study_samples();xyz=centered_xyz(points);y=np.array([p[3] for p in points]);holes=np.array([p[5] for p in points])
old=pd.read_csv(T/'composites.csv',float_precision='round_trip')
assert len(old)==len(y) and np.allclose(old[['x','y','z','cu_pct']].to_numpy(),np.array([p[:4] for p in points]),atol=1e-12,rtol=0)
old_oof=pd.read_csv(T/'predicciones_fuera_muestra.csv')
sp=pd.read_csv(T/'grupos_espaciales.csv');mapping=dict(zip(sp.hole,sp.cell_200m));spatial=np.array([mapping[h] for h in holes])

def create(name,seed):
    if name in ['Random Forest','XGBoost']:return candidate(name).set_params(random_state=seed)
    if name=='Ordinary Kriging':return KrigingModel(spatial_dims=3,n_closest_points=64,max_training_points=500,random_state=seed)
    if name=='Stacking Ensemble':return StackingEnsemble(spatial_dims=3,rf_n_estimators=150,xgb_n_estimators=150,random_state=seed)
    if name=='NN + Bayesian Kriging':return NNBayesianKriging(spatial_dims=3,epochs=100,run_feature_importance=False,random_state=seed)

metrics=[];oof=[];coverage=[];split_rows=[];fit_rows=[];inner_rows=[]
for protocol,groups,seeds in [('sondajes',holes,[42,43,44,45,46]),('celdas_200m',spatial,[42])]:
 for fold,(tr,te) in enumerate(GroupKFold(5).split(xyz,y,groups),1):
    assert not set(holes[tr])&set(holes[te])
    baseline=idw3_from_independent_holes(xyz[tr],y[tr],holes[tr],xyz[te]);mask=np.isfinite(baseline)
    oldg=old_oof[(old_oof.protocol==protocol)&(old_oof.fold==fold)&(old_oof.model=='Random Forest')].sort_values('sample')
    assert np.array_equal(oldg['sample'].to_numpy(),te) and np.array_equal(oldg.supported.to_numpy(),mask)
    tree=cKDTree(xyz[tr]);dist=tree.query(xyz[te],k=1)[0];exhaust=np.array([len(set(holes[tr][ix]))>=3 for ix in tree.query_ball_point(xyz[te],120)])
    coverage.append({'protocol':protocol,'fold':fold,'test_samples':len(te),'supported_samples':int(mask.sum()),'support_full_radius':int(exhaust.sum()),'support_mask_disagreement':int((exhaust!=mask).sum()),'test_holes':len(set(holes[te]))})
    for i in te:split_rows.append({'protocol':protocol,'sample':int(i),'hole':str(holes[i]),'group':str(groups[i]),'test_fold':fold})
    for seed in seeds:
      for name in NAMES:
        if name in REFERENCES and seed!=42:continue
        slug=name.replace(' ','_').replace('+','plus');path=CACHE/f'{protocol}_{fold}_{seed}_{slug}.json'
        params={};details={};log=''
        if name in ['Stacking Ensemble','NN + Bayesian Kriging']:
            size=.30 if name=='Stacking Ensemble' else .15
            it,iv=next(GroupShuffleSplit(n_splits=1,test_size=size,random_state=seed).split(xyz[tr],y[tr],groups[tr]))
            assert not set(holes[tr[it]])&set(holes[tr[iv]])
            assert not set(groups[tr[it]])&set(groups[tr[iv]])
            for role,idx in [('fit',it),('validation',iv)]:
                for i in idx:inner_rows.append({'protocol':protocol,'fold':fold,'seed':seed,'model':name,'role':role,'sample':int(tr[i]),'hole':str(holes[tr[i]]),'group':str(groups[tr[i]])})
            details={'inner_fit_n':len(it),'inner_validation_n':len(iv),'inner_disjoint_holes':True,'inner_disjoint_groups':True,'internal_kriging_seed':42,'refits_all_outer_train':name=='Stacking Ensemble'}
        rec=json.loads(path.read_text()) if path.exists() else None
        if rec is not None and rec['fingerprint']==fingerprint:
            pred=np.array([np.nan if v is None else v for v in rec['predictions']]);secs=rec['seconds'];params=rec['params'];details=rec['details']
        else:
            tic=time.perf_counter()
            with threadpool_limits(limits=1):
                if name=='IDW3':pred=baseline
                elif name=='Media':pred=np.full(len(te),y[tr].mean())
                else:
                    model=create(name,seed);params=model.get_params();buf=io.StringIO()
                    with contextlib.redirect_stdout(buf):
                        if name in ['Stacking Ensemble','NN + Bayesian Kriging']:model.fit(xyz[tr],y[tr],groups=groups[tr])
                        else:model.fit(xyz[tr],y[tr])
                        pred=np.asarray(model.predict(xyz[te])).reshape(-1)
                    log=buf.getvalue()
                    if name=='Ordinary Kriging':details={'n_samples_fit':model.n_samples_fit,'variogram_parameters':model.model.variogram_model_parameters.tolist()}
                    if name=='Stacking Ensemble':details.update({'weights':model.meta_model.coef_.tolist(),'intercept':float(model.meta_model.intercept_),'kriging_n_fit':model.kriging.n_samples_fit,'rf_params':model.rf.get_params(),'xgb_params':model.xgb.get_params()})
                    if name=='NN + Bayesian Kriging':details.update({'nn_weight':float(model.nn_weight),'kriging_n_fit':model.kriging_model.n_samples_fit,'neural_parameters':sum(p.numel() for p in model.nn_model.parameters()),'device':str(model.device)})
            secs=time.perf_counter()-tic
            assert np.isfinite(pred[mask]).all(),name
            rec={'fingerprint':fingerprint,'params':params,'details':details,'predictions':[float(v) if np.isfinite(v) else None for v in pred],'seconds':secs,'utc':datetime.now(timezone.utc).isoformat(),'training_log':log}
            path.write_text(json.dumps(rec,ensure_ascii=False,indent=2,default=lambda v:int(v) if isinstance(v,np.integer) else str(v)),encoding='utf-8')
        a,b=y[te][mask],pred[mask]
        metrics.append({'protocol':protocol,'seed':seed,'fold':fold,'model':name,'n':len(a),'rmse':float(mean_squared_error(a,b)**.5),'mae':float(mean_absolute_error(a,b)),'r2':float(r2_score(a,b)),'bias':float(np.mean(b-a))})
        fit_rows.append({'protocol':protocol,'fold':fold,'seed':seed,'model':name,'train_n':len(tr),'test_n':len(te),'seconds':secs,'details_json':json.dumps(details)})
        if seed==42:
            for j,i in enumerate(te):oof.append({'protocol':protocol,'fold':fold,'sample':int(i),'hole':str(holes[i]),'model':name,'actual':float(y[i]),'predicted':float(pred[j]),'supported':bool(mask[j]),'nearest_train_m':float(dist[j])})
        pd.DataFrame(metrics).to_csv(T/'metricas_cinco_parcial.csv',index=False)
        print(f'{protocol} fold={fold} seed={seed} {name}: RMSE={metrics[-1]["rmse"]:.4f} ({secs:.1f}s)',flush=True)

df=pd.DataFrame(metrics);oo=pd.DataFrame(oof)
df.to_csv(T/'metricas_pliegues.csv',index=False);oo.to_csv(T/'predicciones_fuera_muestra.csv',index=False)
pd.DataFrame(coverage).to_csv(T/'cobertura.csv',index=False);pd.DataFrame(split_rows).to_csv(T/'particiones_explicitadas.csv',index=False)
pd.DataFrame(inner_rows).to_csv(T/'particiones_internas_hibridos.csv',index=False);pd.DataFrame(fit_rows).to_csv(T/'registro_ajustes.csv',index=False)
means=df.groupby(['protocol','seed','model'])[['rmse','mae','r2','bias']].mean().reset_index();means.to_csv(T/'medias_semillas.csv',index=False)
means.groupby(['protocol','model'])[['rmse','mae','r2']].agg(['mean','std']).to_csv(T/'resumen_semillas.csv')
pooled=[]
for (protocol,name),g in oo[oo.supported].groupby(['protocol','model']):pooled.append({'protocol':protocol,'model':name,'n':len(g),'rmse':mean_squared_error(g.actual,g.predicted)**.5,'mae':mean_absolute_error(g.actual,g.predicted),'r2':r2_score(g.actual,g.predicted)})
pd.DataFrame(pooled).to_csv(T/'metricas_agrupadas.csv',index=False)
main=means[(means.protocol=='sondajes')&(means.seed==42)&means.model.isin(PRINCIPAL)];winner=main.loc[main.rmse.idxmin(),'model']
wide=oo[(oo.protocol=='sondajes')&oo.supported].pivot(index=['sample','hole','actual'],columns='model',values='predicted').reset_index();boot=[]
for rival in [n for n in NAMES if n!=winner]:
    errs=wide.assign(win_sq=(wide[winner]-wide.actual)**2,other_sq=(wide[rival]-wide.actual)**2).groupby('hole').agg(n=('actual','size'),win=('win_sq','sum'),other=('other_sq','sum'))
    vals=errs.to_numpy();rng=np.random.default_rng(42);inds=rng.integers(0,len(vals),size=(2000,len(vals)));sums=vals[inds].sum(axis=1);delta=np.sqrt(sums[:,1]/sums[:,0])-np.sqrt(sums[:,2]/sums[:,0])
    boot.append({'comparison':winner+' - '+rival,'delta_pooled_rmse':float(np.sqrt(vals[:,1].sum()/vals[:,0].sum())-np.sqrt(vals[:,2].sum()/vals[:,0].sum())),'p025':float(np.quantile(delta,.025)),'p975':float(np.quantile(delta,.975)),'replicates':2000,'holes':len(vals)})
pd.DataFrame(boot).to_csv(T/'bootstrap_pareado.csv',index=False)
selection={'principal_models':PRINCIPAL,'reference_methods':REFERENCES,'criterion':'min mean RMSE of 5 hole folds, seed 42','study_winner':winner,'published_model_unchanged':'Random Forest','ranking_seed42':main.sort_values('rmse').to_dict('records'),'same_outer_folds_as_v1':True,'same_support_mask_as_v1':True,'inner_hole_and_group_overlap':0,'configuration':configuration}
(E/'seleccion_cinco.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
meta=json.loads(protected[1].read_text(encoding='utf-8'));diff={}
for name,s in meta['comparison'].items():
    cur=means[(means.protocol=='sondajes')&(means.seed==42)&(means.model==name)].iloc[0];diff[name]={m:float(cur[m]-s['mean_'+m]) for m in ['rmse','mae','r2']}
(E/'reproduccion_metadata.json').write_text(json.dumps(diff,indent=2),encoding='utf-8')
command='docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -e OPENBLAS_NUM_THREADS=1 -e OMP_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -v "C:\\Users\\benkr\\Sistema-Gemelos-Digitales:/study:ro" -v "C:\\Users\\benkr\\Sistema-Gemelos-Digitales\\entrega:/study/entrega:rw" -w /study --entrypoint python sistema-gemelos-digitales-motor-inference experimentos/articulo_riai/evaluar_cinco.py'
run={'utc_start':utc_start,'utc':datetime.now(timezone.utc).isoformat(),'command':command,'seeds':[42,43,44,45,46],'python':sys.version,'platform':platform.platform(),'processor':platform.processor(),'logical_cpus':os.cpu_count(),'versions':VERSIONS,'duration_seconds':time.perf_counter()-began,'fit_predict_seconds_total':sum(r['seconds'] for r in fit_rows),'source_hashes':source_hashes(),'script_sha256':sha(Path(__file__)),'protected_before':before,'protected_after':{str(p.relative_to(ROOT)):sha(p) for p in protected},'configuration':configuration,'fit_count':len(fit_rows),'all_completed':len(fit_rows)==170}
assert run['all_completed']
(E/'ejecucion.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
print('COMPLETE',winner,flush=True);print(means[means.seed==42].to_string(index=False),flush=True)
