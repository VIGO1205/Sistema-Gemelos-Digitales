-- ============================================================================
-- Schema SQL para Motor IA M-6
-- Tablas de benchmark, predicciones y modelo activo por banco
-- ============================================================================

-- Tabla: Resultados de benchmark por modelo y banco
CREATE TABLE IF NOT EXISTS benchmark_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    model_type VARCHAR(20) NOT NULL CHECK (model_type IN ('CLASSIC', 'HYBRID')),
    bench INTEGER NOT NULL,
    rmse FLOAT,
    mae FLOAT,
    r2 FLOAT,
    mape FLOAT,
    bias FLOAT,
    uncertainty FLOAT,
    composite_score FLOAT,
    is_winner BOOLEAN DEFAULT FALSE,
    trained_at TIMESTAMP DEFAULT NOW(),
    hyperparameters JSONB DEFAULT '{}',
    feature_importance JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_benchmark_models_bench ON benchmark_models(bench);
CREATE INDEX IF NOT EXISTS idx_benchmark_models_model ON benchmark_models(model_name);
CREATE INDEX IF NOT EXISTS idx_benchmark_models_winner ON benchmark_models(is_winner) WHERE is_winner = TRUE;

-- Tabla: Predicciones detalladas por bloque para cada modelo
CREATE TABLE IF NOT EXISTS model_predictions (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(50) NOT NULL,
    bench INTEGER NOT NULL,
    block_id VARCHAR(50),
    x FLOAT,
    y FLOAT,
    z FLOAT,
    predicted_cu FLOAT,
    actual_cu FLOAT,
    residual FLOAT,
    p10 FLOAT,
    p50 FLOAT,
    p90 FLOAT,
    predicted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_model_predictions_bench ON model_predictions(bench);
CREATE INDEX IF NOT EXISTS idx_model_predictions_model ON model_predictions(model_name);
CREATE INDEX IF NOT EXISTS idx_model_predictions_block ON model_predictions(block_id);

-- Tabla: Modelo activo (ganador) por banco
CREATE TABLE IF NOT EXISTS active_models (
    id SERIAL PRIMARY KEY,
    bench INTEGER UNIQUE NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    composite_score FLOAT,
    rmse FLOAT,
    r2 FLOAT,
    activated_at TIMESTAMP DEFAULT NOW(),
    deactivated_at TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_active_models_bench ON active_models(bench);
CREATE INDEX IF NOT EXISTS idx_active_models_current ON active_models(is_current) WHERE is_current = TRUE;

-- Tabla: Log de experimentos para trazabilidad
CREATE TABLE IF NOT EXISTS experiment_logs (
    id SERIAL PRIMARY KEY,
    experiment_id VARCHAR(100) UNIQUE NOT NULL,
    bench INTEGER NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    phase VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    metrics JSONB DEFAULT '{}',
    duration_seconds FLOAT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiment_logs_exp ON experiment_logs(experiment_id);
CREATE INDEX IF NOT EXISTS idx_experiment_logs_bench ON experiment_logs(bench);

-- Vista: Resumen de benchmark por banco (solo ganadores)
CREATE OR REPLACE VIEW benchmark_winners AS
SELECT 
    b.bench,
    b.model_name,
    b.model_type,
    b.composite_score,
    b.rmse,
    b.mae,
    b.r2,
    b.mape,
    b.bias,
    b.trained_at
FROM benchmark_models b
WHERE b.is_winner = TRUE
ORDER BY b.bench DESC;

-- Funcion: Activar nuevo modelo ganador con metricas completas
CREATE OR REPLACE FUNCTION activate_model(
    p_bench INTEGER, 
    p_model_name VARCHAR, 
    p_score FLOAT,
    p_rmse FLOAT DEFAULT NULL,
    p_r2 FLOAT DEFAULT NULL,
    p_mae FLOAT DEFAULT NULL,
    p_mape FLOAT DEFAULT NULL,
    p_bias FLOAT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    -- Desactivar modelo anterior
    UPDATE active_models 
    SET is_current = FALSE, 
        deactivated_at = NOW() 
    WHERE bench = p_bench AND is_current = TRUE;
    
    -- Insertar nuevo modelo activo con metricas completas
    INSERT INTO active_models 
        (bench, model_name, composite_score, rmse, r2, mae, mape, bias)
    VALUES (p_bench, p_model_name, p_score, p_rmse, p_r2, p_mae, p_mape, p_bias)
    ON CONFLICT (bench) DO UPDATE 
    SET model_name = EXCLUDED.model_name,
        composite_score = EXCLUDED.composite_score,
        rmse = EXCLUDED.rmse,
        r2 = EXCLUDED.r2,
        mae = EXCLUDED.mae,
        mape = EXCLUDED.mape,
        bias = EXCLUDED.bias,
        activated_at = NOW(),
        deactivated_at = NULL,
        is_current = TRUE;
END;
$$ LANGUAGE plpgsql;
