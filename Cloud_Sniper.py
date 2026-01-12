import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 13.0 (Profit Hunter)
# ==========================================
st.set_page_config(page_title="AI Sniper Pro", page_icon="🦅", layout="wide")

# רשימת המניות
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
    if now_ny < market_open: return "🌅 PRE-MARKET"
    return "☀️ MARKET OPEN"

def calculate_indicators(df):
    try:
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
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
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            
            # בדיקת נתונים בסיסית
            try:
                info = stock.info
                float_shares = info.get('floatShares', 1000000000)
                if float_shares is None: float_shares = 1000000000
            except:
                float_shares = 1000000000

            # הורדת נתונים (מספיק היסטוריה לניתוח)
            df = stock.history(period="3mo", interval="1d")
            if df.empty or len(df) < 30:
                skipped_count += 1
                continue
            
            # --- חישובים ---
            df = calculate_indicators(df)
            last = df.iloc[-1]
            price = last['Close']
            
            if price < 0.1: # סינון רק למניות "מתות" ממש
                skipped_count += 1
                continue

            # --- סיווג אסטרטגיה ---
            strategy_type = "📅 SWING" # ברירת מחדל
            reasons = []
            
            # זיהוי מסחר יומי (תנודתיות גבוהה)
            vol_ratio = 1.0
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if avg_vol > 0: vol_ratio = last['Volume'] / avg_vol
            
            if vol_ratio > 1.5 or (last['ATR']/price) > 0.04:
                strategy_type = "☀️ DAY TRADE"
                reasons.append(f"High Volatility")

            if float_shares < 20_000_000:
                reasons.append("Low Float")

            # --- חישוב יעד רווח (הבקשה שלך: מינימום 20%) ---
            stop_loss = price - (last['ATR'] * 1.5)
            
            # היעד הוא הגבוה מבין השניים: או טכני (ATR) או 20% קבוע
            target_technical = price + (last['ATR'] * 4.0)
            target_min_20 = price * 1.20
            take_profit = max(target_technical, target_min_20)
            
            # חישוב אחוז פוטנציאלי
            potential_pct = ((take_profit - price) / price) * 100

            # ניקוד
            score = 50
            if strategy_type == "☀️ DAY TRADE": score += 10
            if float_shares < 20_000_000: score += 20
            if last['Close'] > last['EMA_9']: score += 15
            if vol_ratio > 2.0: score += 15

            results.append({
                "Ticker": ticker,
                "Strategy": strategy_type,
                "Price": price,
                "Stop": stop_loss,
                "Target": take_profit,
                "Potential": f"+{potential_pct:.1f}%",
                "Prob": min(100, score),
                "Reasons": ", ".join(reasons)
            })
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), skipped_count

def plot_chart(ticker, stop, target):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d")
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], color='black', label='Price')
        
        # קווים
        ax.axhline(stop, color='red', linestyle='--', label='Stop Loss')
        ax.axhline(target, color='green', linestyle='--', label='Target (+20% Min)')
        
        ax.set_title(f"{ticker} Analysis")
        ax.legend()
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🦅 AI Sniper - Profit Hunter")
st.caption("Auto-Target: Minimum 20% Profit on all setups")

status = get_market_status()
st.info(f"Status: {status}")

if st.button("🚀 START PROFIT SCAN", type="primary"):
    with st.spinner('Hunting 20%+ Opportunities...'):
        df, skipped = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            
            # --- כאן הלשוניות שביקשת ---
            tab1, tab2 = st.tabs(["☀️ Day Trade (Volatile)", "📅 Swing Trade (Trends)"])
            
            # לשונית 1
            with tab1:
                day_df = df[df['Strategy'] == "☀️ DAY TRADE"]
                if not day_df.empty:
                    st.success(f"Found {len(day_df)} Day Trade Tickers")
                    for idx, row in day_df.iterrows():
                        with st.expander(f"🔥 {row['Ticker']} | Potential: {row['Potential']}", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.write(f"Price: ${row['Price']:.2f}")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            with c2:
                                st.caption(row['Reasons'])
                                fig = plot_chart(row['Ticker'], row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.warning("No high-volatility stocks found today.")

            # לשונית 2
            with tab2:
                swing_df = df[df['Strategy'] == "📅 SWING"]
                if not swing_df.empty:
                    st.info(f"Found {len(swing_df)} Swing Candidates")
                    for idx, row in swing_df.iterrows():
                        with st.expander(f"📈 {row['Ticker']} | Potential: {row['Potential']}", expanded=False):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.write(f"Price: ${row['Price']:.2f}")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            with c2:
                                st.caption(row['Reasons'])
                                fig = plot_chart(row['Ticker'], row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.warning("No swing setups found.")
            
        else:
            st.error("No data found at all. Check connection or tickers.")
