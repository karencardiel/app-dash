
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text
from pathlib import Path
import json
import html


# ─────────────────────────────────────
# 1. CONEXIÓN A LA BASE DE DATOS
# ─────────────────────────────────────

engine = create_engine(
    "postgresql+psycopg2://karen@localhost:5432/Viz2026"
)


# ─────────────────────────────────────
# 2. CONSULTA DE SESIONES
# ─────────────────────────────────────

query = text("""
    SELECT
        "ID de sesión" AS id_sesion,
        "Abierta por" AS usuario,
        DATE_TRUNC('week', "Fecha de apertura")::date AS semana,
        EXTRACT(
            EPOCH FROM ("Fecha de cierre" - "Fecha de apertura")
        ) / 3600.0 AS duracion_horas
    FROM sesion_punto_venta
    WHERE "Fecha de apertura" IS NOT NULL
      AND "Fecha de cierre" IS NOT NULL
      AND "Fecha de cierre" >= "Fecha de apertura"
      AND "Abierta por" IS NOT NULL
      AND TRIM("Abierta por") <> ''
    ORDER BY semana, usuario;
""")

with engine.connect() as connection:
    df = pd.read_sql(query, connection)

if df.empty:
    raise ValueError("No se encontraron sesiones cerradas válidas.")


# ─────────────────────────────────────
# 3. PREPARAR LOS DATOS
# ─────────────────────────────────────

df["semana"] = pd.to_datetime(df["semana"])

resumen = (
    df.groupby(["semana", "usuario"], as_index=False)
    .agg(duracion_promedio=("duracion_horas", "mean"))
)

resumen["semana_label"] = resumen["semana"].dt.strftime("%d/%m/%Y")

promedio_general = df["duracion_horas"].mean()
total_sesiones = len(df)
total_usuarios = df["usuario"].nunique()

horas = int(promedio_general)
minutos = round((promedio_general - horas) * 60)

if minutos == 60:
    horas += 1
    minutos = 0

promedio_texto = f"{horas} h {minutos:02d} min"

usuarios = sorted(df["usuario"].unique().tolist())

# Resumen semanal para todos los usuarios
fig = px.line(
    resumen,
    x="semana",
    y="duracion_promedio",
    color="usuario",
    markers=True,
    custom_data=["semana_label"],
    labels={
        "semana": "Semana",
        "duracion_promedio": "Duración promedio (horas)",
        "usuario": "Usuario",
    },
)

fig.update_traces(
    line=dict(width=2.5),
    marker=dict(size=6),
    hovertemplate=(
        "<b>%{fullData.name}</b><br>"
        "Semana del %{customdata[0]}<br>"
        "Promedio: %{y:.2f} horas"
        "<extra></extra>"
    ),
)

fig.update_layout(
    template="plotly_white",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Arial, sans-serif", color="#344054", size=12),
    hovermode="closest",
    margin=dict(l=15, r=20, t=25, b=15),
    height=430,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        title_text="",
    ),
    xaxis=dict(
        title="Semana (inicio en lunes)",
        showgrid=False,
        tickformat="%d %b %Y",
        automargin=True,
    ),
    yaxis=dict(
        title="Horas promedio",
        rangemode="tozero",
        gridcolor="#EAECF0",
        zeroline=False,
    ),
)

chart_html = fig.to_html(
    full_html=False,
    include_plotlyjs=True,
    config={
        "responsive": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"],
    },
)

# Escapar los nombres para usarlos de forma segura en HTML
opciones_usuarios = "".join(
    f'<option value="{html.escape(usuario, quote=True)}">'
    f'{html.escape(usuario)}</option>'
    for usuario in usuarios
)

# ─────────────────────────────────────
# 4. DISEÑO DEL DASHBOARD
# ─────────────────────────────────────

documento = f"""
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>Sesiones | Punto de venta</title>

<style>
:root {{
    --bg: #f5f7fb;
    --card: #ffffff;
    --text: #172b4d;
    --muted: #667085;
    --border: #e8edf4;
    --primary: #4f46e5;
    --primary-light: #eef2ff;
    --green: #168568;
    --shadow: 0 3px 14px rgba(16, 24, 40, 0.04);
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                 Roboto, Arial, sans-serif;
}}

.container {{
    width: min(1320px, 100%);
    margin: 0 auto;
    padding: 36px 32px 48px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 20px;
    margin-bottom: 30px;
}}

.eyebrow {{
    color: var(--primary);
    font-size: 11px;
    font-weight: 750;
    text-transform: uppercase;
    letter-spacing: 1.4px;
    margin-bottom: 10px;
}}

h1 {{
    font-size: clamp(27px, 3vw, 36px);
    letter-spacing: -1.1px;
    margin: 0 0 9px;
    font-weight: 750;
}}

.subtitle {{
    color: var(--muted);
    font-size: 14px;
    line-height: 1.6;
    margin: 0;
}}

.status {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: #e8f7ef;
    color: #16734b;
    padding: 9px 13px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 650;
    white-space: nowrap;
}}

.status-dot {{
    width: 7px;
    height: 7px;
    background: #20a464;
    border-radius: 50%;
}}

.section-label {{
    color: #667085;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: .8px;
    text-transform: uppercase;
    margin: 0 0 14px;
}}

.kpis {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
    margin-bottom: 28px;
}}

.card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    box-shadow: var(--shadow);
}}

.kpi {{
    padding: 22px 24px;
    min-height: 150px;
}}

.kpi-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
}}

.kpi-label {{
    color: var(--muted);
    font-size: 13px;
    font-weight: 550;
}}

.kpi-icon {{
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border-radius: 11px;
    background: var(--primary-light);
    color: var(--primary);
    font-size: 17px;
    font-weight: 700;
}}

.kpi-value {{
    font-size: clamp(25px, 3vw, 34px);
    font-weight: 750;
    letter-spacing: -1px;
    line-height: 1.15;
}}

.kpi-help {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 9px;
}}

.chart-card {{
    padding: 25px 25px 12px;
}}

.chart-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 20px;
    margin-bottom: 8px;
}}

.chart-title {{
    font-size: 18px;
    font-weight: 720;
    margin: 0 0 7px;
    letter-spacing: -.3px;
}}

.chart-description {{
    color: var(--muted);
    font-size: 13px;
    line-height: 1.5;
    margin: 0;
}}

.filter {{
    display: flex;
    flex-direction: column;
    gap: 7px;
    min-width: 205px;
}}

.filter label {{
    color: #475467;
    font-size: 12px;
    font-weight: 650;
}}

select {{
    width: 100%;
    border: 1px solid #d0d5dd;
    background: white;
    color: var(--text);
    padding: 10px 34px 10px 12px;
    border-radius: 9px;
    font-size: 13px;
    outline: none;
}}

select:focus {{
    border-color: var(--primary);
    box-shadow: 0 0 0 3px #eef2ff;
}}

.chart-wrap {{
    width: 100%;
    min-width: 0;
}}

.insight {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-top: 22px;
    padding: 16px 18px;
    background: #f0f4ff;
    border: 1px solid #e0e7ff;
    border-radius: 12px;
    color: #344478;
    font-size: 13px;
    line-height: 1.6;
}}

.insight-icon {{
    font-weight: 800;
    color: var(--primary);
}}

.footer {{
    color: #98a2b3;
    text-align: center;
    font-size: 11px;
    margin-top: 28px;
}}

@media (max-width: 760px) {{
    .container {{
        padding: 24px 16px 32px;
    }}

    .header {{
        flex-direction: column;
        margin-bottom: 24px;
    }}

    .kpis {{
        grid-template-columns: 1fr;
        gap: 12px;
    }}

    .kpi {{
        min-height: auto;
        padding: 18px 20px;
    }}

    .kpi-top {{
        margin-bottom: 12px;
    }}

    .chart-card {{
        padding: 20px 12px 10px;
    }}

    .chart-header {{
        padding: 0 5px;
    }}

    .filter {{
        width: 100%;
    }}
}}
</style>
</head>

<body>
<main class="container">

    <header class="header">
        <div>
            <div class="eyebrow">Punto de venta · Analítica</div>
            <h1>Análisis de sesiones</h1>
            <p class="subtitle">
                Explora la duración promedio de las sesiones de trabajo
                y compara su evolución semanal por usuario.
            </p>
        </div>
        <div class="status">
            <span class="status-dot"></span>
            Datos procesados
        </div>
    </header>

    <div class="section-label">Resumen general</div>

    <section class="kpis">
        <article class="card kpi">
            <div class="kpi-top">
                <div class="kpi-label">Duración promedio</div>
                <div class="kpi-icon">◷</div>
            </div>
            <div class="kpi-value">{promedio_texto}</div>
            <div class="kpi-help">Por sesión cerrada</div>
        </article>

        <article class="card kpi">
            <div class="kpi-top">
                <div class="kpi-label">Sesiones analizadas</div>
                <div class="kpi-icon">▤</div>
            </div>
            <div class="kpi-value">{total_sesiones:,}</div>
            <div class="kpi-help">Registros con duración válida</div>
        </article>

        <article class="card kpi">
            <div class="kpi-top">
                <div class="kpi-label">Usuarios registrados</div>
                <div class="kpi-icon">♙</div>
            </div>
            <div class="kpi-value">{total_usuarios:,}</div>
            <div class="kpi-help">Con sesiones válidas</div>
        </article>
    </section>

    <section class="card chart-card">
        <div class="chart-header">
            <div>
                <h2 class="chart-title">Evolución semanal</h2>
                <p class="chart-description">
                    Cada punto representa el promedio de duración de las
                    sesiones abiertas por un usuario durante esa semana.
                </p>
            </div>

            <div class="filter">
                <label for="userFilter">Filtrar por usuario</label>
                <select id="userFilter">
                    <option value="__all__">Todos los usuarios</option>
                    {opciones_usuarios}
                </select>
            </div>
        </div>

        <div class="chart-wrap">
            {chart_html}
        </div>

        <div class="insight">
            <span class="insight-icon">i</span>
            <div>
                <strong>Cómo interpretar la gráfica</strong><br>
                Compara los cambios en la duración promedio de cada usuario.
                Las semanas se agrupan de lunes a domingo. Las sesiones que
                aún están abiertas se excluyen del análisis.
            </div>
        </div>
    </section>

    <footer class="footer">
        Dashboard de sesiones · PostgreSQL · Visualización con Plotly
    </footer>

</main>

<script>
const userFilter = document.getElementById("userFilter");
const chart = document.querySelector(".chart-wrap .plotly-graph-div");

userFilter.addEventListener("change", function () {{
    const selected = this.value;

    if (!chart) return;

    const visibility = chart.data.map(trace => {{
        return selected === "__all__" || trace.name === selected;
    }});

    Plotly.restyle(chart, {{ visible: visibility }});
}});
</script>

</body>
</html>
"""

# ─────────────────────────────────────
# 5. GUARDAR EL HTML
# ─────────────────────────────────────

salida = Path(__file__).resolve().parent / "sesiones.html"
salida.write_text(documento, encoding="utf-8")

print(f"Dashboard generado: {salida}")
print(f"Sesiones analizadas: {total_sesiones:,}")
print(f"Usuarios: {total_usuarios:,}")
print(f"Duración promedio: {promedio_texto}")
