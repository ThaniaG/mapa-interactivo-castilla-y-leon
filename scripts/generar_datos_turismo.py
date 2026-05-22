"""
generar_datos_turismo.py
════════════════════════
Procesa los datasets oficiales de la Junta de Castilla y León y genera
datos_turismo.js con museos y monumentos para el dashboard.

Fuentes:
  - Directorio de Museos de Castilla y León (datosabiertos.jcyl.es)
  - Relación de Monumentos de Castilla y León (datosabiertos.jcyl.es)

Cómo ejecutar:
    python generar_datos_turismo.py
"""

import pandas as pd
import json
import os
import re
import time

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(BASE, 'museos y monumentos')
F_MUSEOS = os.path.join(CARPETA, 'Directorio de Museos de Castilla y León.csv')
F_MONUM  = os.path.join(CARPETA, 'relacion-monumentos.csv')
SALIDA   = os.path.join(BASE, 'datos_turismo.js')


# ── Utilidades ────────────────────────────────────────────────────────────────
def limpiar_html(texto):
    """Elimina etiquetas HTML y decodifica entidades básicas."""
    if not texto or pd.isna(texto):
        return ''
    texto = re.sub(r'<[^>]+>', ' ', str(texto))
    texto = texto.replace('&nbsp;', ' ').replace('&amp;', '&')
    texto = texto.replace('&aacute;', 'á').replace('&eacute;', 'é')
    texto = texto.replace('&iacute;', 'í').replace('&oacute;', 'ó')
    texto = texto.replace('&uacute;', 'ú').replace('&ntilde;', 'ñ')
    texto = texto.replace('&Aacute;', 'Á').replace('&Eacute;', 'É')
    texto = texto.replace('&Iacute;', 'Í').replace('&Oacute;', 'Ó')
    texto = texto.replace('&Uacute;', 'Ú').replace('&Ntilde;', 'Ñ')
    texto = texto.replace('&quot;', '"').replace('&lt;', '<').replace('&gt;', '>')
    texto = re.sub(r'\s+', ' ', texto).strip()
    # Truncar a 300 caracteres para no inflar el archivo
    return texto[:300] + '…' if len(texto) > 300 else texto


def extraer_coords_museo(valor):
    """Extrae lat/lon del campo DirectorioRelacionado con formato 'lat#lon#alt'."""
    if pd.isna(valor):
        return None, None
    m = re.match(r'([\d\.\-]+)#([\d\.\-]+)', str(valor))
    if m:
        return round(float(m.group(1)), 6), round(float(m.group(2)), 6)
    return None, None


def limpiar_horario(html):
    """Extrae texto legible del campo de horario."""
    if not html or pd.isna(html):
        return ''
    texto = limpiar_html(html)
    # Quitar "Del 01/01 al 30/12 -" para acortar
    texto = re.sub(r'Del \d{2}/\d{2} al \d{2}/\d{2} - ', '', texto)
    return texto[:200] + '…' if len(texto) > 200 else texto


# ── Procesar Museos ───────────────────────────────────────────────────────────
def procesar_museos():
    print('Procesando museos...')
    df = pd.read_csv(F_MUSEOS, sep=';', skiprows=1, encoding='latin-1')

    puntos = []
    sin_coords = 0

    for _, row in df.iterrows():
        lat, lon = extraer_coords_museo(row.get('DirectorioRelacionado.1'))
        if lat is None:
            sin_coords += 1
            continue

        nombre = str(row.get('NombreEntidad', '')).strip()
        if not nombre or nombre == 'nan':
            continue

        punto = {
            'nombre':    nombre,
            'categoria': 'Museo',
            'lat':       lat,
            'lon':       lon,
            'municipio': str(row.get('Localidad', '')).strip(),
        }

        horario = limpiar_horario(row.get('Horario de apertura', ''))
        if horario:
            punto['horario'] = horario

        web = str(row.get('Enlace al contenido', '')).strip()
        if web and web != 'nan':
            punto['web'] = web

        puntos.append(punto)

    print(f'  Museos procesados: {len(puntos)} (sin coords: {sin_coords})')
    return puntos


# ── Procesar Monumentos ───────────────────────────────────────────────────────
def procesar_monumentos():
    print('Procesando monumentos...')
    df = pd.read_csv(F_MONUM, sep=';', encoding='utf-8')

    puntos = []
    sin_coords = 0

    for _, row in df.iterrows():
        try:
            lat = float(row['coordenadas_latitud'])
            lon = float(row['coordenadas_longitud'])
        except (ValueError, TypeError):
            sin_coords += 1
            continue

        nombre = str(row.get('nombre', '')).strip()
        if not nombre or nombre == 'nan':
            continue

        punto = {
            'nombre':    nombre,
            'categoria': str(row.get('tipoMonumento', 'Monumento')).strip(),
            'lat':       round(lat, 6),
            'lon':       round(lon, 6),
            'provincia': str(row.get('poblacion_provincia', '')).strip(),
            'municipio': str(row.get('poblacion_municipio', '')).strip(),
        }

        periodo = str(row.get('periodoHistorico', '')).strip()
        if periodo and periodo != 'nan':
            punto['periodo'] = periodo

        desc = limpiar_html(row.get('Descripcion', ''))
        if desc:
            punto['descripcion'] = desc

        puntos.append(punto)

    print(f'  Monumentos procesados: {len(puntos)} (sin coords: {sin_coords})')
    return puntos


# ── Estadísticas ──────────────────────────────────────────────────────────────
def mostrar_estadisticas(puntos):
    conteo = {}
    for p in puntos:
        cat = p['categoria']
        conteo[cat] = conteo.get(cat, 0) + 1

    print('\nResumen por categoría:')
    for cat, n in sorted(conteo.items(), key=lambda x: -x[1]):
        print(f'  {cat:<35} {n:>4}')
    print(f'  {"TOTAL":<35} {len(puntos):>4}')


# ── Generar JS ────────────────────────────────────────────────────────────────
def generar_js(puntos):
    categorias = sorted(set(p['categoria'] for p in puntos))

    js  = '// Puntos turísticos de Castilla y León — fuente: datosabiertos.jcyl.es (Junta de CyL)\n'
    js += f'// Generado: {time.strftime("%Y-%m-%d")} · {len(puntos)} puntos\n'
    js += '// Categorías: ' + ', '.join(categorias) + '\n'
    js += 'var datosTurismo = ' + json.dumps(puntos, ensure_ascii=False, indent=2) + ';\n'

    with open(SALIDA, 'w', encoding='utf-8') as f:
        f.write(js)

    kb = os.path.getsize(SALIDA) / 1024
    print(f'\nArchivo generado: datos_turismo.js ({kb:.0f} KB)')


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    museos    = procesar_museos()
    monum     = procesar_monumentos()
    todos     = museos + monum

    mostrar_estadisticas(todos)
    generar_js(todos)
    print('\nListo.')
