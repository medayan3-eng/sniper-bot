import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import pytz

# ==========================================
# ⚙️ הגדרות ענן
# ==========================================
st.set_page_config(page_title="AI Sniper Cloud", page_icon="☁️", layout="wide")

# רשימת המניות
TICKERS = [
    'PLTR', 'RKLB', 'GEV', 'INVZ', 'NVO', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'INV', 'SCWO', 'ICON', 'MVO', 'FIEE', 'CD', 'KITT', 'UNTJ', 'RDHL', 'FLXY', 
    'STAI', 'ORGN', 'VIOT', 'BRNF', 'ROMA', 'OPEN', 'MU', 'SOUN', 'BBAI', 'ACLS', 
    'RGTI', 'QUBT', 'RGC', 'GLUE', 'IPSC', 'ERAS', 'MNTS', 'LIMN', 'GPUS', 'ABVE', 
    'VTYX', 'TGL', 'AMOD', 'FBLG', 'SLRX', 'COOT', 'RVMD', 'CLIR', 'GHRS', 'NMRA', 
    'MOBX', 'IMRX', 'RZLT', 'OLPX', 'OSS', 'BHVN', 'TNGX', 'MTEN', 'ANPA', 'ZJZZT', 
    'NBY', 'VLN', 'GP', 'ATGL', 'OPAD', 'VCIG', 'THH', 'GGROW', 'ZNTL', 'ELOG', 
    'ZBAO', 'OPTX', 'CGON', 'MLTX', 'TCGL', 'MREO', 'HAO', 'NCRA', 'INBS', 'SOWG', 
    'QTRX', 'SXTC', 'MTAN', 'PASW', 'ACON', 'AQST', 'BBNX', 'PAPL', 'STSS', 'EDHL', 
    'JTAI', 'ATRA', 'MGRX', 'GRI', 'WSHP', 'NVVE', 'DRCT', 'BNZI', 'IZM'
]

# פונקציות עזר
def calculate_adx(df, n=14):
    try:
        df['H-L'] = df['High'] - df['Low']
        df['H-PC'] = abs(df['High'] - df['Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
        df['ATR'] = df['TR'].rolling(n).mean()
        df['UpMove'] = df['High'] - df['High'].shift(1)
        df['DownMove'] = df['Low'].shift(1) - df['Low']
        df['+DM'] = np.where((df['UpMove'] > df['DownMove']) & (df['UpMove'] > 0), df['UpMove'], 0)
        df['-DM'] = np.where((df['DownMove'] > df['UpMove']) & (df['DownMove'] > 0), df['DownMove'], 0)
        df['+DI'] = 100 * (df['+DM'].rolling(n).mean() / df['ATR'])
        df['-DI'] = 100 * (df['-DM'].rolling(n).mean() / df['ATR'])
        df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])
        df['ADX'] = df['DX'].rolling(n).mean()
        return df['ADX'], df['ATR']
    except:
        return pd.Series([0]*len(df)), pd.Series([0]*len(df))

def scan_market():
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total = len(TICKERS)
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            info = stock.info
            float_shares = info.get('floatShares', 1000000000)
            if float_shares is None: float_shares = 1000000000
            
            short_percent = info.get('shortPercentOfFloat', 0)
            if short_percent is None: short_percent = 0
            
            df = stock.history(period="6mo", interval="1h")
            if df.empty or len(df) < 60: continue

            df['ADX'], df['ATR'] = calculate_adx(df)
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
            df['STD_20'] = df['Close'].rolling(window=20).std()
            df['Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
            df['Lower'] = df['SMA_20'] - (df['STD_20'] * 2)
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            last = df.iloc[-1]
            price = last['Close']
            atr = last['ATR']
            adx = last['ADX']
            
            stop_loss = price - (atr * 1.5)
            take_profit = price + (atr * 3.0)
            
            score = 0
            reasons = []
            
            if float_shares < 20_000_000:
                score += 25
                reasons.append("🔥 Low Float")
            if short_percent > 0.20:
                score += 25
                reasons.append("🩳 High Short Interest")
            if adx > 25: score += 15
            else: score -= 10
            if last['RSI'] < 30: 
                score += 20
                reasons.append("Oversold")
            if price <= last['Lower'] * 1.02:
                score += 15
                reasons.append("Bollinger Bottom")
            
            avg_vol = df['Volume'].rolling(50).mean().iloc[-1]
            if avg_vol > 0 and last['Volume'] > avg_vol * 2:
                score += 20
                reasons.append("Volume Explosion")

            probability = max(0, min(100, score))
            action = "WAIT"
            
            if probability >= 80: action = "💎 STRONG BUY"
            elif probability >= 65: action = "🟢 BUY"
            elif probability <= 20: action = "🔴 SELL"
            
            if last['Volume'] < 1000:
                action = "💤 SLEEPING"
                probability = 0

            results.append({
                "Ticker": ticker,
                "Price": price,
                "Action": action,
                "Prob": probability,
                "Stop_Loss": stop_loss,
                "Take_Profit": take_profit,
                "Float(M)": float_shares / 1_000_000,
                "Short%": short_percent * 100,
                "Reasons": ", ".join(reasons)
            })
            
        except Exception:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results)

def plot_chart(ticker, stop_loss, take_profit):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d") # גרף יומי ברור יותר
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], label='Price', color='black')
        
        # קווי מסחר
        ax.axhline(stop_loss, color='red', linestyle='--', label=f'Stop: {stop_loss:.2f}')
        ax.axhline(take_profit, color='green', linestyle='--', label=f'Target: {take_profit:.2f}')
        
        ax.set_title(f"{ticker} Analysis")
        ax.legend()
        ax.grid(True, alpha=0.3)
        return fig
    except:
        return None

# ==========================================
# 🖥️ ממשק משתמש (UI)
# ==========================================
st.title("☁️ AI Sniper Cloud Edition")

if st.button("🚀 START SCAN NOW", type="primary"):
    with st.spinner('Analyzing Market Data...'):
        df = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            
            # 1. סטטיסטיקות
            active = df[df['Action'] != "💤 SLEEPING"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Scanned", len(df))
            c2.metric("💎 Opportunities", len(active[active['Action'].str.contains("BUY")]))
            c3.metric("🔥 Low Float", len(df[df['Float(M)'] < 20]))
            c4.metric("Avg Prob", f"{active['Prob'].mean():.1f}%")
            
            st.divider()
            
            # 2. טבלה
            st.subheader("📊 Live Results")
            def highlight_rows(val):
                if 'STRONG' in str(val): return 'background-color: #28a745; color: white'
                if 'BUY' in str(val): return 'background-color: #d4edda; color: green'
                if 'SELL' in str(val): return 'background-color: #f8d7da; color: red'
                return ''

            st.dataframe(
                df.style.map(highlight_rows, subset=['Action'])
                .format({"Price": "{:.2f}", "Stop_Loss": "{:.2f}", "Take_Profit": "{:.2f}", "Float(M)": "{:.1f}M", "Short%": "{:.1f}%", "Prob": "{:.0f}%"}),
                use_container_width=True
            )
            
            # 3. גרפים (החלק החדש!)
            st.divider()
            st.subheader("📸 Top Charts (Buy Signals)")
            
            buy_signals = df[df['Action'].str.contains("BUY")]
            
            if not buy_signals.empty:
                for idx, row in buy_signals.iterrows():
                    with st.expander(f"Show Chart: {row['Ticker']} ({row['Action']})", expanded=True):
                        fig = plot_chart(row['Ticker'], row['Stop_Loss'], row['Take_Profit'])
                        if fig:
                            st.pyplot(fig)
                            plt.close(fig)
                        st.write(f"**Reasons:** {row['Reasons']}")
            else:
                st.info("No charts to display (No Buy signals found).")
                
        else:
            st.error("No data found.")
