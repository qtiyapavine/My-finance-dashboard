import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# Page Setup
st.set_page_config(page_title="My Wealth Dashboard", layout="wide")
st.title("📊 Personal Investment & Income Dashboard")

# Streamlit Sidebar for Data Link
st.sidebar.header("Configuration")
sheet_url = st.sidebar.text_input(
    "Enter your Google Sheet CSV Link:", 
    help="We will paste your published Google Sheet link here"
)

st.info("👈 Enter your Google Sheet link in the sidebar to load your data!")

# Placeholder for main content
st.header("Asset Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Income", "₹0.00")
col2.metric("Total Investments", "₹0.00")
col3.metric("Net Worth", "₹0.00")

st.markdown("---")
st.subheader("📈 Live Stock Performance")
st.caption("Once connected, your live stock graphs will display here automatically.")
