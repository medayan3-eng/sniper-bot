import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 9.1 (גלאי האמת)
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

def check_data_delay(stock_df):
    """ בדיקה האם המידע מעודכן או באיחור """
    try:
        last_time = stock_df.index[-1]
        # המרה לאזור זמן ניו יורק
        ny_tz = pytz.timezone('America/New_York')
        now_ny = datetime.now(ny_tz)
        
        # אם יש הפרש של יותר מ-20 דקות
        time_diff = now_ny - last_time
        if time_diff.total_seconds() > 1200: # 20 דקות
            return "🔴 DELAYED", f"{int(time_diff.total_seconds()/60)}m ago"
        else:
            return "🟢 Real-Time", "Live"
    except:
        return "❓ Unknown", ""

def get_latest_news(stock_obj):
    try:
        news = stock_obj.news
        if news and len(news) > 0:
            return news[0]['title']
        return "No recent news"
    except:
        return "News unavailable"

def calculate_technical_indicators(df):
    try:
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['Lower'] = df['SMA_20'] - (df['STD_20'] * 2)
        
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
    failed_tickers = [] 
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            time.sleep(0.05) 
            
            stock = yf.Ticker(ticker)
            
            # בדיקת נתונים בסיסית
            try:
                info = stock.info
                float_shares = info.get('floatShares', 1000000000)
                short_percent = info.get('shortPercentOfFloat', 0)
            except:
                float_shares = 1000000000
                short_percent = 0
            
            if float_shares is None: float_shares = 1000000000
            
            # משיכת היסטוריה
            df = stock.history(period="5d", interval="1h") # לקחנו 5 ימים אחרונים שעתיים
            
            if df.empty:
                failed_tickers.append(f"{ticker}: No Data")
                continue

            # --- בדיקת האמת (עיכוב) ---
            data_status, delay_time = check_data_delay(df)

            # חישובים
            df = calculate_technical_indicators(df)
            if df.empty or len(df) < 20: continue

            last = df.iloc[-1]
            price = last['Close']
            atr = last['ATR']
            
            stop_loss = price - (atr * 1.5)
            take_profit = price + (atr * 3.0)
            
            score = 0
            reasons = []
            
            # לוגיקה
            if float_shares < 20_000_000:
                score += 20
                reasons.append("🔥 Low Float")
            if short_percent > 0.20:
                score += 15
                reasons.append("🩳 High Short")
                
            if last['Close'] > last['EMA_9']:
                score += 15
                reasons.append("📈 Above EMA 9")
            
            if last['EMA_9'] > last['SMA_20']:
                score += 15
                reasons.append("⚡ Uptrend")
                
            if last['RSI'] < 30: 
                score += 20
                reasons.append("📉 Oversold")
            
            # ווליום
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            vol_ratio = 0
            if avg_vol > 0:
                vol_ratio = last['Volume'] / avg_vol
                if vol_ratio > 2:
                    score += 20
                    reasons.append(f"📢 Vol x{vol_ratio:.1f}")

            probability = max(0, min(100, score))
            action = "WAIT"
            
            if probability >= 80: action = "💎 STRONG BUY"
            elif probability >= 65: action = "🟢 BUY"
            elif probability <= 20: action = "🔴 SELL"
            
            if last['Volume'] < 500: # ווליום ממש נמוך
                action = "💤 SLEEPING"
                probability = 0
            
            # אם המידע באיחור, מורידים ציון אמינות
            if "DELAYED" in data_status:
                reasons.append("⚠️ Delayed Data")

            news_headline = "No recent news"
            if probability > 50: 
                news_headline = get_latest_news(stock)

            results.append({
                "Ticker": ticker,
                "Price": price,
                "Data_Status": f"{data_status} ({delay_time})",
                "Action": action,
                "Prob": probability,
                "Stop_Loss": stop_loss,
                "Take_Profit": take_profit,
                "Float(M)": float_shares / 1_000_000,
                "RSI": round(last['RSI'], 1),
                "News": news_headline,
                "Reasons": ", ".join(reasons)
            })
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), failed_tickers

def plot_advanced_chart(ticker, stop_loss, take_profit):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d")
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(df.index, df['Close'], label='Price', color='black')
        ax.plot(df.index, df['EMA_9'], label='EMA 9', color='#007bff', alpha=0.8)
        ax.plot(df.index, df['SMA_20'], label='SMA 20', color='#ff7f0e', alpha=0.8)
        ax.axhline(stop_loss, color='red', linestyle='--', label='Stop')
        ax.axhline(take_profit, color='green', linestyle='--', label='Target')
        ax.set_title(f"{ticker} Analysis")
        ax.legend()
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ ממשק משתמש
# ==========================================
st.title("🦅 AI Sniper - Truth Edition")
st.info("💡 Pro Tip: Don't day-trade delayed data. Use this for Swing & Trends.")

if st.button("🚀 START SCAN", type="primary"):
    with st.spinner('Checking Data Freshness & Scanning...'):
        df, failed_list = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            active = df[df['Action'] != "💤 SLEEPING"]
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Opportunities", len(active[active['Action'].str.contains("BUY")]))
            c2.metric("Real-Time Tickers", len(df[df['Data_Status'].str.contains("Real")]))
            c3.metric("Avg Prob", f"{active['Prob'].mean():.1f}%")
            
            st.divider()
            
            buy_signals = df[df['Action'].str.contains("BUY")]
            
            if not buy_signals.empty:
                for idx, row in buy_signals.iterrows():
                    icon = "💎" if "STRONG" in row['Action'] else "🟢"
                    # בדיקת אזהרה אם המידע לא בזמן אמת
                    status_color = "green" if "Real" in row['Data_Status'] else "red"
                    
                    with st.expander(f"{icon} {row['Ticker']} | {row['Data_Status']}", expanded=True):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.markdown(f"**Action:** :green[{row['Action']}]")
                            st.markdown(f"**Price:** ${row['Price']:.2f}")
                            st.markdown(f"**Stop:** :red[${row['Stop_Loss']:.2f}]")
                            st.markdown(f"**Target:** :green[${row['Take_Profit']:.2f}]")
                            if "DELAYED" in row['Data_Status']:
                                st.error("⚠️ DATA IS DELAYED! DO NOT SCALP.")
                        with col2:
                            st.info(f"📰 {row['News']}")
                            fig = plot_advanced_chart(row['Ticker'], row['Stop_Loss'], row['Take_Profit'])
                            if fig:
                                st.pyplot(fig)
                                plt.close(fig)
                            st.caption(f"Reasoning: {row['Reasons']}")
            else:
                st.warning("No safe setups found.")
                
            with st.expander("📊 Full Data Table"):
                st.dataframe(df)
        else:
            st.error("No data found.")
