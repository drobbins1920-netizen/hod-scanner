import streamlit as st
import time
import requests
from datetime import datetime, timedelta, timezone
import finnhub
import pandas as pd
from zoneinfo import ZoneInfo

# ================== YOUR KEYS ==================
FINNHUB_API_KEY = "d8kvl29r01qut1f87070d8kvl29r01qut1f8707g"
FMP_API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"
TELEGRAM_TOKEN = "8970166305:AAGyTrj85fBEjsLvywUtZ79wgHX7gN29Efo"
TELEGRAM_CHAT_ID = "7680581613"

st.set_page_config(page_title="HOD Momentum Scanner", layout="wide")
st.title("🚀 Finnhub HOD Momentum Scanner")
st.caption("Better pre-market & real-time detection")

# Sidebar Filters
with st.sidebar:
    st.header("Filters")
    min_price = st.number_input("Min Price", value=1.0)
    max_price = st.number_input("Max Price", value=100.0)
    min_gain = st.number_input("Min Gain %", value=5.0)
    max_float = st.number_input("Max Float (M)", value=50.0)
    rvol_threshold = st.number_input("Min RVOL", value=1.5)

finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

def send_telegram_alert(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        requests.post(url, json=payload)
    except:
        pass

def get_float(symbol):
    try:
        url = f"https://financialmodelingprep.com/stable/shares-float?symbol={symbol}&apikey={FMP_API_KEY}"
        r = requests.get(url, timeout=8)
        data = r.json()
        if isinstance(data, list) and data:
            return data[0].get('floatShares', 0)
        return 0
    except:
        return 0

def get_news_emoji_and_headline(symbol):
    try:
        now = datetime.now(timezone.edt)
        from_str = (now - timedelta(hours=12)).strftime("%Y-%m-%d")
        to_str = now.strftime("%Y-%m-%d")
        news = finnhub_client.company_news(symbol, _from=from_str, to=to_str)
        if not news:
            return "⚪", ""
        latest = max(news, key=lambda x: x.get('datetime', 0))
        headline = latest.get('headline', '')[:80]
        hours_ago = (now - datetime.fromtimestamp(latest['datetime'], tz=timezone.edt)).total_seconds() / 3600
        if hours_ago < 2:
            return "🟥", headline
        elif hours_ago < 5:
            return "🟧", headline
        elif hours_ago < 12:
            return "🟩", headline
        return "⚪", headline
    except:
        return "⚪", ""

if 'scan_history' not in st.session_state:
    st.session_state.scan_history = []
if 'full_log' not in st.session_state:
    st.session_state.full_log = []

placeholder = st.empty()
last_alert = None

tab1, tab2 = st.tabs(["Live Scanner", "Historical Log"])

while True:
    with placeholder.container():
        st.write(f"Last update: {datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M:%S')}")
        
        try:
            # Finnhub real-time scan
            symbols = finnhub_client.stock_symbols(exchange='US')
            movers = []
            for s in symbols[:1500]:   # Limit to avoid rate limits
                try:
                    quote = finnhub_client.quote(s['symbol'])
                    change_pct = quote.get('dp', 0)
                    if change_pct >= min_gain:
                        movers.append({
                            'symbol': s['symbol'],
                            'changeRatio': change_pct / 100,
                            'close': quote.get('c', 0),
                            'volume': quote.get('v', 0)
                        })
                except:
                    continue
            
            data = []
            for m in movers:
                symbol = m['symbol']
                price = m['close']
                change_pct = m['changeRatio'] * 100
                volume = m['volume']
                avg_vol = volume * 0.5 if volume > 0 else 1
                
                if not (min_price <= price <= max_price):
                    continue
                
                float_shares = get_float(symbol)
                if float_shares == 0 or float_shares > max_float * 1_000_000:
                    continue
                
                rvol = round(volume / avg_vol, 2)
                if rvol < rvol_threshold:
                    continue
                
                emoji, headline = get_news_emoji_and_headline(symbol)
                
                entry = {
                    'time': datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M:%S'),
                    'ticker': f"[{symbol}](https://app.webull.com/quote/{symbol})",
                    'price': round(price, 2),
                    'gain%': round(change_pct, 2),
                    'rvol': rvol,
                    'float_m': round(float_shares / 1_000_000, 2),
                    'news': emoji,
                    'headline': headline
                }
                data.append(entry)
                st.session_state.full_log.append(entry)
                st.session_state.scan_history.append(entry)
            
            # Live Scanner Tab
            with tab1:
                df_live = pd.DataFrame(st.session_state.scan_history)
                if not df_live.empty:
                    df_live = df_live.sort_values(by='gain%', ascending=False)
                    st.dataframe(df_live, use_container_width=True)
                    
                    if data and (last_alert is None or last_alert != data[0]['ticker']):
                        alert_msg = f"🚨 NEW HOD: {data[0]['ticker']} +{data[0]['gain%']}% RVOL: {data[0]['rvol']}"
                        st.success(alert_msg)
                        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", autoplay=True)
                        send_telegram_alert(alert_msg)
                        last_alert = data[0]['ticker']
                else:
                    st.info("No strong setups right now...")
            
            # Historical Log Tab
            with tab2:
                df_log = pd.DataFrame(st.session_state.full_log)
                if not df_log.empty:
                    df_log = df_log.sort_values(by='time', ascending=False)
                    st.dataframe(df_log, use_container_width=True)
            
            st.session_state.scan_history = st.session_state.scan_history[-50:]
            
        except Exception as e:
            st.error(f"Error: {e}")
    
    time.sleep(5)
