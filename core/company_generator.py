"""
company_generator.py
--------------------

Generates dynamically-created companies for the simulation.
Each company receives:
- Name
- Sector
- Starting price
- Volatility rating
- AI count (5-20)
- Placeholder logo
"""

import random
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from core.company_model import Company


# ------------------------------------------------------------
#  NAME GENERATION BANK
# ------------------------------------------------------------

COMPANY_NAME_BANK = [
    "Solaris Dynamics",
    "Pioneer Robotics",
    "Starforge Logistics",
    "Helion Analytics",
    "Vector Mining Group",
    "Astral Systems",
    "Quantum Axis Industries",
    "DeepWell Extraction Corp",
    "NovaTerra Holdings",
    "Stellar Frontier Solutions",
    "Orbital Freight Co.",
    "Celestial Automation",
    "IonCore Technologies",
    "TriStar Resource Ventures",
    "Zenith Consolidated",
    "Stardust Ore Partners",
    "Vertex Quantum Labs",
    "Horizon Yield Systems",
    "ForgePoint Enterprises",
    "AstroLink Engineering",
    "Infinite Meridian Corp",
    "PillarPoint Mechanics",
    "LuminaWave Robotics",
    "Astrosphere Logistics",
    "Momentum Rift Partners",
]


# ------------------------------------------------------------
#  SECTOR BANK
# ------------------------------------------------------------

SECTORS = [
    "AI Research",
    "Robotics",
    "Asteroid Mining",
    "Aerospace Logistics",
    "Deep Space Energy",
    "Quantum Software",
    "NanoFabrication",
]


# ------------------------------------------------------------
#  LOGO PLACEHOLDER
# ------------------------------------------------------------

def generate_placeholder_logo():
    """Returns a small placeholder 48x48 pixmap."""
    pix = QPixmap(48, 48)
    pix.fill(Qt.GlobalColor.darkGray)
    return pix


# ------------------------------------------------------------
#  MAIN GENERATOR FUNCTION
# ------------------------------------------------------------

def generate_companies(count, difficulty="Medium", player_company_name=None):
    """Creates N companies with parameters tuned for difficulty."""
    count = max(5, min(count, 20))  # clamp 5-20

    # Difficulty affects average volatility
    if difficulty == "Easy":
        vol_range = (0.4, 1.2)
        price_range = (15, 85)
    elif difficulty == "Hard":
        vol_range = (1.0, 2.8)
        price_range = (30, 140)
    else:  # Medium
        vol_range = (0.8, 2.0)
        price_range = (20, 110)

    # AI competitor count should mirror total companies (player adds separately)
    ai_count = count

    chosen_names = random.sample(COMPANY_NAME_BANK, count)
    companies = []

    # Player company if provided
    if player_company_name:
        sector = random.choice(SECTORS)
        price = round(random.uniform(*price_range), 2)
        vol = round(random.uniform(*vol_range), 2)
        player_co = Company(
            name=player_company_name,
            base_price=price,
            volatility=vol,
            sector=sector,
            logo=generate_placeholder_logo(),
            ai_count=ai_count,
            is_player=True,
        )
        # Give CEO starter stake (10%)
        starter = int(player_co.total_shares * 0.10)
        player_co.player_shares = starter
        player_co.update_public_float()
        companies.append(player_co)

    for name in chosen_names:
        sector = random.choice(SECTORS)
        price = round(random.uniform(*price_range), 2)
        vol = round(random.uniform(*vol_range), 2)

        company = Company(
            name=name,
            base_price=price,
            volatility=vol,
            sector=sector,
            logo=generate_placeholder_logo(),
            ai_count=ai_count,
        )
        # Give AI CEO starter stake (10%)
        starter = int(company.total_shares * 0.10)
        company.player_shares = 0
        company.ai_owners["CEO"] = starter
        company.update_public_float()
        companies.append(company)

    return companies
