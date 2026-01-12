import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 10.0 (Pre-Market Breakout)
# ==========================================
st.set_page_config(page_title="AI Sniper X", page_icon="🦅", layout="wide")

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
    """ בדיקה האם השוק פתוח או בפרה-מרקט """
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    
    # שעות מסחר בניו יורק
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_ny.replace(hour=16, minute=0, second=0, microsecond=0)
    
    if now_ny < market_open:
        return "🌅 PRE-MARKET", True
    elif now_ny > market_close:
        return "🌙 AFTER-HOURS", False
    else:
        return "☀️ MARKET OPEN", False

def check_data_delay(stock_df):
    try:
        last_time = stock_df.index[-1]
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        time_diff = now_ny - last_time
        # אם עברו יותר מ-25 דקות
        if time_diff.total_seconds() > 1500: 
            return "🔴 DELAYED"
        return "🟢 LIVE"
    except:
        return "❓ Unknown"

def calculate_indicators(df):
    try:
        # EMA & SMA
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # ATR
        df['TR'] = np.maximum((df['High'] - df['Low']), 
                   np.maximum(abs(df['High'] - df['Close'].shift(1)), 
                   abs(df['Low'] - df['Close'].shift(1))))
        df['ATR'] = df['TR'].rolling(14).mean()
        
        return df
    except:
        return pd.DataFrame()

def scan_market():
    results = []
    failed_tickers = [] 
    
    market_phase, is_premarket = get_market_status()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            time.sleep(0.05) 
            
            stock = yf.Ticker(ticker)
            
            # בדיקת נתונים
            try:
                info = stock.info
                float_shares = info.get('floatShares', 1000000000)
                if float_shares is None: float_shares = 1000000000
            except:
                float_shares = 1000000000
            
            # משיכת היסטוריה - טריק לפרה-מרקט
            # אנחנו מושכים נתונים תוך יומיים כדי לראות את הפעילות האחרונה
            df = stock.history(period="5d", interval="30m")
            
            if df.empty:
                failed_tickers.append(f"{ticker}: No Data")
                continue

            # בדיקת טריות
            data_status = check_data_delay(df)
            
            # חישוב אינדיקטורים
            df = calculate_indicators(df)
            if df.empty or len(df) < 20: continue

            last = df.iloc[-1]
            price = last['Close']
            atr = last['ATR']
            
            # --- חישוב אסטרטגיה חכם ---
            
            # 1. חישוב מחיר כניסה (פריצה)
            # אם אנחנו בפרה-מרקט, הכניסה היא מעל הגבוה של היום
            # אם במסחר רגיל, הכניסה היא מעל הגבוה של הנר האחרון + קצת מרווח
            entry_price = last['High'] + (atr * 0.5) 
            
            stop_loss = entry_price - (atr * 2.0)
            take_profit = entry_price + (atr * 4.0)
            
            score = 0
            reasons = []
            
            # פילטרים
            if float_shares < 20_000_000:
                score += 25
                reasons.append("🔥 Low Float")
            
            if last['Close'] > last['EMA_9']:
                score += 15
                reasons.append("📈 Trend UP")
                
            if last['RSI'] < 35: 
                score += 20
                reasons.append("📉 Oversold Dip")
            elif last['RSI'] > 50 and last['RSI'] < 70:
                score += 10
                reasons.append("⚡ Momentum")

            # בדיקת ווליום יחסי
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if avg_vol > 0 and last['Volume'] > avg_vol * 1.5:
                score += 25
                reasons.append("📢 High Volume")

            probability = max(0, min(100, score))
            action = "WAIT"
            
            if probability >= 80: action = "💎 SETUP READY"
            elif probability >= 65: action = "🟢 WATCH"
            elif probability <= 20: action = "🔴 AVOID"
            
            # הגנה: אם אין ווליום בכלל
            if last['Volume'] < 500:
                action = "💤 SLEEPING"
                probability = 0
            
            results.append({
                "Ticker": ticker,
                "Price": price,
                "Entry_Order": entry_price, # המחיר שבו שמים את הפקודה
                "Action": action,
                "Prob": probability,
                "Stop_Loss": stop_loss,
                "Take_Profit": take_profit,
                "Float(M)": float_shares / 1_000_000,
                "Status": data_status,
                "Reasons": ", ".join(reasons)
            })
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), market_phase

def plot_setup_chart(ticker, entry, stop, target):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo", interval="1d")
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df['Close'], label='Price', color='black')
        
        # ציור קו פקודת הכניסה
        ax.axhline(entry, color='blue', linestyle='-', linewidth=2, label=f'BUY STOP ORDER @ {entry:.2f}')
        ax.axhline(stop, color='red', linestyle='--', label='Stop Loss')
        ax.axhline(target, color='green', linestyle='--', label='Target')
        
        ax.set_title(f"{ticker} Trade Setup")
        ax.legend()
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ ממשק משתמש
# ==========================================
st.title("🦅 AI Sniper X - Breakout Edition")

# הצגת מצב השוק
status, is_pre = get_market_status()
st.info(f"🕒 Market Status: **{status}**")
if is_pre:
    st.warning("⚠️ PRE-MARKET STRATEGY: Do not buy at 'Market'. Use 'BUY STOP' orders at the Entry Price shown below.")

if st.button("🚀 SCAN FOR SETUPS", type="primary"):
    with st.spinner('Calculating Breakout Levels...'):
        df, phase = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            active = df[df['Action'] != "💤 SLEEPING"]
            
            # מדדים
            c1, c2, c3 = st.columns(3)
            c1.metric("Valid Setups", len(active[active['Action'].str.contains("SETUP")]))
            c2.metric("Real-Time Data", len(df[df['Status'].str.contains("LIVE")]))
            c3.metric("Low Float", len(df[df['Float(M)'] < 20]))
            
            st.divider()
            
            # הצגת תוצאות
            setups = df[df['Action'].str.contains("SETUP|WATCH")]
            
            if not setups.empty:
                for idx, row in setups.iterrows():
                    icon = "💎" if "SETUP" in row['Action'] else "👀"
                    
                    with st.expander(f"{icon} {row['Ticker']} | Order Price: ${row['Entry_Order']:.2f}", expanded=True):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.markdown(f"**Current Price:** ${row['Price']:.2f}")
                            st.markdown(f"**🛑 SET BUY STOP @:** :blue[**${row['Entry_Order']:.2f}**]")
                            st.markdown(f"**Stop Loss:** :red[${row['Stop_Loss']:.2f}]")
                            st.markdown(f"**Target:** :green[${row['Take_Profit']:.2f}]")
                            st.caption(f"Data: {row['Status']}")
                        
                        with col2:
                            fig = plot_setup_chart(row['Ticker'], row['Entry_Order'], row['Stop_Loss'], row['Take_Profit'])
                            if fig:
                                st.pyplot(fig)
                                plt.close(fig)
                            st.write(f"**Logic:** {row['Reasons']}")
            else:
                st.info("No breakouts detected yet. Market might be quiet.")
                
            with st.expander("📊 Full Data Table"):
                st.dataframe(df)
        else:
            st.error("No data found.")
