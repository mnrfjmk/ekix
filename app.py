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
COLOR_PANEL_BG = "#0A0A0A"
COLOR_BORDER = "#333333"

# ==========================================
# 1. PAGE CONFIG & AGGRESSIVE CSS
# ==========================================
st.set_page_config(layout="wide", page_title="eKIX PRO", initial_sidebar_state="collapsed")

# 起動状態
if 'launched' not in st.session_state:
    st.session_state.launched = False

# CSS: Streamlitの標準スタイルを破壊し、デスクトップアプリのレイアウトを強制する
st.markdown(f"""
<style>
    /* 1. ベースリセット: 余白削除・黒背景・スクロールバー装飾 */
    .stApp {{
        background-color: {COLOR_BG};
        color: #E0E0E0;
    }}
    /* Streamlit標準のヘッダー/フッター/メニューを消す */
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* メインコンテナの余白をゼロにする */
    .block-container {{
        padding-top: 0rem !important;
        padding-bottom: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }}

    /* スクロールバーのデザイン (ダークモード風) */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: #111; }}
    ::-webkit-scrollbar-thumb {{ background: #333; }}
    ::-webkit-scrollbar-thumb:hover {{ background: #555; }}

    /* 2. UIコンポーネントのカスタマイズ */
    
    /* ボタン (角ばったデザイン・オレンジ) */
    div.stButton > button {{
        background-color: {COLOR_STYLE_ORANGE};
        color: #000000;
        font-weight: bold;
        border-radius: 0px;
        border: 1px solid #000;
        width: 100%;
        height: 28px;
        line-height: 28px;
        padding: 0px;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_STYLE_TEXT_ORANGE};
        color: #000000;
        border-color: #FFF;
    }}

    /* テキストエリア (エディタの再現) */
    .stTextArea {{ margin-bottom: 0px; }}
    .stTextArea textarea {{
        background-color: #080808;
        color: {COLOR_STYLE_TEXT_ORANGE}; 
        font-family: 'Consolas', monospace;
        font-size: 13px;
        border: 1px solid {COLOR_BORDER};
        border-radius: 0px;
        height: 35vh !important; /* 画面下部の高さを固定 */
    }}
    
    /* 3. カスタムレイアウトクラス (HTML埋め込み用) */
    .app-header {{
        background-color: #111;
        height: 35px;
        display: flex;
        align-items: center;
        border-bottom: 1px solid {COLOR_BORDER};
        padding: 0 10px;
    }}
    .header-logo {{
        background-color: {COLOR_HEADER_RED};
        color: white;
        font-weight: bold;
        padding: 2px 10px;
        margin-right: 15px;
        font-family: Arial, sans-serif;
        font-size: 12px;
    }}
    .panel-header {{
        color: {COLOR_STYLE_ORANGE};
        font-weight: bold;
        font-family: Arial, sans-serif;
        font-size: 12px;
        margin-bottom: 5px;
        padding-left: 5px;
    }}
    .console-box {{
        background-color: #080808;
        color: {COLOR_STYLE_TEXT_ORANGE};
        font-family: 'Consolas', monospace;
        font-size: 12px;
        padding: 5px;
        border: 1px solid {COLOR_BORDER};
        height: 35vh; /* エディタと同じ高さ */
        overflow-y: scroll;
        white-space: pre-wrap;
    }}
    
    /* 水平線の調整 */
    hr {{ margin: 0.2em 0; border-color: {COLOR_BORDER}; }}
    
    /* Streamlitのカラム間隔を狭める */
    div[data-testid="column"] {{
        padding: 0 2px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. STATE & LOGIC
# ==========================================
# セッション変数の初期化
if 'chart_data' not in st.session_state: st.session_state.chart_data = None
if 'chart_config' not in st.session_state: st.session_state.chart_config = {"title": "WAITING FOR DATA", "mav": ()}
if 'console_log' not in st.session_state: st.session_state.console_log = ">>> eKIX Pro Web Initialized.\n"
if 'panel_buttons' not in st.session_state: st.session_state.panel_buttons = []
if 'script_scope' not in st.session_state: st.session_state.script_scope = {}

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
        pass # UI上でのラベル表示は簡易化のため省略（またはログへ）

    def api_add_right_button(self, text, command, color=None):
        st.session_state.panel_buttons.append({"text": text, "func_name": command.__name__})

# --- EXECUTION ENGINE ---
def execute_logic(target_func=None):
    buffer = StringIO()
    api = WebQuantTerminal()
    
    # PrintのリダイレクトとAPIの注入
    def scoped_print(*args):
        buffer.write(" ".join(map(str, args)) + "\n")
    
    if not st.session_state.script_scope:
        st.session_state.script_scope = {"app": api, "pd": pd, "np": np, "print": scoped_print}
    else:
        st.session_state.script_scope["app"] = api
        st.session_state.script_scope["print"] = scoped_print

    try:
        if target_func:
            # ボタン経由: 既存の関数を呼び出す
            func = st.session_state.script_scope.get(target_func)
            if func: func()
        else:
            # RUN経由: 全コードを実行
            exec(st.session_state.user_code, st.session_state.script_scope)
        
        st.session_state.console_log += buffer.getvalue()
    except Exception:
        st.session_state.console_log += f"\nERR: {traceback.format_exc()}"

# ==========================================
# 3. UI RENDERING (PIXEL-PERFECT LAYOUT)
# ==========================================

if not st.session_state.launched:
    # --- LAUNCH SCREEN (Centered) ---
    _, c, _ = st.columns([1, 2, 1])
    with c:
        st.markdown("<div style='height: 40vh'></div>", unsafe_allow_html=True) # Spacer
        st.markdown(f"<h1 style='text-align: center; color: {COLOR_HEADER_RED};'>eKIX PRO WEB</h1>", unsafe_allow_html=True)
        if st.button("LAUNCH TERMINAL"):
            st.session_state.launched = True
            st.rerun()
else:
    # --- MAIN TERMINAL LAYOUT ---
    
    # [A] Header Strip (Custom HTML)
    st.markdown(f"""
    <div class="app-header">
        <div class="header-logo">eKIX PRO</div>
        <div style="color: #666; font-size: 12px; font-family: Arial;">WEB TERMINAL ENV</div>
        <div style="flex-grow:1"></div>
        <div style="color: {COLOR_STYLE_ORANGE}; font-size: 12px;">● LIVE</div>
    </div>
    """, unsafe_allow_html=True)

    # [B] Top Area: Chart (75%) | Panel (25%)
    # Viewport Height (vh) を使ってスクロールを排除し、固定高さにする
    c_chart, c_panel = st.columns([3, 1], gap="small")

    with c_chart:
        # Chart Container (Fixed Height: 55vh)
        chart_container = st.container()
        with chart_container:
            df = st.session_state.chart_data
            cfg = st.session_state.chart_config
            
            if df is not None:
                # MPLFinanceのスタイル
                mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in')
                s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, facecolor='#000000', figcolor='#000000', gridstyle=':')
                
                # 図のサイズを調整してコンテナに収める
                fig, ax = mpf.plot(
                    df, type='candle', style=s, volume=True,
                    mav=cfg['mav'], title=f"\n{cfg['title']}",
                    returnfig=True, 
                    figsize=(10, 5.5), # 比率調整
                    tight_layout=True
                )
                st.pyplot(fig, use_container_width=True)
            else:
                st.markdown("<div style='height: 55vh; display:flex; align-items:center; justify-content:center; color:#444;'>NO DATA LOADED</div>", unsafe_allow_html=True)

    with c_panel:
        # Panel Container (Fixed Height matched to chart)
        st.markdown(f"<div style='height: 5px;'></div>", unsafe_allow_html=True) # Spacer
        st.markdown('<div class="panel-header">COMMAND PANEL</div>', unsafe_allow_html=True)
        
        # Panel Content
        with st.container():
            if st.session_state.panel_buttons:
                for btn in st.session_state.panel_buttons:
                    if st.button(btn["text"], key=f"btn_{btn['text']}"):
                        execute_logic(btn["func_name"])
                        st.rerun()
            else:
                st.caption("No commands.")
                
            st.markdown("---")
            if st.button("RESET VIEW"): st.rerun()

    # [C] Toolbar Strip (Visual Separator)
    st.markdown(f"<div style='background-color: #222; height: 30px; display: flex; align-items: center; padding-left: 5px; border-top: 1px solid {COLOR_BORDER}; border-bottom: 1px solid {COLOR_BORDER}; margin-top: 5px;'></div>", unsafe_allow_html=True)

    # [D] Bottom Area: Editor (50%) | Console (50%)
    # Fixed Height set in CSS to 35vh
    c_edit, c_cons = st.columns([1, 1], gap="small")

    with c_edit:
        # Code Editor Area
        # RUNボタンをツールバーの位置に重ねるため、カラム内に配置
        # 上部にRUNボタン
        if st.button("▶ RUN ASYNC", key="run_main"):
            with st.spinner("Running..."):
                execute_logic()
            st.rerun()
            
        code = st.text_area("Code", value=st.session_state.user_code, label_visibility="collapsed", key="editor_area")
        st.session_state.user_code = code

    with c_cons:
        # Console Area
        st.markdown('<div style="height: 28px; line-height:28px; color:#666; font-size:12px; font-weight:bold; padding-left:5px;">TERMINAL OUTPUT</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="console-box">{st.session_state.console_log}</div>', unsafe_allow_html=True)
        
        # Clear Log (Floating or simple button below)
        if st.button("Clear Log", key="clr_log"):
            st.session_state.console_log = ">>> Log Cleared.\n"
            st.rerun()
