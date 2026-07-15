"""
tfm_analisis_categorias.py
══════════════════════════════════════════════════════════════════════
Análisis flexible de entropía / ganancia de información.

Permite analizar CUALQUIER combinación de categorías de Jenny
cambiando los parámetros de la sección de configuración.

Modos de uso:
  1) Analizar una sola combinación específica (ej: kmeans_mm_4)
  2) Comparar automáticamente varias combinaciones y ver cuál
     produce categorías mejor explicadas por las variables

El docente pidió específicamente: K-Means · Min-Max · K=4
pero este script permite explorar otras combinaciones para
enriquecer el análisis del TFM.
"""

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

# ── Rutas de carpetas ──────────────────────────────────────────────────────────
SCRIPTS    = os.path.dirname(os.path.abspath(__file__))
TFM        = os.path.dirname(SCRIPTS)
RAIZ       = os.path.dirname(TFM)
IMAGENES   = os.path.join(TFM, 'imagenes')
RESULTADOS = os.path.join(TFM, 'resultados')

# ══════════════════════════════════════════════════════════════════════
#   CONFIGURACIÓN — cambia aquí lo que quieres analizar
# ══════════════════════════════════════════════════════════════════════

# Algoritmo: 'kmeans' o 'kmedoids'
ALGORITMO = 'kmeans'

# Normalización: 'mm' (Min-Max), 'z' (Z-score), 'rel' (Relativa), 'corr' (Correlación)
NORMALIZACION = 'mm'

# K a analizar (número de categorías de Jenny)
# Puedes poner un solo valor:  K_ANALIZAR = 4
# O una lista para comparar:   K_ANALIZAR = [3, 4, 5, 6]
K_ANALIZAR = 4

# ══════════════════════════════════════════════════════════════════════

plt.rcParams.update({
    'font.family': 'DejaVu Sans',
    'font.size': 10,
    'axes.titlesize': 12,
    'axes.titleweight': 'bold',
    'figure.dpi': 150,
})

# Variables de entrada (las que tienes recogidas para cada municipio)
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
    'ind_envej':             'Indice envejecimiento',
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
    'tiene_cs':              'Tiene centro de salud',
    'tiene_hospital':        'Tiene hospital',
    'dist_cs_km':            'Distancia a C. Salud (km)',
    'dist_hospital_km':      'Distancia a hospital (km)',
    'tiene_colegio':         'Tiene colegio',
    'tiene_instituto':       'Tiene instituto',
    'dist_colegio_km':       'Distancia a colegio (km)',
    'dist_instituto_km':     'Distancia a instituto (km)',
    'tiene_residencia':      'Tiene residencia mayores',
    'plazas_residencia_1000':'Plazas residencia /1000 hab',
    'dist_residencia_km':    'Distancia a residencia (km)',
    'dist_capital_km':       'Distancia a capital (km)',
    'superficie_km2':        'Superficie (km2)',
}

# ── Funciones auxiliares ───────────────────────────────────────────────────────

def cargar_categorias_jenny(clave):
    """Lee datos_jenny.js y extrae las categorías de la clave indicada."""
    with open(os.path.join(RAIZ, 'datos_jenny.js'), encoding='utf-8') as f:
        contenido = f.read()
    m = re.search(r'"' + clave + r'"\s*:\s*\{([^}]*)\}', contenido)
    if not m:
        return None
    pares = re.findall(r'"(\d+)"\s*:\s*(-?\d+)', m.group(1))
    df = pd.DataFrame(pares, columns=['codigo_ine', 'cluster_jenny'])
    df['cluster_jenny'] = df['cluster_jenny'].astype(int)
    return df


def analizar_combinacion(clave, df_vars):
    """
    Ejecuta el análisis completo de entropía para una combinación de Jenny.
    Devuelve el accuracy de validación cruzada y el ranking de variables.
    """
    print(f"\n{'='*60}")
    print(f"  Analizando: {clave}")
    print(f"{'='*60}")

    # Cargar categorías de Jenny
    df_jenny = cargar_categorias_jenny(clave)
    if df_jenny is None:
        print(f"  ✗ Clave '{clave}' no encontrada en datos_jenny.js")
        return None, None

    # Descartar clusters con un solo municipio (caso atípico)
    tam = df_jenny['cluster_jenny'].value_counts()
    outliers = tam[tam == 1].index.tolist()
    if outliers:
        print(f"  Excluyendo cluster atipico (1 municipio): C{outliers}")
        df_jenny = df_jenny[~df_jenny['cluster_jenny'].isin(outliers)]

    # Verificar que no sea una combinación degenerada (todos en un cluster)
    if len(df_jenny['cluster_jenny'].unique()) < 2:
        print(f"  ✗ Combinación degenerada: todos los municipios en un solo cluster")
        return None, None

    df_jenny['target'] = 'C' + df_jenny['cluster_jenny'].astype(str)

    # Unir con variables
    df_merge = df_vars.merge(df_jenny[['codigo_ine', 'target']], on='codigo_ine', how='inner')
    df_clean = df_merge.dropna(subset=FEATURES + ['target'])

    print(f"  Municipios válidos: {len(df_clean)}")
    print(f"  Distribución: { {k: v for k, v in df_clean['target'].value_counts().sort_index().items()} }")

    X = df_clean[FEATURES].values
    y = df_clean['target'].values

    # Información mutua (ganancia de información por variable)
    discretas = [f in ('tiene_cs', 'tiene_hospital', 'tiene_colegio',
                        'tiene_instituto', 'tiene_residencia') for f in FEATURES]
    mi = mutual_info_classif(X, y, discrete_features=discretas, random_state=42)

    df_mi = pd.DataFrame({
        'variable':          FEATURES,
        'nombre_es':         [NOMBRES_ES[f] for f in FEATURES],
        'informacion_mutua': mi,
    }).sort_values('informacion_mutua', ascending=False)

    # Árbol de decisión con criterio entropía
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
    accuracy = cv_scores.mean()

    print(f"  Accuracy (5-fold CV): {accuracy:.3f} ± {cv_scores.std():.3f}")

    return accuracy, df_mi, arbol, df_clean, y_test, y_pred, df_jenny


def guardar_resultados(clave, accuracy, df_mi, arbol, df_clean, y_test, y_pred):
    """Guarda todos los gráficos y archivos de resultados para una combinación."""

    prefijo = clave  # ej: kmeans_mm_4

    # Ranking combinado (info mutua + árbol)
    df_arbol = pd.DataFrame({
        'variable':          FEATURES,
        'ganancia_info_arbol': arbol.feature_importances_,
    })
    ranking = df_mi.merge(df_arbol, on='variable').sort_values('ganancia_info_arbol', ascending=False)

    # CSV con ranking
    csv_path = os.path.join(RESULTADOS, f'tfm_{prefijo}_importancia.csv')
    ranking.to_csv(csv_path, index=False, encoding='utf-8-sig')

    # Gráfico: información mutua (azul)
    orden_mi = df_mi.sort_values('informacion_mutua', ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(orden_mi['nombre_es'], orden_mi['informacion_mutua'], color='#2980b9', edgecolor='white')
    ax.set_xlabel('Ganancia de informacion (entropia)')
    ax.set_title(f'Ganancia de informacion por variable\n{clave.upper()} — categorias de Jenny')
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGENES, f'tfm_{prefijo}_mutual_info.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # Gráfico: importancia del árbol (rojo)
    orden_arbol = ranking.sort_values('ganancia_info_arbol', ascending=True)
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(orden_arbol['nombre_es'], orden_arbol['ganancia_info_arbol'], color='#c0392b', edgecolor='white')
    ax.set_xlabel('Importancia (criterio entropy)')
    ax.set_title(f'Variables mas influyentes — {clave.upper()}\nArbol de Decision con criterio entropia')
    ax.grid(axis='x', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGENES, f'tfm_{prefijo}_importancia.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # Gráfico: árbol visual (primeros 3 niveles)
    clases = sorted(arbol.classes_)
    fig, ax = plt.subplots(figsize=(20, 9))
    plot_tree(arbol, feature_names=[NOMBRES_ES[f] for f in FEATURES],
              class_names=clases, max_depth=3, filled=True, rounded=True,
              fontsize=7, ax=ax, impurity=False, proportion=True)
    ax.set_title(f'Arbol de Decision (entropia) — {clave.upper()} (primeros 3 niveles)')
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGENES, f'tfm_{prefijo}_arbol.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # Gráfico: matriz de confusión
    cm = confusion_matrix(y_test, y_pred, labels=clases)
    fig, ax = plt.subplots(figsize=(7, 6))
    ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=clases).plot(ax=ax, cmap='Reds')
    ax.set_title(f'Matriz de Confusion — {clave.upper()}')
    plt.tight_layout()
    plt.savefig(os.path.join(IMAGENES, f'tfm_{prefijo}_confusion.png'), dpi=150, bbox_inches='tight')
    plt.close()

    # Archivo de texto con resumen
    txt_path = os.path.join(RESULTADOS, f'tfm_{prefijo}_resultados.txt')
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f'ANALISIS DE ENTROPIA — {clave.upper()}\n')
        f.write('=' * 60 + '\n\n')
        f.write(f'Municipios analizados: {len(df_clean)}\n')
        f.write(f'Accuracy (5-fold CV): {accuracy:.3f}\n\n')
        f.write('RANKING POR INFORMACION MUTUA:\n' + '-' * 40 + '\n')
        for _, row in df_mi.iterrows():
            f.write(f'  {row["informacion_mutua"]:.4f}  {row["nombre_es"]}\n')
        f.write('\nRANKING POR GANANCIA DE INFORMACION (arbol):\n' + '-' * 40 + '\n')
        for _, row in ranking.sort_values('ganancia_info_arbol', ascending=False).iterrows():
            f.write(f'  {row["ganancia_info_arbol"]:.4f}  {row["nombre_es"]}\n')
        f.write('\nINFORME DE CLASIFICACION:\n' + '-' * 40 + '\n')
        f.write(classification_report(y_test, y_pred, zero_division=0))
        f.write('\nREGLAS DEL ARBOL (primeros 3 niveles):\n' + '-' * 40 + '\n')
        f.write(export_text(arbol, feature_names=FEATURES, max_depth=3))

    print(f"  Archivos guardados con prefijo: tfm_{prefijo}_*")


# ── Cargar variables (común para todas las combinaciones) ─────────────────────

print("Cargando dataset_tfm.csv...")
df_vars = pd.read_csv(os.path.join(RESULTADOS, 'dataset_tfm.csv'), encoding='utf-8-sig')
df_vars.columns = df_vars.columns.str.strip()
df_vars['codigo_ine'] = df_vars['codigo_ine'].astype(str).str.zfill(5)

# Los municipios sin establecimientos registrados tienen 0, no dato perdido
for col in ['bares_1000', 'restaurantes_1000', 'alojamiento_1000', 'estab_total_1000']:
    df_vars[col] = df_vars[col].fillna(0)

# ── Ejecutar el análisis ───────────────────────────────────────────────────────

# Construir la lista de combinaciones a analizar
ks = [K_ANALIZAR] if isinstance(K_ANALIZAR, int) else K_ANALIZAR
claves = [f'{ALGORITMO}_{NORMALIZACION}_{k}' for k in ks]

resultados_comparacion = []

for clave in claves:
    resultado = analizar_combinacion(clave, df_vars)
    if resultado[0] is not None:
        accuracy, df_mi, arbol, df_clean, y_test, y_pred, _ = resultado
        guardar_resultados(clave, accuracy, df_mi, arbol, df_clean, y_test, y_pred)
        resultados_comparacion.append({'combinacion': clave, 'accuracy_cv': accuracy})

# ── Si se analizaron varias K, generar gráfico comparativo ────────────────────

if len(resultados_comparacion) > 1:
    print(f"\n{'='*60}")
    print("  COMPARACION ENTRE COMBINACIONES")
    print(f"{'='*60}")

    df_comp = pd.DataFrame(resultados_comparacion).sort_values('accuracy_cv', ascending=False)
    print(df_comp.to_string(index=False))

    # Gráfico comparativo de accuracy por K
    fig, ax = plt.subplots(figsize=(10, 5))
    colores = ['#c0392b' if i == 0 else '#2980b9' for i in range(len(df_comp))]
    ax.bar(df_comp['combinacion'], df_comp['accuracy_cv'], color=colores, edgecolor='white')
    ax.set_ylabel('Accuracy (5-fold CV)')
    ax.set_title(f'Comparacion de combinaciones — {ALGORITMO.upper()} · {NORMALIZACION.upper()}\n'
                 f'¿Qué K produce categorías mejor explicadas por las variables?')
    ax.set_ylim(0, 1)
    ax.axhline(df_comp['accuracy_cv'].max(), color='red', linestyle='--', alpha=0.5)
    ax.grid(axis='y', alpha=0.3)
    plt.xticks(rotation=20, ha='right')
    for bar, val in zip(ax.patches, df_comp['accuracy_cv']):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.01,
                f'{val:.3f}', ha='center', fontsize=10, fontweight='bold')
    plt.tight_layout()
    nombre_comp = f'tfm_{ALGORITMO}_{NORMALIZACION}_comparacion_k.png'
    plt.savefig(os.path.join(IMAGENES, nombre_comp), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n  Mejor combinación: {df_comp.iloc[0]['combinacion']} "
          f"(accuracy={df_comp.iloc[0]['accuracy_cv']:.3f})")
    print(f"  Gráfico comparativo guardado: {nombre_comp}")

print("\nAnalisis completado.")
