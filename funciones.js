/*
 * Copyright © 2026 Thania Gutiérrez
 * Todos los derechos reservados.
 * Prohibida su reproducción, copia o uso fuera del dominio autorizado.
 */

// Verificación de dominio — solo funciona en los dominios autorizados
(function () {
    var dominios = [
        'castilla-y-leon-dashboard.netlify.app',
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
    valladolid: '#d81b60',
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


// Estado global de los filtros activos
const estado = {
    sexo:       'total',
    provincia:  'todas',
    intervalos: 5,
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


// Redibuja el mapa según los filtros activos
function pintarMapa() {
    const campo     = estado.sexo;
    const n         = estado.intervalos;
    const modoTodas = estado.provincia === 'todas';

    const municipiosFiltrados = getMunicipiosSinDuplicados();
    const valores = municipiosFiltrados.map(p => p[campo]);
    const breaks  = calcularBreaks(valores, n);

    const tonosPorProvincia = {};
    Object.entries(COLORES_PROVINCIA).forEach(([clave, color]) => {
        tonosPorProvincia[clave] = generarTonos(color, n);
    });

    if (capaGeo) map.removeLayer(capaGeo);

    capaGeo = L.geoJson(DATOS_GEO, {

        style: feature => {
            const p = feature.properties;
            const visible = modoTodas || p.prov_key === estado.provincia;

            if (!visible) {
                return { fillColor: '#e8eef4', fillOpacity: 0.10, color: '#ffffff', weight: 0.5 };
            }

            const tonos = tonosPorProvincia[p.prov_key] || generarTonos('#999999', n);

            return {
                fillColor:   getColorCoropleta(p[campo], breaks, tonos),
                fillOpacity: 0.80,
                color:   '#ffffff',
                weight:  0.5,
            };
        },

        onEachFeature: (feature, layer) => {
            const p = feature.properties;

            layer.bindTooltip(
                `<strong>${p.nombre}</strong><br>${p.provincia}<br>${p[campo].toLocaleString('es-ES')} hab.`,
                { sticky: true, className: 'mapa-tooltip' }
            );

            layer.on({
                click:     () => mostrarMunicipio(p),
                mouseover: e  => e.target.setStyle({ weight: 2, color: '#333', fillOpacity: 0.95 }),
                mouseout:  e  => capaGeo.resetStyle(e.target),
            });
        }

    }).addTo(map);

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

    let html = `<div class="legend-title">Habitantes · ${ETIQUETAS_SEXO[estado.sexo]}</div>`;
    for (let i = 0; i < n; i++) {
        const desde = (breaks[i]   ?? 0).toLocaleString('es-ES');
        const hasta = (breaks[i+1] ?? 0).toLocaleString('es-ES');
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
    const color = COLORES_PROVINCIA[p.prov_key] || '#1b6ca8';

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
        </div>`;

    actualizarGraficoComparacion(p);
}


// Actualiza el título del mapa según los filtros activos
function actualizarTituloMapa() {
    const selProv    = document.getElementById('sel-provincia');
    const nombreProv = selProv.options[selProv.selectedIndex].text;
    document.getElementById('map-title').textContent =
        `Población · ${nombreProv} · ${ETIQUETAS_SEXO[estado.sexo]} · 2025`;
}


// Eventos de los filtros
document.querySelectorAll('.radio-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.radio-btn').forEach(b => b.classList.remove('active'));
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


// Arrancar la aplicación
pintarMapa();
