import streamlit as st
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import numpy as np
import traceback
import sys
from io import StringIO
import contextlib

# ==========================================
# 1. デザイン & 設定 (eKIX Style)
# ==========================================
st.set_page_config(layout="wide", page_title="eKIX Web Terminal", initial_sidebar_state="collapsed")

# カスタムCSS: 黒背景・オレンジアクセント・モノスペースフォント
st.markdown("""
<style>
    .stApp { background-color: #000000; color: #E0E0E0; }
    .stTextArea textarea { background-color: #080808; color: #FFB03B; font-family: 'Consolas', monospace; }
    .stButton > button { background-color: #FF9900; color: black; font-weight: bold; border: none; }
    .stButton > button:hover { background-color: #FFB03B; color: black; }
    div[data-testid="stExpander"] { background-color: #111; border: 1px solid #333; }
    h1, h2, h3 { color: #800000; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 状態管理 (Session State)
# ==========================================
# チャートデータやログをセッション間で保持します
if 'chart_data' not in st.session_state:
    st.session_state.chart_data = None
if 'chart_config' not in st.session_state:
    st.session_state.chart_config = {"title": "Waiting for Script...", "mav": ()}
if 'logs' not in st.session_state:
    st.session_state.logs = "System Initialized.\n"
if 'user_code' not in st.session_state:
    # デフォルトのスクリプト
    st.session_state.user_code = """
# eKIX Web Script
# 'app' オブジェクトを使って操作します

symbol = "USDJPY=X" # yfinance symbol
print(f"Fetching data for {symbol}...")

# データを取得 (API経由)
df = app.api_get_dataframe(symbol, "1h", "5d")

if df is not None:
    # チャート描画
    app.api_plot_candle(df, title=f"{symbol} 1H Chart", mav=(20, 50))
    print("Chart updated successfully.")
else:
    print("Failed to fetch data.")
"""

# ==========================================
# 3. 互換APIクラス (MT5版のロジックを吸収)
# ==========================================
class WebQuantAPI:
    """ユーザーコードから呼び出されるAPIヘルパー"""
    
    def api_get_dataframe(self, symbol, timeframe, period_or_count):
        """
        yfinanceを使用してデータを取得するラッパー
        timeframe: "1m", "5m", "1h", "1d" etc.
        period: "1d", "5d", "1mo", "1y" etc. (countの代わりにperiodを使います)
        """
        try:
            # yfinance用にシンボル補正などが必要ならここで行う
            df = yf.download(tickers=symbol, interval=timeframe, period=period_or_count, progress=False)
            
            if df.empty:
                return None
            
            # MultiIndex対応
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            # カラムリネーム (mplfinance用)
            # yfinanceは最初から Open, High, Low, Close, Volume なのでそのままでOK
            return df
        except Exception as e:
            print(f"API Error: {e}")
            return None

    def api_plot_candle(self, df, title="Chart", mav=()):
        """Session Stateを更新して、次回の描画サイクルでチャートを表示させる"""
        st.session_state.chart_data = df
        st.session_state.chart_config = {"title": title, "mav": mav}

    def api_clear_log(self):
        st.session_state.logs = ""

# ==========================================
# 4. コード実行エンジン
# ==========================================
def execute_script():
    """ユーザーコードをexecで実行し、標準出力をキャプチャする"""
    code = st.session_state.code_input # Text Areaのキー
    
    # 標準出力をキャプチャするためのバッファ
    buffer = StringIO()
    
    # 実行環境(globals)の準備
    api_instance = WebQuantAPI()
    exec_globals = {
        "app": api_instance,
        "pd": pd,
        "np": np,
        "yf": yf,
        "print": lambda *args: buffer.write(" ".join(map(str, args)) + "\n") # printをオーバーライド
    }

    try:
        with st.spinner("Running Script (Async simulation)..."):
            # 安全ではないが、ユーザーの要望通りexecを使用
            exec(code, exec_globals)
            
        # 成功時のログ追加
        st.session_state.logs += f"\n>>> RUN ({pd.Timestamp.now().strftime('%H:%M:%S')})\n"
        st.session_state.logs += buffer.getvalue()
        
    except Exception:
        # エラー時のログ追加
        st.session_state.logs += f"\n>>> ERROR:\n{traceback.format_exc()}"

# ==========================================
# 5. UI構築 (レイアウト)
# ==========================================

# --- ヘッダー ---
c1, c2 = st.columns([1, 5])
with c1:
    st.markdown("## eKIX PRO")
with c2:
    st.caption("Web-based Quant Terminal | Powered by Streamlit & yfinance")

st.divider()

# --- 上部: チャート表示エリア ---
chart_placeholder = st.empty()

# 描画ロジック
df = st.session_state.chart_data
config = st.session_state.chart_config

if df is not None and not df.empty:
    # mplfinanceスタイル定義
    mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in')
    s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, facecolor='#000000', figcolor='#000000', gridstyle=':')
    
    try:
        fig, axlist = mpf.plot(
            df, type='candle', style=s, volume=True,
            mav=config['mav'],
            title=f"\n{config['title']}",
            returnfig=True, figsize=(10, 6), tight_layout=True
        )
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Chart Rendering Error: {e}")
else:
    # データがない場合のプレースホルダー
    st.info("No Data. Click 'RUN SCRIPT' to fetch data and plot.")


st.divider()

# --- 下部: エディタとコンソール (2カラム) ---
col_editor, col_console = st.columns([1, 1])

with col_editor:
    st.markdown("### 📝 Code Editor")
    st.text_area(
        "Python Script", 
        value=st.session_state.user_code, 
        height=300, 
        key="code_input",
        help="ここで `app.api_get_dataframe` などを呼び出します"
    )
    
    # 実行ボタン
    if st.button("▶ RUN SCRIPT", use_container_width=True):
        execute_script()
        st.rerun() # 画面をリロードしてチャートとログを反映

with col_console:
    st.markdown("### 📟 Terminal Console")
    # ログ表示エリア（スクロール可能なテキストボックス風）
    st.text_area(
        "Output Log", 
        value=st.session_state.logs, 
        height=300, 
        disabled=True, # 読み取り専用
        key="log_output"
    )
    
    if st.button("Clear Console"):
        st.session_state.logs = ""
        st.rerun()
