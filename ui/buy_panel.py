from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QSpinBox, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt

class BuySellPanel(QWidget):
    def __init__(self, on_buy, on_sell):
        super().__init__()

        self.on_buy = on_buy
        self.on_sell = on_sell

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(layout)

        title = QLabel("Trade Shares")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(title)

        amount_row = QHBoxLayout()
        layout.addLayout(amount_row)

        self.amount = QSpinBox()
        self.amount.setRange(1, 1000000)
        amount_row.addWidget(QLabel("Amount:"))
        amount_row.addWidget(self.amount)

        buy_btn = QPushButton("BUY")
        buy_btn.setStyleSheet("background-color: #4caf50; color: white; font-size: 18px; padding: 8px;")
        buy_btn.clicked.connect(lambda: self.on_buy(self.amount.value()))
        layout.addWidget(buy_btn)

        sell_btn = QPushButton("SELL")
        sell_btn.setStyleSheet("background-color: #e53935; color: white; font-size: 18px; padding: 8px;")
        sell_btn.clicked.connect(lambda: self.on_sell(self.amount.value()))
        layout.addWidget(sell_btn)
