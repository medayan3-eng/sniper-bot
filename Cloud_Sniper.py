import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 11.0 (Liquidity Guard)
# ==========================================
st.set_page_config(page_title="AI Sniper Pro", page_icon="🦅", layout="wide")

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
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
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
    
    status, is_pre = get_market_status()
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            
            # --- פילטר 1: ווליום ממוצע (מסננת זבל) ---
            try:
                info = stock.info
                avg_vol_10d = info.get('averageVolume10days', 0)
                if avg_vol_10d is not None and avg_vol_10d < 50000: # אם פחות מ-50 אלף מניות ביום
                    skipped_count += 1
                    continue # דלג למניה הבאה
                    
                float_shares = info.get('floatShares', 1000000000)
                if float_shares is None: float_shares = 1000000000
            except:
                skipped_count += 1
                continue

            # --- משיכת נתונים ---
            # מושכים נתונים של 5 ימים כדי לקבל ממוצעים טובים
            df = stock.history(period="5d", interval="30m")
            
            if df.empty or len(df) < 20:
                skipped_count += 1
                continue
            
            # --- פילטר 2: מחיר מינימום ---
            last_price = df['Close'].iloc[-1]
            if last_price < 0.5: # מניות מתחת ל-50 סנט זה מסוכן מידי
                skipped_count += 1
                continue

            # חישוב אינדיקטורים
            df = calculate_indicators(df)
            last = df.iloc[-1]
            atr = last['ATR']
            
            # --- פילטר 3: נזילות רגעית (Liquidity Check) ---
            # בדיקה: האם בנר האחרון עבר כסף אמיתי?
            dollar_volume = last['Close'] * last['Volume']
            liquidity_status = "OK"
            
            # אם ב-30 הדקות האחרונות עברו פחות מ-10,000 דולר - זו מניה תקועה
            if dollar_volume < 10000: 
                liquidity_status = "⚠️ LOW LIQ"

            # --- אסטרטגיה ---
            entry_price = last['High'] + (atr * 0.5)
            stop_loss = entry_price - (atr * 2.0)
            take_profit = entry_price + (atr * 4.0)
            
            score = 0
            reasons = []
            
            if float_shares < 20_000_000:
                score += 25
                reasons.append("🔥 Low Float")
            
            if last['Close'] > last['EMA_9']:
                score += 15
                reasons.append("📈 Trend UP")
                
            if last['RSI'] < 35: 
                score += 20
                reasons.append("📉 Oversold")
            elif last['RSI'] > 50 and last['RSI'] < 70:
                score += 10
                reasons.append("⚡ Momentum")

            # בדיקת ווליום יחסי
            avg_vol_recent = df['Volume'].rolling(20).mean().iloc[-1]
            if avg_vol_recent > 0 and last['Volume'] > avg_vol_recent * 1.5:
                score += 25
                reasons.append("📢 High Vol")

            probability = max(0, min(100, score))
            action = "WAIT"
            
            if probability >= 80: action = "💎 SETUP READY"
            elif probability >= 65: action = "🟢 WATCH"
            
            # אם הנזילות נמוכה, מבטלים המלצת קנייה
            if liquidity_status == "⚠️ LOW LIQ":
                action = "⚠️ STUCK / ILLIQUID"
                probability = 0
            
            # אם הציון גבוה, שומרים
            if probability > 50 or "SETUP" in action:
                data_status = check_data_delay(df)
                
                results.append({
                    "Ticker": ticker,
                    "Price": last_price,
                    "Action": action,
                    "Entry": entry_price,
                    "Stop": stop_loss,
                    "Target": take_profit,
                    "Liquidity": liquidity_status,
                    "Status": data_status,
                    "Prob": probability,
                    "Reasons": ", ".join(reasons)
                })
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), skipped_count

def plot_setup_chart(ticker, entry, stop, target):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo", interval="1d")
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], color='black')
        ax.axhline(entry, color='blue', linestyle='-', label=f'Buy Stop @ {entry:.2f}')
        ax.axhline(stop, color='red', linestyle='--', label='Stop')
        ax.axhline(target, color='green', linestyle='--', label='Target')
        ax.legend()
        ax.set_title(f"{ticker} Setup")
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🦅 AI Sniper - Liquidity Guard")

status, is_pre = get_market_status()
st.info(f"🕒 Status: **{status}**")
if is_pre:
    st.warning("⚠️ Pre-Market: Use BUY STOP orders only.")

if st.button("🚀 SCAN CLEAN STOCKS", type="primary"):
    with st.spinner('Filtering junk stocks & Scanning...'):
        df, skipped = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            
            # מדדים
            valid_setups = df[df['Action'].str.contains("SETUP")]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("💎 Prime Setups", len(valid_setups))
            c2.metric("🗑️ Junk Removed", skipped)
            c3.metric("Avg Prob", f"{df['Prob'].mean():.1f}%")
            
            st.divider()
            
            if not valid_setups.empty:
                for idx, row in valid_setups.iterrows():
                    with st.expander(f"💎 {row['Ticker']} | Buy Stop: ${row['Entry']:.2f}", expanded=True):
                        c_a, c_b = st.columns([1, 2])
                        with c_a:
                            st.markdown(f"**Action:** :green[{row['Action']}]")
                            st.markdown(f"**Current:** ${row['Price']:.2f}")
                            st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                            st.caption(f"Data: {row['Status']}")
                        with c_b:
                            fig = plot_setup_chart(row['Ticker'], row['Entry'], row['Stop'], row['Target'])
                            if fig: st.pyplot(fig)
                            st.write(f"**Why:** {row['Reasons']}")
            else:
                st.info("No high-quality setups found right now (Junk filtered out).")
            
            with st.expander("📊 View Watchlist (Lower Probability)"):
                st.dataframe(df)
        else:
            st.warning(f"No opportunities found. (Filtered {skipped} junk stocks).")
