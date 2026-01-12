import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import time 
from datetime import datetime
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 15.0 (Wall St. Edition)
# ==========================================
st.set_page_config(page_title="AI Sniper Pro", page_icon="🏛️", layout="wide")

# רשימת המניות (כולל הסקטורים החמים והבקשות שלך)
TICKERS = [
    'DXCM', 'AKAM', 'ENPH', 'VST', 'ALB', 'ALNY', 'SYF', 'COF',
    'NVDA', 'AMD', 'PLTR', 'SOUN', 'BBAI', 'AI', 'SMCI', 'MU', 'ARM',
    'MARA', 'COIN', 'RIOT', 'MSTR', 'CLSK', 'BITF',
    'OPEN', 'SOFI', 'PLUG', 'LCID', 'DKNG', 'CVNA', 'UPST', 'AFRM',
    'RKLB', 'GEV', 'INVZ', 'NVO', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'INV', 'SCWO', 'ICON', 'MVO', 'FIEE', 'CD', 'KITT', 'UNTJ', 'RDHL', 'FLXY', 
    'STAI', 'ORGN', 'VIOT', 'BRNF', 'ROMA', 'ACLS', 
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
TICKERS = list(set(TICKERS))

# --- פונקציות ליבה מקצועיות ---

def get_market_status():
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    if now_ny < market_open: return "🌅 PRE-MARKET"
    return "☀️ MARKET OPEN"

def calculate_vwap(df):
    """ חישוב VWAP - המדד של המוסדיים """
    v = df['Volume'].values
    p = df['Close'].values
    # חישוב מצטבר של מחיר כפול ווליום, חלקי ווליום מצטבר
    return df.assign(VWAP=(p * v).cumsum() / v.cumsum())

def identify_patterns(df):
    """ זיהוי תבניות נרות יפניים (Price Action) """
    # נר פטיש (Hammer) - היפוך למעלה
    # גוף קטן, צללית תחתונה ארוכה
    df['Body'] = abs(df['Close'] - df['Open'])
    df['Lower_Wick'] = df[['Open', 'Close']].min(axis=1) - df['Low']
    df['Upper_Wick'] = df['High'] - df[['Open', 'Close']].max(axis=1)
    
    # תנאי לפטיש: צללית תחתונה גדולה פי 2 מהגוף, צללית עליונה קטנה
    df['Hammer'] = (df['Lower_Wick'] > 2 * df['Body']) & (df['Upper_Wick'] < df['Body'])
    
    # נר עוטף/בליעה (Bullish Engulfing) - קונים משתלטים
    # הנר הקודם אדום, הנר הנוכחי ירוק ועוטף את הקודם
    df['Prev_Open'] = df['Open'].shift(1)
    df['Prev_Close'] = df['Close'].shift(1)
    df['Bullish_Engulfing'] = (df['Open'] < df['Prev_Close']) & (df['Close'] > df['Prev_Open']) & (df['Close'] > df['Open']) & (df['Prev_Open'] > df['Prev_Close'])
    
    return df

def calculate_advanced_indicators(df):
    try:
        # VWAP
        df = calculate_vwap(df)
        
        # תבניות נרות
        df = identify_patterns(df)
        
        # ממוצעים נעים
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        
        # זיהוי פריצה (Breakout): הגבוה של 20 הימים האחרונים
        df['20_Day_High'] = df['High'].rolling(window=20).max()
        
        # RSI & ATR
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
            
            # בדיקת נתונים
            try:
                df = stock.history(period="6mo", interval="1d")
                if df.empty or len(df) < 50:
                    skipped_count += 1
                    continue
                
                # סינון בסיסי
                if df['Close'].iloc[-1] < 0.5:
                    skipped_count += 1
                    continue
                    
                info = stock.info
                float_shares = info.get('floatShares', 1000000000)
            except:
                skipped_count += 1
                continue

            # --- הפעלת המנוע המתקדם ---
            df = calculate_advanced_indicators(df)
            last = df.iloc[-1]
            prev = df.iloc[-2]
            price = last['Close']
            
            # --- ועדת ההשקעות (The Investment Committee) ---
            score = 0
            reasons = []
            setup_type = "None"
            
            # 1. מבחן ה-VWAP (האם אנחנו בצד הנכון של הכסף?)
            # אם המחיר מעל ה-VWAP, הקונים שולטים
            if price > last['VWAP']:
                score += 20
                reasons.append("Above VWAP (Institutions Bullish)")
            
            # 2. מבחן הפריצה (Breakout)
            # האם שברנו את השיא של החודש האחרון?
            if price >= last['20_Day_High'] * 0.98: # קרוב מאוד לפריצה או פורץ
                score += 25
                reasons.append("🚨 20-Day Breakout")
                setup_type = "BREAKOUT"
            
            # 3. מבחן ה-Price Action (נרות)
            if last['Hammer']:
                score += 15
                reasons.append("🕯️ Hammer Candle")
            if last['Bullish_Engulfing']:
                score += 15
                reasons.append("🕯️ Engulfing Candle")
                
            # 4. מבחן המגמה הגדולה (Trend Alignment)
            if price > last['SMA_50'] and last['SMA_50'] > last['SMA_200']:
                score += 15
                reasons.append("Golden Trend")
            
            # 5. ווליום חריג (Smart Money Footprint)
            avg_vol = df['Volume'].rolling(20).mean().iloc[-1]
            vol_ratio = last['Volume'] / avg_vol
            if vol_ratio > 1.5:
                score += 15
                reasons.append(f"Big Volume (x{vol_ratio:.1f})")

            # --- החלטה סופית ---
            
            # מניות Low Float מקבלות יחס מיוחד למסחר יומי
            if float_shares < 20000000 and vol_ratio > 2.0:
                 setup_type = "MOMENTUM"
                 score += 10

            action = "WATCH"
            if score >= 80: action = "💎 STRONG BUY"
            elif score >= 60: action = "🟢 BUY"
            
            # חישוב יעדים מתקדם
            stop_loss = price - (last['ATR'] * 1.5)
            # אם יש פריצה, היעד הוא רחוק יותר
            target_mult = 5.0 if setup_type == "BREAKOUT" else 3.0
            target = price + (last['ATR'] * target_mult)
            potential = ((target - price) / price) * 100
            
            # רק אם יש לפחות סיבה טובה אחת
            if score >= 50:
                results.append({
                    "Ticker": ticker,
                    "Type": setup_type if setup_type != "None" else "TREND",
                    "Price": price,
                    "Action": action,
                    "Stop": stop_loss,
                    "Target": target,
                    "Potential": f"+{potential:.1f}%",
                    "Score": score,
                    "Reasons": ", ".join(reasons)
                })
            else:
                skipped_count += 1
            
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), skipped_count

def plot_pro_chart(ticker, stop, target):
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="6mo", interval="1d")
        df = calculate_vwap(df) # חישוב לצורך הגרף
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # מחיר
        ax.plot(df.index, df['Close'], color='black', linewidth=1.5, label='Price')
        
        # VWAP - קו סגול (מוסדיים)
        ax.plot(df.index, df['VWAP'], color='purple', linestyle='-', alpha=0.6, linewidth=1, label='VWAP (Inst. Level)')
        
        # אזורי מסחר
        ax.axhline(stop, color='red', linestyle='--', label='Stop Loss')
        ax.axhline(target, color='green', linestyle='--', label='Target')
        
        ax.set_title(f"{ticker} Professional Analysis")
        ax.legend()
        ax.grid(True, alpha=0.2)
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI - ממשק מקצועי
# ==========================================
st.title("🏛️ AI Sniper - Wall St. Edition")
st.caption("Criteria: VWAP, Price Action, Breakouts, Smart Money Volume")

status = get_market_status()
st.info(f"Market Status: {status}")

if st.button("🚀 RUN INSTITUTIONAL SCAN", type="primary"):
    with st.spinner('Analyzing Price Action & Institutional Levels...'):
        df, skipped = scan_market()
        
        if not df.empty:
            df = df.sort_values(by='Score', ascending=False)
            
            # חלוקה לקטגוריות מסחר
            tab1, tab2, tab3 = st.tabs(["💎 Top Picks", "🚨 Breakouts", "🌊 Momentum"])
            
            # 1. Top Picks (הכי בטוחות)
            with tab1:
                top = df[df['Score'] >= 75]
                if not top.empty:
                    for idx, row in top.iterrows():
                        with st.expander(f"💎 {row['Ticker']} | Score: {row['Score']} | {row['Potential']}", expanded=True):
                            c1, c2 = st.columns([1, 2])
                            with c1:
                                st.markdown(f"**Price:** ${row['Price']:.2f}")
                                st.markdown(f"**Target:** :green[${row['Target']:.2f}]")
                                st.markdown(f"**Stop:** :red[${row['Stop']:.2f}]")
                            with c2:
                                st.success(f"**Thesis:** {row['Reasons']}")
                                fig = plot_pro_chart(row['Ticker'], row['Stop'], row['Target'])
                                if fig: st.pyplot(fig)
                else:
                    st.info("No 'Strong Buy' candidates meeting institutional criteria.")

            # 2. Breakouts (פריצות)
            with tab2:
                breakouts = df[df['Type'] == "BREAKOUT"]
                if not breakouts.empty:
                    st.dataframe(breakouts[['Ticker', 'Price', 'Potential', 'Reasons']])
                else:
                    st.info("No stocks breaking 20-day highs right now.")
            
            # 3. Momentum (למסחר יומי מהיר)
            with tab3:
                mom = df[df['Type'] == "MOMENTUM"]
                if not mom.empty:
                    st.dataframe(mom[['Ticker', 'Price', 'Potential', 'Reasons']])
                else:
                    st.info("No high-volume momentum stocks found.")
                    
            st.divider()
            st.caption(f"Filtered out {skipped} stocks that didn't meet professional standards.")
            
        else:
            st.error("No stocks met the strict professional criteria.")
