import streamlit as st
import os
from dotenv import load_dotenv
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from database import TradingDatabase
from ai_analyzer import FuryTraderAI

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="FuryTrader Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 1rem;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = TradingDatabase()

if 'ai' not in st.session_state:
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        st.session_state.ai = FuryTraderAI(api_key=api_key)
    else:
        st.session_state.ai = None

# Header
st.markdown('<h1 class="main-header">📈 FuryTrader Pro</h1>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar
with st.sidebar:
    st.title("Navigation")
    page = st.radio(
        "Choose Module",
        ["🏠 Dashboard", "🤖 AI Analysis", "📝 Manual Journal", "📊 Analytics", "⚙️ Settings"],
        key="main_navigation",  # FIXED: Added unique key
        label_visibility="collapsed"
    )
    st.markdown("---")
    stats = st.session_state.db.get_statistics()
    st.metric("Total Trades", stats['total_trades'])
    st.metric("Win Rate", f"{stats['win_rate']:.1f}%")
    st.metric("Total P&L", f"${stats['total_pnl']:.2f}")
    st.markdown("---")
    st.caption("FuryTrader Pro v5.0")

# DASHBOARD PAGE
if page == "🏠 Dashboard":
    st.header("📊 Trading Dashboard")
    stats = st.session_state.db.get_statistics()
    trades_df = st.session_state.db.get_all_trades()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", stats['total_trades'], delta=f"{stats.get('wins', 0)} Wins")  # FIXED
    with col2:
        st.metric("Win Rate", f"{stats['win_rate']:.1f}%", delta=f"{stats.get('losses', 0)} Losses")  # FIXED
    with col3:
        st.metric("Avg R:R", f"{stats['avg_rr']:.2f}R", delta="Per Trade")
    with col4:
        st.metric("Total P&L", f"${stats['total_pnl']:.2f}", delta=f"Best: ${stats['best_trade']:.2f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📈 Equity Curve")
        if not trades_df.empty and 'balance_after' in trades_df.columns:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trades_df['date'], y=trades_df['balance_after'],
                mode='lines+markers', name='Balance',
                line=dict(color='#667eea', width=3)
            ))
            fig.update_layout(height=300, xaxis_title="Date", yaxis_title="Balance ($)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades yet!")
    
    with col2:
        st.subheader("🎯 Win/Loss")
        if not trades_df.empty and 'outcome' in trades_df.columns:
            outcome_counts = trades_df['outcome'].value_counts()
            fig = go.Figure(data=[go.Pie(
                labels=outcome_counts.index, values=outcome_counts.values, hole=.4
            )])
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades yet!")
    
    st.markdown("---")
    st.subheader("📋 Recent Trades")
    if not trades_df.empty:
        display_df = trades_df.head(10)[['date', 'pair', 'direction', 'entry_price', 'outcome', 'pnl']]
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info("No trades recorded yet!")

# AI ANALYSIS PAGE
elif page == "🤖 AI Analysis":
    st.header("🤖 AI Chart Analysis")
    
    if st.session_state.ai is None:
        st.error("⚠️ OpenAI API key not found! Add it to .env file.")
        st.stop()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📸 Upload Charts")
        pair = st.text_input("Currency Pair", "GBP/CAD")
        htf_image = st.file_uploader("📊 Higher Timeframe", type=['png', 'jpg', 'jpeg'], key="htf")
        h1_image = st.file_uploader("⏰ 1 Hour Chart", type=['png', 'jpg', 'jpeg'], key="h1")
        ltf_image = st.file_uploader("🎯 Lower Timeframe (Optional)", type=['png', 'jpg', 'jpeg'], key="ltf")
        user_context = st.text_area("Context (Optional)", height=100)
    
    with col2:
        st.info("**What to upload:**\n- HTF (Daily/4H)\n- 1H Chart\n- LTF (Optional)")
    
    if st.button("🔍 Analyze Charts", type="primary", key="analyze_btn"):
        if not htf_image or not h1_image:
            st.error("Upload HTF and 1H charts!")
        else:
            with st.spinner("🧠 Analyzing..."):
                images = [htf_image.read(), h1_image.read()]
                timeframes = ["HTF", "1H"]
                if ltf_image:
                    images.append(ltf_image.read())
                    timeframes.append("LTF")
                
                result = st.session_state.ai.analyze_chart(images, pair, timeframes, user_context)
                
                if result['success']:
                    st.session_state.analysis_result = result
                    st.success("✅ Analysis complete!")
                    st.rerun()
                else:
                    st.error(f"❌ Failed: {result['error']}")
    
    if 'analysis_result' in st.session_state:
        st.markdown("---")
        result = st.session_state.analysis_result
        parsed = result['parsed']
        
        if 'YES' in parsed['verdict'].upper():
            st.success(f"### ✅ {parsed['verdict']} | Confidence: {parsed['confidence']}/10")
        else:
            st.warning(f"### ⏸️ {parsed['verdict']} | Confidence: {parsed['confidence']}/10")
        
        st.subheader("📖 Market Story")
        st.write(parsed['market_story'])
        
        st.subheader("🎯 Confluences")
        for conf in parsed['confluences']:
            st.markdown(f"- {conf}")
        
        tab1, tab2, tab3 = st.tabs(["Scenario A", "Scenario B", "Scenario C"])
        
        with tab1:
            scenario = parsed['scenario_a']
            if scenario:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Entry", scenario.get('entry', 'N/A'))
                with col2:
                    st.metric("SL", scenario.get('stop_loss', 'N/A'))
                with col3:
                    st.metric("TP", scenario.get('take_profit', 'N/A'))
                st.write("**Logic:**", scenario.get('logic', 'N/A'))
        
        with st.expander("📄 Full Response"):
            st.text(result['raw_analysis'])

# MANUAL JOURNAL PAGE
elif page == "📝 Manual Journal":
    st.header("📝 Manual Trade Journal")
    
    with st.form("trade_entry"):
        col1, col2, col3 = st.columns(3)
        with col1:
            trade_date = st.date_input("Date")
            pair = st.text_input("Pair", "EUR/USD")
            direction = st.selectbox("Direction", ["LONG", "SHORT"])
        with col2:
            entry_price = st.number_input("Entry", min_value=0.0, step=0.0001, format="%.4f")
            stop_loss = st.number_input("Stop Loss", min_value=0.0, step=0.0001, format="%.4f")
            take_profit = st.number_input("Take Profit", min_value=0.0, step=0.0001, format="%.4f")
        with col3:
            balance_before = st.number_input("Balance Before", min_value=0.0)
            balance_after = st.number_input("Balance After", min_value=0.0)
            outcome = st.selectbox("Outcome", ["Win", "Loss", "Break Even"])
        
        confluences = st.multiselect("Confluences", 
            ["FVG", "Snake Trick", "H&S", "Double Top/Bottom", "Supply/Demand"])
        setup_type = st.selectbox("Setup", ["Gap", "Day", "Continuation"])
        narrative = st.text_area("Narrative", height=100)
        
        if st.form_submit_button("💾 Log Trade", type="primary"):
            pnl = balance_after - balance_before if balance_before > 0 else 0
            trade_data = {
                'date': trade_date.strftime('%Y-%m-%d'), 'pair': pair, 'direction': direction,
                'entry_price': entry_price, 'stop_loss': stop_loss, 'take_profit': take_profit,
                'balance_before': balance_before, 'balance_after': balance_after,
                'pnl': pnl, 'outcome': outcome, 'confluences': ', '.join(confluences),
                'narrative': narrative, 'setup_type': setup_type
            }
            trade_id = st.session_state.db.add_trade(trade_data)
            st.success(f"✅ Logged! ID: {trade_id}")

# ANALYTICS PAGE
elif page == "📊 Analytics":
    st.header("📊 Analytics")
    trades_df = st.session_state.db.get_all_trades()
    
    if trades_df.empty:
        st.info("No data yet!")
        st.stop()
    
    tab1, tab2 = st.tabs(["By Setup", "By Pair"])
    
    with tab1:
        if 'setup_type' in trades_df.columns:
            setup_stats = trades_df.groupby('setup_type').agg({
                'id': 'count', 'pnl': 'sum'
            }).reset_index()
            fig = go.Figure(data=[go.Bar(x=setup_stats['setup_type'], y=setup_stats['pnl'])])
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        if 'pair' in trades_df.columns:
            pair_stats = trades_df.groupby('pair')['pnl'].sum().reset_index()
            fig = go.Figure(data=[go.Bar(x=pair_stats['pair'], y=pair_stats['pnl'])])
            st.plotly_chart(fig, use_container_width=True)

# SETTINGS PAGE
elif page == "⚙️ Settings":
    st.header("⚙️ Settings")
    st.subheader("🔑 API Key")
    current_key = os.getenv('OPENAI_API_KEY')
    if current_key:
        st.success(f"✅ Configured: {current_key[:8]}...")
    else:
        st.error("❌ Not found")
    
    st.markdown("---")
    st.subheader("💾 Export Data")
    if st.button("Download Trades CSV"):
        trades_df = st.session_state.db.get_all_trades()
        if not trades_df.empty:
            csv = trades_df.to_csv(index=False)
            st.download_button("⬇️ Download", csv, 
                f"trades_{datetime.now().strftime('%Y%m%d')}.csv", "text/csv")