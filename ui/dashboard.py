import random
from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QSlider, QTextEdit, QComboBox,
    QTabWidget, QListWidget as QtListWidget, QFrame, QGridLayout, QProgressBar,
    QScrollArea
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap, QColor
import pyqtgraph as pg
from PyQt6.QtCore import QTimer
from core.assets_engine import AssetManager

from charts.candle_plot import CandlestickItem


# --------------------------------------------------------------
#  COMPANY SIDEBAR ENTRY
# --------------------------------------------------------------

def trim_name(name, max_len=18):
    """No truncation now."""
    return name


class CompanyListItem(QWidget):
    def __init__(self, company):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(6, 4, 4, 4)
        layout.setSpacing(10)
        self.setLayout(layout)

        # Compact logo (placeholder if missing)
        logo_label = QLabel()
        if company.logo:
            pix = company.logo.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        else:
            pix = QPixmap(18, 18)
            pix.fill(QColor("#7a8a9e"))  # Grey placeholder
        logo_label.setPixmap(pix)
        logo_label.setFixedSize(20, 20)
        layout.addWidget(logo_label)

        # Name + price
        text_col = QVBoxLayout()
        text_col.setSpacing(0)
        name = QLabel(trim_name(company.name))
        name.setStyleSheet("font-size: 15px; font-weight: 800; color: #e5f5ff;")
        text_col.addWidget(name)

        price = QLabel(f"${company.price:.2f}")
        price.setStyleSheet("font-size: 13px; color: #69f0ff;")
        text_col.addWidget(price)

        float_lbl = QLabel(f"Float: {company.public_float}")
        float_lbl.setStyleSheet("font-size: 12px; color: #9cb9d8;")
        text_col.addWidget(float_lbl)

        owned_lbl = QLabel(f"Owned: {company.player_shares}")
        owned_lbl.setStyleSheet("font-size: 12px; color: #7ef2bf;")
        text_col.addWidget(owned_lbl)

        rating_lbl = QLabel("CEO: --")
        rating_lbl.setStyleSheet("font-size: 12px; color: #ffd479;")
        text_col.addWidget(rating_lbl)

        layout.addLayout(text_col)

        self.price_label = price
        self.float_label = float_lbl
        self.owned_label = owned_lbl
        self.rating_label = rating_lbl
        self.company = company


# --------------------------------------------------------------
#  DASHBOARD
# --------------------------------------------------------------

class CompetitionDashboard(QWidget):
    def __init__(self, companies,
                 buy_callback=None, sell_callback=None, dump_callback=None, offer_callback=None,
                 set_speed_callback=None, asset_purchase_callback=None,
                 pr_callback=None, rd_callback=None, sabotage_callback=None, fortify_callback=None,
                 buy_bot_callback=None, upgrade_bot_callback=None):
        super().__init__()

        self.setWindowTitle("Space Miner Guild — Market Dominion Dashboard")
        self.resize(1650, 950)
        self.setStyleSheet("""
            QWidget {
                background: radial-gradient(circle at 15% 20%, #0b1021 0%, #060912 35%, #04060d 65%);
                color: #dff3ff;
                font-family: 'Orbitron', 'Segoe UI', 'Inter', sans-serif;
                letter-spacing: 0.3px;
            }
            QListWidget {
                background: linear-gradient(145deg, rgba(14,22,40,0.95) 0%, rgba(6,10,22,0.92) 100%);
                border: 1px solid #1e2b46;
                border-radius: 10px;
            }
            QListWidget::item:selected {
                background: rgba(47,142,255,0.2);
                color: #f3fbff;
                border-left: 3px solid #4cf2ff;
            }
            QPushButton {
                border: none;
            }
            QFrame {
                border-radius: 12px;
            }
        """)

        self.companies = companies
        self.selected_company = companies[0]
        self.current_chart_mode = "daily"
        self.cash = 0.0
        self.company_trades = {}
        self.selected_owner_name = None

        # Hooks to controller
        self.buy_callback = buy_callback
        self.sell_callback = sell_callback
        self.dump_callback = dump_callback
        self.offer_callback = offer_callback
        self.set_speed_callback = set_speed_callback
        self.asset_purchase_callback = asset_purchase_callback
        self.pr_callback = pr_callback
        self.rd_callback = rd_callback
        self.sabotage_callback = sabotage_callback
        self.fortify_callback = fortify_callback
        self.offer_premium = 15  # % premium default
        self.asset_purchase_callback = asset_purchase_callback
        self.buy_bot_callback = buy_bot_callback
        self.upgrade_bot_callback = upgrade_bot_callback

        self._build_ui()
        self.refresh_selected_company()

    # ----------------------------------------------------------
    #  UI STRUCTURE
    # ----------------------------------------------------------

    def _build_ui(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        # ======================================================
        #  LEFT SIDEBAR
        # ======================================================
        left = QVBoxLayout()
        title = QLabel("Companies")
        title.setStyleSheet("font-size: 22px; font-weight: 800; margin: 0 0 8px 4px; color: #eaf2ff; letter-spacing: 0.5px;")
        left.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setFixedWidth(360)

        self._sidebar_items = []

        for c in self.companies:
            item = QListWidgetItem()
            item.setSizeHint(QSize(300, 70))
            widget = CompanyListItem(c)
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            self._sidebar_items.append(widget)

        self.list_widget.currentRowChanged.connect(self._select_company)

        left.addWidget(self.list_widget)
        layout.addLayout(left)

        # Tabs container for main content
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #1a2840; background: #05070f; }
            QTabBar::tab {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101a32, stop:1 #0c1224);
                color: #dff3ff;
                padding: 8px 16px;
                margin-right: 4px;
                border: 1px solid #223452;
                border-radius: 8px;
            }
            QTabBar::tab:selected { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1c3f74, stop:1 #215e9c); color: #f5fdff; }
        """)
        layout.addWidget(self.tabs, stretch=1)

        trading_page = QWidget()
        trading_layout = QHBoxLayout()
        trading_layout.setContentsMargins(0, 0, 0, 0)
        trading_page.setLayout(trading_layout)

        # ======================================================
        #  CENTER PANEL (TRADING)
        # ======================================================
        center = QVBoxLayout()
        center.setContentsMargins(18, 18, 18, 18)

        # ---------- Title ----------
        self.header = QLabel()
        self.header.setStyleSheet("font-size: 30px; font-weight: 900; color: #eaf2ff; letter-spacing: 0.4px;")
        center.addWidget(self.header)

        self.subheader = QLabel()
        self.subheader.setStyleSheet("font-size: 16px; color: #8fa2bd; margin-bottom: 12px; letter-spacing: 0.2px;")
        center.addWidget(self.subheader)

        self.owned_info = QLabel()
        self.owned_info.setStyleSheet("font-size: 15px; color: #8ee0a8; margin-bottom: 12px;")
        center.addWidget(self.owned_info)

        # ---------- Clock ----------
        clock_row = QHBoxLayout()
        self.clock_label = QLabel("00:00 UTC")
        self.clock_label.setStyleSheet("font-size: 15px; color: #c7d7f2;")
        clock_row.addWidget(self.clock_label)

        self.quarter_label = QLabel("Q1 Day 1")
        self.quarter_label.setStyleSheet("font-size: 15px; margin-left: 14px; color: #9fb7d8;")
        clock_row.addWidget(self.quarter_label)

        self.cash_label = QLabel("$0")
        self.cash_label.setStyleSheet("font-size: 15px; margin-left: 24px; color: #9cefbc; font-weight: 700;")
        clock_row.addWidget(self.cash_label)

        clock_row.addStretch()
        center.addLayout(clock_row)

        # ---------- Activity Feed + Order Flow ----------
        feed_label = QLabel("Market Activity")
        feed_label.setStyleSheet("font-size: 18px; font-weight: 800; margin-top: 5px; color: #eaf2ff; letter-spacing: 0.4px; text-transform: uppercase;")
        center.addWidget(feed_label)

        feed_row = QHBoxLayout()

        self.feed_box = QTextEdit()
        self.feed_box.setReadOnly(True)
        self.feed_box.setStyleSheet("""
            background-color: rgba(11,17,30,0.92);
            color: #e5f1ff;
            font-size: 14px;
            border: 1px solid #244064;
            border-radius: 12px;
            padding: 10px;
        """)
        self.feed_box.setFixedHeight(140)
        feed_row.addWidget(self.feed_box, 1)

        self.trade_box = QTextEdit()
        self.trade_box.setReadOnly(True)
        self.trade_box.setStyleSheet("""
            background-color: rgba(11,17,30,0.92);
            color: #e5f1ff;
            font-size: 14px;
            border: 1px solid #244064;
            border-radius: 12px;
            padding: 10px;
        """)
        self.trade_box.setFixedHeight(140)
        feed_row.addWidget(self.trade_box, 1)

        center.addLayout(feed_row)

        # ---------- Chart Buttons ----------
        time_row = QHBoxLayout()
        self.btn_daily = QPushButton("Last 30 Days")
        self.btn_quarterly = QPushButton("Last 30 Quarters")

        for b in (self.btn_daily, self.btn_quarterly):
            b.setStyleSheet("""
                padding: 9px 18px;
                font-size: 15px;
                background-color: #0c1322;
                color: #eaf2ff;
                border-radius: 12px;
                border: 1px solid #22324a;
                letter-spacing: 0.3px;
            """)

        self.btn_daily.clicked.connect(lambda: self._switch_chart("daily"))
        self.btn_quarterly.clicked.connect(lambda: self._switch_chart("quarterly"))

        time_row.addWidget(self.btn_daily)
        time_row.addWidget(self.btn_quarterly)
        center.addLayout(time_row)

        # ---------- Chart ----------
        self.chart = pg.PlotWidget()
        self.chart.setBackground("#05080f")
        vb = self.chart.getViewBox()
        vb.setMouseEnabled(False, False)
        vb.setMenuEnabled(False)
        self.chart.hideButtons()
        self.candle_item = None
        center.addWidget(self.chart, stretch=1)

        # ---------- Modifiers Panel ----------
        mod_frame = QFrame()
        mod_frame.setStyleSheet("QFrame { background: #0d1424; border: 1px solid #1f2f4a; border-radius: 10px; }")
        mod_layout = QHBoxLayout()
        mod_layout.setContentsMargins(10, 6, 10, 6)
        mod_frame.setLayout(mod_layout)
        self.mod_labels = {}
        for key in ["rating", "assets", "sector", "disruption", "demand", "sentiment", "ext_income"]:
            lbl = QLabel(f"{key.title()}: --")
            lbl.setStyleSheet("color: #d6e2ff; font-size: 13px;")
            mod_layout.addWidget(lbl)
            self.mod_labels[key] = lbl
        mod_layout.addStretch()
        center.addWidget(mod_frame)

        # ---------- Player Controls ----------
        center.addLayout(self._build_controls())

        trading_layout.addLayout(center, stretch=3)

        # ======================================================
        #  RIGHT PANEL (OWNERSHIP)
        # ======================================================
        right = QVBoxLayout()
        right.setContentsMargins(10, 20, 10, 20)

        own_title = QLabel("Ownership Breakdown")
        own_title.setStyleSheet("font-size: 21px; font-weight: 700; margin-bottom: 10px; color: #e5e7eb;")
        right.addWidget(own_title)

        # Ownership list (clickable, bubble-like)
        self.owner_list = QListWidget()
        self.owner_list.setStyleSheet("""
            QListWidget { background: #0f1525; border: 1px solid #1f2f4a; border-radius: 10px; color: #d6e2ff; padding: 6px; }
            QListWidget::item { margin: 4px; padding: 10px; border: 1px solid #2b3d5c; border-radius: 8px; }
            QListWidget::item:selected { background: #1a2f4f; border: 1px solid #44e3ff; }
        """)
        self.owner_list.itemSelectionChanged.connect(self._select_owner)
        right.addWidget(self.owner_list)

        self.disruption_label = QLabel("∆ Disruption Index: 0%")
        self.disruption_label.setStyleSheet("font-size: 20px; color: #33ff33; margin-top: 25px;")
        right.addWidget(self.disruption_label)

        # Sector events board on main view
        events_frame = QFrame()
        events_frame.setStyleSheet("QFrame { background: #0c1322; border: 1px solid #23324a; border-radius: 10px; }")
        ev_layout = QVBoxLayout()
        ev_layout.setContentsMargins(8, 6, 8, 6)
        events_frame.setLayout(ev_layout)
        ev_label = QLabel("Sector Events")
        ev_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #eaf2ff;")
        ev_layout.addWidget(ev_label)
        self.events_list = QtListWidget()
        self.events_list.setStyleSheet("QListWidget { background: transparent; border: none; color: #d6e2ff; }")
        ev_layout.addWidget(self.events_list)
        events_frame.setFixedHeight(160)
        right.addWidget(events_frame)

        # Owner offer panel
        owner_frame = QFrame()
        owner_frame.setStyleSheet("QFrame { background: #0c1322; border: 1px solid #23324a; border-radius: 10px; }")
        owner_layout = QVBoxLayout()
        owner_layout.setContentsMargins(10, 8, 10, 8)
        owner_frame.setLayout(owner_layout)
        owner_label = QLabel("Owner Actions")
        owner_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #eaf2ff;")
        owner_layout.addWidget(owner_label)
        self.owner_target_label = QLabel("Select an owner")
        self.owner_target_label.setStyleSheet("font-size: 13px; color: #d6e2ff;")
        owner_layout.addWidget(self.owner_target_label)
        self.owner_offer_slider = QSlider(Qt.Orientation.Horizontal)
        self.owner_offer_slider.setMinimum(1)
        self.owner_offer_slider.setMaximum(1)
        self.owner_offer_slider.valueChanged.connect(self._update_owner_offer_label)
        owner_layout.addWidget(self.owner_offer_slider)
        self.owner_offer_label = QLabel("0 shares")
        self.owner_offer_label.setStyleSheet("font-size: 12px; color: #9fb7d8;")
        owner_layout.addWidget(self.owner_offer_label)

        self.owner_premium_slider = QSlider(Qt.Orientation.Horizontal)
        self.owner_premium_slider.setMinimum(0)
        self.owner_premium_slider.setMaximum(50)
        self.owner_premium_slider.setValue(15)
        self.owner_premium_slider.valueChanged.connect(lambda v: self.owner_premium_label.setText(f"Premium: {v}%"))
        owner_layout.addWidget(self.owner_premium_slider)
        self.owner_premium_label = QLabel("Premium: 15%")
        self.owner_premium_label.setStyleSheet("font-size: 12px; color: #9fb7d8;")
        owner_layout.addWidget(self.owner_premium_label)

        self.owner_offer_btn = QPushButton("Send Offer")
        self.owner_offer_btn.setStyleSheet("""
            background-color: #8b6bff;
            color: #05070f;
            padding: 8px 10px;
            border-radius: 8px;
        """)
        self.owner_offer_btn.clicked.connect(self._do_owner_offer)
        owner_layout.addWidget(self.owner_offer_btn)

        right.addWidget(owner_frame)

        trading_layout.addLayout(right, stretch=1)

        # ------------------------------------------------------
        # Assets tab layout
        # ------------------------------------------------------
        assets_page = QWidget()
        assets_layout = QVBoxLayout()
        assets_layout.setContentsMargins(18, 18, 18, 18)
        assets_page.setLayout(assets_layout)

        assets_title = QLabel("Assets & Expansion")
        assets_title.setStyleSheet("font-size: 24px; font-weight: 900; color: #eaf2ff; letter-spacing: 0.4px;")
        assets_layout.addWidget(assets_title)

        self.ceo_rating_label = QLabel("CEO Rating: 0")
        self.ceo_rating_label.setStyleSheet("font-size: 16px; color: #9fe6ff;")
        assets_layout.addWidget(self.ceo_rating_label)

        self.asset_value_label = QLabel("Asset Value: $0 | Daily Income: $0")
        self.asset_value_label.setStyleSheet("font-size: 15px; color: #d6e2ff;")
        assets_layout.addWidget(self.asset_value_label)

        self.external_income_label = QLabel("External Income (last tick): $0")
        self.external_income_label.setStyleSheet("font-size: 14px; color: #9fe6ff;")
        assets_layout.addWidget(self.external_income_label)

        self.asset_cash_label = QLabel("Liquidity: $0")
        self.asset_cash_label.setStyleSheet("font-size: 14px; color: #8ee0a8;")
        assets_layout.addWidget(self.asset_cash_label)

        list_frame = QFrame()
        list_frame.setStyleSheet("QFrame { background: #0b1222; border: 1px solid #1f2f4a; border-radius: 14px; }")
        list_layout = QVBoxLayout()
        list_layout.setContentsMargins(14, 14, 14, 14)
        list_frame.setLayout(list_layout)
        assets_layout.addWidget(list_frame, stretch=1)

        header = QLabel("Fleet & Holdings")
        header.setStyleSheet("font-size: 15px; font-weight: 800; color: #dce6ff; letter-spacing: 0.3px;")
        list_layout.addWidget(header)

        # Player cards grid
        self.asset_grid = QGridLayout()
        self.asset_grid.setHorizontalSpacing(10)
        self.asset_grid.setVerticalSpacing(10)
        list_layout.addLayout(self.asset_grid)

        # Rivals compact list with scroll
        rival_frame = QFrame()
        rival_frame.setStyleSheet("QFrame { background: #0d1528; border: 1px solid #1f2f4a; border-radius: 10px; }")
        rival_layout = QVBoxLayout()
        rival_layout.setContentsMargins(10, 8, 10, 8)
        rival_frame.setLayout(rival_layout)
        rival_label = QLabel("Rival Fleets")
        rival_label.setStyleSheet("font-size: 14px; font-weight: 700; color: #9fe6ff;")
        rival_layout.addWidget(rival_label)
        self.rival_list = QtListWidget()
        self.rival_list.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #d6e2ff; }
            QListWidget::item { margin: 6px 0; }
        """)
        rival_scroll = QScrollArea()
        rival_scroll.setWidgetResizable(True)
        holder = QWidget()
        holder_layout = QVBoxLayout()
        holder_layout.setContentsMargins(0, 0, 0, 0)
        holder_layout.addWidget(self.rival_list)
        holder.setLayout(holder_layout)
        rival_scroll.setWidget(holder)
        rival_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        rival_layout.addWidget(rival_scroll)
        list_layout.addWidget(rival_frame)

        asset_buttons = QHBoxLayout()
        for label, cfg in AssetManager.ASSET_TYPES.items():
            btn = QPushButton(f"{label} (${cfg['cost']:,.0f})")
            btn.setStyleSheet("""
                background-color: #1f2e4a;
                color: #eaf2ff;
                padding: 10px 12px;
                border-radius: 10px;
                border: 1px solid #2d3d5f;
            """)
            btn.clicked.connect(lambda _, t=label: self._do_buy_asset(t))
            asset_buttons.addWidget(btn)
        assets_layout.addLayout(asset_buttons)

        # Add tabs
        self.tabs.addTab(trading_page, "Trading")
        self.tabs.addTab(assets_page, "Assets")

        # Reports tab
        reports_page = QWidget()
        reports_layout = QVBoxLayout()
        reports_layout.setContentsMargins(18, 18, 18, 18)
        reports_page.setLayout(reports_layout)

        reports_title = QLabel("Financial Reports")
        reports_title.setStyleSheet("font-size: 24px; font-weight: 900; color: #eaf2ff; letter-spacing: 0.4px;")
        reports_layout.addWidget(reports_title)

        self.reports_list = QtListWidget()
        self.reports_list.setStyleSheet("""
            QListWidget { background: #0c1325; border: 1px solid #1a2840; border-radius: 10px; color: #d6e2ff; }
            QListWidget::item { margin: 6px; padding: 10px; }
        """)
        reports_layout.addWidget(self.reports_list, stretch=1)

        dividends_label = QLabel("Profit Streams (dividends from holdings)")
        dividends_label.setStyleSheet("font-size: 16px; font-weight: 800; color: #9fe6ff; margin-top: 8px;")
        reports_layout.addWidget(dividends_label)

        # Dividends grid inside a scroll area (2 columns)
        self.dividends_grid = QGridLayout()
        self.dividends_grid.setContentsMargins(8, 8, 8, 8)
        self.dividends_grid.setHorizontalSpacing(8)
        self.dividends_grid.setVerticalSpacing(8)
        grid_host = QWidget()
        grid_host.setLayout(self.dividends_grid)

        self.dividends_scroll = QScrollArea()
        self.dividends_scroll.setWidgetResizable(True)
        self.dividends_scroll.setWidget(grid_host)
        self.dividends_scroll.setStyleSheet("QScrollArea { border: 1px solid #1a2840; border-radius: 10px; background: #0c1325; }")
        reports_layout.addWidget(self.dividends_scroll, stretch=1)

        self.tabs.addTab(reports_page, "Reports")

        # Automation tab
        auto_page = QWidget()
        auto_layout = QVBoxLayout()
        auto_layout.setContentsMargins(18, 18, 18, 18)
        auto_page.setLayout(auto_layout)

        auto_title = QLabel("Automation")
        auto_title.setStyleSheet("font-size: 24px; font-weight: 900; color: #eaf2ff; letter-spacing: 0.4px;")
        auto_layout.addWidget(auto_title)

        self.bot_status = QLabel("Bot: inactive")
        self.bot_status.setStyleSheet("font-size: 15px; color: #9fe6ff;")
        auto_layout.addWidget(self.bot_status)

        btn_row = QHBoxLayout()
        self.btn_buy_bot = QPushButton("Buy Automation Bot ($15k)")
        self.btn_buy_bot.setStyleSheet("background:#1f2e4a; color:#eaf2ff; padding:10px; border-radius:10px; border:1px solid #2d3d5f;")
        self.btn_buy_bot.clicked.connect(lambda: self.buy_bot_callback() if self.buy_bot_callback else None)
        btn_row.addWidget(self.btn_buy_bot)

        self.btn_upg_speed = QPushButton("Upgrade Speed")
        self.btn_upg_speed.clicked.connect(lambda: self.upgrade_bot_callback("speed") if self.upgrade_bot_callback else None)
        self.btn_upg_speed.setStyleSheet("background:#27435f; color:#d6e2ff; padding:8px; border-radius:10px;")
        btn_row.addWidget(self.btn_upg_speed)

        self.btn_upg_acc = QPushButton("Upgrade Accuracy")
        self.btn_upg_acc.clicked.connect(lambda: self.upgrade_bot_callback("accuracy") if self.upgrade_bot_callback else None)
        self.btn_upg_acc.setStyleSheet("background:#27435f; color:#d6e2ff; padding:8px; border-radius:10px;")
        btn_row.addWidget(self.btn_upg_acc)

        self.btn_upg_size = QPushButton("Upgrade Size")
        self.btn_upg_size.clicked.connect(lambda: self.upgrade_bot_callback("size") if self.upgrade_bot_callback else None)
        self.btn_upg_size.setStyleSheet("background:#27435f; color:#d6e2ff; padding:8px; border-radius:10px;")
        btn_row.addWidget(self.btn_upg_size)
        auto_layout.addLayout(btn_row)

        self.bot_history = QtListWidget()
        self.bot_history.setStyleSheet("""
            QListWidget { background: #0c1325; border: 1px solid #1a2840; border-radius: 10px; color: #d6e2ff; }
            QListWidget::item { margin: 4px; padding: 6px; }
        """)
        auto_layout.addWidget(self.bot_history, stretch=1)

        self.bot_cost_label = QLabel("Upgrades: Speed/Accuracy/Size cost scales with level.")
        self.bot_cost_label.setStyleSheet("font-size: 13px; color: #9ba5b5;")
        auto_layout.addWidget(self.bot_cost_label)

        self.tabs.addTab(auto_page, "Automation")

        # Set default selection after UI elements exist
        self.list_widget.setCurrentRow(0)
        self.selected_owner_name = None

    # ----------------------------------------------------------
    #  PLAYER CONTROLS
    # ----------------------------------------------------------

    def _build_controls(self):
        layout = QVBoxLayout()

        label = QLabel("Trade Controls")
        label.setStyleSheet("font-size: 20px; font-weight: 800; color: #eaf2ff; letter-spacing: 0.5px; text-transform: uppercase;")
        layout.addWidget(label)

        # Buy/Sell sliders
        srow = QHBoxLayout()
        buy_col = QVBoxLayout()
        sell_col = QVBoxLayout()

        buy_label = QLabel("Buy")
        buy_label.setStyleSheet("font-size: 13px; color: #7fd8ff; font-weight: 700;")
        buy_col.addWidget(buy_label)
        self.buy_slider = QSlider(Qt.Orientation.Horizontal)
        self.buy_slider.setMinimum(1)
        self.buy_slider.setMaximum(100)
        self.buy_slider.setValue(1)
        self.buy_slider.valueChanged.connect(self._update_trade_costs)
        buy_col.addWidget(self.buy_slider)
        self.buy_slider_label = QLabel("1 shares")
        buy_col.addWidget(self.buy_slider_label)

        sell_label = QLabel("Sell")
        sell_label.setStyleSheet("font-size: 13px; color: #ff9b8f; font-weight: 700;")
        sell_col.addWidget(sell_label)
        self.sell_slider = QSlider(Qt.Orientation.Horizontal)
        self.sell_slider.setMinimum(1)
        self.sell_slider.setMaximum(100)
        self.sell_slider.setValue(1)
        self.sell_slider.valueChanged.connect(self._update_trade_costs)
        sell_col.addWidget(self.sell_slider)
        self.sell_slider_label = QLabel("1 shares")
        sell_col.addWidget(self.sell_slider_label)

        srow.addLayout(buy_col)
        srow.addLayout(sell_col)
        layout.addLayout(srow)

        self.trade_cost_label = QLabel("Est. Buy: $0 | Sell: $0 | Dump: $0")
        self.trade_cost_label.setStyleSheet("font-size: 13px; color: #9fb7d8;")
        layout.addWidget(self.trade_cost_label)

        # Buttons
        brow = QHBoxLayout()

        self.btn_buy = QPushButton("Buy")
        self.btn_buy.setStyleSheet("""
            background-color: #2dd782;
            padding: 10px 18px;
            font-size: 16px;
            font-weight: 700;
            color: #041221;
            border-radius: 10px;
        """)

        self.btn_sell = QPushButton("Sell")
        self.btn_sell.setStyleSheet("""
            background-color: #33b1ff;
            padding: 10px 18px;
            font-size: 16px;
            font-weight: 700;
            color: #041221;
            border-radius: 10px;
        """)

        self.btn_dump = QPushButton("Dump (Panic)")
        self.btn_dump.setStyleSheet("""
            background-color: #ff6b5c;
            padding: 10px 18px;
            font-size: 16px;
            font-weight: 700;
            color: #041221;
            border-radius: 10px;
        """)

        self.btn_buy.clicked.connect(self._do_buy)
        self.btn_sell.clicked.connect(self._do_sell)
        self.btn_dump.clicked.connect(self._do_dump)

        brow.addWidget(self.btn_buy)
        brow.addWidget(self.btn_sell)
        brow.addWidget(self.btn_dump)

        layout.addLayout(brow)

        # Offer row
        offer_row = QHBoxLayout()
        self.offer_target = QComboBox()
        self.offer_target.setStyleSheet("""
            background-color: #0f1b2f;
            color: #eaf2ff;
            padding: 6px;
            border: 1px solid #23324a;
            border-radius: 8px;
        """)
        offer_row.addWidget(self.offer_target, 1)

        self.offer_premium_slider = QSlider(Qt.Orientation.Horizontal)
        self.offer_premium_slider.setMinimum(0)
        self.offer_premium_slider.setMaximum(50)
        self.offer_premium_slider.setValue(15)
        self.offer_premium_slider.setStyleSheet("padding: 4px;")
        self.offer_premium_slider.valueChanged.connect(lambda v: self._update_offer_premium(v))
        offer_row.addWidget(self.offer_premium_slider, 2)

        self.btn_offer = QPushButton("Make Offer")
        self.btn_offer.setStyleSheet("""
            background-color: #8b6bff;
            padding: 8px 14px;
            font-size: 15px;
            font-weight: 700;
            color: #05070f;
            border-radius: 10px;
        """)
        self.btn_offer.clicked.connect(self._do_offer)
        offer_row.addWidget(self.btn_offer)

        layout.addLayout(offer_row)

        # Strategy row
        strat_row = QHBoxLayout()

        self.btn_pr = QPushButton("PR Campaign")
        self.btn_pr.setStyleSheet("""
            background-color: #2ac1a0;
            color: #041221;
            padding: 8px 12px;
            border-radius: 8px;
        """)
        self.btn_pr.clicked.connect(self._do_pr)
        strat_row.addWidget(self.btn_pr)

        self.btn_rd = QPushButton("R&D Sprint")
        self.btn_rd.setStyleSheet("""
            background-color: #5c7bff;
            color: #041221;
            padding: 8px 12px;
            border-radius: 8px;
        """)
        self.btn_rd.clicked.connect(self._do_rd)
        strat_row.addWidget(self.btn_rd)

        self.btn_sabotage = QPushButton("Sabotage")
        self.btn_sabotage.setStyleSheet("""
            background-color: #ff7b7b;
            color: #041221;
            padding: 8px 12px;
            border-radius: 8px;
        """)
        self.btn_sabotage.clicked.connect(self._do_sabotage)
        strat_row.addWidget(self.btn_sabotage)

        self.btn_fortify = QPushButton("Fortify")
        self.btn_fortify.setStyleSheet("""
            background-color: #8b6bff;
            color: #041221;
            padding: 8px 12px;
            border-radius: 8px;
        """)
        self.btn_fortify.clicked.connect(self._do_fortify)
        strat_row.addWidget(self.btn_fortify)

        layout.addLayout(strat_row)

        # Speed toggle
        self.btn_speed = QPushButton("Normal Speed")
        self.btn_speed.setCheckable(True)
        self.btn_speed.clicked.connect(self._toggle_speed)
        self.btn_speed.setStyleSheet("""
            background-color: #142035;
            color: #eaf2ff;
            padding: 8px 14px;
            margin-top: 10px;
            border: 1px solid #23324a;
            border-radius: 10px;
        """)
        layout.addWidget(self.btn_speed)

        return layout

    # ----------------------------------------------------------
    #  FEED HANDLING
    # ----------------------------------------------------------

    def push_feed(self, text, color="#cccccc"):
        """Adds an entry to the activity feed."""
        self.feed_box.append(f"<span style='color:{color};'>{text}</span>")
        self.feed_box.verticalScrollBar().setValue(
            self.feed_box.verticalScrollBar().maximum()
        )

    def log_trade(self, company_name, text, color="#cccccc"):
        """Store a per-company trade entry."""
        if company_name not in self.company_trades:
            self.company_trades[company_name] = []
        self.company_trades[company_name].append((text, color))
        # keep last 50
        if len(self.company_trades[company_name]) > 50:
            self.company_trades[company_name] = self.company_trades[company_name][-50:]
        # if this company is selected, update box
        if self.selected_company and self.selected_company.name == company_name:
            self._refresh_trade_box()

    # ----------------------------------------------------------
    #  ACTION HANDLING
    # ----------------------------------------------------------

    def _do_buy(self):
        s = self.buy_slider.value()
        if self.buy_callback:
            self.buy_callback(self.selected_company, s)

    def _do_sell(self):
        s = self.sell_slider.value()
        if self.sell_callback:
            self.sell_callback(self.selected_company, s)

    def _do_dump(self):
        s = self.sell_slider.value()
        if self.dump_callback:
            self.dump_callback(self.selected_company, s)

    def _do_offer(self):
        s = self.sell_slider.value()
        target = self.offer_target.currentText()
        if self.offer_callback and target:
            self.btn_offer.setEnabled(False)
            self.offer_cooldown_ms = 3000
            self.offer_callback(self.selected_company, target, s, self.offer_premium)
            QTimer.singleShot(self.offer_cooldown_ms, lambda: self.btn_offer.setEnabled(True))

    def _do_owner_offer(self):
        items = self.owner_list.selectedItems()
        if not items or not self.offer_callback:
            return
        target = items[0].text().split(":")[0]
        shares = self.owner_offer_slider.value()
        premium = self.owner_premium_slider.value()
        self.offer_callback(self.selected_company, target, shares, premium)

    def _do_pr(self):
        if self.pr_callback:
            self.pr_callback()

    def _do_rd(self):
        if self.rd_callback:
            self.rd_callback()

    def _do_sabotage(self):
        if self.sabotage_callback:
            self.sabotage_callback(self.selected_company)

    def _do_fortify(self):
        if self.fortify_callback:
            self.fortify_callback(self.selected_company)

    def _do_buy_asset(self, asset_type):
        if self.asset_purchase_callback:
            self.asset_purchase_callback(asset_type)

    # ----------------------------------------------------------

    def _toggle_speed(self):
        fast = self.btn_speed.isChecked()
        self.btn_speed.setText("Fast Speed" if fast else "Normal Speed")
        if self.set_speed_callback:
            self.set_speed_callback(fast)

    # ----------------------------------------------------------
    #  COMPANY SELECTION
    # ----------------------------------------------------------

    def _select_company(self, index):
        if index == -1:
            return
        self.selected_company = self.companies[index]
        self.refresh_selected_company()

    def _select_owner(self):
        c = self.selected_company
        items = self.owner_list.selectedItems()
        if not items:
            if self.selected_owner_name:
                for i in range(self.owner_list.count()):
                    if self.owner_list.item(i).text().startswith(self.selected_owner_name + ":"):
                        self.owner_list.setCurrentRow(i)
                        return
            self.owner_target_label.setText("Select an owner")
            self.owner_offer_slider.setMaximum(1)
            self.owner_offer_slider.setValue(1)
            return
        text = items[0].text()
        name = text.split(":")[0]
        self.owner_target_label.setText(f"Target: {name}")
        self.selected_owner_name = name
        if name == "You":
            max_shares = c.player_shares
        elif name == "Public Float":
            max_shares = c.public_float
        else:
            max_shares = c.ai_owners.get(name, 0)
        max_shares = max(1, int(max_shares))
        self.owner_offer_slider.setMaximum(max_shares)
        self.owner_offer_slider.setValue(min(self.owner_offer_slider.value(), max_shares))
        self._update_owner_offer_label()

    # ----------------------------------------------------------
    #  UI UPDATES
    # ----------------------------------------------------------

    def refresh_selected_company(self):
        c = self.selected_company
        self.header.setText(c.name)
        self.subheader.setText(f"{c.sector} — ${c.price:.2f}")
        self.owned_info.setText(f"You own {c.player_shares} • Float {c.public_float}")

        self._rebuild_ownership()
        self.update_disruption_ui()
        self._update_slider_limits()
        self._update_trade_costs()
        self._refresh_trade_box()

        self._update_chart(self.current_chart_mode)

    def _switch_chart(self, mode):
        self.current_chart_mode = mode
        self._update_chart(mode)

    def _update_chart(self, mode):
        if not hasattr(self, "chart") or self.chart is None:
            return
        if not self.isVisible():
            return

        c = self.selected_company
        base = c.daily_candles if mode == "daily" else c.quarterly_candles

        if not base:
            return

        # Append forming candle for intraday view (daily only)
        if mode == "daily":
            forming = type(base[0])(
                round(c.current_open, 2),
                round(c.current_high, 2),
                round(c.current_low, 2),
                round(c.current_close, 2),
            )
            data = base + [forming]
        else:
            data = base

        try:
            # Remove previous candle item without clearing axes to avoid pyqtgraph axis deletion
            if getattr(self, "candle_item", None):
                try:
                    self.chart.removeItem(self.candle_item)
                except RuntimeError:
                    pass
            item = CandlestickItem(data)
            self.chart.addItem(item)
            self.candle_item = item

            highs = [x.high for x in data]
            lows = [x.low for x in data]

            self.chart.setYRange(min(lows) - 1, max(highs) + 1)
            self.chart.setXRange(0, len(data))
        except RuntimeError:
            # Widget might be gone during shutdown; ignore
            return

    def update_chart_only(self):
        """Refreshes candles every tick without changing mode."""
        if not self.isVisible():
            return
        try:
            self._update_chart(self.current_chart_mode)
        except RuntimeError:
            return

    def _rebuild_ownership(self):
        # Populate ownership list
        self.owner_list.clear()
        c = self.selected_company
        parts = [("You", c.player_shares)]

        for name, amt in sorted(c.ai_owners.items(), key=lambda x: x[1], reverse=True):
            parts.append((name, amt))

        parts.append(("Public Float", c.public_float))

        for name, amt in parts:
            item = QListWidgetItem(f"{name}: {amt} shares")
            self.owner_list.addItem(item)
            if name == self.selected_owner_name:
                item.setSelected(True)
        if self.selected_owner_name is None and self.owner_list.count() > 0:
            self.owner_list.setCurrentRow(0)

        # Update offer targets
        self.offer_target.clear()
        ai_names = [name for name, amt in c.ai_owners.items() if amt > 0]
        if ai_names:
            self.offer_target.addItems(ai_names)
            self.btn_offer.setEnabled(True)
        else:
            self.offer_target.addItem("No AI holders")
            self.btn_offer.setEnabled(False)

    def _update_slider_limits(self):
        c = self.selected_company
        affordable = int(self.cash / c.price) if c.price > 0 else 0
        max_buyable = max(1, min(int(c.public_float), affordable))
        max_sellable = max(1, int(c.player_shares))
        if self.buy_slider.maximum() != max_buyable:
            self.buy_slider.setMaximum(max_buyable)
        if self.buy_slider.value() > max_buyable:
            self.buy_slider.setValue(max_buyable)
        if self.sell_slider.maximum() != max_sellable:
            self.sell_slider.setMaximum(max_sellable)
        if self.sell_slider.value() > max_sellable:
            self.sell_slider.setValue(max_sellable)
        self.buy_slider_label.setText(f"{self.buy_slider.value()} shares")
        self.sell_slider_label.setText(f"{self.sell_slider.value()} shares")
        self._update_trade_costs()

    def update_disruption_ui(self):
        if not hasattr(self, "disruption_engine"):
            return

        txt = self.disruption_engine.get_display_text()
        col = self.disruption_engine.get_color_for_disruption()
        self.disruption_label.setText(txt)
        self.disruption_label.setStyleSheet(f"font-size: 20px; color: {col};")

    def update_price_display(self):
        for w in self._sidebar_items:
            c = w.company
            w.price_label.setText(f"${c.price:.2f}")
            w.float_label.setText(f"Float: {c.public_float}")
            w.owned_label.setText(f"Owned: {c.player_shares}")
            if hasattr(self, "ai_ratings"):
                rating = self.ai_ratings.get(c.name, "--")
                if getattr(c, "is_player", False):
                    rating = f"{self.player_rating}" if hasattr(self, "player_rating") else "--"
                w.rating_label.setText(f"CEO: {rating}")
        self._update_slider_limits()

    def set_clock(self, t, q):
        self.clock_label.setText(t)
        self.quarter_label.setText(q)

    def set_disruption_engine(self, engine):
        self.disruption_engine = engine

    def set_cash(self, cash):
        self.cash = cash
        self.cash_label.setText(f"${cash:,.2f}")
        self._update_slider_limits()

    def set_asset_manager(self, asset_manager):
        self.asset_manager = asset_manager

    def set_company_ratings(self, player_rating, ai_ratings):
        self.player_rating = player_rating
        self.ai_ratings = ai_ratings
        self.update_price_display()

    def _update_offer_premium(self, value):
        self.offer_premium = value
        self.btn_offer.setText(f"Offer (+{value}%)")
        self._update_trade_costs()

    def set_modifiers_display(self, rating, asset_boost, sector_boost, disruption, demand, sentiment, ext_income):
        self.mod_labels["rating"].setText(f"Rating: {rating}")
        self.mod_labels["assets"].setText(f"Assets: {asset_boost:.2f}")
        self.mod_labels["sector"].setText(f"Sector: {sector_boost:.2f}")
        self.mod_labels["disruption"].setText(f"Disruption: {disruption:.1f}%")
        self.mod_labels["demand"].setText(f"Demand: {demand:+.2f}")
        self.mod_labels["sentiment"].setText(f"Sentiment: {sentiment:+.2f}")
        self.mod_labels["ext_income"].setText(f"Ext. income: ${ext_income:,.0f}")

    def _refresh_trade_box(self):
        if not self.selected_company:
            return
        self.trade_box.clear()
        entries = self.company_trades.get(self.selected_company.name, [])
        for text, color in entries:
            self.trade_box.append(f"<span style='color:{color};'>{text}</span>")
        self.trade_box.verticalScrollBar().setValue(
            self.trade_box.verticalScrollBar().maximum()
        )

    def update_reports(self, reports, dividends=None):
        """Populate reports tab with per-company financial summary and profit streams."""
        self.reports_list.clear()
        # Clear dividends grid
        while self.dividends_grid.count():
            item = self.dividends_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not reports:
            item = QListWidgetItem()
            widget = QLabel("No financial reports yet.")
            widget.setStyleSheet("color: #9ba5b5; padding: 10px;")
            item.setSizeHint(widget.sizeHint())
            self.reports_list.addItem(item)
            self.reports_list.setItemWidget(item, widget)
        else:
            for r in reports:
                item = QListWidgetItem()
                widget = QFrame()
                widget.setStyleSheet("""
                    QFrame { background: #0f1c33; border: 1px solid #2b3d5c; border-radius: 10px; }
                    QLabel { color: #d6e2ff; font-size: 13px; }
                """)
                v = QVBoxLayout()
                v.setContentsMargins(12, 10, 12, 10)
                v.setSpacing(4)
                widget.setLayout(v)
                header = QLabel(f"<b>{r['name']}</b> — price ${r['price']:.2f} | float {r['float']} | owned {r['owned']}")
                header.setStyleSheet("font-size: 14px; font-weight: 700; color: #eaf2ff;")
                v.addWidget(header)
                body = QLabel(
                    f"Asset income/day: ${r['asset_income']:,.0f} | Dividends paid last tick: ${r['div_paid']:,.0f} | "
                    f"Dividends received last tick: ${r['div_received']:,.0f}"
                )
                body.setWordWrap(True)
                v.addWidget(body)
                # Ensure the row has some height so it doesn't collapse to a thin bar
                widget.setMinimumHeight(64)
                item.setSizeHint(widget.sizeHint())
                self.reports_list.addItem(item)
                self.reports_list.setItemWidget(item, widget)

        # Profit streams (dividends) section
        if dividends is None:
            dividends = {}
        owner_totals = []
        for owner, pairs in dividends.items():
            total = sum(x[1] for x in pairs)
            owner_totals.append((owner, total, pairs))
        owner_totals.sort(key=lambda x: x[1], reverse=True)

        rarity_colors = {
            "player": "#9fe6ff"
        }

        if not owner_totals:
            placeholder = QLabel("No dividend activity yet.")
            placeholder.setStyleSheet("color: #9ba5b5; padding: 8px;")
            self.dividends_grid.addWidget(placeholder, 0, 0)
        else:
            row = col = 0
            for owner, total, pairs in owner_totals:
                widget = QFrame()
                widget.setStyleSheet("""
                    QFrame { background: #0f1c33; border: 1px solid #2b3d5c; border-radius: 10px; }
                    QLabel { color: #d6e2ff; font-size: 12px; }
                """)
                v = QVBoxLayout()
                v.setContentsMargins(10, 6, 10, 6)
                widget.setLayout(v)
                tone = rarity_colors.get(owner, "#d6e2ff")
                title = QLabel(f"<b><span style='color:{tone};'>{owner}</span></b> — income ${total:,.0f}")
                v.addWidget(title)
                lines = [f"{src}: ${amt:,.0f}" for src, amt in pairs]
                detail = QLabel(" | ".join(lines))
                detail.setWordWrap(True)
                v.addWidget(detail)
                self.dividends_grid.addWidget(widget, row, col)
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

    def update_automation(self, bot_state):
        active = bot_state.get("active", False)
        if not active:
            self.bot_status.setText("Bot: inactive")
        else:
            self.bot_status.setText(
                f"Bot: Level {bot_state.get('level',1)} | speed {bot_state.get('speed',1)} | "
                f"accuracy {bot_state.get('accuracy',0):.2f} | size {bot_state.get('size',1.0):.1f} | "
                f"PNL ${bot_state.get('total_pnl',0):,.0f}"
            )
        self.bot_history.clear()
        for entry in bot_state.get("history", []):
            text = f"{entry['result']} {entry['shares']} {entry['name']} buy ${entry['buy']:.2f} / sell ${entry['sell']:.2f} -> {entry['pnl']:+.0f}"
            item = QListWidgetItem(text)
            if entry["result"] == "WIN":
                item.setForeground(QColor("#8ee0a8"))
            else:
                item.setForeground(QColor("#ff8b8b"))
            self.bot_history.addItem(item)
        # Update upgrade button labels with current cost
        if active:
            next_cost = 8000 + bot_state.get("level", 1) * 4000
            self.btn_upg_speed.setText(f"Upgrade Speed (${next_cost:,.0f})")
            self.btn_upg_acc.setText(f"Upgrade Accuracy (${next_cost:,.0f})")
            self.btn_upg_size.setText(f"Upgrade Size (${next_cost:,.0f})")
        else:
            self.btn_upg_speed.setText("Upgrade Speed")
            self.btn_upg_acc.setText("Upgrade Accuracy")
            self.btn_upg_size.setText("Upgrade Size")

    def update_assets_panel(self, cash, portfolio_value, ai_cash=0.0, active_events=None, external_income=0.0, dividends=None):
        if not hasattr(self, "asset_manager"):
            return
        # Clear grids/lists
        while self.asset_grid.count():
            item = self.asset_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rival_list.clear()

        rarity_colors = {
            "Common": "#9fb7d8",
            "Rare": "#9fe6ff",
            "Epic": "#f5d76b",
        }

        def summarize(owner):
            items = self.asset_manager.snapshot(owner)
            if not items:
                return {}, 0, 0
            buckets = {}
            total_income = 0.0
            for a in items:
                bucket = buckets.setdefault(a["type"], {"count": 0, "avg_cond": 0.0, "tiers": {}})
                bucket["count"] += 1
                bucket["avg_cond"] += a["condition"]
                tier = a.get("tier", "Common")
                bucket["tiers"][tier] = bucket["tiers"].get(tier, 0) + 1
                cfg = self.asset_manager.ASSET_TYPES[a["type"]]
                income_this = cfg["income_per_day"] * a["condition"]
                bucket["income"] = bucket.get("income", 0.0) + income_this
                total_income += income_this
            for t, data in buckets.items():
                data["avg_cond"] = (data["avg_cond"] / data["count"]) * 100
            total_val = self.asset_manager.total_value(owner)
            return buckets, total_val, total_income

        # Player cards
        buckets, total_value, daily_income = summarize("player")
        row = col = 0
        for name, data in buckets.items():
            tiers = " ".join([
                f"<span style='color:{rarity_colors.get(t, '#d6e2ff')};'>{t}:{n}</span>"
                for t, n in data["tiers"].items()
            ])
            card = QLabel(f"""
                <b>{name}</b><br>
                Units: {data['count']}<br>
                Tiers: {tiers}<br>
                Avg condition: {data['avg_cond']:.0f}%<br>
                Income/day: ${data.get('income',0):,.0f}
            """)
            card.setStyleSheet("""
                QLabel {
                    background-color: #0f1c33;
                    border: 1px solid #2b3d5c;
                    border-radius: 12px;
                    padding: 8px;
                    color: #d6e2ff;
                    min-width: 180px;
                    max-width: 220px;
                }
            """)
            self.asset_grid.addWidget(card, row, col)
            col += 1
            if col >= 5:
                col = 0
                row += 1

        # Rivals summary
        for owner in self.asset_manager.assets.keys():
            if owner == "player":
                continue
            obuckets, ovalue, oincome = summarize(owner)
            item = QListWidgetItem()
            widget = QFrame()
            widget.setStyleSheet("""
                QFrame { background-color: #0f1c33; border: 1px solid #2b3d5c; border-radius: 10px; }
                QLabel { color: #d6e2ff; font-size: 12px; }
            """)
            v = QVBoxLayout()
            v.setContentsMargins(10, 8, 10, 8)
            widget.setLayout(v)
            title = QLabel(f"<b>{owner}</b> — value ${ovalue:,.0f} | income ${oincome:,.0f}")
            v.addWidget(title)
            lines = []
            for k, n in obuckets.items():
                lines.append(f"{k}: {n['count']} units, income ${n.get('income',0):,.0f}")
            detail = QLabel("<br>".join(lines))
            detail.setWordWrap(True)
            v.addWidget(detail)
            item.setSizeHint(widget.sizeHint())
            self.rival_list.addItem(item)
            self.rival_list.setItemWidget(item, widget)

        # Sector events display
        self.events_list.clear()
        if active_events:
            for ev in active_events:
                tone = "#9fe6ff" if ev.get("drift", 0) > 0 else "#ffcc88"
                self.events_list.addItem(f"{ev['name']} ({ev['sector']}): drift {ev['drift']:+.2f}, vol {ev['vol']:+.2f} ({ev['days_left']}d)")

        rating = self.asset_manager.ceo_rating(cash, portfolio_value)
        self.ceo_rating_label.setText(f"CEO Rating: {rating} | Your Cash: ${cash:,.0f} | AI Treasury: ${ai_cash:,.0f}")
        self.asset_value_label.setText(
            f"Asset Value: ${total_value:,.0f} | Daily Income: ${daily_income:,.0f}"
        )
        self.asset_cash_label.setText(f"Liquidity: ${cash:,.0f}")
        self.external_income_label.setText(f"External Income (last tick): ${external_income:,.0f}")

    def _update_trade_costs(self):
        c = self.selected_company
        buy_shares = self.buy_slider.value() if hasattr(self, "buy_slider") else 1
        sell_shares = self.sell_slider.value() if hasattr(self, "sell_slider") else 1
        buy_cost = c.price * buy_shares
        sell_gain = c.price * sell_shares
        dump_gain = c.price * sell_shares
        self.trade_cost_label.setText(
            f"Est. Buy: ${buy_cost:,.0f} | Sell: ${sell_gain:,.0f} | Dump: ${dump_gain:,.0f}"
        )
        self.btn_buy.setToolTip(f"Buy {buy_shares} shares for ${buy_cost:,.0f}")
        self.btn_sell.setToolTip(f"Sell {sell_shares} shares for ${sell_gain:,.0f}")
        self.btn_dump.setToolTip(f"Dump {sell_shares} shares for ${dump_gain:,.0f}")
        self.btn_offer.setToolTip(f"Offer {sell_shares} shares at {self.offer_premium}% premium")

    def _update_owner_offer_label(self):
        self.owner_offer_label.setText(f"{self.owner_offer_slider.value()} shares")
