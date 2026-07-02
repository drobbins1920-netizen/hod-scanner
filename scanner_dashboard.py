import streamlit as st
import time
import requests
from datetime import datetime, timedelta, timezone
import pandas as pd
from zoneinfo import ZoneInfo

# ================== YOUR KEYS ==================
WEBULL_API_KEY = "1269f73b49b78f8702a3ad84752b9718"
TELEGRAM_TOKEN = "8970166305:AAGyTrj85fBEjsLvywUtZ79wgHX7gN29Efo"
TELEGRAM_CHAT_ID = "7680581613"

st.set_page_config(page_title="HOD Momentum Scanner", layout="wide")
st.title("🚀 HOD Momentum Scanner")
st.caption("Simple & Aggressive - Market Hours Test")

# Sidebar Filters
with st.sidebar:
    st.header("Filters")
    min_gain = st.number_input("Min Gain %", value=2.0)
    max_float = st.number_input("Max Float (M)", value=100.0)

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
            headers = {"Authorization": f"Bearer {WEBULL_API_KEY}"}
            response = requests.get("https://api.webull.com/quote/tickerRank/get?rankType=1", headers=headers)
            movers = response.json() if response.ok else []
            
            data = []
            for m in movers[:1000]:
                symbol = m.get('symbol')
                if not symbol:
                    continue
                price = float(m.get('close', m.get('lastPrice', 0)))
                change_pct = float(m.get('changeRatio', 0)) * 100
                volume = int(m.get('volume', 0))
                avg_vol = int(m.get('avgVolume', volume * 0.3 or 1))
                
                if change_pct < min_gain:
                    continue
                
                entry = {
                    'time': datetime.now(ZoneInfo('America/New_York')).strftime('%H:%M:%S'),
                    'ticker': f"[{symbol}](https://app.webull.com/quote/{symbol})",
                    'price': round(price, 2),
                    'gain%': round(change_pct, 2),
                    'rvol': round(volume / avg_vol, 2) if avg_vol else 0,
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
                    
                    if data:
                        alert_msg = f"🚨 NEW HOD: {data[0]['ticker']} +{data[0]['gain%']}%"
                        st.success(alert_msg)
                        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3", autoplay=True)
                        send_telegram_alert(alert_msg)
                        last_alert = data[0]['ticker']
                else:
                    st.info("Waiting for movers...")
            
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
