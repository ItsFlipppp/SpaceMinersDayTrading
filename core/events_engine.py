import random
import time


class SectorEvent:
    def __init__(self, name, sector, drift_delta=0.0, vol_delta=0.0, duration_days=2):
        self.name = name
        self.sector = sector
        self.drift_delta = drift_delta
        self.vol_delta = vol_delta
        self.duration_days = duration_days
        self.start_day = None

    def is_active(self, current_day):
        if self.start_day is None:
            return False
        return current_day < self.start_day + self.duration_days


class SectorEventEngine:
    def __init__(self, sectors):
        self.sectors = sectors
        self.active_events = []

    def maybe_spawn(self, current_day):
        # 10% daily chance to spawn an event
        if random.random() > 0.10:
            return None
        sector = random.choice(self.sectors)
        if random.random() < 0.5:
            ev = SectorEvent(
                name="Sector Tailwind",
                sector=sector,
                drift_delta=0.02,
                vol_delta=-0.1,
                duration_days=random.randint(1, 3),
            )
        else:
            ev = SectorEvent(
                name="Sector Shock",
                sector=sector,
                drift_delta=-0.02,
                vol_delta=0.15,
                duration_days=random.randint(1, 3),
            )
        ev.start_day = current_day
        self.active_events.append(ev)
        return ev

    def get_modifiers(self, sector, current_day):
        drift = 0.0
        vol = 0.0
        self.active_events = [e for e in self.active_events if e.is_active(current_day)]
        for e in self.active_events:
            if e.sector == sector:
                drift += e.drift_delta
                vol += e.vol_delta
        return drift, vol
