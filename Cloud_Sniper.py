import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 12.0 (Hybrid Sniper)
# ==========================================
st.set_page_config(page_title="AI Sniper Hybrid", page_icon="🦅", layout="wide")

# רשימת המניות (המעודכנת)
TICKERS = [
    'PLTR', 'RKLB', 'GEV', 'INVZ', 'NVO', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'INV', 'SCWO', 'ICON', 'MVO', 'FIEE', 'CD', 'KITT', 'UNTJ', 'RDHL', 'FLXY', 
    'STAI', 'ORGN', 'VIOT', 'BRNF', 'ROMA', 'OPEN', 'MU', 'SOUN', 'BBAI', 'ACLS', 
    'RGTI', 'QUBT', 'RGC', 'GLUE', 'IPSC', 'ERAS', 'MNTS', 'LIMN', 'GPUS', 'ABVE', 
    'VTYX', 'TGL', 'AMOD', 'FBLG', 'SLRX', 'COOT', 'RVMD', 'CLIR', 'GHRS', 'NMRA', 
    'MOBX', 'IMRX', 'RZLT', 'OLPX', 'OSS', 'BHVN', 'TNGX', 'MTEN', 'ANPA', 
    'NBY', 'VLN', 'GP', 'ATGL', 'OPAD', 'VCIG', 'THH', 'GGROW', 'ZNTL', 'ELOG', 
    'ZBAO', 'OPTX', 'CGON', 'MLTX', 'TCGL', 'MREO', 'HAO', 'NCRA', 'INBS', 'SOWG', 
    'QTRX', 'SXTC', 'MTAN', 'PASW', 'ACON', 'AQST', 'BBNX', 'PAPL', 'STSS', 'EDHL', 
    'JTAI', 'ATRA', 'MGRX', 'GRI', 'WSHP', 'NVVE', 'DRCT', 'BNZI', 'IZM',
    'EVTV', 'BDSX', 'SUGP', 'UP', 'SOGP', 'OMH', 'BEAM', 'BARK', 
    'LYRA', 'LXEO', 'VMAR', 'TSE', 
    'SLQT', 'CLRB', 'ZBIO', 'STKL', 'UUU', 'AKAN', 'FBRX', 'BIOA', 'HYMC',
    'LVLU', 'KC', 'ZH', 'SRL', 'DAWN', 'OM', 'RBOT', 
    'ATEC', 'KUST', 'ANF', 'FLYX', 'STOK', 'GOVX', 'LRHC'
]
TICKERS = list(set(TICKERS))

# --- פונקציות ליבה ---

def get_market_status():
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    
    if now_ny < market_open:
        return "🌅 PRE-MARKET", True
    return "☀️ MARKET OPEN", False

def check_data_delay(stock_df):
    try:
        last_time = stock_df.index[-1]
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        if (now_ny - last_time).total_seconds() > 1800: # 30 דקות
            return "🔴 OLD DATA"
        return "🟢 LIVE"
    except:
        return "❓"

def calculate_indicators(df):
    try:
        # ממוצעים לטרנד (Swing)
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        # ממוצע מהיר ליום (Day)
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR & Volatility
        df['TR'] = np.maximum((df['High'] - df['Low']), 
                   np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                   abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = df['TR'].rolling(14).mean()
        
        return df
    except:
        return pd.DataFrame()

def scan_market():
    results = []
    skipped_count = 0
    
    status, is_pre = get_market_status()
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            
            # --- פילטר נזילות ---
            try:
                info = stock.info
                avg_vol_10d = info.get('averageVolume10days', 0)
                if avg_vol_10d is not None and avg_vol_10d < 50000:
                    skipped_count += 1
                    continue
                
                float_shares = info.get('floatShares', 1000000000)
                if float_shares is None: float_shares = 1000000000
            except:
                skipped_count += 1
                continue

            # נתונים (קצת יותר היסטוריה בשביל ה-Swing)
            df = stock.history(period="6mo", interval="1d") # נתונים יומיים לניתוח סווינג
            
            # אם צריך נתונים תוך יומיים למסחר יומי, נמשוך גם אותם
            df_intraday = stock.history(period="5d", interval="30m")
            
            if df.empty or len(df) < 50:
                skipped_count += 1
                continue
            
            # חישוב אינדיקטורים על הגרף היומי
            df = calculate_indicators(df)
            last = df.iloc[-1]
            
            # נתונים בסיסיים
            price = last['Close']
            if price < 0.5: 
                skipped_count += 1
                continue

            # --- סיווג אסטרטגיה ---
            strategy_type = "NONE"
            reasons = []
            
            # 1. בדיקת Swing (מגמה יציבה)
            # תנאים: המחיר מעל ממוצע 20, ממוצע 20 מעל 50, ומגמה חיובית
            is_swing = False
            if price > last['SMA_20'] and last['SMA_20'] > last['SMA_50']:
                is_swing = True
            
            # 2. בדיקת Day Trade (תנודתיות ו-ווליום)
            # משתמשים בנתונים התוך-יומיים אם יש, או ביום האחרון
            is_day = False
            vol_ratio = 1.0
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if avg_vol > 0:
                vol_ratio = last['Volume'] / avg_vol
            
            # תנאי יום: ווליום חריג + תנודתיות (ATR) גבוהה ביחס למחיר
            volatility_pct = (last['ATR'] / price) * 100
            if vol_ratio > 1.5 and volatility_pct > 3.0:
                is_day = True

            # החלטה סופית על סוג
            if is_day:
                strategy_type = "☀️ DAY TRADE"
                reasons.append(f"High Vol (x{vol_ratio:.1f})")
                reasons.append(f"Volatile ({volatility_pct:.1f}%)")
            elif is_swing:
                strategy_type = "📅 SWING"
                reasons.append("Uptrend (Price > SMA20 > SMA50)")
            
            if strategy_type == "NONE":
                continue # לא מעניין אותנו

            # --- ניהול סיכונים (לפי ATR) ---
            stop_loss = price - (last['ATR'] * 2.0)
            take_profit = price + (last['ATR'] * 4.0)
            
            # ציון
            score = 50 # ציון התחלתי
            if is_day and float_shares < 20_000_000: score += 20 # יתרון למסחר יומי
            if is_swing and last['RSI'] < 70 and last['RSI'] > 50: score += 20 # יתרון לסווינג
            if vol_ratio > 2.0: score += 15
            
            probability = min(100, score)
            
            # סטטוס נתונים (מהגרף התוך יומי)
            data_status = "Unknown"
            if not df_intraday.empty:
                data_status = check_data_delay(df_intraday)

            results.append({
                "Ticker": ticker,
                "Strategy": strategy_type,
                "Price": price,
                "Action": "BUY WATCH",
                "Stop": stop_loss,
                "Target": take_profit,
                "Prob": probability,
                "Status": data_status,
                "Reasons": ", ".join(reasons)
            })
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), skipped_count

def plot_chart(ticker, strategy, stop, target):
    try:
        stock = yf.Ticker(ticker)
        # טווח זמן בגרף לפי האסטרטגיה
        period = "6mo" if "SWING" in strategy else "1mo"
        df = stock.history(period=period, interval="1d")
        
        # חישוב ממוצעים לציור
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], color='black', label='Price')
        
        if "SWING" in strategy:
            ax.plot(df.index, df['SMA_20'], color='orange', label='SMA 20')
            ax.plot(df.index, df['SMA_50'], color='blue', label='SMA 50')
            ax.set_title(f"{ticker} - SWING Analysis (Trend Follow)")
        else:
            ax.set_title(f"{ticker} - DAY TRADE Setup (Volatility)")
            
        ax.axhline(stop, color='red', linestyle='--', label='Stop')
        ax.axhline(target, color='green', linestyle='--', label='Target')
        ax.legend()
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🦅 AI Sniper - Hybrid Edition")
st.caption("Auto-Classifying: Day Trades (Volatility) vs. Swing Trades (Trends)")

if st.button("🚀 CLASSIFY & SCAN", type="primary"):
    with st.spinner('Analyzing Volatility & Trends...'):
        df, skipped = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            
            # יצירת לשוניות (Tabs)
            tab1, tab2 = st.tabs(["☀️ Day Trade (Intraday)", "📅 Swing Trade (Weekly)"])
            
            # --- לשונית 1: מסחר יומי ---
            with tab1:
                day_df = df[df['Strategy'].str.contains("DAY")]
                if not day_df.empty:
                    st.success(f"Found {len(day_df)} Explosive Day-Trade Setups")
                    for idx, row in day_df.iterrows():
                        with st.expander(f"🔥 {row['Ticker']} | ${row['Price']:.2f}", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.caption(f"Data: {row['Status']}")
                            with c2:
                                st.write(f"**Why:** {row['Reasons']}")
                                fig = plot_chart(row['Ticker'], "DAY", row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.info("No Day-Trade setups found (Low volatility currently).")

            # --- לשונית 2: סווינג ---
            with tab2:
                swing_df = df[df['Strategy'].str.contains("SWING")]
                if not swing_df.empty:
                    st.info(f"Found {len(swing_df)} Stable Swing Trends")
                    for idx, row in swing_df.iterrows():
                        with st.expander(f"📈 {row['Ticker']} | ${row['Price']:.2f}", expanded=False):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                            with c2:
                                st.write(f"**Trend:** {row['Reasons']}")
                                fig = plot_chart(row['Ticker'], "SWING", row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.info("No Swing setups found (Market might be choppy).")
            
            st.divider()
            st.caption(f"Filtered out {skipped} junk/illiquid stocks.")
            
        else:
            st.warning("No opportunities found.")
