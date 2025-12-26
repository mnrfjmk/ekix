import streamlit as st
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import numpy as np
import traceback
from io import StringIO
import time

# ==========================================
# 0. CONSTANTS & THEME (Original App Colors)
# ==========================================
COLOR_BG = "#000000"
COLOR_HEADER_RED = "#800000"
COLOR_STYLE_ORANGE = "#FF9900"
COLOR_STYLE_TEXT_ORANGE = "#FFB03B"
COLOR_BORDER = "#333333"
COLOR_PANEL_BG = "#050505" # Original Right Panel BG

# ==========================================
# 1. PAGE CONFIG & PIXEL-PERFECT CSS
# ==========================================
st.set_page_config(layout="wide", page_title="eKIX PRO", initial_sidebar_state="collapsed")

# 起動状態管理
if 'launched' not in st.session_state:
    st.session_state.launched = False

# CSS: Streamlitのウェブっぽさを消し、Tkinterアプリ風にする強力なスタイル
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

    /* コンテナの枠線と背景 (TkinterのFrameっぽく) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {COLOR_BG};
        border: 1px solid {COLOR_BORDER};
        border-radius: 0px !important;
        padding: 0px !important;
    }}

    /* ----------------------------------
       WIDGET STYLING
    ---------------------------------- */
    
    /* ボタン (eKIX CustomTkinter Style) */
    div.stButton > button {{
        background-color: {COLOR_STYLE_ORANGE};
        color: #000000;
        font-family: Arial, sans-serif;
        font-weight: bold;
        border-radius: 0px;
        border: 1px solid #222;
        width: 100%;
        height: 30px;
        line-height: 30px;
        padding: 0px;
        margin-top: 2px;
        margin-bottom: 2px;
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
    
    /* Disabledなテキストエリア（コンソール用）の文字色を強制的に維持 */
    .stTextArea textarea[disabled] {{
        color: {COLOR_STYLE_TEXT_ORANGE} !important;
        -webkit-text-fill-color: {COLOR_STYLE_TEXT_ORANGE} !important;
        opacity: 1 !important;
    }}

    /* スクロールバー (Dark Theme) */
    ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
    ::-webkit-scrollbar-track {{ background: #111; }}
    ::-webkit-scrollbar-thumb {{ background: #333; border: 1px solid #000; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLOR_STYLE_ORANGE}; }}

    /* ----------------------------------
       CUSTOM HTML COMPONENTS (Header & Labels)
    ---------------------------------- */
    .app-header {{
        background-color: #111;
        height: 30px;
        display: flex;
        align-items: center;
        border-bottom: 0px solid {COLOR_HEADER_RED}; /* 元コードに合わせて枠線なし、左にラベル */
        padding: 0 0px;
        font-family: Arial, sans-serif;
    }}
    .header-logo {{
        background-color: {COLOR_HEADER_RED};
        color: white;
        font-weight: bold;
        padding: 0px 15px;
        height: 30px;
        line-height: 30px;
        font-size: 11px;
        margin-right: 15px;
        display: inline-block;
    }}
    .panel-header {{
        color: {COLOR_STYLE_ORANGE};
        font-weight: bold;
        font-size: 11px;
        font-family: Arial, sans-serif;
        padding: 5px;
        text-align: center;
        margin-bottom: 5px;
    }}
    
    /* ステータスバーのスタイル */
    .status-text {{
        color: #888;
        font-family: Arial, sans-serif;
        font-weight: bold;
        font-size: 10px;
        padding-left: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. STATE & LOGIC
# ==========================================
if 'chart_data' not in st.session_state: st.session_state.chart_data = None
if 'chart_config' not in st.session_state: st.session_state.chart_config = {"title": "", "mav": ()}
if 'console_log' not in st.session_state: st.session_state.console_log = ">>> System Initialized. Press 'RUN ASYNC' to start.\n>>> "
if 'panel_buttons' not in st.session_state: st.session_state.panel_buttons = []
if 'script_scope' not in st.session_state: st.session_state.script_scope = {}
if 'status_msg' not in st.session_state: st.session_state.status_msg = "Ready"

# 元のロジックに近いデフォルトスクリプト (yfinance版)
DEFAULT_CODE = """import pandas as pd

# --- 1. 設定管理クラス (状態保持) ---
class ChartConfig:
    def __init__(self):
        # 監視リスト (yfinance tickers)
        self.symbols = ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "GC=F", "BTC-USD"]
        self.sym_idx = 0
        
        # 時間足 (yfinance format)
        self.timeframes = ["1m", "5m", "15m", "1h", "1d"]
        self.tf_idx = 3 # Initial: 1h
        
        # 期間 (yfinance logic)
        self.periods = ["1d", "5d", "1mo", "3mo"]
        self.cnt_idx = 1 # Initial: 5d

    @property
    def current_symbol(self): return self.symbols[self.sym_idx]
    @property
    def current_tf(self): return self.timeframes[self.tf_idx]
    @property
    def current_period(self): return self.periods[self.cnt_idx]

# グローバル変数に 'state' がなければ作成
if 'state' not in globals():
    state = ChartConfig()

# --- 2. チャート更新関数 ---
def refresh_chart():
    sym = state.current_symbol
    tf = state.current_tf
    prd = state.current_period
    
    print(f"Loading: {sym} / {tf} / {prd}...")
    
    # データを取得 (API経由)
    df = app.api_get_dataframe(sym, tf, prd)
    
    if df is not None and not df.empty:
        title = f"{sym} [{tf}]"
        
        # データ量に応じて移動平均線の計算有無を決定
        if len(df) > 50:
            mav_set = (20, 50)
        else:
            mav_set = ()

        # チャート描画 (API経由)
        app.api_plot_candle(df, title=title, mav=mav_set)
        print("Chart Updated successfully.")
    else:
        print(f"Error: No data found for {sym}.")

# --- 3. コントロールパネル構築 ---
def build_panel():
    app.api_clear_panel()
    
    # 銘柄変更
    def cycle_symbol():
        state.sym_idx = (state.sym_idx + 1) % len(state.symbols)
        refresh_chart()
    app.api_add_right_button(f"Symbol: Rotate", cycle_symbol)

    # 時間足変更
    def cycle_tf():
        state.tf_idx = (state.tf_idx + 1) % len(state.timeframes)
        refresh_chart()
    app.api_add_right_button(f"TimeFrame: Rotate", cycle_tf)

    # 期間変更
    def cycle_period():
        state.cnt_idx = (state.cnt_idx + 1) % len(state.periods)
        refresh_chart()
    app.api_add_right_button(f"Period: Rotate", cycle_period)
    
    app.api_add_right_button("Force Refresh", refresh_chart)

# --- 4. メイン実行 ---
print("Initializing Script Logic...")
build_panel()
refresh_chart()
"""

if 'user_code' not in st.session_state: st.session_state.user_code = DEFAULT_CODE

# --- API CLASS (Shim for original app structure) ---
class WebQuantTerminal:
    def api_get_dataframe(self, symbol, timeframe, period_or_count):
        try:
            # yfinance logic
            p = period_or_count if isinstance(period_or_count, str) else "5d"
            df = yf.download(tickers=symbol, interval=timeframe, period=p, progress=False)
            if df.empty: return None
            # Handle MultiIndex headers if present
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            # yfinance returns Title case (Open, High...), mplfinance is happy with that
            return df
        except Exception as e:
            print(f"API ERR: {e}")
            return None

    def api_plot_candle(self, df, title="Chart", mav=()):
        st.session_state.chart_data = df
        st.session_state.chart_config = {"title": title, "mav": mav}

    def api_clear_panel(self):
        st.session_state.panel_buttons = []

    def api_add_right_label(self, text):
        pass # UI Label skip for web simplicity or add to log

    def api_add_right_button(self, text, command, color=None):
        # Store function name to call later
        st.session_state.panel_buttons.append({"text": text, "func_name": command.__name__})
        
    def api_set_panel_visibility(self, visible):
        pass

# --- EXECUTION ENGINE ---
def execute_logic(target_func=None):
    buffer = StringIO()
    api = WebQuantTerminal()
    
    # Redirect print to buffer
    def scoped_print(*args):
        buffer.write(" ".join(map(str, args)) + "\n")
    
    # Init Globals if needed
    if not st.session_state.script_scope:
        st.session_state.script_scope = {"app": api, "pd": pd, "np": np, "print": scoped_print}
    else:
        # Refresh API instance and print hook
        st.session_state.script_scope["app"] = api
        st.session_state.script_scope["print"] = scoped_print

    st.session_state.status_msg = "Running..."
    try:
        if target_func:
            # Execute specific button function
            func = st.session_state.script_scope.get(target_func)
            if func: func()
        else:
            # Execute full script
            exec(st.session_state.user_code, st.session_state.script_scope)
        
        # Append buffer to log
        output = buffer.getvalue()
        if output:
            st.session_state.console_log += output
            st.session_state.console_log += ">>> "
            
        st.session_state.status_msg = "Ready"
    except Exception:
        err = traceback.format_exc()
        st.session_state.console_log += f"\nERR:\n{err}\n>>> "
        st.session_state.status_msg = "Error"

# ==========================================
# 3. UI RENDERING (FIXED LAYOUT)
# ==========================================

if not st.session_state.launched:
    # --- LAUNCH SCREEN (Centered) ---
    _, c, _ = st.columns([1, 2, 1])
    with c:
        st.markdown("<div style='height: 40vh'></div>", unsafe_allow_html=True) 
        st.markdown(f"<h1 style='text-align: center; color: {COLOR_HEADER_RED}; font-family: Arial;'>eKIX PRO WEB</h1>", unsafe_allow_html=True)
        if st.button("LAUNCH TERMINAL"):
            st.session_state.launched = True
            st.rerun()
else:
    # ---------------------------------------------------------
    # [A] HEADER (Custom HTML)
    # ---------------------------------------------------------
    st.markdown(f"""
    <div class="app-header">
        <div class="header-logo"> eKIX PRO </div>
        <div style="flex-grow:1"></div>
        <div style="color: #666; font-size: 11px; margin-right:10px;">SESSION ACTIVE</div>
    </div>
    """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [B] TOP PANE: CHART (Left) + PANEL (Right)
    # Fixed height container is key to prevent layout shifts
    # ---------------------------------------------------------
    # Using 3.5 : 1 ratio as per original visual weight
    c_chart, c_panel = st.columns([3.5, 1], gap="small")

    # HEIGHT SETTING: Adjust this (e.g., 500) to match desired window size
    TOP_HEIGHT = 500 

    with c_chart:
        # Fixed Chart Container
        with st.container(height=TOP_HEIGHT, border=True):
            df = st.session_state.chart_data
            cfg = st.session_state.chart_config
            
            if df is not None:
                # mplfinance setup
                mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in')
                s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, facecolor='#000000', figcolor='#000000', gridstyle=':')
                
                # Plot with exact sizing to fill container
                fig, ax = mpf.plot(
                    df, type='candle', style=s, volume=True,
                    mav=cfg['mav'], title=f"\n{cfg['title']}",
                    returnfig=True, 
                    figsize=(10, 5.8), # Tuned for aspect ratio
                    tight_layout=True
                )
                st.pyplot(fig, use_container_width=True)
            else:
                st.markdown("<div style='height: 100%; display:flex; align-items:center; justify-content:center; color:#333; font-family:Arial;'>NO DATA LOADED</div>", unsafe_allow_html=True)

    with c_panel:
        # Fixed Panel Container (Orange Buttons)
        with st.container(height=TOP_HEIGHT, border=True):
            # Panel Background trick (CSS handles global, here we just place content)
            st.markdown('<div class="panel-header">COMMAND PANEL</div>', unsafe_allow_html=True)
            
            # Dynamic Buttons
            if st.session_state.panel_buttons:
                for btn in st.session_state.panel_buttons:
                    if st.button(btn["text"], key=f"btn_{btn['text']}"):
                        execute_logic(btn["func_name"])
                        st.rerun()
            else:
                st.markdown("<div style='text-align:center; color:#444; font-size:10px;'>Running Init...</div>", unsafe_allow_html=True)
            
            st.markdown("---")
            if st.button("RESET VIEW"): st.rerun()

    # ---------------------------------------------------------
    # [C] TOOLBAR (Middle Strip)
    # ---------------------------------------------------------
    # Replicates the "Toolbar" frame from tkinter
    with st.container():
        c_tool_btn, c_tool_lbl = st.columns([1, 6])
        with c_tool_btn:
            if st.button("▶ RUN ASYNC"):
                with st.spinner(".."):
                    execute_logic()
                st.rerun()
        with c_tool_lbl:
            # Status Label styling
            status_col = COLOR_STYLE_ORANGE if st.session_state.status_msg == "Running..." else "#888"
            st.markdown(f"<div style='height: 38px; line-height: 38px; display:flex; align-items:center;'><span class='status-text' style='color:{status_col}'> {st.session_state.status_msg}</span></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # [D] BOTTOM PANE: EDITOR (Left) + CONSOLE (Right)
    # ---------------------------------------------------------
    c_edit, c_cons = st.columns([1, 1], gap="small")
    
    BOTTOM_HEIGHT = 280

    with c_edit:
        with st.container(height=BOTTOM_HEIGHT, border=True):
            # Code Editor
            code = st.text_area("Code", value=st.session_state.user_code, height=BOTTOM_HEIGHT-20, label_visibility="collapsed")
            st.session_state.user_code = code

    with c_cons:
        with st.container(height=BOTTOM_HEIGHT, border=True):
            # Console: disabled=True ensures read-only text area (no HTML rendering issues)
            # The CSS above forces the color to remain bright orange even when disabled.
            st.text_area("Console", value=st.session_state.console_log, height=BOTTOM_HEIGHT-20, disabled=True, label_visibility="collapsed")
