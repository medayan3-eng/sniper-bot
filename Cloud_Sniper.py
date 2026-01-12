import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 17.0 (Pre-Market Commander)
# ==========================================
st.set_page_config(page_title="Pre-Market Commander", page_icon="🌅", layout="wide")

# רשימת המניות (כולל הכל)
TICKERS = [
    'NVDA', 'AMD', 'PLTR', 'SOUN', 'BBAI', 'AI', 'SMCI', 'MU', 'ARM', 'TSM',
    'MARA', 'COIN', 'RIOT', 'MSTR', 'CLSK', 'BITF', 'HUT', 'CIFR',
    'OPEN', 'SOFI', 'PLUG', 'LCID', 'DKNG', 'CVNA', 'UPST', 'AFRM', 'GME', 'AMC',
    'DXCM', 'AKAM', 'ENPH', 'VST', 'ALB', 'ALNY', 'SYF', 'COF',
    'RKLB', 'GEV', 'INVZ', 'SMX', 'COHN', 'ASTI', 'NXTT', 'BNAI', 
    'SCWO', 'MVO', 'CD', 'KITT', 'RDHL', 'FLXY', 'OSS', 'BHVN',
    'RGTI', 'QUBT', 'RGC', 'GLUE', 'MREO', 'BDSX', 'EVTV', 'SUGP',
    'SLQT', 'CLRB', 'ZBIO', 'STKL', 'UUU', 'AKAN', 'FBRX', 'BIOA', 'HYMC',
    'LVLU', 'KC', 'ZH', 'SRL', 'DAWN', 'OM', 'RBOT', 'ATEC', 'KUST', 'ANF', 'FLYX'
]
TICKERS = list(set(TICKERS))

# --- פונקציות ליבה ---

def get_data_status():
    """ בדיקת זמן אמת """
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    
    if now_ny < market_open:
        return "🌅 PRE-MARKET (16:00-16:30 IL)", True
    return "☀️ MARKET OPEN", False

def scan_market():
    results = []
    skipped_count = 0
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    market_status, is_pre_market = get_data_status()
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Checking {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            stock = yf.Ticker(ticker)
            
            # --- הטריק: משיכת נתונים כולל Pre-Market ---
            # interval=15m נותן לנו לראות את הקפיצה של הבוקר
            df = stock.history(period="5d", interval="15m", prepost=True)
            
            if df.empty or len(df) < 10:
                skipped_count += 1
                continue
            
            # מחיר נוכחי (הכי עדכני שיש)
            current_price = df['Close'].iloc[-1]
            
            # מחיר סגירה של אתמול (כדי לחשב GAP)
            # אנחנו לוקחים את המחיר האחרון של יום המסחר הקודם
            # הדרך הכי פשוטה: למצוא את המקסימום של אתמול או הסגירה האחרונה לפני היום
            yesterday_close = df['Close'].iloc[-15] # בערך לפני יום מסחר, לצורך הערכה
            # חישוב מדויק יותר ל-Gap:
            # אם אנחנו בפרה-מרקט, הסגירה של אתמול היא ה-Close של הנר האחרון ביום הקודם
            # לצורך הפשטות נשווה ללפני כמה נרות
            
            gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
            
            # בדיקת ווליום אחרון (האם יש מסחר עכשיו?)
            last_vol = df['Volume'].iloc[-1]
            
            # --- לוגיקת החלטה (Decision Engine) ---
            action = "IGNORE"
            instruction = ""
            reasons = []
            
            # 1. 🚀 מניה שטסה ב-Pre-Market (מעל 3% עלייה)
            if gap_percent > 3.0:
                action = "🚀 GAP UP"
                if gap_percent > 15.0:
                    instruction = "⚠️ RISKY! Wait for Pullback" # עלתה יותר מדי, מסוכן
                else:
                    instruction = "⚡ BUY NOW / LIMIT" # עלייה בריאה
                reasons.append(f"Gapped Up +{gap_percent:.1f}%")
            
            # 2. 📉 מניה שירדה חזק (הזדמנות לתיקון?)
            elif gap_percent < -3.0:
                action = "📉 GAP DOWN"
                instruction = "👀 WATCH FOR BOUNCE"
                reasons.append(f"Dropped {gap_percent:.1f}%")
            
            # 3. 👀 מניה שקטה אבל עם ווליום (מתבשלת)
            elif last_vol > 5000: # יש ווליום בפרה מרקט
                action = "👀 ACTIVE PRE-MARKET"
                instruction = "⏳ WAIT FOR OPEN BREAKOUT"
                reasons.append("High Pre-Market Volume")
            
            # חישוב יעדים טכניים
            stop_loss = current_price * 0.95 # 5% סטופ
            target = current_price * 1.10    # 10% יעד ראשוני
            
            # סינון: מציגים רק אם יש אקשן (GAP או ווליום)
            if action != "IGNORE":
                results.append({
                    "Ticker": ticker,
                    "Action": action,
                    "Instruction": instruction,
                    "Price": current_price,
                    "Gap": gap_percent,
                    "Stop": stop_loss,
                    "Target": target,
                    "Reasons": ", ".join(reasons)
                })
            else:
                skipped_count += 1
                
        except:
            skipped_count += 1
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), market_status

def plot_gap_chart(ticker):
    try:
        stock = yf.Ticker(ticker)
        # שים לב: prepost=True חובה כדי לראות את הגרף עכשיו!
        df = stock.history(period="2d", interval="5m", prepost=True)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], color='blue', label='Price (Inc. Pre-Market)')
        
        ax.set_title(f"{ticker} - Last 2 Days (With Pre-Market)")
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🌅 Pre-Market Commander")
st.caption("Designed for 16:00-16:30 Israel Time | Live Pre-Market Data")

df, status = scan_market()
st.info(f"🕒 Time Zone Status: **{status}**")

if not df.empty:
    df = df.sort_values(by='Gap', ascending=False)
    
    # לשוניות לפי סוג הפעולה
    tab1, tab2 = st.tabs(["🚀 ACTION NOW (Gappers)", "👀 WATCHLIST (Wait)"])
    
    # 1. מניות שזזות עכשיו
    with tab1:
        gappers = df[df['Action'].str.contains("GAP")]
        if not gappers.empty:
            for i, row in gappers.iterrows():
                # צבעים לפי סוג ההוראה
                color = "green" if "BUY" in row['Instruction'] else "orange"
                
                with st.expander(f"{row['Action']} {row['Ticker']} | {row['Gap']:.1f}% | ${row['Price']:.2f}", expanded=True):
                    st.markdown(f"### 💡 Instruction: :{color}[**{row['Instruction']}**]")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Target:** ${row['Target']:.2f}")
                        st.write(f"**Stop:** ${row['Stop']:.2f}")
                    with c2:
                        st.caption(f"Reason: {row['Reasons']}")
                    
                    # גרף לכל מניה - חובה!
                    fig = plot_gap_chart(row['Ticker'])
                    if fig: st.pyplot(fig)
        else:
            st.info("No big gappers found yet.")

    # 2. מניות למעקב
    with tab2:
        watch = df[~df['Action'].str.contains("GAP")]
        if not watch.empty:
            st.dataframe(watch[['Ticker', 'Price', 'Instruction', 'Reasons']])
        else:
            st.info("No active pre-market stocks found.")

else:
    if st.button("🚀 SCAN PRE-MARKET"):
        st.rerun()
