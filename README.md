
# Space Miner Guild — Market Dominion

A real-time sci-fi trading simulation where you and rival AI corporations fight over shares, assets, and control. Candles form every tick, floats squeeze, dividends pay out, and takeovers are on the table.

## Features
- **Live markets:** Intraday ticks, daily/quarterly candles, demand/sentiment-driven price moves, panic sell-offs, and disruption effects.
- **Ownership game:** Buy/sell/dump with pressure queues (buys queue when float is gone; sells trickle out), premium offers to owners, and takeovers when you control a majority.
- **Assets & dividends:** Build mining fleets, refineries, labs, hotels, and more; assets decay and boost valuation. Dividends ladder pays higher yields for bigger stakes.
- **AI competitors:** Makers, scalpers, and speculators trade, panic, and build assets; inter-company holdings simulate cross-ownership.
- **Automation:** Purchase and upgrade a trading bot; view its win/loss history and P&L.
- **UI tabs:** Trading, Assets, Reports (financials + dividends), Automation.

## Setup
1) Python 3.11+ recommended.  
2) Create a virtual env and install deps:
```bash
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```
3) Run the game:
```bash
py -3 main.py
```
<img width="589" height="463" alt="image" src="https://github.com/user-attachments/assets/add9c7a1-2626-45e6-b881-d158c6b119d4" />
<img width="2550" height="1380" alt="image" src="https://github.com/user-attachments/assets/c41758e3-ab28-406d-8d4c-44ddbf208045" />
<img width="2148" height="1353" alt="image" src="https://github.com/user-attachments/assets/63e8e63a-cabf-42f4-8d45-60ca72dd3b18" />
<img width="2179" height="1362" alt="image" src="https://github.com/user-attachments/assets/2bb74daf-ef5e-40b6-bc66-a88a52234f83" />
<img width="2163" height="1350" alt="image" src="https://github.com/user-attachments/assets/96f5eec6-3185-4477-8e83-7a639d530e4f" />






## Controls & Flow
- **Trading tab:** Select a company, place buys/sells/dumps, make offers to owners, watch pressure queues and candles update.
- **Assets tab:** View your fleet and rival holdings; buy new assets from the bottom bar.
- **Reports tab:** Per-company financial summaries and dividend streams.
- **Automation tab:** Buy/upgrade the bot; review its trade log and P&L.


## Notes
- Candles update every tick; daily/quarterly views are available.
- Float squeezes increase demand; queued buys fill when float frees up.
- Dividends use a stepped ladder—larger stakes earn more.
- Automation trades apply real buy/sell pressure and log colored wins/losses.
=======
# SpaceMinersDayTrading
This is a real-time sci‑fi trading sim where you and competing AI corporations fight over shares, assets, and control

