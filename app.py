
from dash import Dash, html, dcc, Input, Output
from sqlalchemy import create_engine, text
import pandas as pd
import plotly.express as px

# Connect to PostgreSQL
engine = create_engine(
    "postgresql+psycopg2://karen@localhost:5432/Viz2026"
)

# Get data directly from the database
query = text("""
    SELECT
        EXTRACT(MONTH FROM "Fecha") AS mes,
        FLOOR((EXTRACT(DAY FROM "Fecha") - 1) / 7) + 1 AS semana,
        "Responsable",
        SUM("Total") AS importe_total
    FROM ordenes_punto_venta
    WHERE EXTRACT(YEAR FROM "Fecha") = 2026
    GROUP BY mes, semana, "Responsable"
    ORDER BY mes, semana, "Responsable";
""")

with engine.connect() as connection:
    df = pd.read_sql(query, connection)

df["mes"] = df["mes"].astype(int)
df["semana"] = df["semana"].astype(int)

months = {
    1: "January", 2: "February", 3: "March",
    4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September",
    10: "October", 11: "November", 12: "December"
}

app = Dash(__name__)

app.layout = html.Div(
    style={"padding": "25px", "fontFamily": "Arial"},
    children=[
        html.H1(
            "Sales by Month, Week and Responsible Person",
            style={"textAlign": "center"}
        ),

        html.Label("Select month:"),

        dcc.Dropdown(
            id="month-dropdown",
            options=[
                {"label": months[m], "value": m}
                for m in sorted(df["mes"].unique())
            ],
            value=int(df["mes"].min()) if not df.empty else None,
            clearable=True
        ),

        dcc.Graph(id="sales-chart")
    ]
)


@app.callback(
    Output("sales-chart", "figure"),
    Input("month-dropdown", "value")
)
def update_chart(selected_month):
    filtered_df = df.copy()

    if selected_month is not None:
        filtered_df = filtered_df[
            filtered_df["mes"] == selected_month
        ]

    if filtered_df.empty:
        return px.bar(title="No data available for this month")

    fig = px.bar(
        filtered_df,
        x="semana",
        y="importe_total",
        color="Responsable",
        barmode="group",
        title="Total Sales by Week and Responsible Person",
        labels={
            "semana": "Week of the Month",
            "importe_total": "Total Amount",
            "Responsable": "Responsible Person"
        },
        category_orders={
            "semana": [1, 2, 3, 4, 5]
        }
    )

    fig.update_layout(
        template="plotly_white",
        xaxis=dict(type="category"),
        legend_title="Responsible Person"
    )

    return fig


if __name__ == "__main__":
    app.run(debug=True)
