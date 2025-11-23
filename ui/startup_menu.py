"""
startup_menu.py
----------------

Start screen for the Space Miner Guild - Market Dominion sim.
Player chooses company count and difficulty, then launches the game.
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QSlider, QComboBox, QLineEdit
)
from PyQt6.QtCore import Qt


class StartupMenu(QWidget):
    def __init__(self, start_callback):
        super().__init__()

        self.start_callback = start_callback

        self.setWindowTitle("Space Miner Guild — Simulation Setup")
        self.resize(600, 400)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

        # ------------------------------------------------------
        # Player + Company names
        # ------------------------------------------------------

        name_row = QHBoxLayout()
        layout.addLayout(name_row)

        name_col = QVBoxLayout()
        name_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        name_row.addLayout(name_col)

        player_label = QLabel("Your Name")
        player_label.setStyleSheet("font-size: 16px; color: #ccc;")
        name_col.addWidget(player_label)
        self.player_name_input = QLineEdit()
        self.player_name_input.setPlaceholderText("Patriot")
        name_col.addWidget(self.player_name_input)

        company_col = QVBoxLayout()
        company_col.setAlignment(Qt.AlignmentFlag.AlignTop)
        name_row.addLayout(company_col)

        company_label = QLabel("Your Company Name")
        company_label.setStyleSheet("font-size: 16px; color: #ccc;")
        company_col.addWidget(company_label)
        self.company_name_input = QLineEdit()
        self.company_name_input.setPlaceholderText("Patriot Airlines")
        company_col.addWidget(self.company_name_input)

        layout.addSpacing(12)

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        title = QLabel("Space Miner Guild")
        subtitle = QLabel("Market Dominion Simulator")

        title.setStyleSheet("""
            font-size: 40px;
            font-weight: bold;
            color: white;
        """)

        subtitle.setStyleSheet("""
            font-size: 20px;
            color: #999;
            margin-bottom: 25px;
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        # ------------------------------------------------------
        # Company Count Selector (5-20 AI competitors)
        # ------------------------------------------------------

        comp_label = QLabel("Number of AI Companies")
        comp_label.setStyleSheet("font-size: 18px; color: #ccc;")
        layout.addWidget(comp_label)

        self.comp_slider = QSlider(Qt.Orientation.Horizontal)
        self.comp_slider.setMinimum(5)
        self.comp_slider.setMaximum(20)
        self.comp_slider.setValue(10)
        self.comp_slider.setTickInterval(1)
        self.comp_slider.setFixedWidth(300)
        layout.addWidget(self.comp_slider)

        self.comp_value = QLabel("10 companies")
        self.comp_value.setStyleSheet("font-size: 16px; color: #bbb;")
        layout.addWidget(self.comp_value)

        self.comp_slider.valueChanged.connect(
            lambda v: self.comp_value.setText(f"{v} AI companies (+ you)")
        )

        # Spacing
        layout.addSpacing(20)

        # ------------------------------------------------------
        # Difficulty Dropdown
        # ------------------------------------------------------

        diff_label = QLabel("Select Difficulty")
        diff_label.setStyleSheet("font-size: 18px; color: #ccc;")
        layout.addWidget(diff_label)

        self.diff_choice = QComboBox()
        self.diff_choice.addItems(["Easy", "Medium", "Hard"])
        self.diff_choice.setFixedWidth(200)
        self.diff_choice.setStyleSheet("""
            font-size: 16px;
            padding: 4px;
        """)

        layout.addWidget(self.diff_choice)

        layout.addSpacing(20)

        # ------------------------------------------------------
        # Start Button
        # ------------------------------------------------------

        start_btn = QPushButton("Start Game")
        start_btn.setStyleSheet("""
            font-size: 18px;
            padding: 8px 20px;
            background-color: #4aa3ff;
            border-radius: 8px;
            color: white;
        """)

        start_btn.clicked.connect(self._start_clicked)
        layout.addWidget(start_btn)

        # Padding
        layout.addSpacing(20)

        # Background Style
        self.setStyleSheet("""
            background-color: #0f0f17;
        """)

    # ------------------------------------------------------
    # Event Handler
    # ------------------------------------------------------

    def _start_clicked(self):
        count = self.comp_slider.value()
        difficulty = self.diff_choice.currentText()
        player_name = self.player_name_input.text().strip() or "Player"
        player_company = self.company_name_input.text().strip() or "Player Corp"

        if self.start_callback:
            self.start_callback(count, difficulty, player_name, player_company)
