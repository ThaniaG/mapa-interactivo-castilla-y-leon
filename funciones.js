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

// Capa de puntos turísticos
let capaTurismo = null;

// Estado global de los filtros activos
const estado = {
    sexo:       'total',
    provincia:  'todas',
    intervalos: 5,
    variable:   'poblacion',
    anio_subv:  'total',
    turismo:    false,
};

let capaGeo      = null;
let capaEtiquetas = null;


// Devuelve los municipios sin duplicados (un registro por código INE)
// y aplicando el filtro de provincia si está activo
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

// Devuelve el valor de la variable activa para un municipio dado
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
    const TITULOS_VAR = {
        poblacion:     `Habitantes · ${ETIQUETAS_SEXO[estado.sexo]}`,
        porc_65:       `% Mayores de 65${sufSexo}`,
        ind_envej:     `Índice de envejecimiento${sufSexo}`,
        renta_media:   'Renta media por persona (€)',
        subvenciones:  'Subvenciones recibidas 2022-2025 (€)',
    };
    const formatBreak = v => {
        if (estado.variable === 'poblacion') return (v ?? 0).toLocaleString('es-ES');
        if (estado.variable === 'renta_media' || estado.variable === 'subvenciones')
            return (v ?? 0).toLocaleString('es-ES') + ' €';
        return (v ?? 0).toFixed(1);
    };

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

    wrap.innerHTML = `<div style="position:relative;height:90px"><canvas id="chart-comparacion"></canvas></div>`;

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
        </div>`;

    actualizarGraficoComparacion(p);
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

    wrap.innerHTML = `<div style="position:relative;height:160px"><canvas id="chart-evolucion"></canvas></div>`;

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
    const TITULOS_VAR = { poblacion: 'Población', porc_65: '% Mayores de 65', ind_envej: 'Índice de envejecimiento', renta_media: 'Renta media por persona', subvenciones: 'Subvenciones diputaciones' };
    const varNombre  = TITULOS_VAR[estado.variable] || estado.variable;
    const sinSexo    = ['renta_media', 'subvenciones'].includes(estado.variable);
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
    if (tabId === 'municipio') {
        if (graficoComparacion) graficoComparacion.resize();
        if (graficoEvolucion)   graficoEvolucion.resize();
    } else {
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
    const esSubv = estado.variable === 'subvenciones';
    document.getElementById('filtro-anio').style.display = esSubv ? '' : 'none';
    document.getElementById('div-anio').style.display    = esSubv ? '' : 'none';
    if (!esSubv) { estado.anio_subv = 'total'; document.getElementById('sel-anio').value = 'total'; }
    pintarMapa();
});

document.getElementById('sel-anio').addEventListener('change', e => {
    estado.anio_subv = e.target.value;
    pintarMapa();
});


document.getElementById('btn-turismo').addEventListener('click', function () {
    estado.turismo = !estado.turismo;
    this.classList.toggle('active', estado.turismo);
    pintarTurismo();
});

// Muestra u oculta los puntos turísticos oficiales (museos y monumentos de la Junta de CyL)
function pintarTurismo() {
    if (capaTurismo) { map.removeLayer(capaTurismo); capaTurismo = null; }
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
    actualizarPanelTurismo();
}

// Muestra la información de un punto turístico en el panel derecho
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

// Muestra u oculta la leyenda de turismo en la pestaña Castilla y León
function actualizarPanelTurismo() {
    const secKpis    = document.getElementById('seccion-kpis');
    const secGrafico = document.getElementById('seccion-grafico-prov');
    let   secLeyenda = document.getElementById('seccion-turismo-leyenda');

    if (!estado.turismo) {
        if (secLeyenda) secLeyenda.style.display = 'none';
        secKpis.style.display    = '';
        secGrafico.style.display = '';
        return;
    }

    secKpis.style.display    = 'none';
    secGrafico.style.display = 'none';

    const conteo = {};
    if (typeof datosTurismo !== 'undefined') {
        datosTurismo.forEach(p => { conteo[p.categoria] = (conteo[p.categoria] || 0) + 1; });
    }
    const ordenadas = Object.entries(conteo).sort((a, b) => b[1] - a[1]);
    const total     = ordenadas.reduce((s, [, n]) => s + n, 0);

    let html = `<div class="kpi-title" style="margin-bottom:8px">Puntos turísticos · Castilla y León</div>`;
    ordenadas.forEach(([cat, n]) => {
        const color = COLORES_TURISMO[cat] || '#9e9e9e';
        html += `<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid #f0f4f8">
            <div style="width:11px;height:11px;border-radius:50%;background:${color};flex-shrink:0;border:1px solid #fff;box-shadow:0 0 0 1px ${color}55"></div>
            <span style="flex:1;font-size:12px;color:#2d3f50">${cat}</span>
            <span style="font-size:12px;font-weight:600;color:#2d3f50">${n.toLocaleString('es-ES')}</span>
        </div>`;
    });
    html += `<div style="display:flex;align-items:center;gap:8px;padding:8px 0 4px">
        <div style="width:11px;height:11px;flex-shrink:0"></div>
        <span style="flex:1;font-size:12px;font-weight:700;color:#1b6ca8">Total</span>
        <span style="font-size:13px;font-weight:700;color:#1b6ca8">${total.toLocaleString('es-ES')}</span>
    </div>
    <div style="font-size:10px;color:#aaa;margin-top:2px">Fuente: datosabiertos.jcyl.es · Junta de CyL</div>`;

    if (!secLeyenda) {
        secLeyenda = document.createElement('div');
        secLeyenda.id = 'seccion-turismo-leyenda';
        secLeyenda.className = 'panel-section';
        document.getElementById('tab-cyl').appendChild(secLeyenda);
    }
    secLeyenda.innerHTML = html;
    secLeyenda.style.display = '';
}

document.getElementById('btn-turismo').addEventListener('click', function () {
    estado.turismo = !estado.turismo;
    this.classList.toggle('active', estado.turismo);
    pintarTurismo();
    if (!estado.turismo) {
        cambiarPestana('cyl');
        document.getElementById('muni-detail').innerHTML = `<div class="no-selection"><div class="icon">🗺️</div>Haz clic en un municipio del mapa para ver sus datos</div>`;
        document.getElementById('grafico-comparacion-wrap').innerHTML = `<div class="no-selection"><div class="icon">👆</div>Haz clic en un municipio para ver la comparación</div>`;
        document.getElementById('grafico-evolucion-wrap').innerHTML = `<div class="no-selection"><div class="icon">📈</div>Haz clic en un municipio para ver su evolución</div>`;
    }
});

// Arrancar la aplicación
pintarMapa();
