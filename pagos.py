
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.express as px
from pathlib import Path

# 1. Conexión a PostgreSQL
engine = create_engine(
    "postgresql+psycopg2://karen@localhost:5432/Viz2026"
)

# 2. Consulta: únicamente datos de 2025 y 2026
# Se asume que Fecha está almacenada como YYYY-MM-DD.

query_variable = text("""
    SELECT
        TO_TIMESTAMP(LEFT(TRIM("Fecha"), 19), 'YYYY-MM-DD HH24:MI:SS')::date AS fecha,
        COALESCE(
            NULLIF(TRIM("Método de pago"), ''),
            'Sin método'
        ) AS metodo_pago,
        SUM("Importe") AS importe_total
    FROM pagos_punto_venta
    WHERE TRIM("Fecha") ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'
      AND LEFT(TRIM("Fecha"), 10) >= '2025-01-01'
      AND LEFT(TRIM("Fecha"), 10) < '2027-01-01'
    GROUP BY fecha, metodo_pago
    ORDER BY fecha, metodo_pago;
""")

with engine.connect() as connection:
    df = pd.read_sql(query_variable, connection)

if df.empty:
    raise ValueError(
        "No se encontraron pagos de 2025-2026. "
        "Revisa el formato de la columna Fecha."
    )

df["fecha"] = pd.to_datetime(df["fecha"])

# 3. Preparar los datos para las cuatro agrupaciones
def agrupar_pagos(data, periodo):
    data = data.copy()

    if periodo == "Día":
        data["periodo"] = data["fecha"].dt.strftime("%d/%m/%Y")
        data["orden_periodo"] = data["fecha"]

    elif periodo == "Semana":
        data["orden_periodo"] = (
            data["fecha"].dt.to_period("W").apply(lambda x: x.start_time)
        )
        data["periodo"] = data["orden_periodo"].dt.strftime("%d/%m/%Y")

    elif periodo == "Mes":
        data["orden_periodo"] = (
            data["fecha"].dt.to_period("M").dt.start_time
        )
        data["periodo"] = data["orden_periodo"].dt.strftime("%b %Y")

    else:  # Trimestre
        data["orden_periodo"] = (
            data["fecha"].dt.to_period("Q").dt.start_time
        )
        data["periodo"] = (
            data["orden_periodo"].dt.quarter.astype(str)
            .radd("T")
            + " "
            + data["orden_periodo"].dt.year.astype(str)
        )

    resumen = (
        data.groupby(
            ["orden_periodo", "periodo", "metodo_pago"],
            as_index=False
        )["importe_total"]
        .sum()
        .sort_values("orden_periodo")
    )

    return resumen


# 4. Crear una gráfica interactiva
periodo_inicial = "Mes"
resumen = agrupar_pagos(df, periodo_inicial)

fig = px.bar(
    resumen,
    x="periodo",
    y="importe_total",
    color="metodo_pago",
    barmode="group",
    title="Importe por método de pago",
    labels={
        "periodo": "Periodo",
        "importe_total": "Importe total",
        "metodo_pago": "Método de pago"
    },
    template="plotly_white",
    color_discrete_sequence=px.colors.qualitative.Set2
)

fig.update_layout(
    title_font_size=22,
    title_font_color="#172033",
    font=dict(family="Arial, sans-serif", color="#475569"),
    paper_bgcolor="white",
    plot_bgcolor="white",
    margin=dict(l=35, r=25, t=80, b=50),
    legend_title_text="Método de pago",
    xaxis=dict(showgrid=False, title=None),
    yaxis=dict(
        title="Importe total",
        tickprefix="$",
        tickformat=",.0f",
        gridcolor="#EDF1F5"
    )
)

graph_html = fig.to_html(
    full_html=False,
    include_plotlyjs=True,
    config={"responsive": True, "displaylogo": False}
)

# 5. Preparar el HTML
total_importe = df["importe_total"].sum()
total_pagos = len(df)
metodos = df["metodo_pago"].nunique()

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Pagos | Viz2026</title>
<style>
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #F4F7FB;
    color: #172033;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
}
.page { max-width: 1440px; margin: auto; padding: 38px 30px; }
.header {
    display: flex; justify-content: space-between; align-items: center;
    gap: 20px; flex-wrap: wrap; margin-bottom: 28px;
}
.eyebrow {
    color: #5265D5; font-size: 12px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 9px;
}
h1 { margin: 0; font-size: clamp(27px, 4vw, 36px); }
.subtitle { color: #64748B; margin-top: 10px; font-size: 14px; line-height: 1.6; }
.status {
    background: #E8F7EF; color: #18794E; border: 1px solid #C7EBD6;
    border-radius: 20px; padding: 9px 13px; font-size: 12px; font-weight: 600;
}
.kpis { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 18px; margin-bottom: 22px; }
.kpi, .panel {
    background: white; border: 1px solid #E5EAF1; border-radius: 16px;
    box-shadow: 0 3px 12px rgba(30,45,75,.03);
}
.kpi { padding: 23px; }
.kpi-label { color: #64748B; font-size: 13px; margin-bottom: 14px; }
.kpi-value { font-size: clamp(23px, 3vw, 31px); font-weight: 700; overflow-wrap: anywhere; }
.kpi-note { color: #94A3B8; font-size: 12px; margin-top: 9px; }
.panel { border-radius: 18px; padding: 20px 14px 10px; }
.panel-heading { padding: 2px 15px 0; }
.panel-heading h2 { margin: 0; font-size: 17px; }
.panel-heading p { color: #64748B; font-size: 13px; line-height: 1.6; }
.controls { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; padding: 16px 15px 0; }
label { font-size: 13px; font-weight: 600; color: #475569; }
select {
    border: 1px solid #D9E2EC; border-radius: 9px; background: white;
    padding: 10px 14px; color: #172033; font-size: 14px; cursor: pointer;
}
.footer { text-align: center; color: #94A3B8; font-size: 12px; margin-top: 22px; }
@media(max-width:700px) {
    .page { padding: 24px 14px; }
    .kpis { grid-template-columns: 1fr; gap: 12px; }
    .kpi { padding: 18px; }
    .panel { padding: 14px 5px 5px; }
}
</style>
</head>
<body>
<main class="page">
    <header class="header">
        <div>
            <div class="eyebrow">Punto de venta · Analytics</div>
            <h1>Análisis de pagos</h1>
            <div class="subtitle">Importes por método de pago · Periodo 2025–2026</div>
        </div>
        <div class="status">● Datos de PostgreSQL</div>
    </header>

    <section class="kpis">
        <article class="kpi">
            <div class="kpi-label">Importe total</div>
            <div class="kpi-value">__TOTAL__</div>
            <div class="kpi-note">Pagos del periodo seleccionado</div>
        </article>
        <article class="kpi">
            <div class="kpi-label">Registros agrupados</div>
            <div class="kpi-value">__PAGOS__</div>
            <div class="kpi-note">Filas de fecha y método de pago</div>
        </article>
        <article class="kpi">
            <div class="kpi-label">Métodos de pago</div>
            <div class="kpi-value">__METODOS__</div>
            <div class="kpi-note">Métodos distintos encontrados</div>
        </article>
    </section>

    <section class="panel">
        <div class="panel-heading">
            <h2>Importe por método de pago</h2>
            <p>Elige cómo agrupar los importes. Puedes seleccionar métodos en la leyenda.</p>
        </div>
        <div class="controls">
            <label for="periodo">Agrupar por:</label>
            <select id="periodo">
                <option value="Día">Día</option>
                <option value="Semana">Semana</option>
                <option value="Mes" selected>Mes</option>
                <option value="Trimestre">Trimestre</option>
            </select>
        </div>
        <div id="chart">__GRAPH__</div>
    </section>
    <footer class="footer">Viz2026 · PostgreSQL + SQLAlchemy + Plotly</footer>
</main>

<script>
const rawData = __DATA__;

document.getElementById("periodo").addEventListener("change", function() {
    const periodo = this.value;
    const rows = rawData.map(row => {
        const date = new Date(row.fecha + "T12:00:00");
        let label;

        if (periodo === "Día") {
            label = date.toLocaleDateString("es-MX");
        } else if (periodo === "Semana") {
            const day = (date.getDay() + 6) % 7;
            const monday = new Date(date);
            monday.setDate(date.getDate() - day);
            label = monday.toLocaleDateString("es-MX");
        } else if (periodo === "Mes") {
            label = date.toLocaleDateString("es-MX", {month: "short", year: "numeric"});
        } else {
            label = "T" + (Math.floor(date.getMonth() / 3) + 1) + " " + date.getFullYear();
        }

        return {...row, periodo: label, fecha_orden: date.getTime()};
    });

    const grouped = {};
    rows.forEach(row => {
        const key = row.periodo + "||" + row.metodo_pago;
        if (!grouped[key]) {
            grouped[key] = {
                periodo: row.periodo,
                metodo_pago: row.metodo_pago,
                importe_total: 0,
                fecha_orden: row.fecha_orden
            };
        }
        grouped[key].importe_total += Number(row.importe_total);
    });

    const data = Object.values(grouped).sort((a, b) => a.fecha_orden - b.fecha_orden);
    const methods = [...new Set(data.map(row => row.metodo_pago))];
    const periods = [...new Map(data.map(row => [row.periodo, row.fecha_orden])).entries()]
        .sort((a, b) => a[1] - b[1]).map(item => item[0]);

    const traces = methods.map(method => ({
        type: "bar",
        name: method,
        x: periods,
        y: periods.map(period => {
            const match = data.find(row => row.periodo === period && row.metodo_pago === method);
            return match ? match.importe_total : 0;
        }),
        hovertemplate: "<b>" + method + "</b><br>%{x}<br>Importe: $%{y:,.2f}<extra></extra>"
    }));

    Plotly.react("chart", traces, {
        title: {text: "Importe por método de pago", x: 0.02},
        barmode: "group",
        paper_bgcolor: "white",
        plot_bgcolor: "white",
        font: {family: "Arial, sans-serif", color: "#475569"},
        margin: {l: 45, r: 20, t: 70, b: 90},
        xaxis: {title: null, tickangle: -35, showgrid: false},
        yaxis: {title: "Importe total", tickprefix: "$", tickformat: ",.0f", gridcolor: "#EDF1F5"},
        legend: {orientation: "h", y: -0.25}
    }, {responsive: true, displaylogo: false});
});
</script>
</body>
</html>
"""

# Exportar los datos consultados para permitir que el selector funcione sin conexión
data_json = df.assign(
    fecha=df["fecha"].dt.strftime("%Y-%m-%d")
)[["fecha", "metodo_pago", "importe_total"]].to_json(
    orient="records", force_ascii=False
)

html_output = (
    html_template
    .replace("__GRAPH__", graph_html)
    .replace("__DATA__", data_json)
    .replace("__TOTAL__", f"${total_importe:,.2f}")
    .replace("__PAGOS__", f"{total_pagos:,}")
    .replace("__METODOS__", f"{metodos:,}")
)

Path("pagos.html").write_text(html_output, encoding="utf-8")

print("Archivo creado: pagos.html")
print(f"Importe total: ${total_importe:,.2f}")
print(f"Registros consultados: {total_pagos:,}")
print(f"Métodos de pago: {metodos}")
