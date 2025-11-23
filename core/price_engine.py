"""
Price Engine
------------
Handles intraday price action and candle formation for one company.

Features:
- 15-minute ticks (normal) or 30-minute ticks (fast)
- Candle updates each tick
- Day/quarter rollovers with history trim
- Volatility + drift + panic + disruption friction
"""

import random


class PriceEngine:
    """
    Price movement system for ONE company.

    The Company object must provide:
        price (float)
        volatility (float)
        tick_price() -> updates forming candle highs/lows/closes
        finalize_daily_candle()
        finalize_quarterly_candle()
        ticks_today (int)
    """

    TICKS_PER_DAY_NORMAL = 64   # ~22.5-minute ticks
    TICKS_PER_DAY_FAST = 32     # ~45-minute ticks
    DAYS_PER_QUARTER = 90

    def __init__(self, company):
        self.company = company

        # Global simulation time
        self.global_tick = 0
        self.global_day = 1
        self.global_quarter = 1

        self.fast_mode = False
        self.panic_pressure = 0.0
        self.market_disruption_factor = 0.0  # 0.0 -> 1.0 scale
        self.rating_factor = 0.0  # -0.5 .. +0.5
        self.asset_boost = 0.0
        self.sector_boost = 0.0
        self.ownership_vol_boost = 0.0
        self.demand_bias = 0.0

    # ------------------------------------------------------------
    # TICK ADVANCEMENT
    # ------------------------------------------------------------

    def tick(self):
        """
        One simulation tick:
            - Price moves
            - Candle updates
            - Check day rollover
            - Check quarter rollover
        """

        ticks_per_day = (
            self.TICKS_PER_DAY_FAST if self.fast_mode else self.TICKS_PER_DAY_NORMAL
        )

        # Apply price movement before updating the candle
        self._apply_price_movement()

        # Update forming candle (high/low/close)
        self.company.tick_price()

        # Tick counters
        self.global_tick += 1
        self.company.ticks_today += 1

        # Day rollover
        if self.company.ticks_today >= ticks_per_day:
            self._close_day()

        # Quarter rollover (trigger at end of each quarter)
        if self.global_day > 1 and (self.global_day - 1) % self.DAYS_PER_QUARTER == 0:
            self._close_quarter()

    # ------------------------------------------------------------
    # PRICE MOVEMENT MODEL
    # ------------------------------------------------------------

    def _apply_price_movement(self):
        """Handles volatility, drift, panic impact, disruption impact."""

        c = self.company
        # Apply sector volatility boost
        base_vol = c.volatility * (1.0 + self.sector_boost)

        # Random walk
        delta = random.uniform(-base_vol, base_vol)
        # Demand bias nudges delta
        delta += base_vol * self.demand_bias * 0.5
        # Ensure some motion even when everything is flat
        if delta == 0:
            delta = random.uniform(-base_vol * 0.1, base_vol * 0.1)

        # Mean reversion drift towards recent daily close, influenced by boosts
        long_term_mean = c.daily_candles[-1].close if c.daily_candles else c.price
        drift_strength = 0.015 + (self.asset_boost + self.sector_boost) * 0.01 + self.rating_factor * 0.02
        drift = (long_term_mean - c.price) * drift_strength
        # CEO rating influence (positive rating accelerates drift/move, negative dampens)
        delta *= (1.0 + self.rating_factor * 0.4)
        drift *= (1.0 + self.rating_factor * 0.4)

        # Panic pressure decays each tick
        if self.panic_pressure > 0:
            delta -= self.panic_pressure
            self.panic_pressure *= 0.90  # slow decay

        # Disruption friction (makes price movement harder)
        if self.market_disruption_factor > 0:
            delta *= max(0.05, 1.0 - (self.market_disruption_factor * 1.2))
        # Ownership-driven volatility boost
        delta *= (1.0 + self.ownership_vol_boost)

        # Combine effects
        new_price = c.price + delta + drift
        # Ensure a visible cent-level move
        if abs(new_price - c.price) < 0.01:
            new_price += 0.02 if random.random() > 0.5 else -0.02

        # Hard floor
        c.price = round(max(0.01, new_price), 2)

    # ------------------------------------------------------------
    # DAY CLOSE
    # ------------------------------------------------------------

    def _close_day(self):
        """When one simulated day passes."""
        self.company.finalize_daily_candle()

        self.global_day += 1
        self.company.ticks_today = 0

        # Reset daily disruption friction
        self.market_disruption_factor = 0.0

    # ------------------------------------------------------------
    # QUARTER CLOSE
    # ------------------------------------------------------------

    def _close_quarter(self):
        self.company.finalize_quarterly_candle()
        self.global_quarter += 1

    # ------------------------------------------------------------
    # PANIC IMPACT
    # ------------------------------------------------------------

    def apply_panic_impact(self, dumped_shares, total_shares):
        """
        Triggered when the player dumps shares.
        Larger dumps = larger immediate price crash + multi-tick pressure.
        """
        if total_shares <= 0:
            return 0.0

        frac = dumped_shares / total_shares
        crash_strength = frac * 0.30  # up to 30% immediate collapse

        self.company.price = max(0.01, self.company.price * (1 - crash_strength))
        self.panic_pressure += crash_strength * 0.5  # lingering pressure

        return crash_strength

    # ------------------------------------------------------------
    # CLOCK DISPLAY
    # ------------------------------------------------------------

    def get_clock_display(self):
        """
        Returns:
            ("11:00PM UTC", "Q3 Day 12")
        """
        ticks_per_day = (
            self.TICKS_PER_DAY_FAST if self.fast_mode else self.TICKS_PER_DAY_NORMAL
        )

        day_fraction = self.company.ticks_today / ticks_per_day
        total_minutes = int(day_fraction * 24 * 60)

        hour = (total_minutes // 60) % 24
        minute = total_minutes % 60

        ampm = "AM" if hour < 12 else "PM"
        hour12 = hour if hour % 12 != 0 else 12

        time_str = f"{hour12}:{minute:02d}{ampm} UTC"
        quarter_str = f"Q{self.global_quarter} Day {self.global_day}"

        return time_str, quarter_str

    # ------------------------------------------------------------
    # SPEED CONTROL
    # ------------------------------------------------------------

    def set_fast_mode(self, enabled: bool):
        self.fast_mode = enabled

    # ------------------------------------------------------------
    # DISRUPTION INPUT
    # ------------------------------------------------------------

    def apply_disruption_friction(self, disruption_pct):
        """
        Controller calls this when disruption engine updates.
        disruption_pct is 0.0 -> 1.0 (0% -> 100%).
        """
        self.market_disruption_factor = disruption_pct

    # ------------------------------------------------------------
    # CEO RATING INPUT
    # ------------------------------------------------------------

    def set_rating_factor(self, rating: float):
        """
        rating 0-100 -> factor -0.5..+0.5 roughly.
        """
        normalized = (rating - 50.0) / 100.0
        self.rating_factor = max(-0.5, min(0.5, normalized))

    # ------------------------------------------------------------
    # ASSET/SECTOR BOOSTS
    # ------------------------------------------------------------

    def set_asset_boost(self, boost: float):
        self.asset_boost = boost

    def set_sector_boost(self, boost: float):
        self.sector_boost = boost

    def set_ownership_vol_boost(self, boost: float):
        self.ownership_vol_boost = boost

    def set_demand_bias(self, bias: float):
        # bias expected small: positive = demand, negative = supply
        self.demand_bias = max(-1.0, min(1.0, bias))
