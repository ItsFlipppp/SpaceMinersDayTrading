"""
Disruption Engine
-----------------
Tracks a global disruption index:
- Increases from trades (buy/sell/dump)
- Decays each tick and slightly more each day
- Feeds UI (text/color), price friction, and panic sensitivity
"""


class DisruptionEngine:
    def __init__(self):
        self.value = 0.0            # 0.0 .. 300.0% (soft cap)
        self.decay_rate = 0.15      # % decay per tick
        self.max_value = 300.0      # cap runaway values

    # ------------------------------------------------------------
    #  DISRUPTION APPLICATION
    # ------------------------------------------------------------

    def apply_trade_disruption(self, amount):
        """Apply disruption from buying, selling, dumping shares."""
        self.value += amount
        if self.value > self.max_value:
            self.value = self.max_value

    # ------------------------------------------------------------
    #  DECAY LOGIC
    # ------------------------------------------------------------

    def decay_tick(self):
        """Called every tick to slowly reduce disruption."""
        if self.value <= 0:
            return
        self.value -= self.decay_rate
        if self.value < 0:
            self.value = 0

    def decay_daily(self):
        """Larger decay at end of day."""
        self.value *= 0.92  # lose ~8% of remaining disruption daily
        if self.value < 0:
            self.value = 0

    # ------------------------------------------------------------
    #  MARKET FRICTION (TAX MULTIPLIER)
    # ------------------------------------------------------------

    def get_trade_penalty_multiplier(self):
        """
        Returns multiplier applied to buying fees:
            0% disruption   -> 1.00x
            50% disruption  -> 1.50x
            100% disruption -> 2.00x
            200% disruption -> 3.00x
        """
        return 1.0 + (self.value / 100)

    # ------------------------------------------------------------
    #  TEXT + COLOR FOR UI
    # ------------------------------------------------------------

    def get_display_text(self):
        return f"∆ Disruption Index: {self.value:.1f}%"

    def get_color_for_disruption(self):
        """
        Mimics Puffin-style UI:
            0-40%   -> green
            40-100% -> yellow
            100%+   -> red
        """
        if self.value < 40:
            return "#44ff44"
        elif self.value < 100:
            return "#ffcc33"
        else:
            return "#ff4444"

    # ------------------------------------------------------------
    #  PANIC SELL MODIFIER (used by dump events)
    # ------------------------------------------------------------

    def get_panic_sensitivity(self):
        """
        Raising disruption increases panic sell-off responsiveness.

        Example:
            0% disruption   -> factor 1.0
            100% disruption -> factor 1.5
            200% disruption -> factor 2.0
        """
        return 1.0 + (self.value / 200.0)
