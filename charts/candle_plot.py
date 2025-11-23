from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush
from PyQt6.QtCore import QRectF, QPointF, Qt


class CandlestickItem(QGraphicsItem):
    """
    A clean QGraphicsItem candlestick renderer.
    Compatible with pyqtgraph PlotWidget.
    """

    def __init__(self, candles, candle_width=0.8):
        super().__init__()
        self.candles = candles
        self.candle_width = float(candle_width)

        # Pre-compute bounding rect
        if candles:
            xs = [i for i in range(len(candles))]
            highs = [c.high for c in candles]
            lows = [c.low for c in candles]

            self._bounds = QRectF(
                float(min(xs)) - 1,
                float(min(lows)) - 1,
                float(max(xs)) - float(min(xs)) + 2,
                float(max(highs)) - float(min(lows)) + 2,
            )
        else:
            self._bounds = QRectF(0, 0, 1, 1)

    # ----------------------------------------------------------
    # Required by QGraphicsItem
    # ----------------------------------------------------------

    def boundingRect(self):
        return self._bounds

    # ----------------------------------------------------------
    # Painting
    # ----------------------------------------------------------

    def paint(self, painter: QPainter, option, widget=None):
        if not self.candles:
            return

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        for i, c in enumerate(self.candles):
            self._draw_candle(painter, i, c)

    # ----------------------------------------------------------
    # Draw a single candlestick
    # ----------------------------------------------------------

    def _draw_candle(self, painter: QPainter, index: int, c):
        # Determine color
        up = c.close >= c.open
        color = QColor("#4caf50") if up else QColor("#e53935")

        # Wick Pen
        wick_pen = QPen(color, 0.15)
        painter.setPen(wick_pen)

        # Wick line: use QPointF to avoid float errors
        center_x = float(index) + 0.5
        p1 = QPointF(center_x, float(c.low))
        p2 = QPointF(center_x, float(c.high))
        painter.drawLine(p1, p2)

        # Body
        body_pen = QPen(Qt.PenStyle.NoPen)
        painter.setPen(body_pen)
        painter.setBrush(QBrush(color))

        body_top = float(max(c.open, c.close))
        body_bottom = float(min(c.open, c.close))
        height = max(body_top - body_bottom, 0.05)

        rect = QRectF(
            float(index) + 0.1,  # x
            body_bottom,         # y
            self.candle_width,   # width
            height               # height
        )

        painter.drawRect(rect)
