import streamlit as st
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import numpy as np
import traceback
import sys
from io import StringIO
import time

# ==========================================
# 0. CONSTANTS (ここを追加しました)
# ==========================================
COLOR_BG = "#000000"
COLOR_HEADER_RED = "#800000"
COLOR_STYLE_ORANGE = "#FF9900"
COLOR_STYLE_TEXT_ORANGE = "#FFB03B"
COLOR_PANEL_BG = "#0A0A0A"

# ==========================================
# 1. ページ設定 & CSS (全画面・ダークテーマ化)
# ==========================================
st.set_page_config(layout="wide", page_title="eKIX Pro Web", initial_sidebar_state="collapsed")

# 起動状態の管理
if 'launched' not in st.session_state:
    st.session_state.launched = False

# CSS: ブラウザの余白を極限まで削り、デスクトップアプリ風にする
st.markdown(f"""
<style>
    /* 全体の背景と色 */
    .stApp {{
        background-color: {COLOR_BG};
        color: #E0E0E0;
    }}
    /* ヘッダーを隠す (全画面感) */
    header {{visibility: hidden;}}
    
    /* ブロックごとの余白調整 */
    .block-container {{
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }}
    
    /* ボタンデザイン (eKIX Orange) */
    div.stButton > button {{
        background-color: {COLOR_STYLE_ORANGE};
        color: #000000;
        font-weight: bold;
        border-radius: 0px;
        border: 1px solid #333;
        width: 100%;
    }}
    div.stButton > button:hover {{
        background-color: {COLOR_STYLE_TEXT_ORANGE};
        color: #000000;
        border-color: #FFF;
    }}
    
    /* テキストエリア (エディタ風) */
    .stTextArea textarea {{
        background-color: #080808;
        color: {COLOR_STYLE_TEXT_ORANGE}; 
        font-family: 'Consolas', monospace;
        font-size: 14px;
        border: 1px solid #333;
    }}
    
    /* コンソール出力エリア */
    .console-box {{
        background-color: #080808;
        color: #E0E0E0;
        font-family: 'Consolas', monospace;
        padding: 10px;
        border: 1px solid #333;
        height: 300px;
        overflow-y: scroll;
        white-space: pre-wrap;
    }}
    
    /* タイトルなどの装飾 */
    h1, h2, h3 {{ color: {COLOR_HEADER_RED} !important; font-family: 'Arial', sans-serif; }}
    hr {{ margin: 0.5em 0; border-color: #333; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. セッション状態管理 (変数の永続化)
# ==========================================
if 'chart_data' not in st.session_state:
    st.session_state.chart_data = None
if 'chart_config' not in st.session_state:
    st.session_state.chart_config = {"title": "NO DATA", "mav": ()}
if 'console_log' not in st.session_state:
    st.session_state.console_log = ">>> System Ready.\n"
if 'panel_buttons' not in st.session_state:
    st.session_state.panel_buttons = [] # 動的ボタンのリスト
if 'script_scope' not in st.session_state:
    st.session_state.script_scope = {} # ユーザーコードのグローバル変数空間

# デフォルトスクリプト
DEFAULT_CODE = """
# eKIX Web Script (yfinance版)
import pandas as pd

# 設定保持用クラス
class Config:
    def __init__(self):
        self.symbols = ["USDJPY=X", "EURUSD=X", "BTC-USD", "GC=F"]
        self.idx = 0
        self.period = "5d"
        self.interval = "1h"

if 'state' not in globals():
    state = Config()

def refresh_chart():
    sym = state.symbols[state.idx]
    print(f"Fetching {sym} ({state.period}/{state.interval})...")
    
    # データ取得
    df = app.api_get_dataframe(sym, state.interval, state.period)
    
    if df is not None:
        title = f"{sym} [{state.interval}]"
        app.api_plot_candle(df, title=title, mav=(20, 50))
        print("Done.")
    else:
        print("Data fetch failed.")

# --- パネル構築 ---
app.api_clear_panel()
app.api_add_right_label("=== CONTROL ===")

def rotate_symbol():
    state.idx = (state.idx + 1) % len(state.symbols)
    refresh_chart()

app.api_add_right_button("Rotate Symbol", rotate_symbol)
app.api_add_right_button("Refresh Chart", refresh_chart)

# 初回実行
refresh_chart()
"""

if 'user_code' not in st.session_state:
    st.session_state.user_code = DEFAULT_CODE

# ==========================================
# 3. 互換APIクラス (仮想Terminal環境)
# ==========================================
class WebQuantTerminal:
    """デスクトップ版のメソッドをWeb用にエミュレートするクラス"""
    
    def api_get_dataframe(self, symbol, timeframe, period_or_count):
        """yfinanceでデータ取得"""
        try:
            # yfinanceは count ではなく period (1d, 5d, 1mo) を使うため、簡易変換
            if isinstance(period_or_count, int):
                period = "5d" # 整数が来たらとりあえず5日にする安全策
            else:
                period = period_or_count

            df = yf.download(tickers=symbol, interval=timeframe, period=period, progress=False)
            
            if df.empty: return None
            
            # MultiIndex対応 (yfinanceのバージョン差異吸収)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)
            
            return df
        except Exception as e:
            print(f"API Error: {e}")
            return None

    def api_plot_candle(self, df, title="Chart", mav=()):
        """チャート描画指示（データだけ保存し、描画はメインループに任せる）"""
        st.session_state.chart_data = df
        st.session_state.chart_config = {"title": title, "mav": mav}

    def api_clear_panel(self):
        """右パネルのボタンをクリア"""
        st.session_state.panel_buttons = []

    def api_add_right_label(self, text):
        """右パネルにラベル追加（今回は簡易的にログ出力で代用または無視）"""
        pass 

    def api_add_right_button(self, text, command, color="#222"):
        """
        右パネルにボタンを追加。
        重要: commandは関数オブジェクトだが、Webでは永続化できないため
        関数名を文字列として保存し、実行時にスコープから探す。
        """
        func_name = command.__name__
        st.session_state.panel_buttons.append({"text": text, "func_name": func_name})

    def api_set_panel_visibility(self, visible):
        pass

# ==========================================
# 4. ロジック実行エンジン
# ==========================================
def run_code_logic():
    """エディタのコードを実行する"""
    code = st.session_state.user_code
    buffer = StringIO()
    
    # APIインスタンス
    api = WebQuantTerminal()
    
    # 実行用グローバル変数を準備（前回の状態を引き継ぐ）
    if not st.session_state.script_scope:
        st.session_state.script_scope = {
            "app": api, "pd": pd, "np": np, "mt5": None, # mt5はダミー
            "print": lambda *args: buffer.write(" ".join(map(str, args)) + "\n")
        }
    else:
        # appインスタンスとprintだけは新しく更新
        st.session_state.script_scope["app"] = api
        st.session_state.script_scope["print"] = lambda *args: buffer.write(" ".join(map(str, args)) + "\n")

    try:
        # コード実行
        exec(code, st.session_state.script_scope)
        st.session_state.console_log += buffer.getvalue()
    except Exception:
        st.session_state.console_log += f"\nERROR:\n{traceback.format_exc()}\n"

def trigger_button_action(func_name):
    """右パネルのボタンが押されたときに特定の関数を実行する"""
    buffer = StringIO()
    # API再設定
    st.session_state.script_scope["app"] = WebQuantTerminal()
    st.session_state.script_scope["print"] = lambda *args: buffer.write(" ".join(map(str, args)) + "\n")
    
    try:
        func = st.session_state.script_scope.get(func_name)
        if callable(func):
            func() # 関数実行
            st.session_state.console_log += f">>> Called: {func_name}\n"
            st.session_state.console_log += buffer.getvalue()
        else:
            st.session_state.console_log += f"Error: Function '{func_name}' not found.\n"
    except Exception:
        st.session_state.console_log += f"\nERROR:\n{traceback.format_exc()}\n"

# ==========================================
# 5. UI構築 (条件分岐: ランディング vs ターミナル)
# ==========================================

if not st.session_state.launched:
    # --- ランディング画面 (Launchボタンのみ) ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        # 修正: f-stringでCOLOR_HEADER_REDを参照できるようになりました
        st.markdown(f"<h1 style='text-align: center; color: {COLOR_HEADER_RED};'>eKIX PRO WEB</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Integrated Quant Environment (Cloud Edition)</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("LAUNCH TERMINAL", use_container_width=True):
            st.session_state.launched = True
            st.rerun()

else:
    # --- 全画面ターミナルモード ---
    
    # 1. ヘッダーバー
    st.markdown(f"<div style='background-color: #111; padding: 5px; border-bottom: 2px solid {COLOR_HEADER_RED};'><b>eKIX PRO</b> <span style='color:#888; font-size:0.8em;'>| SESSION ACTIVE</span></div>", unsafe_allow_html=True)

    # 2. 上段: チャート(左) + コントロールパネル(右)
    # Streamlitのcolumns比率でPanedWindowを再現
    col_chart, col_panel = st.columns([4, 1]) 

    with col_chart:
        # チャート描画
        df = st.session_state.chart_data
        cfg = st.session_state.chart_config
        
        if df is not None:
            # mplfinanceの設定
            mc = mpf.make_marketcolors(up='#00ff00', down='#ff0000', edge='inherit', wick='inherit', volume='in')
            s = mpf.make_mpf_style(base_mpf_style='nightclouds', marketcolors=mc, facecolor=COLOR_BG, figcolor=COLOR_BG, gridstyle=':')
            
            try:
                fig, ax = mpf.plot(
                    df, type='candle', style=s, volume=True,
                    mav=cfg['mav'], title=f"\n{cfg['title']}",
                    returnfig=True, figsize=(10, 6), tight_layout=True
                )
                st.pyplot(fig)
            except Exception as e:
                st.error(f"Plot Error: {e}")
        else:
            st.info("NO DATA. Press RUN or Controls.")

    with col_panel:
        st.markdown("**COMMAND PANEL**")
        st.markdown("---")
        # 動的ボタンの生成
        if st.session_state.panel_buttons:
            for btn in st.session_state.panel_buttons:
                # ボタンを押すと、その関数を実行する
                if st.button(btn["text"], key=btn["text"]):
                    trigger_button_action(btn["func_name"])
                    st.rerun()
        else:
            st.caption("No controls defined.")
        
        st.markdown("---")
        if st.button("RELOAD UI", help="Force UI Refresh"):
            st.rerun()

    st.markdown("---")

    # 3. 下段: エディタ(左) + コンソール(右)
    col_editor, col_console = st.columns([1, 1])

    with col_editor:
        st.markdown("**SCRIPT EDITOR**")
        # コード入力エリア (session_stateと紐付け)
        new_code = st.text_area(
            "Code", 
            value=st.session_state.user_code, 
            height=300, 
            label_visibility="collapsed",
            key="editor_area"
        )
        # 変更があれば保存
        st.session_state.user_code = new_code
        
        # RUNボタン
        if st.button("▶ RUN SCRIPT (ASYNC)", use_container_width=True):
            with st.spinner("Processing Script..."):
                run_code_logic() # コード実行
            st.rerun() # 画面更新

    with col_console:
        st.markdown("**TERMINAL OUTPUT**")
        # ログ表示 (HTML+CSSでスクロールボックスを再現)
        log_content = st.session_state.console_log
        st.markdown(f'<div class="console-box">{log_content}</div>', unsafe_allow_html=True)
        
        if st.button("CLEAR LOG", key="clr_log"):
            st.session_state.console_log = ">>> Log Cleared.\n"
            st.rerun()
