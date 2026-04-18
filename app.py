"""
STIR & XCCY Trading Dashboard — Flask Backend
==============================================
For Euro STIRT & Cross Currency Trading Desk (JPM, GS style)

Covers:
  - OIS curves monitoring (EUR ESTR, USD SOFR, GBP SONIA)
  - XCCY basis curves (EUR/USD, EUR/GBP, USD/JPY)
  - Basis trading P&L (carry, roll-down, spot move)
  - Curve steepener/flattener positions (2s5s, 5s10s, 2s10s)
  - XCCY positions with MTM & risk metrics
  - Stress scenarios (parallel shift, curve twist, basis shock)

Run:
    pip install -r requirements.txt
    python app.py  →  http://localhost:5003
"""

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import numpy as np
from scipy.interpolate import CubicSpline
from datetime import datetime

app = Flask(__name__)
CORS(app)

# ---------------------------------------------------------------------------
# OIS Curves (3M–30Y)
# ---------------------------------------------------------------------------
TENORS = np.array([0.25, 0.5, 1, 2, 3, 5, 7, 10, 15, 20, 30])
TENOR_LABELS = ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "15Y", "20Y", "30Y"]

# Live OIS rates (realistic as of Apr 2026)
EUR_OIS = np.array([0.0350, 0.0340, 0.0320, 0.0290, 0.0275, 0.0260, 0.0252, 0.0248, 0.0245, 0.0242, 0.0238])
USD_SOFR = np.array([0.0430, 0.0425, 0.0415, 0.0405, 0.0395, 0.0385, 0.0378, 0.0375, 0.0372, 0.0370, 0.0368])
GBP_SONIA = np.array([0.0465, 0.0460, 0.0450, 0.0440, 0.0430, 0.0420, 0.0415, 0.0410, 0.0405, 0.0400, 0.0395])

# ---------------------------------------------------------------------------
# XCCY Basis Curves (in basis points, negative = pay premium to get USD)
# ---------------------------------------------------------------------------
EUR_USD_BASIS = np.array([-15, -20, -22, -25, -24, -22, -20, -18, -16, -15, -14])
EUR_GBP_BASIS = np.array([-10, -12, -15, -18, -17, -16, -15, -14, -13, -12, -11])
USD_JPY_BASIS = np.array([-25, -28, -30, -32, -30, -28, -25, -22, -20, -18, -16])

# ---------------------------------------------------------------------------
# XCCY Positions (Active book)
# ---------------------------------------------------------------------------
XCCY_POSITIONS = [
    {"id": "XC01", "pair": "EUR/USD", "direction": "Pay EUR / Rcv USD", "notional": 250_000_000, "tenor": 2, "entry_basis": -22, "mark_basis": -25, "entry_date": "2025-10-17"},
    {"id": "XC02", "pair": "EUR/USD", "direction": "Rcv EUR / Pay USD", "notional": 180_000_000, "tenor": 5, "entry_basis": -18, "mark_basis": -22, "entry_date": "2025-04-17"},
    {"id": "XC03", "pair": "EUR/USD", "direction": "Pay EUR / Rcv USD", "notional": 150_000_000, "tenor": 10, "entry_basis": -20, "mark_basis": -18, "entry_date": "2024-10-17"},
    {"id": "XC04", "pair": "EUR/GBP", "direction": "Pay EUR / Rcv GBP", "notional": 120_000_000, "tenor": 3, "entry_basis": -15, "mark_basis": -17, "entry_date": "2025-07-17"},
    {"id": "XC05", "pair": "EUR/GBP", "direction": "Rcv EUR / Pay GBP", "notional": 100_000_000, "tenor": 5, "entry_basis": -14, "mark_basis": -16, "entry_date": "2025-01-17"},
    {"id": "XC06", "pair": "USD/JPY", "direction": "Pay USD / Rcv JPY", "notional": 80_000_000,  "tenor": 3, "entry_basis": -28, "mark_basis": -30, "entry_date": "2025-12-17"},
]

# ---------------------------------------------------------------------------
# Curve Trades (Steepeners / Flatteners)
# ---------------------------------------------------------------------------
CURVE_TRADES = [
    {"id": "CT01", "currency": "EUR", "trade": "2s5s Steepener", "dv01": 50_000, "entry_spread": 15, "mark_spread": 18, "pnl": 150_000},
    {"id": "CT02", "currency": "EUR", "trade": "5s10s Flattener", "dv01": 75_000, "entry_spread": -12, "mark_spread": -15, "pnl": -225_000},
    {"id": "CT03", "currency": "USD", "trade": "2s10s Steepener", "dv01": 100_000, "entry_spread": 20, "mark_spread": 25, "pnl": 500_000},
    {"id": "CT04", "currency": "GBP", "trade": "2s5s Flattener", "dv01": 40_000, "entry_spread": -10, "mark_spread": -8, "pnl": -80_000},
    {"id": "CT05", "currency": "USD", "trade": "5s10s Steepener", "dv01": 80_000, "entry_spread": 8, "mark_spread": 10, "pnl": 160_000},
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def curve_interp(rates, tenor):
    """Interpolate rate at given tenor"""
    cs = CubicSpline(TENORS, rates, bc_type="natural")
    return float(cs(tenor))

def compute_basis_pnl(pos):
    """Compute P&L for XCCY basis position"""
    notional = pos["notional"]
    tenor = pos["tenor"]
    entry_bp = pos["entry_basis"]
    mark_bp = pos["mark_basis"]
    direction = pos["direction"]
    
    # P&L from basis move: notional * tenor * basis_change / 10000
    basis_move_bp = mark_bp - entry_bp
    
    # Sign depends on direction: "Pay" EUR means long basis (short EUR, long USD funding)
    if "Pay EUR" in direction or "Pay USD" in direction:
        sign = 1  # Long basis move positive
    else:
        sign = -1
    
    pnl_basis = sign * notional * tenor * basis_move_bp / 10000
    
    # Carry (per year) = |basis| * notional / 10000 (simplified)
    carry_annual = abs(mark_bp) * notional / 10000 * (1 if "Pay" in direction else -1)
    
    # Roll-down: as time passes, you slide down the basis curve
    # Simplified: assume 2bp/year roll for most tenors
    roll_annual = 2 * notional / 10000 * sign
    
    return {
        "pnl_basis": round(pnl_basis, 0),
        "carry_annual": round(carry_annual, 0),
        "roll_annual": round(roll_annual, 0),
        "basis_move_bp": basis_move_bp,
        "dv01_basis": round(notional * tenor / 10000, 0),
    }

def tenor_idx(tenor_label):
    return TENOR_LABELS.index(tenor_label) if tenor_label in TENOR_LABELS else None

def yield_steepness(rates, t1, t2):
    """Compute spread between 2 tenors in bp"""
    r1 = curve_interp(rates, t1)
    r2 = curve_interp(rates, t2)
    return round((r2 - r1) * 10000, 0)

# ---------------------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/ois_curves")
def api_ois_curves():
    """Return OIS curves + key metrics"""
    curves = {
        "EUR_OIS": {
            "tenors": TENOR_LABELS,
            "rates": (EUR_OIS * 100).tolist(),
            "name": "EUR OIS (ESTR)",
            "color": "#4a8fe8",
            "2s10s": yield_steepness(EUR_OIS, 2, 10),
            "5s10s": yield_steepness(EUR_OIS, 5, 10),
            "2s5s": yield_steepness(EUR_OIS, 2, 5),
        },
        "USD_SOFR": {
            "tenors": TENOR_LABELS,
            "rates": (USD_SOFR * 100).tolist(),
            "name": "USD SOFR",
            "color": "#2dc89a",
            "2s10s": yield_steepness(USD_SOFR, 2, 10),
            "5s10s": yield_steepness(USD_SOFR, 5, 10),
            "2s5s": yield_steepness(USD_SOFR, 2, 5),
        },
        "GBP_SONIA": {
            "tenors": TENOR_LABELS,
            "rates": (GBP_SONIA * 100).tolist(),
            "name": "GBP SONIA",
            "color": "#f0a830",
            "2s10s": yield_steepness(GBP_SONIA, 2, 10),
            "5s10s": yield_steepness(GBP_SONIA, 5, 10),
            "2s5s": yield_steepness(GBP_SONIA, 2, 5),
        },
    }
    
    # Spreads
    spreads = {
        "EUR_USD": [round((USD_SOFR[i] - EUR_OIS[i]) * 10000, 0) for i in range(len(TENORS))],
        "EUR_GBP": [round((GBP_SONIA[i] - EUR_OIS[i]) * 10000, 0) for i in range(len(TENORS))],
        "USD_GBP": [round((GBP_SONIA[i] - USD_SOFR[i]) * 10000, 0) for i in range(len(TENORS))],
    }
    
    return jsonify({"curves": curves, "spreads": spreads, "tenors": TENOR_LABELS})

@app.route("/api/basis_curves")
def api_basis_curves():
    """Return XCCY basis curves"""
    return jsonify({
        "EUR_USD_BASIS": {"tenors": TENOR_LABELS, "values": EUR_USD_BASIS.tolist(), "name": "EUR/USD Basis (bp)", "color": "#e85050"},
        "EUR_GBP_BASIS": {"tenors": TENOR_LABELS, "values": EUR_GBP_BASIS.tolist(), "name": "EUR/GBP Basis (bp)", "color": "#f0a830"},
        "USD_JPY_BASIS": {"tenors": TENOR_LABELS, "values": USD_JPY_BASIS.tolist(), "name": "USD/JPY Basis (bp)", "color": "#a078e8"},
        "tenors": TENOR_LABELS,
    })

@app.route("/api/xccy_positions")
def api_xccy_positions():
    """XCCY positions with P&L"""
    total_notional = 0
    total_pnl = 0
    total_carry = 0
    total_roll = 0
    total_dv01 = 0
    rows = []
    
    for pos in XCCY_POSITIONS:
        pnl_data = compute_basis_pnl(pos)
        
        row = {
            "id": pos["id"],
            "pair": pos["pair"],
            "direction": pos["direction"],
            "notional": pos["notional"],
            "tenor": pos["tenor"],
            "entry_basis": pos["entry_basis"],
            "mark_basis": pos["mark_basis"],
            "basis_move_bp": pnl_data["basis_move_bp"],
            "pnl_basis": pnl_data["pnl_basis"],
            "carry_annual": pnl_data["carry_annual"],
            "roll_annual": pnl_data["roll_annual"],
            "dv01_basis": pnl_data["dv01_basis"],
            "entry_date": pos["entry_date"],
        }
        total_notional += pos["notional"]
        total_pnl += pnl_data["pnl_basis"]
        total_carry += pnl_data["carry_annual"]
        total_roll += pnl_data["roll_annual"]
        total_dv01 += pnl_data["dv01_basis"]
        rows.append(row)
    
    return jsonify({
        "positions": rows,
        "total_notional": total_notional,
        "total_pnl": total_pnl,
        "total_carry": total_carry,
        "total_roll": total_roll,
        "total_dv01_basis": total_dv01,
        "count": len(rows),
    })

@app.route("/api/curve_trades")
def api_curve_trades():
    """Curve steepener/flattener positions"""
    total_dv01 = 0
    total_pnl = 0
    for t in CURVE_TRADES:
        total_dv01 += t["dv01"]
        total_pnl += t["pnl"]
    
    return jsonify({
        "trades": CURVE_TRADES,
        "total_dv01": total_dv01,
        "total_pnl": total_pnl,
        "count": len(CURVE_TRADES),
    })

@app.route("/api/stress")
def api_stress():
    """Stress scenarios"""
    rate_shift = float(request.args.get("rate", 50))  # bp parallel
    basis_shock = float(request.args.get("basis", 10))  # bp basis widening
    curve_twist = float(request.args.get("twist", 0))  # bp 2s10s steepening
    
    # Impact on XCCY positions (basis move)
    xccy_impact = 0
    for pos in XCCY_POSITIONS:
        sign = 1 if "Pay EUR" in pos["direction"] or "Pay USD" in pos["direction"] else -1
        impact = sign * pos["notional"] * pos["tenor"] * basis_shock / 10000
        xccy_impact += impact
    
    # Impact on curve trades (DV01-based)
    curve_impact = 0
    for t in CURVE_TRADES:
        if "Steepener" in t["trade"]:
            curve_impact += t["dv01"] * curve_twist / 10000 * 1000  # Simplified
        else:
            curve_impact -= t["dv01"] * curve_twist / 10000 * 1000
    
    # Parallel rate impact (on all DV01)
    total_dv01 = sum(t["dv01"] for t in CURVE_TRADES)
    parallel_impact = -total_dv01 * rate_shift
    
    return jsonify({
        "scenario": f"Rates {rate_shift:+.0f}bp, Basis {basis_shock:+.0f}bp, Twist {curve_twist:+.0f}bp",
        "xccy_impact": round(xccy_impact, 0),
        "curve_impact": round(curve_impact, 0),
        "parallel_impact": round(parallel_impact, 0),
        "total_impact": round(xccy_impact + curve_impact + parallel_impact, 0),
    })

if __name__ == "__main__":
    print("STIR & XCCY Trading Dashboard running at http://localhost:5003")
    app.run(debug=True, port=5003)
