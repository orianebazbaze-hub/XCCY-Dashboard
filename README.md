# STIR & XCCY Trading Dashboard

> **Euro STIR and Cross-Currency Trading Desk | Front Office**  
> Real-time OIS curve monitoring, XCCY basis trading, and curve position management.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Flask](https://img.shields.io/badge/Flask-3.0-green) ![Chart.js](https://img.shields.io/badge/Chart.js-4.4-orange)

> **Fictitious portfolio for demonstration purposes only.** All positions, curves, and basis levels are simulated for demo. Not for trading.

---

## Use Case

A **STIR & XCCY trading desk** needs to monitor:

**OIS curves** in EUR ESTR, USD SOFR, GBP SONIA (3M–30Y)  
**XCCY basis curves** for EUR/USD, EUR/GBP, USD/JPY  
**Active XCCY positions** (direction, notional, basis levels, MTM P&L)  
**Curve trades** (2s5s, 5s10s, 2s10s steepeners/flatteners)  
**P&L attribution** (basis move + carry + roll-down)  
**Stress scenarios** (rates, basis shock, curve twist)

---

## Dashboard Views

### 1. **OIS Curves**
Live OIS curves for 3 currencies (EUR ESTR, USD SOFR, GBP SONIA) from 3M to 30Y. Key metrics: 2s10s steepness per curve. Cross-currency spread table (EUR–USD, EUR–GBP, USD–GBP) per tenor.

### 2. **XCCY Basis**
Basis curves for EUR/USD, EUR/GBP, USD/JPY. Current 5Y basis levels. Interactive chart showing basis evolution across tenors.

### 3. **XCCY Positions**
Active book: 6 XCCY positions across EUR/USD, EUR/GBP, USD/JPY. Each row shows direction (Pay/Receive), notional, tenor, entry vs mark basis, basis move, realized P&L.

### 4. **Curve Trades**
Steepener/flattener positions: 5 trades across EUR, USD, GBP. DV01 per trade, entry/mark spread, P&L.

### 5. **Basis P&L Attribution**
Per position breakdown: P&L from basis move, annual carry, annual roll-down. Full attribution of basis book P&L.

### 6. **Stress Scenarios**
Interactive sliders:
- **Rate shift**: ±200bp parallel
- **Basis shock**: ±50bp
- **Curve twist**: ±50bp 2s10s steepening/flattening

Impact split: XCCY (basis move), Curve (DV01), Parallel (rate).

---

## Quickstart

```bash
pip install -r requirements.txt
python app.py
# → http://localhost:5003
```

---

## API Reference

| Endpoint | Description |
|---|---|
| `GET /api/ois_curves` | 3 OIS curves + cross-currency spreads |
| `GET /api/basis_curves` | XCCY basis curves for 3 pairs |
| `GET /api/xccy_positions` | XCCY book with MTM P&L, carry, roll |
| `GET /api/curve_trades` | Curve steepener/flattener positions |
| `GET /api/stress?rate=N&basis=M&twist=P` | Stress scenario P&L impact |

---

## Key Metrics

**OIS Monitoring:**
- **2s10s steepness**: EUR/USD/GBP current levels, historical context
- **Cross-currency spreads**: EUR-USD, EUR-GBP, USD-GBP per tenor
- **Key tenors**: 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 15Y, 20Y, 30Y

**XCCY Book:**
- **Notional**: total book size
- **Basis P&L**: realized from basis move since entry
- **Carry (annual)**: expected income from basis spread
- **Roll (annual)**: curve roll-down effect
- **DV01 basis**: sensitivity per bp basis move

**Curve Trades:**
- **DV01**: spread duration per trade
- **Entry vs Mark spread**: basis points of move
- **P&L**: realized from curve moves



---


---

## Limitations

Fictitious data — no live market feeds  
Simplified P&L model (real systems use full revaluation)  
Parallel shifts only — real stress uses key rate durations  
No options / volatility component  

## Extensions

- Live market data (Bloomberg, Refinitiv APIs)
- Monte Carlo stress scenarios (historical VaR)
- Key rate duration decomposition
- Swaption / caps-floors integration
