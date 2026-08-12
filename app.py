from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

# ----------------------------------------------------
# 1. HARDCODED GOOGLE SHEET CSV LINKS
# ----------------------------------------------------
STOCKS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=0&single=true&output=csv"
BONDS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=784070610&single=true&output=csv"
INCOME_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=877997891&single=true&output=csv"

# Start date for daily line chart timeline
START_HIST_DATE = "2026-08-03"

# ----------------------------------------------------
# 2. STREAMLIT CONFIGURATION
# ----------------------------------------------------
st.set_page_config(
    page_title="Family Wealth Dashboard",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("👨‍👩‍👧‍👦 Family's Overall Wealth & Portfolio Dashboard")

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

# ----------------------------------------------------
# 3. DATA PROCESSING: FDs & BONDS
# ----------------------------------------------------
bonds_df = pd.DataFrame()
if BONDS_CSV:
    try:
        bonds_df = pd.read_csv(BONDS_CSV)
        earned_interest_list = []
        monthly_payout_list = []
        today = datetime.today()

        for _, row in bonds_df.iterrows():
            principal = float(row.get("Invested_Amount", 0))
            rate = float(row.get("Interest_Rate_Pct", 0)) / 100.0

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
# 4. DATA PROCESSING: STOCKS (NSE & BSE SUPPORT)
# ----------------------------------------------------
stocks_df = pd.DataFrame()
closed_df = pd.DataFrame()
daily_closing_wealth_df = pd.DataFrame()
daily_wealth_series = pd.Series(dtype=float)

if STOCKS_CSV:
    try:
        raw_stocks_df = pd.read_csv(STOCKS_CSV)

        # Separate Active and Closed positions
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

            # Live current valuations from Google Sheet
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

            # Fetch historical close prices for NSE and BSE via yfinance
            for _, row in stocks_df.iterrows():
                ticker = str(row["Ticker"]).strip()
                exchange = (
                    str(row.get("Exchange", "NSE")).strip().upper()
                )  # Defaults to NSE

                # Auto-append correct extension for yfinance (.NS or .BO)
                if ticker.endswith(".NS") or ticker.endswith(".BO"):
                    yf_ticker = ticker
                elif exchange in ["BSE", "BO"]:
                    yf_ticker = f"{ticker}.BO"
                else:
                    yf_ticker = f"{ticker}.NS"

                shares = float(row["Shares"])

                try:
                    hist_data = yf.Ticker(yf_ticker).history(
                        start=START_HIST_DATE
                    )
                    if not hist_data.empty:
                        daily_stock_val = hist_data["Close"] * shares
                        daily_stock_val.index = daily_stock_val.index.strftime(
                            "%Y-%m-%d"
                        )
                        daily_closing_wealth_df[ticker] = daily_stock_val
                except Exception as e:
                    st.sidebar.warning(f"Could not load data for {yf_ticker}")

            if not daily_closing_wealth_df.empty:
                daily_wealth_series = (
                    daily_closing_wealth_df.sum(axis=1) + total_bonds_val
                )

        if not closed_df.empty and "Realized_PnL" in closed_df.columns:
            total_realized_pnl = pd.to_numeric(
                closed_df["Realized_PnL"], errors="coerce"
            ).sum()
    except Exception as e:
        st.sidebar.error(f"Error loading Stocks: {e}")

# ----------------------------------------------------
# 5. DATA PROCESSING: INCOME
# ----------------------------------------------------
income_df = pd.DataFrame()
if INCOME_CSV:
    try:
        income_df = pd.read_csv(INCOME_CSV)
        monthly_total = 0.0

        for _, row in income_df.iterrows():
            amt = float(row.get("Amount", 0))
            freq = str(row.get("Frequency", "")).strip().lower()
            if freq == "monthly":
                monthly_total += amt
            elif freq == "yearly":
                monthly_total += amt / 12
            else:
                monthly_total += amt

        total_monthly_income = monthly_total + total_monthly_payout
    except Exception as e:
        st.sidebar.error(f"Error loading Income: {e}")

# Net Worth Calculations
net_worth = total_stock_val + total_bonds_val
stock_gain = total_stock_val - total_stock_invested
aug3_val = (
    daily_wealth_series.iloc[0] if not daily_wealth_series.empty else net_worth
)
wealth_change_since_aug3 = net_worth - aug3_val

# ----------------------------------------------------
# 6. TOP SUMMARY METRIC CARDS
# ----------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric(
    "💰 Total Family Net Worth",
    f"₹{net_worth:,.2f}",
    delta=f"₹{wealth_change_since_aug3:,.2f} since Aug 3",
)
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
    "💵 Total Est. Monthly Income",
    f"₹{total_monthly_income:,.2f}",
    delta=f"₹{total_monthly_payout:,.2f} from FDs",
)

st.markdown("---")

# ----------------------------------------------------
# 7. MAIN DASHBOARD TABS
# ----------------------------------------------------
tab_overview, tab_stocks, tab_bonds, tab_income = st.tabs(
    ["📊 Overall Summary", "📈 Stocks & Trades", "📜 FDs & Bonds", "💵 Income Tracker"]
)

# TAB 1: OVERALL SUMMARY
with tab_overview:
    # 1. Day-by-Day Family Wealth Growth Line Chart
    st.subheader("📈 Day-by-Day Family Wealth Growth (Daily Closing Prices)")

    if not daily_wealth_series.empty:
        daily_wealth_df = daily_wealth_series.reset_index()
        daily_wealth_df.columns = ["Date", "Total Wealth (₹)"]

        fig_wealth = px.line(
            daily_wealth_df,
            x="Date",
            y="Total Wealth (₹)",
            title="Daily Total Family Net Worth Trend",
            markers=True,
        )
        fig_wealth.update_traces(
            line_color="#00D4B1", line_width=3, marker_size=8
        )
        fig_wealth.update_layout(hovermode="x unified")
        st.plotly_chart(fig_wealth, use_container_width=True)

        # Day-by-Day Wealth Numbers Expander
        with st.expander("📄 View Day-by-Day Wealth Breakdown Numbers"):
            detailed_daily_df = daily_closing_wealth_df.copy()
            detailed_daily_df["FDs & Bonds (₹)"] = total_bonds_val
            detailed_daily_df["Total Net Worth (₹)"] = daily_wealth_series

            st.dataframe(
                detailed_daily_df.style.format("₹{:,.2f}"),
                use_container_width=True,
            )
    else:
        st.info("Daily market history timeline is loading or unavailable.")

    st.markdown("---")

    # 2. Asset Allocation Breakdown & Portfolio Table
    st.subheader("Asset Allocation Breakdown")
    if net_worth > 0:
        alloc_data = {
            "Asset Type": ["Stocks & Equities", "FDs & Fixed Income"],
            "Value": [total_stock_val, total_bonds_val],
        }
        fig_donut = px.pie(
            alloc_data,
            values="Value",
            names="Asset Type",
            hole=0.45,
            color_discrete_sequence=["#00D4B1", "#3B82F6"],
            title="Overall Net Worth Distribution",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("### Portfolio Asset Summary")
        summary_df = pd.DataFrame(
            [
                {
                    "Asset Class": "Stocks & Equities",
                    "Invested Amount": f"₹{total_stock_invested:,.2f}",
                    "Current Value": f"₹{total_stock_val:,.2f}",
                    "Total Gains / Interest": f"₹{stock_gain:,.2f}",
                },
                {
                    "Asset Class": "FDs & Bonds",
                    "Invested Amount": f"₹{(total_bonds_val - total_bonds_earned_interest):,.2f}",
                    "Current Value": f"₹{total_bonds_val:,.2f}",
                    "Total Gains / Interest": f"₹{total_bonds_earned_interest:,.2f}",
                },
            ]
        )
        st.dataframe(summary_df, use_container_width=True)

# TAB 2: STOCKS & TRADES
with tab_stocks:
    if not stocks_df.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig_stock_pie = px.pie(
                stocks_df,
                values="Total_Value",
                names="Ticker",
                title="Stock Portfolio Allocation",
                hole=0.35,
            )
            st.plotly_chart(fig_stock_pie, use_container_width=True)
        with col_s2:
            fig_stock_bar = px.bar(
                stocks_df,
                x="Ticker",
                y="Total_Value",
                color="P/L (₹)",
                title="Stock Values & Unrealized Gain/Loss",
                color_continuous_scale="Blugrn",
            )
            st.plotly_chart(fig_stock_bar, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 Active Stock Holdings Table")
        display_cols = [
            "Ticker",
            "Exchange",
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
            ).map(
                lambda v: (
                    "color: #00E676; font-weight: bold;"
                    if v > 0
                    else (
                        "color: #FF5252; font-weight: bold;" if v < 0 else ""
                    )
                ),
                subset=["P/L (₹)", "P/L (%)"],
            ),
            use_container_width=True,
        )

    st.markdown("---")
    st.subheader("🏁 Closed Trades & Realized P&L")
    if not closed_df.empty:
        st.metric("Total Realized Profit / Loss", f"₹{total_realized_pnl:,.2f}")
        st.dataframe(closed_df, use_container_width=True)
    else:
        st.info("No closed trades recorded.")

# TAB 3: FDS & BONDS
with tab_bonds:
    if not bonds_df.empty:
        st.subheader("🏦 Fixed Deposits & Bond Holdings")
        fig_bonds = px.bar(
            bonds_df,
            x="Name",
            y="Current Value (₹)",
            color="Asset_Type",
            title="FD & Bond Current Values",
            barmode="group",
        )
        st.plotly_chart(fig_bonds, use_container_width=True)
        st.dataframe(
            bonds_df.style.format(
                {
                    "Invested_Amount": "₹{:.2f}",
                    "Interest_Rate_Pct": "{:.2f}%",
                    "Est. Monthly Payout (₹)": "₹{:.2f}",
                    "Total Interest Earned (₹)": "₹{:.2f}",
                    "Current Value (₹)": "₹{:.2f}",
                }
            ),
            use_container_width=True,
        )

# TAB 4: INCOME TRACKER
with tab_income:
    if not income_df.empty:
        st.subheader("💵 Monthly Recurring Income Breakdown")
        fig_inc = px.pie(
            income_df,
            values="Amount",
            names="Source",
            title="Income Sources",
        )
        st.plotly_chart(fig_inc, use_container_width=True)
        st.dataframe(income_df, use_container_width=True)
