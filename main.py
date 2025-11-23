import sys
import random
from collections import defaultdict
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from ui.dashboard import CompetitionDashboard
from ui.startup_menu import StartupMenu

from core.company_generator import generate_companies
from core.price_engine import PriceEngine
from core.ownership_engine import OwnershipEngine
from core.disruption_engine import DisruptionEngine
from core.ai_traders import AITraderLogic
from core.event_system import EventBus
from core.player import Player
from core.assets_engine import AssetManager
from core.events_engine import SectorEventEngine
from collections import defaultdict


# ============================================================
# GAME CONTROLLER
# ============================================================

class GameController:
    def __init__(self, company_count, difficulty, player_name, player_company_name):
        # ------------------------------------------------------
        # Generate companies
        # ------------------------------------------------------
        self.companies = generate_companies(company_count, difficulty, player_company_name)

        # ------------------------------------------------------
        # Engines: per-company systems
        # ------------------------------------------------------
        self.price_engines = {c: PriceEngine(c) for c in self.companies}
        self.ownership_engines = {c: OwnershipEngine(c) for c in self.companies}

        # Global systems
        self.disruption_engine = DisruptionEngine()
        self.ai_logic = AITraderLogic()
        self.event_bus = EventBus()
        self.player = Player(name=player_name)
        self.asset_manager = AssetManager()
        # Simple automation bot state
        self.autobot = {
            "active": False,
            "level": 0,
            "speed": 1,
            "accuracy": 0.52,
            "size": 1.0,
            "total_pnl": 0.0,
            "history": [],
        }
        self.ai_cash = {c.name: 120000 for c in self.companies if not getattr(c, "is_player", False)}
        self._prev_prices = {c: c.price for c in self.companies}
        self.prev_ratings = {}
        self.sector_events = SectorEventEngine(sectors=list({c.sector for c in self.companies}))
        self.last_player_external_income = 0.0
        self._seed_intercompany_ai_holders()
        # Order pressure queues
        self.buy_pressure = {c: 0 for c in self.companies}
        self.sell_pressure = {c: [] for c in self.companies}
        # Seed initial AI assets
        for c in self.companies:
            if getattr(c, "is_player", False):
                continue
            owner_id = c.name
            budget = self.ai_cash.get(owner_id, 0)
            for _ in range(2):
                pick = self.asset_manager.random_ai_pick(owner_id, budget * 0.3)
                if pick:
                    cost = self.asset_manager.ASSET_TYPES[pick]["cost"]
                    if budget >= cost:
                        self.asset_manager.purchase(pick, owner=owner_id)
                        budget -= cost
            self.ai_cash[owner_id] = budget
        # Demand tracker per company
        self.demand_scores = {c: 0.0 for c in self.companies}
        self.sentiment = {c: 0.0 for c in self.companies}

        # Track day transitions for daily decay
        sample_engine = next(iter(self.price_engines.values()))
        self.last_global_day = sample_engine.global_day

        # ------------------------------------------------------
        # Dashboard UI
        # ------------------------------------------------------
        self.dashboard = CompetitionDashboard(
            companies=self.companies,
            buy_callback=self.on_buy,
            sell_callback=self.on_sell,
            dump_callback=self.on_dump,
            offer_callback=self.on_offer,
            set_speed_callback=self.set_speed,
            asset_purchase_callback=self.on_buy_asset,
            pr_callback=self.on_pr_campaign,
            rd_callback=self.on_rd_sprint,
            sabotage_callback=self.on_sabotage,
            fortify_callback=self.on_fortify,
            buy_bot_callback=self.on_buy_bot,
            upgrade_bot_callback=self.on_upgrade_bot,
        )

        self.dashboard.set_disruption_engine(self.disruption_engine)
        self.dashboard.set_asset_manager(self.asset_manager)
        self.event_bus.subscribe(self.dashboard.push_feed)
        self.dashboard.set_cash(self.player.cash)
        self.dashboard.update_automation(self.autobot)

        # ------------------------------------------------------
        # Tick Timer
        # ------------------------------------------------------
        self.fast_speed = False
        self.timer = QTimer()
        self.timer.timeout.connect(self.game_tick)
        self.timer.start(500)  # faster ticks

        self.dashboard.show()

    # ============================================================
    # PLAYER ACTIONS
    # ============================================================

    def on_buy(self, company, shares):
        eng = self.ownership_engines[company]
        cost = company.price * shares

        if cost > self.player.cash:
            self.dashboard.push_feed(
                f"Insufficient funds: need ${cost:,.2f}", "#ff8b8b"
            )
            return

        # If no float, queue buy pressure instead of failing
        if company.public_float <= 0:
            self.buy_pressure[company] += shares
            self.dashboard.push_feed(
                f"No float available. Queued buy order for {shares} shares of {company.name}.",
                "#7fd8ff",
            )
            return

        success, disruption_gain = eng.buy_player(shares, self.disruption_engine)

        if success:
            self.player.spend(cost)
            self.demand_scores[company] += shares
            self.dashboard.push_feed(
                f"You bought {shares} shares of {company.name}",
                "#a8ffb0",
            )
            self.dashboard.log_trade(company.name, f"Buy {shares} @ ${company.price:.2f}", "#7fd8ff")
            self.dashboard.set_cash(self.player.cash)

        self.dashboard.refresh_selected_company()

    def on_sell(self, company, shares):
        if shares <= 0 or company.player_shares < shares:
            self.dashboard.push_feed("Not enough shares to sell.", "#ff8b8b")
            return
        # Reserve shares and schedule sell pressure over time
        company.player_shares -= shares
        chunk = max(1, shares // 8)
        self.sell_pressure[company].append({
            "owner": "player",
            "remaining": shares,
            "chunk": chunk,
            "penalty": 1.0,  # full value
        })
        self.dashboard.push_feed(f"Queued sell of {shares} shares of {company.name}", "#99d8ff")
        self.dashboard.refresh_selected_company()

    def on_dump(self, company, shares):
        if shares <= 0 or company.player_shares < shares:
            self.dashboard.push_feed("Not enough shares to dump.", "#ff8b8b")
            return
        # Reserve shares and schedule fast dump with worse price
        company.player_shares -= shares
        chunk = max(1, shares // 4)
        self.sell_pressure[company].append({
            "owner": "player",
            "remaining": shares,
            "chunk": chunk,
            "penalty": 0.9,  # worse price
        })
        self.disruption_engine.apply_trade_disruption(10)
        self.dashboard.push_feed(f"Dumped {shares} shares of {company.name} (queued, discount payout)", "#ff7b7b")
        self.dashboard.refresh_selected_company()

    def on_offer(self, company, target_ai, shares, premium_pct):
        own_eng = self.ownership_engines[company]
        cost = company.price * shares * (1 + premium_pct / 100)
        if cost > self.player.cash:
            self.dashboard.push_feed(
                f"Offer failed: need ${cost:,.2f} cash", "#ff8b8b"
            )
            return

        accepted, transferred = own_eng.offer_purchase_from_ai(
            target_ai, shares, self.disruption_engine, premium_pct=premium_pct / 100, accept_bias=-0.05
        )

        if accepted and transferred > 0:
            self.player.spend(cost)
            self.dashboard.push_feed(
                f"{target_ai} accepted offer for {transferred} shares of {company.name}",
                "#c2a8ff",
            )
            self.dashboard.set_cash(self.player.cash)
        else:
            self.dashboard.push_feed(
                f"{target_ai} declined your offer for {shares} shares of {company.name}",
                "#ffaa7f",
            )

        self.dashboard.refresh_selected_company()

    def on_buy_asset(self, asset_type):
        cfg = self.asset_manager.ASSET_TYPES.get(asset_type)
        if not cfg:
            return
        cost = cfg["cost"]
        if cost > self.player.cash:
            self.dashboard.push_feed(
                f"Not enough cash for {asset_type} (${cost:,.0f})", "#ff8b8b"
            )
            return

        purchased, spent, broken = self.asset_manager.purchase(asset_type)
        if purchased:
            self.player.spend(cost)
            self.dashboard.push_feed(
                f"Purchased {asset_type} for ${cost:,.0f}" + (" (broken)" if broken else ""),
                "#ff9b8f" if broken else "#9fe6ff",
            )
            self.dashboard.set_cash(self.player.cash)
            self.dashboard.update_assets_panel(self.player.cash, self.portfolio_value())

    def on_pr_campaign(self):
        cost = 5000
        if self.player.cash < cost:
            self.dashboard.push_feed("Not enough cash for PR ($5,000)", "#ff8b8b")
            return
        self.player.spend(cost)
        self.disruption_engine.value = max(0, self.disruption_engine.value - 10)
        self.prev_ratings["player"] = self.prev_ratings.get("player", 50) + 2
        self.dashboard.push_feed("PR campaign lowered disruption by 10% and lifted CEO rating", "#9fe6ff")
        self.dashboard.set_cash(self.player.cash)

    def on_rd_sprint(self):
        cost = 7000
        if self.player.cash < cost:
            self.dashboard.push_feed("Not enough cash for R&D ($7,000)", "#ff8b8b")
            return
        self.player.spend(cost)
        if random.random() < 0.65:
            delta = 4
            self.dashboard.push_feed("R&D sprint succeeded: CEO rating +4", "#c2a8ff")
        else:
            delta = -3
            self.disruption_engine.apply_trade_disruption(5)
            self.dashboard.push_feed("R&D failed: CEO rating -3, disruption +5", "#ff9b8f")
        self.prev_ratings["player"] = self.prev_ratings.get("player", 50) + delta
        self.dashboard.set_cash(self.player.cash)

    def on_sabotage(self, target_company):
        if not target_company or target_company.is_player:
            return
        cost = 4000
        if self.player.cash < cost:
            self.dashboard.push_feed("Not enough cash to sabotage ($4,000)", "#ff8b8b")
            return
        self.player.spend(cost)
        # reduce public float slightly and add disruption
        target_company.public_float = max(0, target_company.public_float - 5)
        self.disruption_engine.apply_trade_disruption(12)
        self.prev_ratings["player"] = self.prev_ratings.get("player", 50) - 5
        self.dashboard.push_feed(f"Sabotaged {target_company.name} (float -5, rating hit)", "#ff7b7b")
        self.dashboard.set_cash(self.player.cash)

    def on_fortify(self, target_company):
        cost = 6000
        if self.player.cash < cost:
            self.dashboard.push_feed("Not enough cash to fortify ($6,000)", "#ff8b8b")
            return
        self.player.spend(cost)
        self.dashboard.push_feed("Fortified operations: +3 CEO rating, -5 disruption", "#9fe6ff")
        self.disruption_engine.value = max(0, self.disruption_engine.value - 5)
        self.prev_ratings["player"] = self.prev_ratings.get("player", 50) + 3
        self.dashboard.set_cash(self.player.cash)

    # ============================================================
    # AUTOMATION BOT
    # ============================================================
    def on_buy_bot(self):
        if self.autobot["active"]:
            self.dashboard.push_feed("Automation bot already active.", "#9fe6ff")
            return
        cost = 15000
        if self.player.cash < cost:
            self.dashboard.push_feed(f"Need ${cost:,.0f} to activate bot.", "#ff8b8b")
            return
        self.player.spend(cost)
        self.autobot.update({"active": True, "level": 1, "speed": 1, "accuracy": 0.55, "size": 0.5})
        self.dashboard.push_feed("Automation bot online (Level 1).", "#9fe6ff")
        self.dashboard.set_cash(self.player.cash)
        self.dashboard.update_automation(self.autobot)

    def on_upgrade_bot(self, aspect):
        if not self.autobot["active"]:
            self.dashboard.push_feed("Activate the bot first.", "#ff8b8b")
            return
        upgrade_cost = 8000 + self.autobot["level"] * 4000
        if self.player.cash < upgrade_cost:
            self.dashboard.push_feed(f"Need ${upgrade_cost:,.0f} for upgrade.", "#ff8b8b")
            return
        self.player.spend(upgrade_cost)
        self.autobot["level"] += 1
        if aspect == "speed":
            self.autobot["speed"] = min(5, self.autobot["speed"] + 1)
        elif aspect == "accuracy":
            self.autobot["accuracy"] = min(0.9, self.autobot["accuracy"] + 0.05)
        elif aspect == "size":
            self.autobot["size"] = min(3.0, self.autobot["size"] + 0.25)
        self.dashboard.push_feed(f"Automation upgrade applied ({aspect}).", "#9fe6ff")
        self.dashboard.set_cash(self.player.cash)
        self.dashboard.update_automation(self.autobot)

    def _tick_bot(self):
        if not self.autobot["active"]:
            return
        # Faster cadence; speed scales chance
        act_chance = 0.12 * self.autobot["speed"]
        if random.random() > act_chance:
            return
        target = random.choice(self.companies)
        if target.public_float <= 0:
            return
        base_shares = max(1, int(target.total_shares * 0.006 * self.autobot["size"]))
        shares = min(base_shares, target.public_float)
        cost = target.price * shares
        if self.player.cash < cost:
            return
        win = random.random() < self.autobot["accuracy"]
        buy_price = target.price
        sell_price = buy_price * (1.012 + random.uniform(0, 0.012) if win else 1 - (0.008 + random.uniform(0, 0.01)))
        pnl = (sell_price - buy_price) * shares
        # Apply buy/sell pressure and price change
        self.player.spend(cost)
        target.public_float = max(0, target.public_float - shares)
        target.public_float = max(0, target.public_float + shares)
        target.price = round(sell_price, 2)
        self.price_engines[target].company.price = target.price
        # Demand signal for downstream AI
        self.demand_scores[target] = self.demand_scores.get(target, 0.0) + (shares if win else -shares * 0.5)
        # Return cash plus pnl
        self.player.earn(cost + pnl)
        self.autobot["total_pnl"] += pnl
        record = {
            "result": "WIN" if win else "LOSS",
            "shares": shares,
            "name": target.name,
            "buy": buy_price,
            "sell": sell_price,
            "pnl": pnl,
        }
        self.autobot["history"] = (self.autobot["history"] + [record])[-20:]
        self.dashboard.update_automation(self.autobot)

    # ============================================================
    # SPEED CONTROL
    # ============================================================

    def set_speed(self, fast: bool):
        self.fast_speed = fast

        # Change timer speed
        self.timer.stop()
        self.timer.start(500 if fast else 1000)

        # Change engine tick speed
        for eng in self.price_engines.values():
            eng.set_fast_mode(fast)

    # ============================================================
    # MAIN TICK LOOP
    # ============================================================

    def game_tick(self):
        trend_changes = []
        sample_eng = next(iter(self.price_engines.values()))
        # Assets tick (income + decay) — do early so AI can reason about yield
        ticks_per_day = (
            PriceEngine.TICKS_PER_DAY_FAST if self.fast_speed else PriceEngine.TICKS_PER_DAY_NORMAL
        )
        income, _, asset_events = self.asset_manager.tick(ticks_per_day)
        player_income = income.get("player", 0.0)
        if player_income:
            self.player.earn(player_income)
        for owner, msg in asset_events:
            color = "#ff9b8f" if owner == "player" else "#ffcc88"
            self.event_bus.emit(f"{owner}: {msg}", color)

        # Tick every company
        for c in self.companies:
            price_eng = self.price_engines[c]
            own_eng = self.ownership_engines[c]

            # Feed disruption friction into price movement
            price_eng.apply_disruption_friction(self.disruption_engine.value / 100.0)

            price_eng.tick()

            # AI behavior
            self.ai_logic.tick(
                company=c,
                ownership_engine=own_eng,
                disruption_engine=self.disruption_engine,
                event_bus=self.event_bus,
                trade_callback=self.on_ai_trade,
                income_map=income,
            )
            # Free-fall detection (>5% drop in one tick)
            prev_p = self._prev_prices.get(c, c.price)
            if prev_p > 0:
                pct = (c.price - prev_p) / prev_p
                trend_changes.append(pct)
                if pct <= -0.05:
                    self.event_bus.emit(
                        f"{c.name} in free fall ({pct*100:.1f}%)",
                        "#ff7b7b",
                    )
            self._prev_prices[c] = c.price
            # Sentiment tracking as moving avg of pct change
            self.sentiment[c] = (self.sentiment.get(c, 0.0) * 0.9) + (pct * 0.1)

        # Bot action after AI loop
        self._tick_bot()

        # Process queued sell pressure (player sells trickle out)
        for c, orders in self.sell_pressure.items():
            if not orders:
                continue
            new_orders = []
            for o in orders:
                if o["remaining"] <= 0:
                    continue
                lot = min(o["chunk"], o["remaining"])
                o["remaining"] -= lot
                # release float and pay out
                c.public_float += lot
                price_paid = c.price * o["penalty"]
                cash = lot * price_paid
                self.player.earn(cash) if o["owner"] == "player" else None
                self.demand_scores[c] -= lot * (1.2 if o["penalty"] < 1.0 else 0.6)
                self._prev_prices[c] = c.price
                # nudge price down slightly on each lot
                c.price = round(max(0.01, c.price * (1 - lot / max(1, c.total_shares) * 0.15)), 2)
                self.price_engines[c].company.price = c.price
                if o["remaining"] > 0:
                    new_orders.append(o)
            self.sell_pressure[c] = new_orders

        # Process queued buy pressure when float becomes available
        for c, qty in list(self.buy_pressure.items()):
            if qty <= 0 or c.public_float <= 0:
                continue
            take = min(qty, c.public_float)
            c.public_float -= take
            # allocate to a placeholder market maker
            c.ai_owners["Market Queue"] = c.ai_owners.get("Market Queue", 0) + take
            self.demand_scores[c] += take * 0.5
            # price uptick
            c.price = round(c.price * (1 + take / max(1, c.total_shares) * 0.1), 2)
            self.price_engines[c].company.price = c.price
            self.buy_pressure[c] -= take
        # AI income and acquisitions
        for c in self.companies:
            if getattr(c, "is_player", False):
                continue
            owner_id = c.name
            ai_inc = income.get(owner_id, 0.0)
            self.ai_cash[owner_id] = self.ai_cash.get(owner_id, 0.0) + ai_inc
            # More frequent asset buying
            if self.ai_cash[owner_id] > 6000 and random.random() < 0.6:
                budget_slice = self.ai_cash[owner_id] * random.uniform(0.15, 0.35)
                ai_pick = self.asset_manager.random_ai_pick(owner_id, budget_slice)
                if ai_pick:
                    cost = self.asset_manager.ASSET_TYPES[ai_pick]["cost"]
                    if self.ai_cash[owner_id] >= cost:
                        self.ai_cash[owner_id] -= cost
                        purchased, _, broken = self.asset_manager.purchase(ai_pick, owner=owner_id)
                        if purchased:
                            note = f"{owner_id} bought asset {ai_pick}" + (" (broken)" if broken else "")
                            self.event_bus.emit(note, "#c2a8ff")

        # Dividend sharing: proportional income + controlling bonus
        LADDER = [
            (0.9, 0.32),
            (0.8, 0.29),
            (0.7, 0.25),
            (0.6, 0.21),
            (0.5, 0.18),
            (0.4, 0.15),
            (0.3, 0.12),
            (0.2, 0.09),
            (0.1, 0.06),
            (0.0, 0.03),
        ]

        def ladder_rate(frac):
            for threshold, rate in LADDER:
                if frac >= threshold:
                    return rate
            return 0.0

        self.last_player_external_income = 0.0
        dividend_map = defaultdict(list)
        dividends_received = defaultdict(float)
        dividends_paid = defaultdict(float)
        for c in self.companies:
            target_income = income.get(c.name, 0.0)
            if target_income <= 0:
                continue
            total_shares = max(1, c.total_shares)
            # Player
            player_frac = c.player_shares / total_shares
            if player_frac > 0:
                rate = ladder_rate(player_frac)
                dividend = target_income * rate
                if dividend > 0:
                    self.player.earn(dividend)
                    self.last_player_external_income += dividend
                    dividend_map["player"].append((c.name, dividend))
                    dividends_paid[c.name] += dividend
                    dividends_received["player"] += dividend
            # AI holders
            for ai_name, amt in c.ai_owners.items():
                frac = amt / total_shares
                if frac > 0:
                    rate = ladder_rate(frac)
                    dividend = target_income * rate
                    self.ai_cash[ai_name] = self.ai_cash.get(ai_name, 0.0) + dividend
                    dividend_map[ai_name].append((c.name, dividend))
                    dividends_paid[c.name] += dividend
                    dividends_received[ai_name] += dividend

        # Apply disruption decay
        self.disruption_engine.decay_tick()
        # Soften demand scores over time
        for c in self.demand_scores:
            self.demand_scores[c] *= 0.98
            if abs(self.demand_scores[c]) < 0.5:
                self.demand_scores[c] = 0.0
            # Queue pressure when float is zero
            if c.public_float <= 0:
                self.demand_scores[c] += c.total_shares * 0.01

        # Daily decay check (against any sample engine)
        if sample_eng.global_day != self.last_global_day:
            self.disruption_engine.decay_daily()
            self.last_global_day = sample_eng.global_day
            # Spawn sector events
            ev = self.sector_events.maybe_spawn(sample_eng.global_day)
            if ev:
                tone = "#9fe6ff" if ev.drift_delta > 0 else "#ffcc88"
                self.event_bus.emit(f"{ev.name} in {ev.sector} for {ev.duration_days}d", tone)

        # Update sidebar prices
        self.dashboard.update_price_display()

        # Update disruption UI
        self.dashboard.update_disruption_ui()
        self.dashboard.set_cash(self.player.cash)
        ai_treasury = sum(self.ai_cash.values()) if isinstance(self.ai_cash, dict) else self.ai_cash
        # Build active events snapshot
        active_ev = []
        for ev in self.sector_events.active_events:
            if ev.is_active(sample_eng.global_day):
                active_ev.append({
                    "name": ev.name,
                    "sector": ev.sector,
                    "drift": ev.drift_delta,
                    "vol": ev.vol_delta,
                    "days_left": ev.start_day + ev.duration_days - sample_eng.global_day
                })
        self.dashboard.update_assets_panel(
            self.player.cash,
            self.portfolio_value(),
            ai_treasury,
            active_events=active_ev,
            external_income=self.last_player_external_income,
            dividends=dividend_map,
        )

        # Stock boost from assets (player company only)
        player_company = next((c for c in self.companies if getattr(c, "is_player", False)), None)
        if player_company:
            boost = sum(
                a.get("boost", 0.0) * a.get("condition", 1.0)
                for a in self.asset_manager.snapshot("player")
            )
            if boost:
                price_eng = self.price_engines[player_company]
                player_company.price = round(player_company.price * (1.0 + boost * 0.005), 2)
                price_eng.company.price = player_company.price

        # Takeover check: if player owns >50% of a company (not already taken)
        for c in self.companies:
            if getattr(c, "is_player", False):
                continue
            if getattr(c, "taken_over", False):
                continue
            if c.player_shares > c.total_shares * 0.5:
                # Transfer AI-held assets of that owner to player
                assets_to_move = self.asset_manager.snapshot(c.name)
                self.asset_manager.ensure_owner("player")
                for a in assets_to_move:
                    self.asset_manager.assets["player"].append(dict(a))
                if c.name in self.asset_manager.assets:
                    self.asset_manager.assets[c.name] = []
                c.taken_over = True
                c.ai_owners.clear()
                c.update_public_float()
                self.event_bus.emit(f"You took over {c.name}! Assets integrated.", "#8bf0a7")

        # Bankruptcy/respawn: if price too low and float full, respawn company
        for c in self.companies:
            if getattr(c, "is_player", False):
                continue
            if c.price <= 0.5 and c.public_float >= c.total_shares * 0.95:
                c.price = round(random.uniform(15, 60), 2)
                c.player_shares = 0
                c.ai_owners = {}
                c.public_float = c.total_shares
                c.daily_candles = []
                c.quarterly_candles = []
                c.generate_initial_history()
                c.current_open = c.price
                c.current_high = c.price
                c.current_low = c.price
                c.current_close = c.price
                c.ticks_today = 0
                self._prev_prices[c] = c.price
                self.event_bus.emit(f"{c.name} went bankrupt and respawned at ${c.price}", "#ffaa7f")
            # AI profit taking: occasionally sell small lots when price rises
            if not getattr(c, "is_player", False) and self._prev_prices.get(c, c.price) > 0:
                pct = (c.price - self._prev_prices[c]) / self._prev_prices[c]
                if pct > 0.05 and c.ai_owners and random.random() < 0.2:
                    for ai_name, amt in list(c.ai_owners.items()):
                        if amt <= 0:
                            continue
                        sell_amt = max(1, int(amt * 0.02))
                        sell_amt = min(sell_amt, amt)
                        c.ai_owners[ai_name] -= sell_amt
                        if c.ai_owners[ai_name] <= 0:
                            del c.ai_owners[ai_name]
                        c.public_float += sell_amt
                        self.event_bus.emit(f"{ai_name} trimmed {sell_amt} of {c.name}", "#99d8ff")

        # CEO ratings update
        avg_trend = sum(trend_changes) / len(trend_changes) if trend_changes else 0.0
        player_rating = self.asset_manager.ceo_rating(
            self.player.cash,
            self.portfolio_value(),
            owner="player",
            disruption=self.disruption_engine.value,
            trend=avg_trend,
        )
        # Apply extra penalties for disruption and negative trend
        player_rating -= int(self.disruption_engine.value * 0.2)
        if avg_trend < 0:
            player_rating -= int(abs(avg_trend) * 200)
        # Bad trades: if disruption very high, penalize rating
        if self.disruption_engine.value > 80:
            player_rating -= 5
        if "player" in self.prev_ratings:
            delta = player_rating - self.prev_ratings["player"]
            if abs(delta) >= 10:
                note = "surged" if delta > 0 else "plummeted"
                self.event_bus.emit(f"Your CEO rating {note} to {player_rating}", "#9fe6ff" if delta > 0 else "#ff9b8f")
        self.prev_ratings["player"] = player_rating
        # Compute AI ratings per company (simplified: based on their cash + assets + price trend)
        ai_ratings = {}
        for c in self.companies:
            if getattr(c, "is_player", False):
                continue
            owner_id = c.name
            ai_rating = self.asset_manager.ceo_rating(
                self.ai_cash.get(owner_id, 0.0),
                c.price * sum(c.ai_owners.values()),
                owner=owner_id,
                disruption=0.0,
                trend=avg_trend,
            )
            if avg_trend < 0:
                ai_rating -= int(abs(avg_trend) * 150)
            ai_ratings[c.name] = ai_rating
        self.dashboard.set_company_ratings(player_rating, ai_ratings)

        # Feed ratings into price engines
        for c in self.companies:
            rating = player_rating if getattr(c, "is_player", False) else ai_ratings.get(c.name, 50)
            # Asset boost: sum boost * condition for player company only
            asset_boost = 0.0
            if getattr(c, "is_player", False):
                asset_boost = sum(
                    a.get("boost", 0.0) * a.get("condition", 1.0)
                    for a in self.asset_manager.snapshot("player")
                )
            # Sector boost from events
            sector_boost, sector_vol = self.sector_events.get_modifiers(getattr(c, "sector", ""), sample_eng.global_day)
            # Ownership vol: higher player+AI ownership -> more vol
            owned = c.player_shares + sum(c.ai_owners.values())
            ownership_vol = min(0.5, owned / max(1, c.total_shares) * 0.5)
            demand_bias = self.demand_scores.get(c, 0.0) / max(1, c.total_shares)
            sentiment_bias = self.sentiment.get(c, 0.0)

            self.price_engines[c].set_rating_factor(rating)
            self.price_engines[c].set_asset_boost(asset_boost)
            self.price_engines[c].set_sector_boost(sector_boost)
            self.price_engines[c].set_ownership_vol_boost(ownership_vol)
            self.price_engines[c].set_demand_bias(demand_bias)
            # sentiment indirectly affects demand bias via drift strength already; keep display only

        # Modifiers panel for current selected company
        sel = self.dashboard.selected_company
        sel_rating = player_rating if getattr(sel, "is_player", False) else ai_ratings.get(sel.name, 50)
        sel_asset_boost = sum(
            a.get("boost", 0.0) * a.get("condition", 1.0)
            for a in self.asset_manager.snapshot("player")
        ) if getattr(sel, "is_player", False) else 0.0
        sel_sector_boost, _ = self.sector_events.get_modifiers(getattr(sel, "sector", ""), sample_eng.global_day)
        sel_demand = self.demand_scores.get(sel, 0.0) / max(1, sel.total_shares)
        sel_sentiment = self.sentiment.get(sel, 0.0)
        self.dashboard.set_modifiers_display(sel_rating, sel_asset_boost, sel_sector_boost, self.disruption_engine.value, sel_demand, sel_sentiment, self.last_player_external_income)

        # Update clock from sample engine
        time_str, quarter_str = sample_eng.get_clock_display()
        self.dashboard.set_clock(time_str, quarter_str)

        # Refresh chart visuals without resetting selection
        self.dashboard.update_chart_only()

        # Reports tab data
        reports = []
        assets_income_map = income
        for c in self.companies:
            reports.append({
                "name": c.name,
                "price": c.price,
                "float": c.public_float,
                "owned": c.player_shares,
                "asset_income": assets_income_map.get(c.name, 0.0),
                "div_paid": dividends_paid.get(c.name, 0.0),
                "div_received": dividends_received.get(c.name, 0.0),
            })
        self.dashboard.update_reports(reports, dividends=dividend_map)

    def on_ai_trade(self, company, delta_shares, actor="AI"):
        # Positive delta = buy (demand), negative = supply
        self.demand_scores[company] = self.demand_scores.get(company, 0.0) + delta_shares
        # Log trade for per-company view
        if delta_shares > 0:
            txt = f"{actor} bought {delta_shares} {company.name}"
            color = "#7fd8ff"
        else:
            txt = f"{actor} sold {abs(delta_shares)} {company.name}"
            color = "#ff9b8f"
        self.dashboard.log_trade(company.name, txt, color)

    def _seed_intercompany_ai_holders(self):
        """
        Replace generic AI holders with other company names to simulate inter-company trading.
        """
        names = [c.name for c in self.companies]
        for c in self.companies:
            # Preserve CEO stake if present
            ceo_shares = c.ai_owners.get("CEO", 0)
            c.ai_owners = {}
            if ceo_shares > 0:
                c.ai_owners["CEO"] = ceo_shares
            remaining = c.total_shares - c.player_shares - sum(c.ai_owners.values())
            remaining = max(0, remaining)
            others = [n for n in names if n != c.name]
            random.shuffle(others)
            for name in others[: min(5, len(others))]:
                if remaining <= 0:
                    break
                give = random.randint(1, max(1, int(c.total_shares * 0.05)))
                give = min(give, remaining)
                c.ai_owners[name] = give
                remaining -= give
            c.public_float = remaining

    def portfolio_value(self):
        total = 0.0
        for c in self.companies:
            total += c.player_shares * c.price
        return total


# ============================================================
# START FUNCTION
# ============================================================

def start_game(company_count, difficulty, player_name, player_company_name):
    GameController(company_count, difficulty, player_name, player_company_name)


# ============================================================
# ENTRYPOINT
# ============================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    menu = StartupMenu(start_game)
    menu.show()
    sys.exit(app.exec())
