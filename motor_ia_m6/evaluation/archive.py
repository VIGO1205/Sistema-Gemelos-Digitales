"""Portable evidence for the actual Streamlit session, without pickled models."""
import io
import json
import zipfile
from importlib.metadata import version
import numpy as np
import pandas as pd


def evaluation_archive(results, predictions, test_frame, hyperparameters, provenance, statistics):
    def convert(value):
        if isinstance(value, np.ndarray):
            return value.tolist()
        if isinstance(value, np.generic):
            return value.item()
        raise TypeError(type(value).__name__)
    metadata = {'provenance': provenance, 'metrics': results,
                'hyperparameters': hyperparameters, 'statistics': statistics,
                'export_environment_versions': {p: version(p) for p in
                  ['numpy', 'scikit-learn', 'torch', 'xgboost', 'pykrige', 'joblib']},
                'mape_definition': 'Only measured Cu >= 1 percent; not all test samples',
                'test_selection_limitation': 'Winner ranked on this test; no independent post-selection validation'}
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('evaluation.json', json.dumps(metadata, ensure_ascii=False, indent=2, default=convert))
        for name, pred in predictions.items():
            frame = test_frame.reset_index(drop=True).copy() if test_frame is not None else pd.DataFrame()
            frame['actual'] = pred['y_true']
            frame['predicted'] = pred['y_pred']
            frame['residual'] = np.asarray(pred['y_true']) - np.asarray(pred['y_pred'])
            archive.writestr(f'predictions_{name}.csv', frame.to_csv(index=False))
    return stream.getvalue()
