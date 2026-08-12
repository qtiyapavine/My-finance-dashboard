from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

# ----------------------------------------------------
# 1. HARDCODED GOOGLE SHEET CSV LINKS
# ----------------------------------------------------
STOCKS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=0&single=true&output=csv"
BONDS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=784070610&single=true&output=csv"
INCOME_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=877997891&single=true&output=csv"

# Optional: Add your published Income_Log tab CSV URL here
LOGGED_INCOME_CSV = ""  # Replace with published URL for historical income logs

# ----------------------------------------------------
# 2. STREAMLIT CONFIGURATION
# ----------------------------------------------------
st.set_page_config(
    page_title="Family Wealth & Total Income Tracker",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("👨‍👩‍👧‍👦 Family Wealth & Income Tracker")

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    st.caption("Data syncs automatically with Google Sheets.")

# Global Variables
total_stock_val = 0.0
total_stock_invested = 0.0
total_bonds_val = 0.0
total_bonds_earned_interest = 0.0
total_monthly_payout = 0.0
total_monthly_income = 0.0
total_realized_pnl = 0.0
total_historical_income = 0.0

# ----------------------------------------------------
# 3. BONDS & FDS PROCESSING
# ----------------------------------------------------
bonds_df = pd.DataFrame()
if BONDS_CSV:
    try:
        bonds_df = pd.read_csv(BONDS_CSV)
        earned_interest_list = []
        monthly_payout_list = []
        today = datetime.today()

        for _, row in bonds_df.iterrows():
            principal = float(row["Invested_Amount"])
            rate = float(row["Interest_Rate_Pct"]) / 100.0

            monthly_income = (principal * rate) / 12.0
            monthly_payout_list.append(monthly_income)

            if "Purchase_Date" in row and pd.notnull(row["Purchase_Date"]):
                p_date = pd.to_datetime(row["Purchase_Date"])
                months_active = (today.year - p_date.year) * 12 + (
                    today.month - p_date.month
                )
                months_active = max(0, months_active)
            else:
                months_active = 0

            earned_interest_list.append(monthly_income * months_active)

        bonds_df["Est. Monthly Payout (₹)"] = monthly_payout_list
        bonds_df["Total Interest Earned (₹)"] = earned_interest_list
        bonds_df["Current Value (₹)"] = (
            bonds_df["Invested_Amount"] + bonds_df["Total Interest Earned (₹)"]
        )

        total_bonds_val = bonds_df["Current Value (₹)"].sum()
        total_bonds_earned_interest = bonds_df[
            "Total Interest Earned (₹)"
        ].sum()
        total_monthly_payout = bonds_df["Est. Monthly Payout (₹)"].sum()
    except Exception as e:
        st.sidebar.error(f"Error loading FDs & Bonds: {e}")

# ----------------------------------------------------
# 4. STOCKS PROCESSING
# ----------------------------------------------------
stocks_df = pd.DataFrame()
closed_df = pd.DataFrame()

if STOCKS_CSV:
    try:
        raw_stocks_df = pd.read_csv(STOCKS_CSV)

        if "Status" in raw_stocks_df.columns:
            stocks_df = raw_stocks_df[
                raw_stocks_df["Status"].astype(str).str.lower() != "sold"
            ].copy()
            closed_df = raw_stocks_df[
                raw_stocks_df["Status"].astype(str).str.lower() == "sold"
            ].copy()
        elif "Shares" in raw_stocks_df.columns:
            stocks_df = raw_stocks_df[raw_stocks_df["Shares"] > 0].copy()
            closed_df = raw_stocks_df[raw_stocks_df["Shares"] == 0].copy()
        else:
            stocks_df = raw_stocks_df.copy()

        if not stocks_df.empty:
            for col in ["Shares", "Buy_Price", "Current_Price"]:
                if col in stocks_df.columns:
                    stocks_df[col] = pd.to_numeric(
                        stocks_df[col], errors="coerce"
                    ).fillna(0)

            stocks_df["Total_Value"] = (
                stocks_df["Shares"] * stocks_df["Current_Price"]
            )
            stocks_df["Invested_Val"] = (
                stocks_df["Shares"] * stocks_df["Buy_Price"]
            )
            stocks_df["P/L (₹)"] = (
                stocks_df["Total_Value"] - stocks_df["Invested_Val"]
            )
            stocks_df["P/L (%)"] = (
                stocks_df["P/L (₹)"] / stocks_df["Invested_Val"].replace(0, 1)
            ) * 100

            if "Remarks" not in stocks_df.columns:
                stocks_df["Remarks"] = "-"

            total_stock_invested = stocks_df["Invested_Val"].sum()
            total_stock_val = stocks_df["Total_Value"].sum()

        if not closed_df.empty and "Realized_PnL" in closed_df.columns:
            total_realized_pnl = pd.to_numeric(
                closed_df["Realized_PnL"], errors="coerce"
            ).sum()
    except Exception as e:
        st.sidebar.error(f"Error loading Stocks: {e}")

# ----------------------------------------------------
# 5. INCOME & LOGGED INCOME PROCESSING
# ----------------------------------------------------
income_df = pd.DataFrame()
income_log_df = pd.DataFrame()

if INCOME_CSV:
    try:
        income_df = pd.read_csv(INCOME_CSV)
        monthly_total = 0.0

        for _, row in income_df.iterrows():
            amt = float(row["Amount"])
            freq = str(row["Frequency"]).strip().lower()
            if freq == "monthly":
                monthly_total += amt
            elif freq == "yearly":
                monthly_total += amt / 12
            else:
                monthly_total += amt
        total_monthly_income = monthly_total + total_monthly_payout
    except Exception as e:
        st.sidebar.error(f"Error loading Income sources: {e}")

if LOGGED_INCOME_CSV:
    try:
        income_log_df = pd.read_csv(LOGGED_INCOME_CSV)
        income_log_df["Amount"] = pd.to_numeric(
            income_log_df["Amount"], errors="coerce"
        ).fillna(0)
        income_log_df["Date"] = pd.to_datetime(income_log_df["Date"])
        income_log_df["Year-Month"] = income_log_df["Date"].dt.strftime("%Y-%m")
        total_historical_income = income_log_df["Amount"].sum()
    except Exception as e:
        st.sidebar.error(f"Error loading Income Log: {e}")

net_worth = total_stock_val + total_bonds_val
stock_gain = total_stock_val - total_stock_invested

# ----------------------------------------------------
# 6. TOP METRICS
# ----------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 Total Family Net Worth", f"₹{net_worth:,.2f}")
m2.metric(
    "📈 Active Stocks Value",
    f"₹{total_stock_val:,.2f}",
    delta=f"₹{stock_gain:,.2f} Unrealized",
)
m3.metric(
    "🏦 FDs & Bonds Value",
    f"₹{total_bonds_val:,.2f}",
    delta=f"₹{total_bonds_earned_interest:,.2f} Interest",
)
m4.metric(
    "💵 Total Cumulative Income Logged",
    f"₹{total_historical_income if total_historical_income > 0 else (total_monthly_income * 12):,.2f}",
    delta=f"₹{total_monthly_income:,.2f} Est. Monthly",
)

st.markdown("---")

# ----------------------------------------------------
# 7. DASHBOARD TABS
# ----------------------------------------------------
tab_overview, tab_stocks, tab_bonds, tab_income = st.tabs(
    [
        "📊 Asset Summary",
        "📈 Stocks & Trades",
        "📜 FDs & Bonds",
        "💵 Total Income Tracker",
    ]
)

# TAB 1: ASSET OVERVIEW
with tab_overview:
    st.subheader("Asset Allocation Breakdown")
    if net_worth > 0:
        alloc_data = {
            "Asset Type": ["Stocks", "FDs & Bonds"],
            "Value": [total_stock_val, total_bonds_val],
        }
        fig_donut = px.pie(
            alloc_data,
            values="Value",
            names="Asset Type",
            hole=0.4,
            color_discrete_sequence=["#00D4B1", "#3B82F6"],
        )
        st.plotly_chart(fig_donut, use_container_width=True)

# TAB 2: STOCKS
with tab_stocks:
    if not stocks_df.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig_stock_pie = px.pie(
                stocks_df,
                values="Total_Value",
                names="Ticker",
                title="Active Stock Portfolio Allocation",
                hole=0.3,
            )
            st.plotly_chart(fig_stock_pie, use_container_width=True)
        with col_s2:
            fig_stock_bar = px.bar(
                stocks_df,
                x="Ticker",
                y="Total_Value",
                color="P/L (₹)",
                title="Value & Gain/Loss per Stock",
                color_continuous_scale="Blugrn",
            )
            st.plotly_chart(fig_stock_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Active Stock Holdings Table")
        display_cols = [
            "Ticker",
            "Shares",
            "Buy_Price",
            "Current_Price",
            "Total_Value",
            "P/L (₹)",
            "P/L (%)",
            "Remarks",
        ]
        display_cols = [c for c in display_cols if c in stocks_df.columns]

        st.dataframe(
            stocks_df[display_cols].style.format(
                {
                    "Buy_Price": "₹{:.2f}",
                    "Current_Price": "₹{:.2f}",
                    "Total_Value": "₹{:.2f}",
                    "P/L (₹)": "₹{:+.2f}",
                    "P/L (%)": "{:+.2f}%",
                }
            ),
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("🏁 Closed Trades & Realized P&L Tracker")
    if not closed_df.empty:
        st.metric("Lifetime Realized P&L", f"₹{total_realized_pnl:,.2f}")
        st.dataframe(closed_df, use_container_width=True)
    else:
        st.info("No exited trades logged yet.")

# TAB 3: BONDS
with tab_bonds:
    if not bonds_df.empty:
        st.subheader("🏦 Fixed Deposits & Bond Holdings")
        fig_bonds = px.bar(
            bonds_df,
            x="Name",
            y="Current Value (₹)",
            color="Asset_Type",
            title="Invested vs Earned Value per Asset",
            barmode="group",
        )
        st.plotly_chart(fig_bonds, use_container_width=True)
        st.dataframe(bonds_df, use_container_width=True)

# TAB 4: TOTAL CUMULATIVE INCOME TRACKER
with tab_income:
    st.subheader("💵 Total Overall Income Tracker")

    col_i1, col_i2, col_i3 = st.columns(3)
    col_i1.metric(
        "Est. Total Monthly Cash Flow", f"₹{total_monthly_income:,.2f}/mo"
    )
    col_i2.metric(
        "FD Passive Monthly Income", f"₹{total_monthly_payout:,.2f}/mo"
    )
    col_i3.metric(
        "Total Lifetime FD Interest", f"₹{total_bonds_earned_interest:,.2f}"
    )

    st.markdown("---")

    # Historical Income Chart & Log Table (if Income_Log CSV provided)
    if not income_log_df.empty:
        st.markdown("### 📈 Cumulative Income Over Time (Monthly Received)")
        monthly_income_summary = (
            income_log_df.groupby("Year-Month")["Amount"].sum().reset_index()
        )

        fig_inc_line = px.bar(
            monthly_income_summary,
            x="Year-Month",
            y="Amount",
            title="Monthly Total Income Received (₹)",
            text_auto=".2s",
            color_discrete_sequence=["#00D4B1"],
        )
        st.plotly_chart(fig_inc_line, use_container_width=True)

        st.markdown("### 📋 Complete Income Log History")
        st.dataframe(
            income_log_df.sort_values(by="Date", ascending=False).style.format(
                {"Amount": "₹{:,.2f}"}
            ),
            use_container_width=True,
        )
    else:
        st.info(
            "💡 **Tip to track total income over time:** Create a new tab named `Income_Log` in your Google Sheet with columns (`Date`, `Source`, `Amount`, `Category`, `Remarks`), publish it to CSV, and paste its URL into `LOGGED_INCOME_CSV`."
        )

    st.markdown("---")
    st.markdown("### ⚙️ Recurring Income Sources Breakdown")
    if not income_df.empty:
        fig_inc = px.pie(
            income_df,
            values="Amount",
            names="Source",
            title="Recurring Monthly Income Breakdown",
        )
        st.plotly_chart(fig_inc, use_container_width=True)
        st.dataframe(income_df, use_container_width=True)
