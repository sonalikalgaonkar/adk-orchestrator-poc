"""Mock investment-banking data tools. Hard-coded so the demo is repeatable."""

COMPANIES = {
    "helix robotics": {"ticker": "HLXR", "sector": "Industrial automation", "hq": "Boston, MA",
                       "revenue_musd": 1240, "ebitda_musd": 205, "ceo": "Dana Whitfield",
                       "md_coverage": "Priya Raman"},
    "apex logistics": {"ticker": "APXL", "sector": "Logistics software", "hq": "Atlanta, GA",
                       "revenue_musd": 860, "ebitda_musd": 172, "ceo": "Marcus Lee",
                       "md_coverage": "Tom Becker"},
}

COMPS = {
    "HLXR": [
        {"peer": "Rockwell Automation", "ev_ebitda": 17.8, "ev_revenue": 3.6},
        {"peer": "Teradyne", "ev_ebitda": 21.4, "ev_revenue": 5.1},
        {"peer": "Cognex", "ev_ebitda": 28.9, "ev_revenue": 7.2},
    ],
    "APXL": [
        {"peer": "Descartes Systems", "ev_ebitda": 30.2, "ev_revenue": 11.0},
        {"peer": "Manhattan Associates", "ev_ebitda": 41.5, "ev_revenue": 12.3},
    ],
}

DEALS = {
    "industrial automation": [
        {"target": "Gridline Motion", "acquirer": "Siemens", "value_musd": 2100, "ev_ebitda": 19.5, "year": 2026},
        {"target": "Kestrel Vision", "acquirer": "Zebra", "value_musd": 640, "ev_ebitda": 22.0, "year": 2025},
    ],
}

RESTRICTED_LIST = {"apex logistics"}  # firm is advising a counterparty


def get_company_profile(company: str) -> dict:
    """Get a company's ticker, sector, HQ, revenue, EBITDA (USD millions), CEO and coverage MD."""
    return COMPANIES.get(company.lower(), {"error": f"No profile for {company}"})


def get_trading_comps(ticker: str) -> dict:
    """Get trading comparables (EV/EBITDA, EV/Revenue) for a ticker's public peers."""
    return {"ticker": ticker, "peers": COMPS.get(ticker.upper(), [])}


def get_recent_deals(sector: str) -> dict:
    """Get recent M&A transactions in a sector, with deal value and EV/EBITDA multiple."""
    return {"sector": sector, "deals": DEALS.get(sector.lower(), [])}


def check_restricted_list(company: str) -> dict:
    """Check whether a company is on the firm's restricted list."""
    return {"company": company, "restricted": company.lower() in RESTRICTED_LIST}


TOOLS = {f.__name__: f for f in [get_company_profile, get_trading_comps, get_recent_deals, check_restricted_list]}
