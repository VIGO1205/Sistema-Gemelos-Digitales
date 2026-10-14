"""Reconstruct the 2026-10-08 Streamlit evaluation with its recorded parameters.

No model is deployed and no old evidence is overwritten. The reconstruction
is explicitly a separate audit, never presented as the original UI session.
"""
from pathlib import Path
import sys, json, hashlib, platform, argparse
from datetime import datetime, timezone
from importlib.metadata import version
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'motor_ia_m6'))
import numpy as np
import pandas as pd
import torch
from threadpoolctl import threadpool_limits
from training.pipeline import TrainingPipeline
from evaluation.statistical_tests import rmse_bootstrap
from evaluation.diagnostics import stability_curve

parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path,
                    default=ROOT / 'entrega/articulo_RIAI/evidencia/streamlit_20261008')
OUT = parser.parse_args().output_dir
OUT.mkdir(parents=True, exist_ok=True)
if (OUT/'audit.json').exists() and json.loads((OUT/'audit.json').read_text(encoding='utf8')).get('finished_utc'):
    raise SystemExit('Evidencia finalizada: use --output-dir con otra carpeta para una nueva ejecución.')
DATA = ROOT / 'dataset/copper_creek_mammoth_streamlit.csv'
observed = {
 'kriging': [.3245, .1619, -5.2804, 58.7322, .0819],
 'random_forest': [.1127, .0676, .2431, 67.7298, .2262],
 'xgboost': [.1338, .0761, -.0668, 76.5524, .2225],
 'stacking': [.2338, .1658, -2.2586, 58.1543, .1463],
 'nn_bayesian': [.1491, .1044, -.3252, 83.3585, .1237],
}
params = {
 'random_forest': {'n_estimators': 200, 'max_depth': 10, 'min_samples_split': 5},
 'xgboost': {'n_estimators': 100, 'max_depth': 6, 'learning_rate': .05},
 'nn_bayesian': {'epochs': 100, 'learning_rate': .002},
}
metadata = {'audit_id': 'CC-STREAMLIT-20261008-AUDIT',
 'original_run': 'Capturas del usuario y metadatos exportados 2026-10-08T21:01:31Z',
 'started_utc': datetime.now(timezone.utc).isoformat(),
 'dataset_sha256': hashlib.sha256(DATA.read_bytes()).hexdigest(),
 'versions': {p: version(p) for p in ['numpy','pandas','scipy','scikit-learn','xgboost','pykrige','torch','joblib']},
 'python': platform.python_version(), 'parameters_from_screenshots': params,
 'original_metrics_rounded': {k: dict(zip(['rmse','mae','r2','mape','composite_score'],v)) for k,v in observed.items()},
 'cv': 'No ejecutada en la sesión de sondajes; sin Friedman ni Wilcoxon',
 'bootstrap': {'unit': 'hole_id', 'rmse_iterations': 1000, 'paired_iterations': 2000, 'seed': 42},
 'code_hashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [
 ROOT/'motor_ia_m6/models/nn_bayesian.py', ROOT/'motor_ia_m6/training/pipeline.py',
 ROOT/'motor_ia_m6/evaluation/statistical_tests.py', ROOT/'motor_ia_m6/evaluation/diagnostics.py', Path(__file__)]}}
(OUT/'audit.json').write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding='utf8')
torch.set_num_threads(1)
torch.set_num_interop_threads(1)
with threadpool_limits(limits=1):
 p = TrainingPipeline()
 df = p.load_from_file(str(DATA))
 X,y,features,df = p.preprocess(df)
 Xtr,Xv,Xte,ytr,yv,yte = p.split_data(X,y,df)
 tr,va,te = p._split_holes(df.hole_id.to_numpy(), .15,.15,42)
 split = df.copy()
 split['partition'] = ''
 for indices,label in [(tr,'train'),(va,'validation'),(te,'test')]:
  split.loc[split.index[indices],'partition'] = label
 split.to_csv(OUT/'partitions.csv',index=False)
 metadata['partition_counts'] = {label:{'rows':int(len(a)), 'holes':int(a.hole_id.nunique()),
  'cu_mean':float(a.cu_bayesian.mean()),'cu_std':float(a.cu_bayesian.std()),
  'cu_min':float(a.cu_bayesian.min()),'cu_max':float(a.cu_bayesian.max())}
  for label,a in split.groupby('partition')}
 p.hyperparameters['tuning'] = {k:{'best_params':v} for k,v in params.items()}
 p.train_all_models(Xtr,ytr,Xv,yv,tune_hyperparameters=False)
 p.evaluate_all_models(Xte,yte,p.get_test_frame(df))
 metadata['metrics'] = p.results
 metadata['used_parameters'] = p.hyperparameters['used']
 metadata['stat_tests'] = p.stat_tests
 metadata['rmse_bootstrap'] = {}
 metadata['stability'] = {}
 metadata['point_metric_differences'] = {}
 rows=[]
 for name, pr in p.predictions.items():
  frame = p.get_test_frame(df).copy()
  frame['model']=name
  frame['predicted']=pr['y_pred']
  frame['residual']=pr['residuals']
  rows.append(frame)
  metadata['point_metric_differences'][name] = {m:float(p.results[name][m]-metadata['original_metrics_rounded'][name][m]) for m in ['rmse','mae','r2']}
  metadata['rmse_bootstrap'][name] = rmse_bootstrap(yte,pr['y_pred'],frame.hole_id.to_numpy())
  print('STABILITY', name, flush=True)
  metadata['stability'][name] = stability_curve(p.models[name],Xte,yte,pr['y_pred'],[0,.01,.02,.05,.1,.15,.2])
 metadata['stability_noise_unit']='metres; same perturbations across models; 5 repetitions per nonzero level'
 metadata['finished_utc']=datetime.now(timezone.utc).isoformat()
 pd.concat(rows).to_csv(OUT/'predictions.csv',index=False)
 (OUT/'audit.json').write_text(json.dumps(metadata,indent=2,ensure_ascii=False,default=str),encoding='utf8')
 print(json.dumps({'metrics':p.results,'differences':metadata['point_metric_differences'],'counts':metadata['partition_counts']},indent=2),flush=True)
