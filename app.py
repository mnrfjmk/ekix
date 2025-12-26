import streamlit as st
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import numpy as np
import traceback
from io import StringIO
import time

# ==========================================
# 0. CONSTANTS & THEME
# ==========================================
COLOR_BG = "#000000"
COLOR_HEADER_RED = "#800000"
COLOR_STYLE_ORANGE = "#FF9900"
COLOR_STYLE_TEXT_ORANGE = "#FFB03B"
COLOR_BORDER = "#333333"
COLOR_PANEL_BG = "#0A0A0A"

# ==========================================
# 1. PAGE CONFIG & PIXEL-PERFECT CSS
# ==========================================
st.set_page_config(layout="wide", page_title="eKIX PRO", initial_sidebar_state="collapsed")

# 起動状態管理
if 'launched' not in st.session_state:
    st.session_state.launched = False

# CSS: 徹底的なスタイル強制
st.markdown(f"""
<style>
    /* ----------------------------------
       BASE RESET
    ---------------------------------- */
    .stApp {{
        background-color: {COLOR_BG};
        color: #E0E0E0;
    }}
    header, footer {{display: none !important;}}
    
    /* 余白削除: 画面いっぱいに使う */
    .block-container {{
        padding: 0rem !important;
        max-width: 100% !important;
    }}

    /* コンテナの枠線と背景 */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {COLOR_BG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 0px !important;
        padding: 0px !important;
    }}

    /* ----------------------------------
       WIDGET STYLING
    ---------------------------------- */
    
    /* ボタン (eKIX Style) */
    div.stButton > button {{
        background-color: {COLOR_STYLE_ORANGE};
        color: #000000;
        font-family: Arial, sans-serif;
        font-weight: bold;
        border-radius: 0px;
        border: 1px solid #222;
        width: 100%;
        height: 28px;
        line-height: 28px;
        padding: 0px;
        margin: 0px;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_STYLE_TEXT_ORANGE};
        color: #000;
        border-color: #FFF;
    }}

    /* テキストエリア (Editor & Console 共通) */
    .stTextArea {{ margin-bottom: 0px; }}
    .stTextArea label {{ display: none; }} /* ラベルを完全に隠す */
    
    .stTextArea textarea {{
        background-color: #080808 !important;
        color: {COLOR_STYLE_TEXT_ORANGE} !important;
        font-family: 'Consolas', 'Courier New', monospace !important;
        font-size: 13px !important;
        line-height: 1.4 !important;
        border: none !important;
        border-radius: 0px !important;
        padding: 10px !important;
    }}
    
    /* Disabledなテキストエリア（コンソール用）の文字色を強制的に濃くする */
    .stTextArea textarea[disabled] {{
        color: {COLOR_STYLE_TEXT_ORANGE} !important;
        -webkit-text-fill-color: {COLOR_STYLE_TEXT_ORANGE} !important;
        opacity: 1 !important;
    }}

    /* スクロールバー */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: #111; }}
    ::-webkit-scrollbar-thumb {{ background: #333; border: 1px solid #000; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLOR_STYLE_ORANGE}; }}

    /* ----------------------------------
       CUSTOM HTML COMPONENTS
    ---------------------------------- */
    .app-header {{
        background-color: #111;
        height: 32px;
        display: flex;
        align-items: center;
        border-bottom: 2px solid {COLOR_HEADER_RED};
        padding: 0 10px;
        font-family: Arial, sans-serif;
    }}
    .header-logo {{
        background-color: {COLOR_HEADER_RED};
        color: white;
        font-weight: bold;
        padding: 2px 8px;
        font-size: 11px;
        margin-right: 15px;
    }}
    .panel-header {{
        color: {COLOR_STYLE_ORANGE};
        font-weight: bold;
        font-size: 11px;
        font-family: Arial, sans-serif;
        padding: 5px;
        border-bottom: 1px solid #333;
        margin-bottom: 5px;
    }}
    
    /* ツールバーのスタイル調整 */
    .toolbar-box {{
        background-color: #151515;
        height: 36px;
        border-top: 1px solid {COLOR_BORDER};
        border-bottom: 1px solid {COLOR_BORDER};
        display: flex;
        align-items: center;
        padding: 0 5px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. STATE & LOGIC
# ==========================================
if 'chart_data' not in st.session_state: st.session_state.chart_data = None
if 'chart_config' not in st.session_state: st.session_state.chart_config = {"title": "", "mav": ()}
if 'console_log' not in st.session_state: st.session_state.console_log = ">>> eKIX Pro Web Initialized.\n"
if 'panel_buttons' not in st.session_state: st.session_state.panel_buttons = []
if 'script_scope' not in st.session_state: st.session_state.script_scope = {}
if 'status_msg' not in st.session_state: st.session_state.status_msg = "Ready"

DEFAULT_CODE = """# eKIX Logic Script
import pandas as pd

# 状態保持クラス
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
        print("Chart updated successfully.")
    else:
        print("No data found.")

# パネル構築
app.api_clear_panel()
app.api_add_right_label("=== CONTROLS ===")

def change_sym():
    state.idx = (state.idx + 1) % len(state.symbols)
    main()

app.api_add_right_button("Rotate Symbol", change_sym)
app.api_add_right_button("Force Refresh", main)

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
        # ログには出さず、UI構築用として処理（今回はシンプル化のためスキップ）
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

    st.session_state.status_msg = "Running..."
    try:
        if target_func:
            func = st.session_state.script_scope.get(target_func)
            if func: func()
        else:
            exec(st.session_state.user_code, st.session_state.script_scope)
        
        st.session_state.console_log += buffer.getvalue()
        st.session_state.status_msg = "Ready"
    except Exception:
        st.session_state.console_log += f"\nERR: {traceback.format_exc()}"
        st.session_state.status_msg = "Error"

# ==========================================
# 3. UI RENDERING (FIXED LAYOUT)
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
    # ---------------------------------------------------------
    # [A] Header Strip
    # ---------------------------------------------------------
    st.markdown(f"""
    <div class="app-header">
        <div class="header-logo">eKIX PRO</div>
        <div style="color: #666; font-size: 11px; font-weight:bold;">WEB ENV</div>
        <div style="flex-grow:1"></div>
        <div style="color: {COLOR_STYLE_ORANGE}; font-size: 11px;">● LIVE</div>
    </div>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [B] Top Area: Chart (Left) | Panel (Right)
    # ---------------------------------------------------------
    c_chart, c_panel = st.columns([3.5, 1], gap="small")

    with c_chart:
        # 固定高コンテナ (Height 500px)
        with st.container(height=500, border=True):
            df = st.session_state.chart_data
            cfg = st.session_state.chart_config
            
            if df is not None:
                # チャート描画
                mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in')
                s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, facecolor='#000000', figcolor='#000000', gridstyle=':')
                
                # コンテナサイズに合わせた図のサイズ調整
                fig, ax = mpf.plot(
                    df, type='candle', style=s, volume=True,
                    mav=cfg['mav'], title=f"\n{cfg['title']}",
                    returnfig=True, 
                    figsize=(10, 5.8), # 高さを微調整してスクロールを防止
                    tight_layout=True
                )
                st.pyplot(fig, use_container_width=True)
            else:
                st.markdown("<div style='height: 100%; display:flex; align-items:center; justify-content:center; color:#333; font-family:Arial;'>NO DATA LOADED</div>", unsafe_allow_html=True)

    with c_panel:
        # パネルコンテナ (Height 500px)
        with st.container(height=500, border=True):
            st.markdown('<div class="panel-header">COMMAND PANEL</div>', unsafe_allow_html=True)
            
            # 動的ボタン描画
            if st.session_state.panel_buttons:
                for btn in st.session_state.panel_buttons:
                    if st.button(btn["text"], key=f"btn_{btn['text']}"):
                        execute_logic(btn["func_name"])
                        st.rerun()
            else:
                st.caption("No commands.")
            
            st.markdown("---")
            if st.button("RESET VIEW"): st.rerun()

    # ---------------------------------------------------------
    # [C] Toolbar (Run Button & Status) - 元のTkinter版と同じ位置
    # ---------------------------------------------------------
    # CSSで高さを固定したツールバーエリア
    with st.container():
        # 少し色をつけるためコンテナを使うが、CSSでクラス指定が難しいため
        # 単純なカラムレイアウトで再現
        col_tb_btn, col_tb_stat = st.columns([1, 6])
        with col_tb_btn:
            if st.button("▶ RUN ASYNC"):
                with st.spinner(".."):
                    execute_logic()
                st.rerun()
        with col_tb_stat:
            # ステータス表示
            status_color = "#888" if st.session_state.status_msg == "Ready" else COLOR_STYLE_ORANGE
            st.markdown(f"<div style='height: 30px; line-height: 30px; margin-left: 10px; color: {status_color}; font-family: Arial; font-weight: bold; font-size: 11px;'>{st.session_state.status_msg}</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [D] Bottom Area: Editor (Left) | Console (Right)
    # ---------------------------------------------------------
    c_edit, c_cons = st.columns([1, 1], gap="small")

    # 高さ300px固定
    with c_edit:
        with st.container(height=300, border=True):
            # Editor
            code = st.text_area("Code", value=st.session_state.user_code, height=290, label_visibility="collapsed")
            st.session_state.user_code = code

    with c_cons:
        with st.container(height=300, border=True):
            # Console: disabled=Trueにすることで編集不可にし、CSSで色を維持
            # これによりHTMLタグの問題も解消し、ネイティブなスクロールが効く
            st.text_area("Console", value=st.session_state.console_log, height=290, disabled=True, label_visibility="collapsed")
            
            # クリアボタンはスペース節約のため省略するか、ログの先頭にコマンドとして追加する運用を想定
