"""Exercise the real Phase 5 renderer with audited predictions, no external AI."""
import unittest
from pathlib import Path
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[2]


class Phase5UI(unittest.TestCase):
    def test_grouped_evaluation_renders_and_exports_without_hidden_negative_r2(self):
        code = '''
import sys, ast, json
from pathlib import Path
ROOT=Path(ROOT_LITERAL)
sys.path.insert(0,str(ROOT/'motor_ia_m6'))
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from config import MODELS, MODEL_COLORS
from evaluation.interpretation_engine import InterpretationEngine
from evaluation.statistical_tests import run_statistical_analysis, rmse_bootstrap
from evaluation.diagnostics import stability_curve
from evaluation.archive import evaluation_archive
render_dual_interpretation=lambda *a,**kw: None
e=ROOT/'entrega/articulo_RIAI/evidencia/streamlit_20261008'
m=json.loads((e/'audit.json').read_text(encoding='utf8'))
p=pd.read_csv(e/'predictions.csv')
preds={name:{'y_true':a.cu_bayesian.to_numpy(),'y_pred':a.predicted.to_numpy(),
 'residuals':a.residual.to_numpy()} for name,a in p.groupby('model',sort=False)}
st.session_state['benchmark_3170']=m['metrics']
st.session_state['predictions_3170']=preds
st.session_state['testdata_3170']={'df_test':p[p.model=='random_forest'].reset_index(drop=True)}
st.session_state['experiment_profile_3170']='drillholes_exploratory'
st.session_state['stat_tests_3170']=m['stat_tests']
# A stale CV entry must never be read for a drillhole experiment.
st.session_state['cv_3170']='stale unrelated run'
st.session_state['figure_limits']=[]
def record_plot(fig,*a,**kw):
 for ax in fig.axes:
  if ax.get_title().startswith('R² por Modelo'): st.session_state['figure_limits'].append(ax.get_xlim())
 plt.close(fig)
st.pyplot=record_plot
tree=ast.parse((ROOT/'motor_ia_m6/app.py').read_text(encoding='utf8'))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render_phase5_evaluation')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'phase5','exec'))
render_phase5_evaluation(3170)
'''.replace('ROOT_LITERAL', repr(str(ROOT)))
        app = AppTest.from_string(code).run(timeout=120)
        self.assertFalse(list(app.exception), [x.message for x in app.exception])
        self.assertLess(app.session_state['figure_limits'][0][0], -5.28)
        self.assertTrue(any('sondajes' in x.value for x in app.subheader))
        self.assertTrue(any('no se ejecutaron' in x.value for x in app.caption))
        self.assertTrue(list(app.get('download_button')))


if __name__ == '__main__': unittest.main()
