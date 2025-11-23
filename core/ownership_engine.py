"""
Ownership Engine
----------------
Handles:
- Player purchases / sells / dumps
- AI ownership changes
- Public float updates
- Disruption contribution from trades
"""

import random


class OwnershipEngine:
    """
    One OwnershipEngine per Company.

    Company object must provide:
        player_shares
        ai_owners (dict)
        public_float
        total_shares
        price
    """

    def __init__(self, company):
        self.company = company

    # ------------------------------------------------------------
    # PLAYER BUY LOGIC
    # ------------------------------------------------------------

    def buy_player(self, shares, disruption_engine):
        """
        Player buys X shares from the public float.
        Returns (success, disruption_gain).
        """
        c = self.company

        if shares <= 0 or shares > c.public_float:
            return False, 0.0

        c.public_float -= shares
        c.player_shares += shares

        disruption_gain = (shares / c.total_shares) * 3.5
        disruption_engine.apply_trade_disruption(disruption_gain)

        return True, disruption_gain

    # ------------------------------------------------------------
    # PLAYER SELL LOGIC (normal sell)
    # ------------------------------------------------------------

    def sell_player(self, shares, disruption_engine):
        """
        Player sells shares in an orderly way.
        Returns (success, disruption_gain, panic_chance).
        """
        c = self.company

        if shares <= 0 or shares > c.player_shares:
            return False, 0.0, 0.0

        c.player_shares -= shares
        c.public_float += shares

        disruption_gain = (shares / c.total_shares) * 2.5
        panic_chance = (shares / c.total_shares) * 0.35

        disruption_engine.apply_trade_disruption(disruption_gain)

        return True, disruption_gain, panic_chance

    # ------------------------------------------------------------
    # PLAYER DUMP LOGIC (panic)
    # ------------------------------------------------------------

    def dump_player(self, shares, disruption_engine, price_engine):
        """
        Player dumps shares onto the open market instantly.
        Returns (success, disruption_gain, panic_chance).
        """
        c = self.company

        if shares <= 0 or shares > c.player_shares:
            return False, 0.0, 0.0

        c.player_shares -= shares
        c.public_float += shares

        disruption_gain = (shares / c.total_shares) * 6.0
        panic_chance = (shares / c.total_shares) * 0.7

        disruption_engine.apply_trade_disruption(disruption_gain)
        price_engine.apply_panic_impact(
            dumped_shares=shares,
            total_shares=c.total_shares,
        )

        return True, disruption_gain, panic_chance

    # ------------------------------------------------------------
    # AI LOGIC
    # ------------------------------------------------------------

    def ai_buy(self, ai_name, shares):
        """AI buys shares from public float."""
        c = self.company
        if shares <= 0 or shares > c.public_float:
            return False

        c.public_float -= shares
        c.ai_owners[ai_name] = c.ai_owners.get(ai_name, 0) + shares
        return True

    def ai_sell(self, ai_name, shares):
        """AI sells shares back to float."""
        c = self.company
        owned = c.ai_owners.get(ai_name, 0)
        if shares <= 0 or shares > owned:
            return False

        new_amt = owned - shares
        if new_amt > 0:
            c.ai_owners[ai_name] = new_amt
        else:
            c.ai_owners.pop(ai_name, None)

        c.public_float += shares
        return True

    # ------------------------------------------------------------
    # OFFER TO AI FOR THEIR SHARES
    # ------------------------------------------------------------

    def offer_purchase_from_ai(self, ai_name, shares, disruption_engine, premium_pct=0.15, accept_bias=0.0):
        """
        Attempt to buy shares directly from an AI holder.
        Returns (accepted: bool, cleared_shares: int)
        """
        c = self.company
        owned = c.ai_owners.get(ai_name, 0)
        if shares <= 0 or owned <= 0:
            return False, 0

        shares = min(shares, owned)

        # Acceptance chance: base 35%, reduced by disruption and ownership stake, premium helps
        ownership_ratio = owned / c.total_shares
        accept_chance = 0.35 + accept_bias - (disruption_engine.value / 200.0)
        accept_chance -= ownership_ratio * 0.9  # bigger holders much less likely
        accept_chance += premium_pct * 0.6     # premium helps
        accept_chance = max(0.02, min(0.6, accept_chance))

        accepted = random.random() < accept_chance
        if not accepted:
            return False, 0

        c.ai_owners[ai_name] = owned - shares
        if c.ai_owners[ai_name] <= 0:
            del c.ai_owners[ai_name]

        c.player_shares += shares
        c.update_public_float()

        disrupt_gain = (shares / c.total_shares) * 5.0
        disruption_engine.apply_trade_disruption(disrupt_gain)

        return True, shares

    # ------------------------------------------------------------
    # UTILITIES
    # ------------------------------------------------------------

    def total_ai_shares(self):
        return sum(self.company.ai_owners.values())

    def debug_state(self):
        c = self.company
        return {
            "player": c.player_shares,
            "public_float": c.public_float,
            "ai": c.ai_owners,
        }
