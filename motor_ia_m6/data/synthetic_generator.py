"""
Generador de Datos Sinteticos Realistas para Mineria
Crea datasets mineros con correlaciones geologicas realistas
"""

import numpy as np
import pandas as pd
from scipy import ndimage
from scipy.interpolate import Rbf


def generate_realistic_mining_data(bench: int, n_samples: int = 2000, random_state: int = 42):
    """
    Genera un dataset minero sintetico pero realista.
    
    Caracteristicas:
    - Zonas de enriquecimiento mineral (skarn, porfidico)
    - Contactos litologicos (andesita esteril vs mineralizado)
    - Efecto de alteracion supérgena (crisocola en zonas superficiales)
    - Patrones espaciales coherentes (no aleatorios)
    - Correlaciones realistas entre variables
    """
    np.random.seed(random_state + bench % 100)
    
    # Coordenadas espaciales (grid regular + ruido)
    # Asegurar que grid_size^2 >= n_samples
    grid_size = int(np.ceil(np.sqrt(n_samples)))
    x_grid = np.linspace(0, 500, grid_size)
    y_grid = np.linspace(0, 500, grid_size)
    xx, yy = np.meshgrid(x_grid, y_grid)
    
    # Añadir ruido aleatorio para hacerlo irregular
    total_points = grid_size * grid_size
    x = xx.flatten() + np.random.normal(0, 5, total_points)
    y = yy.flatten() + np.random.normal(0, 5, total_points)
    z = np.full(len(x), bench)
    
    # Truncar a n_samples exactos
    x = x[:n_samples]
    y = y[:n_samples]
    z = z[:n_samples]
    
    # ============================================================
    # 1. MODELO GEOLOGICO: Zonas de mineralizacion
    # ============================================================
    
    # Zona principal de skarn (elipse centrada)
    center_x, center_y = 250, 250
    a, b = 180, 120  # ejes de la elipse
    angle = np.pi / 6  # rotacion 30 grados
    
    # Distancia a la zona mineralizada (elipse rotada)
    x_rot = (x - center_x) * np.cos(angle) + (y - center_y) * np.sin(angle)
    y_rot = -(x - center_x) * np.sin(angle) + (y - center_y) * np.cos(angle)
    dist_to_zone = np.sqrt((x_rot / a)**2 + (y_rot / b)**2)
    
    # Asegurar que todas las variables tengan exactamente n_samples
    dist_to_zone = dist_to_zone[:n_samples]
    
    # Zona de enriquecimiento supérgena (cerca de la superficie = bancos altos)
    # A mayor elevacion (banco alto), mas enriquecimiento por crisocola
    elevation_factor = (3260 - bench) / 135  # 0 en fondo, 1 en superficie
    
    # ============================================================
    # 2. GENERAR LEY DE COBRE (cu_base)
    # ============================================================
    
    # Componente 1: Zona skarn (alta ley en elipse)
    skarn_grade = 0.8 * np.exp(-dist_to_zone**2 / 0.5)
    
    # Componente 2: Porfido periferico (anillo alrededor)
    porphyry_grade = 0.3 * np.exp(-(dist_to_zone - 1.2)**2 / 0.3)
    
    # Component 3: Enriquecimiento supérgena (crisocola)
    supergene_enrichment = 0.2 * elevation_factor * np.exp(-dist_to_zone**2 / 0.8)
    
    # Component 4: Ruido geologico (variograma)
    from scipy.ndimage import gaussian_filter
    noise_grid = np.random.normal(0, 0.1, (grid_size, grid_size))
    smooth_noise = gaussian_filter(noise_grid, sigma=2).flatten()[:n_samples]
    
    # Combinar componentes
    cu_base = skarn_grade + porphyry_grade + supergene_enrichment + smooth_noise
    cu_base = np.clip(cu_base, 0.05, 2.5)  # Limites realistas
    
    # ============================================================
    # 3. VARIABLES GEOLOGICAS
    # ============================================================
    
    # Tipo de roca: depende de la distancia a la zona
    rock_probs = np.column_stack([
        np.exp(-dist_to_zone**2 / 0.3),           # skarn
        np.exp(-(dist_to_zone - 1.0)**2 / 0.4),   # andesita
        np.exp(-(dist_to_zone - 0.7)**2 / 0.2)    # porfido
    ])
    rock_probs = rock_probs / rock_probs.sum(axis=1, keepdims=True)
    rock_types = np.random.choice(['skarn', 'andesite', 'porphyry'], 
                                   size=n_samples, p=[0.4, 0.35, 0.25])
    
    # Alteracion: correlacionada con tipo de roca y ley
    alteration_probs = {
        'skarn': [0.6, 0.3, 0.1],      # silice, argilica, propilitica
        'andesite': [0.1, 0.3, 0.6],
        'porphyry': [0.4, 0.4, 0.2]
    }
    alterations = []
    for rt in rock_types:
        alterations.append(np.random.choice(
            ['silica', 'argillic', 'propylitic'], 
            p=alteration_probs[rt]
        ))
    
    # SWIR alteration index: correlacionado con tipo de alteracion
    swir_map = {'silica': 0.8, 'argillic': 0.5, 'propylitic': 0.2}
    swir_base = np.array([swir_map[a] for a in alterations])
    swir_alteration_index = swir_base + np.random.normal(0, 0.1, n_samples)
    swir_alteration_index = np.clip(swir_alteration_index, 0, 1)
    
    # ============================================================
    # 4. VARIABLES ESTRUCTURALES
    # ============================================================
    
    # Falla principal (linea NNE-SSW)
    fault_x = 180
    fault_y = 300
    distance_to_fault = np.abs((x - fault_x) * np.cos(np.pi/3) + (y - fault_y) * np.sin(np.pi/3))
    distance_to_fault = np.clip(distance_to_fault, 5, 300)
    
    # Contacto litologico (curva)
    contact_curve = 200 + 100 * np.sin(x / 100)
    distance_to_contact = np.abs(y - contact_curve)
    distance_to_contact = np.clip(distance_to_contact, 2, 250)
    
    # ============================================================
    # 5. VARIABLES OPERACIONALES
    # ============================================================
    
    # Densidad de perforacion (mayor cerca de la zona mineralizada)
    blasthole_density = 8 + 12 * np.exp(-dist_to_zone**2 / 0.4) + np.random.poisson(2, n_samples)
    blasthole_density = np.clip(blasthole_density, 2, 25)
    
    # ============================================================
    # 6. INCERTIDUMBRE EPISTEMICA
    # ============================================================
    
    # Mayor incertidumbre en contactos y bordes de zonas
    epistemic_unc = 0.2 + 0.5 * np.exp(-(dist_to_zone - 1.0)**2 / 0.2)
    epistemic_unc += 0.1 * elevation_factor  # Mayor incertidumbre en superficie
    epistemic_unc = np.clip(epistemic_unc, 0.05, 0.9)
    
    # ============================================================
    # 7. INTERVALOS DE PREDICCION (P10, P50, P90)
    # ============================================================
    
    std = epistemic_unc * cu_base
    p10 = np.clip(cu_base - 1.28 * std, 0.01, None)
    p50 = cu_base
    p90 = cu_base + 1.28 * std
    
    # ============================================================
    # 8. LEY BAYESIANA (target): correccion del modelo base
    # ============================================================
    
    # El modelo bayesiano corrige el kriging base:
    # - Detecta enriquecimiento supérgena (crisocola) que kriging subestima
    # - Mejor estimacion en contactos litologicos
    bayesian_correction = (
        0.15 * supergene_enrichment +  # Correccion por crisocola
        0.05 * (1 - np.exp(-dist_to_zone**2 / 0.5)) +  # Mejor en zonas
        np.random.normal(0, 0.05, n_samples)  # Ruido
    )
    cu_bayesian = cu_base + bayesian_correction
    cu_bayesian = np.clip(cu_bayesian, 0.05, 2.5)
    
    # ============================================================
    # 9. CONSTRUIR DATAFRAME
    # ============================================================
    
    df = pd.DataFrame({
        'id': [f'BLK-{bench}-{i:04d}' for i in range(n_samples)],
        'x': np.round(x, 2),
        'y': np.round(y, 2),
        'z': z,
        'cu_base': np.round(cu_base, 4),
        'cu_bayesian': np.round(cu_bayesian, 4),
        'rock_type': rock_types,
        'alteration': alterations,
        'distance_to_fault': np.round(distance_to_fault, 2),
        'distance_to_contact': np.round(distance_to_contact, 2),
        'swir_alteration_index': np.round(swir_alteration_index, 4),
        'blasthole_density': blasthole_density,
        'epistemic_unc': np.round(epistemic_unc, 4),
        'p10': np.round(p10, 4),
        'p50': np.round(p50, 4),
        'p90': np.round(p90, 4),
    })
    
    return df


def generate_multi_bench_dataset(benches: list, samples_per_bench: int = 2000):
    """Genera dataset para multiples bancos"""
    dfs = []
    for bench in benches:
        print(f"Generando datos para banco {bench}m...")
        df = generate_realistic_mining_data(bench, samples_per_bench)
        dfs.append(df)
    
    return pd.concat(dfs, ignore_index=True)


def generate_process_control_data(n_points: int = 50, bench: int = 3170):
    """
    Genera datos de control de procesos (voladuras con leyes reales de planta)
    para la reconciliacion Mine-to-Mill
    """
    np.random.seed(42)
    
    # Generar voladuras
    blasts = []
    for i in range(n_points):
        blast_id = f'BLAST-{bench}-{i+1:03d}'
        
        # Ley real de planta (con error de medicion)
        true_grade = np.random.normal(0.85, 0.25)
        true_grade = np.clip(true_grade, 0.3, 1.8)
        
        # Prediccion Kriging (con bias sistematico)
        krig_bias = -0.08  # Kriging tiende a subestimar
        krig_noise = np.random.normal(0, 0.12)
        predicted_krig = true_grade + krig_bias + krig_noise
        
        # Prediccion Bayesiana (mejor, con menos bias)
        bayes_bias = -0.02
        bayes_noise = np.random.normal(0, 0.05)
        predicted_bayes = true_grade + bayes_bias + bayes_noise
        
        # Residuales
        residual_krig = true_grade - predicted_krig
        residual_bayes = true_grade - predicted_bayes
        
        blasts.append({
            'point_id': f'PC-{bench}-{i+1:03d}',
            'blast_id': blast_id,
            'timestamp': f'2026-08-{20 + i//3:02d} {8 + (i%3)*4:02d}:00:00',
            'bench': bench,
            'tonnage': np.random.randint(5000, 15000),
            'plant_feed_grade': np.round(true_grade, 4),
            'predicted_base_krig': np.round(predicted_krig, 4),
            'predicted_bayesian': np.round(predicted_bayes, 4),
            'residual_base': np.round(residual_krig, 4),
            'residual_bayesian': np.round(residual_bayes, 4),
        })
    
    return pd.DataFrame(blasts)


if __name__ == '__main__':
    # Generar dataset de ejemplo
    print("Generando dataset minero sintetico realista...")
    df = generate_realistic_mining_data(3170, n_samples=3000)
    print(f"Dataset generado: {len(df)} muestras")
    print(f"\nEstadisticas de ley:")
    print(df[['cu_base', 'cu_bayesian']].describe())
    print(f"\nPrimeras filas:")
    print(df.head())
    
    # Guardar como CSV
    output_path = '../data/processed/synthetic_mining_dataset.csv'
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\nDataset guardado en: {output_path}")
