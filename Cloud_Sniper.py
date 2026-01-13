import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 21.0 (Sniper Elite)
# ==========================================
st.set_page_config(page_title="Day Trading Robot", page_icon="🎯", layout="wide")

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
            score = 0
            if any(x in t_lower for x in ['beat', 'record', 'jump', 'surge', 'approval', 'buy', 'upgrade']):
                sentiment = "🟢"
                score = 10
            elif any(x in t_lower for x in ['miss', 'drop', 'fall', 'investigation', 'lawsuit', 'downgrade']):
                sentiment = "🔴"
                score = -10
            return f"{sentiment} {title}", score
        return "No News", 0
    except:
        return "N/A", 0

def analyze_daily_context(ticker):
    """ ניתוח הרקע היומי - 3 ימי ירידות ומגמה ראשית """
    try:
        stock = yf.Ticker(ticker)
        # מושכים חודש אחרון של נרות יומיים
        daily = stock.history(period="1mo", interval="1d")
        
        if len(daily) < 5: return 0, False, 0
        
        # 1. בדיקת רצף ירידות (The User's Idea)
        # בודקים אם 3 הימים האחרונים היו אדומים (Close < Open או ירידה במחיר)
        last_3 = daily.tail(3)
        is_3_red_days = all(day['Close'] < day['Open'] for i, day in last_3.iterrows())
        
        # 2. בדיקת המגמה הראשית (SMA 50)
        sma_50 = daily['Close'].rolling(window=50).mean().iloc[-1]
        last_close = daily['Close'].iloc[-1]
        is_uptrend = last_close > sma_50 # האם אנחנו במגמה עולה כללית?
        
        # 3. רמות מפתח
        yesterday_high = daily['High'].iloc[-2]
        yesterday_low = daily['Low'].iloc[-2]
        
        return is_3_red_days, is_uptrend, yesterday_high
    except:
        return False, False, 0

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
            
            # ניתוח יומי (הרקע)
            is_3_drops, is_uptrend, yest_high = analyze_daily_context(ticker)
            
            stock = yf.Ticker(ticker)
            df = stock.history(period="5d", interval="15m", prepost=True)
            
            if df.empty or len(df) < 5: continue
            
            current_price = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1]
            
            # GAP calculation
            yesterday_close = df['Close'].iloc[-16] if len(df) > 16 else df['Close'].iloc[0]
            gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
            
            # Indicators
            df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
            df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
            current_vwap = df['VWAP'].iloc[-1]
            price_vs_ema = current_price > df['EMA_9'].iloc[-1]
            
            # News
            news_text, news_score = get_latest_news(stock)
            
            # --- חישוב הציון החדש (Sniper Score) ---
            score = 50
            reasons = []
            
            # הבונוס של "הקפיץ" (הרעיון שלך)
            if is_3_drops:
                score += 15
                reasons.append("Spring Loaded (3 Red Days)")
            
            # האם פרצנו את הגבוה של אתמול?
            if current_price > yest_high:
                score += 15
                reasons.append("Broke Yesterday High")
                
            # מגמה ראשית
            if is_uptrend:
                score += 10
            else:
                score -= 5 # מסוכן לקנות במגמה יורדת
            
            # טכני תוך יומי
            if gap_percent > 2: score += 10
            if current_price > current_vwap: score += 10
            if last_vol > 10000: score += 5
            score += news_score
            
            final_score = min(100, max(0, score))
            
            # --- אסטרטגיה ---
            status = "💤 SLEEP"
            instruction = ""
            
            if final_score >= 70:
                if is_3_drops and gap_percent > -1:
                    status = "🪃 REVERSAL" # הקפיץ משתחרר
                    instruction = "STRONG BUY (Oversold Bounce)"
                elif gap_percent > 0 and current_price > yest_high:
                    status = "🚀 BREAKOUT"
                    instruction = "MOMENTUM BUY"
                else:
                    status = "⚡ ACTION"
                    instruction = "Watch Intraday"
            elif final_score >= 50 and abs(gap_percent) > 2:
                status = "👀 WATCH"
                instruction = "Wait for Setup"

            # ניהול סיכונים
            stop_loss = current_price * 0.95
            target = current_price * 1.15
            
            if status != "💤 SLEEP":
                results.append({
                    "Score": final_score,
                    "Ticker": ticker,
                    "Status": status,
                    "Price": round(current_price, 2),
                    "Gap": round(gap_percent, 2),
                    "Target": round(target, 2),
                    "Stop": round(stop_loss, 2),
                    "Details": ", ".join(reasons),
                    "News": news_text
                })
                
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), market_status

def plot_elite_chart(ticker, reasons):
    try:
        stock = yf.Ticker(ticker)
        # נתונים תוך יומיים
        df = stock.history(period="2d", interval="5m", prepost=True)
        # נתונים יומיים (כדי לראות את ה-3 ימים אחורה)
        daily = stock.history(period="5d", interval="1d")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        # גרף 1: תוך יומי (הרגיל)
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
        
        ax1.plot(df.index, df['Close'], color='black', label='Price')
        ax1.plot(df.index, df['EMA_9'], color='orange', label='EMA 9')
        ax1.plot(df.index, df['VWAP'], color='purple', linestyle='--', label='VWAP')
        ax1.set_title(f"{ticker} - Intraday (Today)")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # גרף 2: יומי (Daily Context) - כדי לראות את ה-3 ימים ירידה
        # צבעים לנרות: ירוק לעליה, אדום לירידה
        colors = ['green' if c >= o else 'red' for c, o in zip(daily['Close'], daily['Open'])]
        ax2.bar(daily.index, daily['Close'] - daily['Open'], bottom=daily['Open'], color=colors, width=0.5)
        ax2.plot(daily.index, daily['Close'], color='blue', alpha=0.3) # קו מחיר
        ax2.set_title("Daily Trend (Last 5 Days)")
        ax2.grid(True, alpha=0.3)
        
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🎯 AI Sniper - Elite Edition")
st.caption("Filters: 3-Day Drop | Yesterday's High Breakout | Daily Trend")

data_df, m_status = scan_market()
st.info(f"🕒 Market Status: **{m_status}**")

if not data_df.empty:
    data_df = data_df.sort_values(by='Score', ascending=False)
    
    tab1, tab2 = st.tabs(["📊 SNIPER TABLE", "🔬 DEEP ANALYSIS"])
    
    with tab1:
        st.dataframe(
            data_df,
            column_config={
                "Score": st.column_config.ProgressColumn("Confidence", format="%d", min_value=0, max_value=100),
                "Status": st.column_config.TextColumn("Signal"),
                "Gap": st.column_config.NumberColumn("Gap %", format="%.1f%%"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Details": "Why to Buy?",
                "News": "Sentiment"
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

    with tab2:
        # רק מניות איכותיות באמת
        elite_stocks = data_df[data_df['Score'] >= 70]
        if not elite_stocks.empty:
            for i, row in elite_stocks.iterrows():
                st.divider()
                st.markdown(f"### 🎯 {row['Ticker']} | Score: {row['Score']}")
                st.markdown(f"**Thesis:** {row['Details']}")
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.info(f"Signal: {row['Status']}")
                    st.write(f"Strategy: {row['Status']}")
                    st.success(f"Target: ${row['Target']}")
                    st.error(f"Stop: ${row['Stop']}")
                with c2:
                    fig = plot_elite_chart(row['Ticker'], row['Details'])
                    if fig: st.pyplot(fig)
        else:
            st.warning("No 'Elite' setups found. Market might be choppy.")

else:
    if st.button("🚀 RELOAD"):
        st.rerun()
