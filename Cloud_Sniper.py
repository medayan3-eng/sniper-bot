import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 18.0 (The War Room)
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
    
    # אם לפני 9:30 בבוקר ניו יורק -> פרה מרקט
    if now_ny < market_open:
        return "🌅 PRE-MARKET (Live)", True
    return "☀️ MARKET OPEN", False

def get_latest_news(stock_obj):
    try:
        news = stock_obj.news
        if news and len(news) > 0:
            latest = news[0]
            title = latest['title']
            # ניתוח סנטימנט פשוט לפי מילים
            sentiment = "😐"
            t_lower = title.lower()
            if any(x in t_lower for x in ['beat', 'record', 'jump', 'surge', 'approval', 'buy', 'upgrade']):
                sentiment = "🟢"
            elif any(x in t_lower for x in ['miss', 'drop', 'fall', 'investigation', 'lawsuit', 'downgrade']):
                sentiment = "🔴"
            return f"{sentiment} {title}"
        return "No News"
    except:
        return "N/A"

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
            
            # prepost=True חובה לנתוני פרה-מרקט
            df = stock.history(period="5d", interval="15m", prepost=True)
            
            if df.empty or len(df) < 5:
                # הוספת מניה גם אם אין נתונים, כדי שתופיע ברשימה
                results.append({
                    "Ticker": ticker, "Status": "❌ ERROR", "Price": 0, "Gap": 0, 
                    "Instruction": "No Data", "News": "", "Target": 0, "Stop": 0
                })
                continue
            
            current_price = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1]
            
            # חישוב GAP (ביחס לסגירה של יום קודם)
            # מוצאים את המחיר האחרון של יום המסחר הקודם
            yesterday_close = df['Close'].iloc[-16] if len(df) > 16 else df['Close'].iloc[0]
            gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
            
            news = get_latest_news(stock)
            
            # --- סיווג (Classification) ---
            status = "💤 SLEEP"
            instruction = "Avoid / Low Vol"
            
            # 1. Action (Buy/Sell)
            if abs(gap_percent) > 3.0:
                if gap_percent > 0:
                    status = "⚡ ACTION (UP)"
                    instruction = "BUY THE DIP" if gap_percent < 15 else "WAIT PULLBACK"
                else:
                    status = "🔻 ACTION (DOWN)"
                    instruction = "WATCH REVERSAL"
            
            # 2. Watch (Active but small move)
            elif abs(gap_percent) > 1.0 or last_vol > 5000:
                status = "👀 WATCH"
                instruction = "Wait for Breakout"
            
            # יעדים
            stop_loss = current_price * 0.95
            target = current_price * 1.10
            
            results.append({
                "Ticker": ticker,
                "Status": status,
                "Price": round(current_price, 2),
                "Gap": round(gap_percent, 2),
                "Instruction": instruction,
                "News": news,
                "Target": round(target, 2),
                "Stop": round(stop_loss, 2)
            })
                
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), market_status

def plot_chart(ticker, status):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="2d", interval="5m", prepost=True)
        
        fig, ax = plt.subplots(figsize=(10, 3))
        # צבע הגרף לפי הסטטוס
        color = 'green' if 'UP' in status else 'red' if 'DOWN' in status else 'blue'
        
        ax.plot(df.index, df['Close'], color=color, label='Price')
        ax.set_title(f"{ticker} ({status})")
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI (ממשק)
# ==========================================
st.title("🤖 Day Trading Robot - War Room")

data_df, m_status = scan_market()
st.info(f"🕒 Market Status: **{m_status}**")

if not data_df.empty:
    
    # לשוניות
    tab1, tab2 = st.tabs(["📋 MASTER TABLE (Data)", "📈 CHARTS (Action Only)"])
    
    # --- טאב 1: הטבלה הגדולה ---
    with tab1:
        st.caption("Sort by clicking columns. Focus on '⚡ ACTION' rows.")
        
        # עיצוב הטבלה
        st.dataframe(
            data_df,
            column_config={
                "Ticker": "Symbol",
                "Status": st.column_config.TextColumn("Status", help="Action > Watch > Sleep"),
                "Gap": st.column_config.NumberColumn(
                    "Gap %",
                    format="%.2f%%",
                ),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Target": st.column_config.NumberColumn("Target (TP)", format="$%.2f"),
                "Stop": st.column_config.NumberColumn("Stop (SL)", format="$%.2f"),
                "News": "Latest News",
                "Instruction": "Strategy"
            },
            hide_index=True,
            use_container_width=True,
            height=600 # גובה הטבלה
        )

    # --- טאב 2: גרפים למניות חמות בלבד ---
    with tab2:
        # סינון: רק מניות שהן ACTION
        action_stocks = data_df[data_df['Status'].str.contains("ACTION")]
        
        if not action_stocks.empty:
            st.success(f"Showing charts for {len(action_stocks)} Action Stocks")
            for i, row in action_stocks.iterrows():
                st.divider()
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.subheader(f"{row['Ticker']}")
                    st.metric("Gap", f"{row['Gap']}%", f"{row['Price']}$")
                    st.write(f"**Strategy:** {row['Instruction']}")
                    st.caption(f"News: {row['News']}")
                with c2:
                    fig = plot_chart(row['Ticker'], row['Status'])
                    if fig: st.pyplot(fig)
        else:
            st.warning("No 'ACTION' stocks found right now. Check the table for 'WATCH' stocks.")

else:
    if st.button("🚀 RELOAD DATA"):
        st.rerun()
