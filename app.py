import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# ----------------------------------------------------
# 1. HARDCODED GOOGLE SHEET CSV LINKS
# Replace the URLs inside the quotes with your actual published CSV links
# ----------------------------------------------------
STOCKS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=0&single=true&output=csv"
BONDS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=784070610&single=true&output=csv"
INCOME_CSV = "PASTE_YOUR_INCOME_CSV_URL_HERE"

# ----------------------------------------------------
# 2. STREAMLIT PAGE CONFIGURATION
# ----------------------------------------------------
st.set_page_config(
    page_title="Personal Wealth Command Center",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Dashboard Styling
st.markdown("""
    <style>
    .main { padding: 1rem 2rem; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; color: #00D4B1; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px; padding: 10px 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("🛡️ Personal Wealth Command Center")

# Sidebar Configuration Options
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Refresh Data"):
        st.rerun()
    st.caption("Editing your Google Sheet will auto-reflect here on refresh.")

# Global Variables
total_stock_val = 0.0
total_stock_invested = 0.0
total_bonds_val = 0.0
total_monthly_income = 0.0

# ----------------------------------------------------
# 3. DATA PROCESSING: STOCKS
# ----------------------------------------------------
stocks_df = pd.DataFrame()
if STOCKS_CSV and "http" in STOCKS_CSV:
    try:
        stocks_df = pd.read_csv(STOCKS_CSV)
        live_prices = []
        current_vals = []
        
        for _, row in stocks_df.iterrows():
            ticker = row['Ticker']
            shares = float(row['Shares'])
            
            # Fetch live price via Yahoo Finance
            data = yf.Ticker(ticker).history(period="1d")
            price = data['Close'].iloc[-1] if not data.empty else float(row['Buy_Price'])
            
            live_prices.append(price)
            current_vals.append(price * shares)
            
        stocks_df['Current_Price'] = live_prices
        stocks_df['Total_Value'] = current_vals
        stocks_df['P/L'] = stocks_df['Total_Value'] - (stocks_df['Shares'] * stocks_df['Buy_Price'])
        
        total_stock_invested = (stocks_df['Shares'] * stocks_df['Buy_Price']).sum()
        total_stock_val = stocks_df['Total_Value'].sum()
    except Exception as e:
        st.sidebar.error(f"Error loading Stocks tab: {e}")

# ----------------------------------------------------
# 4. DATA PROCESSING: FDs & BONDS
# ----------------------------------------------------
bonds_df = pd.DataFrame()
if BONDS_CSV and "http" in BONDS_CSV:
    try:
        bonds_df = pd.read_csv(BONDS_CSV)
        total_bonds_val = bonds_df['Invested_Amount'].sum()
    except Exception as e:
        st.sidebar.error(f"Error loading FDs & Bonds tab: {e}")

# ----------------------------------------------------
# 5. DATA PROCESSING: INCOME
# ----------------------------------------------------
income_df = pd.DataFrame()
if INCOME_CSV and "http" in INCOME_CSV:
    try:
        income_df = pd.read_csv(INCOME_CSV)
        monthly_total = 0.0
        
        for _, row in income_df.iterrows():
            amt = float(row['Amount'])
            freq = str(row['Frequency']).strip().lower()
            if freq == 'monthly':
                monthly_total += amt
            elif freq == 'yearly':
                monthly_total += (amt / 12)
            else:
                monthly_total += amt
        total_monthly_income = monthly_total
    except Exception as e:
        st.sidebar.error(f"Error loading Income tab: {e}")

# ----------------------------------------------------
# 6. TOP HIGHLIGHT METRICS
# ----------------------------------------------------
net_worth = total_stock_val + total_bonds_val
stock_gain = total_stock_val - total_stock_invested

m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 Total Portfolio Value", f"₹{net_worth:,.2f}")
m2.metric("📈 Stocks Current Value", f"₹{total_stock_val:,.2f}", delta=f"₹{stock_gain:,.2f}")
m3.metric("🏦 FDs & Bonds Value", f"₹{total_bonds_val:,.2f}")
m4.metric("💵 Est. Monthly Income", f"₹{total_monthly_income:,.2f}")

st.markdown("---")

# ----------------------------------------------------
# 7. DASHBOARD TABS
# ----------------------------------------------------
tab_overview, tab_stocks, tab_bonds, tab_income = st.tabs([
    "📊 Overall Summary", "📈 Stocks Portfolio", "📜 FDs & Bonds", "💵 Income Tracker"
])

# TAB 1: OVERALL SUMMARY
with tab_overview:
    st.subheader("Asset Allocation Breakdown")
    if net_worth > 0:
        alloc_data = {
            "Asset Type": ["Stocks", "FDs & Bonds"],
            "Value": [total_stock_val, total_bonds_val]
        }
        fig_donut = px.pie(
            alloc_data, values="Value", names="Asset Type", 
            hole=0.4, color_discrete_sequence=["#00D4B1", "#3B82F6"]
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    else:
        st.info("Please update your CSV URLs in app.py to view your asset allocation charts!")

# TAB 2: STOCKS DETAIL
with tab_stocks:
    if not stocks_df.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig_stock_pie = px.pie(
                stocks_df, values='Total_Value', names='Ticker', 
                title="Stock Allocation", hole=0.3
            )
            st.plotly_chart(fig_stock_pie, use_container_width=True)
        with col_s2:
            fig_stock_bar = px.bar(
                stocks_df, x='Ticker', y='Total_Value', color='P/L', 
                title="Value & Gain/Loss per Stock", color_continuous_scale="Blugrn"
            )
            st.plotly_chart(fig_stock_bar, use_container_width=True)
            
        st.subheader("Detailed Stock Holdings")
        st.dataframe(stocks_df.style.highlight_max(axis=0), use_container_width=True)
    else:
        st.info("No Stocks data loaded.")

# TAB 3: FDS & BONDS
with tab_bonds:
    if not bonds_df.empty:
        st.subheader("Fixed Deposits & Bond Holdings")
        fig_bonds = px.bar(
            bonds_df, x='Name', y='Invested_Amount', color='Asset_Type',
            title="Investments by Asset Type", barmode="group"
        )
        st.plotly_chart(fig_bonds, use_container_width=True)
        st.dataframe(bonds_df, use_container_width=True)
    else:
        st.info("No FDs or Bonds data loaded.")

# TAB 4: INCOME TRACKER
with tab_income:
    if not income_df.empty:
        st.subheader("Income Sources")
        fig_inc = px.pie(income_df, values='Amount', names='Source', title="Income Breakdown")
        st.plotly_chart(fig_inc, use_container_width=True)
        st.dataframe(income_df, use_container_width=True)
    else:
        st.info("No Income data loaded.")
