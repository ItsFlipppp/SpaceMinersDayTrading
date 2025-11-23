import random
from dataclasses import dataclass


# ------------------------------------------------------------
#  AI NAME GENERATION (Neutral Futuristic Finance Firms)
# ------------------------------------------------------------

AI_NAME_BANK = [
    "Apex Equity Group", "Nova Securities", "Hyperion Holdings",
    "Solstice Investment Fund", "Stellar Trust Capital",
    "AstroYield Financial", "Zenith Market Authority",
    "Momentum Arbitrage Partners", "Cosmic Charter Investments",
    "Astral Yield Corporation", "Radiant Capital Management",
    "Prime Vector Equity", "Helios Bridge Markets",
    "Unified Stellar Fund", "PillarPoint Global",
    "Ascendant Financial Systems", "Constellation Partners",
    "CrestGate Advisors", "Northstar Wealth Syndicate",
    "Lumina Core Financial",
]


# ------------------------------------------------------------
#  DATA STRUCTURES
# ------------------------------------------------------------

@dataclass
class Candle:
    """Represents a single OHLC candle."""
    open: float
    high: float
    low: float
    close: float


# ------------------------------------------------------------
#  COMPANY MODEL
# ------------------------------------------------------------

class Company:
    """
    Represents a company in the trading simulation.
    Handles:
    - Ownership (player, AIs, public float)
    - Price action + candle data
    - Daily & quarterly history
    - Intra-day forming candle
    """

    TOTAL_SHARES = 10000  # Fixed supply for now

    def __init__(self, name, base_price, volatility, sector, logo=None, ai_count=10, is_player=False):
        self.name = name
        self.sector = sector
        self.logo = logo
        self.is_player = is_player

        # Core financial fields
        self.price = float(base_price)
        self.volatility = float(volatility)
        self.total_shares = Company.TOTAL_SHARES

        # Ownership fields
        self.player_shares = 0
        self.ai_owners: dict[str, int] = {}  # { "AI Name": shares }
        self.public_float = 0

        # Candle containers
        self.daily_candles: list[Candle] = []
        self.quarterly_candles: list[Candle] = []

        # Intra-day working candle
        self.current_open = self.price
        self.current_high = self.price
        self.current_low = self.price
        self.current_close = self.price

        self.ticks_today = 0  # Counts 15-minute increments

        # Assign AI shareholders (scalable 5-20)
        self.assign_ai_owners(ai_count)

        # Initialize history
        self.generate_initial_history()

    # ------------------------------------------------------------
    #  AI Ownership Assignment
    # ------------------------------------------------------------

    def assign_ai_owners(self, ai_count):
        """Distributes shares among a dynamic number of AI competitors."""
        ai_count = max(5, min(ai_count, 20))  # safety clamp

        chosen_names = random.sample(AI_NAME_BANK, ai_count)

        remaining = self.total_shares

        for ai in chosen_names:
            shares = min(random.randint(0, 10), max(0, remaining))
            self.ai_owners[ai] = shares
            remaining -= shares
            if remaining <= 0:
                remaining = 0
                break

        self.player_shares = 0
        self.public_float = max(0, remaining)

    # ------------------------------------------------------------
    #  PRICE + CANDLE ENGINE
    # ------------------------------------------------------------

    def generate_initial_history(self):
        """Creates 30 daily + 30 quarterly candles for chart warm-up."""
        for _ in range(30):
            open_p = self.price
            close_p = open_p + random.uniform(-self.volatility, self.volatility)
            high_p = max(open_p, close_p) + random.uniform(0, self.volatility)
            low_p = min(open_p, close_p) - random.uniform(0, self.volatility)

            self.daily_candles.append(
                Candle(round(open_p, 2), round(high_p, 2),
                       round(low_p, 2), round(close_p, 2))
            )

            q_close = close_p + random.uniform(-self.volatility * 2, self.volatility * 2)
            q_high = max(open_p, q_close) + random.uniform(0, self.volatility * 1.5)
            q_low = min(open_p, q_close) - random.uniform(0, self.volatility * 1.5)

            self.quarterly_candles.append(
                Candle(round(open_p, 2), round(q_high, 2),
                       round(q_low, 2), round(q_close, 2))
            )

        self.current_open = self.price
        self.current_high = self.price
        self.current_low = self.price
        self.current_close = self.price

    # ------------------------------------------------------------
    #  TICK UPDATE (15 MIN)
    # ------------------------------------------------------------

    def tick_price(self):
        """
        Engine already sets the price. This updates the forming candle
        without double-counting ticks.
        """
        self.current_close = self.price
        self.current_high = max(self.current_high, self.price)
        self.current_low = min(self.current_low, self.price)

    # ------------------------------------------------------------
    #  DAILY CANDLE FINALIZATION
    # ------------------------------------------------------------

    def finalize_daily_candle(self):
        """When a simulated day passes, close the candle."""
        candle = Candle(
            round(self.current_open, 2),
            round(self.current_high, 2),
            round(self.current_low, 2),
            round(self.current_close, 2),
        )

        self.daily_candles.append(candle)
        if len(self.daily_candles) > 30:
            self.daily_candles.pop(0)

        self.current_open = self.price
        self.current_high = self.price
        self.current_low = self.price
        self.current_close = self.price
        self.ticks_today = 0

    # ------------------------------------------------------------
    #  QUARTERLY CANDLE FINALIZATION
    # ------------------------------------------------------------

    def finalize_quarterly_candle(self):
        """After 90 days lock a new quarterly candle."""
        open_p = self.quarterly_candles[-1].close
        close_p = self.daily_candles[-1].close

        high_p = max(open_p, close_p) + random.uniform(0, self.volatility * 1.0)
        low_p = min(open_p, close_p) - random.uniform(0, self.volatility * 1.0)

        q_candle = Candle(
            round(open_p, 2),
            round(high_p, 2),
            round(low_p, 2),
            round(close_p, 2),
        )

        self.quarterly_candles.append(q_candle)

        if len(self.quarterly_candles) > 30:
            self.quarterly_candles.pop(0)

    # ------------------------------------------------------------
    #  OWNERSHIP / SHARES
    # ------------------------------------------------------------

    def update_public_float(self):
        """Recalculates float after ownership changes."""
        owned = self.player_shares + sum(self.ai_owners.values())
        self.public_float = max(0, self.total_shares - owned)

    def buy_shares(self, amount, entity="player"):
        """Player or AI buys shares from public float."""
        amount = min(amount, self.public_float)
        if amount <= 0:
            return 0

        if entity == "player":
            self.player_shares += amount
        else:
            self.ai_owners[entity] = self.ai_owners.get(entity, 0) + amount

        self.update_public_float()
        return amount

    def sell_shares(self, amount, entity="player"):
        """Player or AI sells shares back into public float."""
        if entity == "player":
            amount = min(amount, self.player_shares)
            self.player_shares -= amount
        else:
            owned = self.ai_owners.get(entity, 0)
            amount = min(amount, owned)
            self.ai_owners[entity] = owned - amount
            if self.ai_owners[entity] <= 0:
                del self.ai_owners[entity]

        self.public_float += amount
        return amount
