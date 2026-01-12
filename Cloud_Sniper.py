import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 

# ==========================================
# ⚙️ הגדרות ענן - גרסה 9.0
# ==========================================
st.set_page_config(page_title="AI Sniper Pro", page_icon="🦅", layout="wide")

# רשימת המניות (המעודכנת והנקייה)
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
TICKERS = list(set(TICKERS)) # מחיקת כפילויות

# --- פונקציות ליבה ---

def get_latest_news(stock_obj):
    """ משיכת הכותרת האחרונה של החדשות """
    try:
        news = stock_obj.news
        if news and len(news) > 0:
            return news[0]['title']
        return "No recent news"
    except:
        return "News unavailable"

def calculate_technical_indicators(df):
    """ חישוב כל האינדיקטורים לקוד ולגרף """
    try:
        # EMA (ממוצעים נעים) לגרף
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        # רצועות בולינגר
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['Lower'] = df['SMA_20'] - (df['STD_20'] * 2)
        
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
        
        # ADX (עוצמת מגמה) - חישוב מקוצר
        df['ADX'] = df['TR'].rolling(14).mean() # פישוט לחיסכון בזמן עיבוד
        
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
            time.sleep(0.1) # הגנה מחסימה
            
            stock = yf.Ticker(ticker)
            
            # נתוני בסיס
            try:
                info = stock.info
                float_shares = info.get('floatShares', 1000000000)
                if float_shares is None: float_shares = 1000000000
                short_percent = info.get('shortPercentOfFloat', 0)
                if short_percent is None: short_percent = 0
            except:
                float_shares = 1000000000
                short_percent = 0
            
            # היסטוריה
            df = stock.history(period="6mo", interval="1h")
            if df.empty or len(df) < 60:
                failed_tickers.append(f"{ticker}: No Data")
                continue

            # חישוב אינדיקטורים
            df = calculate_technical_indicators(df)
            if df.empty: continue

            # נתונים אחרונים
            last = df.iloc[-1]
            price = last['Close']
            atr = last['ATR']
            
            # ניהול סיכונים
            stop_loss = price - (atr * 1.5)
            take_profit = price + (atr * 3.0)
            
            # --- ציון והערכה ---
            score = 0
            reasons = []
            
            # 1. מבנה המניה
            if float_shares < 20_000_000:
                score += 20
                reasons.append("🔥 Low Float")
            if short_percent > 0.20:
                score += 15
                reasons.append("🩳 High Short Interest")
                
            # 2. מצב טכני בגרף
            if last['Close'] > last['EMA_9']: # מעל הממוצע המהיר
                score += 15
                reasons.append("📈 Above EMA 9")
            
            if last['EMA_9'] > last['SMA_20']: # מומנטום חיובי
                score += 15
                reasons.append("⚡ Uptrend Cross")
                
            if last['RSI'] < 30: 
                score += 20
                reasons.append("📉 Oversold (RSI < 30)")
            elif last['RSI'] > 70:
                score -= 10 # מסוכן, קניית יתר
            
            # 3. ווליום
            avg_vol = df['Volume'].rolling(50).mean().iloc[-1]
            vol_ratio = 0
            if avg_vol > 0:
                vol_ratio = last['Volume'] / avg_vol
                if vol_ratio > 2:
                    score += 20
                    reasons.append(f"📢 Volume x{vol_ratio:.1f}")

            # סיכום
            probability = max(0, min(100, score))
            action = "WAIT"
            
            if probability >= 80: action = "💎 STRONG BUY"
            elif probability >= 65: action = "🟢 BUY"
            elif probability <= 20: action = "🔴 SELL"
            
            # סינון שוק מת
            if last['Volume'] < 1000:
                action = "💤 SLEEPING"
                probability = 0
            
            # משיכת חדשות (רק למניות רלוונטיות כדי לחסוך זמן)
            news_headline = "No recent news"
            if probability > 50: 
                news_headline = get_latest_news(stock)

            results.append({
                "Ticker": ticker,
                "Price": price,
                "Action": action,
                "Prob": probability,
                "Stop_Loss": stop_loss,
                "Take_Profit": take_profit,
                "Float(M)": float_shares / 1_000_000,
                "RSI": round(last['RSI'], 1),
                "Vol_Ratio": round(vol_ratio, 1),
                "News": news_headline,
                "Reasons": ", ".join(reasons)
            })
            
        except Exception as e:
            failed_tickers.append(f"{ticker}: Error")
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), failed_tickers

def plot_advanced_chart(ticker, stop_loss, take_profit):
    """ יצירת גרף מתקדם עם ממוצעים """
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="3mo", interval="1d")
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # מחיר
        ax.plot(df.index, df['Close'], label='Price', color='black', linewidth=1.5)
        
        # ממוצעים (האינדיקטורים שביקשת)
        ax.plot(df.index, df['EMA_9'], label='EMA 9 (Fast)', color='#007bff', alpha=0.8, linewidth=1)
        ax.plot(df.index, df['SMA_20'], label='SMA 20 (Trend)', color='#ff7f0e', alpha=0.8, linewidth=1)
        
        # קווי מסחר
        ax.axhline(stop_loss, color='red', linestyle='--', label='Stop Loss')
        ax.axhline(take_profit, color='green', linestyle='--', label='Target')
        
        ax.set_title(f"{ticker} Analysis | Blue cross Orange = BUY Signal")
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.2)
        
        return fig
    except:
        return None

# ==========================================
# 🖥️ ממשק משתמש (UI)
# ==========================================
st.title("🦅 AI Sniper - Full Vision")
st.caption("Live Data | Advanced Charts | News Analysis")

if st.button("🚀 START SCAN (With News & Charts)", type="primary"):
    with st.spinner('Scanning Market & Reading News...'):
        df, failed_list = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Prob', ascending=False)
            active = df[df['Action'] != "💤 SLEEPING"]
            
            # מדדים למעלה
            c1, c2, c3 = st.columns(3)
            c1.metric("Opportunities", len(active[active['Action'].str.contains("BUY")]))
            c2.metric("Low Float Gems", len(df[df['Float(M)'] < 20]))
            c3.metric("Avg Probability", f"{active['Prob'].mean():.1f}%")
            
            st.divider()
            
            # תצוגה ראשית - קלפים של מניות
            st.subheader("📋 Top Opportunities")
            
            buy_signals = df[df['Action'].str.contains("BUY")]
            
            if not buy_signals.empty:
                for idx, row in buy_signals.iterrows():
                    # צבע הכותרת לפי החוזק
                    icon = "💎" if "STRONG" in row['Action'] else "🟢"
                    
                    with st.expander(f"{icon} {row['Ticker']} | Prob: {row['Prob']:.0f}% | Price: ${row['Price']:.2f}", expanded=True):
                        
                        # עמודות מידע
                        col1, col2 = st.columns([1, 2])
                        
                        with col1:
                            st.markdown(f"**Action:** :green[{row['Action']}]")
                            st.markdown(f"**Stop:** :red[${row['Stop_Loss']:.2f}]")
                            st.markdown(f"**Target:** :green[${row['Take_Profit']:.2f}]")
                            st.divider()
                            st.markdown("**Technical Data:**")
                            st.text(f"RSI: {row['RSI']}")
                            st.text(f"Vol Ratio: x{row['Vol_Ratio']}")
                            st.text(f"Float: {row['Float(M)']}M")
                        
                        with col2:
                            # חדשות
                            st.info(f"📰 **Latest News:** {row['News']}")
                            
                            # גרף
                            fig = plot_advanced_chart(row['Ticker'], row['Stop_Loss'], row['Take_Profit'])
                            if fig:
                                st.pyplot(fig)
                                plt.close(fig)
                            
                            # סיבות
                            st.caption(f"**Why to buy?** {row['Reasons']}")
            else:
                st.warning("No clear buy signals found right now.")
                
            # טבלה מלאה למי שרוצה
            with st.expander("📊 View All Data (Table)"):
                st.dataframe(df)
                
            # כשלונות
            if failed_list:
                with st.expander("⚠️ Skipped Tickers"):
                    st.write(failed_list)
                
        else:
            st.error("No data found.")
