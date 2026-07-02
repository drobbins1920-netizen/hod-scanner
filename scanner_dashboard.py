import streamlit as st
import time
import requests
from datetime import datetime, timedelta, timezone
import finnhub
import pandas as pd

# ================== YOUR KEYS ==================
FINNHUB_API_KEY = "d8kvl29r01qut1f87070d8kvl29r01qut1f8707g"
FMP_API_KEY = "Q36YW4o2v1XwkQHhj5zVxbI3C6vDjgGC"
WEBULL_API_KEY = "1269f73b49b78f8702a3ad84752b9718"
TELEGRAM_TOKEN = "8970166305:AAGyTrj85fBEjsLvywUtZ79wgHX7gN29Efo"
TELEGRAM_CHAT_ID = "7680581613"

st.set_page_config(page_title="HOD Momentum Scanner", layout="wide")
st.title("🚀 High of Day Momentum Scanner")
st.caption("Auto-refreshes every 3 seconds + Sound + Telegram alerts")

# Sidebar Filters
with st.sidebar:
    st.header("Filters")
    min_price = st.number_input("Min Price", value=1.0)
    max_price = st.number_input("Max Price", value=20.0)
    min_gain = st.number_input("Min Gain %", value=10.0)
    max_float = st.number_input("Max Float (M)", value=10.0)
    rvol_threshold = st.number_input("Min RVOL", value=3.0)

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
        now = datetime.now(timezone.utc)
        from_str = (now - timedelta(hours=12)).strftime("%Y-%m-%d")
        to_str = now.strftime("%Y-%m-%d")
        news = finnhub_client.company_news(symbol, _from=from_str, to=to_str)
        if not news:
            return "⚪", ""
        latest = max(news, key=lambda x: x.get('datetime', 0))
        headline = latest.get('headline', '')[:80]
        hours_ago = (now - datetime.fromtimestamp(latest['datetime'], tz=timezone.utc)).total_seconds() / 3600
        if hours_ago < 2:
            return "🟥", headline
        elif hours_ago < 5:
            return "🟧", headline
        elif hours_ago < 12:
            return "🟩", headline
        return "⚪", headline
    except:
        return "⚪", ""

placeholder = st.empty()
last_alert = None

while True:
    with placeholder.container():
        st.write(f"Last update: {datetime.now(timezone.utc).astimezone().strftime('%H:%M:%S')}")
        
        try:
            # Webull API call using your key
            headers = {"Authorization": f"Bearer {WEBULL_API_KEY}"}
            response = requests.get("https://api.webull.com/quote/tickerRank/get?rankType=1", headers=headers)
            movers = response.json() if response.ok else []
            
            data = []
            for m in movers[:200]:
                symbol = m.get('symbol')
                if not symbol:
                    continue
                price = float(m.get('close', m.get('lastPrice', 0)))
                change_pct = float(m.get('changeRatio', 0)) * 100
                volume = int(m.get('volume', 0))
                avg_vol = int(m.get('avgVolume', volume * 0.3 or 1))
                
                if not (min_price <= price <= max_price and change_pct >= min_gain):
                    continue
                
                float_shares = get_float(symbol)
                if float_shares == 0 or float_shares > max_float * 1_000_000:
                    continue
                
                rvol = round(volume / avg_vol, 2) if avg_vol else 0
                if rvol < rvol_threshold:
                    continue
                
                emoji, headline = get_news_emoji_and_headline(symbol)
                
                data.append({
                    'ticker': symbol,
                    'price': round(price, 2),
                    'gain%': round(change_pct, 2),
                    'rvol': rvol,
                    'float_m': round(float_shares / 1_000_000, 2),
                    'news': emoji,
                    'headline': headline
                })
            
            df = pd.DataFrame(data)
            if not df.empty:
                df = df.sort_values(by='gain%', ascending=False)
                st.dataframe(df, use_container_width=True)
                
                if data and (last_alert is None or last_alert != data[0]['ticker']):
                    alert_msg = f"🚨 NEW HOD: {data[0]['ticker']} +{data[0]['gain%']}% RVOL: {data[0]['rvol']}"
                    st.success(alert_msg)
                    st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", autoplay=True)
                    send_telegram_alert(alert_msg)
                    last_alert = data[0]['ticker']
            else:
                st.info("No strong setups right now...")
        except Exception as e:
            st.error(f"Error: {e}")
    
    time.sleep(3)
