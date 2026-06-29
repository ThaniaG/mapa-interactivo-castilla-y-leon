/*
══════════════════════════════════════════════════════════
  funciones.js — Funciones de la aplicación
  Castilla y León · Datos de Población

  Contenido:
  1.  Constantes: colores por provincia y centros de etiquetas
  2.  Inicialización del mapa (Leaflet)
  3.  Inicialización del gráfico (Chart.js)
  4.  Estado global de los filtros
  5.  Funciones auxiliares (colores, filtrado, deduplicación)
  6.  Función principal: pintarMapa()
  7.  Etiquetas de nombres de provincia sobre el mapa
  8.  Leyenda del mapa
  9.  Tarjetas KPI (totales)
  10. Gráfico de barras por provincia
  11. Tabla de ranking de municipios
  12. Mostrar municipio seleccionado
  13. Título del mapa
  14. Eventos de los filtros
  15. Inicio de la aplicación

  Dependencias (deben cargarse antes en el HTML):
  - Leaflet (librería de mapas)
  - Chart.js (librería de gráficos)
  - datos_municipios.js (generado por generar_municipios_datos.py)
══════════════════════════════════════════════════════════
*/


/* ══════════════════════════════════════════
   1. CONSTANTES
   ══════════════════════════════════════════ */

/*
  Coordenadas del centro de cada provincia.
  Se usan para colocar el nombre de la provincia sobre el mapa.
*/
const CENTROS_PROVINCIA = {
    avila:      [40.50, -4.85],
    burgos:     [42.20, -3.60],
    leon:       [42.65, -5.80],
    palencia:   [42.15, -4.60],
    salamanca:  [40.75, -5.95],
    segovia:    [41.00, -3.90],
    soria:      [41.50, -2.60],
    valladolid: [41.55, -4.50],
    zamora:     [41.55, -5.85],
};

/*
  Color distinto por provincia — se usa en el gráfico de barras,
  en la tabla de ranking y en las etiquetas del mapa.
*/
const COLORES_PROVINCIA = {
    avila:      '#e53935',
    burgos:     '#fb8c00',
    leon:       '#c0a800',
    palencia:   '#43a047',
    salamanca:  '#00897b',
    segovia:    '#1e88e5',
    soria:      '#8e24aa',
    valladolid: '#7b2d42',
    zamora:     '#6d4c41',
};

/*
  Nombres legibles de cada provincia.
*/
const NOMBRES_PROVINCIA = {
    avila:      'Ávila',
    burgos:     'Burgos',
    leon:       'León',
    palencia:   'Palencia',
    salamanca:  'Salamanca',
    segovia:    'Segovia',
    soria:      'Soria',
    valladolid: 'Valladolid',
    zamora:     'Zamora',
};

/*
  Funciones para generar tonos del color de cada provincia.
  Permiten pasar del color claro (poca población) al color oscuro (mucha población)
  usando el mismo color base de la provincia.

  hexARgb(): convierte un color hexadecimal (#e53935) a sus componentes RGB (229, 57, 53)
  mezclarConBlanco(): mezcla un color con blanco según un factor (0=blanco, 1=color puro)
  generarTonos(): genera n tonos de un color base, de claro a oscuro
*/
function hexARgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return [r, g, b];
}

function mezclarConBlanco(hex, factor) {
    // factor 0.0 → blanco puro, factor 1.0 → color puro
    const [r, g, b] = hexARgb(hex);
    const nr = Math.round(255 + (r - 255) * factor);
    const ng = Math.round(255 + (g - 255) * factor);
    const nb = Math.round(255 + (b - 255) * factor);
    return `rgb(${nr},${ng},${nb})`;
}

function generarTonos(colorBase, n) {
    // Genera n tonos desde muy claro (15% del color) hasta el color completo
    const tonos = [];
    for (let i = 0; i < n; i++) {
        const factor = 0.15 + (0.85 * i / (n - 1));
        tonos.push(mezclarConBlanco(colorBase, factor));
    }
    return tonos;
}

// Colores por categoría turística (fuente: Junta de CyL)
const COLORES_TURISMO = {
    'Museo':                     '#ff9800',
    'Castillos':                 '#6d4c41',
    'Iglesias y Ermitas':        '#5c6bc0',
    'Monasterios':               '#7b1fa2',
    'Palacios':                  '#c62828',
    'Yacimientos arqueológicos': '#827717',
    'Catedrales':                '#1565c0',
    'Murallas y puertas':        '#37474f',
    'Torres':                    '#455a64',
    'Puentes':                   '#00695c',
};

// Referencia a la capa de puntos turísticos
let capaTurismo = null;

// Referencia a la capa de red viaria
let capaRedViaria = null;

// Referencia a la capa de naturaleza
let capaNaturaleza = null;

// Referencia a la capa de reciclaje
let capaReciclaje = null;

// Colores y etiquetas para la capa de puntos de establecimientos
const COLORES_ESTAB = {
    bares:        '#f59e0b',
    restaurantes: '#10b981',
    cafeterias:   '#92400e',
    alojamiento:  '#3b82f6',
};
const LABELS_ESTAB = {
    bares:        'Bares',
    restaurantes: 'Restaurantes',
    cafeterias:   'Cafeterías',
    alojamiento:  'Alojamiento',
};

// Referencia a la capa de puntos de establecimientos
let capaPuntosEstab = null;

// Colores y etiquetas para cobertura sanitaria (variable coroplética)
const COLORES_SALUD = {
    hospital:     '#c0392b',
    centro_salud: '#1565c0',
    consultorio:  '#27ae60',
    asignado:     '#b0bec5',
    sin_datos:    '#eceff1',
};
const LABELS_SALUD = {
    hospital:     'Hospital',
    centro_salud: 'Centro de Salud',
    consultorio:  'Consultorio Local',
    asignado:     'Asignado a CS externo',
    sin_datos:    'Sin datos',
};

// Referencia a la capa de puntos de salud
let capaPuntosSalud = null;

// Colores y etiquetas para clústeres K-Means (variable coroplética categórica)
const COLORES_KMEANS = {
    1: '#d73027',   // C1 Despoblación severa  — rojo
    2: '#fc8d59',   // C2 Despoblación moderada — naranja
    3: '#91cf60',   // C3 Crecimiento moderado  — verde claro
    4: '#1a9850',   // C4 Crecimiento alto      — verde oscuro
    0: '#cccccc',   // Sin datos
};
const NOMBRES_KMEANS = {
    1: 'C1 · Despoblación severa',
    2: 'C2 · Despoblación moderada',
    3: 'C3 · Crecimiento moderado',
    4: 'C4 · Crecimiento alto',
};

// Etiquetas legibles del campo de sexo
const ETIQUETAS_SEXO = {
    total:   'Total',
    hombres: 'Hombres',
    mujeres: 'Mujeres'
};

// Límites geográficos de Castilla y León (evita que el mapa se aleje demasiado)
const LIMITES_CYL = L.latLngBounds([38.5, -7.5], [44.0, -1.0]);


/* ══════════════════════════════════════════
   2. INICIALIZACIÓN DEL MAPA (Leaflet)
   El mapa se centra y restringe a Castilla y León.
   ══════════════════════════════════════════ */

const map = L.map('map', {
    center: [41.65, -4.72],
    zoom: 7,
    zoomControl: true,
    maxBounds: LIMITES_CYL,      // No permite alejarse de Castilla y León
    maxBoundsViscosity: 0.8,     // El borde actúa como una goma elástica
    minZoom: 6,
});

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    className: 'osm-tiles'       // Aplica el filtro de color definido en style.css
}).addTo(map);


/* ══════════════════════════════════════════
   3. INICIALIZACIÓN DEL GRÁFICO (Chart.js)
   Gráfico de barras horizontales que muestra
   la población total por provincia.
   ══════════════════════════════════════════ */

const ctxGrafico = document.getElementById('chart-top').getContext('2d');
const graficoPoblacion = new Chart(ctxGrafico, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: 'Población',
            data: [],
            backgroundColor: [],
            borderRadius: 4,
            borderSkipped: false,
        }]
    },
    options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: ctx => ' ' + ctx.parsed.x.toLocaleString('es-ES') + ' hab.'
                }
            }
        },
        scales: {
            x: {
                ticks: {
                    font: { size: 10 },
                    callback: v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'k' : v
                },
                grid: { color: '#f0f4f8' }
            },
            y: {
                ticks: { font: { size: 11 } },
                grid: { display: false }
            }
        }
    }
});


const ctxGrafico2 = document.getElementById('chart-top2').getContext('2d');
const graficoPoblacion2 = new Chart(ctxGrafico2, {
    type: 'bar',
    data: {
        labels: [],
        datasets: [{
            label: 'Cambio',
            data: [],
            backgroundColor: [],
            borderRadius: 4,
            borderSkipped: false,
        }]
    },
    options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                callbacks: {
                    label: ctx => {
                        const v = ctx.parsed.x;
                        return v < 0 ? ` Pérdida: ${Math.abs(v).toFixed(1)}%` : ` Ganancia: +${v.toFixed(1)}%`;
                    }
                }
            }
        },
        scales: {
            x: {
                ticks: { font: { size: 10 }, callback: v => v.toFixed(0) + '%' },
                grid: { color: '#f0f4f8' }
            },
            y: {
                ticks: { font: { size: 11 } },
                grid: { display: false }
            }
        }
    }
});


/* ══════════════════════════════════════════
   4. ESTADO GLOBAL DE LOS FILTROS
   Guarda qué filtros tiene activos el usuario.
   ══════════════════════════════════════════ */

const estado = {
    sexo:           'total',
    provincia:      'todas',
    intervalos:     5,
    variable:       'poblacion',
    anio_subv:      'total',
    anio_vital:     '2024',
    anio_base_desp: '2000',
    tipo_estab:     'total',
    turismo:        false,
    estab_puntos:   false,
    salud_puntos:   false,
    red_viaria:     false,
    naturaleza:     false,
    reciclaje:      false,
    jenny_algo:     'kmeans',
    jenny_met:      'mm',
    jenny_k:        4,
};

// Capa de bordes de provincia (visible solo en modo "Todas")
const capaProvincias = L.geoJson(DATOS_PROVINCIAS, {
    style: feature => ({
        fillColor:   'transparent',
        fillOpacity: 0,
        color:  feature.properties.prov_key === 'valladolid' ? '#7b2d42' : '#2d3f50',
        weight: feature.properties.prov_key === 'valladolid' ? 1.8 : 0.8,
    }),
    interactive: false,
}).addTo(map);

// Referencia a la capa GeoJSON activa (se guarda para poder eliminarla al redibujar)
let capaGeo = null;

// Referencia a la capa de etiquetas de provincia
let capaEtiquetas = null;



/* ══════════════════════════════════════════
   5. FUNCIONES AUXILIARES
   ══════════════════════════════════════════ */

/*
  getMunicipiosSinDuplicados()
  El GeoJSON puede tener varios polígonos con el mismo código INE
  (por ejemplo, distintos barrios de una misma ciudad). Esta función
  devuelve solo un registro por municipio para que los datos no se dupliquen
  en el gráfico, la tabla y los KPIs.

  Aplica también el filtro de provincia activo.
*/
function getMunicipiosSinDuplicados(soloProvinciaActiva = true) {
    const vistos = {};

    DATOS_GEO.features.forEach(f => {
        const p = f.properties;
        if (soloProvinciaActiva && estado.provincia !== 'todas' && p.prov_key !== estado.provincia) return;
        if (!vistos[p.codigo]) {
            vistos[p.codigo] = { ...p };
        }
    });

    return Object.values(vistos);
}

/*
  calcularBreaks()
  Divide los valores en n grupos iguales (cuantiles) para el mapa de coropletas.
  Devuelve los límites de cada intervalo.
*/
function calcularBreaks(valores, n, incluirNegativos = false) {
    const ordenados = [...valores].filter(v => incluirNegativos ? v !== 0 : v > 0).sort((a, b) => a - b);
    const breaks = [];
    for (let i = 0; i <= n; i++) {
        const idx = Math.round((i / n) * (ordenados.length - 1));
        breaks.push(ordenados[idx] || 0);
    }
    return breaks;
}

/*
  getColorCoropleta()
  Devuelve el color que le corresponde a un municipio
  según su valor de población y los límites calculados.
*/
function getColorCoropleta(valor, breaks, paleta) {
    for (let i = paleta.length - 1; i >= 0; i--) {
        if (valor >= breaks[i]) return paleta[i];
    }
    return paleta[0];
}

/*
  getValorVariable()
  Devuelve el valor de la variable activa para un municipio dado.
  Para "poblacion" usa los campos del GeoJSON; para variables de edad
  consulta DATOS_EDADES usando el código INE del municipio.
*/
function getValorVariable(props) {
    if (estado.variable === 'poblacion') return props[estado.sexo] || 0;
    if (estado.variable === 'renta_media') {
        const renta = (typeof DATOS_RENTA !== 'undefined') && DATOS_RENTA[props.codigo];
        return renta ? renta.renta_media : 0;
    }
    if (estado.variable === 'subvenciones') {
        const subv = (typeof DATOS_SUBVENCIONES !== 'undefined') && DATOS_SUBVENCIONES[props.codigo];
        if (!subv) return 0;
        return estado.anio_subv === 'total' ? subv.total : (subv.por_anio[estado.anio_subv] || 0);
    }
    if (estado.variable === 'establecimientos') {
        const estab = (typeof DATOS_ESTABLECIMIENTOS !== 'undefined') && DATOS_ESTABLECIMIENTOS[props.codigo];
        if (!estab) return 0;
        return estab[estado.tipo_estab + '_1000'] || 0;
    }
    if (estado.variable === 'cobertura_salud') {
        const salud = (typeof DATOS_SALUD !== 'undefined') && DATOS_SALUD[props.codigo];
        return salud ? salud.nivel_salud : -1;
    }
    if (estado.variable === 'kmeans') {
        const clave = `${estado.jenny_algo}_${estado.jenny_met}_${estado.jenny_k}`;
        const datos = (typeof DATOS_JENNY !== 'undefined') && DATOS_JENNY[clave];
        return datos ? (datos[props.codigo] ?? -1) : -1;
    }
    if (estado.variable === 'despoblacion') {
        const ev = (typeof DATOS_EVOLUCION !== 'undefined') && DATOS_EVOLUCION[props.codigo];
        if (!ev) return 0;
        const idxBase = ev.años.indexOf(parseInt(estado.anio_base_desp));
        const idx2025 = ev.años.indexOf(2025);
        if (idxBase === -1 || idx2025 === -1) return 0;
        const popBase = ev.total[idxBase];
        const pop2025 = ev.total[idx2025];
        if (!popBase) return 0;
        return Math.max(0, (popBase - pop2025) / popBase * 100);
    }
    if (['nacimientos', 'defunciones', 'balance_vital'].includes(estado.variable)) {
        const vt = (typeof DATOS_VITAL !== 'undefined') && DATOS_VITAL[props.codigo];
        if (!vt) return 0;
        const idx = vt.años.indexOf(parseInt(estado.anio_vital));
        if (idx === -1) return 0;
        if (estado.variable === 'nacimientos')   return vt.nacimientos[idx];
        if (estado.variable === 'defunciones')   return vt.defunciones[idx];
        if (estado.variable === 'balance_vital') return vt.balance[idx];
    }
    const edades = (typeof DATOS_EDADES !== 'undefined') && DATOS_EDADES[props.codigo];
    if (!edades) return 0;
    const sufijo = estado.sexo === 'hombres' ? '_h' : estado.sexo === 'mujeres' ? '_m' : '';
    return edades[estado.variable + sufijo] || 0;
}


/* ══════════════════════════════════════════
   6. FUNCIÓN PRINCIPAL: pintarMapa()
   Redibuja el mapa completo según los filtros activos.

   Modo "Todas las provincias":
     cada provincia tiene un color distinto para distinguirlas.

   Modo "Una provincia":
     se usa una escala de azules según la población de cada municipio.
   ══════════════════════════════════════════ */

function pintarMapa() {
    const n         = estado.intervalos;
    const modoTodas = estado.provincia === 'todas';

    // Calcular breaks usando todos los municipios para escala consistente
    const todosMunicipios = getMunicipiosSinDuplicados(false);
    const valores = todosMunicipios.map(p => getValorVariable(p));
    const breaks  = calcularBreaks(valores, n, estado.variable === 'balance_vital');

    // Municipios filtrados (para KPIs y gráfico)
    const municipiosFiltrados = getMunicipiosSinDuplicados();

    // Tonos de color para Valladolid (azul) y para el resto (gris)
    const tonosValladolid = generarTonos('#7b2d42', n);
    const tonosGris       = generarTonos('#8a9baa', n);

    // Eliminar capa anterior
    if (capaGeo) map.removeLayer(capaGeo);

    // Pre-calcular tamaño de cada clúster para detectar municipios outlier (singleton)
    let tamanoCluster = {};
    if (estado.variable === 'kmeans') {
        const _clave = `${estado.jenny_algo}_${estado.jenny_met}_${estado.jenny_k}`;
        const _datos = (typeof DATOS_JENNY !== 'undefined') && DATOS_JENNY[_clave];
        if (_datos) Object.values(_datos).forEach(cl => { tamanoCluster[cl] = (tamanoCluster[cl] || 0) + 1; });
    }

    capaGeo = L.geoJson(DATOS_GEO, {

        style: feature => {
            const p = feature.properties;

            // Cobertura sanitaria: colores categóricos fijos, ignora cuantiles
            if (estado.variable === 'cobertura_salud') {
                if (!modoTodas && p.prov_key !== estado.provincia) {
                    return { fillColor: 'transparent', fillOpacity: 0, color: 'transparent', weight: 0 };
                }
                const s = (typeof DATOS_SALUD !== 'undefined') && DATOS_SALUD[p.codigo];
                const tipo = s ? s.tipo : 'sin_datos';
                return {
                    fillColor:   COLORES_SALUD[tipo] || COLORES_SALUD.sin_datos,
                    fillOpacity: 0.85,
                    color:       '#ffffff',
                    weight:      0.4,
                    fillRule:    'nonzero',
                };
            }

            // K-Means / K-Medoids: colores categóricos por clúster (datos de Jenny)
            if (estado.variable === 'kmeans') {
                if (!modoTodas && p.prov_key !== estado.provincia) {
                    return { fillColor: 'transparent', fillOpacity: 0, color: 'transparent', weight: 0 };
                }
                const clave = `${estado.jenny_algo}_${estado.jenny_met}_${estado.jenny_k}`;
                const datos = (typeof DATOS_JENNY !== 'undefined') && DATOS_JENNY[clave];
                const cl    = datos ? (datos[p.codigo] ?? -1) : -1;
                const esOutlier = cl >= 0 && tamanoCluster[cl] === 1;
                const paleta = ['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00','#a65628','#f781bf','#666666','#00ced1','#e6ab02'];
                return {
                    fillColor:   esOutlier ? '#ffd700' : (cl >= 0 ? paleta[cl % paleta.length] : '#cccccc'),
                    fillOpacity: esOutlier ? 1.0 : 0.88,
                    color:       esOutlier ? '#333333' : '#ffffff',
                    weight:      esOutlier ? 1.5 : 0.4,
                    fillRule:    'nonzero',
                };
            }

            if (modoTodas) {
                // Modo todas: Valladolid en guindo, resto en gris — ambos con coropleta de la variable activa
                const tonos = p.prov_key === 'valladolid' ? tonosValladolid : tonosGris;
                return {
                    fillColor:   getColorCoropleta(getValorVariable(p), breaks, tonos),
                    fillOpacity: 0.80,
                    color:       '#ffffff',
                    weight:      0.4,
                    fillRule:    'nonzero',
                };
            }

            // Modo provincia concreta: la seleccionada en su color, resto invisible
            if (p.prov_key !== estado.provincia) {
                return { fillColor: 'transparent', fillOpacity: 0, color: 'transparent', weight: 0 };
            }

            const colorProv = COLORES_PROVINCIA[p.prov_key] || '#999999';
            const tonos = generarTonos(colorProv, n);
            return {
                fillColor:   getColorCoropleta(getValorVariable(p), breaks, tonos),
                fillOpacity: 0.80,
                color:       colorProv,
                weight:      0.6,
                fillRule:    'nonzero',
            };
        },

        onEachFeature: (feature, layer) => {
            const p = feature.properties;

            // Sin interactividad para municipios de otras provincias
            if (!modoTodas && p.prov_key !== estado.provincia) return;

            const val = getValorVariable(p);
            const valStr = estado.variable === 'poblacion'
                ? val.toLocaleString('es-ES') + ' hab.'
                : estado.variable === 'porc_65'
                    ? val.toFixed(1) + '% ≥65 años'
                    : estado.variable === 'ind_envej'
                        ? 'Índice env.: ' + val.toFixed(1)
                        : estado.variable === 'subvenciones'
                            ? val.toLocaleString('es-ES') + ' € (subv.)'
                            : estado.variable === 'kmeans'
                                ? (() => { const clave = `${estado.jenny_algo}_${estado.jenny_met}_${estado.jenny_k}`; const datos = (typeof DATOS_JENNY !== 'undefined') && DATOS_JENNY[clave]; const cl = datos ? datos[p.codigo] : undefined; return cl !== undefined ? `C${cl+1}` : 'Sin datos'; })()
                            : estado.variable === 'cobertura_salud'
                                ? (() => { const s = (typeof DATOS_SALUD !== 'undefined') && DATOS_SALUD[p.codigo]; return LABELS_SALUD[s ? s.tipo : 'sin_datos']; })()
                                : estado.variable === 'nacimientos'
                                    ? val.toLocaleString('es-ES') + ' nacimientos'
                                    : estado.variable === 'defunciones'
                                        ? val.toLocaleString('es-ES') + ' defunciones'
                                        : estado.variable === 'balance_vital'
                                            ? (val >= 0 ? '+' : '') + val.toLocaleString('es-ES') + ' balance'
                                            : estado.variable === 'despoblacion'
                                                ? (() => {
                                                    const ev = (typeof DATOS_EVOLUCION !== 'undefined') && DATOS_EVOLUCION[p.codigo];
                                                    if (!ev) return 'Sin datos';
                                                    const idxBase = ev.años.indexOf(parseInt(estado.anio_base_desp));
                                                    const idx2025 = ev.años.indexOf(2025);
                                                    if (idxBase === -1 || idx2025 === -1) return 'Sin datos';
                                                    const diff = ev.total[idx2025] - ev.total[idxBase];
                                                    const pct  = ev.total[idxBase] ? (diff / ev.total[idxBase] * 100) : 0;
                                                    return (pct >= 0 ? '+' : '') + pct.toFixed(1) + '% desde ' + estado.anio_base_desp;
                                                })()
                                                : val.toLocaleString('es-ES') + ' €';
            layer.bindTooltip(
                `<strong>${p.nombre}</strong><br>${p.provincia}<br>${valStr}`,
                { sticky: true, className: 'mapa-tooltip' }
            );

            layer.on({
                click:     () => { if (!estado.turismo) mostrarMunicipio(p); },
                mouseover: e  => { if (!estado.turismo) e.target.setStyle({ weight: 2, color: '#333', fillOpacity: 0.95 }); },
                mouseout:  e  => { if (!estado.turismo) capaGeo.resetStyle(e.target); },
            });
        }

    }).addTo(map);

    // Mostrar bordes de provincia solo en modo "Todas" y traerlos al frente
    if (modoTodas) {
        if (!map.hasLayer(capaProvincias)) capaProvincias.addTo(map);
        capaProvincias.bringToFront();
    } else {
        if (map.hasLayer(capaProvincias)) map.removeLayer(capaProvincias);
    }

    actualizarEtiquetasProvincias();
    actualizarLeyenda(breaks);
    actualizarKPIs(municipiosFiltrados);
    actualizarGrafico();
    actualizarTituloMapa();
    actualizarPanelDerecho();
}


/* ══════════════════════════════════════════
   7. ETIQUETAS DE NOMBRE DE PROVINCIA
   Muestra el nombre de cada provincia sobre el mapa.
   Solo se muestran cuando el filtro es "Todas".
   Al filtrar por una provincia desaparecen porque
   ya no hace falta indicar cuál es.
   ══════════════════════════════════════════ */

function actualizarEtiquetasProvincias() {
    if (capaEtiquetas) map.removeLayer(capaEtiquetas);

    // Si hay una provincia seleccionada, mostrar solo su etiqueta
    // Si se ven todas, mostrar todas las etiquetas
    const provinciasMostrar = estado.provincia === 'todas'
        ? Object.keys(CENTROS_PROVINCIA)
        : [estado.provincia];

    capaEtiquetas = L.layerGroup();

    provinciasMostrar.forEach(clave => {
        const coords = CENTROS_PROVINCIA[clave];
        const etiqueta = L.marker(coords, {
            icon: L.divIcon({
                className: '',
                html: `<div style="
                    color: #1a2a3a;
                    font-size: 13px;
                    font-weight: 700;
                    white-space: nowrap;
                    font-family: Inter, sans-serif;
                    text-shadow:
                        -1px -1px 0 #fff,
                         1px -1px 0 #fff,
                        -1px  1px 0 #fff,
                         1px  1px 0 #fff,
                         0 0 6px #fff;
                ">${NOMBRES_PROVINCIA[clave]}</div>`,
                iconAnchor: [0, 0],
            }),
            interactive: false,
        });
        capaEtiquetas.addLayer(etiqueta);
    });

    capaEtiquetas.addTo(map);
}


/* ══════════════════════════════════════════
   8. LEYENDA DEL MAPA
   Siempre muestra los rangos de población
   con los colores de la coropleta.
   ══════════════════════════════════════════ */

function actualizarLeyenda(breaks) {
    const legend = document.getElementById('map-legend');
    const n      = estado.intervalos;

    // En modo "Todas las provincias": mostrar los rangos de población con una escala de gris
    // En modo "Una provincia": mostrar los tonos del color de esa provincia
    const colorEjemplo = estado.provincia === 'todas'
        ? '#64748b'   // Gris neutro para representar todos
        : COLORES_PROVINCIA[estado.provincia] || '#64748b';

    const tonos = generarTonos(colorEjemplo, n);

    const sufSexo = estado.sexo !== 'total' ? ` · ${ETIQUETAS_SEXO[estado.sexo]}` : '';
    const ETIQUETAS_TIPO_ESTAB = { total: 'Todos', bares: 'Bares', restaurantes: 'Restaurantes', cafeterias: 'Cafeterías', alojamiento: 'Alojamiento' };
    const TITULOS_VAR = {
        poblacion:        `Habitantes · ${ETIQUETAS_SEXO[estado.sexo]}`,
        porc_65:          `% Mayores de 65${sufSexo}`,
        ind_envej:        `Índice de envejecimiento${sufSexo}`,
        renta_media:      'Renta media por persona (€)',
        subvenciones:     'Subvenciones recibidas 2022-2025 (€)',
        establecimientos: `Establecimientos turísticos · ${ETIQUETAS_TIPO_ESTAB[estado.tipo_estab]} (por 1.000 hab.)`,
        cobertura_salud:  'Cobertura sanitaria',
        nacimientos:      `Nacimientos · ${estado.anio_vital}`,
        defunciones:      `Defunciones · ${estado.anio_vital}`,
        balance_vital:    `Balance vegetativo · ${estado.anio_vital}`,
        despoblacion:     `Despoblación desde ${estado.anio_base_desp} (%)`,
        kmeans:           'K-Means · Clústeres demográficos',
    };
    const formatBreak = v => {
        if (estado.variable === 'poblacion') return (v ?? 0).toLocaleString('es-ES');
        if (estado.variable === 'renta_media' || estado.variable === 'subvenciones')
            return (v ?? 0).toLocaleString('es-ES') + ' €';
        if (['nacimientos', 'defunciones', 'balance_vital'].includes(estado.variable))
            return Math.round(v ?? 0).toLocaleString('es-ES');
        if (estado.variable === 'despoblacion') return (v ?? 0).toFixed(1) + '%';
        return (v ?? 0).toFixed(1);
    };

    // Leyenda categórica para clústeres (datos de Jenny)
    if (estado.variable === 'kmeans') {
        const algoNombre = estado.jenny_algo === 'kmeans' ? 'K-Means' : 'K-Medoids';
        const metNombre  = {mm:'Min-Max', z:'Z-score', rel:'Relativa', corr:'Correlación'}[estado.jenny_met] || estado.jenny_met;
        const k = estado.jenny_k;
        const ETIQUETAS_K = {
            2: ['Mayor despoblación', 'Menor despoblación'],
            3: ['Mayor despoblación', 'Despoblación moderada', 'Menor despoblación'],
            4: ['Mayor despoblación', 'Despoblación moderada', 'Crecimiento moderado', 'Menor despoblación'],
            5: ['Mayor despoblación', 'Despoblación alta', 'Despoblación media', 'Crecimiento moderado', 'Menor despoblación'],
            6: ['Mayor despoblación', 'Despoblación alta', 'Despoblación media', 'Estable', 'Crecimiento moderado', 'Menor despoblación'],
        };
        const etiquetas = ETIQUETAS_K[k] || Array.from({length: k}, (_, i) => i === 0 ? 'Mayor despoblación' : i === k-1 ? 'Menor despoblación' : `Grupo ${i+1}`);
        let html = `<div class="legend-title">${algoNombre} · ${metNombre} · K=${k}</div>`;
        const paleta = ['#e41a1c','#377eb8','#4daf4a','#984ea3','#ff7f00','#a65628','#f781bf','#666666','#00ced1','#e6ab02'];
        // Calcular tamaños de clúster para marcar outliers en la leyenda
        const claveL = `${estado.jenny_algo}_${estado.jenny_met}_${estado.jenny_k}`;
        const datosL = (typeof DATOS_JENNY !== 'undefined') && DATOS_JENNY[claveL];
        const tamL   = {};
        if (datosL) Object.values(datosL).forEach(cl => { tamL[cl] = (tamL[cl] || 0) + 1; });
        for (let i = 0; i < k; i++) {
            const esOutlierL = tamL[i] === 1;
            const color  = esOutlierL ? '#ffd700' : paleta[i];
            const borde  = esOutlierL ? 'border:1.5px solid #333;' : '';
            const label  = esOutlierL ? 'Caso atípico (1 mun.)' : `C${i+1}`;
            html += `<div class="legend-item"><div class="legend-color" style="background:${color};${borde}"></div><span class="legend-label">${label}</span></div>`;
        }
        legend.innerHTML = html;
        return;
    }

    // Leyenda categórica para cobertura sanitaria
    if (estado.variable === 'cobertura_salud') {
        let html = `<div class="legend-title">Cobertura sanitaria</div>`;
        [['hospital','Hospital'],['centro_salud','Centro de Salud'],['consultorio','Consultorio Local'],['asignado','Asignado (CS externo)'],['sin_datos','Sin datos']].forEach(([tipo, label]) => {
            html += `<div class="legend-item"><div class="legend-color" style="background:${COLORES_SALUD[tipo]}"></div><span class="legend-label">${label}</span></div>`;
        });
        legend.innerHTML = html;
        return;
    }

    let html = `<div class="legend-title">${TITULOS_VAR[estado.variable] || 'Valor'}</div>`;
    for (let i = 0; i < n; i++) {
        const desde = formatBreak(breaks[i]);
        const hasta = formatBreak(breaks[i+1]);
        html += `
            <div class="legend-item">
                <div class="legend-color" style="background:${tonos[i]}"></div>
                <span class="legend-label">${desde} – ${hasta}</span>
            </div>`;
    }

    legend.innerHTML = html;
}


/* ══════════════════════════════════════════
   9. TARJETAS KPI
   Suma la población de los municipios visibles
   y actualiza las 3 tarjetas: Total, Hombres, Mujeres.
   ══════════════════════════════════════════ */

function actualizarKPIs(municipios) {
    const suma = campo => municipios.reduce((acc, m) => acc + m[campo], 0);
    document.getElementById('kpi-total').textContent   = suma('total').toLocaleString('es-ES');
    document.getElementById('kpi-hombres').textContent = suma('hombres').toLocaleString('es-ES');
    document.getElementById('kpi-mujeres').textContent = suma('mujeres').toLocaleString('es-ES');
    const titulo = estado.provincia === 'todas'
        ? 'Castilla y León · Totales'
        : `${NOMBRES_PROVINCIA[estado.provincia]} · Totales`;
    document.getElementById('kpi-titulo').textContent = titulo;
}


/* ══════════════════════════════════════════
   10. GRÁFICO: POBLACIÓN POR PROVINCIA
   Muestra la población de cada provincia en barras.
   Siempre muestra las 9 provincias para comparar.

   Cuando se añadan más años, este gráfico podrá
   evolucionar a mostrar la evolución por año.
   ══════════════════════════════════════════ */

function actualizarGrafico() {
    if (estado.variable === 'despoblacion' && typeof DATOS_EVOLUCION !== 'undefined') {
        const anioBase = parseInt(estado.anio_base_desp);

        // Media de % cambio por municipio (cada municipio cuenta igual, sin ponderar por tamaño)
        const sumaPct = {}, conteo = {};
        Object.keys(NOMBRES_PROVINCIA).forEach(k => { sumaPct[k] = 0; conteo[k] = 0; });
        const vistos = {};
        DATOS_GEO.features.forEach(f => {
            const p = f.properties;
            if (vistos[p.codigo]) return;
            vistos[p.codigo] = true;
            const ev = DATOS_EVOLUCION[p.codigo];
            if (!ev || sumaPct[p.prov_key] === undefined) return;
            const idxBase = ev.años.indexOf(anioBase);
            const idx2025 = ev.años.indexOf(2025);
            if (idxBase === -1 || idx2025 === -1) return;
            const base = ev.total[idxBase];
            if (!base) return;
            sumaPct[p.prov_key] += (ev.total[idx2025] - base) / base * 100;
            conteo[p.prov_key]++;
        });

        // % cambio medio por municipio: positivo = creció, negativo = perdió población
        const pctCambio = {};
        Object.keys(NOMBRES_PROVINCIA).forEach(k => {
            pctCambio[k] = conteo[k] > 0 ? sumaPct[k] / conteo[k] : 0;
        });

        // Ordenar de más pérdida (negativo) a más ganancia (positivo)
        const ordenadas = Object.entries(pctCambio).sort((a, b) => a[1] - b[1]);

        document.getElementById('titulo-grafico-prov').textContent = `Despoblación municipal media · ${anioBase}–2025`;
        graficoPoblacion.data.labels                      = ordenadas.map(([k]) => NOMBRES_PROVINCIA[k]);
        graficoPoblacion.data.datasets[0].data            = ordenadas.map(([, v]) => +v.toFixed(1));
        graficoPoblacion.data.datasets[0].backgroundColor = ordenadas.map(([, v]) => v < 0 ? '#e53935' : '#43a047');
        graficoPoblacion.options.plugins.tooltip.callbacks.label = ctx => {
            const v = ctx.parsed.x;
            return v < 0 ? ` Pérdida: ${Math.abs(v).toFixed(1)}%` : ` Ganancia: +${v.toFixed(1)}%`;
        };
        graficoPoblacion.options.scales.x.ticks.callback = v => v.toFixed(0) + '%';
        graficoPoblacion.update();

        // Segundo gráfico: cambio total agregado por provincia
        const popBase2 = {}, pop2025b = {};
        Object.keys(NOMBRES_PROVINCIA).forEach(k => { popBase2[k] = 0; pop2025b[k] = 0; });
        const vistos2 = {};
        DATOS_GEO.features.forEach(f => {
            const p = f.properties;
            if (vistos2[p.codigo]) return;
            vistos2[p.codigo] = true;
            const ev = DATOS_EVOLUCION[p.codigo];
            if (!ev || popBase2[p.prov_key] === undefined) return;
            const idxBase = ev.años.indexOf(anioBase);
            const idx2025 = ev.años.indexOf(2025);
            if (idxBase === -1 || idx2025 === -1) return;
            popBase2[p.prov_key]  += ev.total[idxBase];
            pop2025b[p.prov_key]  += ev.total[idx2025];
        });
        const pctTotal = {};
        Object.keys(NOMBRES_PROVINCIA).forEach(k => {
            pctTotal[k] = popBase2[k] > 0 ? (pop2025b[k] - popBase2[k]) / popBase2[k] * 100 : 0;
        });
        const ordenadas2 = Object.entries(pctTotal).sort((a, b) => a[1] - b[1]);

        document.getElementById('seccion-grafico-prov2').style.display = '';
        document.getElementById('titulo-grafico-prov2').textContent = `Cambio total de población · ${anioBase}–2025`;
        graficoPoblacion2.data.labels                      = ordenadas2.map(([k]) => NOMBRES_PROVINCIA[k]);
        graficoPoblacion2.data.datasets[0].data            = ordenadas2.map(([, v]) => +v.toFixed(1));
        graficoPoblacion2.data.datasets[0].backgroundColor = ordenadas2.map(([, v]) => v < 0 ? '#e53935' : '#43a047');
        graficoPoblacion2.update();
        return;
    }

    // Modo normal: población por provincia
    document.getElementById('seccion-grafico-prov2').style.display = 'none';
    document.getElementById('titulo-grafico-prov').textContent = 'Población por provincia';
    graficoPoblacion.options.plugins.tooltip.callbacks.label = ctx => ' ' + ctx.parsed.x.toLocaleString('es-ES') + ' hab.';
    graficoPoblacion.options.scales.x.ticks.callback = v => v >= 1000000 ? (v/1000000).toFixed(1)+'M' : v >= 1000 ? (v/1000).toFixed(0)+'k' : v;

    const todosSinDup = getMunicipiosSinDuplicados(false);
    const totales = {};
    Object.keys(NOMBRES_PROVINCIA).forEach(k => totales[k] = 0);
    todosSinDup.forEach(m => { totales[m.prov_key] = (totales[m.prov_key] || 0) + m[estado.sexo]; });

    const ordenadas = Object.entries(totales).sort((a, b) => b[1] - a[1]);
    graficoPoblacion.data.labels                       = ordenadas.map(([k]) => NOMBRES_PROVINCIA[k]);
    graficoPoblacion.data.datasets[0].data             = ordenadas.map(([, v]) => v);
    graficoPoblacion.data.datasets[0].backgroundColor  = ordenadas.map(([k]) => COLORES_PROVINCIA[k]);
    graficoPoblacion.update();
}


/* ══════════════════════════════════════════
   11. GRÁFICO COMPARACIÓN HOMBRES VS MUJERES
   Muestra un gráfico de dona con la proporción
   de hombres y mujeres del municipio seleccionado.
   Se actualiza cada vez que el usuario hace clic
   en un municipio del mapa.
   ══════════════════════════════════════════ */

// Variable que guarda la instancia del gráfico de comparación.
// Se guarda para poder destruirlo y recrearlo al cambiar de municipio.
let graficoComparacion = null;

function actualizarGraficoComparacion(p) {
    const wrap = document.getElementById('grafico-comparacion-wrap');

    // Si ya existía un gráfico anterior, destruirlo antes de crear uno nuevo
    if (graficoComparacion) {
        graficoComparacion.destroy();
        graficoComparacion = null;
    }

    // Crear el canvas donde se dibujará el gráfico
    wrap.innerHTML = `<div style="position:relative;height:110px"><canvas id="chart-comparacion"></canvas></div>`;

    const ctx = document.getElementById('chart-comparacion').getContext('2d');
    graficoComparacion = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Hombres', 'Mujeres'],
            datasets: [{
                data: [p.hombres, p.mujeres],
                backgroundColor: ['#1e88e5', '#d81b60'],  // Azul hombres, rosa mujeres
                borderRadius: 4,
                borderSkipped: false,
            }]
        },
        options: {
            indexAxis: 'y',              // Barras horizontales
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: ctx => {
                            const val = ctx.parsed.x;
                            const pct = p.total > 0 ? ((val / p.total) * 100).toFixed(1) : 0;
                            return ` ${val.toLocaleString('es-ES')} hab. (${pct}%)`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        font: { size: 10 },
                        callback: v => v >= 1000 ? (v/1000).toFixed(0)+'k' : v
                    },
                    grid: { color: '#f0f4f8' }
                },
                y: {
                    ticks: { font: { size: 11 } },
                    grid: { display: false }
                }
            }
        }
    });
}


/* ══════════════════════════════════════════
   12. MOSTRAR MUNICIPIO SELECCIONADO
   Al hacer clic en el mapa o en la tabla,
   muestra la información del municipio en el panel derecho.
   El color de la tarjeta corresponde al color de su provincia.
   ══════════════════════════════════════════ */

function mostrarMunicipio(p) {
    cambiarPestana('municipio');
    // Marcar pestaña Gráficos con punto indicador de que hay datos nuevos
    const btnGraficos = document.querySelector('.tab-btn[data-tab="graficos"]');
    if (btnGraficos) btnGraficos.setAttribute('data-ready', '1');
    const color  = COLORES_PROVINCIA[p.prov_key] || '#1b6ca8';
    const subv   = (typeof DATOS_SUBVENCIONES !== 'undefined') && DATOS_SUBVENCIONES[p.codigo];
    const subvVal   = subv ? (estado.anio_subv === 'total' ? subv.total : (subv.por_anio[estado.anio_subv] || 0)) : 0;
    const subvLabel = estado.anio_subv === 'total' ? 'Subvenciones diputación 2022-2025' : `Subvenciones diputación ${estado.anio_subv}`;
    const subvHtml = `
        <div class="muni-stats" style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.3);padding-top:6px">
            <div class="muni-stat" style="grid-column:1/3">
                <div class="stat-val">${subv ? subvVal.toLocaleString('es-ES') + ' €' : '0 €'}</div>
                <div class="stat-lbl">${subv ? subvLabel : 'Sin concesiones en el BDNS 2022-2025'}</div>
            </div>
            ${subv ? `<div class="muni-stat"><div class="stat-val">${subv.num_subvenciones}</div><div class="stat-lbl">Nº concesiones</div></div>` : ''}
        </div>`;
    const renta  = (typeof DATOS_RENTA !== 'undefined') && DATOS_RENTA[p.codigo];
    const rentaHtml = renta ? `
        <div class="muni-stats" style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.3);padding-top:6px">
            <div class="muni-stat" style="grid-column:1/3">
                <div class="stat-val">${renta.renta_media.toLocaleString('es-ES')} €</div>
                <div class="stat-lbl">Renta media/persona (2023)</div>
            </div>
            ${renta.renta_mediana ? `<div class="muni-stat" style="grid-column:3/4">
                <div class="stat-val">${renta.renta_mediana.toLocaleString('es-ES')} €</div>
                <div class="stat-lbl">Renta mediana</div>
            </div>` : ''}
        </div>` : '';
    const estab = (typeof DATOS_ESTABLECIMIENTOS !== 'undefined') && DATOS_ESTABLECIMIENTOS[p.codigo];
    const estabHtml = estab ? `
        <div class="muni-stats" style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.3);padding-top:6px">
            <div class="muni-stat" style="grid-column:1/3">
                <div class="stat-val">${estab.total}</div>
                <div class="stat-lbl">Total establecimientos</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${estab.total_1000}</div>
                <div class="stat-lbl">por 1.000 hab.</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${estab.bares}</div>
                <div class="stat-lbl">Bares</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${estab.restaurantes}</div>
                <div class="stat-lbl">Restaurantes</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${estab.cafeterias}</div>
                <div class="stat-lbl">Cafeterías</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${estab.alojamiento}</div>
                <div class="stat-lbl">Alojamiento</div>
            </div>
        </div>` : `
        <div class="muni-stats" style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.3);padding-top:6px">
            <div class="muni-stat" style="grid-column:1/3">
                <div class="stat-val">0</div>
                <div class="stat-lbl">Sin establecimientos registrados</div>
            </div>
        </div>`;

    const saludD = (typeof DATOS_SALUD !== 'undefined') && DATOS_SALUD[p.codigo];
    const saludHtml = saludD ? `
        <div class="muni-stats" style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.3);padding-top:6px">
            <div class="muni-stat" style="grid-column:1/3">
                <div class="stat-val" style="font-size:13px">${LABELS_SALUD[saludD.tipo] || '—'}</div>
                <div class="stat-lbl">Cobertura sanitaria</div>
            </div>
            ${saludD.nombre_cs ? `<div class="muni-stat" style="grid-column:1/3">
                <div class="stat-val" style="font-size:11px;font-weight:500">${saludD.nombre_cs}</div>
                <div class="stat-lbl">Centro de salud asignado</div>
            </div>` : ''}
        </div>` : '';

    const edades = (typeof DATOS_EDADES !== 'undefined') && DATOS_EDADES[p.codigo];
    const edadHtml = edades ? `
        <div class="muni-stats" style="margin-top:6px;border-top:1px solid rgba(255,255,255,0.3);padding-top:6px">
            <div class="muni-stat">
                <div class="stat-val">${edades.porc_65}%</div>
                <div class="stat-lbl">≥65 años</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${edades.ind_envej}</div>
                <div class="stat-lbl">Índice env.</div>
            </div>
            <div class="muni-stat">
                <div class="stat-val">${edades.pob_65.toLocaleString('es-ES')}</div>
                <div class="stat-lbl">Mayores 65</div>
            </div>
        </div>` : '';

    // Actualizar la tarjeta de información del municipio
    document.getElementById('muni-detail').innerHTML = `
        <div class="muni-info" style="background:linear-gradient(135deg,${color},${color}bb)">
            <div class="muni-name">${p.nombre}</div>
            <div class="muni-prov">Provincia de ${p.provincia} · INE: ${p.codigo}</div>
            <div class="muni-stats">
                <div class="muni-stat">
                    <div class="stat-val">${p.total.toLocaleString('es-ES')}</div>
                    <div class="stat-lbl">Total</div>
                </div>
                <div class="muni-stat">
                    <div class="stat-val">${p.hombres.toLocaleString('es-ES')}</div>
                    <div class="stat-lbl">Hombres</div>
                </div>
                <div class="muni-stat">
                    <div class="stat-val">${p.mujeres.toLocaleString('es-ES')}</div>
                    <div class="stat-lbl">Mujeres</div>
                </div>
            </div>
            ${edadHtml}
            ${rentaHtml}
            ${subvHtml}
            ${estabHtml}
            ${saludHtml}
        </div>`;

    // Gráfico H vs M: solo cuando la variable tiene desglose por sexo
    const conSexo = ['poblacion', 'porc_65', 'ind_envej'].includes(estado.variable);
    const secComp = document.getElementById('seccion-comparacion');
    const TITULOS_COMP = {
        poblacion:  'Hombres vs Mujeres',
        porc_65:    '% Mayores de 65 · H vs M',
        ind_envej:  'Índice envejecimiento · H vs M',
    };
    if (conSexo) {
        secComp.style.display = '';
        document.getElementById('titulo-comparacion').textContent =
            TITULOS_COMP[estado.variable] || 'Hombres vs Mujeres';
        actualizarGraficoComparacion(p);
    } else {
        if (graficoComparacion) { graficoComparacion.destroy(); graficoComparacion = null; }
        secComp.style.display = 'none';
    }

    // Actualizar el gráfico de evolución temporal
    actualizarGraficoEvolucion(p);

    // Actualizar el gráfico de movimiento natural (nacimientos/defunciones)
    actualizarGraficoVital(p);
}


/* ══════════════════════════════════════════
   13. GRÁFICO DE EVOLUCIÓN TEMPORAL
   Muestra la evolución de población 1996-2025
   del municipio seleccionado.
   ══════════════════════════════════════════ */

let graficoEvolucion = null;

function actualizarGraficoEvolucion(p) {
    const wrap = document.getElementById('grafico-evolucion-wrap');

    if (typeof DATOS_EVOLUCION === 'undefined' || !DATOS_EVOLUCION[p.codigo]) {
        wrap.innerHTML = '<div class="no-selection" style="font-size:12px;color:#888">Sin datos de evolución para este municipio</div>';
        return;
    }

    const ev = DATOS_EVOLUCION[p.codigo];
    const color = COLORES_PROVINCIA[p.prov_key] || '#1b6ca8';

    if (graficoEvolucion) {
        graficoEvolucion.destroy();
        graficoEvolucion = null;
    }

    wrap.innerHTML = `<div style="position:relative;height:190px"><canvas id="chart-evolucion"></canvas></div>`;

    const ctx = document.getElementById('chart-evolucion').getContext('2d');
    graficoEvolucion = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ev.años,
            datasets: [
                {
                    label: 'Total',
                    data: ev.total,
                    borderColor: color,
                    backgroundColor: color + '22',
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: true,
                    tension: 0.3,
                },
                {
                    label: 'Hombres',
                    data: ev.hombres,
                    borderColor: '#1e88e5',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3,
                    borderDash: [4, 3],
                },
                {
                    label: 'Mujeres',
                    data: ev.mujeres,
                    borderColor: '#d81b60',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3,
                    borderDash: [4, 3],
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { font: { size: 10 }, boxWidth: 20, padding: 8 }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('es-ES')} hab.`
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        font: { size: 9 },
                        maxTicksLimit: 10,
                    },
                    grid: { color: '#f0f4f8' }
                },
                y: {
                    ticks: {
                        font: { size: 9 },
                        callback: v => v >= 1000 ? (v/1000).toFixed(0)+'k' : v
                    },
                    grid: { color: '#f0f4f8' }
                }
            }
        }
    });
}


/* ══════════════════════════════════════════
   13b. GRÁFICO DE MOVIMIENTO NATURAL
   Muestra nacimientos, defunciones y balance
   vegetativo del municipio (2016-2024).
   ══════════════════════════════════════════ */

let graficoVital = null;

function actualizarGraficoVital(p) {
    const wrap = document.getElementById('grafico-vital-wrap');

    if (typeof DATOS_VITAL === 'undefined' || !DATOS_VITAL[p.codigo]) {
        wrap.innerHTML = '<div class="no-selection" style="font-size:12px;color:#888">Sin datos de movimiento natural para este municipio</div>';
        return;
    }

    const vt = DATOS_VITAL[p.codigo];

    if (graficoVital) {
        graficoVital.destroy();
        graficoVital = null;
    }

    wrap.innerHTML = `<div style="position:relative;height:190px"><canvas id="chart-vital"></canvas></div>`;

    const ctx = document.getElementById('chart-vital').getContext('2d');
    graficoVital = new Chart(ctx, {
        type: 'line',
        data: {
            labels: vt.años,
            datasets: [
                {
                    label: 'Nacimientos',
                    data: vt.nacimientos,
                    borderColor: '#43a047',
                    backgroundColor: '#43a04722',
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: false,
                    tension: 0.3,
                },
                {
                    label: 'Defunciones',
                    data: vt.defunciones,
                    borderColor: '#e53935',
                    backgroundColor: '#e5393522',
                    borderWidth: 2,
                    pointRadius: 2,
                    fill: false,
                    tension: 0.3,
                },
                {
                    label: 'Balance',
                    data: vt.balance,
                    borderColor: '#7b8fa1',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.3,
                    borderDash: [4, 3],
                },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    labels: { font: { size: 10 }, boxWidth: 20, padding: 8 }
                },
                tooltip: {
                    callbacks: {
                        label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('es-ES')}`
                    }
                }
            },
            scales: {
                x: {
                    ticks: { font: { size: 9 }, maxTicksLimit: 10 },
                    grid: { color: '#f0f4f8' }
                },
                y: {
                    ticks: {
                        font: { size: 9 },
                        callback: v => v >= 1000 ? (v/1000).toFixed(1)+'k' : v
                    },
                    grid: { color: '#f0f4f8' }
                }
            }
        }
    });
}


/* ══════════════════════════════════════════
   14. TÍTULO DEL MAPA
   Actualiza el texto flotante del mapa
   según los filtros activos.
   ══════════════════════════════════════════ */

function actualizarTituloMapa() {
    const selProv    = document.getElementById('sel-provincia');
    const nombreProv = selProv.options[selProv.selectedIndex].text;
    const ETIQUETAS_TIPO_ESTAB2 = { total: 'Todos', bares: 'Bares', restaurantes: 'Restaurantes', cafeterias: 'Cafeterías', alojamiento: 'Alojamiento' };
    const _algoLbl = estado.jenny_algo === 'kmeans' ? 'K-Means' : 'K-Medoids';
    const _metLbl  = {mm:'Min-Max', z:'Z-score', rel:'Relativa', corr:'Correlación'}[estado.jenny_met] || estado.jenny_met;
    const TITULOS_VAR = { poblacion: 'Población', porc_65: '% Mayores de 65', ind_envej: 'Índice de envejecimiento', renta_media: 'Renta media por persona', subvenciones: 'Subvenciones diputaciones', establecimientos: `Establecimientos · ${ETIQUETAS_TIPO_ESTAB2[estado.tipo_estab]}`, cobertura_salud: 'Cobertura sanitaria', kmeans: `${_algoLbl} · ${_metLbl} · K=${estado.jenny_k}` };
    const varNombre  = TITULOS_VAR[estado.variable] || estado.variable;
    const sinSexo    = ['renta_media', 'subvenciones', 'establecimientos', 'cobertura_salud', 'nacimientos', 'defunciones', 'balance_vital', 'despoblacion', 'kmeans'].includes(estado.variable);
    const sufSexo    = (estado.sexo !== 'total' && !sinSexo) ? ` · ${ETIQUETAS_SEXO[estado.sexo]}` : '';
    const esVital    = ['nacimientos', 'defunciones', 'balance_vital'].includes(estado.variable);
    const anio       = estado.variable === 'kmeans' ? '1996–2025' : estado.variable === 'renta_media' ? '2023' : estado.variable === 'subvenciones' ? (estado.anio_subv === 'total' ? '2022-2025' : estado.anio_subv) : estado.variable === 'establecimientos' ? '2025' : estado.variable === 'cobertura_salud' ? '2025' : estado.variable === 'despoblacion' ? `${estado.anio_base_desp}–2025` : esVital ? estado.anio_vital : '2025';
    document.getElementById('map-title').textContent =
        `${varNombre} · ${nombreProv}${sufSexo} · ${anio}`;
}


/* ══════════════════════════════════════════
   14. PESTAÑAS DEL PANEL DERECHO
   ══════════════════════════════════════════ */

function cambiarPestana(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab-btn[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.add('active');
    // Forzar redibujado de los gráficos por si estaban en un contenedor oculto
    if (tabId === 'graficos') {
        if (graficoComparacion) graficoComparacion.resize();
        if (graficoEvolucion)   graficoEvolucion.resize();
        // Quitar indicador de datos nuevos al abrir la pestaña
        const btnGraficos = document.querySelector('.tab-btn[data-tab="graficos"]');
        if (btnGraficos) btnGraficos.removeAttribute('data-ready');
    } else if (tabId === 'cyl') {
        graficoPoblacion.resize();
    }
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => cambiarPestana(btn.dataset.tab));
});


/* ══════════════════════════════════════════
   15. CAPA DE PUNTOS TURÍSTICOS
   Muestra/oculta museos y monumentos de CyL
   (fuente: datosabiertos.jcyl.es — Junta de CyL).
   ══════════════════════════════════════════ */

function pintarTurismo() {
    if (capaTurismo) { map.removeLayer(capaTurismo); capaTurismo = null; }
    actualizarPanelDerecho();
    if (!estado.turismo || typeof datosTurismo === 'undefined') return;

    capaTurismo = L.layerGroup();

    datosTurismo.forEach(p => {
        const color  = COLORES_TURISMO[p.categoria] || '#9e9e9e';
        const marker = L.circleMarker([p.lat, p.lon], {
            radius:      5,
            fillColor:   color,
            color:       '#fff',
            weight:      1,
            fillOpacity: 0.85,
        });

        marker.on('click', () => mostrarPuntoTuristico(p));
        capaTurismo.addLayer(marker);
    });

    capaTurismo.addTo(map);
}


/* ══════════════════════════════════════════
   CAPA DE PUNTOS DE ESTABLECIMIENTOS
   Muestra/oculta bares, restaurantes, cafeterías
   y alojamiento como puntos sobre el mapa.
   Solo los registros con coordenadas GPS válidas.
   ══════════════════════════════════════════ */

function pintarPuntosEstab() {
    if (capaPuntosEstab) { map.removeLayer(capaPuntosEstab); capaPuntosEstab = null; }
    actualizarPanelDerecho();
    if (!estado.estab_puntos || typeof datosPuntosEstab === 'undefined') return;

    capaPuntosEstab = L.layerGroup();

    datosPuntosEstab.forEach(p => {
        const color  = COLORES_ESTAB[p.tipo] || '#9e9e9e';
        const marker = L.circleMarker([p.lat, p.lon], {
            radius:      4,
            fillColor:   color,
            color:       '#fff',
            weight:      1,
            fillOpacity: 0.85,
        });

        marker.on('click', () => mostrarPuntoEstab(p));
        capaPuntosEstab.addLayer(marker);
    });

    capaPuntosEstab.addTo(map);
}

function mostrarPuntoEstab(p) {
    cambiarPestana('municipio');
    const color = COLORES_ESTAB[p.tipo] || '#9e9e9e';
    const label = LABELS_ESTAB[p.tipo] || p.tipo;
    const ubicacion = [p.municipio, p.provincia].filter(Boolean).join(' · ');

    document.getElementById('muni-detail').innerHTML = `
        <div class="muni-info" style="background:linear-gradient(135deg,${color},${color}bb)">
            <div class="muni-name">${p.nombre || label}</div>
            <div class="muni-prov">${label}${ubicacion ? ' · ' + ubicacion : ''}</div>
            ${p.categoria && p.categoria !== label ? `<div class="muni-prov" style="font-size:11px;opacity:0.85">${p.categoria}</div>` : ''}
        </div>`;

    document.getElementById('grafico-comparacion-wrap').innerHTML = `
        <div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
    document.getElementById('grafico-evolucion-wrap').innerHTML = `
        <div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
    document.getElementById('grafico-vital-wrap').innerHTML = `
        <div class="no-selection"><div class="icon">🏥</div>Haz clic en un municipio para ver el movimiento natural</div>`;
}


/* ══════════════════════════════════════════
   16. TARJETA DE PUNTO TURÍSTICO
   Al hacer clic en un punto del mapa, muestra su
   información en el panel derecho (pestaña Municipio).
   ══════════════════════════════════════════ */

function mostrarPuntoTuristico(p) {
    cambiarPestana('municipio');
    const color = COLORES_TURISMO[p.categoria] || '#9e9e9e';

    const ubicacion = [p.municipio, p.provincia].filter(Boolean).join(' · ');

    document.getElementById('muni-detail').innerHTML = `
        <div class="muni-info" style="background:linear-gradient(135deg,${color},${color}bb)">
            <div class="muni-name">${p.nombre}</div>
            <div class="muni-prov">${p.categoria}${ubicacion ? ' · ' + ubicacion : ''}</div>
            ${p.periodo ? `<div class="muni-prov" style="font-size:11px;opacity:0.85">${p.periodo}</div>` : ''}
        </div>
        ${p.descripcion ? `<div style="padding:10px 12px;font-size:12px;color:#444;line-height:1.6;border-bottom:1px solid #f0f4f8">${p.descripcion}</div>` : ''}
        ${p.horario ? `<div style="padding:8px 12px;font-size:11px;color:#555;border-bottom:1px solid #f0f4f8">🕐 ${p.horario}</div>` : ''}
        ${p.web ? `<div style="padding:8px 12px"><a href="${p.web}" target="_blank" style="font-size:12px;color:#1b6ca8;text-decoration:none">Ver ficha oficial ↗</a></div>` : ''}
    `;

    if (graficoComparacion) { graficoComparacion.destroy(); graficoComparacion = null; }
    if (graficoEvolucion)   { graficoEvolucion.destroy();   graficoEvolucion = null; }
    if (graficoVital)       { graficoVital.destroy();       graficoVital = null; }

    document.getElementById('grafico-comparacion-wrap').innerHTML =
        '<div class="no-selection" style="font-size:12px;color:#aaa">No disponible para puntos turísticos</div>';
    document.getElementById('grafico-evolucion-wrap').innerHTML =
        '<div class="no-selection" style="font-size:12px;color:#aaa">No disponible para puntos turísticos</div>';
    document.getElementById('grafico-vital-wrap').innerHTML =
        '<div class="no-selection" style="font-size:12px;color:#aaa">No disponible para puntos turísticos</div>';
}


/* ══════════════════════════════════════════
   17. LEYENDA DE TURISMO EN PESTAÑA CYL
   Cuando el modo turismo está activo, sustituye
   los KPIs y el gráfico de población por una
   leyenda explicando qué significa cada color.
   ══════════════════════════════════════════ */

function actualizarPanelDerecho() {
    const secKpis    = document.getElementById('seccion-kpis');
    const secGrafico = document.getElementById('seccion-grafico-prov');
    let secTurismo   = document.getElementById('seccion-turismo-leyenda');
    let secEstab     = document.getElementById('seccion-estab-resumen');
    let secRV        = document.getElementById('seccion-redviaria');

    // ── RECICLAJE ACTIVO ──────────────────────────────────────────────────────
    if (estado.reciclaje) {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';
        if (secEstab)   secEstab.style.display   = 'none';
        if (secRV)      secRV.style.display      = 'none';
        const _secNat3 = document.getElementById('seccion-naturaleza');
        if (_secNat3) _secNat3.style.display = 'none';

        let html = `<div class="kpi-title" style="margin-bottom:8px">Gestión de residuos · CyL</div>`;

        if (typeof RESIDUOS_META !== 'undefined') {
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                    <div style="width:18px;height:18px;border-radius:50%;background:#1b5e20;flex-shrink:0;border:2px solid #fff;box-shadow:0 0 0 1px #1b5e2066"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50">Puntos Limpios (ecoparques)</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${RESIDUOS_META.n_puntos_limpios}</span>
                </div>
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                    <div style="width:18px;height:18px;border-radius:50%;background:#e65100;flex-shrink:0;border:2px solid #fff;box-shadow:0 0 0 1px #e6510066"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50">Plantas de Transferencia</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${RESIDUOS_META.n_plantas_transf}</span>
                </div>`;

            // Distribución provincial de puntos limpios
            if (typeof PUNTOS_LIMPIOS !== 'undefined' && PUNTOS_LIMPIOS.length) {
                const porProv = {};
                PUNTOS_LIMPIOS.forEach(p => { porProv[p.provincia] = (porProv[p.provincia] || 0) + 1; });
                html += `<div style="font-size:11px;font-weight:600;color:#555;margin:10px 0 4px">Puntos Limpios por provincia</div>`;
                Object.entries(porProv).sort((a,b) => b[1]-a[1]).forEach(([prov, n]) => {
                    html += `
                        <div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid #f8f9fa">
                            <span style="flex:1;font-size:11px;color:#2d3f50">${prov}</span>
                            <span style="font-size:11px;font-weight:600;color:#2d3f50">${n}</span>
                        </div>`;
                });
            }
        }
        html += `<div style="font-size:10px;color:#aaa;margin-top:8px">Haz clic en los puntos para ver la información del gestor.<br>Fuente: Junta de CyL · datosabiertos.jcyl.es</div>`;

        let secRec = document.getElementById('seccion-reciclaje');
        if (!secRec) {
            secRec = document.createElement('div');
            secRec.id = 'seccion-reciclaje';
            secRec.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secRec);
        }
        secRec.innerHTML = html;
        secRec.style.display = '';
        return;
    }

    const _secRec = document.getElementById('seccion-reciclaje');
    if (_secRec) _secRec.style.display = 'none';

    // ── NATURALEZA ACTIVA ─────────────────────────────────────────────────────
    if (estado.naturaleza) {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';
        if (secEstab)   secEstab.style.display   = 'none';
        if (secRV)      secRV.style.display      = 'none';

        let html = `<div class="kpi-title" style="margin-bottom:8px">Rutas y espacios naturales · CyL</div>`;

        if (typeof NATURALEZA_META !== 'undefined') {
            const tiposRuta = [
                ['GR', 'Gran Recorrido (GR)',    '#c0392b'],
                ['PR', 'Pequeño Recorrido (PR)', '#e67e22'],
                ['SL', 'Sendero Local (SL)',      '#f39c12'],
            ];
            tiposRuta.forEach(([t, label, color]) => {
                const km = NATURALEZA_META.km_rutas[t] || 0;
                if (!km) return;
                html += `
                    <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                        <div style="width:22px;height:3px;border-radius:2px;background:${color};flex-shrink:0"></div>
                        <span style="flex:1;font-size:12px;color:#2d3f50">${label}</span>
                        <span style="font-size:12px;font-weight:600;color:#2d3f50">${km.toLocaleString('es-ES')} km</span>
                    </div>`;
            });
        }

        if (typeof ESPACIOS_NATURALES !== 'undefined') {
            const tiposEsp = {};
            ESPACIOS_NATURALES.forEach(e => { tiposEsp[e.tipo] = (tiposEsp[e.tipo] || 0) + 1; });
            const tiposOrden = [
                ['Parque Nacional',       '#1b5e20'],
                ['Parque Natural',        '#2e7d32'],
                ['Reserva Natural',       '#388e3c'],
                ['Paisaje Protegido',     '#558b2f'],
                ['Zona de Especial Protección (ZEPA)', '#00695c'],
                ['Zona de Especial Conservación (ZEC)', '#0277bd'],
            ];
            html += `<div style="font-size:11px;font-weight:600;color:#555;margin:10px 0 4px">Espacios Protegidos</div>`;
            tiposOrden.forEach(([label, color]) => {
                const n = tiposEsp[label] || 0;
                if (!n) return;
                html += `
                    <div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #f0f4f8">
                        <div style="width:11px;height:11px;border-radius:50%;background:${color};flex-shrink:0;border:1.5px solid #fff;box-shadow:0 0 0 1px ${color}66"></div>
                        <span style="flex:1;font-size:11px;color:#2d3f50">${label}</span>
                        <span style="font-size:12px;font-weight:600;color:#2d3f50">${n}</span>
                    </div>`;
            });
            const nEsp = Object.values(tiposEsp).reduce((s, n) => s + n, 0);
            html += `
                <div style="display:flex;justify-content:space-between;padding:8px 0 4px;font-size:11px;font-weight:700;color:#1b6ca8">
                    <span>Total espacios protegidos</span><span>${nEsp}</span>
                </div>`;
        }
        html += `<div style="font-size:10px;color:#aaa;margin-top:4px">Haz clic en los puntos para ver el nombre del espacio. Fuente: OpenStreetMap · Mayo 2025</div>`;

        let secNat = document.getElementById('seccion-naturaleza');
        if (!secNat) {
            secNat = document.createElement('div');
            secNat.id = 'seccion-naturaleza';
            secNat.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secNat);
        }
        secNat.innerHTML = html;
        secNat.style.display = '';
        return;
    }

    const secNat2 = document.getElementById('seccion-naturaleza');
    if (secNat2) secNat2.style.display = 'none';

    // ── RED VIARIA ACTIVA ─────────────────────────────────────────────────────
    if (estado.red_viaria) {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';
        if (secEstab)   secEstab.style.display   = 'none';
        const _secNat = document.getElementById('seccion-naturaleza');
        if (_secNat) _secNat.style.display = 'none';

        let html = `<div class="kpi-title" style="margin-bottom:8px">Red viaria · Castilla y León</div>`;

        if (typeof CARRETERAS_META !== 'undefined') {
            const tipos = [
                ['motorway', 'Autopista / Autovía',   '#c0392b'],
                ['trunk',    'Carretera Nacional',     '#e67e22'],
                ['primary',  'Carretera Autonómica',  '#f39c12'],
                ['secondary','Carretera Provincial',  '#27ae60'],
            ];
            tipos.forEach(([t, label, color]) => {
                const km = CARRETERAS_META.tipos[t]?.km || 0;
                html += `
                    <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                        <div style="width:22px;height:4px;border-radius:2px;background:${color};flex-shrink:0"></div>
                        <span style="flex:1;font-size:12px;color:#2d3f50">${label}</span>
                        <span style="font-size:12px;font-weight:600;color:#2d3f50">${km.toLocaleString('es-ES')} km</span>
                    </div>`;
            });
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px">
                    <div style="width:22px;height:4px;flex-shrink:0"></div>
                    <span style="flex:1;font-size:12px;font-weight:700;color:#1b6ca8">Total</span>
                    <span style="font-size:13px;font-weight:700;color:#1b6ca8">${CARRETERAS_META.total_km.toLocaleString('es-ES')} km</span>
                </div>`;
        }
        html += `<div style="font-size:10px;color:#aaa;margin-top:4px">Fuente: OpenStreetMap · Mayo 2025</div>`;

        if (!secRV) {
            secRV = document.createElement('div');
            secRV.id = 'seccion-redviaria';
            secRV.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secRV);
        }
        secRV.innerHTML = html;
        secRV.style.display = '';
        return;
    }

    if (secRV) secRV.style.display = 'none';

    // ── TURISMO ACTIVO ─────────────────────────────────────────────────────────
    if (estado.turismo) {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secEstab) secEstab.style.display = 'none';

        const conteo = {};
        if (typeof datosTurismo !== 'undefined') {
            datosTurismo.forEach(p => { conteo[p.categoria] = (conteo[p.categoria] || 0) + 1; });
        }
        const ordenadas = Object.entries(conteo).sort((a, b) => b[1] - a[1]);
        const total     = ordenadas.reduce((s, [, n]) => s + n, 0);

        let html = `<div class="kpi-title" style="margin-bottom:8px">Puntos turísticos · Castilla y León</div>`;
        ordenadas.forEach(([cat, n]) => {
            const color = COLORES_TURISMO[cat] || '#9e9e9e';
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                    <div style="width:11px;height:11px;border-radius:50%;background:${color};flex-shrink:0;border:1px solid #fff;box-shadow:0 0 0 1px ${color}55"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50">${cat}</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${n.toLocaleString('es-ES')}</span>
                </div>`;
        });
        html += `
            <div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px">
                <div style="width:11px;height:11px;flex-shrink:0"></div>
                <span style="flex:1;font-size:12px;font-weight:700;color:#1b6ca8">Total</span>
                <span style="font-size:13px;font-weight:700;color:#1b6ca8">${total.toLocaleString('es-ES')}</span>
            </div>
            <div style="font-size:10px;color:#aaa;margin-top:2px">Fuente: datosabiertos.jcyl.es · Junta de CyL</div>`;

        if (!secTurismo) {
            secTurismo = document.createElement('div');
            secTurismo.id = 'seccion-turismo-leyenda';
            secTurismo.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secTurismo);
        }
        secTurismo.innerHTML = html;
        secTurismo.style.display = '';
        return;
    }

    // ── CAPA PUNTOS ESTABLECIMIENTOS ACTIVA ───────────────────────────────────
    if (estado.estab_puntos) {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';

        const TIPOS = ['bares', 'restaurantes', 'cafeterias', 'alojamiento'];
        const conteoP = { bares: 0, restaurantes: 0, cafeterias: 0, alojamiento: 0 };
        if (typeof datosPuntosEstab !== 'undefined') {
            datosPuntosEstab.forEach(p => { if (conteoP[p.tipo] !== undefined) conteoP[p.tipo]++; });
        }
        const totalP = TIPOS.reduce((s, t) => s + conteoP[t], 0);

        let html = `<div class="kpi-title" style="margin-bottom:8px">Establecimientos · Castilla y León</div>`;
        TIPOS.forEach(t => {
            const color = COLORES_ESTAB[t];
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                    <div style="width:11px;height:11px;border-radius:50%;background:${color};flex-shrink:0;border:1px solid #fff;box-shadow:0 0 0 1px ${color}55"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50">${LABELS_ESTAB[t]}</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${conteoP[t].toLocaleString('es-ES')}</span>
                </div>`;
        });
        html += `
            <div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px">
                <div style="width:11px;height:11px;flex-shrink:0"></div>
                <span style="flex:1;font-size:12px;font-weight:700;color:#1b6ca8">Total con GPS</span>
                <span style="font-size:13px;font-weight:700;color:#1b6ca8">${totalP.toLocaleString('es-ES')}</span>
            </div>
            <div style="font-size:10px;color:#aaa;margin-top:4px">GPS propio: 6.926 registros · Centroide municipal: 27.716.<br>Haz clic en un punto para ver su información.</div>
            <div style="font-size:10px;color:#aaa;margin-top:2px">Fuente: Registro de Turismo · Junta de CyL</div>`;

        if (!secEstab) {
            secEstab = document.createElement('div');
            secEstab.id = 'seccion-estab-resumen';
            secEstab.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secEstab);
        }
        secEstab.innerHTML = html;
        secEstab.style.display = '';
        return;
    }

    // ── CAPA PUNTOS SALUD ACTIVA ───────────────────────────────────────────────
    if (estado.salud_puntos) {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';
        if (secEstab)   secEstab.style.display   = 'none';

        const conteoS = { hospital: 0, cs: 0, consultorio: 0, pac: 0, cg: 0, asignado: 0, sin_datos: 0 };
        if (typeof datosPuntosSalud !== 'undefined') {
            datosPuntosSalud.forEach(p => { if (conteoS[p.tipo] !== undefined) conteoS[p.tipo]++; });
        }

        let html = `<div class="kpi-title" style="margin-bottom:8px">Cobertura sanitaria · Castilla y León</div>`;
        [
            ['hospital',    'Hospital',                    '#c0392b'],
            ['cs',          'Centro de Salud',             '#1565c0'],
            ['consultorio', 'Consultorio Local',           '#27ae60'],
            ['pac',         'Urgencias (PAC)',             '#e65100'],
            ['cg',          'Centro de Guardia',           '#bf360c'],
            ['asignado',    'Sin centro (asignado a CS)',  '#90a4ae'],
            ['sin_datos',   'Sin datos sanitarios',        '#cfd8dc'],
        ].forEach(([t, label, color]) => {
            if (!conteoS[t]) return;
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                    <div style="width:11px;height:11px;border-radius:50%;background:${color};flex-shrink:0;border:1px solid #fff;box-shadow:0 0 0 1px ${color}55"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50">${label}</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${conteoS[t].toLocaleString('es-ES')}</span>
                </div>`;
        });
        html += `<div style="font-size:10px;color:#aaa;margin-top:8px">Haz clic en un punto para ver su información.</div>
            <div style="font-size:10px;color:#aaa;margin-top:2px">Fuente: Sacyl · Junta de CyL · Ministerio de Sanidad</div>`;

        let secSalud = document.getElementById('seccion-salud-resumen');
        if (!secSalud) {
            secSalud = document.createElement('div');
            secSalud.id = 'seccion-salud-resumen';
            secSalud.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secSalud);
        }
        secSalud.innerHTML = html;
        secSalud.style.display = '';
        return;
    }

    // ── VARIABLE COBERTURA SALUD ───────────────────────────────────────────────
    if (estado.variable === 'cobertura_salud') {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';

        const conteoN = { hospital: 0, centro_salud: 0, consultorio: 0, asignado: 0, sin_datos: 0 };
        if (typeof DATOS_SALUD !== 'undefined') {
            Object.values(DATOS_SALUD).forEach(m => { conteoN[m.tipo] = (conteoN[m.tipo] || 0) + 1; });
        }
        const total = Object.values(conteoN).reduce((s, n) => s + n, 0);

        let html = `<div class="kpi-title" style="margin-bottom:8px">Cobertura sanitaria · CyL</div>`;
        [['hospital','Hospital','#c0392b'],['centro_salud','Centro de Salud','#1565c0'],['consultorio','Consultorio Local','#27ae60'],['asignado','Asignado (CS externo)','#b0bec5'],['sin_datos','Sin datos','#eceff1']].forEach(([tipo, label, color]) => {
            const n = conteoN[tipo] || 0;
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
                    <div style="width:11px;height:11px;border-radius:3px;background:${color};flex-shrink:0;border:1px solid #ddd"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50">${label}</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${n.toLocaleString('es-ES')}</span>
                </div>`;
        });
        html += `<div style="font-size:10px;color:#aaa;margin-top:6px">El mapa muestra el nivel de servicio sanitario de cada municipio.</div>
            <div style="font-size:10px;color:#aaa;margin-top:2px">Fuente: Sacyl · Junta de CyL · Ministerio de Sanidad</div>`;

        let secSaludVar = document.getElementById('seccion-salud-var');
        if (!secSaludVar) {
            secSaludVar = document.createElement('div');
            secSaludVar.id = 'seccion-salud-var';
            secSaludVar.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secSaludVar);
        }
        secSaludVar.innerHTML = html;
        secSaludVar.style.display = '';
        return;
    }

    // ── VARIABLE ESTABLECIMIENTOS ──────────────────────────────────────────────
    if (estado.variable === 'establecimientos') {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';

        const COLORES_TIPO = { bares: '#f59e0b', restaurantes: '#10b981', cafeterias: '#92400e', alojamiento: '#3b82f6' };
        const LABELS_TIPO  = { bares: 'Bares', restaurantes: 'Restaurantes', cafeterias: 'Cafeterías', alojamiento: 'Alojamiento' };
        const TIPOS = ['bares', 'restaurantes', 'cafeterias', 'alojamiento'];

        let totales = { bares: 0, restaurantes: 0, cafeterias: 0, alojamiento: 0 };
        let sinDatos = 0;
        const totalMunicipios = Object.keys(window.DATOS_GEO
            ? [...new Set(DATOS_GEO.features.map(f => f.properties.codigo))].length
            : 2248).length || 2248;

        if (typeof DATOS_ESTABLECIMIENTOS !== 'undefined') {
            Object.values(DATOS_ESTABLECIMIENTOS).forEach(m => {
                TIPOS.forEach(t => { totales[t] += m[t] || 0; });
            });
            sinDatos = totalMunicipios - Object.keys(DATOS_ESTABLECIMIENTOS).length;
        }
        const totalEstab = TIPOS.reduce((s, t) => s + totales[t], 0);

        const tipoActivo = estado.tipo_estab;

        let html = `<div class="kpi-title" style="margin-bottom:8px">Establecimientos turísticos · CyL</div>`;
        TIPOS.forEach(t => {
            const color     = COLORES_TIPO[t];
            const esBold    = tipoActivo === t || tipoActivo === 'total';
            const fontW     = esBold ? '700' : '400';
            const opacity   = (tipoActivo === 'total' || tipoActivo === t) ? '1' : '0.45';
            html += `
                <div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8;opacity:${opacity}">
                    <div style="width:11px;height:11px;border-radius:3px;background:${color};flex-shrink:0"></div>
                    <span style="flex:1;font-size:12px;color:#2d3f50;font-weight:${fontW}">${LABELS_TIPO[t]}</span>
                    <span style="font-size:12px;font-weight:600;color:#2d3f50">${totales[t].toLocaleString('es-ES')}</span>
                </div>`;
        });
        html += `
            <div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px">
                <div style="width:11px;height:11px;flex-shrink:0"></div>
                <span style="flex:1;font-size:12px;font-weight:700;color:#1b6ca8">Total</span>
                <span style="font-size:13px;font-weight:700;color:#1b6ca8">${totalEstab.toLocaleString('es-ES')}</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;padding:4px 0 2px;border-top:1px solid #f0f4f8;margin-top:4px">
                <div style="width:11px;height:11px;border-radius:50%;background:#e2e8f0;flex-shrink:0"></div>
                <span style="flex:1;font-size:11px;color:#888">Sin establecimientos registrados</span>
                <span style="font-size:11px;font-weight:600;color:#888">~${sinDatos}</span>
            </div>
            <div style="font-size:10px;color:#aaa;margin-top:6px">El mapa muestra establecimientos por 1.000 hab.
Los municipios más claros tienen menos oferta de servicios.</div>
            <div style="font-size:10px;color:#aaa;margin-top:2px">Fuente: Registro de Turismo · Junta de CyL</div>`;

        if (!secEstab) {
            secEstab = document.createElement('div');
            secEstab.id = 'seccion-estab-resumen';
            secEstab.className = 'panel-section';
            document.getElementById('tab-cyl').appendChild(secEstab);
        }
        secEstab.innerHTML = html;
        secEstab.style.display = '';
        return;
    }

    // ── MODO NORMAL ────────────────────────────────────────────────────────────
    const secSaludResumen = document.getElementById('seccion-salud-resumen');
    const secSaludVar     = document.getElementById('seccion-salud-var');
    const veniaDeModo = (secTurismo      && secTurismo.style.display      !== 'none') ||
                        (secEstab        && secEstab.style.display        !== 'none') ||
                        (secSaludResumen && secSaludResumen.style.display !== 'none') ||
                        (secSaludVar     && secSaludVar.style.display     !== 'none');

    secKpis.style.display    = 'block';
    secGrafico.style.display = 'block';
    if (secTurismo)      secTurismo.style.display      = 'none';
    if (secEstab)        secEstab.style.display        = 'none';
    if (secSaludResumen) secSaludResumen.style.display = 'none';
    if (secSaludVar)     secSaludVar.style.display     = 'none';

    // Solo volver a la pestaña CyL si se estaba en un modo especial
    if (veniaDeModo) cambiarPestana('cyl');
}


/* ══════════════════════════════════════════
   18. EVENTOS DE LOS FILTROS
   Cada filtro actualiza el estado y llama a pintarMapa().
   ══════════════════════════════════════════ */

document.getElementById('sel-sexo').addEventListener('change', function () {
    estado.sexo = this.value;
    pintarMapa();
});

document.getElementById('sel-provincia').addEventListener('change', e => {
    estado.provincia = e.target.value;
    pintarMapa();

    if (estado.provincia !== 'todas' && capaGeo) {
        const features = { type: 'FeatureCollection', features: DATOS_GEO.features.filter(f => f.properties.prov_key === estado.provincia) };
        map.fitBounds(L.geoJson(features).getBounds(), { padding: [30, 30] });
    } else {
        map.setView([41.65, -4.72], 7);
    }
});

document.getElementById('sel-intervalos').addEventListener('change', e => {
    estado.intervalos = parseInt(e.target.value);
    pintarMapa();
});

document.getElementById('sel-variable').addEventListener('change', e => {
    estado.variable = e.target.value;
    const esSubv  = estado.variable === 'subvenciones';
    const esEstab = estado.variable === 'establecimientos';
    const esVital = ['nacimientos', 'defunciones', 'balance_vital'].includes(estado.variable);
    const esDesp  = estado.variable === 'despoblacion';
    const esKmeans = estado.variable === 'kmeans';
    document.getElementById('filtro-anio').style.display          = esSubv  ? '' : 'none';
    document.getElementById('div-anio').style.display             = esSubv  ? '' : 'none';
    document.getElementById('filtro-tipo-estab').style.display    = esEstab ? '' : 'none';
    document.getElementById('div-tipo-estab').style.display       = esEstab ? '' : 'none';
    document.getElementById('filtro-anio-vital').style.display    = esVital ? '' : 'none';
    document.getElementById('div-anio-vital').style.display       = esVital ? '' : 'none';
    document.getElementById('filtro-anio-base').style.display     = esDesp  ? '' : 'none';
    document.getElementById('div-anio-base').style.display        = esDesp  ? '' : 'none';
    // Barra secundaria de clustering: solo visible cuando variable=clústeres
    document.getElementById('filter-bar-jenny').style.display     = esKmeans ? '' : 'none';
    // Ocultar intervalos cuando se usan clusters (no aplica)
    document.getElementById('filtro-intervalos').style.display    = esKmeans ? 'none' : '';
    if (!esSubv)  { estado.anio_subv      = 'total'; document.getElementById('sel-anio').value       = 'total'; }
    if (!esEstab) { estado.tipo_estab     = 'total'; document.getElementById('sel-tipo-estab').value = 'total'; }
    if (!esVital) { estado.anio_vital     = '2024';  document.getElementById('sel-anio-vital').value = '2024'; }
    if (!esDesp)  { estado.anio_base_desp = '2000';  document.getElementById('sel-anio-base').value  = '2000'; }

    // Mostrar u ocultar la sección H vs M según la variable
    const conSexo = ['poblacion', 'porc_65', 'ind_envej'].includes(estado.variable);
    const secComp = document.getElementById('seccion-comparacion');
    if (conSexo) {
        secComp.style.display = '';
    } else {
        if (graficoComparacion) { graficoComparacion.destroy(); graficoComparacion = null; }
        secComp.style.display = 'none';
    }

    // Deshabilitar el selector de sexo para variables sin desglose por sexo
    const sinSexoVar = ['renta_media', 'subvenciones', 'establecimientos', 'cobertura_salud', 'nacimientos', 'defunciones', 'balance_vital', 'despoblacion', 'kmeans'].includes(estado.variable);
    const selSexo = document.getElementById('sel-sexo');
    selSexo.disabled = sinSexoVar;
    selSexo.style.opacity = sinSexoVar ? '0.4' : '1';
    if (sinSexoVar) { selSexo.value = 'total'; estado.sexo = 'total'; }

    pintarMapa();
    actualizarAvisoCorr();
});

document.getElementById('sel-tipo-estab').addEventListener('change', e => {
    estado.tipo_estab = e.target.value;
    pintarMapa();
});

document.getElementById('sel-anio').addEventListener('change', e => {
    estado.anio_subv = e.target.value;
    pintarMapa();
});

document.getElementById('sel-anio-vital').addEventListener('change', e => {
    estado.anio_vital = e.target.value;
    pintarMapa();
});

document.getElementById('sel-anio-base').addEventListener('change', e => {
    estado.anio_base_desp = e.target.value;
    pintarMapa();
});

function actualizarAvisoCorr() {
    const aviso = document.getElementById('aviso-corr');
    if (!aviso) return;
    aviso.style.display = (estado.variable === 'kmeans' && estado.jenny_algo === 'kmeans' && estado.jenny_met === 'corr')
        ? 'block' : 'none';
}

// Controles visuales de clustering (pills)
document.querySelectorAll('.jenny-algo-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.jenny-algo-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        estado.jenny_algo = this.dataset.algo;
        pintarMapa();
        actualizarAvisoCorr();
    });
});

document.querySelectorAll('.jenny-met-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.jenny-met-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        estado.jenny_met = this.dataset.met;
        pintarMapa();
        actualizarAvisoCorr();
    });
});

document.querySelectorAll('.jenny-k-btn').forEach(btn => {
    btn.addEventListener('click', function () {
        document.querySelectorAll('.jenny-k-btn').forEach(b => b.classList.remove('active'));
        this.classList.add('active');
        estado.jenny_k = parseInt(this.dataset.k);
        pintarMapa();
    });
});

/* ══════════════════════════════════════════
   CAPA DE PUNTOS DE SALUD
   Muestra hospitales, centros de salud y
   consultorios locales como puntos en el mapa.
   ══════════════════════════════════════════ */

const COLORES_PUNTOS_SALUD = { hospital: '#c0392b', cs: '#1565c0', consultorio: '#27ae60', pac: '#e65100', cg: '#bf360c', asignado: '#90a4ae', sin_datos: '#cfd8dc' };
const RADIOS_SALUD         = { hospital: 8, cs: 6, consultorio: 4, pac: 6, cg: 7, asignado: 3, sin_datos: 3 };

function pintarPuntosSalud() {
    if (capaPuntosSalud) { map.removeLayer(capaPuntosSalud); capaPuntosSalud = null; }
    actualizarPanelDerecho();
    if (!estado.salud_puntos || typeof datosPuntosSalud === 'undefined') return;

    capaPuntosSalud = L.layerGroup();

    datosPuntosSalud.forEach(p => {
        const color  = COLORES_PUNTOS_SALUD[p.tipo] || '#9e9e9e';
        const radio  = RADIOS_SALUD[p.tipo] || 4;
        const marker = L.circleMarker([p.lat, p.lon], {
            radius:      radio,
            fillColor:   color,
            color:       '#fff',
            weight:      1.5,
            fillOpacity: 0.88,
        });
        marker.on('click', () => mostrarPuntoSalud(p));
        capaPuntosSalud.addLayer(marker);
    });

    capaPuntosSalud.addTo(map);
}

function mostrarPuntoSalud(p) {
    cambiarPestana('municipio');
    const color = COLORES_PUNTOS_SALUD[p.tipo] || '#9e9e9e';
    const labels = {
        hospital: 'Hospital', cs: 'Centro de Salud', consultorio: 'Consultorio Local',
        pac: 'Urgencias (PAC)', cg: 'Centro de Guardia',
        asignado: 'Sin centro · asignado a CS externo', sin_datos: 'Sin datos sanitarios'
    };
    const label  = labels[p.tipo] || p.tipo;

    let extra = '';
    if (p.tipo === 'hospital' && p.camas) extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">${p.camas} camas · ${p.clase || ''}</div>`;
    if (p.tipo === 'cs') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Zona: ${p.zona || ''}</div>`;
    if (p.tipo === 'consultorio') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Depende de: ${p.cs_padre || ''}</div>`;
    if (p.tipo === 'pac' || p.tipo === 'cg') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Ubicado en: ${p.ubicacion || ''}</div>`;
    if (p.tipo === 'asignado') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">CS asignado: ${p.nombre_cs || '—'}</div>`;
    if (p.tipo === 'sin_datos') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Sin información sanitaria disponible</div>`;

    document.getElementById('muni-detail').innerHTML = `
        <div class="muni-info" style="background:linear-gradient(135deg,${color},${color}bb)">
            <div class="muni-name">${p.nombre || label}</div>
            <div class="muni-prov">${label} · ${p.municipio || ''}</div>
            ${extra}
        </div>`;
    document.getElementById('grafico-comparacion-wrap').innerHTML =
        `<div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
    document.getElementById('grafico-evolucion-wrap').innerHTML =
        `<div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
    document.getElementById('grafico-vital-wrap').innerHTML =
        `<div class="no-selection"><div class="icon">🏥</div>Haz clic en un municipio para ver el movimiento natural</div>`;
}


/* ══════════════════════════════════════════
   RED VIARIA — capa de líneas sobre el mapa
   Fuente: OpenStreetMap / Overpass API
   ══════════════════════════════════════════ */

function pintarRedViaria() {
    if (capaRedViaria) { map.removeLayer(capaRedViaria); capaRedViaria = null; }
    actualizarPanelDerecho();
    if (!estado.red_viaria || typeof DATOS_CARRETERAS === 'undefined') return;

    capaRedViaria = L.layerGroup();

    // Dibujamos de más ancha a más fina para que las autopistas queden encima
    ['secondary', 'primary', 'trunk', 'motorway'].forEach(tipo => {
        const segs = DATOS_CARRETERAS[tipo];
        const meta = CARRETERAS_META.tipos[tipo];
        if (!segs || !segs.length || !meta) return;

        // Convertir [lon, lat] → [lat, lon] para Leaflet
        // L.polyline acepta array de arrays: crea un "multi-polyline" eficiente
        const latlngSegs = segs.map(seg => seg.map(c => [c[1], c[0]]));

        L.polyline(latlngSegs, {
            color:       meta.color,
            weight:      meta.weight,
            opacity:     0.85,
            smoothFactor: 2,
            interactive: false,
        }).addTo(capaRedViaria);
    });

    capaRedViaria.addTo(map);
}


document.getElementById('btn-turismo').addEventListener('click', function () {
    estado.turismo = !estado.turismo;
    this.classList.toggle('active', estado.turismo);
    pintarTurismo();

    // Al desactivar turismo: restaurar pestaña CyL y limpiar tarjeta
    if (!estado.turismo) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `
            <div class="no-selection">
                <div class="icon">🗺️</div>
                Haz clic en un municipio del mapa para ver sus datos
            </div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
        document.getElementById('grafico-vital-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">🏥</div>Haz clic en un municipio para ver el movimiento natural</div>`;
    }
});


document.getElementById('btn-estab-puntos').addEventListener('click', function () {
    estado.estab_puntos = !estado.estab_puntos;
    this.classList.toggle('active', estado.estab_puntos);
    pintarPuntosEstab();

    if (!estado.estab_puntos) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `
            <div class="no-selection">
                <div class="icon">🗺️</div>
                Haz clic en un municipio del mapa para ver sus datos
            </div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
        document.getElementById('grafico-vital-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">🏥</div>Haz clic en un municipio para ver el movimiento natural</div>`;
    }
});


document.getElementById('btn-salud').addEventListener('click', function () {
    estado.salud_puntos = !estado.salud_puntos;
    this.classList.toggle('active', estado.salud_puntos);
    pintarPuntosSalud();

    if (!estado.salud_puntos) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `
            <div class="no-selection">
                <div class="icon">🗺️</div>
                Haz clic en un municipio del mapa para ver sus datos
            </div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML =
            `<div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML =
            `<div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
        document.getElementById('grafico-vital-wrap').innerHTML =
            `<div class="no-selection"><div class="icon">🏥</div>Haz clic en un municipio para ver el movimiento natural</div>`;
    }
});


/* ══════════════════════════════════════════
   NATURALEZA — rutas de senderismo y espacios protegidos
   Fuente: OpenStreetMap / Overpass API
   ══════════════════════════════════════════ */

const COLORES_ESPACIO = {
    '1': '#1b5e20', '2': '#1b5e20',   // Parque Nacional
    '3': '#2e7d32', '4': '#2e7d32',   // Parque Natural
    '5': '#388e3c',                    // Reserva Natural
    '6': '#558b2f',                    // Paisaje Protegido
    '7': '#00695c',                    // ZEPA
    '8': '#0277bd',                    // ZEC
};

function pintarNaturaleza() {
    if (capaNaturaleza) { map.removeLayer(capaNaturaleza); capaNaturaleza = null; }
    actualizarPanelDerecho();
    if (!estado.naturaleza) return;

    capaNaturaleza = L.layerGroup();

    // Rutas de senderismo (GR/PR/SL) como polilíneas
    if (typeof RUTAS_NATURALEZA !== 'undefined' && typeof NATURALEZA_META !== 'undefined') {
        ['SL', 'PR', 'GR'].forEach(tipo => {
            const segs  = RUTAS_NATURALEZA[tipo] || [];
            const info  = NATURALEZA_META.tipos_GR[tipo];
            if (!segs.length || !info) return;

            segs.forEach(r => {
                const latlngs = r.coords.map(c => [c[1], c[0]]);
                L.polyline(latlngs, {
                    color:       info.color,
                    weight:      info.weight,
                    opacity:     0.9,
                    smoothFactor: 1.5,
                    interactive: true,
                }).bindTooltip(`${r.ref || tipo} · ${r.nombre || ''}`, { sticky: true })
                  .addTo(capaNaturaleza);
            });
        });
    }

    // Espacios Naturales Protegidos como marcadores de círculo
    if (typeof ESPACIOS_NATURALES !== 'undefined') {
        ESPACIOS_NATURALES.forEach(e => {
            const color  = COLORES_ESPACIO[e.pc] || '#33691e';
            const radius = ['1','2'].includes(e.pc) ? 9 : ['3','4'].includes(e.pc) ? 7 : 5;
            L.circleMarker([e.lat, e.lon], {
                radius,
                fillColor:   color,
                color:       '#fff',
                weight:      1.5,
                fillOpacity: 0.85,
            }).bindPopup(`
                <div style="font-size:13px;font-weight:600">${e.nombre}</div>
                <div style="font-size:11px;color:#555;margin-top:2px">${e.tipo}</div>
            `).addTo(capaNaturaleza);
        });
    }

    capaNaturaleza.addTo(map);
}


document.getElementById('btn-naturaleza').addEventListener('click', function () {
    estado.naturaleza = !estado.naturaleza;
    this.classList.toggle('active', estado.naturaleza);
    pintarNaturaleza();
    if (!estado.naturaleza) cambiarPestana('cyl');
});


/* ══════════════════════════════════════════
   RECICLAJE — puntos limpios y plantas de transferencia
   Fuente: Junta de CyL (datosabiertos.jcyl.es)
   ══════════════════════════════════════════ */

function pintarReciclaje() {
    if (capaReciclaje) { map.removeLayer(capaReciclaje); capaReciclaje = null; }
    actualizarPanelDerecho();
    if (!estado.reciclaje) return;

    capaReciclaje = L.layerGroup();

    // Plantas de Transferencia (naranja, debajo)
    if (typeof PLANTAS_TRANSFERENCIA !== 'undefined') {
        PLANTAS_TRANSFERENCIA.forEach(p => {
            L.circleMarker([p.lat, p.lon], {
                radius:      7,
                fillColor:   '#e65100',
                color:       '#fff',
                weight:      1.5,
                fillOpacity: 0.85,
            }).bindPopup(`
                <div style="font-size:13px;font-weight:600">${p.nombre}</div>
                <div style="font-size:11px;color:#555;margin-top:2px">Planta de Transferencia · ${p.municipio}</div>
                <div style="font-size:10px;color:#888;margin-top:2px">${p.direccion || ''}</div>
            `).addTo(capaReciclaje);
        });
    }

    // Puntos Limpios (verde oscuro, encima)
    if (typeof PUNTOS_LIMPIOS !== 'undefined') {
        PUNTOS_LIMPIOS.forEach(p => {
            L.circleMarker([p.lat, p.lon], {
                radius:      9,
                fillColor:   '#1b5e20',
                color:       '#fff',
                weight:      2,
                fillOpacity: 0.92,
            }).bindPopup(`
                <div style="font-size:13px;font-weight:600">${p.nombre}</div>
                <div style="font-size:11px;color:#555;margin-top:2px">Punto Limpio · ${p.municipio} (${p.provincia})</div>
                <div style="font-size:10px;color:#888;margin-top:2px">${p.direccion || ''}</div>
            `).addTo(capaReciclaje);
        });
    }

    capaReciclaje.addTo(map);
}


document.getElementById('btn-reciclaje').addEventListener('click', function () {
    estado.reciclaje = !estado.reciclaje;
    this.classList.toggle('active', estado.reciclaje);
    pintarReciclaje();
    if (!estado.reciclaje) cambiarPestana('cyl');
});


document.getElementById('btn-redviaria').addEventListener('click', function () {
    estado.red_viaria = !estado.red_viaria;
    this.classList.toggle('active', estado.red_viaria);
    pintarRedViaria();

    if (!estado.red_viaria) {
        cambiarPestana('cyl');
    }
});


/* ══════════════════════════════════════════
   15. INICIO DE LA APLICACIÓN
   ══════════════════════════════════════════ */

pintarMapa();
