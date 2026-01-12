import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 14.0 (Trend Master)
# ==========================================
st.set_page_config(page_title="AI Sniper Trends", page_icon="🔥", layout="wide")

# רשימת המניות המורחבת (כולל בקשותיך והמלצות שוק חמות)
TICKERS = [
    # --- הבקשות שלך מהתמונה ---
    'DXCM', 'AKAM', 'ENPH', 'VST', 'ALB', 'ALNY', 'SYF', 'COF',
    
    # --- AI & Tech (הסקטור החם) ---
    'NVDA', 'AMD', 'PLTR', 'SOUN', 'BBAI', 'AI', 'SMCI', 'MU', 'ARM',
    
    # --- Crypto & Blockchain (תנודתיות גבוהה) ---
    'MARA', 'COIN', 'RIOT', 'MSTR', 'CLSK', 'BITF',
    
    # --- High Volatility / Meme ---
    'OPEN', 'SOFI', 'PLUG', 'LCID', 'DKNG', 'CVNA', 'UPST', 'AFRM',
    
    # --- הרשימה המקורית והנקייה ---
    'RKLB', 'GEV', 'INVZ', 'NVO', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'INV', 'SCWO', 'ICON', 'MVO', 'FIEE', 'CD', 'KITT', 'UNTJ', 'RDHL', 'FLXY', 
    'STAI', 'ORGN', 'VIOT', 'BRNF', 'ROMA', 'SOUN', 'ACLS', 
    'RGTI', 'QUBT', 'RGC', 'GLUE', 'IPSC', 'ERAS', 'MNTS', 'LIMN', 'GPUS', 'ABVE', 
    'VTYX', 'TGL', 'AMOD', 'FBLG', 'SLRX', 'COOT', 'RVMD', 'CLIR', 'GHRS', 'NMRA', 
    'MOBX', 'IMRX', 'RZLT', 'OLPX', 'OSS', 'BHVN', 'TNGX', 'MTEN', 'ANPA', 
    'NBY', 'VLN', 'GP', 'ATGL', 'OPAD', 'VCIG', 'THH', 'GGROW', 'ZNTL', 'ELOG', 
    'ZBAO', 'OPTX', 'CGON', 'MLTX', 'TCGL', 'MREO', 'HAO', 'NCRA', 'INBS', 'SOWG', 
    'QTRX', 'SXTC', 'MTAN', 'PASW', 'ACON', 'AQST', 'BBNX', 'PAPL', 'STSS', 'EDHL', 
    'JTAI', 'ATRA', 'MGRX', 'GRI', 'WSHP', 'NVVE', 'DRCT', 'BNZI', 'IZM',
    'EVTV', 'BDSX', 'SUGP', 'UP', 'SOGP', 'OMH', 'BEAM', 'BARK', 
    'LYRA', 'LXEO', 'VMAR', 'TSE', 'SLQT', 'CLRB', 'ZBIO', 'STKL', 'UUU', 
    'AKAN', 'FBRX', 'BIOA', 'HYMC', 'LVLU', 'KC', 'ZH', 'SRL', 'DAWN', 'OM', 
    'RBOT', 'ATEC', 'KUST', 'ANF', 'FLYX', 'STOK', 'GOVX', 'LRHC'
]
# מסירים כפילויות באופן אוטומטי
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
        # ממוצעים
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        
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
            
            # --- סינון ראשוני עדין יותר ---
            try:
                # ננסה למשוך היסטוריה קצרה לבדיקה
                df = stock.history(period="3mo", interval="1d")
                if df.empty or len(df) < 20:
                    skipped_count += 1
                    continue
                
                last_price = df['Close'].iloc[-1]
                if last_price < 0.3: # הורדנו את הרף ל-30 סנט כדי לתפוס יותר מניות
                    skipped_count += 1
                    continue
                    
                info = stock.info
                float_shares = info.get('floatShares', 1000000000)
                if float_shares is None: float_shares = 1000000000
            except:
                skipped_count += 1
                continue

            # --- חישובים ---
            df = calculate_indicators(df)
            last = df.iloc[-1]
            price = last['Close']
            
            # --- סיווג אסטרטגיה (מנוע משופר) ---
            strategy_type = "📅 SWING" # ברירת מחדל
            reasons = []
            
            # זיהוי מסחר יומי (תנודתיות או ווליום חריג)
            vol_ratio = 1.0
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            if avg_vol > 0: vol_ratio = last['Volume'] / avg_vol
            
            # תנאי יום: ווליום כפול או תנודתיות גבוהה
            if vol_ratio > 2.0 or (last['ATR']/price) > 0.03:
                strategy_type = "☀️ DAY TRADE"
                reasons.append(f"Vol x{vol_ratio:.1f}")

            if float_shares < 20_000_000:
                reasons.append("Low Float")
            
            # זיהוי סקטורים חמים (לפי רשימה ידנית)
            hot_sectors = ['NVDA', 'AMD', 'SOUN', 'MARA', 'COIN', 'MSTR', 'PLUG', 'PLTR']
            if ticker in hot_sectors:
                score_boost = 15
                reasons.append("🔥 HOT SECTOR")
            else:
                score_boost = 0

            # --- חישוב יעדים ---
            stop_loss = price - (last['ATR'] * 1.5)
            # יעד מינימום 15-20%
            target = max(price + (last['ATR'] * 4.0), price * 1.15)
            
            potential_pct = ((target - price) / price) * 100

            # --- ניקוד ---
            score = 50 + score_boost
            
            if strategy_type == "☀️ DAY TRADE": score += 10
            if last['Close'] > last['EMA_9']: score += 10 # מומנטום חיובי
            if last['RSI'] < 30: score += 15 # מכירת יתר (הזדמנות)
            elif last['RSI'] > 70: score -= 10 # קניית יתר (מסוכן)
            
            # אנחנו רוצים להציג הכל, אז נשמור גם מניות עם ציון בינוני
            # אבל נסמן אותן כ-WATCH
            action = "WATCH"
            if score >= 75: action = "💎 BUY"
            elif score >= 60: action = "🟢 READY"
            
            results.append({
                "Ticker": ticker,
                "Strategy": strategy_type,
                "Price": price,
                "Action": action,
                "Stop": stop_loss,
                "Target": target,
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
        
        # אזור רווח והפסד
        ax.axhline(stop, color='red', linestyle='--', label='Stop')
        ax.axhline(target, color='green', linestyle='--', label='Target')
        
        ax.set_title(f"{ticker} Analysis")
        ax.legend()
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI - ממשק משתמש
# ==========================================
st.title("🔥 AI Sniper - Trend Master")
status = get_market_status()
st.caption(f"Market Status: {status} | Focus: High Volatility & Hot Sectors")

if st.button("🚀 SCAN HOT TRENDS", type="primary"):
    with st.spinner('Scanning AI, Crypto & Volatile Stocks...'):
        df, skipped = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            
            # חלוקה ללשוניות
            tab1, tab2, tab3 = st.tabs(["⚡ Day Action", "📈 Swing Trends", "📋 Watchlist"])
            
            # לשונית 1: מסחר יומי (אקשן)
            with tab1:
                day_df = df[df['Strategy'] == "☀️ DAY TRADE"]
                if not day_df.empty:
                    # סינון רק למניות חזקות
                    top_day = day_df[day_df['Prob'] > 60]
                    if not top_day.empty:
                        for idx, row in top_day.iterrows():
                            with st.expander(f"{row['Action']} {row['Ticker']} | Est. {row['Potential']}", expanded=True):
                                c1, c2 = st.columns([1, 2])
                                with c1:
                                    st.write(f"Price: ${row['Price']:.2f}")
                                    st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                    st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                                with c2:
                                    st.info(f"Why: {row['Reasons']}")
                                    fig = plot_chart(row['Ticker'], row['Stop'], row['Target'])
                                    if fig: st.pyplot(fig)
                    else:
                        st.warning("Day trades found but low probability. Check Watchlist.")
                else:
                    st.info("No Day Trade setups right now.")

            # לשונית 2: סווינג
            with tab2:
                swing_df = df[df['Strategy'] == "📅 SWING"]
                if not swing_df.empty:
                    top_swing = swing_df[swing_df['Prob'] > 60]
                    for idx, row in top_swing.iterrows():
                        with st.expander(f"{row['Action']} {row['Ticker']} | Est. {row['Potential']}", expanded=False):
                            st.write(f"**Target:** ${row['Target']:.2f} | **Stop:** ${row['Stop']:.2f}")
                            st.caption(row['Reasons'])
                            fig = plot_chart(row['Ticker'], row['Stop'], row['Target'])
                            if fig: st.pyplot(fig)
                else:
                    st.info("No Swing setups.")

            # לשונית 3: הכל (כדי שלא יהיה מסך ריק)
            with tab3:
                st.dataframe(df[['Ticker', 'Price', 'Action', 'Potential', 'Reasons']])
                st.caption(f"Total Scanned: {len(df)} | Skipped (Junk): {skipped}")
            
        else:
            st.error("Connection Error or No Data. Please try again in 1 minute.")
