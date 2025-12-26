import streamlit as st
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import numpy as np
import traceback
from io import StringIO

# ==========================================
# 0. CONSTANTS & THEME
# ==========================================
COLOR_BG = "#000000"
COLOR_HEADER_RED = "#800000"
COLOR_STYLE_ORANGE = "#FF9900"
COLOR_STYLE_TEXT_ORANGE = "#FFB03B"
COLOR_BORDER = "#333333"

# ==========================================
# 1. PAGE CONFIG & RIGID CSS
# ==========================================
st.set_page_config(layout="wide", page_title="eKIX PRO", initial_sidebar_state="collapsed")

# 起動状態
if 'launched' not in st.session_state:
    st.session_state.launched = False

# CSS: 徹底的な固定レイアウト化
st.markdown(f"""
<style>
    /* 全体のリセット */
    .stApp {{
        background-color: {COLOR_BG};
        color: #E0E0E0;
    }}
    header {{display: none !important;}}
    footer {{display: none !important;}}
    
    /* 余白の完全削除 */
    .block-container {{
        padding: 0rem !important;
        max-width: 100% !important;
    }}

    /* Streamlitの固定コンテナ(st.container)のデザイン上書き */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #000;
        border: 1px solid {COLOR_BORDER};
        border-radius: 0px !important;
        padding: 0px !important;
    }}
    
    /* 内部のスクロールバー装飾 */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: #111; }}
    ::-webkit-scrollbar-thumb {{ background: #444; border-radius: 0px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLOR_STYLE_ORANGE}; }}

    /* ボタンデザイン */
    div.stButton > button {{
        background-color: {COLOR_STYLE_ORANGE};
        color: #000000;
        font-weight: bold;
        border-radius: 0px;
        border: none;
        width: 100%;
        height: 30px;
        margin-top: 5px;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_STYLE_TEXT_ORANGE};
        color: #000;
    }}

    /* エディタの入力エリア */
    .stTextArea textarea {{
        background-color: #080808;
        color: {COLOR_STYLE_TEXT_ORANGE}; 
        font-family: 'Consolas', monospace;
        border: none;
    }}
    
    /* カスタムヘッダー */
    .app-header {{
        background-color: #111;
        height: 30px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid {COLOR_HEADER_RED};
        padding: 0 10px;
    }}
    .header-logo {{
        background-color: {COLOR_HEADER_RED};
        color: white;
        font-weight: bold;
        padding: 2px 8px;
        font-size: 11px;
        margin-right: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. STATE & LOGIC
# ==========================================
# 状態変数の初期化
if 'chart_data' not in st.session_state: st.session_state.chart_data = None
if 'chart_config' not in st.session_state: st.session_state.chart_config = {"title": "", "mav": ()}
if 'console_log' not in st.session_state: st.session_state.console_log = ">>> eKIX Pro Web Initialized.\n"
if 'panel_buttons' not in st.session_state: st.session_state.panel_buttons = []
if 'script_scope' not in st.session_state: st.session_state.script_scope = {}

# デフォルトコード
DEFAULT_CODE = """# eKIX Logic Script
import pandas as pd

# 状態管理クラス
class State:
    def __init__(self):
        self.symbols = ["USDJPY=X", "EURUSD=X", "BTC-USD", "^N225"]
        self.idx = 0
        self.tf = "1h"

if 'state' not in globals():
    state = State()

def main():
    sym = state.symbols[state.idx]
    print(f"Loading {sym} [{state.tf}]...")
    
    # データ取得
    df = app.api_get_dataframe(sym, state.tf, "5d")
    
    if df is not None:
        title = f"{sym} - {state.tf}"
        app.api_plot_candle(df, title=title, mav=(20, 50))
        print("Chart updated.")
    else:
        print("No data.")

# パネルUI構築
app.api_clear_panel()
app.api_add_right_label("=== CONTROLS ===")

def change_sym():
    state.idx = (state.idx + 1) % len(state.symbols)
    main()

app.api_add_right_button("Rotate Symbol", change_sym)
app.api_add_right_button("Refresh", main)

# 初回実行
main()
"""

if 'user_code' not in st.session_state: st.session_state.user_code = DEFAULT_CODE

# --- API CLASS ---
class WebQuantTerminal:
    def api_get_dataframe(self, symbol, timeframe, period_or_count):
        try:
            p = period_or_count if isinstance(period_or_count, str) else "5d"
            df = yf.download(tickers=symbol, interval=timeframe, period=p, progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            return df
        except Exception as e:
            print(f"ERR: {e}")
            return None

    def api_plot_candle(self, df, title="Chart", mav=()):
        st.session_state.chart_data = df
        st.session_state.chart_config = {"title": title, "mav": mav}

    def api_clear_panel(self):
        st.session_state.panel_buttons = []

    def api_add_right_label(self, text):
        pass 

    def api_add_right_button(self, text, command, color=None):
        st.session_state.panel_buttons.append({"text": text, "func_name": command.__name__})

# --- EXECUTION ENGINE ---
def execute_logic(target_func=None):
    buffer = StringIO()
    api = WebQuantTerminal()
    
    def scoped_print(*args):
        buffer.write(" ".join(map(str, args)) + "\n")
    
    if not st.session_state.script_scope:
        st.session_state.script_scope = {"app": api, "pd": pd, "np": np, "print": scoped_print}
    else:
        st.session_state.script_scope["app"] = api
        st.session_state.script_scope["print"] = scoped_print

    try:
        if target_func:
            func = st.session_state.script_scope.get(target_func)
            if func: func()
        else:
            exec(st.session_state.user_code, st.session_state.script_scope)
        
        st.session_state.console_log += buffer.getvalue()
    except Exception:
        st.session_state.console_log += f"\nERR: {traceback.format_exc()}"

# ==========================================
# 3. UI RENDERING (FIXED GRID LAYOUT)
# ==========================================

if not st.session_state.launched:
    # --- LAUNCH SCREEN ---
    _, c, _ = st.columns([1, 2, 1])
    with c:
        st.markdown("<div style='height: 40vh'></div>", unsafe_allow_html=True) 
        st.markdown(f"<h1 style='text-align: center; color: {COLOR_HEADER_RED};'>eKIX PRO WEB</h1>", unsafe_allow_html=True)
        if st.button("LAUNCH TERMINAL"):
            st.session_state.launched = True
            st.rerun()
else:
    # --- TERMINAL HEADER ---
    st.markdown(f"""
    <div class="app-header">
        <div class="header-logo">eKIX PRO</div>
        <div style="color: #666; font-size: 12px; font-family: Arial;">WEB TERMINAL ENV</div>
        <div style="flex-grow:1"></div>
        <div style="color: {COLOR_STYLE_ORANGE}; font-size: 12px;">● LIVE</div>
    </div>
    """, unsafe_allow_html=True)

    # ========================================================
    # GRID LAYOUT: Using st.container(height=...) for RIGIDITY
    # ========================================================
    
    # CSS Gridの代わりに、Streamlitの新しい固定高コンテナを使用します。
    # これにより、内部コンテンツが増減しても外枠のサイズが絶対にかわりません。
    
    # TOP ROW: Height 550px
    c_top_left, c_top_right = st.columns([3.5, 1], gap="small")
    
    # --- TOP LEFT: CHART ---
    with c_top_left:
        with st.container(height=550, border=True):
            df = st.session_state.chart_data
            cfg = st.session_state.chart_config
            
            if df is not None:
                # グラフ設定
                mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in')
                s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, facecolor='#000000', figcolor='#000000', gridstyle=':')
                
                # 図の比率をコンテナに合わせる (スクロールバーが出ないように調整)
                fig, ax = mpf.plot(
                    df, type='candle', style=s, volume=True,
                    mav=cfg['mav'], title=f"\n{cfg['title']}",
                    returnfig=True, 
                    figsize=(10, 6), 
                    tight_layout=True
                )
                st.pyplot(fig, use_container_width=True)
            else:
                st.markdown("<div style='height: 100%; display:flex; align-items:center; justify-content:center; color:#333;'>NO DATA LOADED</div>", unsafe_allow_html=True)

    # --- TOP RIGHT: PANEL ---
    with c_top_right:
        with st.container(height=550, border=True):
            st.markdown(f"<div style='color:{COLOR_STYLE_ORANGE}; font-weight:bold; margin-bottom:10px;'>COMMAND PANEL</div>", unsafe_allow_html=True)
            
            if st.session_state.panel_buttons:
                for btn in st.session_state.panel_buttons:
                    if st.button(btn["text"], key=f"btn_{btn['text']}"):
                        execute_logic(btn["func_name"])
                        st.rerun()
            else:
                st.caption("No active commands.")
            
            st.markdown("---")
            if st.button("RESET VIEW"): st.rerun()

    # BOTTOM ROW: Height 300px
    c_bot_left, c_bot_right = st.columns([1, 1], gap="small")

    # --- BOTTOM LEFT: EDITOR ---
    with c_bot_left:
        # コンテナの中にエディタとRUNボタンを入れる
        with st.container(height=300, border=True):
            # RUNボタンをタブのように配置
            col_run, col_label = st.columns([1, 3])
            with col_run:
                if st.button("▶ RUN ASYNC"):
                    with st.spinner(".."):
                        execute_logic()
                    st.rerun()
            
            # コードエディタ (高さはCSSで調整済みだが、ここでもfitさせる)
            code = st.text_area("Code", value=st.session_state.user_code, height=220, label_visibility="collapsed")
            st.session_state.user_code = code

    # --- BOTTOM RIGHT: CONSOLE ---
    with c_bot_right:
        with st.container(height=300, border=True):
            st.markdown(f"<div style='color:#666; font-size:12px; margin-bottom:5px;'>TERMINAL OUTPUT</div>", unsafe_allow_html=True)
            
            # ログ表示エリア (HTMLでスクロール領域を作る)
            log_html = f"""
            <div style='font-family:"Consolas",monospace; color:{COLOR_STYLE_TEXT_ORANGE}; font-size:12px; white-space:pre-wrap;'>
            {st.session_state.console_log}
            </div>
            """
            st.markdown(log_html, unsafe_allow_html=True)
            
            # 一番下にクリアボタン
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("CLEAR LOG"):
                st.session_state.console_log = ">>> Log Cleared.\n"
                st.rerun()
