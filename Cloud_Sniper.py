import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import pytz

# ==========================================
# ⚙️ הגדרות - גרסה 17.5 (News & Gaps)
# ==========================================
st.set_page_config(page_title="Pre-Market Commander", page_icon="📰", layout="wide")

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

def get_latest_news(stock_obj):
    """ משיכת הכותרת האחרונה """
    try:
        news = stock_obj.news
        if news and len(news) > 0:
            latest = news[0]
            title = latest['title']
            publisher = latest['publisher']
            link = latest['link']
            # בדיקת מילות מפתח חיוביות/שליליות בכותרת
            sentiment = "neutral"
            title_lower = title.lower()
            if any(x in title_lower for x in ['beat', 'record', 'jump', 'up', 'surge', 'agreement', 'approval']):
                sentiment = "positive"
            elif any(x in title_lower for x in ['miss', 'down', 'drop', 'fall', 'lawsuit', 'fail', 'investigation']):
                sentiment = "negative"
                
            return title, publisher, link, sentiment
        return "No recent news found", "", "", "neutral"
    except:
        return "News unavailable", "", "", "neutral"

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
            
            # --- משיכת נתונים כולל Pre-Market ---
            df = stock.history(period="5d", interval="15m", prepost=True)
            
            if df.empty or len(df) < 10:
                skipped_count += 1
                continue
            
            # מחיר נוכחי
            current_price = df['Close'].iloc[-1]
            
            # מחיר סגירה של אתמול (לחישוב GAP)
            # לוקחים את הנתון מלפני יום מסחר (בערך) כדי לדלג על הפרי-מרקט של היום
            # פתרון חכם: לוקחים את ה-Close של השעה 16:00 אתמול אם אפשר, או פשוט אחורה
            yesterday_close = df['Close'].iloc[-16] # בערך יום אחורה בנרות של 15 דק
            
            gap_percent = ((current_price - yesterday_close) / yesterday_close) * 100
            last_vol = df['Volume'].iloc[-1]
            
            # --- משיכת חדשות ---
            news_title, news_pub, news_link, sentiment = get_latest_news(stock)
            
            # --- לוגיקה ---
            action = "IGNORE"
            instruction = ""
            reasons = []
            
            # 1. מניה שזזה חזק (GAP)
            if abs(gap_percent) > 3.0:
                action = "🚀 GAP MOVER" if gap_percent > 0 else "📉 GAP DROP"
                if gap_percent > 0:
                    instruction = "Check News -> Buy Dip"
                else:
                    instruction = "Watch for Reversal"
                reasons.append(f"Gap {gap_percent:+.1f}%")
            
            # 2. מניה עם ווליום חריג בבוקר
            elif last_vol > 10000:
                action = "👀 HIGH VOL"
                instruction = "Wait for Breakout"
                reasons.append("Active Pre-Market Volume")
                
            # סינון: רק אם יש אקשן או חדשות דרמטיות
            if action != "IGNORE":
                results.append({
                    "Ticker": ticker,
                    "Action": action,
                    "Instruction": instruction,
                    "Price": current_price,
                    "Gap": gap_percent,
                    "News_Title": news_title,
                    "News_Pub": news_pub,
                    "News_Link": news_link,
                    "Sentiment": sentiment,
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
        # גרף עם Pre-Market
        df = stock.history(period="2d", interval="5m", prepost=True)
        
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(df.index, df['Close'], color='#2980b9', linewidth=1.5, label='Price (Inc. Pre-Market)')
        
        ax.set_title(f"{ticker} - Live Price Action")
        ax.grid(True, alpha=0.3)
        ax.legend()
        return fig
    except:
        return None

# ==========================================
# 🖥️ UI
# ==========================================
st.title("🌅 Pre-Market Commander + News")
st.caption("Live Data (16:00 IL) | News Analysis | Gap Detection")

df, status = scan_market()
st.info(f"🕒 Status: **{status}**")

if not df.empty:
    df = df.sort_values(by='Gap', ascending=False, key=abs) # מיון לפי גודל התנועה (חיובי או שלילי)
    
    # חלוקה ללשוניות
    tab1, tab2 = st.tabs(["🚀 ACTION LIST", "📋 WATCHLIST"])
    
    with tab1:
        # מניות שזזות חזק (מעל 3% או מתחת ל-3%)
        movers = df[abs(df['Gap']) > 3.0]
        if not movers.empty:
            for i, row in movers.iterrows():
                # אייקון לפי חדשות
                news_icon = "📰"
                if row['Sentiment'] == 'positive': news_icon = "🟢 Good News:"
                if row['Sentiment'] == 'negative': news_icon = "🔴 Bad News:"
                
                with st.expander(f"{row['Action']} {row['Ticker']} | {row['Gap']:+.1f}% | ${row['Price']:.2f}", expanded=True):
                    
                    # הצגת חדשות מובלטת
                    st.info(f"**{news_icon} {row['News_Title']}**\n\n*{row['News_Pub']}*")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"**Strategy:** {row['Instruction']}")
                        if row['News_Link']:
                            st.markdown(f"[Read Full Story]({row['News_Link']})")
                    with c2:
                        st.caption(f"Tech Reason: {row['Reasons']}")
                    
                    fig = plot_gap_chart(row['Ticker'])
                    if fig: st.pyplot(fig)
        else:
            st.info("No major gaps found yet.")

    with tab2:
        watch = df[abs(df['Gap']) <= 3.0]
        if not watch.empty:
            st.dataframe(watch[['Ticker', 'Price', 'Gap', 'News_Title']])
        else:
            st.info("No active stocks.")

else:
    if st.button("🚀 SCAN PRE-MARKET"):
        st.rerun()
