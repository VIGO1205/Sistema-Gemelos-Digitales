"""Resume la evaluación terminada y comprueba la integridad de las comparaciones."""
from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'entrega/articulo_RIAI';T=OUT/'tablas';E=OUT/'evidencia'
run=json.loads((E/'ejecucion.json').read_text(encoding='utf-8'))
sel=json.loads((E/'seleccion_cinco.json').read_text(encoding='utf-8'))
assert run['all_completed'] and run['fit_count']==170
metrics=pd.read_csv(T/'metricas_pliegues.csv');means=pd.read_csv(T/'medias_semillas.csv')
oo=pd.read_csv(T/'predicciones_fuera_muestra.csv');inner=pd.read_csv(T/'particiones_internas_hibridos.csv')
outer=pd.read_csv(T/'particiones_explicitadas.csv');fits=pd.read_csv(T/'registro_ajustes.csv')
assert len(metrics)==170 and not metrics.duplicated(['protocol','fold','seed','model']).any()
for (protocol,fold),g in oo.groupby(['protocol','fold']):
    assert g.model.nunique()==7
    p=g.pivot(index='sample',columns='model',values='supported')
    assert p.notna().all().all() and p.nunique(axis=1).eq(1).all()
    assert g.groupby('sample').actual.nunique().eq(1).all()
for (protocol,fold,seed,model),g in inner.groupby(['protocol','fold','seed','model']):
    a=g[g.role=='fit'];b=g[g.role=='validation']
    assert not set(a.hole)&set(b.hole) and not set(a.group)&set(b.group)
    test=outer[(outer.protocol==protocol)&(outer.test_fold==fold)]
    assert not set(g['sample'])&set(test['sample']) and not set(g.hole)&set(test.hole)
weights=[]
for _,r in fits.iterrows():
    if r.model not in ['NN + Bayesian Kriging','Stacking Ensemble']:continue
    d=json.loads(r.details_json);row={k:r[k] for k in ['protocol','fold','seed','model']}
    row.update({k:d[k] for k in ['inner_fit_n','inner_validation_n','kriging_n_fit']})
    if 'nn_weight' in d:row.update(nn_weight=d['nn_weight'],ok_weight=1-d['nn_weight'])
    else:row.update(zip(['ok_weight','rf_weight','xgb_weight'],d['weights']));row['intercept']=d['intercept']
    weights.append(row)
pd.DataFrame(weights).to_csv(T/'pesos_hibridos.csv',index=False)
negative=[]
for (protocol,model),g in oo[oo.supported].groupby(['protocol','model']):
    negative.append({'protocol':protocol,'model':model,'n':len(g),'negative_predictions':int(g.predicted.lt(0).sum()),'minimum_prediction':float(g.predicted.min())})
pd.DataFrame(negative).to_csv(T/'predicciones_negativas.csv',index=False)
seed_winners=[]
for seed,g in means[(means.protocol=='sondajes')&means.model.isin(sel['principal_models'])].groupby('seed'):
    r=g.loc[g.rmse.idxmin()];seed_winners.append({'seed':int(seed),'winner':r.model,'mean_rmse':float(r.rmse)})
records=[]
for model,g in means[(means.protocol=='sondajes')&means.model.isin(sel['principal_models'])].groupby('model'):
    records.append({'model':model,'mean_rmse':float(g.rmse.mean()),'sd_rmse':float(g.rmse.std(ddof=1))})
protected_ok=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in run['protected_before'].items())
code_ok=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in run['configuration']['code_hashes'].items())
snapshot=E/'evaluar_cinco_ejecutado.py.txt'
recorded_code_ok=all(
    hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    or (p=='experimentos/articulo_riai/evaluar_cinco.py' and snapshot.exists()
        and hashlib.sha256(snapshot.read_bytes()).hexdigest()==h)
    for p,h in run['configuration']['code_hashes'].items())
report={'completed_fits':len(metrics),'models':7,'principal_models':5,'references':2,'same_test_observations_between_models':True,'inner_outer_overlap':0,'production_unchanged':protected_ok,'evaluated_code_unchanged':code_ok,'seed_winners':seed_winners,'seed_summary':records,'negative_predictions':negative}
report['recorded_code_verified']=recorded_code_ok
assert protected_ok and recorded_code_ok
(E/'comprobacion_cinco.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
