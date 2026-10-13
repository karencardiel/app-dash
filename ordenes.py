
import pandas as pd
from sqlalchemy import create_engine, text
import plotly.graph_objects as go
from pathlib import Path
import json

# --------------------------------------------------
# 1. DATABASE CONNECTION
# --------------------------------------------------

engine = create_engine(
    "postgresql+psycopg2://karen@localhost:5432/Viz2026"
)

# The SQL query is stored in the required variable
query_variable = text("""
    SELECT
        EXTRACT(MONTH FROM "Fecha")::INTEGER AS mes,
        (FLOOR((EXTRACT(DAY FROM "Fecha") - 1) / 7) + 1)::INTEGER
            AS semana,
        COALESCE(
            NULLIF(TRIM("Responsable"), ''),
            'Sin responsable'
        ) AS responsable,
        SUM("Total") AS importe_total,
        COUNT(*) AS num_ordenes
    FROM ordenes_punto_venta
    WHERE "Fecha" >= '2026-01-01'
      AND "Fecha" < '2027-01-01'
    GROUP BY mes, semana, responsable
    ORDER BY mes, semana, responsable;
""")

with engine.connect() as connection:
    df = pd.read_sql(query_variable, connection)

if df.empty:
    raise ValueError("No order data was found for 2026.")

df["mes"] = df["mes"].astype(int)
df["semana"] = df["semana"].astype(int)

# --------------------------------------------------
# 2. PREPARE DATA
# --------------------------------------------------

months = {
    1: "Enero", 2: "Febrero", 3: "Marzo",
    4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre",
    10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

available_months = sorted(df["mes"].unique())
responsibles = sorted(df["responsable"].unique())
weeks = [1, 2, 3, 4, 5]

total_amount = df["importe_total"].sum()
total_orders = int(df["num_ordenes"].sum())
total_responsibles = df["responsable"].nunique()

# --------------------------------------------------
# 3. CREATE THE GROUPED BAR CHART
# --------------------------------------------------

fig = go.Figure()

for responsible in responsibles:
    first_month = available_months[0]
    month_df = df[
        (df["mes"] == first_month)
        & (df["responsable"] == responsible)
    ]

    values = [
        month_df.loc[
            month_df["semana"] == week,
            "importe_total"
        ].sum()
        for week in weeks
    ]

    fig.add_trace(go.Bar(
        x=[f"Semana {week}" for week in weeks],
        y=values,
        name=responsible,
        visible=bool(not month_df.empty),
        marker_line_width=0,
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "%{x}<br>"
            "Importe: $%{y:,.2f}"
            "<extra></extra>"
        )
    ))

# Month selector: update the bars without reloading the page
buttons = []

for month in available_months:
    month_df = df[df["mes"] == month]
    y_values = []
    visibility = []

    for responsible in responsibles:
        responsible_df = month_df[
            month_df["responsable"] == responsible
        ]

        y_values.append([
            responsible_df.loc[
                responsible_df["semana"] == week,
                "importe_total"
            ].sum()
            for week in weeks
        ])

        visibility.append(not responsible_df.empty)

    buttons.append({
        "label": months[month],
        "method": "update",
        "args": [
            {
                "y": y_values,
                "visible": visibility
            },
            {
                "title": (
                    f"Importe por semana · {months[month]} 2026"
                )
            }
        ]
    })

fig.update_layout(
    title=f"Importe por semana · {months[available_months[0]]} 2026",
    title_font=dict(size=21, color="#172033"),
    title_x=0.02,
    barmode="group",
    bargap=0.28,
    bargroupgap=0.08,
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(
        family="Arial, sans-serif",
        color="#475569",
        size=12
    ),
    margin=dict(l=35, r=25, t=115, b=45),
    xaxis=dict(
        title=None,
        type="category",
        categoryorder="array",
        categoryarray=[f"Semana {w}" for w in weeks],
        showgrid=False,
        linecolor="#E2E8F0"
    ),
    yaxis=dict(
        title="Importe total",
        tickprefix="$",
        tickformat=",.0f",
        gridcolor="#EDF1F5",
        zeroline=False
    ),
    legend=dict(
        title="Responsable",
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    ),
    updatemenus=[{
        "type": "dropdown",
        "direction": "down",
        "x": 0.02,
        "y": 1.16,
        "xanchor": "left",
        "yanchor": "top",
        "buttons": buttons,
        "showactive": True,
        "bgcolor": "#FFFFFF",
        "bordercolor": "#D9E2EC",
        "font": {"color": "#172033", "size": 12}
    }],
    hoverlabel=dict(
        bgcolor="#172033",
        font_color="#FFFFFF"
    )
)

# --------------------------------------------------
# 4. EXPORT THE DASHBOARD TO HTML
# --------------------------------------------------

graph_html = fig.to_html(
    full_html=False,
    include_plotlyjs=True,
    config={
        "responsive": True,
        "displaylogo": False,
        "modeBarButtonsToRemove": ["lasso2d", "select2d"]
    }
)

html_template = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Órdenes | Viz2026</title>
    <style>
        * { box-sizing: border-box; }

        body {
            margin: 0;
            background: #F4F7FB;
            color: #172033;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI",
                         Arial, sans-serif;
        }

        .page {
            max-width: 1440px;
            margin: auto;
            padding: 38px 30px;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
            flex-wrap: wrap;
            margin-bottom: 28px;
        }

        .eyebrow {
            color: #5265D5;
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 1.6px;
            text-transform: uppercase;
            margin-bottom: 9px;
        }

        h1 {
            margin: 0;
            font-size: clamp(27px, 4vw, 36px);
            letter-spacing: -1px;
        }

        .subtitle {
            color: #64748B;
            margin-top: 10px;
            font-size: 14px;
            line-height: 1.6;
        }

        .status {
            background: #E8F7EF;
            color: #18794E;
            border: 1px solid #C7EBD6;
            border-radius: 20px;
            padding: 9px 13px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }

        .kpis {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 18px;
            margin-bottom: 22px;
        }

        .kpi {
            background: #FFFFFF;
            border: 1px solid #E5EAF1;
            border-radius: 16px;
            padding: 23px;
            box-shadow: 0 3px 12px rgba(30, 45, 75, 0.025);
            min-width: 0;
        }

        .kpi-label {
            color: #64748B;
            font-size: 13px;
            margin-bottom: 14px;
        }

        .kpi-value {
            font-size: clamp(23px, 3vw, 31px);
            font-weight: 700;
            letter-spacing: -0.8px;
            overflow-wrap: anywhere;
        }

        .kpi-note {
            color: #94A3B8;
            font-size: 12px;
            margin-top: 9px;
        }

        .panel {
            background: #FFFFFF;
            border: 1px solid #E5EAF1;
            border-radius: 18px;
            padding: 20px 14px 10px;
            box-shadow: 0 4px 18px rgba(30, 45, 75, 0.035);
        }

        .panel-heading {
            padding: 2px 15px 0;
        }

        .panel-heading h2 {
            margin: 0;
            font-size: 17px;
        }

        .panel-heading p {
            color: #64748B;
            font-size: 13px;
            line-height: 1.6;
            margin: 8px 0 0;
        }

        .footer {
            text-align: center;
            color: #94A3B8;
            font-size: 12px;
            margin-top: 22px;
        }

        @media (max-width: 700px) {
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
                <h1>Resumen de órdenes</h1>
                <div class="subtitle">
                    Análisis de importes semanales por responsable durante 2026.
                </div>
            </div>
            <div class="status">● Datos consultados desde Viz2026</div>
        </header>

        <section class="kpis">
            <article class="kpi">
                <div class="kpi-label">Importe total · 2026</div>
                <div class="kpi-value">__TOTAL_AMOUNT__</div>
                <div class="kpi-note">Suma de los importes registrados</div>
            </article>
            <article class="kpi">
                <div class="kpi-label">Órdenes registradas</div>
                <div class="kpi-value">__TOTAL_ORDERS__</div>
                <div class="kpi-note">Órdenes incluidas en la consulta</div>
            </article>
            <article class="kpi">
                <div class="kpi-label">Responsables</div>
                <div class="kpi-value">__TOTAL_RESPONSIBLES__</div>
                <div class="kpi-note">Con órdenes en el periodo</div>
            </article>
        </section>

        <section class="panel">
            <div class="panel-heading">
                <h2>Desempeño semanal</h2>
                <p>
                    Selecciona un mes en el menú de la gráfica.
                    Haz clic en los responsables de la leyenda para
                    mostrar u ocultar sus barras.
                </p>
            </div>
            __GRAPH_HTML__
        </section>

        <footer class="footer">
            Viz2026 · PostgreSQL + SQLAlchemy + Plotly
        </footer>
    </main>
</body>
</html>
"""

html_output = (
    html_template
    .replace("__GRAPH_HTML__", graph_html)
    .replace("__TOTAL_AMOUNT__", f"${total_amount:,.2f}")
    .replace("__TOTAL_ORDERS__", f"{total_orders:,}")
    .replace("__TOTAL_RESPONSIBLES__", f"{total_responsibles:,}")
)

Path("ordenes.html").write_text(html_output, encoding="utf-8")

print("Dashboard created: ordenes.html")
print(f"Orders analyzed: {total_orders:,}")
print(f"Total amount: ${total_amount:,.2f}")
