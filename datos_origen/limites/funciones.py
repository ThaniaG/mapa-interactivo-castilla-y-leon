import requests
import folium
import os
import json
import re

# ─────────────────────────────────────────────
# FUNCIÓN: descargar nombres de municipios desde SIGPAC (itacyl.es)
# Los archivos se llaman "47001_Adalia.zip" → extraemos código y nombre
# León es excepción: sus archivos son "24001.zip" sin nombre → usa C.P.
# ─────────────────────────────────────────────
def descargar_nombres_municipios():
    ruta = "datos/municipios_sigpac.json"
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)

    BASE = "https://ftp.itacyl.es/cartografia/05_SIGPAC/2024_ETRS89/Parcelario_SIGPAC_CyL_Municipios/"
    carpetas = ["Avila","Burgos","Leon","Palencia","Salamanca","Segovia","Soria","Valladolid","Zamora"]
    municipios = {}

    for carpeta in carpetas:
        print(f"  Obteniendo municipios de {carpeta}...")
        r = requests.get(BASE + carpeta + "/", timeout=10)
        archivos = re.findall(r'href=\"(\d{5}_[^\"]+)\.zip\"', r.text)
        for archivo in archivos:
            codigo, nombre = archivo.split("_", 1)
            municipios[codigo] = nombre.replace("-", " ")
        if not archivos:
            print(f"    ({carpeta} sin nombres, usará código postal como respaldo)")

    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(municipios, f, ensure_ascii=False)
    print(f"  ✓ {len(municipios)} municipios guardados\n")
    return municipios


# ─────────────────────────────────────────────
# FUNCIÓN: calcular el centro real de una provincia desde el GeoJSON
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
# PASO 1: Definir las 9 provincias de Castilla y León
# ─────────────────────────────────────────────
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

URL_BASE = "https://raw.githubusercontent.com/inigoflores/ds-codigos-postales/master/data/{}.geojson"
os.makedirs("datos", exist_ok=True)

# ─────────────────────────────────────────────
# PASO 2: Descargar GeoJSON de cada provincia si no existe
# ─────────────────────────────────────────────
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

# ─────────────────────────────────────────────
# PASO 3: Descargar nombres de municipios desde SIGPAC
# ─────────────────────────────────────────────
municipios = descargar_nombres_municipios()

# ─────────────────────────────────────────────
# PASO 4: Crear el mapa base con OpenStreetMap
# ─────────────────────────────────────────────
mapa = folium.Map(location=[41.65, -4.72], zoom_start=7, tiles="OpenStreetMap")

# ─────────────────────────────────────────────
# PASO 5: Pintar cada provincia en el mapa
# ─────────────────────────────────────────────
for provincia in provincias:

    ruta_local = f"datos/{provincia['archivo']}.geojson"
    with open(ruta_local, "r", encoding="utf-8") as f:
        datos_geojson = json.load(f)

    # Añadir a cada zona el nombre del municipio (desde SIGPAC) o C.P. como respaldo
    for feature in datos_geojson["features"]:
        props = feature["properties"]
        codigo = str(int(props.get("CODIGO_INE", 0))).zfill(5)
        cp = props.get("COD_POSTAL", "")
        nombre_mun = municipios.get(codigo, f"C.P. {cp}")
        # Construir info en una sola línea horizontal
        props["info"] = f"{provincia['nombre']}   |   {nombre_mun}"

    es_valladolid = provincia["nombre"] == "Valladolid"

    folium.GeoJson(
        datos_geojson,
        name=provincia["nombre"],
        style_function=lambda feature, p=provincia, vll=es_valladolid: {
            "fillColor":   p["color_relleno"],
            "color":       p["color_borde"],
            "weight":      2 if vll else 0.8,
            "fillOpacity": 0.65 if vll else 0.30,
        },
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

    centro = calcular_centroide(datos_geojson)

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

# ─────────────────────────────────────────────
# PASO 6: Control de capas y guardar
# ─────────────────────────────────────────────
folium.LayerControl(collapsed=True).add_to(mapa)

mapa.save("mapa_castilla_leon.html")
print("\n✓ Mapa guardado.")

mapa
