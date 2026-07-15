"""
tfm_entropia.py
══════════════════════════════════════════════════════════════════════
Análisis de entropía / ganancia de información — Castilla y León.

Objetivo (indicado por el docente):
  El TFM no se centra en "despoblación" sino en la TENDENCIA poblacional,
  representada por las categorías que generó Jenny con K-Means.

  Experimento de predicción:
    INPUT  -> variables ya recogidas (renta, edad, servicios, subvenciones,
              establecimientos, sanidad, educación, residencias, distancias...)
    OUTPUT -> categoría de clúster K-Means · Min-Max · K=4  (kmeans_mm_4)

  Pregunta: ¿qué variables son más informativas para predecir en qué
  categoría de tendencia cae un municipio? Se mide con:
    1) Ganancia de información / Información mutua (entropía) variable a variable
    2) Árbol de decisión con criterio='entropy' -> ranking de importancia

Nota metodológica:
  Se EXCLUYEN del input las variables que describen directamente la
  evolución/tendencia de población (tasa_cambio_pob, tendencia_anual,
  perdida_5a/10a/25a, clase_despoblacion), porque son la base con la que
  Jenny construyó los clústeres K-Means: usarlas como input sería
  circular (fuga de información). Las variables de entrada son las
  "externas" -> renta, servicios, demografía estructural, etc.

  El clúster 1 de kmeans_mm_4 tiene un único municipio (caso atípico:
  San Cristóbal de Segovia, 40906) en casi todas las combinaciones de
  Jenny. Se excluye del experimento porque con 1 solo caso no se puede
  entrenar ni validar nada para esa clase.

Salida:
  tfm_entropia_importancia.csv   (ranking: info. mutua + entropía del árbol)
  tfm_entropia_mutual_info.png
  tfm_entropia_importancia.png
  tfm_entropia_arbol.png
  tfm_entropia_confusion.png
  tfm_entropia_resultados.txt
"""

# Librerías necesarias:
# - os, re       -> manejar rutas de archivos y leer el archivo de Jenny (no es JSON puro)
# - pandas       -> manejar tablas de datos (municipios x variables)
# - numpy        -> operaciones numéricas auxiliares
# - matplotlib   -> generar los gráficos PNG
# - sklearn      -> árbol de decisión, información mutua y métricas de evaluación
import os
import re
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import warnings
warnings.filterwarnings('ignore')

# Rutas de carpetas: se calculan automáticamente desde la ubicación del script,
# así funciona sin importar desde dónde lo ejecutes.
# RAIZ = carpeta PRACTICAS (donde están datos_jenny.js y los datos del dashboard)
# IMAGENES y RESULTADOS = subcarpetas de tfm/ donde se guardan los archivos generados
SCRIPTS   = os.path.dirname(os.path.abspath(__file__))
TFM       = os.path.dirname(SCRIPTS)
RAIZ      = os.path.dirname(TFM)
IMAGENES  = os.path.join(TFM, 'imagenes')
RESULTADOS = os.path.join(TFM, 'resultados')

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'figure.dpi': 150,
})

CLAVE_JENNY = 'kmeans_mm_4'   # K-Means · Min-Max · K=4 (categoría de entrada que pidió el docente)

# ── 1. Cargar variable objetivo: categorías de Jenny (kmeans_mm_4) ────────────
# datos_jenny.js contiene las categorías que generó Jenny con K-Means para cada municipio.
# La clave 'kmeans_mm_4' = K-Means · normalización Min-Max · K=4 grupos.
# El archivo tiene comas finales y no se puede leer como JSON estándar,
# por eso se usa una expresión regular (re.search / re.findall) para extraer los datos.

print(f"Cargando categorias de Jenny ({CLAVE_JENNY}) desde datos_jenny.js...")
with open(os.path.join(RAIZ, 'datos_jenny.js'), encoding='utf-8') as f:
    contenido = f.read()

# datos_jenny.js no es JSON estricto (tiene comas finales) -> extraccion por regex
m = re.search(r'"' + CLAVE_JENNY + r'"\s*:\s*\{([^}]*)\}', contenido)
if not m:
    raise SystemExit(f"No se encontro la clave {CLAVE_JENNY} en datos_jenny.js")

pares = re.findall(r'"(\d+)"\s*:\s*(-?\d+)', m.group(1))
df_jenny = pd.DataFrame(pares, columns=['codigo_ine', 'cluster_jenny'])
df_jenny['cluster_jenny'] = df_jenny['cluster_jenny'].astype(int)
print(f"  Municipios con categoria Jenny: {len(df_jenny)}")
print("  Distribucion de clusters:")
for cl, n in df_jenny['cluster_jenny'].value_counts().sort_index().items():
    print(f"    C{cl}: {n} municipios")

# El C1 tiene solo 1 municipio (San Cristóbal de Segovia, caso atípico).
# Con 1 solo caso no se puede entrenar ni validar un modelo, así que se descarta.
tam = df_jenny['cluster_jenny'].value_counts()
outliers = tam[tam == 1].index.tolist()
if outliers:
    print(f"\n  Excluyendo cluster(es) atipico(s) con 1 solo municipio: {outliers}")
    df_jenny = df_jenny[~df_jenny['cluster_jenny'].isin(outliers)]

df_jenny['target'] = 'C' + df_jenny['cluster_jenny'].astype(str)

# ── 2. Cargar variables predictoras ────────────────────────────────────────────
# dataset_tfm.csv contiene las 26 variables recogidas para cada municipio:
# datos demográficos (edad, natalidad, mortalidad), económicos (renta, subvenciones),
# de servicios (sanidad, educación, residencias) y geográficos (densidad, distancias).
# Estas son las variables de ENTRADA (input) del experimento de predicción.

print("\nCargando dataset_tfm.csv...")
df = pd.read_csv(os.path.join(RESULTADOS, 'dataset_tfm.csv'), encoding='utf-8-sig')
df.columns = df.columns.str.strip()
df['codigo_ine'] = df['codigo_ine'].astype(str).str.zfill(5)

FEATURES = [
    'densidad_pob',
    'porc_65',
    'ind_envej',
    'porc_extranjeros',
    'tasa_natalidad',
    'tasa_mortalidad',
    'balance_vital_1000',
    'renta_media',
    'subv_per_capita',
    'bares_1000',
    'restaurantes_1000',
    'alojamiento_1000',
    'estab_total_1000',
    'tiene_cs',
    'tiene_hospital',
    'dist_cs_km',
    'dist_hospital_km',
    'tiene_colegio',
    'tiene_instituto',
    'dist_colegio_km',
    'dist_instituto_km',
    'tiene_residencia',
    'plazas_residencia_1000',
    'dist_residencia_km',
    'dist_capital_km',
    'superficie_km2',
]

NOMBRES_ES = {
    'densidad_pob':          'Densidad (hab/km2)',
    'porc_65':               '% Mayores de 65',
    'ind_envej':              'Indice envejecimiento',
    'porc_extranjeros':      '% Poblacion extranjera',
    'tasa_natalidad':        'Tasa natalidad',
    'tasa_mortalidad':       'Tasa mortalidad',
    'balance_vital_1000':    'Balance vital /1000 hab',
    'renta_media':           'Renta media (EUR/hab)',
    'subv_per_capita':       'Subvenciones per capita (EUR)',
    'bares_1000':            'Bares / 1.000 hab',
    'restaurantes_1000':     'Restaurantes / 1.000 hab',
    'alojamiento_1000':      'Alojamientos / 1.000 hab',
    'estab_total_1000':      'Total estab. / 1.000 hab',
    'tiene_cs':               'Tiene centro de salud',
    'tiene_hospital':         'Tiene hospital',
    'dist_cs_km':             'Distancia a C. Salud (km)',
    'dist_hospital_km':       'Distancia a hospital (km)',
    'tiene_colegio':          'Tiene colegio',
    'tiene_instituto':        'Tiene instituto',
    'dist_colegio_km':        'Distancia a colegio (km)',
    'dist_instituto_km':      'Distancia a instituto (km)',
    'tiene_residencia':       'Tiene residencia mayores',
    'plazas_residencia_1000': 'Plazas residencia /1000 hab',
    'dist_residencia_km':     'Distancia a residencia (km)',
    'dist_capital_km':        'Distancia a capital (km)',
    'superficie_km2':         'Superficie (km2)',
}

# Los municipios sin dato en establecimientos no tienen bares/restaurantes registrados,
# no es un dato perdido, es que realmente no tienen -> se rellena con 0.
COLS_ESTAB = ['bares_1000', 'restaurantes_1000', 'alojamiento_1000', 'estab_total_1000']
df[COLS_ESTAB] = df[COLS_ESTAB].fillna(0)

# ── 3. Unir variables + categoria Jenny ────────────────────────────────────────
# Se cruzan las dos tablas por el código INE del municipio.
# Resultado: una fila por municipio con sus 26 variables + su categoría de Jenny.
# Los municipios con algún dato faltante se descartan (dropna).

df_merge = df.merge(df_jenny[['codigo_ine', 'target']], on='codigo_ine', how='inner')
df_clean = df_merge.dropna(subset=FEATURES + ['target'])
print(f"\n  Municipios con categoria Jenny + variables completas: {len(df_clean)} (de {len(df_merge)})")

print("\n  Distribucion de la variable objetivo (categoria Jenny, tras limpieza):")
for clase, n in df_clean['target'].value_counts().sort_index().items():
    pct = 100 * n / len(df_clean)
    print(f"    {clase:6}: {n:4} ({pct:.1f}%)")

X = df_clean[FEATURES].values
y = df_clean['target'].values

# ── 4. Informacion mutua (ganancia de informacion / entropia variable a variable) ──
# Para cada variable por separado, se mide cuánto reduce la incertidumbre
# sobre la categoría de Jenny. Esto es la "ganancia de información" o entropía.
# Valor alto = la variable es muy informativa para predecir el grupo.
# Valor cercano a 0 = la variable no aporta casi nada.
# Las variables binarias (tiene_cs, tiene_hospital...) se marcan como discretas
# para que el cálculo sea más preciso.

print("\nCalculando informacion mutua (ganancia de informacion) por variable...")
discretas = [f in ('tiene_cs', 'tiene_hospital', 'tiene_colegio', 'tiene_instituto', 'tiene_residencia')
             for f in FEATURES]
mi = mutual_info_classif(X, y, discrete_features=discretas, random_state=42)

df_mi = pd.DataFrame({
    'variable': FEATURES,
    'nombre_es': [NOMBRES_ES[f] for f in FEATURES],
    'informacion_mutua': mi,
}).sort_values('informacion_mutua', ascending=False)

print("\n  Ranking por informacion mutua (entropia):")
for _, row in df_mi.iterrows():
    bar = '#' * int(row['informacion_mutua'] * 200)
    print(f"    {row['informacion_mutua']:.4f}  {bar}  {row['nombre_es']}")

# ── 5. Arbol de decision con criterio de entropia ──────────────────────────────
# Se divide el dataset: 80% para entrenar el árbol y 20% para probarlo (test_size=0.2).
# criterion='entropy' -> el árbol elige en cada nodo la variable que más reduce
#   la entropía (incertidumbre). Esto es exactamente lo que pidió el docente.
# max_depth=5         -> el árbol no crece más de 5 niveles (evita sobreajuste).
# min_samples_leaf=10 -> cada hoja necesita al menos 10 municipios.
# class_weight='balanced' -> compensa que C0 tiene muchos más municipios que C2.
# La validación cruzada (5-fold CV) divide el dataset en 5 partes, entrena y prueba
# el modelo 5 veces, dando una medida más fiable de la precisión real.

print("\nEntrenando arbol de decision (criterio=entropy)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

arbol = DecisionTreeClassifier(
    criterion='entropy',
    max_depth=5,
    min_samples_leaf=10,
    class_weight='balanced',
    random_state=42
)
arbol.fit(X_train, y_train)

y_pred = arbol.predict(X_test)
cv_scores = cross_val_score(arbol, X, y, cv=5, scoring='accuracy')

print("\n  Informe de clasificacion:")
print(classification_report(y_test, y_pred, zero_division=0))
print(f"  Accuracy (5-fold CV): {cv_scores.mean():.3f} +/- {cv_scores.std():.3f}")

# ── 6. Ranking combinado (informacion mutua + ganancia de informacion del arbol) ──
# Une los dos rankings en una sola tabla:
#   - informacion_mutua: calculada variable a variable (paso 4), independiente del árbol
#   - ganancia_info_arbol: importancia según el árbol entrenado (paso 5)
# Tener los dos permite comparar: si una variable es importante en ambos rankings,
# la conclusión es más sólida. Se guarda en CSV para usarlo en la memoria del TFM.

df_arbol = pd.DataFrame({
    'variable': FEATURES,
    'ganancia_info_arbol': arbol.feature_importances_,
})

ranking = df_mi.merge(df_arbol, on='variable').sort_values('ganancia_info_arbol', ascending=False)
ranking['rank_info_mutua'] = ranking['informacion_mutua'].rank(ascending=False).astype(int)
ranking['rank_arbol'] = ranking['ganancia_info_arbol'].rank(ascending=False).astype(int)

csv_path = os.path.join(RESULTADOS, 'tfm_entropia_importancia.csv')
ranking.to_csv(csv_path, index=False, encoding='utf-8-sig')
print(f"\nGuardado: {csv_path}")

# ── 7. Grafico: informacion mutua ──────────────────────────────────────────────
# Gráfico de barras horizontales (azul) con el ranking de información mutua.
# Las barras más largas = variables más informativas para predecir la categoría.
# Se guarda en tfm_entropia_mutual_info.png para incluir en la memoria del TFM.

orden_mi = df_mi.sort_values('informacion_mutua', ascending=True)
fig, ax = plt.subplots(figsize=(10, 8))
ax.barh(orden_mi['nombre_es'], orden_mi['informacion_mutua'], color='#2980b9', edgecolor='white')
ax.set_xlabel('Informacion mutua (entropia)', fontsize=11)
ax.set_title('Ganancia de informacion por variable\nPrediccion de la categoria K-Means (Min-Max, K=4) de Jenny',
             fontsize=12, fontweight='bold')
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
png_mi = os.path.join(IMAGENES, 'tfm_entropia_mutual_info.png')
plt.savefig(png_mi, dpi=150, bbox_inches='tight')
plt.close()
print(f"Guardado: {png_mi}")

# ── 8. Grafico: importancia del arbol (entropia) ───────────────────────────────
# Gráfico de barras horizontales (rojo) con el ranking del árbol de decisión.
# A diferencia del paso 7, aquí la importancia refleja cómo el árbol completo
# usa cada variable en todas sus ramas, no solo variable a variable.
# Se guarda en tfm_entropia_importancia.png.

orden_arbol = ranking.sort_values('ganancia_info_arbol', ascending=True)
fig, ax = plt.subplots(figsize=(10, 8))
ax.barh(orden_arbol['nombre_es'], orden_arbol['ganancia_info_arbol'], color='#c0392b', edgecolor='white')
ax.set_xlabel('Importancia (ganancia de informacion, criterio entropy)', fontsize=11)
ax.set_title('Variables mas influyentes en la categoria de tendencia (K-Means)\nArbol de Decision - criterio entropia',
             fontsize=12, fontweight='bold')
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
png_imp = os.path.join(IMAGENES, 'tfm_entropia_importancia.png')
plt.savefig(png_imp, dpi=150, bbox_inches='tight')
plt.close()
print(f"Guardado: {png_imp}")

# ── 9. Grafico: arbol (primeros 3 niveles) ─────────────────────────────────────
# Dibuja el árbol de decisión visualmente: cada nodo muestra qué variable usa
# y el umbral de corte (ej: "balance vital < -3.2").
# Solo se muestran los primeros 3 niveles para que sea legible (el árbol completo
# tiene hasta 5 niveles y sería demasiado grande).
# filled=True -> los nodos se colorean según la clase mayoritaria (C0, C2 o C3).
# Se guarda en tfm_entropia_arbol.png.

clases_ordenadas = sorted(arbol.classes_)
fig, ax = plt.subplots(figsize=(20, 9))
plot_tree(
    arbol,
    feature_names=[NOMBRES_ES[f] for f in FEATURES],
    class_names=clases_ordenadas,
    max_depth=3,
    filled=True,
    rounded=True,
    fontsize=7,
    ax=ax,
    impurity=False,
    proportion=True,
)
ax.set_title('Arbol de Decision (entropia) - Categoria de tendencia K-Means (primeros 3 niveles)',
             fontsize=13, fontweight='bold', pad=15)
plt.tight_layout()
png_arbol = os.path.join(IMAGENES, 'tfm_entropia_arbol.png')
plt.savefig(png_arbol, dpi=150, bbox_inches='tight')
plt.close()
print(f"Guardado: {png_arbol}")

# ── 10. Grafico: matriz de confusion ───────────────────────────────────────────
# Muestra cuántos municipios clasificó bien y cuántos mal el árbol.
# Filas = categoría real (la de Jenny), columnas = categoría predicha por el árbol.
# Los números en la diagonal = aciertos. Fuera de la diagonal = errores.
# Por ejemplo: 10 municipios que eran C2 pero el árbol predijo C0.
# Se guarda en tfm_entropia_confusion.png.

orden_cm = ['C0', 'C3', 'C2']
cm = confusion_matrix(y_test, y_pred, labels=orden_cm)
fig, ax = plt.subplots(figsize=(7, 6))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=orden_cm)
disp.plot(ax=ax, colorbar=True, cmap='Reds')
ax.set_title('Matriz de Confusion - Arbol de Decision (entropia)\nCategoria de tendencia K-Means · Min-Max · K=4',
             fontsize=11, fontweight='bold')
plt.tight_layout()
png_cm = os.path.join(IMAGENES, 'tfm_entropia_confusion.png')
plt.savefig(png_cm, dpi=150, bbox_inches='tight')
plt.close()
print(f"Guardado: {png_cm}")

# ── 11. Guardar resumen ─────────────────────────────────────────────────────────
# Escribe un archivo de texto con todo el análisis: rankings, precisión del modelo,
# informe de clasificación por categoría y las reglas del árbol en texto plano.
# Este archivo es útil para copiar los datos directamente en la memoria del TFM.

txt_path = os.path.join(RESULTADOS, 'tfm_entropia_resultados.txt')
with open(txt_path, 'w', encoding='utf-8') as f:
    f.write('ANALISIS DE ENTROPIA / GANANCIA DE INFORMACION\n')
    f.write('Prediccion de la categoria de tendencia K-Means (Min-Max, K=4) de Jenny\n')
    f.write('=' * 70 + '\n\n')
    f.write(f'Municipios analizados: {len(df_clean)}\n')
    f.write(f'Cluster(s) atipico(s) excluido(s) (1 solo municipio): {outliers}\n\n')

    f.write('VARIABLE OBJETIVO (output): categoria de cluster K-Means Min-Max K=4\n')
    f.write('-' * 60 + '\n')
    for clase, n in df_clean['target'].value_counts().sort_index().items():
        pct = 100 * n / len(df_clean)
        f.write(f'  {clase:6}: {n:4} ({pct:.1f}%)\n')

    f.write('\nVARIABLES PREDICTORAS (input): %d variables externas a la tendencia\n' % len(FEATURES))
    f.write('-' * 60 + '\n')
    f.write('(se excluyen tasa_cambio_pob, tendencia_anual, perdida_5/10/25a y\n')
    f.write(' clase_despoblacion por ser la base con la que se construyo el cluster)\n\n')

    f.write('RANKING POR INFORMACION MUTUA (entropia, independiente del arbol):\n')
    f.write('-' * 60 + '\n')
    for _, row in df_mi.iterrows():
        f.write(f'  {row["informacion_mutua"]:.4f}  {row["nombre_es"]}\n')

    f.write('\nRANKING POR GANANCIA DE INFORMACION DEL ARBOL (criterio entropy):\n')
    f.write('-' * 60 + '\n')
    for _, row in ranking.sort_values('ganancia_info_arbol', ascending=False).iterrows():
        f.write(f'  {row["ganancia_info_arbol"]:.4f}  {row["nombre_es"]}\n')

    f.write(f'\nPRECISION DEL MODELO:\n')
    f.write('-' * 60 + '\n')
    f.write(f'  Validacion cruzada (5-fold): {cv_scores.mean():.3f} +/- {cv_scores.std():.3f}\n\n')

    f.write('INFORME DE CLASIFICACION (test 20%):\n')
    f.write('-' * 60 + '\n')
    f.write(classification_report(y_test, y_pred, zero_division=0))

    f.write('\nREGLAS DEL ARBOL (primeros 3 niveles):\n')
    f.write('-' * 60 + '\n')
    f.write(export_text(arbol, feature_names=FEATURES, max_depth=3))

print(f"\nResultados guardados: {txt_path}")
print('\nAnalisis completado!')
print('Archivos generados:')
for archivo in ['tfm_entropia_importancia.csv', 'tfm_entropia_mutual_info.png',
                'tfm_entropia_importancia.png', 'tfm_entropia_arbol.png',
                'tfm_entropia_confusion.png', 'tfm_entropia_resultados.txt']:
    print(f'  - {archivo}')
