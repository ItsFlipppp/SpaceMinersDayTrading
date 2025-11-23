import math
import random


class AssetManager:
    """
    Handles assets for multiple owners (player + AI).
    Assets decay and produce income each tick.
    """

    TICKS_PER_DAY = 96

    ASSET_TYPES = {
        "Asteroid Hotel": {"cost": 25000, "income_per_day": 5200, "decay": 0.0016, "boost": 0.02},
        "Mining Ship": {"cost": 18000, "income_per_day": 4100, "decay": 0.0025, "boost": 0.01},
        "Element Mine": {"cost": 12000, "income_per_day": 2600, "decay": 0.0005, "boost": 0.0},  # stable backbone
        "Orbital Refinery": {"cost": 32000, "income_per_day": 7200, "decay": 0.0030, "boost": 0.03},
        "Drone Swarm": {"cost": 14000, "income_per_day": 2300, "decay": 0.0045, "boost": 0.0},
        "Terraform Rig": {"cost": 45000, "income_per_day": 9000, "decay": 0.0030, "boost": 0.04},
        "Orbital Lab": {"cost": 22000, "income_per_day": 3600, "decay": 0.0030, "boost": 0.02},
        "Shield Array": {"cost": 28000, "income_per_day": 0, "decay": 0.0025, "boost": 0.05},
        "Black Market Node": {"cost": 9000, "income_per_day": 2200, "decay": 0.0055, "boost": -0.02},
    }

    QUALITY_TIERS = [
        ("Common", 0.9, 1.1, "#7fa0ff"),
        ("Rare", 1.05, 1.0, "#9fe6ff"),
        ("Epic", 1.2, 0.9, "#f5d76b"),
    ]

    def __init__(self):
        self.assets = {"player": []}  # owner -> list of assets

    def ensure_owner(self, owner):
        if owner not in self.assets:
            self.assets[owner] = []

    def purchase(self, asset_type, owner="player"):
        cfg = self.ASSET_TYPES.get(asset_type)
        if not cfg:
            return False, 0, False
        self.ensure_owner(owner)
        tier = random.choices(self.QUALITY_TIERS, weights=[0.55, 0.35, 0.1])[0]
        broken = random.random() < 0.15
        condition = 1.0
        efficiency = 0.7 + 0.6 * random.random()
        if broken:
            condition = 0.35
            efficiency = 0.4 + 0.2 * random.random()
        self.assets[owner].append(
            {
                "type": asset_type,
                "condition": condition,
                "value": float(cfg["cost"]),
                "efficiency": efficiency,
                "tier": tier[0],
                "tier_income": tier[1],
                "tier_decay": tier[2],
                "color": tier[3],
                "broken": broken,
            }
        )
        return True, cfg["cost"], broken

    def tick(self, ticks_per_day=None):
        """
        Returns dicts: income_by_owner, decay_by_owner.
        """
        if ticks_per_day is None:
            ticks_per_day = self.TICKS_PER_DAY

        income = {}
        decay_loss = {}
        events = []

        for owner, items in list(self.assets.items()):
            keep = []
            owner_income = 0.0
            owner_decay = 0.0
            for asset in items:
                cfg = self.ASSET_TYPES[asset["type"]]
                # income scales with condition, efficiency, tier bonus
                owner_income += (cfg["income_per_day"] / ticks_per_day) * asset["condition"] * asset["efficiency"] * asset["tier_income"]

                asset["condition"] *= (1.0 - cfg["decay"] * asset["tier_decay"])
                asset["condition"] = max(0.0, asset["condition"])

                new_value = cfg["cost"] * asset["condition"]
                owner_decay += max(0.0, asset["value"] - new_value)
                asset["value"] = new_value

                if asset["condition"] > 0.1 and asset["value"] > 100:
                    keep.append(asset)

            self.assets[owner] = keep
            income[owner] = owner_income
            decay_loss[owner] = owner_decay

        return income, decay_loss, events

    def scrap_one(self, owner="player", asset_type=None):
        self.ensure_owner(owner)
        if not self.assets[owner]:
            return 0
        if asset_type:
            pool = [a for a in self.assets[owner] if a["type"] == asset_type]
            if not pool:
                return 0
            asset = pool[0]
            self.assets[owner].remove(asset)
        else:
            asset = self.assets[owner].pop(0)
        return asset["value"] * 0.4

    def total_value(self, owner="player"):
        self.ensure_owner(owner)
        return sum(a["value"] for a in self.assets.get(owner, []))

    def ceo_rating(self, cash, portfolio_value, owner="player", disruption=0.0, trend=0.0):
        base = cash + portfolio_value + self.total_value(owner)
        if base <= 0:
            return 0
        score = min(100, int(math.log1p(base) / math.log(1.0005)))
        score += int(trend * 120)  # reward positive trend modestly
        score -= int(disruption * 0.35)  # disruption hurts
        return max(0, min(100, score))

    def snapshot(self, owner="player"):
        self.ensure_owner(owner)
        return list(self.assets.get(owner, []))

    def random_ai_pick(self, ai_owner, budget):
        self.ensure_owner(ai_owner)
        affordable = [k for k, v in self.ASSET_TYPES.items() if v["cost"] <= budget]
        if not affordable:
            return None
        # Randomly choose among affordable, bias to mid-cost
        affordable.sort(key=lambda k: self.ASSET_TYPES[k]["cost"])
        mid = affordable[len(affordable) // 2]
        choice = random.choice(affordable + [mid])  # mid appears twice for slight bias
        return choice
