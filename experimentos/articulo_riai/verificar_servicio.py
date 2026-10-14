"""Comprueba consultas de lectura/predicción sin modificar el servicio."""
from pathlib import Path
import json,time,urllib.request,urllib.error,hashlib
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'entrega/articulo_RIAI/evidencia'
scene=json.loads((ROOT/'backend/data/copper_creek_mammoth.json').read_text(encoding='utf-8'))
rows=[]
for i in [0,len(scene['blocks'])//2,len(scene['blocks'])-1]:
    b=scene['blocks'][i];payload={k:b[k] for k in ['x','y','z']}
    req=urllib.request.Request('http://localhost:8502/api/models/copper-creek/predict',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(req,timeout=30) as r: result=json.load(r);status=r.status
        rows.append({'block':b['id'],'query':payload,'http_status':status,'response':result,'scene_prediction':b['cu_bayesian'],'absolute_difference':abs(result['predicted_cu_pct']-b['cu_bayesian']),'seconds':time.perf_counter()-start})
    except Exception as e: rows.append({'block':b['id'],'error':str(e)})
req=urllib.request.Request('http://localhost:8502/api/models/copper-creek/predict',data=json.dumps({'x':0,'y':0,'z':0}).encode(),headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req,timeout=30) as r: rows.append({'out_of_bounds_status':r.status})
except urllib.error.HTTPError as e: rows.append({'out_of_bounds_status':e.code,'detail':e.read().decode()})
out={'utc':datetime.now(timezone.utc).isoformat(),'command':'python experimentos/articulo_riai/verificar_servicio.py','checks':rows}
(OUT/'verificacion_servicio.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
