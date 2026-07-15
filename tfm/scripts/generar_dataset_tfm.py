"""
generar_dataset_tfm.py
══════════════════════════════════════════════════════════════════
Genera el dataset completo para el TFM con todas las variables
de despoblación por municipio de Castilla y León.

Salida: dataset_tfm.csv

Variables generadas:
  IDENTIFICACIÓN    : codigo_ine, nombre, provincia
  DEMOGRAFÍA        : poblacion, densidad_pob, superficie_km2
                      porc_65, ind_envej, porc_extranjeros
  MOVIMIENTO NATURAL: tasa_natalidad, tasa_mortalidad, balance_vital_1000
  TENDENCIA         : perdida_5a, perdida_10a, perdida_25a, tendencia_anual
  ECONOMÍA          : renta_media, subv_per_capita
  SERVICIOS SALUD   : tiene_cs, tiene_hospital, dist_cs_km, dist_hospital_km
  EDUCACIÓN         : tiene_colegio, tiene_instituto, dist_colegio_km, dist_instituto_km
  SERVICIOS SOCIALES: tiene_residencia, plazas_residencia_1000, dist_residencia_km
  ACTIVIDAD ECONÓMICA: bares_1000, restaurantes_1000, alojamiento_1000, estab_total_1000
  GEOGRAFÍA         : dist_capital_km
  VARIABLE OBJETIVO : tasa_cambio_pob, clase_despoblacion
"""

import csv, json, math, re, os, io
import urllib.request

SCRIPTS    = os.path.dirname(os.path.abspath(__file__))
TFM        = os.path.dirname(SCRIPTS)
RAIZ       = os.path.dirname(TFM)
IMAGENES   = os.path.join(TFM, 'imagenes')
RESULTADOS = os.path.join(TFM, 'resultados')

# ── Utilidades ─────────────────────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = math.sin(d_lat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def dist_minima(lat, lon, puntos):
    """Distancia al punto más cercano de una lista [{lat, lon}]."""
    if not puntos:
        return None
    return min(haversine(lat, lon, p['lat'], p['lon']) for p in puntos)

def leer_js(nombre_archivo, nombre_var):
    """Lee un archivo .js y extrae el JSON de la variable declarada."""
    ruta = os.path.join(RAIZ, nombre_archivo)
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            with open(ruta, encoding=enc) as f:
                texto = f.read()
            break
        except Exception:
            continue
    # Quitar líneas de comentarios y buscar la declaración de variable
    lineas = [l for l in texto.splitlines() if not l.strip().startswith('//')]
    texto  = '\n'.join(lineas)
    patron = rf'const\s+{nombre_var}\s*=\s*'
    texto  = re.sub(patron, '', texto).strip().rstrip(';')
    return json.loads(texto)

def centroide(coords):
    """Centroide aproximado de un polígono (lon, lat)."""
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    return sum(lons)/len(lons), sum(lats)/len(lats)

def area_km2(coords):
    """Área en km² de un polígono de coordenadas geográficas."""
    R = 6371
    n = len(coords)
    area = 0
    for i in range(n):
        j = (i+1) % n
        lon1, lat1 = math.radians(coords[i][0]), math.radians(coords[i][1])
        lon2, lat2 = math.radians(coords[j][0]), math.radians(coords[j][1])
        area += (lon2 - lon1) * (math.sin(lat1) + math.sin(lat2))
    return abs(area) * R * R / 2

def regresion_pendiente(xs, ys):
    """Pendiente de regresión lineal simple."""
    n = len(xs)
    if n < 2: return 0
    mx, my = sum(xs)/n, sum(ys)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,ys))
    den = sum((x-mx)**2 for x in xs)
    return num/den if den else 0

# ── 1. Cargar datos base ────────────────────────────────────────────────────────

print("Cargando datos base...")

geo       = leer_js('datos_municipios.js',      'DATOS_GEO')
edades    = leer_js('datos_edades.js',           'DATOS_EDADES')
evolucion = leer_js('datos_evolucion.js',        'DATOS_EVOLUCION')
vital     = leer_js('datos_vital.js',            'DATOS_VITAL')
renta     = leer_js('datos_renta.js',            'DATOS_RENTA')
subv      = leer_js('datos_subvenciones.js',     'DATOS_SUBVENCIONES')
estab     = leer_js('datos_establecimientos.js', 'DATOS_ESTABLECIMIENTOS')
salud     = leer_js('datos_salud.js',            'DATOS_SALUD')

puntos_salud = leer_js('datos_puntos_salud.js', 'datosPuntosSalud')

print("  OK")

# ── 2. Geometría: centroides, superficie y área por municipio ──────────────────

print("Calculando centroides y superficies...")

geom_muni = {}  # codigo -> {lat, lon, sup_km2}

for feat in geo['features']:
    p   = feat['properties']
    cod = p['codigo']
    geom = feat['geometry']
    polys = []
    if geom['type'] == 'Polygon':
        polys = [geom['coordinates'][0]]
    elif geom['type'] == 'MultiPolygon':
        polys = [poly[0] for poly in geom['coordinates']]

    sup = sum(area_km2(poly) for poly in polys)
    cx  = sum(c[0] for poly in polys for c in poly) / sum(len(poly) for poly in polys)
    cy  = sum(c[1] for poly in polys for c in poly) / sum(len(poly) for poly in polys)

    if cod not in geom_muni:
        geom_muni[cod] = {'lat': cy, 'lon': cx, 'sup_km2': 0}
    geom_muni[cod]['sup_km2'] += sup

print(f"  {len(geom_muni)} municipios con geometría")

# ── 3. Capitales de provincia (para distancia a capital) ──────────────────────

CAPITALES = {
    'avila':      '05019',
    'burgos':     '09059',
    'leon':       '24089',
    'palencia':   '34120',
    'salamanca':  '37274',
    'segovia':    '40194',
    'soria':      '42173',
    'valladolid': '47186',
    'zamora':     '49275',
}

coords_capitales = {}
for prov_key, cod_cap in CAPITALES.items():
    if cod_cap in geom_muni:
        coords_capitales[prov_key] = geom_muni[cod_cap]

# ── 4. Puntos de salud clasificados ───────────────────────────────────────────

puntos_cs       = [p for p in puntos_salud if p['tipo'] in ('cs', 'hospital')]
puntos_hospital = [p for p in puntos_salud if p['tipo'] == 'hospital']

print(f"  {len(puntos_cs)} centros de salud+hospital | {len(puntos_hospital)} hospitales")

# ── 5. Colegios ────────────────────────────────────────────────────────────────

print("Cargando datos de colegios...")

TIPOS_COLEGIO   = {'COLEGIO DE EDUCACION INFANTIL Y PRIMARIA', 'ESCUELA DE EDUCACION INFANTIL'}
TIPOS_INSTITUTO = {'INSTITUTO DE EDUCACION SECUNDARIA', 'INSTITUTO DE EDUCACION SECUNDARIA OBLIGATORIA'}

puntos_colegio   = []
puntos_instituto = []
munis_colegio    = set()
munis_instituto  = set()

with open(os.path.join(RAIZ, 'Colegios/directorio-de-centros-docentes.csv'), encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        if row['SITUACIÓN'] != 'ALTA': continue
        try:
            lat = float(row['COORD. LATITUD'])
            lon = float(row['COORD. LONGITUD'])
        except ValueError:
            continue
        cod = row['C.PROV'].zfill(2) + row['C.MUNI'].zfill(3)
        tipo = row['DENOMINACIÓN GENÉRICA']
        if tipo in TIPOS_COLEGIO:
            puntos_colegio.append({'lat': lat, 'lon': lon})
            munis_colegio.add(cod)
        elif tipo in TIPOS_INSTITUTO:
            puntos_instituto.append({'lat': lat, 'lon': lon})
            munis_instituto.add(cod)

print(f"  {len(puntos_colegio)} CEIPs | {len(puntos_instituto)} IES")

# ── 6. Residencias de mayores ─────────────────────────────────────────────────

print("Cargando residencias...")

puntos_residencia  = []
munis_residencia   = {}  # codigo -> plazas totales

with open(os.path.join(RAIZ, 'residencia/centros-de-caracter-social.csv'), encoding='latin-1') as f:
    reader = csv.DictReader(f, delimiter=';')
    for row in reader:
        sector = row.get('Sector', '').strip().upper()
        tipo   = row.get('Tipo', '').strip()
        if 'PERSONAS MAYORES' not in sector: continue
        tipo_up = tipo.upper()
        tipo_sin = tipo_up.replace('Í','I').replace('Ó','O').replace('Á','A').replace('É','E').replace('Ú','U')
        if 'RESIDENCIA' not in tipo_up and 'DIA' not in tipo_sin: continue
        try:
            lat = float(str(row.get('Latitud', '') or '').replace(',', '.'))
            lon = float(str(row.get('Longitud', '') or '').replace(',', '.'))
        except (ValueError, TypeError):
            continue
        # Plazas puede ser 'ASISTIDOS: 61, VÁLIDOS: 5' → sumar todos los números
        plazas = sum(int(x) for x in re.findall(r'\d+', str(row.get('Plazas', '') or '')))
        # Codigo municipioINE ya contiene el código INE completo de 5 dígitos
        cod = str(row.get('Codigo municipioINE', '')).zfill(5)
        if not cod or cod == '00000': continue
        puntos_residencia.append({'lat': lat, 'lon': lon})
        munis_residencia[cod] = munis_residencia.get(cod, 0) + plazas

print(f"  {len(puntos_residencia)} centros | {len(munis_residencia)} municipios")

# ── 7. Población extranjera ────────────────────────────────────────────────────

print("Cargando datos de nacionalidad...")

porc_extranjeros = {}

try:
    import openpyxl
    ruta_nac = os.path.join(RAIZ, 'Poblacion por edades, sexo, nacionalidad',
                             'Total de municipios de españa, sexo, edad, nacionalidad y periodo.xlsx')
    wb = openpyxl.load_workbook(ruta_nac, read_only=True, data_only=True)
    ws = wb.active
    # Estructura conocida (fila 10 contiene años, datos desde fila 11):
    # col 0  = nombre municipio con código 5 dígitos al inicio
    # col 2  = Total todas las edades 2024
    # col 12 = Extranjera todas las edades 2024
    CYL_PROV = {'05','09','24','34','37','40','42','47','49'}
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if i <= 10: continue
        if not row or not row[0]: continue
        m = re.match(r'^(\d{5})', str(row[0]).strip())
        if not m: continue
        cod = m.group(1)
        if cod[:2] not in CYL_PROV: continue
        try:
            total_2024 = float(row[2] or 0)
            ext_2024   = float(row[12] or 0)
        except (TypeError, ValueError):
            continue
        if total_2024 > 0:
            porc_extranjeros[cod] = round(ext_2024 / total_2024 * 100, 2)
    wb.close()
    print(f"  {len(porc_extranjeros)} municipios con dato de extranjeros")
except Exception as e:
    print(f"  No se pudo cargar nacionalidad: {e}")

# ── 8. Municipios únicos del GeoJSON ──────────────────────────────────────────

print("Compilando municipios únicos...")

muni_base = {}
for feat in geo['features']:
    p = feat['properties']
    cod = p['codigo']
    if cod not in muni_base:
        muni_base[cod] = p

print(f"  {len(muni_base)} municipios únicos")

# ── 9. Construir dataset ───────────────────────────────────────────────────────

print("Construyendo dataset...")

AÑOS_EVOL = list(range(1996, 2026))

filas = []
sin_geom = 0

for cod, p in muni_base.items():
    g = geom_muni.get(cod)
    if not g:
        sin_geom += 1
        continue

    lat, lon = g['lat'], g['lon']
    sup      = round(g['sup_km2'], 2)
    pob      = p.get('total', 0) or 0
    densidad = round(pob / sup, 2) if sup > 0 else 0

    # Edades
    ed       = edades.get(cod, {})
    p65      = ed.get('porc_65', None)
    ind_env  = ed.get('ind_envej', None)

    # Evolución
    ev = evolucion.get(cod, {})
    pob_2025 = pob
    pob_2020 = pob_2015 = pob_2000 = None
    tend_anual = None
    if ev:
        años  = ev.get('años', [])
        tots  = ev.get('total', [])
        def get_pob(anio):
            if anio in años: return tots[años.index(anio)]
            return None
        pob_2020 = get_pob(2020)
        pob_2015 = get_pob(2015)
        pob_2000 = get_pob(2000)
        # Tendencia: pendiente regresión lineal % anual
        if len(años) >= 2 and tots[0]:
            pct_serie = [(t/tots[0]-1)*100 for t in tots]
            tend_anual = round(regresion_pendiente(list(range(len(años))), pct_serie), 3)

    perdida_5a  = round((pob_2025 - pob_2020) / pob_2020 * 100, 2) if pob_2020 else None
    perdida_10a = round((pob_2025 - pob_2015) / pob_2015 * 100, 2) if pob_2015 else None
    perdida_25a = round((pob_2025 - pob_2000) / pob_2000 * 100, 2) if pob_2000 else None

    # Variable objetivo
    tasa_cambio  = perdida_10a
    if tasa_cambio is None:
        clase = None
    elif tasa_cambio <= -15:
        clase = 'Alta'
    elif tasa_cambio <= -5:
        clase = 'Media'
    elif tasa_cambio <= 0:
        clase = 'Leve'
    else:
        clase = 'Crecimiento'

    # Vital
    vt = vital.get(cod, {})
    if vt:
        n_media = sum(vt['nacimientos']) / len(vt['nacimientos'])
        d_media = sum(vt['defunciones']) / len(vt['defunciones'])
        tasa_nat  = round(n_media / pob * 1000, 2) if pob else None
        tasa_mort = round(d_media / pob * 1000, 2) if pob else None
        bal_vital = round((n_media - d_media) / pob * 1000, 2) if pob else None
    else:
        tasa_nat = tasa_mort = bal_vital = None

    # Renta
    rn = renta.get(cod, {})
    renta_m = rn.get('renta_media', None)

    # Subvenciones
    sv = subv.get(cod, {})
    subv_pc = None
    if sv and pob:
        subv_pc = round(sv.get('total', 0) / pob, 2)

    # Establecimientos
    est = estab.get(cod, {})
    bares_1k  = est.get('bares_1000', None)
    rest_1k   = est.get('restaurantes_1000', None)
    aloj_1k   = est.get('alojamiento_1000', None)
    tot_1k    = est.get('total_1000', None)

    # Salud
    sl = salud.get(cod, {})
    tipo_sl   = sl.get('tipo', None) if sl else None
    tiene_cs  = 1 if tipo_sl in ('cs', 'hospital', 'consultorio') else 0
    tiene_hosp= 1 if tipo_sl == 'hospital' else 0

    # Distancias salud
    dist_cs   = round(dist_minima(lat, lon, puntos_cs), 2)       if puntos_cs       else None
    dist_hosp = round(dist_minima(lat, lon, puntos_hospital), 2) if puntos_hospital  else None

    # Distancias colegios
    tiene_col = 1 if cod in munis_colegio   else 0
    tiene_ins = 1 if cod in munis_instituto else 0
    dist_col  = round(dist_minima(lat, lon, puntos_colegio),   2) if puntos_colegio   else None
    dist_ins  = round(dist_minima(lat, lon, puntos_instituto), 2) if puntos_instituto  else None

    # Residencias
    tiene_res = 1 if cod in munis_residencia else 0
    plazas_res = munis_residencia.get(cod, 0)
    plazas_res_1k = round(plazas_res / pob * 1000, 2) if pob and plazas_res else 0
    dist_res  = round(dist_minima(lat, lon, puntos_residencia), 2) if puntos_residencia else None

    # Distancia a capital de provincia
    cap = coords_capitales.get(p.get('prov_key', ''))
    dist_cap = round(haversine(lat, lon, cap['lat'], cap['lon']), 2) if cap else None

    # Extranjeros
    porc_ext = porc_extranjeros.get(cod, None)

    filas.append({
        'codigo_ine':           cod,
        'nombre':               p.get('nombre', ''),
        'provincia':            p.get('provincia', ''),
        'prov_key':             p.get('prov_key', ''),
        'poblacion':            pob,
        'superficie_km2':       sup,
        'densidad_pob':         densidad,
        'porc_65':              p65,
        'ind_envej':            ind_env,
        'porc_extranjeros':     porc_ext,
        'tasa_natalidad':       tasa_nat,
        'tasa_mortalidad':      tasa_mort,
        'balance_vital_1000':   bal_vital,
        'perdida_5a':           perdida_5a,
        'perdida_10a':          perdida_10a,
        'perdida_25a':          perdida_25a,
        'tendencia_anual':      tend_anual,
        'renta_media':          renta_m,
        'subv_per_capita':      subv_pc,
        'bares_1000':           bares_1k,
        'restaurantes_1000':    rest_1k,
        'alojamiento_1000':     aloj_1k,
        'estab_total_1000':     tot_1k,
        'tiene_cs':             tiene_cs,
        'tiene_hospital':       tiene_hosp,
        'dist_cs_km':           dist_cs,
        'dist_hospital_km':     dist_hosp,
        'tiene_colegio':        tiene_col,
        'tiene_instituto':      tiene_ins,
        'dist_colegio_km':      dist_col,
        'dist_instituto_km':    dist_ins,
        'tiene_residencia':     tiene_res,
        'plazas_residencia_1000': plazas_res_1k,
        'dist_residencia_km':   dist_res,
        'dist_capital_km':      dist_cap,
        'tasa_cambio_pob':      tasa_cambio,
        'clase_despoblacion':   clase,
    })

print(f"  {len(filas)} municipios procesados | {sin_geom} sin geometría")

# ── 10. Guardar CSV ────────────────────────────────────────────────────────────

salida = os.path.join(RESULTADOS, 'dataset_tfm.csv')
campos = list(filas[0].keys())

with open(salida, 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.DictWriter(f, fieldnames=campos)
    writer.writeheader()
    writer.writerows(filas)

# ── 11. Resumen ────────────────────────────────────────────────────────────────

print(f"\n{'='*55}")
print(f"  DATASET GENERADO: dataset_tfm.csv")
print(f"{'='*55}")
print(f"  Municipios : {len(filas)}")
print(f"  Variables  : {len(campos)}")
print(f"\n  DISTRIBUCION CLASE DESPOBLACION:")
from collections import Counter
clases = Counter(f['clase_despoblacion'] for f in filas if f['clase_despoblacion'])
for cls, n in sorted(clases.items(), key=lambda x: -x[1]):
    pct = n / sum(clases.values()) * 100
    print(f"    {cls:12s}: {n:4d} ({pct:.1f}%)")

print(f"\n  COBERTURA DE VARIABLES:")
for campo in campos[4:]:
    n_ok = sum(1 for f in filas if f[campo] is not None and f[campo] != '')
    pct  = n_ok / len(filas) * 100
    print(f"    {campo:30s}: {pct:5.1f}%")
print(f"\n  Archivo guardado en: {salida}")
