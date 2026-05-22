"""
generar_datos_renta.py
══════════════════════
Procesa el Excel del INE (Atlas de distribución de renta de los hogares)
y genera datos_renta.js con la renta neta media por persona (2023)
para los municipios de Castilla y León.

Fuente: INE > Atlas de distribución de renta de los hogares > Resultados totales
        Indicadores de renta media y mediana

Cómo ejecutar:
    python generar_datos_renta.py

Resultado:
    Genera datos_renta.js en la carpeta del proyecto.
"""

import openpyxl
import json
import os

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
XLSX   = os.path.join(BASE, 'Indicadores de renta media y mediana',
                      'Indicadores de renta media y mediana.xlsx')
SALIDA = os.path.join(BASE, 'datos_renta.js')

# ── Provincias de Castilla y León ─────────────────────────────────────────────
CYL = {'05', '09', '24', '34', '37', '40', '42', '47', '49'}

# ── Leer Excel ────────────────────────────────────────────────────────────────
print('Leyendo Excel...')
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

# Estructura: fila 6 = grupos, fila 7 = años, datos desde fila 8
# Columna 1 = Renta neta media por persona 2023
# Columna 28 = Mediana de la renta por unidad de consumo 2023
COL_RENTA_MEDIA   = 1   # Renta neta media por persona, 2023
COL_RENTA_MEDIANA = 28  # Mediana de la renta por unidad de consumo, 2023

print(f'  Cabecera columna {COL_RENTA_MEDIA}: {rows[6][COL_RENTA_MEDIA]} — {rows[7][COL_RENTA_MEDIA]}')
print(f'  Cabecera columna {COL_RENTA_MEDIANA}: {rows[6][COL_RENTA_MEDIANA]} — {rows[7][COL_RENTA_MEDIANA]}')

# ── Procesar municipios de CyL ────────────────────────────────────────────────
print('Procesando municipios de CyL...')
resultado  = {}
procesados = 0
sin_datos  = 0

for row in rows[8:]:
    if not row[0]:
        continue

    celda = str(row[0]).strip()

    # Solo municipios: código de 5 dígitos seguido de espacio
    if len(celda) < 6 or celda[5] != ' ':
        continue
    if celda[:2] not in CYL:
        continue

    codigo = celda[:5]
    nombre = celda[6:].strip()

    def get_val(col):
        v = row[col]
        if v is None or str(v).strip() in ('.', ''):
            return None
        try:
            return int(float(str(v)))
        except ValueError:
            return None

    renta_media   = get_val(COL_RENTA_MEDIA)
    renta_mediana = get_val(COL_RENTA_MEDIANA)

    if renta_media is None:
        sin_datos += 1
        continue

    resultado[codigo] = {
        'nombre':        nombre,
        'renta_media':   renta_media,
        'renta_mediana': renta_mediana,
    }
    procesados += 1

print(f'  Municipios con datos : {procesados}')
print(f'  Sin datos (renta=.)  : {sin_datos}')

# ── Escribir datos_renta.js ───────────────────────────────────────────────────
contenido = (
    '// datos_renta.js — Generado automáticamente por generar_datos_renta.py\n'
    '// Renta neta media por persona (€) — INE Atlas de distribución de renta 2023.\n'
    '// NO editar manualmente.\n\n'
    'const DATOS_RENTA = '
    + json.dumps(resultado, ensure_ascii=False, separators=(',', ':'))
    + ';'
)

with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write(contenido)

tamano_kb = os.path.getsize(SALIDA) / 1024
print(f'\nArchivo generado: datos_renta.js ({tamano_kb:.0f} KB)')
print(f'Total municipios: {len(resultado)}')

# ── Ejemplos ──────────────────────────────────────────────────────────────────
print('\nEjemplos:')
for cod in ['47186', '47001', '05001', '09059', '24089']:
    if cod in resultado:
        d = resultado[cod]
        print(f"  {cod} {d['nombre']}: renta media {d['renta_media']}€, mediana {d['renta_mediana']}€")
