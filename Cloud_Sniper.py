import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 22.0 (Pre-Market Execution Fix)
# ==========================================
st.set_page_config(page_title="Day Trading Robot", page_icon="🎯", layout="wide")

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
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    market_open = now_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    
    if now_ny < market_open:
        return "🌅 PRE-MARKET (Live)", True
    return "☀️ MARKET OPEN", False

def get_latest_news(stock_obj):
    try:
        news = stock_obj.news
        if news and len(news) > 0:
            latest = news[0]
            title = latest['title']
            sentiment = "😐"
            t_lower = title.lower()
            score = 0
            if any(x in t_lower for x in ['beat', 'record', 'jump', 'surge', 'approval', 'buy', 'upgrade']):
                sentiment = "🟢"
                score = 10
            elif any(x in t_lower for x in ['miss', 'drop', 'fall', 'investigation', 'lawsuit', 'downgrade']):
                sentiment = "🔴"
                score = -10
            return f"{sentiment} {title}", score
        return "No News", 0
    except:
        return "N/A", 0

def analyze_daily_context(ticker):
    """ התיקון הקריטי: מתעלמים מהיום ובודקים רק היסטוריה סגורה """
    try:
        stock = yf.Ticker(ticker)
        # מושכים יותר ימים כדי להיות בטוחים
        daily = stock.history(period="1mo", interval="1d")
        
        if len(daily) < 5: return False, False, 0
        
        # זיהוי: האם השורה האחרונה היא "היום"?
        # אם כן, נחתוך אותה החוצה כדי לבדוק רק את מה שנסגר אתמול
        last_date = daily.index[-1].date()
        today_date = datetime.now().date() # זהירות עם אזורי זמן, אבל לרוב יאהו נותן תאריך עדכני
        
        # בטיחות: פשוט לוקחים את 3 הימים *לפני* הנר האחרון אם הוא של היום
        # אבל הדרך הכי בטוחה: לבדוק את ה-3 ימים שנגמרו לפני ה-GAP של הבוקר
        
        # נניח שאנחנו בפרה-מרקט, אז הנר האחרון הוא "היום" (וזז).
        # אנחנו רוצים לבדוק את: אתמול, שלשום, ולפני שלשום.
        history_closes = daily.iloc[:-1] # מעיפים את הנר הנוכחי (של היום)
        
        if len(history_closes) < 3: return False, False, 0
        
        last_3_days = history_closes.tail(3)
        
        # הבדיקה: האם ב-3 הימים הסגורים המניה ירדה?
        # (Close < Open) או (Close < Close של יום לפני)
        # שיטה מחמירה: כל יום נסגר נמוך מהיום שלפניו
        closes = last_3_days['Close'].values
        is_downtrend_3d = (closes[2] < closes[1]) and (closes[1] < closes[0])
        
        # או שיטה קלה יותר: 3 נרות אדומים
        is_3_red = all(day['Close'] < day['Open'] for i, day in last_3_days.iterrows())
        
        # מגמה ראשית (50 יום)
        sma_50 = history_closes['Close'].rolling(window=50).mean().iloc[-1]
        is_uptrend = history_closes['Close'].iloc[-1] > sma_50
        
        # הגבוה של אתמול (לפריצה)
        yest_high = history_closes['High'].iloc[-1]
        
        # אנחנו מחזירים True אם אחד התנאים מתקיים (ירידה רצופה במחיר או נרות אדומים)
        return (is_downtrend_3d or is_3_red), is_uptrend, yest_high
        
    except:
        return False, False, 0

def scan_market():
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(TICKERS)
    
    market_status, is_pre_market = get_data_status()
    
    for i, ticker in enumerate(TICKERS):
        try:
            status_text.text(f"Scanning {ticker} ({i+1}/{total})...")
            progress_bar.progress((i + 1) / total)
            
            # 1. ניתוח היסטורי (אתמול ואחורה)
            is_oversold, is_uptrend, yest_high = analyze_daily_context(ticker)
            
            stock = yf.Ticker(ticker)
            df = stock.history(period="5d", interval="15m", prepost=True)
            
            if df.empty or len(df) < 5: continue
            
            # 2. נתונים חיים (עכשיו)
            current_price = df['Close'].iloc[-1]
            last_vol = df['Volume'].iloc[-1]
            
            # חישוב GAP (מול הסגירה של אתמול)
            yesterday_close = df['Close'].iloc[-16] if len(df) > 16 else df['Close'].iloc[0]
            gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
            
            news_text, news_score = get_latest_news(stock)
            
            # --- הציון המשופר ---
            score = 50
            reasons = []
            
            # הקומבינציה המושלמת ל-16:00:
            # ירידה היסטורית (Oversold) + עלייה עכשיו (Gap Up)
            if is_oversold:
                if gap_percent > 0:
                    score += 30 # בינגו!
                    reasons.append("🔥 SPRING LOADED (3-Day Drop + Green Gap)")
                else:
                    score += 10
                    reasons.append("Oversold (Watch for bounce)")
            
            if current_price > yest_high:
                score += 15
                reasons.append("Breaking Yest. High")
                
            if gap_percent > 2: score += 10
            score += news_score
            
            final_score = min(100, max(0, score))
            
            # --- קבלת החלטות ---
            status = "💤 SLEEP"
            instruction = ""
            
            # מניות מעל ציון 70 הן המעניינות
            if final_score >= 70:
                if is_oversold and gap_percent > 0:
                    status = "🎯 PRE-MARKET BUY"
                    instruction = "Limit Order (Spring Loaded)"
                elif gap_percent > 3:
                    status = "🚀 MOMENTUM"
                    instruction = "Ride the Wave"
                else:
                    status = "⚡ ACTION"
                    instruction = "Watch Open"
            elif final_score >= 60:
                 status = "👀 WATCH"
                 instruction = "Wait for Volume"

            # ניהול סיכונים
            stop_loss = current_price * 0.95
            target = current_price * 1.15
            
            if status != "💤 SLEEP":
                results.append({
                    "Score": final_score,
                    "Ticker": ticker,
                    "Status": status,
                    "Price": round(current_price, 2),
                    "Gap": round(gap_percent, 2),
                    "Target": round(target, 2),
                    "Stop": round(stop_loss, 2),
                    "Details": ", ".join(reasons),
                    "News": news_text
                })
                
        except:
            continue
            
    progress_bar.empty()
    status_text.empty()
    return pd.DataFrame(results), market_status

def plot_context_chart(ticker, reasons):
    try:
        stock = yf.Ticker(ticker)
        # גרף יומי (לראות את היסטוריית הירידות)
        daily = stock.history(period="10d", interval="1d")
        # גרף תוך יומי (לראות את הקפיצה היום)
        intraday = stock.history(period="2d", interval="5m", prepost=True)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
        
        # גרף 1: היסטוריה (האם ירדנו?)
        colors = ['green' if c >= o else 'red' for c, o in zip(daily['Close'], daily['Open'])]
        ax1.bar(daily.index, daily['Close'] - daily['Open'], bottom=daily['Open'], color=colors, width=0.6)
        ax1.set_title("1. The Setup (Last 10 Days)")
        ax1.grid(True, alpha=0.3)
        
        # גרף 2: ההזדמנות (עכשיו)
        ax2.plot(intraday.index, intraday['Close'], color='blue')
        ax2.set_title("2. The Trigger (Today/Pre-Market)")
        ax2.grid(True, alpha=0.3)
        
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🎯 Pre-Market Sniper (16:00 Strategy)")
st.caption("Hunting 'Spring Loaded' stocks: 3 Red Days -> Green Gap")

data_df, m_status = scan_market()
st.info(f"🕒 Status: **{m_status}**")

if not data_df.empty:
    data_df = data_df.sort_values(by='Score', ascending=False)
    
    tab1, tab2 = st.tabs(["📋 SNIPER LIST", "🔍 CHART PROOF"])
    
    with tab1:
        st.dataframe(
            data_df,
            column_config={
                "Score": st.column_config.ProgressColumn("Rank", format="%d", min_value=0, max_value=100),
                "Status": st.column_config.TextColumn("Signal"),
                "Gap": st.column_config.NumberColumn("Gap %", format="%.1f%%"),
                "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
                "Details": "Why Buy?",
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

    with tab2:
        top_picks = data_df[data_df['Score'] >= 70]
        if not top_picks.empty:
            for i, row in top_picks.iterrows():
                st.divider()
                st.subheader(f"{row['Ticker']} | {row['Status']}")
                st.write(f"**Why:** {row['Details']}")
                st.info(f"Strategy: {row['Instruction']}")
                
                # כאן נראה את שני הגרפים: היסטוריה + הווה
                fig = plot_context_chart(row['Ticker'], row['Details'])
                if fig: st.pyplot(fig)
        else:
            st.warning("No perfect setups found right now.")

else:
    if st.button("🚀 SCAN"):
        st.rerun()
