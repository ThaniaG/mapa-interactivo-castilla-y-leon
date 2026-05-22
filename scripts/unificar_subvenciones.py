"""
unificar_subvenciones.py
════════════════════════
Une todos los archivos Excel de la carpeta Subvenciones/
en un único archivo subvenciones_unificado.xlsx.

Cómo ejecutar:
    python unificar_subvenciones.py
"""

import pandas as pd
import glob
import os
import warnings
warnings.filterwarnings('ignore')

BASE    = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(BASE, 'Subvenciones')
SALIDA  = os.path.join(BASE, 'Subvenciones', 'subvenciones_unificado.xlsx')

archivos = sorted(glob.glob(os.path.join(CARPETA, 'listado*.xlsx')))
print(f'Archivos encontrados: {len(archivos)}')

dfs = []
for i, f in enumerate(archivos, 1):
    try:
        df = pd.read_excel(f)
        if len(df) > 1:
            dfs.append(df)
            if i % 20 == 0:
                print(f'  Leídos {i}/{len(archivos)}...')
    except Exception as e:
        print(f'  Error en {os.path.basename(f)}: {e}')

todo = pd.concat(dfs, ignore_index=True)
print(f'\nTotal filas unificadas: {len(todo):,}')
print(f'Columnas: {list(todo.columns)}')

print('\nGuardando subvenciones_unificado.xlsx...')
todo.to_excel(SALIDA, index=False)
print(f'Guardado: {SALIDA}')
print(f'Tamaño: {os.path.getsize(SALIDA) / 1024 / 1024:.1f} MB')
