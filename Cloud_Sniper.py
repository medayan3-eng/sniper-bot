import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 20.0 (Full Chart Vision)
# ==========================================
st.set_page_config(page_title="Day Trading Robot", page_icon="🤖", layout="wide")

# רשימת המניות
TICKERS = [
    'NVDA', 'AMD', 'PLTR', 'SOUN', 'BBAI', 'AI', 'SMCI', 'MU', 'ARM', 'TSM',
    'MARA', 'COIN', 'RIOT', 'MSTR', 'CLSK', 'BITF', 'HUT', 'CIFR',
    'OPEN', 'SOFI', 'PLUG', 'LCID', 'DKNG', 'CVNA', 'UPST', 'AFRM', 'GME', 'AMC',
    'DXCM', 'AKAM', 'ENPH', 'VST', 'ALB', 'ALNY', 'SYF', 'COF',
    'RKLB', 'GEV', 'INVZ', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'SCWO', 'MVO', 'CD', 'KITT', 'RDHL', 'FLXY', 'OSS', 'BHVN',
    'RGTI', 'QUBT', 'RGC', 'GLUE', 'MREO', 'BDSX', 'EVTV', 'SUGP',
    'SLQT', 'CLRB', 'ZBIO', 'STKL', 'UUU', 'AKAN', 'FBRX', 'BIOA', 'HYMC',
    'LVLU', 'KC', 'ZH', 'SRL', 'DAWN', 'OM', 'RBOT', 'ATEC', 'KUST', 'ANF', 'FLYX'
]
TICKERS = list(set(TICKERS))

# --- פונקציות ליבה ---

def get_data_status():
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    
    if now_ny < market_open:
        return "🌅 PRE-MARKET (Live)", True
    return "☀️ MARKET OPEN", False

def get_latest_news(stock_obj):
    try:
        news = stock_obj.news
        if news and len(news) > 0:
            latest = news[0]
            title = latest['title']
            sentiment = "😐"
            t_lower = title.lower()
            
            if any(x in t_lower for x in ['beat', 'record', 'jump', 'surge', 'approval', 'buy', 'upgrade', 'deal']):
                sentiment = "🟢"
                score = 10
            elif any(x in t_lower for x in ['miss', 'drop', 'fall', 'investigation', 'lawsuit', 'downgrade']):
                sentiment = "🔴"
                score = -10
            else:
                score = 0
                
            return f"{sentiment} {title}", score
        return "No News", 0
    except:
        return "N/A", 0

def calculate_score(gap, vol, news_score, price, vwap, price_vs_ema):
    score = 50 
    
    # GAP
    if gap > 2: score += 10
    if gap > 5: score += 5
    if gap < -5: score += 10 # Dip Buy opportunity
    
    # Volume
    if vol > 10000: score += 10
    
    # News
    score += news_score
    
    # Technicals
    if price > vwap: score += 10 # Bullish institutional
    if price_vs_ema: score += 10 # Bullish momentum
    
    return min(100, max(0, score))

def scan_market():
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    market_status, is_pre_market = get_data_status()
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            df = stock.history(period="5d", interval="15m", prepost=True)
            
            if df.empty or len(df) < 5:
                continue
            
            current_price = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1]
            
            # חישוב GAP
            yesterday_close = df['Close'].iloc[-16] if len(df) > 16 else df['Close'].iloc[0]
            gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
            
            # --- חישוב אינדיקטורים לציון ---
            # EMA 9
            df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
            price_above_ema = current_price > df['EMA_9'].iloc[-1]
            
            # VWAP
            df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            current_vwap = df['VWAP'].iloc[-1]
            
            # חדשות וניקוד
            news_text, news_score = get_latest_news(stock)
            final_score = calculate_score(gap_percent, last_vol, news_score, current_price, current_vwap, price_above_ema)
            
            # סטטוס
            status = "💤 SLEEP"
            instruction = ""
            
            if final_score >= 60:
                if gap_percent > 0:
                    status = "🚀 MOMENTUM"
                    instruction = "BUY THE DIP"
                else:
                    status = "💎 DIP BUY"
                    instruction = "WATCH REVERSAL"
            elif abs(gap_percent) > 2:
                status = "👀 WATCH"
                instruction = "Wait for Volume"
            
            # יעדים (לפחות 15-20%)
            stop_loss = current_price * 0.95
            target_profit = current_price * 1.20 
            if abs(gap_percent) > 10: target_profit = current_price * 1.30
            
            if status != "💤 SLEEP":
                results.append({
                    "Score": final_score,
                    "Ticker": ticker,
                    "Status": status,
                    "Price": round(current_price, 2),
                    "Gap": round(gap_percent, 2),
                    "Target": round(target_profit, 2),
                    "Stop": round(stop_loss, 2),
                    "Instruction": instruction,
                    "News": news_text
                })
                
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), market_status

def plot_full_chart(ticker, status):
    try:
        stock = yf.Ticker(ticker)
        # שואבים נתונים לגרף
        df = stock.history(period="2d", interval="5m", prepost=True)
        
        # חישוב האינדיקטורים לגרף
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # 1. המחיר (שחור)
        ax.plot(df.index, df['Close'], color='black', linewidth=1.5, label='Price')
        
        # 2. EMA 9 (כתום) - קו המומנטום
        ax.plot(df.index, df['EMA_9'], color='#ff7f0e', linewidth=1.5, linestyle='-', label='EMA 9 (Momentum)')
        
        # 3. VWAP (סגול מרוסק) - קו המוסדיים
        ax.plot(df.index, df['VWAP'], color='#9b59b6', linewidth=1.5, linestyle='--', label='VWAP (Support)')
        
        ax.set_title(f"{ticker} Analysis (Pre-Market Included)")
        ax.grid(True, alpha=0.3)
        ax.legend(loc='upper left') # מקרא בצד שמאל למעלה
        
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🤖 Day Trading Robot - Chart Master")

data_df, m_status = scan_market()
st.info(f"🕒 Market Status: **{m_status}**")

if not data_df.empty:
    data_df = data_df.sort_values(by='Score', ascending=False)
    
    tab1, tab2 = st.tabs(["🏆 SCORE BOARD", "📈 PRO CHARTS"])
    
    with tab1:
        st.dataframe(
            data_df,
            column_config={
                "Score": st.column_config.ProgressColumn("Score", format="%d", min_value=0, max_value=100),
                "Gap": st.column_config.NumberColumn("Gap %", format="%.1f%%"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Target": st.column_config.NumberColumn("Target", format="$%.2f"),
                "Stop": st.column_config.NumberColumn("Stop", format="$%.2f"),
                "News": "Latest News",
            },
            hide_index=True,
            use_container_width=True,
            height=500
        )

    with tab2:
        best_stocks = data_df[data_df['Score'] >= 60]
        if not best_stocks.empty:
            for i, row in best_stocks.iterrows():
                st.divider()
                st.markdown(f"### 🏅 {row['Ticker']} | Score: {row['Score']}")
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.info(f"**Action:** {row['Instruction']}")
                    st.write(f"**Gap:** {row['Gap']}%")
                    st.write(f"**News:** {row['News']}")
                    st.success(f"Target: ${row['Target']}")
                    st.error(f"Stop: ${row['Stop']}")
                with c2:
                    # כאן נוצר הגרף המלא
                    fig = plot_full_chart(row['Ticker'], row['Status'])
                    if fig: st.pyplot(fig)
        else:
            st.warning("No high-score stocks found.")

else:
    if st.button("🚀 RELOAD"):
        st.rerun()
