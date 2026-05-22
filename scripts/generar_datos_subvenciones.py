"""
generar_datos_subvenciones.py
══════════════════════════════
Procesa el archivo unificado de subvenciones del BDNS (9 diputaciones de CyL)
y genera datos_subvenciones.js con el total y desglose anual por municipio.

Fuente: BDNS (infosubvenciones.es) — Concesiones de las 9 diputaciones de CyL
        Filtro: Entidades locales > Castilla y León > 2022-2025

Cómo ejecutar:
    python generar_datos_subvenciones.py
"""

import pandas as pd
import json
import os
import unicodedata
import re
import warnings
warnings.filterwarnings('ignore')

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
EXCEL   = os.path.join(BASE, 'Subvenciones', 'subvenciones_unificado.xlsx')
EDADES  = os.path.join(BASE, 'datos_edades.js')
SALIDA  = os.path.join(BASE, 'datos_subvenciones.js')

# ── Provincias de Castilla y León ─────────────────────────────────────────────
CYL = {'05', '09', '24', '34', '37', '40', '42', '47', '49'}

NOMBRES_PROV = {
    '05': 'Ávila', '09': 'Burgos', '24': 'León', '34': 'Palencia',
    '37': 'Salamanca', '40': 'Segovia', '42': 'Soria', '47': 'Valladolid', '49': 'Zamora'
}

# ── Cargar referencia de municipios desde datos_edades.js ─────────────────────
print('Cargando referencia de municipios...')
with open(EDADES, encoding='utf-8') as f:
    contenido = f.read()
# Extraer el JSON del archivo JS
json_str = contenido.split('const DATOS_EDADES = ')[1].rstrip(';')
edades = json.loads(json_str)

# Normalizar texto para comparación
def normalizar(texto):
    texto = str(texto).upper().strip()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = re.sub(r'[^A-Z0-9 ]', ' ', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

# Construir índice: (provincia, nombre_normalizado) → código INE
# Varias versiones del nombre para cubrir diferencias entre BDNS e INE
def variantes(nombre_norm):
    v = [nombre_norm]
    # Artículo al inicio ↔ al final, y también sin artículo
    for art in ['LA ', 'EL ', 'LOS ', 'LAS ', 'LO ']:
        if nombre_norm.startswith(art):
            sin_art = nombre_norm[len(art):]
            v.append(sin_art + ' ' + art.strip())  # "X LA"
            v.append(sin_art)                        # "X" sin artículo
        elif nombre_norm.endswith(' ' + art.strip()):
            base = nombre_norm[:-(len(art.strip()) + 1)]
            v.append(art + base)   # "LA CISTERNIGA"
            v.append(base)         # "CISTERNIGA"
    # Sin partículas: "SIETEIGLESIAS DE TRABANCOS" -> "SIETEIGLESIAS TRABANCOS"
    sin_de = nombre_norm
    for part in [' DE LA ', ' DE LAS ', ' DE LOS ', ' DEL ', ' DE ']:
        sin_de = sin_de.replace(part, ' ')
    v.append(sin_de)
    # "DE LA" → "LA": "CEPEDA DE LA MORA" → "CEPEDA LA MORA"
    con_art = nombre_norm.replace(' DE LA ', ' LA ').replace(' DE LAS ', ' LAS ').replace(' DEL ', ' EL ')
    v.append(con_art)
    # Prefijo antes del primer "DE" (BDNS trunca: "CARRIZO" de "CARRIZO DE LA RIBERA")
    for sep in [' DE LA ', ' DE LAS ', ' DE LOS ', ' DEL ', ' DE ']:
        idx = nombre_norm.find(sep)
        if idx > 0:
            v.append(nombre_norm[:idx])
            break
    # Prefijo antes de " Y " (nombres compuestos: "MANJABALAGO Y ORTIGOSA..." → "MANJABALAGO")
    idx_y = nombre_norm.find(' Y ')
    if idx_y > 0:
        v.append(nombre_norm[:idx_y])
    # "SIETE IGLESIAS" <-> "SIETEIGLESIAS"
    v.append(nombre_norm.replace('SIETE IGLESIAS', 'SIETEIGLESIAS'))
    v.append(nombre_norm.replace('SIETEIGLESIAS', 'SIETE IGLESIAS'))
    return list(dict.fromkeys(v))

indice = {}
for codigo, datos in edades.items():
    prov = codigo[:2]
    nombre_norm = normalizar(datos['nombre'])
    for v in variantes(nombre_norm):
        key = (prov, v)
        if key not in indice:
            indice[(prov, v)] = codigo

print(f'  Municipios en referencia: {len(edades)}')

# ── Leer y filtrar subvenciones ───────────────────────────────────────────────
print('Leyendo subvenciones unificadas...')
df = pd.read_excel(EXCEL)
print(f'  Total filas: {len(df):,}')

# Filtrar solo beneficiarios con NIF municipal de CyL (P + 2 dígitos provincia + 5 + letra)
patron_nif = r'^P(\d{2})\d{5}[A-Z]\s+'
mask = df['Beneficiario'].astype(str).str.match(patron_nif)
df_muni = df[mask].copy()
print(f'  Con NIF municipal: {len(df_muni):,}')

# Filtrar solo provincias de CyL
df_muni['prov'] = df_muni['Beneficiario'].str.extract(r'^P(\d{2})')
df_muni = df_muni[df_muni['prov'].isin(CYL)]
print(f'  De provincias CyL: {len(df_muni):,}')

# ── Extraer nombre del municipio ──────────────────────────────────────────────
def decodificar_nombre(texto):
    # Corregir codificación rota: &XD1 = Ñ (hex D1 = 209 = Ñ)
    texto = re.sub(r'&XD1', 'N', texto)   # Ñ → N para normalización posterior
    texto = re.sub(r'&XE1', 'a', texto)   # á
    texto = re.sub(r'&XE9', 'e', texto)   # é
    texto = re.sub(r'&XED', 'i', texto)   # í
    texto = re.sub(r'&XF3', 'o', texto)   # ó
    texto = re.sub(r'&XFA', 'u', texto)   # ú
    return texto

def extraer_nombre(beneficiario, prov):
    texto = re.sub(r'^P\d{7}[A-Z]\s*', '', str(beneficiario)).strip()
    texto = decodificar_nombre(texto)
    texto = re.sub(r'\(.*?\)', '', texto).strip()
    # Corregir typos frecuentes del BDNS antes de quitar prefijos
    texto = re.sub(r'^AYUNATMIENTO', 'AYUNTAMIENTO', texto)
    for prefijo in ['AYUNTAMIENTO DE ', 'AYUNTAMIENTO DEL ', 'AYUNTAMIENTO DE LA ',
                    'AYUNTAMIENTO ', 'AYTO. DE ', 'AYTO. DEL ', 'AYTO. DE LA ', 'AYTO. ']:
        if texto.startswith(prefijo):
            texto = texto[len(prefijo):]
            break
    # Quitar AYTO. al final: "MAMOLAR, AYTO." → "MAMOLAR"
    texto = re.sub(r'[,\s]+AYTO\.?\s*$', '', texto, flags=re.IGNORECASE).strip()
    # Quitar "DE " al inicio si quedó tras quitar prefijo doble: "DE DE SAN JUAN" → "SAN JUAN"
    texto = re.sub(r'^DE\s+', '', texto, flags=re.IGNORECASE).strip()
    return normalizar(texto)

# Excluir entidades no municipales: Mancomunidades, Consejos Comarcales, etc.
excluir = ['MANCOMUNIDAD', 'CONSEJO COMARCAL', 'COMARCA', 'DIPUTACION', 'DIPUTACIÓN',
           'JUNTA DE CASTILLA', 'COMUNIDAD DE VILLA', 'COMUNIDAD V.T', 'JUNTA VECINAL',
           'E.L.M.', 'ENTIDAD LOCAL', 'CONSORCIO', 'MIG VALLADOLID', 'MIG ']
mask_excl = df_muni['Beneficiario'].astype(str).str.upper().apply(
    lambda x: not any(e in x for e in excluir)
)
df_muni = df_muni[mask_excl]
print(f'  Tras excluir no-municipios: {len(df_muni):,}')

df_muni['nombre_norm'] = df_muni.apply(
    lambda r: extraer_nombre(r['Beneficiario'], r['prov']), axis=1
)

# ── Cruzar con códigos INE ────────────────────────────────────────────────────
# Mapeo manual para casos donde el nombre del BDNS y del INE difieren demasiado
MAPA_NIF = {
    'P3711500C': '37115',  # Dios le Guarde (BDNS: DIOSLEGUARDE)
    'P3419200E': '34192',  # Valde-Ucieza (BDNS: VALDEUCIEZA)
    'P4902700F': '49024',  # Bóveda de Toro, La (BDNS: BOVEDA TORO)
    'P0509000F': '05090',  # Gutierre-Muñoz (BDNS: GUTIERREZ MUÑOZ)
    'P0919300D': '09190',  # Junta de Villalba de Losa (BDNS: VILLALBA DE LOSA AYTO.)
    'P0924800F': '09241',  # Orbaneja Riopico (BDNS: ORBANEJA RIO PICO)
    'P4015100C': '40130',  # Montejo de la Vega de la Serrezuela (BDNS: SERRAZUELA)
}

def buscar_codigo(row):
    # Primero comprobar mapeo manual por NIF
    nif = re.match(r'^(P\d{7}[A-Z])', str(row['Beneficiario']))
    if nif and nif.group(1) in MAPA_NIF:
        return MAPA_NIF[nif.group(1)]
    prov = row['prov']
    for v in variantes(row['nombre_norm']):
        codigo = indice.get((prov, v))
        if codigo:
            return codigo
    return None

df_muni['codigo_ine'] = df_muni.apply(buscar_codigo, axis=1)

sin_match = df_muni['codigo_ine'].isna().sum()
con_match = df_muni['codigo_ine'].notna().sum()
print(f'\n  Con código INE encontrado: {con_match:,}')
print(f'  Sin coincidencia: {sin_match:,}')

# Mostrar los que no se pudieron cruzar
if sin_match > 0:
    no_match = df_muni[df_muni['codigo_ine'].isna()][['Beneficiario', 'prov', 'nombre_norm']].drop_duplicates()
    print(f'\n  Primeros sin match ({min(10, len(no_match))}):')
    for _, r in no_match.head(10).iterrows():
        print(f'    [{r["prov"]}] {r["Beneficiario"]} -- "{r["nombre_norm"]}"')

# ── Extraer año ───────────────────────────────────────────────────────────────
df_ok = df_muni[df_muni['codigo_ine'].notna()].copy()
df_ok['anio'] = pd.to_datetime(df_ok['Fecha de concesión'], dayfirst=True, errors='coerce').dt.year
df_ok = df_ok[df_ok['anio'].between(2022, 2025)]
df_ok['Importe'] = pd.to_numeric(df_ok['Importe'], errors='coerce').fillna(0)

print(f'\n  Filas con código + año válido: {len(df_ok):,}')
print(f'  Años: {sorted(df_ok["anio"].unique().astype(int).tolist())}')

# ── Agregar por municipio ─────────────────────────────────────────────────────
print('\nAgregando por municipio...')
resultado = {}

# Total acumulado 2022-2025
totales = df_ok.groupby('codigo_ine')['Importe'].sum()

# Desglose anual
anuales = df_ok.groupby(['codigo_ine', 'anio'])['Importe'].sum().unstack(fill_value=0)
num_subv = df_ok.groupby('codigo_ine').size()

for codigo in totales.index:
    datos = edades.get(codigo, {})
    por_anio = {}
    for anio in [2022, 2023, 2024, 2025]:
        val = anuales.loc[codigo, anio] if anio in anuales.columns and codigo in anuales.index else 0
        por_anio[str(anio)] = round(float(val), 2)

    resultado[codigo] = {
        'nombre':          datos.get('nombre', ''),
        'total':           round(float(totales[codigo]), 2),
        'por_anio':        por_anio,
        'num_subvenciones': int(num_subv.get(codigo, 0)),
    }

print(f'  Municipios con subvenciones: {len(resultado)}')

# ── Escribir datos_subvenciones.js ────────────────────────────────────────────
contenido = (
    '// datos_subvenciones.js — Generado automáticamente por generar_datos_subvenciones.py\n'
    '// Subvenciones concedidas por las 9 diputaciones de CyL a municipios (BDNS 2022-2025).\n'
    '// NO editar manualmente.\n\n'
    'const DATOS_SUBVENCIONES = '
    + json.dumps(resultado, ensure_ascii=False, separators=(',', ':'))
    + ';'
)

with open(SALIDA, 'w', encoding='utf-8') as f:
    f.write(contenido)

kb = os.path.getsize(SALIDA) / 1024
print(f'\nArchivo generado: datos_subvenciones.js ({kb:.0f} KB)')
print(f'Total municipios: {len(resultado)}')

# ── Ejemplos ──────────────────────────────────────────────────────────────────
print('\nEjemplos:')
for cod in ['47186', '47161', '09059', '24089', '05001']:
    if cod in resultado:
        d = resultado[cod]
        print(f"  {cod} {d['nombre']}: total {d['total']:,.0f}€ — {d['por_anio']} ({d['num_subvenciones']} subv.)")
