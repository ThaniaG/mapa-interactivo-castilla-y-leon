"""
tfm_random_forest_jenny.py
══════════════════════════════════════════════════════════════════════
Random Forest sobre las categorias de Jenny (kmeans_mm_4: K-Means, Min-Max, K=4).

Complementa el analisis de entropia (arbol de decision unico) con un
ensemble de 200 arboles. Ventajas frente al arbol unico:
  - Mayor accuracy (promedia errores de muchos arboles)
  - Importancia de variables mas robusta (no depende de un solo camino)
  - Menos sobreajuste

Genera:
  tfm_rf_mutual_info.png          — ganancia de informacion por variable
  tfm_rf_importancia.png          — importancia segun Random Forest (Gini/MDI)
  tfm_rf_comparacion_arbol.png    — comparacion RF vs Arbol de decision
  tfm_rf_confusion.png            — matriz de confusion
  tfm_rf_importancia.csv          — tabla de importancias exportable
  tfm_rf_resultados.txt           — resumen numerico del experimento
"""

import os, re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import (classification_report, confusion_matrix,
                             ConfusionMatrixDisplay, accuracy_score)
import warnings
warnings.filterwarnings('ignore')

# ── Rutas ─────────────────────────────────────────────────────────────────────
SCRIPTS    = os.path.dirname(os.path.abspath(__file__))
TFM        = os.path.dirname(SCRIPTS)
RAIZ       = os.path.dirname(TFM)        # carpeta PRACTICAS (donde esta datos_jenny.js)
IMAGENES   = os.path.join(TFM, 'imagenes')
RESULTADOS = os.path.join(TFM, 'resultados')
os.makedirs(IMAGENES, exist_ok=True)
os.makedirs(RESULTADOS, exist_ok=True)

# ── Configuracion ──────────────────────────────────────────────────────────────
CLAVE_JENNY = 'kmeans_mm_4'    # combinacion pedida por el docente
N_ARBOLES   = 200              # cuantos arboles forma el bosque
MAX_PROF    = 10               # profundidad maxima de cada arbol del bosque

plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9,
                     'axes.titlesize': 11, 'figure.dpi': 150})

# ── Variables de entrada (26 variables recopiladas) ────────────────────────────
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
    'balance_vital_1000': 'Balance vital /1000 hab', 'renta_media': 'Renta media (EUR/hab)',
    'subv_per_capita': 'Subvenciones per capita (EUR)', 'bares_1000': 'Bares / 1.000 hab',
    'restaurantes_1000': 'Restaurantes / 1.000 hab', 'alojamiento_1000': 'Alojamientos / 1.000 hab',
    'estab_total_1000': 'Total estab. / 1.000 hab', 'tiene_cs': 'Tiene centro de salud',
    'tiene_hospital': 'Tiene hospital', 'dist_cs_km': 'Distancia a C. Salud (km)',
    'dist_hospital_km': 'Distancia a hospital (km)', 'tiene_colegio': 'Tiene colegio',
    'tiene_instituto': 'Tiene instituto', 'dist_colegio_km': 'Distancia a colegio (km)',
    'dist_instituto_km': 'Distancia a instituto (km)', 'tiene_residencia': 'Tiene residencia mayores',
    'plazas_residencia_1000': 'Plazas residencia /1000 hab',
    'dist_residencia_km': 'Distancia a residencia (km)',
    'dist_capital_km': 'Distancia a capital (km)', 'superficie_km2': 'Superficie (km2)',
}

# Variables binarias (tienen_xxx): el calculo de info mutua trata estas diferente
DISCRETAS = [f in ('tiene_cs','tiene_hospital','tiene_colegio',
                   'tiene_instituto','tiene_residencia') for f in FEATURES]

# ── 1. Cargar categorias de Jenny ──────────────────────────────────────────────
print(f"Cargando categorias Jenny: {CLAVE_JENNY}...")
ruta_jenny = os.path.join(RAIZ, 'datos_jenny.js')
with open(ruta_jenny, encoding='utf-8') as f:
    contenido = f.read()

# datos_jenny.js no es JSON valido (comas finales), extraemos con regex
m = re.search(r'"' + CLAVE_JENNY + r'"\s*:\s*\{([^}]*)\}', contenido)
if not m:
    raise ValueError(f"No se encontro la clave '{CLAVE_JENNY}' en datos_jenny.js")
pares = re.findall(r'"(\d+)"\s*:\s*(-?\d+)', m.group(1))
df_jenny = pd.DataFrame(pares, columns=['codigo_ine', 'cluster_jenny'])
df_jenny['cluster_jenny'] = df_jenny['cluster_jenny'].astype(int)
print(f"  Municipios con datos Jenny: {len(df_jenny)}")

# Detectar y excluir clusters singleton (1 solo municipio = outlier)
tam_cluster = df_jenny['cluster_jenny'].value_counts()
singletons  = tam_cluster[tam_cluster == 1].index.tolist()
if singletons:
    nombres_sin = df_jenny[df_jenny['cluster_jenny'].isin(singletons)]['codigo_ine'].tolist()
    print(f"  Excluyendo cluster singleton (codigo INE: {nombres_sin})")
    df_jenny = df_jenny[~df_jenny['cluster_jenny'].isin(singletons)]

# Convertir numero de cluster a etiqueta C0, C2, C3 ...
df_jenny['target'] = 'C' + df_jenny['cluster_jenny'].astype(str)
clases_jenny = sorted(df_jenny['target'].unique())
print(f"  Categorias Jenny usadas: {clases_jenny}")
print(f"  Municipios por categoria: {df_jenny['target'].value_counts().to_dict()}")

# ── 2. Cargar variables recopiladas ───────────────────────────────────────────
print("\nCargando dataset_tfm.csv...")
ruta_csv = os.path.join(RESULTADOS, 'dataset_tfm.csv')
df_vars = pd.read_csv(ruta_csv, encoding='utf-8-sig')
df_vars.columns = df_vars.columns.str.strip()
df_vars['codigo_ine'] = df_vars['codigo_ine'].astype(str).str.zfill(5)

# Establecimientos: rellenar con 0 si el municipio no tiene ninguno registrado
for col in ['bares_1000', 'restaurantes_1000', 'alojamiento_1000', 'estab_total_1000']:
    df_vars[col] = df_vars[col].fillna(0)

# ── 3. Cruzar variables con categorias Jenny ──────────────────────────────────
df_merge = df_vars.merge(df_jenny[['codigo_ine', 'target']], on='codigo_ine', how='inner')
df_clean  = df_merge.dropna(subset=FEATURES + ['target'])
print(f"  Municipios tras el cruce y limpieza: {len(df_clean)}")

X = df_clean[FEATURES].values
y = df_clean['target'].values

# ── 4. Informacion mutua (ganancia de informacion por variable) ───────────────
print("\nCalculando informacion mutua...")
mi = mutual_info_classif(X, y, discrete_features=DISCRETAS, random_state=42)
df_mi = pd.DataFrame({
    'variable':          FEATURES,
    'nombre_es':         [NOMBRES_ES[f] for f in FEATURES],
    'informacion_mutua': mi,
}).sort_values('informacion_mutua', ascending=False)

# ── 5. Random Forest con validacion cruzada 5-fold ────────────────────────────
print(f"\nEntrenando Random Forest ({N_ARBOLES} arboles, max_depth={MAX_PROF})...")
rf = RandomForestClassifier(
    n_estimators  = N_ARBOLES,
    max_depth     = MAX_PROF,
    class_weight  = 'balanced',   # compensa si hay mas municipios en una categoria
    random_state  = 42,
    n_jobs        = -1,           # usa todos los nucleos disponibles
)

# Validacion cruzada: 5 rondas, cada una usa 20% como test
cv_scores_rf = cross_val_score(rf, X, y, cv=5, scoring='accuracy')
acc_rf_cv    = cv_scores_rf.mean()
print(f"  Accuracy Random Forest (5-fold CV): {acc_rf_cv:.3f} ± {cv_scores_rf.std():.3f}")

# Comparar con arbol de decision unico (mismo criterio que tfm_entropia.py)
arbol = DecisionTreeClassifier(
    criterion        = 'entropy',
    max_depth        = 5,
    min_samples_leaf = 10,
    class_weight     = 'balanced',
    random_state     = 42,
)
cv_scores_arbol = cross_val_score(arbol, X, y, cv=5, scoring='accuracy')
acc_arbol_cv    = cv_scores_arbol.mean()
print(f"  Accuracy Arbol de decision (5-fold CV): {acc_arbol_cv:.3f} ± {cv_scores_arbol.std():.3f}")

# ── 6. Entrenar RF sobre todo el conjunto para extraer importancias ────────────
# Nota: la importancia se extrae del modelo completo, el accuracy ya se evaluo con CV
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)
acc_test = accuracy_score(y_test, y_pred)
print(f"  Accuracy en conjunto de test 20%: {acc_test:.3f}")

# Importancia segun RF: promedio de reduccion de impureza en todos los arboles
importancias = rf.feature_importances_
df_imp = pd.DataFrame({
    'variable':              FEATURES,
    'nombre_es':             [NOMBRES_ES[f] for f in FEATURES],
    'informacion_mutua':     mi,
    'importancia_rf':        importancias,
}).sort_values('importancia_rf', ascending=False)

# ── 7. Exportar CSV de importancias ───────────────────────────────────────────
csv_path = os.path.join(RESULTADOS, 'tfm_rf_importancia.csv')
df_imp.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"\nCSV exportado: {csv_path}")

# ── 8. Grafico 1: Informacion mutua ──────────────────────────────────────────
orden_mi = df_mi.sort_values('informacion_mutua', ascending=True)
fig, ax = plt.subplots(figsize=(10, 8))
colores = ['#2980b9' if v > 0.05 else '#bdc3c7' for v in orden_mi['informacion_mutua']]
ax.barh(orden_mi['nombre_es'], orden_mi['informacion_mutua'],
        color=colores, edgecolor='white')
ax.set_xlabel('Ganancia de informacion (entropia)')
ax.set_title(f'Random Forest — {CLAVE_JENNY}\nGanancia de informacion por variable')
ax.axvline(0.05, color='red', linestyle='--', linewidth=1,
           label='Umbral relevante (0.05)')
ax.legend()
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
png1 = os.path.join(IMAGENES, 'tfm_rf_mutual_info.png')
plt.savefig(png1, dpi=150, bbox_inches='tight')
plt.close()
print(f"Grafico guardado: {png1}")

# ── 9. Grafico 2: Importancia Random Forest ───────────────────────────────────
orden_rf = df_imp.sort_values('importancia_rf', ascending=True)
fig, ax = plt.subplots(figsize=(10, 8))
colores = ['#27ae60' if v > 0.03 else '#bdc3c7' for v in orden_rf['importancia_rf']]
ax.barh(orden_rf['nombre_es'], orden_rf['importancia_rf'],
        color=colores, edgecolor='white')
ax.set_xlabel('Importancia (reduccion media de impureza, MDI)')
ax.set_title(f'Random Forest ({N_ARBOLES} arboles) — {CLAVE_JENNY}\nImportancia de variables')
ax.axvline(0.03, color='red', linestyle='--', linewidth=1,
           label='Umbral relevante (0.03)')
ax.legend()
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
png2 = os.path.join(IMAGENES, 'tfm_rf_importancia.png')
plt.savefig(png2, dpi=150, bbox_inches='tight')
plt.close()
print(f"Grafico guardado: {png2}")

# ── 10. Grafico 3: Comparacion RF vs Arbol de decision ───────────────────────
# Muestra las top-10 variables segun RF, comparando su importancia en ambos modelos

arbol_completo = DecisionTreeClassifier(
    criterion='entropy', max_depth=5, min_samples_leaf=10,
    class_weight='balanced', random_state=42)
arbol_completo.fit(X_train, y_train)
imp_arbol = arbol_completo.feature_importances_

top10_idx  = np.argsort(importancias)[::-1][:10]
nombres_top = [NOMBRES_ES[FEATURES[i]] for i in top10_idx]
vals_rf    = importancias[top10_idx]
vals_arbol = imp_arbol[top10_idx]

x      = np.arange(len(nombres_top))
ancho  = 0.35
fig, ax = plt.subplots(figsize=(13, 6))
ax.bar(x - ancho/2, vals_rf,    ancho, label=f'Random Forest ({N_ARBOLES} arboles)',
       color='#27ae60', edgecolor='white')
ax.bar(x + ancho/2, vals_arbol, ancho, label='Arbol de decision unico (entropia)',
       color='#2980b9', edgecolor='white', alpha=0.8)
ax.set_xticks(x)
ax.set_xticklabels(nombres_top, rotation=35, ha='right', fontsize=8)
ax.set_ylabel('Importancia (MDI)')
ax.set_title(f'{CLAVE_JENNY} — Comparacion: Random Forest vs Arbol de decision\nTop 10 variables mas importantes segun Random Forest')
ax.legend()
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
png3 = os.path.join(IMAGENES, 'tfm_rf_comparacion_arbol.png')
plt.savefig(png3, dpi=150, bbox_inches='tight')
plt.close()
print(f"Grafico guardado: {png3}")

# ── 11. Grafico 4: Matriz de confusion ───────────────────────────────────────
orden_cm = ['C0', 'C3', 'C2']
cm       = confusion_matrix(y_test, y_pred, labels=orden_cm)
fig, ax = plt.subplots(figsize=(6, 5))
disp_cm = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=orden_cm)
disp_cm.plot(ax=ax, colorbar=False, cmap='Blues')
ax.set_title(f'Random Forest — {CLAVE_JENNY}\nMatriz de confusion (conjunto test 20%)')
plt.tight_layout()
png4 = os.path.join(IMAGENES, 'tfm_rf_confusion.png')
plt.savefig(png4, dpi=150, bbox_inches='tight')
plt.close()
print(f"Grafico guardado: {png4}")

# ── 12. Resumen en TXT ────────────────────────────────────────────────────────
txt_path = os.path.join(RESULTADOS, 'tfm_rf_resultados.txt')
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write(f"RANDOM FOREST — {CLAVE_JENNY}\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"Configuracion:\n")
    f.write(f"  Arboles:          {N_ARBOLES}\n")
    f.write(f"  Profundidad max:  {MAX_PROF}\n")
    f.write(f"  Variables entrada: {len(FEATURES)}\n")
    f.write(f"  Municipios usados: {len(df_clean)}\n")
    f.write(f"  Categorias Jenny:  {clases_jenny}\n\n")
    f.write(f"Resultados:\n")
    f.write(f"  Accuracy RF (5-fold CV):     {acc_rf_cv:.4f} ({acc_rf_cv*100:.1f}%)\n")
    f.write(f"  Accuracy Arbol (5-fold CV):  {acc_arbol_cv:.4f} ({acc_arbol_cv*100:.1f}%)\n")
    f.write(f"  Accuracy RF (test 20%):      {acc_test:.4f} ({acc_test*100:.1f}%)\n\n")
    f.write(f"Ranking de variables (por importancia Random Forest):\n")
    f.write(f"  {'#':<4} {'Variable':<35} {'Import. RF':>12}  {'Info. mutua':>12}\n")
    f.write("  " + "-"*67 + "\n")
    for i, (_, row) in enumerate(df_imp.iterrows(), 1):
        f.write(f"  {i:<4} {row['nombre_es']:<35} {row['importancia_rf']:>12.4f}  {row['informacion_mutua']:>12.4f}\n")
    f.write("\n")
    f.write("Informe por categoria:\n")
    f.write(classification_report(y_test, y_pred))
print(f"Resumen guardado: {txt_path}")

# ── 13. Resumen en pantalla ───────────────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  RANDOM FOREST — {CLAVE_JENNY}")
print(f"{'='*60}")
print(f"  Accuracy RF (5-fold CV):    {acc_rf_cv*100:.1f}%  ±{cv_scores_rf.std()*100:.1f}%")
print(f"  Accuracy Arbol (5-fold CV): {acc_arbol_cv*100:.1f}%  ±{cv_scores_arbol.std()*100:.1f}%")
mejora = (acc_rf_cv - acc_arbol_cv) * 100
print(f"  Mejora RF sobre arbol:      +{mejora:.1f} puntos porcentuales")
print(f"\n  Top 10 variables (Random Forest):")
print(f"  {'#':<4} {'Variable':<35} {'Import. RF':>10}")
print("  " + "-"*52)
for i, (_, row) in enumerate(df_imp.head(10).iterrows(), 1):
    print(f"  {i:<4} {row['nombre_es']:<35} {row['importancia_rf']:>10.4f}")
print("\nAnalisis completado.")
