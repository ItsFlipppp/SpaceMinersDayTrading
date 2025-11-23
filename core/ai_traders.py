"""
Simple AI trading behaviors for each company.
"""

import random


class AITraderLogic:
    def __init__(self):
        # tuneable knobs (slowed)
        self.base_buy_chance = 0.28
        self.base_sell_chance = 0.18
        self.dump_chance = 0.02
        self.profiles = {}
        self.last_prices = {}

    def _get_profile(self, company):
        if company.name in self.profiles:
            return self.profiles[company.name]
        archetypes = [
            ("maker", 0.25),
            ("scalper", 0.22),
            ("swing", 0.25),
            ("holder", 0.13),
            ("speculator", 0.15),
        ]
        r = random.random()
        acc = 0
        choice = "swing"
        for name, w in archetypes:
            acc += w
            if r <= acc:
                choice = name
                break
        profile = {
            "type": choice,
            "active_bias": random.uniform(-0.05, 0.15),
            "size_bias": random.uniform(0.5, 1.5),
            "hold_bias": random.uniform(0.0, 0.3),
        }
        self.profiles[company.name] = profile
        return profile

    def _price_nudge(self, company, shares, direction):
        frac = shares / max(1, company.total_shares)
        impact = frac * 0.2
        company.price = round(max(0.01, company.price * (1 + direction * impact)), 2)

    def tick(self, company, ownership_engine, disruption_engine, event_bus=None, trade_callback=None, income_map=None):
        """
        Run one AI trading step for a company.
        AIs are the companies themselves (keys in company.ai_owners).
        """
        if not company.ai_owners:
            return

        if income_map is None:
            income_map = {}

        # Dividend ladder helper (mirrors main controller)
        LADDER = [
            (0.9, 0.25),
            (0.8, 0.22),
            (0.7, 0.19),
            (0.6, 0.16),
            (0.5, 0.14),
            (0.4, 0.12),
            (0.3, 0.10),
            (0.2, 0.07),
            (0.1, 0.04),
            (0.0, 0.02),
        ]

        def ladder_rate(frac):
            for th, rate in LADDER:
                if frac >= th:
                    return rate
            return 0.0

        profile = self._get_profile(company)

        # Global throttle: still throttled but more active
        throttle = 0.12 - profile["active_bias"]
        if random.random() > max(0.02, throttle):
            return

        # Trend signal: compare last daily close vs previous (if available)
        trend_bias = 0.0
        if len(company.daily_candles) >= 2:
            last_close = company.daily_candles[-1].close
            prev_close = company.daily_candles[-2].close
            trend_bias = (last_close - prev_close) / max(1.0, prev_close)
        prev_price = self.last_prices.get(company.name, company.price)
        price_change = (company.price - prev_price) / max(1.0, prev_price)
        self.last_prices[company.name] = company.price

        disruption_penalty = min(1.0, disruption_engine.value / 150.0)
        float_factor = min(1.0, company.public_float / max(1, company.total_shares))

        asset_income = income_map.get(company.name, 0.0)
        per_share_income = asset_income / max(1, company.total_shares)
        yield_est = per_share_income / max(0.01, company.price)

        for ai_name, ai_shares in list(company.ai_owners.items()):
            # Buy logic
            buy_roll = random.random()
            float_bias = float_factor * 0.35  # more float -> more willing to buy
            # Expected dividend improvement if this AI increases stake modestly
            probe_shares = max(1, int(company.total_shares * 0.01))
            now_rate = ladder_rate(ai_shares / max(1, company.total_shares))
            next_rate = ladder_rate((ai_shares + probe_shares) / max(1, company.total_shares))
            div_gain = (next_rate - now_rate) * asset_income
            # Convert to an annualized-ish yield signal (scaled)
            income_bias = min(0.18, yield_est * 6 + (div_gain / max(1.0, probe_shares * company.price)) * 0.3)
            buy_threshold = self.base_buy_chance + trend_bias * 0.35 - disruption_penalty * 0.25 + profile["active_bias"] + float_bias + income_bias
            buy_threshold = max(0.05, min(0.45, buy_threshold))

            if buy_roll < buy_threshold and company.public_float > 0:
                max_buy = max(1, int(company.total_shares * 0.08 * profile["size_bias"]))
                shares = random.randint(1, max_buy)
                shares = min(shares, company.public_float)
                # Boost size a bit if yield is attractive
                if yield_est > 0.01:
                    shares = min(company.public_float, shares + int(company.total_shares * 0.01))
                if ownership_engine.ai_buy(ai_name, shares):
                    self._price_nudge(company, shares, +1)
                    if trade_callback:
                        trade_callback(company, shares, ai_name)
                continue  # skip selling same tick

            # Dump (rare, but more likely on downward trend)
            dump_roll = random.random()
            if dump_roll < self.dump_chance * (1 + trend_bias * -10):
                if trend_bias < -0.01 or price_change < -0.02:
                    dump_amount = ai_shares  # full exit on slide
                else:
                    dump_amount = max(1, int(ai_shares * 0.15 * profile["size_bias"]))
                dump_amount = min(dump_amount, ai_shares)
                if ownership_engine.ai_sell(ai_name, dump_amount):
                    if event_bus and dump_amount >= ai_shares:
                        event_bus.emit(f"{ai_name} panic-dumped all shares of {company.name}", "#ff6666")
                    self._price_nudge(company, dump_amount, -1)
                    if trade_callback:
                        trade_callback(company, -dump_amount, ai_name)
                continue

            # Maker logic: aim for inventory around 8-15% of total shares
            if profile["type"] == "maker":
                target_low = company.total_shares * 0.08
                target_high = company.total_shares * 0.15
                # If under target, buy small lots
                if ai_shares < target_low and company.public_float > 0:
                    shares = max(1, int(company.total_shares * 0.01))
                    shares = min(shares, company.public_float)
                    if ownership_engine.ai_buy(ai_name, shares):
                        self._price_nudge(company, shares, +1)
                    continue
                # If above target_high, sell small lots
                if ai_shares > target_high:
                    shares = max(1, int((ai_shares - target_high) * 0.3))
                    if ownership_engine.ai_sell(ai_name, shares):
                        self._price_nudge(company, shares, -1)
                    continue

            # Sell logic
            sell_roll = random.random()
            sell_threshold = self.base_sell_chance - trend_bias * 0.25 + disruption_penalty * 0.2 + float_factor * 0.1 - profile["hold_bias"]
            if price_change > 0.03:
                sell_threshold += 0.12  # take profits on strong rise
            if price_change > 0.10:
                sell_threshold += 0.22   # very strong rise -> more selling
            # If yield is strong, dampen selling pressure (they prefer collecting income)
            sell_threshold -= min(0.08, yield_est * 4)
            # If float is empty, encourage releasing shares to market
            if company.public_float <= 0:
                sell_threshold += 0.2
            # Speculators/scalpers take profits faster on spikes
            if profile["type"] in ("scalper", "speculator") and price_change > 0.05:
                sell_threshold += 0.18
            sell_threshold = max(0.05, min(0.60, sell_threshold))

            if sell_roll < sell_threshold and ai_shares > 0:
                min_hold = max(5, int(company.total_shares * 0.03))
                if ai_shares <= min_hold:
                    continue
                # If big run-up, sometimes exit a chunk
                if price_change > 0.1 and random.random() < 0.4:
                    shares = max(1, int(ai_shares * 0.5))
                else:
                    max_sell = max(1, int((ai_shares - min_hold) * 0.5 * profile["size_bias"]))
                    shares = random.randint(1, max_sell)
                # Scalpers/speculators trim lighter but more frequently
                if profile["type"] in ("scalper", "speculator") and price_change > 0.05:
                    shares = max(1, int(ai_shares * random.uniform(0.15, 0.35)))
                if ownership_engine.ai_sell(ai_name, shares):
                    self._price_nudge(company, shares, -1)
                    if trade_callback:
                        trade_callback(company, -shares, ai_name)
