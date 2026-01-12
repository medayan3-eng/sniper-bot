import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 16.0 (Day Trader Pro)
# ==========================================
st.set_page_config(page_title="Day Trader Pro", page_icon="⚡", layout="wide")

# רשימת המניות (ממוקדת למסחר יומי: AI, קריפטו, תנודתיות)
TICKERS = [
    # AI & Chips
    'NVDA', 'AMD', 'PLTR', 'SOUN', 'BBAI', 'AI', 'SMCI', 'MU', 'ARM', 'TSM',
    # Crypto
    'MARA', 'COIN', 'RIOT', 'MSTR', 'CLSK', 'BITF', 'HUT', 'CIFR',
    # High Volatility / Meme
    'OPEN', 'SOFI', 'PLUG', 'LCID', 'DKNG', 'CVNA', 'UPST', 'AFRM', 'GME', 'AMC',
    # The requests
    'DXCM', 'AKAM', 'ENPH', 'VST', 'ALB', 'ALNY', 'SYF', 'COF',
    # Recent Movers
    'RKLB', 'GEV', 'INVZ', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'SCWO', 'MVO', 'CD', 'KITT', 'RDHL', 'FLXY', 'OSS', 'BHVN',
    'RGTI', 'QUBT', 'RGC', 'GLUE', 'MREO', 'BDSX', 'EVTV', 'SUGP'
]
TICKERS = list(set(TICKERS))

# --- פונקציות ליבה ---

def get_market_status():
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    if now_ny < market_open: return "🌅 PRE-MARKET"
    return "☀️ MARKET OPEN"

def calculate_vwap(df):
    v = df['Volume'].values
    p = df['Close'].values
    return df.assign(VWAP=(p * v).cumsum() / v.cumsum())

def analyze_day_structure(df):
    """ ניתוח עומק למסחר יומי """
    # אינדיקטורים בסיסיים
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ATR (תנודתיות)
    df['TR'] = np.maximum((df['High'] - df['Low']), 
                   np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                   abs(df['Low'] - df['Close'].shift(1))))
    df['ATR'] = df['TR'].rolling(14).mean()
    
    # זיהוי נר פטיש (Hammer) - להיפוך
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Lower_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['Hammer'] = (df['Lower_Wick'] > 2 * df['Body']) & (df['RSI'] < 35)
    
    # זיהוי פריצה של הגבוה היומי (של 20 יום אחרונים)
    df['20_Day_High'] = df['High'].rolling(window=20).max()
    
    return df

def scan_market():
    results = []
    skipped_count = 0
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            
            # --- שלב 1: האם המניה חיה היום? ---
            try:
                # מושכים גרף יומי (לניתוח כללי) + גרף תוך יומי (אם יש)
                df = stock.history(period="3mo", interval="1d")
                if df.empty or len(df) < 30:
                    skipped_count += 1
                    continue
                
                # בדיקת מחיר מינימום
                last_price = df['Close'].iloc[-1]
                if last_price < 0.5: 
                    skipped_count += 1
                    continue

                # בדיקת ווליום יחסי (האם יש עניין היום?)
                avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
                last_vol = df['Volume'].iloc[-1]
                vol_ratio = last_vol / avg_vol if avg_vol > 0 else 0
                
            except:
                skipped_count += 1
                continue

            # --- שלב 2: הפעלת המנוע ---
            df = calculate_vwap(df)
            df = analyze_day_structure(df)
            
            last = df.iloc[-1]
            
            # --- סיווג לאסטרטגיות (Day Strategies) ---
            strategy = "NONE"
            reasons = []
            score = 0
            
            # אסטרטגיה 1: 🔥 Momentum (ווליום + מעל VWAP)
            if vol_ratio > 1.5 and last_price > last['VWAP']:
                strategy = "MOMENTUM"
                score += 30
                reasons.append(f"Vol x{vol_ratio:.1f}")
                reasons.append("Above VWAP")
            
            # אסטרטגיה 2: 🚨 Breakout (פריצת שיא)
            # אם המחיר קרוב מאוד לשיא של 20 יום (או שבר אותו)
            if last_price >= last['20_Day_High'] * 0.98:
                strategy = "BREAKOUT"
                score += 40
                reasons.append("Testing 20-Day High")
                
            # אסטרטגיה 3: 📉 Reversal (היפוך למעלה)
            # RSI נמוך + נר פטיש
            if last['Hammer']:
                strategy = "REVERSAL"
                score += 25
                reasons.append("Hammer Candle")
                reasons.append(f"RSI {last['RSI']:.0f} (Oversold)")

            # אם לא מצאנו כלום - דלג
            if strategy == "NONE":
                skipped_count += 1
                continue

            # --- ניהול סיכונים ---
            # סטופ צמוד למסחר יומי (1.5 ATR)
            stop_loss = last_price - (last['ATR'] * 1.5)
            # יעד רווח (פי 3 מהסיכון)
            target = last_price + (last['ATR'] * 4.5)
            
            potential = ((target - last_price) / last_price) * 100
            
            results.append({
                "Ticker": ticker,
                "Strategy": strategy,
                "Price": last_price,
                "Stop": stop_loss,
                "Target": target,
                "Potential": f"+{potential:.1f}%",
                "Reasons": ", ".join(reasons),
                "Score": score
            })
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), skipped_count

def plot_day_chart(ticker, stop, target):
    try:
        stock = yf.Ticker(ticker)
        # גרף קצר טווח
        df = stock.history(period="1mo", interval="1d")
        df = calculate_vwap(df)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        
        # מחיר
        ax.plot(df.index, df['Close'], color='black', label='Price')
        # VWAP
        ax.plot(df.index, df['VWAP'], color='#9b59b6', linestyle='-', alpha=0.8, label='VWAP')
        
        # קווים
        ax.axhline(stop, color='red', linestyle='--', label='Stop')
        ax.axhline(target, color='green', linestyle='--', label='Target')
        
        ax.set_title(f"{ticker} Day Analysis")
        ax.legend()
        ax.grid(True, alpha=0.3)
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("⚡ Day Trader Pro")
status = get_market_status()
st.caption(f"Status: {status} | Mode: Intraday Only | No Swing")

if st.button("🚀 SCAN DAY OPPORTUNITIES", type="primary"):
    with st.spinner('Hunting High Volume & Breakouts...'):
        df, skipped = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Score', ascending=False)
            
            # יצירת לשוניות לפי סוג האסטרטגיה
            t1, t2, t3 = st.tabs(["🔥 Momentum", "🚨 Breakouts", "📉 Reversals (Dip)"])
            
            # 1. Momentum
            with t1:
                mom = df[df['Strategy'] == "MOMENTUM"]
                if not mom.empty:
                    for i, row in mom.iterrows():
                        with st.expander(f"🔥 {row['Ticker']} | Est. {row['Potential']}", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.write(f"**Price:** ${row['Price']:.2f}")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            with c2:
                                st.info(f"Why: {row['Reasons']}")
                                fig = plot_day_chart(row['Ticker'], row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.info("No pure momentum setups right now.")

            # 2. Breakouts
            with t2:
                brk = df[df['Strategy'] == "BREAKOUT"]
                if not brk.empty:
                    for i, row in brk.iterrows():
                        with st.expander(f"🚨 {row['Ticker']} | Est. {row['Potential']}", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.write(f"**Price:** ${row['Price']:.2f}")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            with c2:
                                st.success(f"Why: {row['Reasons']}")
                                fig = plot_day_chart(row['Ticker'], row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.info("No stocks breaking highs right now.")

            # 3. Reversals
            with t3:
                rev = df[df['Strategy'] == "REVERSAL"]
                if not rev.empty:
                    for i, row in rev.iterrows():
                        with st.expander(f"📉 {row['Ticker']} (Buy the Dip)", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.write(f"**Price:** ${row['Price']:.2f}")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            with c2:
                                st.warning(f"Why: {row['Reasons']}")
                                fig = plot_day_chart(row['Ticker'], row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.info("No reversal patterns found.")
                    
        else:
            st.error("No setups found. Market might be quiet.")
