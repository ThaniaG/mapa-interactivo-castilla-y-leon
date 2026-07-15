# ═══════════════════════════════════════════════════════════════
# ¿QUÉ ES FOLIUM?
#
# Folium es una librería de Python que permite crear mapas
# interactivos sin necesidad de saber HTML ni JavaScript.
#
# Analogía: imagina que quieres construir una casa.
#   Sin folium → tienes que poner tú cada ladrillo
#                (escribir HTML, JS y CSS a mano)
#   Con folium → le dices al arquitecto lo que quieres
#                y él lo construye por ti
#
# Por debajo usa LEAFLET, que es la herramienta más popular
# del mundo para mapas web (está escrita en JavaScript).
# Folium hace la traducción automática:
#
#   TU CÓDIGO PYTHON           LO QUE GENERA FOLIUM
#   ──────────────────         ─────────────────────
#   folium.Map(...)       →    var map = L.map(...)
#   folium.GeoJson(...)   →    L.geoJson(...)
#   folium.Marker(...)    →    L.marker(...)
#
# El resultado final es un archivo .html que funciona en
# cualquier navegador sin instalar nada.
#
# ¿Por qué folium y no otras opciones?
#   - Folium  → solo necesitas Python, gratuito
#   - Leaflet → necesitas saber JavaScript
#   - Google Maps → requiere API de pago
#   - ArcGIS → software muy caro
#
# Instalación: pip install folium
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# LIBRERÍAS UTILIZADAS
#
# requests → permite hacer peticiones HTTP, es decir, descargar
#            archivos de internet desde Python
#
# folium   → genera mapas interactivos (explicado arriba)
#
# os       → permite interactuar con el sistema de archivos:
#            crear carpetas, comprobar si un archivo existe, etc.
#
# json     → permite leer y escribir archivos .json desde Python
#
# re       → módulo de expresiones regulares, lo usamos para
#            extraer los nombres de municipios del HTML del servidor
# ═══════════════════════════════════════════════════════════════
import requests
import folium
import os
import json
import re


# ═══════════════════════════════════════════════════════════════
# FUNCIÓN: descargar_nombres_municipios()
#
# ¿Qué hace?
#   Descarga los nombres oficiales de los municipios de Castilla
#   y León desde el servidor SIGPAC de la Junta (itacyl.es).
#
# ¿Cómo funciona?
#   El servidor tiene una carpeta por provincia con archivos ZIP
#   que se llaman "47001_Adalia.zip", "47002_Aguasal.zip", etc.
#   No descargamos los ZIP (son pesados), solo leemos el listado
#   HTML de la carpeta y extraemos código + nombre del archivo.
#
# ¿Por qué guardamos en disco (caché)?
#   Para no tener que conectarse a internet cada vez que ejecutas
#   el script. La primera vez descarga y guarda municipios_sigpac.json.
#   Las siguientes veces lo lee directamente del disco → más rápido.
#
# Excepción: León
#   Sus archivos son "24001.zip" sin nombre → no podemos extraer
#   el nombre del municipio. Para esos casos usará el C.P. como respaldo.
# ═══════════════════════════════════════════════════════════════
def descargar_nombres_municipios():
    ruta = "datos/municipios_sigpac.json"

    # Si el archivo ya existe en disco, lo cargamos directamente
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)

    BASE = "https://ftp.itacyl.es/cartografia/05_SIGPAC/2024_ETRS89/Parcelario_SIGPAC_CyL_Municipios/"
    carpetas = ["Avila","Burgos","Leon","Palencia","Salamanca","Segovia","Soria","Valladolid","Zamora"]
    municipios = {}

    for carpeta in carpetas:
        print(f"  Obteniendo municipios de {carpeta}...")
        r = requests.get(BASE + carpeta + "/", timeout=10)

        # Buscar en el HTML todos los archivos con formato "47001_NombreMunicipio.zip"
        # re.findall extrae todos los textos que coincidan con ese patrón
        archivos = re.findall(r'href=\"(\d{5}_[^\"]+)\.zip\"', r.text)

        for archivo in archivos:
            # Separar el código del nombre: "47001_Adalia" → "47001" y "Adalia"
            codigo, nombre = archivo.split("_", 1)
            # Los guiones en el nombre se reemplazan por espacios
            municipios[codigo] = nombre.replace("-", " ")

        if not archivos:
            print(f"    ({carpeta} sin nombres disponibles, usará código postal)")

    # Guardar en disco para no repetir la descarga la próxima vez
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(municipios, f, ensure_ascii=False)

    print(f"  ✓ {len(municipios)} municipios guardados\n")
    return municipios


# ═══════════════════════════════════════════════════════════════
# FUNCIÓN: calcular_centroide(geojson)
#
# ¿Qué hace?
#   Calcula el punto central de una provincia para colocar
#   la etiqueta con su nombre en el lugar correcto del mapa.
#
# ¿Cómo funciona?
#   Recorre todas las coordenadas [longitud, latitud] de todos
#   los polígonos del GeoJSON y calcula el promedio.
#   Eso nos da el "centro de masa" de la provincia.
#
# ¿Por qué no ponemos las coordenadas a mano?
#   Antes lo hacíamos y las etiquetas salían desplazadas porque
#   las estimábamos a ojo. Con este cálculo siempre queda centrado.
# ═══════════════════════════════════════════════════════════════
def calcular_centroide(geojson):
    lats, lons = [], []
    for feature in geojson["features"]:
        geom = feature["geometry"]
        if geom["type"] == "Polygon":
            for lon, lat in geom["coordinates"][0]:
                lats.append(lat)
                lons.append(lon)
        elif geom["type"] == "MultiPolygon":
            for poligono in geom["coordinates"]:
                for lon, lat in poligono[0]:
                    lats.append(lat)
                    lons.append(lon)
    return [sum(lats) / len(lats), sum(lons) / len(lons)]


# ═══════════════════════════════════════════════════════════════
# PASO 1: Definir las 9 provincias de Castilla y León
#
# Cada provincia es un diccionario con:
#   nombre        → nombre legible con tildes (para mostrar en el mapa)
#   archivo       → nombre del archivo GeoJSON en GitHub (mayúsculas)
#   color_relleno → color del interior de los municipios (formato hex)
#   color_borde   → color de las líneas entre municipios (más oscuro)
#
# Valladolid va al final de la lista para que se pinte encima
# de las demás provincias y sea más visible.
# ═══════════════════════════════════════════════════════════════
provincias = [
    {"nombre": "Ávila",      "archivo": "AVILA",      "color_relleno": "#cddc39", "color_borde": "#9e9d24"},
    {"nombre": "Burgos",     "archivo": "BURGOS",     "color_relleno": "#4caf50", "color_borde": "#2e7d32"},
    {"nombre": "León",       "archivo": "LEON",       "color_relleno": "#9c27b0", "color_borde": "#6a1b9a"},
    {"nombre": "Palencia",   "archivo": "PALENCIA",   "color_relleno": "#ff9800", "color_borde": "#e65100"},
    {"nombre": "Salamanca",  "archivo": "SALAMANCA",  "color_relleno": "#1565c0", "color_borde": "#0d47a1"},
    {"nombre": "Segovia",    "archivo": "SEGOVIA",    "color_relleno": "#009688", "color_borde": "#00695c"},
    {"nombre": "Soria",      "archivo": "SORIA",      "color_relleno": "#e91e63", "color_borde": "#880e4f"},
    {"nombre": "Zamora",     "archivo": "ZAMORA",     "color_relleno": "#795548", "color_borde": "#4e342e"},
    {"nombre": "Valladolid", "archivo": "VALLADOLID", "color_relleno": "#ff1744", "color_borde": "#b71c1c"},
]

# URL base del repositorio GitHub con los GeoJSON de códigos postales de España
# {} se reemplaza por el nombre del archivo (ej: VALLADOLID, BURGOS...)
URL_BASE = "https://raw.githubusercontent.com/inigoflores/ds-codigos-postales/master/data/{}.geojson"

# Crear la carpeta "datos/" si no existe para guardar los archivos descargados
os.makedirs("datos", exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# PASO 2: Descargar los GeoJSON de cada provincia
#
# GeoJSON es un formato de archivo estándar para datos geográficos.
# Contiene los polígonos (límites) de cada municipio con sus
# coordenadas y propiedades (código postal, código INE, etc.)
#
# Si el archivo ya está en la carpeta "datos/" no lo vuelve a
# descargar → ahorra tiempo y no depende de internet cada vez.
# ═══════════════════════════════════════════════════════════════
for provincia in provincias:
    ruta_local = f"datos/{provincia['archivo']}.geojson"
    if not os.path.exists(ruta_local):
        print(f"  Descargando {provincia['nombre']}...")
        datos = requests.get(URL_BASE.format(provincia["archivo"])).json()
        with open(ruta_local, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
    else:
        print(f"  (ya existe) {provincia['nombre']}")

print()


# ═══════════════════════════════════════════════════════════════
# PASO 3: Descargar nombres de municipios desde SIGPAC
#
# El GeoJSON solo tiene códigos (CODIGO_INE = 47001), no nombres.
# Aquí descargamos el diccionario código → nombre del municipio
# para poder mostrarlo en el tooltip al pasar el cursor.
# ═══════════════════════════════════════════════════════════════
municipios = descargar_nombres_municipios()


# ═══════════════════════════════════════════════════════════════
# PASO 4: Crear el mapa base con OpenStreetMap
#
# folium.Map() crea el contenedor del mapa.
#   location  → coordenadas del centro inicial [latitud, longitud]
#   zoom_start → nivel de zoom inicial (7 = ver toda Castilla y León)
#   tiles     → proveedor del mapa de fondo. "OpenStreetMap" es
#               gratuito y de código abierto. Requiere que el HTML
#               se sirva desde un servidor (Live Server en VSCode)
#               y no abrirse directamente como archivo local.
# ═══════════════════════════════════════════════════════════════
mapa = folium.Map(location=[41.65, -4.72], zoom_start=7, tiles="OpenStreetMap")


# ═══════════════════════════════════════════════════════════════
# PASO 5: Recorrer cada provincia y pintarla en el mapa
# ═══════════════════════════════════════════════════════════════
for provincia in provincias:

    # Leer el GeoJSON de esta provincia desde disco
    ruta_local = f"datos/{provincia['archivo']}.geojson"
    with open(ruta_local, "r", encoding="utf-8") as f:
        datos_geojson = json.load(f)

    # ── Enriquecer los datos ──────────────────────────────────
    # El GeoJSON original no tiene nombre de provincia ni municipio.
    # Los añadimos nosotros a cada "feature" (zona/municipio) para
    # que el tooltip pueda mostrarlos al pasar el cursor.
    for feature in datos_geojson["features"]:
        props = feature["properties"]
        # CODIGO_INE es un número (ej: 47168.0) → lo convertimos a texto de 5 dígitos
        codigo = str(int(props.get("CODIGO_INE", 0))).zfill(5)
        cp = props.get("COD_POSTAL", "")
        # Buscar el nombre en el diccionario; si no existe usar el C.P. como respaldo
        nombre_mun = municipios.get(codigo, f"C.P. {cp}")
        # Unir provincia y municipio en una sola línea para el tooltip
        props["info"] = f"{provincia['nombre']}   |   {nombre_mun}"

    # Variable que indica si estamos procesando Valladolid
    # Se usa para aplicarle un estilo diferente (más destacado)
    es_valladolid = provincia["nombre"] == "Valladolid"

    # ── Dibujar los municipios ────────────────────────────────
    # folium.GeoJson dibuja todos los polígonos del archivo GeoJSON
    # sobre el mapa y les aplica color y tooltip.
    #
    # style_function → función que devuelve el estilo de cada zona.
    #   El truco "p=provincia, vll=es_valladolid" captura los valores
    #   correctos en cada vuelta del bucle. Sin esto, todas las
    #   provincias usarían los colores de la última iteración.
    #
    # Valladolid → borde más grueso (weight:2) y más opaco (0.65)
    # El resto   → borde fino (0.8) y más transparente (0.30)
    folium.GeoJson(
        datos_geojson,
        name=provincia["nombre"],
        style_function=lambda feature, p=provincia, vll=es_valladolid: {
            "fillColor":   p["color_relleno"],
            "color":       p["color_borde"],
            "weight":      2 if vll else 0.8,
            "fillOpacity": 0.65 if vll else 0.30,
        },
        # ── Tooltip ───────────────────────────────────────────
        # Aparece al pasar el cursor por encima de cualquier municipio.
        # Muestra el campo "info" que construimos arriba.
        # labels=False → no muestra el nombre del campo, solo el valor.
        # white-space: nowrap → evita que el texto se parta en varias líneas.
        tooltip=folium.GeoJsonTooltip(
            fields=["info"],
            aliases=[""],
            sticky=True,
            labels=False,
            style=(
                "font-family: Arial, sans-serif;"
                "font-size: 13px;"
                "font-weight: bold;"
                "color: #111111;"
                "background-color: white;"
                "border: 1px solid #ccc;"
                "border-radius: 4px;"
                "padding: 6px 12px;"
                "white-space: nowrap;"
            ),
        )
    ).add_to(mapa)

    # ── Etiqueta con el nombre de la provincia ────────────────
    # Calculamos el centro real de la provincia desde los propios
    # datos del GeoJSON (promedio de todas las coordenadas).
    centro = calcular_centroide(datos_geojson)

    # folium.Marker con DivIcon permite colocar HTML puro en el mapa.
    # Es la única forma en folium de poner texto sin icono de marcador.
    # transform: translateX(-50%) centra el texto sobre las coordenadas.
    # text-shadow blanco alrededor → legible sobre cualquier color de fondo.
    # pointer-events: none → el texto no interfiere con los clics del mapa.
    folium.Marker(
        location=centro,
        icon=folium.DivIcon(
            html=f"""
                <div style="
                    font-family: Arial, sans-serif;
                    font-size: {'15px' if es_valladolid else '13px'};
                    font-weight: bold;
                    color: #111111;
                    text-shadow: 1px 1px 3px white, -1px -1px 3px white,
                                 1px -1px 3px white, -1px 1px 3px white;
                    white-space: nowrap;
                    pointer-events: none;
                    transform: translateX(-50%);
                ">
                    {provincia['nombre']}
                </div>
            """,
            icon_size=(1, 1),
            icon_anchor=(0, 0),
        )
    ).add_to(mapa)

    print(f"✓ {provincia['nombre']}")


# ═══════════════════════════════════════════════════════════════
# PASO 6: Control de capas
#
# folium.LayerControl añade el checkbox en la esquina superior
# derecha del mapa que permite mostrar u ocultar cada provincia.
# collapsed=True → aparece plegado por defecto (solo el icono)
# ═══════════════════════════════════════════════════════════════
folium.LayerControl(collapsed=True).add_to(mapa)


# ═══════════════════════════════════════════════════════════════
# PASO 7: Guardar el mapa como HTML
#
# mapa.save() genera el archivo HTML completo con todo el código
# JavaScript y CSS necesario para que el mapa funcione.
# Folium hace aquí la traducción: Python → HTML + Leaflet (JS)
#
# Para verlo correctamente abre el HTML con Live Server en VSCode
# (no doble clic directo) para que OpenStreetMap no bloquee el mapa.
# ═══════════════════════════════════════════════════════════════
mapa.save("mapa_castilla_leon.html")
print("\n✓ Mapa guardado.")

# En Jupyter Notebook esta línea muestra el mapa en la celda
mapa
