"""
tfm_comparar_jenny.py
══════════════════════════════════════════════════════════════════════
Analiza TODAS las combinaciones de Jenny (72 en total) y genera un
ranking de cuáles producen categorías mejor explicadas por las variables.

Para cada combinación válida calcula:
  - Accuracy (5-fold CV): qué tan bien predice el árbol las categorías
  - Top variable: cuál es la más informativa para esa combinación

Al final genera:
  - tfm_jenny_ranking_completo.csv   (todas las combinaciones, ordenadas)
  - tfm_jenny_ranking_completo.png   (gráfico comparativo)
  - tfm_jenny_top5_detalle/          (análisis detallado de las 5 mejores)
"""

import os, re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier, plot_tree, export_text
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import warnings
warnings.filterwarnings('ignore')

SCRIPTS    = os.path.dirname(os.path.abspath(__file__))
TFM        = os.path.dirname(SCRIPTS)
RAIZ       = os.path.dirname(TFM)
IMAGENES   = os.path.join(TFM, 'imagenes')
RESULTADOS = os.path.join(TFM, 'resultados')
TOP_DIR    = os.path.join(IMAGENES, 'top5_jenny')
os.makedirs(TOP_DIR, exist_ok=True)

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'axes.titlesize': 11, 'figure.dpi': 150})

FEATURES = [
    'densidad_pob', 'porc_65', 'ind_envej', 'porc_extranjeros',
    'tasa_natalidad', 'tasa_mortalidad', 'balance_vital_1000',
    'renta_media', 'subv_per_capita', 'bares_1000', 'restaurantes_1000',
    'alojamiento_1000', 'estab_total_1000', 'tiene_cs', 'tiene_hospital',
    'dist_cs_km', 'dist_hospital_km', 'tiene_colegio', 'tiene_instituto',
    'dist_colegio_km', 'dist_instituto_km', 'tiene_residencia',
    'plazas_residencia_1000', 'dist_residencia_km', 'dist_capital_km',
    'superficie_km2',
]

NOMBRES_ES = {
    'densidad_pob': 'Densidad (hab/km2)', 'porc_65': '% Mayores de 65',
    'ind_envej': 'Indice envejecimiento', 'porc_extranjeros': '% Pob. extranjera',
    'tasa_natalidad': 'Tasa natalidad', 'tasa_mortalidad': 'Tasa mortalidad',
    'balance_vital_1000': 'Balance vital /1000', 'renta_media': 'Renta media',
    'subv_per_capita': 'Subvenciones p.c.', 'bares_1000': 'Bares /1000',
    'restaurantes_1000': 'Restaurantes /1000', 'alojamiento_1000': 'Alojamiento /1000',
    'estab_total_1000': 'Total estab. /1000', 'tiene_cs': 'Tiene C. Salud',
    'tiene_hospital': 'Tiene hospital', 'dist_cs_km': 'Dist. C. Salud (km)',
    'dist_hospital_km': 'Dist. hospital (km)', 'tiene_colegio': 'Tiene colegio',
    'tiene_instituto': 'Tiene instituto', 'dist_colegio_km': 'Dist. colegio (km)',
    'dist_instituto_km': 'Dist. instituto (km)', 'tiene_residencia': 'Tiene residencia',
    'plazas_residencia_1000': 'Plazas residencia /1000', 'dist_residencia_km': 'Dist. residencia (km)',
    'dist_capital_km': 'Dist. capital (km)', 'superficie_km2': 'Superficie (km2)',
}

NOMBRES_MET = {'mm': 'Min-Max', 'z': 'Z-score', 'rel': 'Relativa', 'corr': 'Correlacion'}
NOMBRES_ALG = {'kmeans': 'K-Means', 'kmedoids': 'K-Medoids'}

# ── 1. Cargar variables ────────────────────────────────────────────────────────

print("Cargando dataset_tfm.csv...")
df_vars = pd.read_csv(os.path.join(RESULTADOS, 'dataset_tfm.csv'), encoding='utf-8-sig')
df_vars.columns = df_vars.columns.str.strip()
df_vars['codigo_ine'] = df_vars['codigo_ine'].astype(str).str.zfill(5)
for col in ['bares_1000', 'restaurantes_1000', 'alojamiento_1000', 'estab_total_1000']:
    df_vars[col] = df_vars[col].fillna(0)

# ── 2. Cargar todas las claves de Jenny ────────────────────────────────────────

print("Leyendo datos_jenny.js...")
with open(os.path.join(RAIZ, 'datos_jenny.js'), encoding='utf-8') as f:
    contenido = f.read()

claves = sorted(set(re.findall(r'"((?:kmeans|kmedoids)_\w+)"', contenido)))
print(f"  Total combinaciones: {len(claves)}")

# ── 3. Analizar cada combinación ───────────────────────────────────────────────

resultados = []
discretas = [f in ('tiene_cs','tiene_hospital','tiene_colegio',
                    'tiene_instituto','tiene_residencia') for f in FEATURES]

print("\nAnalizando combinaciones...")
print(f"  {'Combinacion':<22} {'Clusters':>8} {'Municipios':>10} {'Accuracy':>10}  Top variable")
print("  " + "-"*80)

for clave in claves:
    # Extraer datos de Jenny para esta combinación
    m = re.search(r'"' + clave + r'"\s*:\s*\{([^}]*)\}', contenido)
    if not m:
        continue
    pares = re.findall(r'"(\d+)"\s*:\s*(-?\d+)', m.group(1))
    df_jenny = pd.DataFrame(pares, columns=['codigo_ine', 'cluster_jenny'])
    df_jenny['cluster_jenny'] = df_jenny['cluster_jenny'].astype(int)

    # Descartar outliers (1 municipio) y combinaciones degeneradas
    tam = df_jenny['cluster_jenny'].value_counts()
    outliers = tam[tam == 1].index.tolist()
    df_jenny = df_jenny[~df_jenny['cluster_jenny'].isin(outliers)]
    n_clusters = df_jenny['cluster_jenny'].nunique()

    if n_clusters < 2:
        print(f"  {clave:<22} {'DEGENERADA':>8}")
        resultados.append({'combinacion': clave, 'estado': 'degenerada',
                           'n_clusters': n_clusters, 'accuracy_cv': None})
        continue

    df_jenny['target'] = 'C' + df_jenny['cluster_jenny'].astype(str)
    df_merge = df_vars.merge(df_jenny[['codigo_ine', 'target']], on='codigo_ine', how='inner')
    df_clean = df_merge.dropna(subset=FEATURES + ['target'])

    if len(df_clean) < 50:
        continue

    X = df_clean[FEATURES].values
    y = df_clean['target'].values

    # Información mutua
    mi = mutual_info_classif(X, y, discrete_features=discretas, random_state=42)
    top_var = NOMBRES_ES[FEATURES[np.argmax(mi)]]

    # Árbol de decisión con criterio entropía
    arbol = DecisionTreeClassifier(criterion='entropy', max_depth=5,
                                   min_samples_leaf=10, class_weight='balanced',
                                   random_state=42)
    try:
        cv = cross_val_score(arbol, X, y, cv=5, scoring='accuracy')
        accuracy = cv.mean()
    except Exception:
        accuracy = None

    partes = clave.split('_')
    alg = partes[0]
    met = partes[1]
    k   = int(partes[2])

    print(f"  {clave:<22} {n_clusters:>8} {len(df_clean):>10} {accuracy:>10.3f}  {top_var}")
    resultados.append({
        'combinacion':  clave,
        'algoritmo':    NOMBRES_ALG.get(alg, alg),
        'normalizacion': NOMBRES_MET.get(met, met),
        'k':            k,
        'n_clusters':   n_clusters,
        'municipios':   len(df_clean),
        'accuracy_cv':  accuracy,
        'top_variable': top_var,
        'estado':       'valida',
    })

# ── 4. Guardar ranking completo ────────────────────────────────────────────────

df_res = pd.DataFrame(resultados)
df_validas = df_res[df_res['estado'] == 'valida'].sort_values('accuracy_cv', ascending=False)

csv_path = os.path.join(RESULTADOS, 'tfm_jenny_ranking_completo.csv')
df_validas.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"\nRanking guardado: {csv_path}")

# ── 5. Gráfico ranking completo ────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(14, 10))
colores_alg = {'K-Means': '#2980b9', 'K-Medoids': '#c0392b'}
colores = [colores_alg.get(r['algoritmo'], '#888') for _, r in df_validas.iterrows()]
etiquetas = [f"{r['combinacion']}" for _, r in df_validas.iterrows()]

ax.barh(etiquetas[::-1], df_validas['accuracy_cv'].values[::-1],
        color=colores[::-1], edgecolor='white')
ax.set_xlabel('Accuracy (5-fold CV)')
ax.set_title('Ranking de todas las combinaciones de Jenny\n'
             'Que categorias se predicen mejor con las variables recogidas?')
ax.axvline(df_validas['accuracy_cv'].max(), color='gold', linestyle='--',
           linewidth=1.5, label=f"Mejor: {df_validas['accuracy_cv'].max():.3f}")
ax.grid(axis='x', alpha=0.3)

from matplotlib.patches import Patch
ax.legend(handles=[
    Patch(color='#2980b9', label='K-Means'),
    Patch(color='#c0392b', label='K-Medoids'),
    Patch(color='gold',    label=f"Mejor combinacion"),
], loc='lower right')

plt.tight_layout()
png_rank = os.path.join(IMAGENES, 'tfm_jenny_ranking_completo.png')
plt.savefig(png_rank, dpi=150, bbox_inches='tight')
plt.close()
print(f"Grafico guardado: {png_rank}")

# ── 6. Análisis detallado de las TOP 5 ────────────────────────────────────────

print("\nGenerando analisis detallado de las TOP 5...")
top5 = df_validas.head(5)

for pos, (_, fila) in enumerate(top5.iterrows(), 1):
    clave = fila['combinacion']
    print(f"\n  TOP {pos}: {clave} (accuracy={fila['accuracy_cv']:.3f})")

    m = re.search(r'"' + clave + r'"\s*:\s*\{([^}]*)\}', contenido)
    pares = re.findall(r'"(\d+)"\s*:\s*(-?\d+)', m.group(1))
    df_jenny = pd.DataFrame(pares, columns=['codigo_ine', 'cluster_jenny'])
    df_jenny['cluster_jenny'] = df_jenny['cluster_jenny'].astype(int)
    tam = df_jenny['cluster_jenny'].value_counts()
    df_jenny = df_jenny[~df_jenny['cluster_jenny'].isin(tam[tam == 1].index)]
    df_jenny['target'] = 'C' + df_jenny['cluster_jenny'].astype(str)

    df_merge = df_vars.merge(df_jenny[['codigo_ine', 'target']], on='codigo_ine', how='inner')
    df_clean = df_merge.dropna(subset=FEATURES + ['target'])
    X = df_clean[FEATURES].values
    y = df_clean['target'].values

    mi = mutual_info_classif(X, y, discrete_features=discretas, random_state=42)
    df_mi = pd.DataFrame({'variable': FEATURES,
                          'nombre_es': [NOMBRES_ES[f] for f in FEATURES],
                          'informacion_mutua': mi}).sort_values('informacion_mutua', ascending=False)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                          random_state=42, stratify=y)
    arbol = DecisionTreeClassifier(criterion='entropy', max_depth=5,
                                   min_samples_leaf=10, class_weight='balanced',
                                   random_state=42)
    arbol.fit(X_train, y_train)
    y_pred = arbol.predict(X_test)

    # Gráfico info mutua
    orden = df_mi.sort_values('informacion_mutua', ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(orden['nombre_es'], orden['informacion_mutua'], color='#2980b9', edgecolor='white')
    ax.set_xlabel('Ganancia de informacion (entropia)')
    ax.set_title(f'TOP {pos}: {clave} — Ganancia de informacion por variable')
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(TOP_DIR, f'top{pos}_{clave}_mutual_info.png'),
                dpi=150, bbox_inches='tight')
    plt.close()

    # Gráfico árbol
    clases = sorted(arbol.classes_)
    fig, ax = plt.subplots(figsize=(20, 9))
    plot_tree(arbol, feature_names=[NOMBRES_ES[f] for f in FEATURES],
              class_names=clases, max_depth=3, filled=True, rounded=True,
              fontsize=7, ax=ax, impurity=False, proportion=True)
    ax.set_title(f'TOP {pos}: {clave} — Arbol de Decision (entropia, primeros 3 niveles)')
    plt.tight_layout()
    plt.savefig(os.path.join(TOP_DIR, f'top{pos}_{clave}_arbol.png'),
                dpi=150, bbox_inches='tight')
    plt.close()

    print(f"    Graficos guardados en top5_jenny/")

# ── 7. Resumen final en pantalla ───────────────────────────────────────────────

print(f"\n{'='*60}")
print("  RANKING FINAL — MEJORES COMBINACIONES DE JENNY")
print(f"{'='*60}")
print(f"  {'Pos':<4} {'Combinacion':<22} {'Alg':<10} {'Norm':<12} {'K':>3} {'Accuracy':>10}  Top variable")
print("  " + "-"*80)
for pos, (_, r) in enumerate(df_validas.head(10).iterrows(), 1):
    print(f"  {pos:<4} {r['combinacion']:<22} {r['algoritmo']:<10} {r['normalizacion']:<12} "
          f"{int(r['k']):>3} {r['accuracy_cv']:>10.3f}  {r['top_variable']}")

mejor = df_validas.iloc[0]
print(f"\nMEJOR COMBINACION: {mejor['combinacion']}")
print(f"  Algoritmo:     {mejor['algoritmo']}")
print(f"  Normalizacion: {mejor['normalizacion']}")
print(f"  K:             {int(mejor['k'])}")
print(f"  Accuracy:      {mejor['accuracy_cv']:.3f}")
print(f"  Top variable:  {mejor['top_variable']}")
print("\nAnalisis completado.")
