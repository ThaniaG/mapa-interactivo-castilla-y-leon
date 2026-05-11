/*
 * Copyright © 2026 Thania Gutiérrez
 * Todos los derechos reservados.
 * Prohibida su reproducción, copia o uso fuera del dominio autorizado.
 */

// Verificación de dominio — solo funciona en los dominios autorizados
(function () {
    var dominios = [
        'castilla-y-leon-dashboard.netlify.app',
        'thaniag.github.io',
        'localhost',
        '127.0.0.1'
    ];
    if (dominios.indexOf(window.location.hostname) === -1) {
        document.body.innerHTML = '<p style="font-family:sans-serif;padding:2rem;color:#c00">Este proyecto no está autorizado para ejecutarse en este dominio.</p>';
        throw new Error('Dominio no autorizado');
    }
})();


// Coordenadas centrales de cada provincia (para las etiquetas del mapa)
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

// Color identificativo de cada provincia
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

// Convierte hex a RGB
function hexARgb(hex) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return [r, g, b];
}

// Mezcla un color con blanco según un factor (0=blanco, 1=color original)
function mezclarConBlanco(hex, factor) {
    const [r, g, b] = hexARgb(hex);
    const nr = Math.round(255 + (r - 255) * factor);
    const ng = Math.round(255 + (g - 255) * factor);
    const nb = Math.round(255 + (b - 255) * factor);
    return `rgb(${nr},${ng},${nb})`;
}

// Genera n tonos de un color base, de claro a oscuro
function generarTonos(colorBase, n) {
    const tonos = [];
    for (let i = 0; i < n; i++) {
        const factor = 0.15 + (0.85 * i / (n - 1));
        tonos.push(mezclarConBlanco(colorBase, factor));
    }
    return tonos;
}

// Colores por categoría turística
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

let capaTurismo = null;

// Colores y etiquetas para establecimientos turísticos
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

let capaPuntosEstab = null;

// Colores para cobertura sanitaria (mapa coroplético)
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

let capaPuntosSalud = null;

const ETIQUETAS_SEXO = {
    total:   'Total',
    hombres: 'Hombres',
    mujeres: 'Mujeres'
};

const LIMITES_CYL = L.latLngBounds([38.5, -7.5], [44.0, -1.0]);


// Inicializar mapa Leaflet centrado en Castilla y León
const map = L.map('map', {
    center: [41.65, -4.72],
    zoom: 7,
    zoomControl: true,
    maxBounds: LIMITES_CYL,
    maxBoundsViscosity: 0.8,
    minZoom: 6,
});

L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
    className: 'osm-tiles'
}).addTo(map);


// Inicializar gráfico de barras horizontales por provincia
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


// Estado global de los filtros activos
const estado = {
    sexo:           'total',
    provincia:      'todas',
    intervalos:     5,
    variable:       'poblacion',
    anio_subv:      'total',
    tipo_estab:     'total',
    turismo:        false,
    estab_puntos:   false,
    salud_puntos:   false,
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

let capaGeo      = null;
let capaEtiquetas = null;


// Devuelve los municipios sin duplicados, aplicando el filtro de provincia
function getMunicipiosSinDuplicados(soloProvinciaActiva = true) {
    const vistos = {};
    DATOS_GEO.features.forEach(f => {
        const p = f.properties;
        if (soloProvinciaActiva && estado.provincia !== 'todas' && p.prov_key !== estado.provincia) return;
        if (!vistos[p.codigo]) vistos[p.codigo] = { ...p };
    });
    return Object.values(vistos);
}

// Calcula los límites de los intervalos usando cuantiles
function calcularBreaks(valores, n) {
    const ordenados = [...valores].filter(v => v > 0).sort((a, b) => a - b);
    const breaks = [];
    for (let i = 0; i <= n; i++) {
        const idx = Math.round((i / n) * (ordenados.length - 1));
        breaks.push(ordenados[idx] || 0);
    }
    return breaks;
}

// Devuelve el color correspondiente a un valor según los intervalos
function getColorCoropleta(valor, breaks, paleta) {
    for (let i = paleta.length - 1; i >= 0; i--) {
        if (valor >= breaks[i]) return paleta[i];
    }
    return paleta[0];
}

// Devuelve el valor de la variable activa para un municipio
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
    const edades = (typeof DATOS_EDADES !== 'undefined') && DATOS_EDADES[props.codigo];
    if (!edades) return 0;
    const sufijo = estado.sexo === 'hombres' ? '_h' : estado.sexo === 'mujeres' ? '_m' : '';
    return edades[estado.variable + sufijo] || 0;
}


// Redibuja el mapa según los filtros activos
function pintarMapa() {
    const n         = estado.intervalos;
    const modoTodas = estado.provincia === 'todas';

    const todosMunicipios = getMunicipiosSinDuplicados(false);
    const valores = todosMunicipios.map(p => getValorVariable(p));
    const breaks  = calcularBreaks(valores, n);

    const municipiosFiltrados = getMunicipiosSinDuplicados();

    const tonosValladolid = generarTonos('#7b2d42', n);
    const tonosGris       = generarTonos('#8a9baa', n);

    if (capaGeo) map.removeLayer(capaGeo);

    capaGeo = L.geoJson(DATOS_GEO, {

        style: feature => {
            const p = feature.properties;

            // Cobertura sanitaria: colores categóricos fijos
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
                };
            }

            if (modoTodas) {
                const tonos = p.prov_key === 'valladolid' ? tonosValladolid : tonosGris;
                return {
                    fillColor:   getColorCoropleta(getValorVariable(p), breaks, tonos),
                    fillOpacity: 0.80,
                    color:       '#ffffff',
                    weight:      0.4,
                };
            }

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
            };
        },

        onEachFeature: (feature, layer) => {
            const p = feature.properties;

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
                            : estado.variable === 'cobertura_salud'
                                ? (() => { const s = (typeof DATOS_SALUD !== 'undefined') && DATOS_SALUD[p.codigo]; return LABELS_SALUD[s ? s.tipo : 'sin_datos']; })()
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


// Muestra los nombres de provincia sobre el mapa
function actualizarEtiquetasProvincias() {
    if (capaEtiquetas) map.removeLayer(capaEtiquetas);

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


// Actualiza la leyenda con los rangos de color
function actualizarLeyenda(breaks) {
    const legend = document.getElementById('map-legend');
    const n      = estado.intervalos;

    const colorEjemplo = estado.provincia === 'todas'
        ? '#64748b'
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
    };
    const formatBreak = v => {
        if (estado.variable === 'poblacion') return (v ?? 0).toLocaleString('es-ES');
        if (estado.variable === 'renta_media' || estado.variable === 'subvenciones')
            return (v ?? 0).toLocaleString('es-ES') + ' €';
        return (v ?? 0).toFixed(1);
    };

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


// Actualiza las tarjetas KPI con los totales de población
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


// Actualiza el gráfico de barras con la población por provincia
function actualizarGrafico() {
    const campo = estado.sexo;

    const todosSinDup = getMunicipiosSinDuplicados(false);

    const totales = {};
    Object.keys(NOMBRES_PROVINCIA).forEach(k => totales[k] = 0);
    todosSinDup.forEach(m => {
        totales[m.prov_key] = (totales[m.prov_key] || 0) + m[campo];
    });

    const ordenadas = Object.entries(totales).sort((a, b) => b[1] - a[1]);

    graficoPoblacion.data.labels                       = ordenadas.map(([k]) => NOMBRES_PROVINCIA[k]);
    graficoPoblacion.data.datasets[0].data             = ordenadas.map(([, v]) => v);
    graficoPoblacion.data.datasets[0].backgroundColor  = ordenadas.map(([k]) => COLORES_PROVINCIA[k]);
    graficoPoblacion.update();
}


// Gráfico de comparación hombres vs mujeres del municipio seleccionado
let graficoComparacion = null;

function actualizarGraficoComparacion(p) {
    const wrap = document.getElementById('grafico-comparacion-wrap');

    if (graficoComparacion) {
        graficoComparacion.destroy();
        graficoComparacion = null;
    }

    wrap.innerHTML = `<div style="position:relative;height:110px"><canvas id="chart-comparacion"></canvas></div>`;

    const ctx = document.getElementById('chart-comparacion').getContext('2d');
    graficoComparacion = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Hombres', 'Mujeres'],
            datasets: [{
                data: [p.hombres, p.mujeres],
                backgroundColor: ['#1e88e5', '#d81b60'],
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


// Muestra la información del municipio seleccionado en el panel derecho
function mostrarMunicipio(p) {
    cambiarPestana('municipio');
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

    // Gráfico H vs M: solo para variables con desglose por sexo
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

    actualizarGraficoEvolucion(p);
}


// Gráfico de evolución de población 1996-2025 del municipio seleccionado
let graficoEvolucion = null;

function actualizarGraficoEvolucion(p) {
    const wrap = document.getElementById('grafico-evolucion-wrap');

    if (typeof DATOS_EVOLUCION === 'undefined' || !DATOS_EVOLUCION[p.codigo]) {
        wrap.innerHTML = '<div class="no-selection" style="font-size:12px;color:#888">Sin datos de evolución para este municipio</div>';
        return;
    }

    const ev    = DATOS_EVOLUCION[p.codigo];
    const color = COLORES_PROVINCIA[p.prov_key] || '#1b6ca8';

    if (graficoEvolucion) { graficoEvolucion.destroy(); graficoEvolucion = null; }

    wrap.innerHTML = `<div style="position:relative;height:190px"><canvas id="chart-evolucion"></canvas></div>`;

    const ctx = document.getElementById('chart-evolucion').getContext('2d');
    graficoEvolucion = new Chart(ctx, {
        type: 'line',
        data: {
            labels: ev.años,
            datasets: [
                { label: 'Total',   data: ev.total,   borderColor: color,      backgroundColor: color+'22', borderWidth: 2, pointRadius: 2, fill: true,  tension: 0.3 },
                { label: 'Hombres', data: ev.hombres, borderColor: '#1e88e5',  borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.3, borderDash: [4,3] },
                { label: 'Mujeres', data: ev.mujeres, borderColor: '#d81b60',  borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.3, borderDash: [4,3] },
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true, position: 'top', labels: { font: { size: 10 }, boxWidth: 20, padding: 8 } },
                tooltip: { callbacks: { label: ctx => ` ${ctx.dataset.label}: ${ctx.parsed.y.toLocaleString('es-ES')} hab.` } }
            },
            scales: {
                x: { ticks: { font: { size: 9 }, maxTicksLimit: 10 }, grid: { color: '#f0f4f8' } },
                y: { ticks: { font: { size: 9 }, callback: v => v >= 1000 ? (v/1000).toFixed(0)+'k' : v }, grid: { color: '#f0f4f8' } }
            }
        }
    });
}


// Actualiza el título del mapa según los filtros activos
function actualizarTituloMapa() {
    const selProv    = document.getElementById('sel-provincia');
    const nombreProv = selProv.options[selProv.selectedIndex].text;
    const ETIQUETAS_TIPO_ESTAB2 = { total: 'Todos', bares: 'Bares', restaurantes: 'Restaurantes', cafeterias: 'Cafeterías', alojamiento: 'Alojamiento' };
    const TITULOS_VAR = { poblacion: 'Población', porc_65: '% Mayores de 65', ind_envej: 'Índice de envejecimiento', renta_media: 'Renta media por persona', subvenciones: 'Subvenciones diputaciones', establecimientos: `Establecimientos · ${ETIQUETAS_TIPO_ESTAB2[estado.tipo_estab]}`, cobertura_salud: 'Cobertura sanitaria' };
    const varNombre  = TITULOS_VAR[estado.variable] || estado.variable;
    const sinSexo    = ['renta_media', 'subvenciones', 'establecimientos', 'cobertura_salud'].includes(estado.variable);
    const sufSexo    = (estado.sexo !== 'total' && !sinSexo) ? ` · ${ETIQUETAS_SEXO[estado.sexo]}` : '';
    const anio       = estado.variable === 'renta_media' ? '2023' : estado.variable === 'subvenciones' ? (estado.anio_subv === 'total' ? '2022-2025' : estado.anio_subv) : '2025';
    document.getElementById('map-title').textContent =
        `${varNombre} · ${nombreProv}${sufSexo} · ${anio}`;
}


// Cambia la pestaña activa del panel derecho
function cambiarPestana(tabId) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.querySelector(`.tab-btn[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(`tab-${tabId}`).classList.add('active');
    if (tabId === 'graficos') {
        if (graficoComparacion) graficoComparacion.resize();
        if (graficoEvolucion)   graficoEvolucion.resize();
        const btnGraficos = document.querySelector('.tab-btn[data-tab="graficos"]');
        if (btnGraficos) btnGraficos.removeAttribute('data-ready');
    } else if (tabId === 'cyl') {
        graficoPoblacion.resize();
    }
}

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => cambiarPestana(btn.dataset.tab));
});


// Eventos de los filtros
document.querySelectorAll('#radio-sexo .radio-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('#radio-sexo .radio-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        estado.sexo = btn.dataset.val;
        pintarMapa();
    });
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
    document.getElementById('filtro-anio').style.display       = esSubv  ? '' : 'none';
    document.getElementById('div-anio').style.display          = esSubv  ? '' : 'none';
    document.getElementById('filtro-tipo-estab').style.display = esEstab ? '' : 'none';
    document.getElementById('div-tipo-estab').style.display    = esEstab ? '' : 'none';
    if (!esSubv)  { estado.anio_subv  = 'total'; document.getElementById('sel-anio').value = 'total'; }
    if (!esEstab) { estado.tipo_estab = 'total'; document.getElementById('sel-tipo-estab').value = 'total'; }

    const conSexo = ['poblacion', 'porc_65', 'ind_envej'].includes(estado.variable);
    const secComp = document.getElementById('seccion-comparacion');
    if (conSexo) {
        secComp.style.display = '';
    } else {
        if (graficoComparacion) { graficoComparacion.destroy(); graficoComparacion = null; }
        secComp.style.display = 'none';
    }

    pintarMapa();
});

document.getElementById('sel-tipo-estab').addEventListener('change', e => {
    estado.tipo_estab = e.target.value;
    pintarMapa();
});

document.getElementById('sel-anio').addEventListener('change', e => {
    estado.anio_subv = e.target.value;
    pintarMapa();
});


// Muestra u oculta los puntos turísticos (museos y monumentos de la Junta de CyL)
function pintarTurismo() {
    if (capaTurismo) { map.removeLayer(capaTurismo); capaTurismo = null; }
    actualizarPanelDerecho();
    if (!estado.turismo || typeof datosTurismo === 'undefined') return;

    capaTurismo = L.layerGroup();

    datosTurismo.forEach(p => {
        const color  = COLORES_TURISMO[p.categoria] || '#9e9e9e';
        const marker = L.circleMarker([p.lat, p.lon], {
            radius: 5, fillColor: color, color: '#fff', weight: 1, fillOpacity: 0.85,
        });

        marker.on('click', () => mostrarPuntoTuristico(p));
        capaTurismo.addLayer(marker);
    });

    capaTurismo.addTo(map);
}

// Muestra la información de un punto turístico
function mostrarPuntoTuristico(p) {
    cambiarPestana('municipio');
    const color    = COLORES_TURISMO[p.categoria] || '#9e9e9e';
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

    document.getElementById('grafico-comparacion-wrap').innerHTML =
        '<div class="no-selection" style="font-size:12px;color:#aaa">No disponible para puntos turísticos</div>';
    document.getElementById('grafico-evolucion-wrap').innerHTML =
        '<div class="no-selection" style="font-size:12px;color:#aaa">No disponible para puntos turísticos</div>';
}


// Muestra u oculta los puntos de establecimientos turísticos
function pintarPuntosEstab() {
    if (capaPuntosEstab) { map.removeLayer(capaPuntosEstab); capaPuntosEstab = null; }
    actualizarPanelDerecho();
    if (!estado.estab_puntos || typeof datosPuntosEstab === 'undefined') return;

    capaPuntosEstab = L.layerGroup();

    datosPuntosEstab.forEach(p => {
        const color  = COLORES_ESTAB[p.tipo] || '#9e9e9e';
        const marker = L.circleMarker([p.lat, p.lon], {
            radius: 4, fillColor: color, color: '#fff', weight: 1, fillOpacity: 0.85,
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
}


// Colores y tamaños para la capa de puntos de salud
const COLORES_PUNTOS_SALUD = { hospital: '#c0392b', cs: '#1565c0', consultorio: '#27ae60', pac: '#e65100', cg: '#bf360c', asignado: '#90a4ae', sin_datos: '#cfd8dc' };
const RADIOS_SALUD         = { hospital: 8, cs: 6, consultorio: 4, pac: 6, cg: 7, asignado: 3, sin_datos: 3 };

// Muestra u oculta los puntos de cobertura sanitaria
function pintarPuntosSalud() {
    if (capaPuntosSalud) { map.removeLayer(capaPuntosSalud); capaPuntosSalud = null; }
    actualizarPanelDerecho();
    if (!estado.salud_puntos || typeof datosPuntosSalud === 'undefined') return;

    capaPuntosSalud = L.layerGroup();

    datosPuntosSalud.forEach(p => {
        const color  = COLORES_PUNTOS_SALUD[p.tipo] || '#9e9e9e';
        const radio  = RADIOS_SALUD[p.tipo] || 4;
        const marker = L.circleMarker([p.lat, p.lon], {
            radius: radio, fillColor: color, color: '#fff', weight: 1.5, fillOpacity: 0.88,
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
    if (p.tipo === 'cs')          extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Zona: ${p.zona || ''}</div>`;
    if (p.tipo === 'consultorio') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Depende de: ${p.cs_padre || ''}</div>`;
    if (p.tipo === 'pac' || p.tipo === 'cg') extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Ubicado en: ${p.ubicacion || ''}</div>`;
    if (p.tipo === 'asignado')   extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">CS asignado: ${p.nombre_cs || '—'}</div>`;
    if (p.tipo === 'sin_datos')  extra = `<div class="muni-prov" style="font-size:11px;opacity:0.85">Sin información sanitaria disponible</div>`;

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
}


// Gestiona qué se muestra en la pestaña CyL según la capa o variable activa
function actualizarPanelDerecho() {
    const secKpis    = document.getElementById('seccion-kpis');
    const secGrafico = document.getElementById('seccion-grafico-prov');
    let secTurismo   = document.getElementById('seccion-turismo-leyenda');
    let secEstab     = document.getElementById('seccion-estab-resumen');

    // Turismo activo
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

    // Capa puntos establecimientos activa
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

    // Capa puntos salud activa
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

    // Variable cobertura sanitaria seleccionada
    if (estado.variable === 'cobertura_salud') {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';

        const conteoN = { hospital: 0, centro_salud: 0, consultorio: 0, asignado: 0, sin_datos: 0 };
        if (typeof DATOS_SALUD !== 'undefined') {
            Object.values(DATOS_SALUD).forEach(m => { conteoN[m.tipo] = (conteoN[m.tipo] || 0) + 1; });
        }

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

    // Variable establecimientos seleccionada
    if (estado.variable === 'establecimientos') {
        secKpis.style.display    = 'none';
        secGrafico.style.display = 'none';
        if (secTurismo) secTurismo.style.display = 'none';

        const COLORES_TIPO = { bares: '#f59e0b', restaurantes: '#10b981', cafeterias: '#92400e', alojamiento: '#3b82f6' };
        const LABELS_TIPO  = { bares: 'Bares', restaurantes: 'Restaurantes', cafeterias: 'Cafeterías', alojamiento: 'Alojamiento' };
        const TIPOS = ['bares', 'restaurantes', 'cafeterias', 'alojamiento'];

        let totales = { bares: 0, restaurantes: 0, cafeterias: 0, alojamiento: 0 };
        let sinDatos = 0;
        const totalMunicipios = 2248;

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
            const color   = COLORES_TIPO[t];
            const opacity = (tipoActivo === 'total' || tipoActivo === t) ? '1' : '0.45';
            const fontW   = (tipoActivo === 'total' || tipoActivo === t) ? '700' : '400';
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

    // Modo normal: restaurar KPIs y gráfico
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

    if (veniaDeModo) cambiarPestana('cyl');
}


document.getElementById('btn-turismo').addEventListener('click', function () {
    estado.turismo = !estado.turismo;
    this.classList.toggle('active', estado.turismo);
    pintarTurismo();

    if (!estado.turismo) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `
            <div class="no-selection"><div class="icon">🗺️</div>Haz clic en un municipio del mapa para ver sus datos</div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
    }
});

document.getElementById('btn-estab-puntos').addEventListener('click', function () {
    estado.estab_puntos = !estado.estab_puntos;
    this.classList.toggle('active', estado.estab_puntos);
    pintarPuntosEstab();

    if (!estado.estab_puntos) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `
            <div class="no-selection"><div class="icon">🗺️</div>Haz clic en un municipio del mapa para ver sus datos</div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML = `
            <div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
    }
});

document.getElementById('btn-salud').addEventListener('click', function () {
    estado.salud_puntos = !estado.salud_puntos;
    this.classList.toggle('active', estado.salud_puntos);
    pintarPuntosSalud();

    if (!estado.salud_puntos) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `
            <div class="no-selection"><div class="icon">🗺️</div>Haz clic en un municipio del mapa para ver sus datos</div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML =
            `<div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML =
            `<div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
    }
});


// Arrancar la aplicación
pintarMapa();
