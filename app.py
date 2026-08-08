import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

st.set_page_config(page_title="My Wealth Dashboard", layout="wide")
st.title("📊 Personal Wealth Dashboard")

# Sidebar for Google Sheets CSV Links
st.sidebar.header("Google Sheets Data Sources")
stocks_csv = st.sidebar.text_input("Stocks Sheet CSV URL:")

if stocks_csv:
    try:
        # Load stocks data
        stocks_df = pd.read_csv(stocks_csv)
        
        # Calculate Current Stock Values
        current_prices = []
        total_values = []
        
        for index, row in stocks_df.iterrows():
            ticker = row['Ticker']
            shares = float(row['Shares'])
            
            # Fetch live price via Yahoo Finance
            stock_data = yf.Ticker(ticker)
            live_price = stock_data.history(period="1d")['Close'].iloc[-1]
            
            current_prices.append(live_price)
            total_values.append(live_price * shares)
            
        stocks_df['Current_Price'] = current_prices
        stocks_df['Total_Value'] = total_values
        
        # Layout Top Metrics
        total_invested = (stocks_df['Shares'] * stocks_df['Buy_Price']).sum()
        total_current = stocks_df['Total_Value'].sum()
        profit_loss = total_current - total_invested
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invested", f"₹{total_invested:,.2f}")
        col2.metric("Current Portfolio Value", f"₹{total_current:,.2f}")
        col3.metric("Total Gain / Loss", f"₹{profit_loss:,.2f}", delta=f"{profit_loss:,.2f}")
        
        st.markdown("---")
        
        # Charts Section
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("Asset Allocation")
            fig_pie = px.pie(stocks_df, values='Total_Value', names='Ticker', title="Stock Value Breakdown")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_chart2:
            st.subheader("Holdings Value")
            fig_bar = px.bar(stocks_df, x='Ticker', y='Total_Value', title="Value per Holding", color='Ticker')
            st.plotly_chart(fig_bar, use_container_width=True)
            
        st.subheader("Stock Holdings Data")
        st.dataframe(stocks_df)
        
    except Exception as e:
        st.error(f"Error reading Google Sheet CSV. Please check the URL format. Details: {e}")
else:
    st.info("👈 Paste your published Google Sheet CSV link in the sidebar to view your live dashboard!")
