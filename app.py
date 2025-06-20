import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from fpdf import FPDF
import gdown
import os

# === Streamlit Config ===
st.set_page_config(page_title="Invoice Analytics Dashboard", layout="wide")
st.title("📊 Invoice Analytics Dashboard")

# === Load Data ===
@st.cache_data
def load_data():
    url = "https://drive.google.com/uc?export=download&id=100r8Nxz7v-Yctdk2m4UfPdir0GgUgcWA"
    parquet_file = "invoices.parquet"
    if not os.path.exists(parquet_file):
        gdown.download(url, parquet_file, quiet=False)
    df = pd.read_parquet(parquet_file)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    return df

df_full = load_data()
df = df_full.copy()

# === Sidebar ===
st.sidebar.image("https://i.imgur.com/ybXsZKD.png", width=120)
st.sidebar.markdown("### Filters")

countries = sorted(df["Country"].unique())
selected_country = st.sidebar.selectbox("🌍 Country", ["All"] + countries)
if selected_country != "All":
    df = df[df["Country"] == selected_country]

min_date, max_date = df["InvoiceDate"].min(), df["InvoiceDate"].max()
date_range = st.sidebar.date_input("🗕️ Date Range", [min_date, max_date])
if len(date_range) == 2:
    df = df[(df["InvoiceDate"] >= pd.to_datetime(date_range[0])) &
            (df["InvoiceDate"] <= pd.to_datetime(date_range[1]))]

# === Tabs Layout ===
tab1, tab2, tab3, tab4 = st.tabs(["📈 Trends", "👤 Customers", "🗕️ Weekday", "🔁 Retention"])

# === Tab 1: Country Trends ===
with tab1:
    st.subheader("🌍 Monthly Invoice Trends by Country")
    df_country = df.copy()
    df_country["Month"] = df_country["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    country_monthly = df_country.groupby(["Country", "Month"]).agg({"InvoiceNo": "nunique"}).reset_index()

    if selected_country != "All":
        data = country_monthly[country_monthly["Country"] == selected_country]
    else:
        data = country_monthly

    fig_trend = px.line(data, x="Month", y="InvoiceNo", color="Country",
                        title="Monthly Invoice Volume by Country")
    st.plotly_chart(fig_trend, use_container_width=True)

# === Tab 2: Customer Drilldown ===
with tab2:
    st.subheader("💎 Top Customers")
    top_customers = df.groupby("CustomerID")["InvoiceTotal"].sum().reset_index()
    top_customers = top_customers.sort_values("InvoiceTotal", ascending=False).head(10)
    customer_ids = df["CustomerID"].dropna().unique()
    customer_ids = sorted([str(int(cid)) for cid in customer_ids])
    selected_customer = st.selectbox("Select a Customer to View Trend", customer_ids)

    customer_df = df[df["CustomerID"] == float(selected_customer)].copy()
    customer_df["Month"] = customer_df["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    customer_trend = customer_df.groupby("Month")["InvoiceTotal"].sum().reset_index()

    fig_customer = px.line(customer_trend, x="Month", y="InvoiceTotal",
                           title=f"Monthly Spend Trend for Customer {selected_customer}")
    st.plotly_chart(fig_customer, use_container_width=True)

# === Tab 3: Weekday Patterns ===
with tab3:
    st.subheader("🗕️ Weekday Invoice Patterns")
    df["Weekday"] = df["InvoiceDate"].dt.day_name()
    weekday_stats = df.groupby("Weekday").agg({"InvoiceTotal": "sum", "InvoiceNo": "nunique"}).reset_index()
    weekday_stats = weekday_stats.sort_values("InvoiceTotal", ascending=False)

    fig_weekday = px.bar(weekday_stats, x="Weekday", y="InvoiceTotal", title="Revenue by Weekday")
    st.plotly_chart(fig_weekday, use_container_width=True)

# === Tab 4: Retention ===
with tab4:
    st.subheader("📘 Customer Retention Heatmap")
    df_ret = df.copy()
    df_ret["Month"] = df_ret["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    retention = pd.crosstab(df_ret["CustomerID"], df_ret["Month"])
    fig_heatmap = px.imshow(np.log1p(retention), aspect="auto",
                            labels=dict(x="Month", y="CustomerID", color="Log(Repeat Invoices)"),
                            title="Repeat Invoices per Customer Over Time")
    st.plotly_chart(fig_heatmap, use_container_width=True)

# === KPI Metrics ===
st.markdown("---")
col1, col2, col3 = st.columns(3)
col1.metric("💰 Total Revenue", f"\u00a3{df['InvoiceTotal'].sum():,.2f}")
col2.metric("🧾 Total Invoices", f"{len(df):,}")
col3.metric("👥 Unique Customers", df["CustomerID"].nunique())

# === Top 10 Products ===
st.subheader("🔥 Top 10 Products")
@st.cache_data
def load_raw():
    url = "https://drive.google.com/uc?export=download&id=1RYVisaxLMPOBM5VPQnDXHDLm355_vwsc"
    df_raw = pd.read_csv(url, encoding='ISO-8859-1')
    df_raw["LineTotal"] = df_raw["Quantity"] * df_raw["UnitPrice"]
    return df_raw

raw_df = load_raw()
if selected_country != "All":
    raw_df = raw_df[raw_df["Country"] == selected_country]

top_products = raw_df.groupby("Description")["LineTotal"].sum().reset_index()
top_products = top_products.sort_values("LineTotal", ascending=False).head(10)

fig_products = px.bar(top_products, x="LineTotal", y="Description", orientation="h",
                      title="Top 10 Products by Revenue")
st.plotly_chart(fig_products, use_container_width=True)

# === Anomaly Detection ===
st.subheader("⚠️ High-Value Invoice Alerts")
thresh = df["InvoiceTotal"].quantile(0.99)
anomalies = df[df["InvoiceTotal"] > thresh]
st.warning(f"{len(anomalies)} high-value invoices detected above 99th percentile")
st.dataframe(anomalies[["InvoiceNo", "InvoiceDate", "InvoiceTotal", "CustomerID", "Country"]])

# === PDF Export ===
def generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Invoice Summary Report", ln=True, align="C")
    pdf.ln(10)
    pdf.cell(200, 10, txt=f"Total Revenue: \u00a3{df['InvoiceTotal'].sum():,.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Total Invoices: {len(df):,}", ln=True)
    pdf.cell(200, 10, txt=f"Unique Customers: {df['CustomerID'].nunique()}", ln=True)
    pdf.output("invoice_summary.pdf")
    return "invoice_summary.pdf"

if st.button("📄 Download KPI Report as PDF"):
    pdf_file = generate_pdf()
    with open(pdf_file, "rb") as f:
        st.download_button("⬇️ Download PDF", f, file_name=pdf_file)

# === CSV Export ===
st.download_button("📥 Download Filtered Invoices (CSV)",
                   data=df.to_csv(index=False),
                   file_name="filtered_invoices.csv",
                   mime="text/csv")
