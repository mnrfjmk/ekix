import flet as ft
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from flet.matplotlib_chart import MatplotlibChart
import traceback
from io import StringIO

# Matplotlibのバックエンドを非対話型に設定
matplotlib.use("svg")

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
# 1. LOGIC CLASS (Model)
# ==========================================
class ChartConfig:
    def __init__(self):
        self.symbols = ["USDJPY=X", "EURUSD=X", "GBPUSD=X", "GC=F", "BTC-USD", "^N225"]
        self.sym_idx = 0
        self.timeframes = ["1m", "5m", "15m", "1h", "1d"]
        self.tf_idx = 3 # 1h
        self.period = "5d"

    @property
    def current_symbol(self): return self.symbols[self.sym_idx]
    @property
    def current_tf(self): return self.timeframes[self.tf_idx]

state = ChartConfig()

# ==========================================
# 2. MAIN APP UI (Flet)
# ==========================================
def main(page: ft.Page):
    # --- Page Config (Tkinterのroot設定に相当) ---
    page.title = "eKIX PRO | Integrated Quant Environment"
    page.bgcolor = COLOR_BG
    page.padding = 0
    page.spacing = 0
    page.theme_mode = ft.ThemeMode.DARK
    
    # 状態変数
    console_log = StringIO()
    
    # --- Helper: Print to Console UI ---
    def safe_print(*args):
        msg = " ".join(map(str, args))
        console_log.write(msg + "\n")
        # コンソールUIの更新
        txt_console.value = console_log.getvalue()
        txt_console.update()

    # --- API: Get Data & Plot ---
    def get_dataframe(symbol, timeframe, period="5d"):
        try:
            df = yf.download(tickers=symbol, interval=timeframe, period=period, progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.droplevel(1)
            return df
        except Exception as e:
            safe_print(f"API ERR: {e}")
            return None

    def update_chart():
        # ステータス更新
        lbl_status.value = " Running..."
        lbl_status.color = COLOR_STYLE_ORANGE
        lbl_status.update()
        
        sym = state.current_symbol
        tf = state.current_tf
        safe_print(f"Loading: {sym} / {tf}...")

        df = get_dataframe(sym, tf, state.period)

        if df is not None:
            # Matplotlib Figure作成
            fig, ax = mpf.plot(
                df, type='candle', 
                style=mpf.make_mpf_style(base_mpf_style='nightclouds', facecolor='#000000', figcolor='#000000'),
                volume=True, 
                mav=(20, 50), 
                title=f"\n{sym} [{tf}]",
                returnfig=True,
                figsize=(10, 6),
                tight_layout=True
            )
            # Fletのチャートコンポーネントを更新
            chart_container.content = MatplotlibChart(fig, expand=True, transparent=True)
            chart_container.update()
            safe_print("Chart Updated.")
        else:
            safe_print("No Data Found.")
            chart_container.content = ft.Text("NO DATA", color="white")
            chart_container.update()

        lbl_status.value = " Ready"
        lbl_status.color = "#888888"
        lbl_status.update()

    # --- UI Components ---

    # [A] Header
    header = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text(" eKIX PRO ", color="white", weight=ft.FontWeight.BOLD),
                bgcolor=COLOR_HEADER_RED,
                padding=5,
            ),
            ft.Text(" WEB TERMINAL ENV", color="#666666", size=12, weight=ft.FontWeight.BOLD),
            ft.Container(expand=True), # Spacer
            ft.Text("● LIVE ", color=COLOR_STYLE_ORANGE, size=12),
        ], alignment=ft.MainAxisAlignment.START, spacing=0),
        bgcolor="#111111",
        height=30,
        border=ft.border.only(bottom=ft.BorderSide(2, COLOR_HEADER_RED))
    )

    # [B] Chart Area (Tkinter Frame + MatplotlibCanvas)
    chart_container = ft.Container(
        content=ft.Text("Initializing...", color="#333"),
        bgcolor=COLOR_BG,
        expand=3, # 画面比率 3
        border=ft.border.all(1, "#333333"),
        alignment=ft.alignment.center
    )

    # [C] Right Panel (Tkinter Frame)
    def on_cycle_sym(e):
        state.sym_idx = (state.sym_idx + 1) % len(state.symbols)
        update_chart()
    
    def on_cycle_tf(e):
        state.tf_idx = (state.tf_idx + 1) % len(state.timeframes)
        update_chart()

    def on_refresh(e):
        update_chart()

    def create_btn(text, on_click):
        return ft.Container(
            content=ft.Text(text, color="black", weight=ft.FontWeight.BOLD, size=12),
            bgcolor=COLOR_STYLE_ORANGE,
            padding=5,
            margin=ft.margin.only(bottom=5),
            on_click=on_click,
            border=ft.border.all(1, "#222"),
            alignment=ft.alignment.center_left,
            height=30
        )

    panel = ft.Container(
        content=ft.Column([
            ft.Text("COMMAND PANEL", color=COLOR_STYLE_ORANGE, weight=ft.FontWeight.BOLD, size=12),
            ft.Divider(color="#333"),
            create_btn("Symbol: Rotate", on_cycle_sym),
            create_btn("TimeFrame: Rotate", on_cycle_tf),
            ft.Container(height=20),
            create_btn("Force Refresh", on_refresh),
        ], spacing=0),
        bgcolor=COLOR_PANEL_BG,
        expand=1, # 画面比率 1
        padding=10,
        border=ft.border.all(1, "#333333")
    )

    # [D] Toolbar
    lbl_status = ft.Text(" Ready", color="#888888", size=12, weight=ft.FontWeight.BOLD)
    
    def on_run_async(e):
        # 簡易的なスクリプト実行エミュレーション
        code = txt_editor.value
        safe_print(">>> Executing Script...")
        # ここでexec(code)も可能ですが、デモのためチャート更新を呼びます
        update_chart()

    toolbar = ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text("▶ RUN ASYNC", color="black", weight=ft.FontWeight.BOLD, size=11),
                bgcolor=COLOR_STYLE_ORANGE,
                padding=ft.padding.symmetric(horizontal=10, vertical=5),
                on_click=on_run_async,
            ),
            lbl_status
        ]),
        bgcolor="#151515",
        height=35,
        border=ft.border.symmetric(horizontal=ft.BorderSide(0), vertical=ft.BorderSide(1, "#333")),
        padding=ft.padding.only(left=5)
    )

    # [E] Editor & Console
    # TkinterのTextウィジェットの再現
    txt_editor = ft.TextField(
        value= """# eKIX Logic Script
import pandas as pd

def main():
    print("Hello from Flet!")
    # app.update_chart() call logic here
""",
        multiline=True,
        text_style=ft.TextStyle(font_family="Consolas", color=COLOR_STYLE_TEXT_ORANGE, size=13),
        bgcolor="#080808",
        border_color="transparent",
        expand=True,
        cursor_color="white"
    )

    txt_console = ft.TextField(
        value=">>> System Initialized.\n",
        multiline=True,
        read_only=True,
        text_style=ft.TextStyle(font_family="Consolas", color=COLOR_STYLE_TEXT_ORANGE, size=13),
        bgcolor="#080808",
        border_color="transparent",
        expand=True
    )

    editor_area = ft.Container(
        content=txt_editor,
        bgcolor="#080808",
        expand=1,
        border=ft.border.all(1, "#333")
    )
    
    console_area = ft.Container(
        content=txt_console,
        bgcolor="#080808",
        expand=1,
        border=ft.border.all(1, "#333")
    )

    # ==========================================
    # LAYOUT ASSEMBLY (Grid / PanedWindow再現)
    # ==========================================
    
    # 上半分: チャート(左) + パネル(右)
    top_split = ft.Row([chart_container, panel], expand=5, spacing=0)
    
    # 下半分: エディタ(左) + コンソール(右)
    bottom_split = ft.Row([editor_area, console_area], expand=3, spacing=0)

    # 全体構成
    layout = ft.Column([
        header,
        top_split,
        toolbar,
        bottom_split
    ], expand=True, spacing=0)

    page.add(layout)
    
    # 初期化完了後にチャート描画
    update_chart()

# ローカルWebサーバーとして起動する場合
if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
