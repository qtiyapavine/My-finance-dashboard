import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta

# ----------------------------------------------------
# 1. HARDCODED GOOGLE SHEET CSV LINKS
# ----------------------------------------------------
STOCKS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=0&single=true&output=csv"
BONDS_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=784070610&single=true&output=csv"
INCOME_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQwaB9_f1LbFawAhNur6KYfGHmXeMK8Oa2b2uu7JTl-BupeHSSJO9wtaHePWYXxQVqFzex9qKDD51FP/pub?gid=877997891&single=true&output=csv"

# Start date for daily line chart
START_HIST_DATE = "2026-08-03"

# ----------------------------------------------------
# 2. STREAMLIT PAGE CONFIGURATION
# ----------------------------------------------------
st.set_page_config(
    page_title="Family's Overall Wealth",
    page_icon="👨‍👩‍👧‍👦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main { padding: 1rem 2rem; }
    div[data-testid="stMetricValue"] { font-size: 28px; font-weight: bold; color: #00D4B1; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px; padding: 10px 20px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

st.title("👨‍👩‍👧‍👦 Family's Overall Wealth")

# Sidebar Controls
with st.sidebar:
    st.header("⚙️ Controls")
    if st.button("🔄 Refresh Data"):
        st.rerun()
    st.caption("Data syncs automatically with your Google Sheet.")

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
            principal = float(row['Invested_Amount'])
            rate = float(row['Interest_Rate_Pct']) / 100.0
            
            # Monthly Payout
            monthly_income = (principal * rate) / 12.0
            monthly_payout_list.append(monthly_income)
            
            # Calculate months active
            if 'Purchase_Date' in row and pd.notnull(row['Purchase_Date']):
                p_date = pd.to_datetime(row['Purchase_Date'])
                months_active = (today.year - p_date.year) * 12 + (today.month - p_date.month)
                months_active = max(0, months_active)
            else:
                months_active = 0
                
            total_earned = monthly_income * months_active
            earned_interest_list.append(total_earned)
            
        bonds_df['Est. Monthly Payout (₹)'] = monthly_payout_list
        bonds_df['Total Interest Earned (₹)'] = earned_interest_list
        bonds_df['Current Value (₹)'] = bonds_df['Invested_Amount'] + bonds_df['Total Interest Earned (₹)']
        
        total_bonds_val = bonds_df['Current Value (₹)'].sum()
        total_bonds_earned_interest = bonds_df['Total Interest Earned (₹)'].sum()
        total_monthly_payout = bonds_df['Est. Monthly Payout (₹)'].sum()
        
    except Exception as e:
        st.sidebar.error(f"Error loading FDs & Bonds: {e}")

# ----------------------------------------------------
# 4. DATA PROCESSING: STOCKS (Active + Closed Trades)
# ----------------------------------------------------
stocks_df = pd.DataFrame()
closed_df = pd.DataFrame()
daily_wealth_series = pd.Series(dtype=float)

if STOCKS_CSV:
    try:
        raw_stocks_df = pd.read_csv(STOCKS_CSV)
        
        # Separate Active and Sold/Closed positions if 'Status' or 'Shares' == 0 exists
        if 'Status' in raw_stocks_df.columns:
            stocks_df = raw_stocks_df[raw_stocks_df['Status'].astype(str).str.lower() != 'sold'].copy()
            closed_df = raw_stocks_df[raw_stocks_df['Status'].astype(str).str.lower() == 'sold'].copy()
        elif 'Shares' in raw_stocks_df.columns:
            stocks_df = raw_stocks_df[raw_stocks_df['Shares'] > 0].copy()
            closed_df = raw_stocks_df[raw_stocks_df['Shares'] == 0].copy()
        else:
            stocks_df = raw_stocks_df.copy()

        # Process Active Stocks
        if not stocks_df.empty:
            live_prices = []
            current_vals = []
            daily_closing_wealth_df = pd.DataFrame()
            
            for _, row in stocks_df.iterrows():
                ticker = str(row['Ticker']).strip()
                shares = float(row['Shares'])
                stock_obj = yf.Ticker(ticker)
                
                # Fetch Live Price
                live_data = stock_obj.history(period="1d")
                price_live = live_data['Close'].iloc[-1] if not live_data.empty else float(row['Buy_Price'])
                live_prices.append(price_live)
                current_vals.append(price_live * shares)
                
                # Fetch daily historical prices from Aug 3, 2026
                hist_data = stock_obj.history(start=START_HIST_DATE)
                if not hist_data.empty:
                    daily_stock_val = hist_data['Close'] * shares
                    daily_stock_val.index = daily_stock_val.index.strftime('%Y-%m-%d')
                    daily_closing_wealth_df[ticker] = daily_stock_val
                    
            stocks_df['Current_Price'] = live_prices
            stocks_df['Total_Value'] = current_vals
            stocks_df['Invested_Val'] = stocks_df['Shares'] * stocks_df['Buy_Price']
            stocks_df['P/L (₹)'] = stocks_df['Total_Value'] - stocks_df['Invested_Val']
            stocks_df['P/L (%)'] = (stocks_df['P/L (₹)'] / stocks_df['Invested_Val']) * 100
            
            if 'Remarks' not in stocks_df.columns:
                stocks_df['Remarks'] = "-"
                
            total_stock_invested = stocks_df['Invested_Val'].sum()
            total_stock_val = stocks_df['Total_Value'].sum()
            
            if not daily_closing_wealth_df.empty:
                daily_wealth_series = daily_closing_wealth_df.sum(axis=1) + total_bonds_val

        # Process Closed / Realized Trades
        if not closed_df.empty:
            if 'Realized_PnL' in closed_df.columns:
                total_realized_pnl = pd.to_numeric(closed_df['Realized_PnL'], errors='coerce').sum()
            elif 'Sell_Price' in closed_df.columns and 'Buy_Price' in closed_df.columns:
                closed_df['Realized_PnL'] = (closed_df['Sell_Price'] - closed_df['Buy_Price']) * closed_df.get('Shares_Sold', closed_df.get('Shares', 1))
                total_realized_pnl = closed_df['Realized_PnL'].sum()

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
            amt = float(row['Amount'])
            freq = str(row['Frequency']).strip().lower()
            if freq == 'monthly':
                monthly_total += amt
            elif freq == 'yearly':
                monthly_total += (amt / 12)
            else:
                monthly_total += amt
        total_monthly_income = monthly_total + total_monthly_payout
        
        if 'Notes' not in income_df.columns and 'Remarks' not in income_df.columns:
            income_df['Notes'] = "-"
            
    except Exception as e:
        st.sidebar.error(f"Error loading Income: {e}")

# Net Worth Calculations
net_worth = total_stock_val + total_bonds_val
stock_gain = total_stock_val - total_stock_invested
aug3_val = daily_wealth_series.iloc[0] if not daily_wealth_series.empty else net_worth
wealth_change_since_aug3 = net_worth - aug3_val

# ----------------------------------------------------
# 6. TOP METRICS
# ----------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("💰 Total Family Net Worth", f"₹{net_worth:,.2f}", delta=f"₹{wealth_change_since_aug3:,.2f} since Aug 3")
m2.metric("📈 Active Stocks Value", f"₹{total_stock_val:,.2f}", delta=f"₹{stock_gain:,.2f} Unrealized")
m3.metric("🏦 FDs & Bonds Value", f"₹{total_bonds_val:,.2f}", delta=f"₹{total_bonds_earned_interest:,.2f} Interest")
m4.metric("💵 Total Monthly Income", f"₹{total_monthly_income:,.2f}", delta=f"₹{total_monthly_payout:,.2f} from FDs")

st.markdown("---")

# ----------------------------------------------------
# 7. DASHBOARD TABS
# ----------------------------------------------------
tab_overview, tab_stocks, tab_bonds, tab_income = st.tabs([
    "📊 Overall Summary", "📈 Stocks & Trades", "📜 FDs & Bonds", "💵 Income Tracker"
])

# TAB 1: OVERALL SUMMARY
with tab_overview:
    st.subheader("📈 Day-by-Day Family Wealth Growth (Daily Closing Prices)")
    
    if not daily_wealth_series.empty:
        daily_wealth_df = daily_wealth_series.reset_index()
        daily_wealth_df.columns = ['Date', 'Total Wealth (₹)']
        
        fig_wealth = px.line(
            daily_wealth_df, x='Date', y='Total Wealth (₹)', 
            title="Daily Total Wealth Progression",
            markers=True
        )
        fig_wealth.update_traces(line_color='#00D4B1', line_width=3, marker_size=8)
        fig_wealth.update_layout(hovermode="x unified")
        st.plotly_chart(fig_wealth, use_container_width=True)
        
        with st.expander("📄 View Day-by-Day Wealth Numbers"):
            st.dataframe(
                daily_wealth_df.style.format({'Total Wealth (₹)': '₹{:,.2f}'}),
                use_container_width=True
            )
    else:
        st.info("Daily market history is loading or unavailable.")
    
    st.markdown("---")
    
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

# TAB 2: STOCKS & TRADES
with tab_stocks:
    if not stocks_df.empty:
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            fig_stock_pie = px.pie(
                stocks_df, values='Total_Value', names='Ticker', 
                title="Active Stock Portfolio Allocation", hole=0.3
            )
            st.plotly_chart(fig_stock_pie, use_container_width=True)
        with col_s2:
            fig_stock_bar = px.bar(
                stocks_df, x='Ticker', y='Total_Value', color='P/L (₹)', 
                title="Value & Gain/Loss per Stock", color_continuous_scale="Blugrn"
            )
            st.plotly_chart(fig_stock_bar, use_container_width=True)
            
        st.markdown("---")
        
        # TABLE HEADER WITH TIMEFRAME SELECTOR
        col_tbl_title, col_tbl_select = st.columns([2, 1])
        with col_tbl_title:
            st.subheader("📋 Active Stock Holdings Table")
        with col_tbl_select:
            selected_tf = st.selectbox(
                "Change Column Timeframe:",
                ["1 Day", "1 Week", "1 Month", "1 Year", "5 Years"],
                index=0
            )
        
        period_map = {"1 Day": "2d", "1 Week": "5d", "1 Month": "1mo", "1 Year": "1y", "5 Years": "5y"}
        
        change_values = []
        for _, row in stocks_df.iterrows():
            ticker = str(row['Ticker']).strip()
            stock_obj = yf.Ticker(ticker)
            hist = stock_obj.history(period=period_map[selected_tf])
            
            if len(hist) >= 2:
                pct_change = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
            else:
                pct_change = 0.0
            change_values.append(pct_change)
            
        display_stocks_df = stocks_df.copy()
        col_label = f"Change ({selected_tf})"
        display_stocks_df[col_label] = change_values
        
        display_cols = ['Ticker', 'Shares', 'Buy_Price', 'Current_Price', col_label, 'Total_Value', 'P/L (₹)', 'P/L (%)', 'Remarks']
        display_cols = [c for c in display_cols if c in display_stocks_df.columns]
        display_stocks_df = display_stocks_df[display_cols]
        
        st.dataframe(
            display_stocks_df.style.format({
                'Buy_Price': '₹{:.2f}',
                'Current_Price': '₹{:.2f}',
                col_label: '{:+.2f}%',
                'Total_Value': '₹{:.2f}',
                'P/L (₹)': '₹{:+.2f}',
                'P/L (%)': '{:+.2f}%'
            }).map(
                lambda v: 'color: #00E676; font-weight: bold;' if v > 0 else ('color: #FF5252; font-weight: bold;' if v < 0 else ''),
                subset=[col_label, 'P/L (₹)', 'P/L (%)']
            ),
            use_container_width=True
        )

    # FEATURE B: CLOSED POSITIONS & REALIZED PNL SECTION
    st.markdown("---")
    st.subheader("🏁 Closed Trades & Realized P&L Tracker")
    if not closed_df.empty:
        col_c1, col_c2 = st.columns([1, 2])
        col_c1.metric("Lifetime Realized P&L", f"₹{total_realized_pnl:,.2f}")
        
        with col_c2:
            st.caption("Logs of stocks you exited and locked-in profits/losses for.")
            
        st.dataframe(closed_df, use_container_width=True)
    else:
        st.info("No exited trades logged yet. To log sold stocks, set their Status to 'Sold' or Shares to 0 in Google Sheets.")

    st.markdown("---")

    # SINGLE STOCK DEEP DIVE CHART
    st.subheader("🔍 Single Stock Chart Deep-Dive")
    if not stocks_df.empty:
        selected_stock = st.selectbox("Select a stock to view its price chart:", stocks_df['Ticker'].tolist())
        
        if selected_stock:
            stock_obj = yf.Ticker(selected_stock)
            time_frame = st.radio("Select Chart Period:", ["1mo", "3mo", "6mo", "1y", "5y"], index=0, horizontal=True)
            stock_data = stock_obj.history(period=time_frame)
            if not stock_data.empty:
                fig_stock_line = px.line(stock_data, y='Close', title=f"Price Chart for {selected_stock}")
                fig_stock_line.update_traces(line_color='#3B82F6', line_width=2)
                st.plotly_chart(fig_stock_line, use_container_width=True)

    st.markdown("---")

    # NEWS & CORPORATE ACTIONS BELOW CHART
    st.subheader("📰 Whole Portfolio News & Corporate Actions (±1 Month)")
    today_dt = datetime.today()
    one_month_ago = today_dt - timedelta(days=30)
    one_month_ahead = today_dt + timedelta(days=30)
    
    col_all_actions, col_all_news = st.columns([1, 1])
    all_actions, all_news = [], []
    
    if not stocks_df.empty:
        for t in stocks_df['Ticker'].unique():
            stk = yf.Ticker(t)
            # Dividends
            try:
                divs = stk.dividends
                if not divs.empty:
                    for date_idx, val in divs.items():
                        event_dt = pd.to_datetime(date_idx).tz_localize(None) if pd.to_datetime(date_idx).tzinfo else pd.to_datetime(date_idx)
                        if one_month_ago <= event_dt <= one_month_ahead:
                            all_actions.append({'Ticker': t, 'Type': 'Dividend', 'Detail': f"₹{val:.2f}", 'Date': event_dt.strftime('%Y-%m-%d')})
            except Exception: pass
            
            # News
            try:
                news_items = stk.news
                if news_items:
                    for item in news_items:
                        pub_time = item.get('providerPublishTime', None)
                        if pub_time:
                            pub_dt = datetime.fromtimestamp(pub_time)
                            if one_month_ago <= pub_dt <= one_month_ahead:
                                all_news.append({'Ticker': t, 'Title': item.get('title', 'News Item'), 'Link': item.get('link', '#'), 'Publisher': item.get('publisher', 'Financial News'), 'Date': pub_dt.strftime('%Y-%m-%d')})
            except Exception: pass

    with col_all_actions:
        st.markdown("#### 🎁 Corporate Actions (Past & Upcoming 30 Days)")
        with st.container(height=350):
            if all_actions:
                actions_df = pd.DataFrame(all_actions).sort_values(by='Date', ascending=False)
                for _, act in actions_df.iterrows():
                    st.markdown(f"• **[{act['Ticker']}]** {act['Type']}: `{act['Detail']}` on **{act['Date']}**")
            else:
                st.write("No corporate actions found within 30 days.")

    with col_all_news:
        st.markdown("#### 🗞️ Portfolio News Headlines (Past 30 Days)")
        with st.container(height=350):
            if all_news:
                news_df = pd.DataFrame(all_news).sort_values(by='Date', ascending=False)
                for _, n in news_df.iterrows():
                    st.markdown(f"• **[{n['Ticker']}]** [{n['Title']}]({n['Link']})")
                    st.caption(f"Source: {n['Publisher']} | Date: {n['Date']}")
            else:
                st.write("No news items found within 30 days.")

# TAB 3: FDS & BONDS
with tab_bonds:
    if not bonds_df.empty:
        st.subheader("🏦 Fixed Deposits & Bond Holdings")
        
        f1, f2 = st.columns(2)
        f1.metric("Total Monthly Income from FDs", f"₹{total_monthly_payout:,.2f}/mo")
        f2.metric("Total Interest Accumulated to Date", f"₹{total_bonds_earned_interest:,.2f}")
        
        st.markdown("---")
        fig_bonds = px.bar(
            bonds_df, x='Name', y='Current Value (₹)', color='Asset_Type',
            title="Invested vs Earned Value per Asset", barmode="group"
        )
        st.plotly_chart(fig_bonds, use_container_width=True)
        
        st.dataframe(
            bonds_df.style.format({
                'Invested_Amount': '₹{:.2f}',
                'Interest_Rate_Pct': '{:.2f}%',
                'Est. Monthly Payout (₹)': '₹{:.2f}',
                'Total Interest Earned (₹)': '₹{:.2f}',
                'Current Value (₹)': '₹{:.2f}'
            }), 
            use_container_width=True
        )
    else:
        st.info("No FDs or Bonds data loaded.")

# TAB 4: INCOME TRACKER (WITH NOTES/REMARKS SUPPORT)
with tab_income:
    if not income_df.empty:
        st.subheader("💵 Income Sources & Important Notes")
        
        fig_inc = px.pie(income_df, values='Amount', names='Source', title="Income Breakdown")
        st.plotly_chart(fig_inc, use_container_width=True)
        
        st.markdown("### 📋 Income Breakdown & Notes Table")
        st.dataframe(income_df, use_container_width=True)
    else:
        st.info("No Income data loaded.")
