"""
generar_datos_edades.py
═══════════════════════
Procesa el Excel del INE (Censo Anual de Población, grupos quinquenales)
y genera datos_edades.js con dos indicadores por municipio de CyL:

  - porc_65      : % de población mayor de 65 años (2025)
  - ind_envej    : índice de envejecimiento = (>65 / <20) × 100
  - pob_65       : número absoluto de mayores de 65
  - pob_total    : población total (para validación)

Fuente: INE > Censo Anual de Población 2021-2025 > Resultados por municipios
        Población por sexo, edad (grupos quinquenales) y nacionalidad

Cómo ejecutar:
    python generar_datos_edades.py

Resultado:
    Genera datos_edades.js en la carpeta del proyecto.
"""

import openpyxl
import json
import os

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE  = os.path.dirname(os.path.abspath(__file__))
XLSX  = os.path.join(BASE, 'Poblacion por edades, sexo, nacionalidad',
                     'Total de municipios de españa, sexo, edad, nacionalidad y periodo.xlsx')
SALIDA = os.path.join(BASE, 'datos_edades.js')

# ── Provincias de Castilla y León ─────────────────────────────────────────────
CYL = {'05', '09', '24', '34', '37', '40', '42', '47', '49'}

# ── Grupos de edad que suman >65 y <20 ────────────────────────────────────────
GRUPOS_65 = {
    'De 65 a 69 años', 'De 70 a 74 años', 'De 75 a 79 años',
    'De 80 a 84 años', 'De 85 a 89 años', 'De 90 a 94 años',
    'De 95 a 99 años', '100 y más años'
}
GRUPOS_20 = {
    'De 0 a 4 años', 'De 5 a 9 años', 'De 10 a 14 años', 'De 15 a 19 años'
}

# ── Leer Excel ────────────────────────────────────────────────────────────────
print('Leyendo Excel...')
wb = openpyxl.load_workbook(XLSX, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))

# ── Construir índice de columnas ──────────────────────────────────────────────
# Las cabeceras están en las filas 6, 7, 8, 9 (índice 0-based)
# Cada nivel se rellena hacia adelante (fill-forward)
def fill_forward(row):
    result, current = [], None
    for v in row:
        if v is not None and str(v).strip() not in ('', ' '):
            current = str(v).strip()
        result.append(current)
    return result

h_sexo  = fill_forward(rows[6])
h_edad  = fill_forward(rows[7])
h_nac   = fill_forward(rows[8])
h_per   = [str(v).strip() if v else None for v in rows[9]]

# Columnas útiles por sexo: Nacionalidad=Total, Periodo=2025
def buscar_cols(sexo_filtro):
    c65, c20, ctot = [], [], []
    for i in range(1, len(h_sexo)):
        if h_sexo[i] == sexo_filtro and h_nac[i] == 'Total' and h_per[i] == '2025':
            edad = h_edad[i]
            if edad in GRUPOS_65:
                c65.append(i)
            elif edad in GRUPOS_20:
                c20.append(i)
            elif edad == 'Todas las edades':
                ctot.append(i)
    return c65, c20, ctot

cols_65,   cols_20,   cols_total   = buscar_cols('Total')
cols_65_h, cols_20_h, cols_total_h = buscar_cols('Hombres')
cols_65_m, cols_20_m, cols_total_m = buscar_cols('Mujeres')

print(f'  Columnas Total  — >65: {len(cols_65)} (esp. 8), <20: {len(cols_20)} (esp. 4), total: {len(cols_total)} (esp. 1)')
print(f'  Columnas Hombres— >65: {len(cols_65_h)} (esp. 8), <20: {len(cols_20_h)} (esp. 4), total: {len(cols_total_h)} (esp. 1)')
print(f'  Columnas Mujeres— >65: {len(cols_65_m)} (esp. 8), <20: {len(cols_20_m)} (esp. 4), total: {len(cols_total_m)} (esp. 1)')

if len(cols_65) != 8 or len(cols_20) != 4 or len(cols_total) != 1:
    print('ERROR: columnas Total inesperadas. Revisa el archivo Excel.')
    exit(1)
if len(cols_65_h) != 8 or len(cols_total_h) != 1:
    print('ERROR: columnas Hombres inesperadas. Revisa el archivo Excel.')
    exit(1)
if len(cols_65_m) != 8 or len(cols_total_m) != 1:
    print('ERROR: columnas Mujeres inesperadas. Revisa el archivo Excel.')
    exit(1)

col_total   = cols_total[0]
col_total_h = cols_total_h[0]
col_total_m = cols_total_m[0]

# ── Procesar municipios de CyL ────────────────────────────────────────────────
print('Procesando municipios de CyL...')
resultado = {}
procesados = 0
sin_datos  = 0

for row in rows[10:]:
    if not row[0]:
        continue

    celda = str(row[0]).strip()

    # Solo municipios individuales: código 5 dígitos, provincia en CyL
    if len(celda) < 6 or celda[5] != ' ':
        continue
    if celda[:2] not in CYL:
        continue

    codigo = celda[:5]
    nombre = celda[6:].strip()

    # Obtener valores de las columnas identificadas
    def get_val(col):
        v = row[col]
        return float(v) if v is not None else 0.0

    pob_total = get_val(col_total)
    pob_65    = sum(get_val(c) for c in cols_65)
    pob_20    = sum(get_val(c) for c in cols_20)

    if pob_total <= 0:
        sin_datos += 1
        continue

    pob_total_h = get_val(col_total_h)
    pob_65_h    = sum(get_val(c) for c in cols_65_h)
    pob_20_h    = sum(get_val(c) for c in cols_20_h)

    pob_total_m = get_val(col_total_m)
    pob_65_m    = sum(get_val(c) for c in cols_65_m)
    pob_20_m    = sum(get_val(c) for c in cols_20_m)

    porc_65   = round(pob_65   / pob_total   * 100, 1)
    porc_65_h = round(pob_65_h / pob_total_h * 100, 1) if pob_total_h > 0 else 0.0
    porc_65_m = round(pob_65_m / pob_total_m * 100, 1) if pob_total_m > 0 else 0.0

    ind_envej   = round(pob_65   / pob_20   * 100, 1) if pob_20   > 0 else 0.0
    ind_envej_h = round(pob_65_h / pob_20_h * 100, 1) if pob_20_h > 0 else 0.0
    ind_envej_m = round(pob_65_m / pob_20_m * 100, 1) if pob_20_m > 0 else 0.0

    resultado[codigo] = {
        'nombre':      nombre,
        'pob_total':   int(pob_total),
        'pob_65':      int(pob_65),
        'porc_65':     porc_65,
        'porc_65_h':   porc_65_h,
        'porc_65_m':   porc_65_m,
        'ind_envej':   ind_envej,
        'ind_envej_h': ind_envej_h,
        'ind_envej_m': ind_envej_m,
    }
    procesados += 1

print(f'  Municipios procesados : {procesados}')
print(f'  Sin datos (pob=0)     : {sin_datos}')

# ── Escribir datos_edades.js ──────────────────────────────────────────────────
contenido = (
    '// datos_edades.js — Generado automáticamente por generar_datos_edades.py\n'
    '// Contiene indicadores de envejecimiento por municipio de CyL (INE 2025).\n'
    '// NO editar manualmente.\n\n'
    'const DATOS_EDADES = '
    + json.dumps(resultado, ensure_ascii=False, separators=(',', ':'))
    + ';'
)

with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write(contenido)

tamano_kb = os.path.getsize(SALIDA) / 1024
print(f'\nArchivo generado: datos_edades.js ({tamano_kb:.0f} KB)')
print(f'Total municipios: {len(resultado)}')

# ── Mostrar ejemplos ──────────────────────────────────────────────────────────
print('\nEjemplos:')
ejemplos = ['47001', '47186', '05001', '09059']
for cod in ejemplos:
    if cod in resultado:
        d = resultado[cod]
        print(f"  {cod} {d['nombre']}: {d['porc_65']}% >65, índice {d['ind_envej']}, total {d['pob_total']}")
