import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import plotly.express as px
import os
import glob
from datetime import datetime
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import pdfkit

# ------------------------------------------------------------
# 0. CONFIG
# ------------------------------------------------------------

st.set_page_config(page_title="Verrechenbarkeit Dashboard", layout="wide")

LOGO_PATH = "Logo_PD_Services.png"  # Logo-Datei vom Benutzer
PDFKIT_CONFIG_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"  # Standard-Installationspfad

pdfkit_config = pdfkit.configuration(wkhtmltopdf=PDFKIT_CONFIG_PATH)

# OneDrive Basis-Verzeichnis des Users
onedrive_base = os.path.expanduser(
    r"C:\Users\{}\OneDrive\Documents\Management\PDS\Verrechenbarkeit".format(
        os.getlogin()
    )
)

# ------------------------------------------------------------
# 1. CONSULTING REGIONS
# ------------------------------------------------------------

consulting_ch = [
    "aity AG", "Bank Frick AG", "Basellandschaftliche Kantonalbank (BLKB)",
    "IFM Independent Fund Management AG", "LLB Swiss Investment AG",
    "Luzerner Kantonalbank AG", "LUKB Expert Fondsleitung AG",
    "Schweizerische Mobiliar Versicherungsgesellschaft AG",
    "Pax Asset Management AG", "PMG Investment Solutions AG",
    "Solutions & Funds SA", "UBS Fund Management (Switzerland) AG",
    "UBS Business Solutions AG"
]

consulting_de = [
    "Allianz Invest Kapitalanlagegesellschaft mbH",
    "Bank Gutmann Aktiengesellschaft",
    "BayernInvest Kapitalverwaltungsgesellschaft mbH",
    "Bantleon Invest Kapitalverwaltungsgesellschaft mbH",
    "The Bank of New York SA/NV - Frankfurt Branch",
    "DekaBank Deutsche Girozentrale",
    "DZ Bank AG",
    "Evangelische Bank eG",
    "Hamburger Sparkasse AG",
    "Helaba Invest Kapitalanlagegesellschaft mbH",
    "HanseMerkur Trust AG",
    "Kreissparkasse Köln",
    "Liechtensteinische Landesbank (Österreich) AG",
    "Liechtensteinische Landesbank AG",
    "B. Metzler seel. Sohn & Co. AG",
    "Raiffeisen Bank International AG",
    "Security Kapitalanlage Aktiengesellschaft",
    "Universal-Investment-Gesellschaft mbH"
]

consulting_lux = [
    "DZ PRIVATBANK AG",
    "Hauck Aufhäuser Lampe Privatbank AG",
    "LBBW Asset Management Investmentgesellschaft mbH",
    "navAXX S.A.",
    "Utmost Luxembourg S.A."
]


def assign_region(customer):
    if customer in consulting_ch:
        return "CH"
    elif customer in consulting_de:
        return "DE"
    elif customer in consulting_lux:
        return "LUX"
    else:
        return "Other"


# ------------------------------------------------------------
# 2. LOAD DATA (MULTI-YEAR)
# ------------------------------------------------------------

def load_data():
    years = [d for d in os.listdir(onedrive_base) if d.isdigit()]
    df_list = []

    for y in years:
        folder = os.path.join(onedrive_base, y)
        files = glob.glob(os.path.join(folder, "*.xlsx"))
        for f in files:
            df = pd.read_excel(f)
            df["Year"] = int(y)
            df_list.append(df)

    df = pd.concat(df_list, ignore_index=True)
    return df


df = load_data()

# Basic cleaning
df["Datum"] = pd.to_datetime(df["Datum"], dayfirst=True, errors="coerce")
df["Kunde"] = df["Kunde"].astype(str).str.strip()
df["MA"] = df["MA"].astype(str).str.strip()
df["Betrag"] = pd.to_numeric(df["Betrag"], errors="coerce").fillna(0)
df["Stunden"] = pd.to_numeric(df["Stunden"], errors="coerce").fillna(0)
df["Consulting_Region"] = df["Kunde"].apply(assign_region)
df.dropna(subset=["Datum"], inplace=True)

df["Month"] = df["Datum"].dt.month

# ------------------------------------------------------------
# 3. SIDEBAR FILTER
# ------------------------------------------------------------

st.sidebar.header("Filter")

years_avail = sorted(df["Year"].unique())
year_sel = st.sidebar.multiselect("Jahr", options=years_avail, default=years_avail)

regions = st.sidebar.multiselect(
    "Consulting-Region",
    options=df["Consulting_Region"].unique(),
    default=df["Consulting_Region"].unique()
)

customers = st.sidebar.multiselect(
    "Kunde",
    options=df["Kunde"].unique(),
    default=df["Kunde"].unique()
)

employees = st.sidebar.multiselect(
    "Mitarbeitende",
    options=df["MA"].unique(),
    default=df["MA"].unique()
)

types = st.sidebar.multiselect(
    "Leistungsart",
    options=df["Leistungsart"].unique(),
    default=df["Leistungsart"].unique()
)

date_range = st.sidebar.date_input(
    "Datumsbereich",
    (df["Datum"].min(), df["Datum"].max())
)


# ------------------------------------------------------------
# 4. FILTER APPLY
# ------------------------------------------------------------

mask = (
    df["Year"].isin(year_sel) &
    df["Consulting_Region"].isin(regions) &
    df["Kunde"].isin(customers) &
    df["MA"].isin(employees) &
    df["Leistungsart"].isin(types) &
    (df["Datum"] >= pd.to_datetime(date_range[0])) &
    (df["Datum"] <= pd.to_datetime(date_range[1]))
)

filtered = df.loc[mask]


# ------------------------------------------------------------
# 5. KPIs
# ------------------------------------------------------------

st.title("?? Verrechenbarkeit Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Umsatz (EUR)", f"{filtered['Betrag'].sum():,.2f}")
col2.metric("Stunden", f"{filtered['Stunden'].sum():,.2f}")
col3.metric("Buchungen", f"{len(filtered):,}")


# ------------------------------------------------------------
# 6. CHARTS
# ------------------------------------------------------------

st.subheader("Umsatz nach Region")
region_rev = filtered.groupby("Consulting_Region")["Betrag"].sum().sort_values(ascending=False)
st.bar_chart(region_rev)

st.subheader("Umsatz nach Kunden")
cust_rev = filtered.groupby("Kunde")["Betrag"].sum().sort_values(ascending=False)
st.bar_chart(cust_rev)

st.subheader("Umsatz nach Mitarbeitenden")
emp_rev = filtered.groupby("MA")["Betrag"].sum().sort_values(ascending=False)
st.bar_chart(emp_rev)

st.subheader("Täglicher Umsatzverlauf")
daily_rev = filtered.groupby("Datum")["Betrag"].sum().sort_index()
st.line_chart(daily_rev)


# ------------------------------------------------------------
# 7. HEATMAPS
# ------------------------------------------------------------

st.header("?? Heatmaps")

pivot_ma_region = filtered.pivot_table(
    values="Betrag", index="MA", columns="Consulting_Region", aggfunc="sum", fill_value=0
)

st.subheader("MA × Region")
fig, ax = plt.subplots(figsize=(10, 6))
sns.heatmap(pivot_ma_region, annot=False, cmap="Reds", ax=ax)
st.pyplot(fig)


# ------------------------------------------------------------
# 8. FORECASTING
# ------------------------------------------------------------

st.header("?? Forecast: Umsatz pro Region")

region_to_forecast = st.selectbox("Region auswählen", options=filtered["Consulting_Region"].unique())

reg_df = filtered[filtered["Consulting_Region"] == region_to_forecast]
ts = reg_df.groupby("Datum")["Betrag"].sum().asfreq("D").fillna(0)

model = ExponentialSmoothing(ts, trend="add", seasonal=None)
fit = model.fit()
forecast = fit.forecast(30)

fig2, ax2 = plt.subplots(figsize=(10, 5))
ts.plot(ax=ax2, label="Ist")
forecast.plot(ax=ax2, label="Forecast")
plt.legend()
st.pyplot(fig2)


# ------------------------------------------------------------
# 9. ALERTS (<70% Verrechenbarkeit)
# ------------------------------------------------------------

st.header("? Mitarbeiter Alerts (<70% verrechenbar)")

ma_stats = df.groupby("MA").agg(
    billable=("Betrag", lambda x: (x > 0).sum()),
    total=("Betrag", "count")
)

ma_stats["rate"] = ma_stats["billable"] / ma_stats["total"]

alert_df = ma_stats[ma_stats["rate"] < 0.70]

if len(alert_df) > 0:
    st.error("? Mitarbeitende unter 70% Verrechenbarkeit gefunden")
    st.dataframe(alert_df)
else:
    st.success("? Keine Alerts")


# ------------------------------------------------------------
# 10. EXPORT: EXCEL
# ------------------------------------------------------------

def export_excel(df):
    output = BytesIO()
    df.to_excel(output, index=False)
    return output.getvalue()

st.download_button(
    label="?? Export Excel",
    data=export_excel(filtered),
    file_name="export.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


# ------------------------------------------------------------
# 11. EXPORT: PDF (PDFKIT)
# ------------------------------------------------------------

st.header("?? PDF Export")

def generate_pdf():
    html = f"""
    <html>
    <head>
    <meta name="author" content="Profidata Services AG" />
    <meta name="title" content="Verrechenbarkeitsreport" />
    <style>
        body {{ font-family: Arial; margin: 20px; }}
        h1 {{ color: #B00000; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; }}
    </style>
    </head>
    <body>

    {LOGO_PATH}
    <h1>Verrechenbarkeitsreport</h1>
    <br><br><br>

    <h2>KPI Übersicht</h2>
    <p><b>Umsatz:</b> {filtered['Betrag'].sum():,.2f} EUR</p>
    <p><b>Stunden:</b> {filtered['Stunden'].sum():,.2f}</p>
    <p><b>Buchungen:</b> {len(filtered)}</p>

    <h2>Gefilterte Datensätze</h2>
    {filtered.head(30).to_html(index=False)}

    </body></html>
    """

    pdf = pdfkit.from_string(html, False, configuration=pdfkit_config)
    return pdf


st.download_button(
    label="?? PDF Report herunterladen",
    data=generate_pdf(),
    file_name="report.pdf",
    mime="application/pdf"
)


# ------------------------------------------------------------
# 12. TABLE
# ------------------------------------------------------------

st.header("?? Gefilterte Tabelle")
st.dataframe(filtered)
