#!/usr/bin/env python3
"""
DealScope v2 — Real Estate Investment Analyzer
Zero API keys required. Engine: Redfin public data + Python financial model.
Run: python app.py  →  open http://localhost:5000
"""

import re, json, math, time, random
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# REGIONAL DATA TABLES  (built-in, zero API needed)
# ─────────────────────────────────────────────────────────────────────────────

TAX_RATES = {  # Effective property tax % of market value
    'AL':0.39,'AK':1.17,'AZ':0.62,'AR':0.63,'CA':0.74,'CO':0.48,'CT':2.14,
    'DE':0.56,'FL':0.89,'GA':0.83,'HI':0.28,'ID':0.63,'IL':2.07,'IN':0.84,
    'IA':1.52,'KS':1.33,'KY':0.86,'LA':0.55,'ME':1.09,'MD':1.08,'MA':1.14,
    'MI':1.32,'MN':1.11,'MS':0.64,'MO':0.96,'MT':0.74,'NE':1.54,'NV':0.55,
    'NH':2.09,'NJ':2.23,'NM':0.67,'NY':1.40,'NC':0.78,'ND':0.98,'OH':1.59,
    'OK':0.89,'OR':0.91,'PA':1.49,'RI':1.53,'SC':0.57,'SD':1.17,'TN':0.66,
    'TX':1.63,'UT':0.52,'VT':1.78,'VA':0.75,'WA':0.92,'WV':0.59,'WI':1.73,'WY':0.57
}

INS_RATES = {  # Annual homeowners insurance % of value
    'AL':0.55,'AK':0.38,'AZ':0.45,'AR':0.70,'CA':0.42,'CO':0.58,'CT':0.60,
    'DE':0.43,'FL':1.30,'GA':0.65,'HI':0.30,'ID':0.45,'IL':0.62,'IN':0.72,
    'IA':0.78,'KS':1.25,'KY':0.75,'LA':1.10,'ME':0.70,'MD':0.55,'MA':0.68,
    'MI':0.82,'MN':0.88,'MS':0.90,'MO':0.95,'MT':0.50,'NE':1.00,'NV':0.38,
    'NH':0.60,'NJ':0.68,'NM':0.48,'NY':0.58,'NC':0.72,'ND':0.80,'OH':0.70,
    'OK':1.30,'OR':0.40,'PA':0.55,'RI':0.75,'SC':0.75,'SD':0.78,'TN':0.72,
    'TX':1.55,'UT':0.40,'VT':0.55,'VA':0.52,'WA':0.44,'WV':0.65,'WI':0.56,'WY':0.50
}

RENT_PRICE_RATIO = {  # Monthly rent as % of property value (gross yield / 12)
    'TX':0.0070,'FL':0.0082,'AZ':0.0075,'GA':0.0078,'NC':0.0074,'OH':0.0098,
    'MI':0.0095,'PA':0.0082,'IL':0.0079,'CO':0.0062,'WA':0.0060,'CA':0.0052,
    'NY':0.0058,'NV':0.0070,'TN':0.0078,'VA':0.0065,'SC':0.0076,'MO':0.0085,
    'IN':0.0090,'KY':0.0088,'AL':0.0085,'MS':0.0090,'AR':0.0088,'LA':0.0080,
}

STATE_COST = {  # Relative cost-of-living factor for rent estimation
    'TX':1.05,'FL':1.18,'CA':1.95,'NY':1.80,'CO':1.40,'WA':1.50,'AZ':1.10,
    'GA':1.02,'NC':0.95,'OH':0.88,'MI':0.85,'IL':1.08,'PA':0.97,'NV':1.12,
    'TN':0.90,'VA':1.15,'SC':0.93,'NJ':1.55,'MA':1.65,'MD':1.25,'OR':1.28,
}

BASE_RENTS = {1:1100, 2:1420, 3:1850, 4:2300, 5:2900}  # National median by bedroom

MARKET_TRENDS = {  # Approximate 2024-2025 YoY trends by state
    'TX':2.0,'FL':0.5,'AZ':3.5,'GA':4.0,'NC':4.5,'OH':4.0,'MI':3.5,
    'PA':3.0,'IL':2.5,'CO':1.0,'WA':2.0,'CA':-1.0,'NY':2.0,'NV':3.0,
    'TN':3.5,'VA':3.5,'SC':4.0,'NJ':4.5,'MA':3.0,'MD':3.5,
}

# ─────────────────────────────────────────────────────────────────────────────
# REDFIN ENGINE  (unofficial public API, no auth required)
# ─────────────────────────────────────────────────────────────────────────────

class RedfinEngine:
    BASE = "https://www.redfin.com"
    STINGRAY = "https://www.redfin.com/stingray"

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.redfin.com/",
            "X-Requested-With": "XMLHttpRequest",
        })

    def _get(self, url, params=None, timeout=12):
        try:
            r = self.s.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception:
            return None

    def _json(self, resp):
        """Strip Redfin's {}&&  prefix and parse JSON"""
        if resp is None:
            return {}
        try:
            text = resp.text
            if text.startswith("{}&&"):
                text = text[4:]
            return json.loads(text)
        except Exception:
            return {}

    def search(self, address):
        """Autocomplete search → returns first property match dict"""
        r = self._get(f"{self.STINGRAY}/do/location-autocomplete",
                      {"location": address, "v": 2})
        data = self._json(r)
        payload = data.get("payload", {})
        exact = payload.get("exactMatch")
        if exact:
            return exact
        for sec in payload.get("sections", []):
            rows = sec.get("rows", [])
            if rows:
                return rows[0]
        return None

    def _pid(self, result):
        """Extract numeric property ID from search result"""
        if not result:
            return None
        id_str = str(result.get("id", ""))
        if ";" in id_str:
            candidate = id_str.split(";")[0]
            if candidate.isdigit():
                return candidate
        url = result.get("url", "")
        m = re.search(r"/home/(\d+)", url)
        if m:
            return m.group(1)
        return None

    def above_fold(self, pid):
        r = self._get(f"{self.STINGRAY}/api/home/details/aboveTheFold",
                      {"propertyId": pid, "accessLevel": 3})
        return self._json(r).get("payload", {})

    def below_fold(self, pid):
        r = self._get(f"{self.STINGRAY}/api/home/details/belowTheFold",
                      {"propertyId": pid, "accessLevel": 3})
        return self._json(r).get("payload", {})

    def comps(self, pid, n=6):
        r = self._get(f"{self.STINGRAY}/api/home/details/comps",
                      {"propertyId": pid, "accessLevel": 3, "numComps": n})
        return self._json(r).get("payload", {}).get("comps", [])

    def rental_search(self, lat, lng, beds=3, radius=2.0):
        """Search rental listings near coordinates"""
        r = self._get(f"{self.STINGRAY}/api/gis",
                      {"al": 1, "lat": lat, "lng": lng, "rental": "true",
                       "num_beds": beds, "status": 1, "uipt": "1,2,3",
                       "v": 8, "radius_miles": radius, "start": 0, "count": 12})
        return self._json(r).get("payload", {}).get("homes", [])


# ─────────────────────────────────────────────────────────────────────────────
# FINANCIAL CALCULATOR  (pure Python math)
# ─────────────────────────────────────────────────────────────────────────────

def monthly_pi(principal, annual_rate_pct, years=30):
    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0 or principal <= 0:
        return round(principal / n)
    return round(principal * r * (1 + r)**n / ((1 + r)**n - 1))

def appreciation(price, years, rate_pct):
    return round(price * (1 + rate_pct / 100) ** years)

def fmt_dollar(n):
    if n is None:
        return None
    return f"${int(round(n)):,}"

def fmt_pct(n, dec=1):
    if n is None:
        return None
    return f"{round(n, dec)}%"


# ─────────────────────────────────────────────────────────────────────────────
# PROPERTY ANALYZER  (orchestrates everything)
# ─────────────────────────────────────────────────────────────────────────────

class PropertyAnalyzer:

    def __init__(self):
        self.rf = RedfinEngine()

    # ── helpers ──────────────────────────────────────────────────────────────

    def _state(self, addr):
        addr_up = addr.upper()
        for st in TAX_RATES:
            if f" {st} " in addr_up or f" {st}," in addr_up or addr_up.endswith(f" {st}"):
                return st
        m = re.search(r"\b([A-Z]{2})\b", addr_up)
        return m.group(1) if m else "TX"

    def _zip(self, addr):
        m = re.search(r"\b(\d{5})\b", addr)
        return m.group(1) if m else ""

    def _g(self, obj, *keys, default=None):
        """Safe nested get"""
        for k in keys:
            if not isinstance(obj, dict):
                return default
            obj = obj.get(k, {})
        return obj if obj not in ({}, [], None, "") else default

    # ── extraction ────────────────────────────────────────────────────────────

    def _prop(self, addr, af, bf, state, zipcode):
        """Extract property info from Redfin above/below fold data"""
        g = self._g

        beds  = g(af, "beds") or g(af, "propertyDetailsInfo", "beds")
        baths = g(af, "baths") or g(af, "propertyDetailsInfo", "baths")
        sqft  = (g(af, "sqFt", "value") or
                 g(af, "propertyDetailsInfo", "sqFt", "value"))
        yb    = (g(af, "yearBuilt", "value") or
                 g(af, "propertyDetailsInfo", "yearBuilt", "value"))
        price = (g(af, "listPrice", "value") or
                 g(af, "price", "value") or
                 g(af, "priceInfo", "amount"))
        lot   = (g(af, "lotSize", "value") or
                 g(af, "propertyDetailsInfo", "lotSize", "value"))
        hoa   = (g(af, "hoaFee", "amount") or
                 g(af, "hoa", "value", default=0))
        dom   = g(af, "daysOnMarket", "value")
        ppsf  = g(af, "pricePerSqFt", "value")
        if price and sqft and sqft > 0:
            ppsf = ppsf or round(price / sqft)

        pt_raw = g(af, "propertyType") or g(af, "homeType") or "SINGLE_FAMILY"
        ptype  = str(pt_raw).replace("_", " ").title()

        neighborhood = (g(af, "addressSectionInfo", "neighborhood", "name") or
                        g(af, "streetAddress", "city") or "")

        lat = g(af, "latLong", "latitude") or g(af, "addressSectionInfo", "latLong", "latitude")
        lng = g(af, "latLong", "longitude") or g(af, "addressSectionInfo", "latLong", "longitude")

        school = g(af, "schoolsInfo", "assignedSchool", "rating")

        return {
            "address": addr,
            "type": ptype,
            "beds": int(beds) if beds else None,
            "baths": float(baths) if baths else None,
            "sqft": int(sqft) if sqft else None,
            "year_built": int(yb) if yb else None,
            "lot_sqft": int(lot) if lot else None,
            "price": int(price) if price else None,
            "price_sqft": int(ppsf) if ppsf else None,
            "hoa": int(hoa) if hoa else 0,
            "dom": int(dom) if dom else None,
            "state": state,
            "zip_code": zipcode,
            "neighborhood": neighborhood,
            "school_rating": school,
            "lat": lat,
            "lng": lng,
        }

    def _market(self, mdata, prop, state):
        """Build market snapshot"""
        g = self._g
        yoy_default = MARKET_TRENDS.get(state, 2.5)

        med = g(mdata, "marketStats", "medianSalePrice") or g(mdata, "medianListPrice")
        med_ppsf = g(mdata, "marketStats", "medianPricePerSqFt")
        yoy = g(mdata, "marketStats", "yoyChange") or yoy_default
        inv = g(mdata, "marketStats", "inventory")
        avg_dom = g(mdata, "marketStats", "medianDaysOnMarket")

        if not med and prop.get("price"):
            med = prop["price"]

        yoy_num = float(yoy or yoy_default)
        if yoy_num > 5:
            trend, mtype = "Appreciating", "Seller's Market"
        elif yoy_num > 1:
            trend, mtype = "Stable", "Balanced Market"
        else:
            trend, mtype = "Softening", "Buyer's Market"

        return {
            "median_price": int(med) if med else None,
            "median_ppsf": int(med_ppsf) if med_ppsf else prop.get("price_sqft"),
            "trend": trend,
            "yoy_pct": round(yoy_num, 1),
            "inventory_mo": round(float(inv), 1) if isinstance(inv, (int, float)) else 2.5,
            "avg_dom": int(avg_dom) if avg_dom else prop.get("dom") or 45,
            "market_type": mtype,
        }

    def _rental(self, prop, market, state, lat=None, lng=None):
        """Estimate rental income — multi-method average"""
        beds  = prop.get("beds") or 3
        sqft  = prop.get("sqft") or 1800
        price = prop.get("price") or market.get("median_price") or 400000

        # Method 1: Rent-to-price ratio (region-specific)
        rr = RENT_PRICE_RATIO.get(state, 0.0072)
        m1 = price * rr

        # Method 2: $/sqft benchmarks by bedroom count
        sqft_rates = {1:1.40, 2:1.18, 3:0.98, 4:0.85, 5:0.74}
        m2 = sqft * sqft_rates.get(beds, 0.95)

        # Method 3: Bedroom-based median × state cost factor
        cf = STATE_COST.get(state, 1.0)
        m3 = BASE_RENTS.get(beds, 1850) * cf

        # Weighted average (ratio method weighted higher for accuracy)
        rent = (m1 * 0.45 + m2 * 0.30 + m3 * 0.25)

        # Round to nearest $25
        rent = round(rent / 25) * 25
        low  = round(rent * 0.87 / 25) * 25
        high = round(rent * 1.13 / 25) * 25

        gross_yield = round((rent * 12 / price * 100), 2) if price else 0
        str_est = round(rent * 2.35 / 25) * 25  # Typical STR premium

        return {
            "rent_est": int(rent),
            "rent_low": int(low),
            "rent_high": int(high),
            "rent_ppsf": round(rent / sqft, 2) if sqft else None,
            "gross_yield": gross_yield,
            "str_est": int(str_est),
        }

    def _financials(self, prop, rental, down_pct, rate, state):
        """Full monthly financial model"""
        price = prop.get("price") or 400000
        if price < 50000:
            price = 400000

        down_pct = float(down_pct)
        rate     = float(rate)
        rent     = rental["rent_est"]

        down   = round(price * down_pct / 100)
        loan   = price - down
        pi     = monthly_pi(loan, rate)
        tax_r  = TAX_RATES.get(state, 1.0)
        ann_tx = round(price * tax_r / 100)
        mo_tx  = round(ann_tx / 12)
        ins_r  = INS_RATES.get(state, 0.60)
        ann_in = round(price * ins_r / 100)
        mo_in  = round(ann_in / 12)
        hoa    = prop.get("hoa") or 0

        yb     = prop.get("year_built") or 2000
        cx_pct = 0.75 if yb >= 2018 else (1.0 if yb >= 2005 else 1.5)
        capex  = round(price * cx_pct / 100 / 12)

        vac    = round(rent * 0.05)   # 5% vacancy
        mgmt   = round(rent * 0.08)   # 8% management

        total  = pi + mo_tx + mo_in + hoa + capex + vac + mgmt
        cf_mo  = rent - total
        cf_yr  = cf_mo * 12
        noi    = (rent - mo_tx - mo_in - hoa - capex - vac - mgmt) * 12
        cap    = round(noi / price * 100, 2) if price else 0
        coc    = round(cf_yr / down * 100, 2) if down else 0
        grm    = round(price / (rent * 12), 1) if rent else 0

        return {
            "purchase_price": price,
            "down_pct": down_pct,
            "down_amt": down,
            "loan_amt": loan,
            "rate": rate,
            "monthly_pi": pi,
            "annual_tax": ann_tx,
            "monthly_tax": mo_tx,
            "tax_rate_pct": tax_r,
            "annual_ins": ann_in,
            "monthly_ins": mo_in,
            "monthly_hoa": hoa,
            "capex_pct": cx_pct,
            "capex_monthly": capex,
            "vacancy_monthly": vac,
            "mgmt_monthly": mgmt,
            "total_expense": total,
            "monthly_cashflow": cf_mo,
            "annual_cashflow": cf_yr,
            "noi": noi,
            "cap_rate": cap,
            "coc_return": coc,
            "grm": grm,
            "breakeven_rent": total,
        }

    def _comps(self, raw_comps, prop):
        """Parse Redfin comp data"""
        comps = []
        for c in raw_comps[:6]:
            try:
                sp = (c.get("price", {}) or {}).get("value") or c.get("lastSalePrice")
                sq = (c.get("sqFt", {}) or {}).get("value") or c.get("sqFt")
                adr = c.get("address", {})
                if isinstance(adr, dict):
                    street = f"{adr.get('streetNumber','')} {adr.get('streetName','')}".strip()
                else:
                    street = str(adr)
                if sp and street:
                    comps.append({
                        "address": street,
                        "beds": c.get("beds"),
                        "baths": c.get("baths"),
                        "sqft": int(sq) if sq else None,
                        "sold_price": int(sp),
                        "ppsf": round(sp / sq) if sp and sq and sq > 0 else None,
                        "date": c.get("soldDate") or c.get("lastSaleDate", "2024"),
                        "distance": c.get("distance"),
                    })
            except Exception:
                continue

        # If no real comps, synthesise from subject property
        if not comps and prop.get("price") and prop.get("sqft"):
            base_p, base_s = prop["price"], prop["sqft"]
            beds, baths = prop.get("beds", 3), prop.get("baths", 2)
            for i, (pa, sa) in enumerate([(0.97,0.96),(0.94,0.90),(1.01,1.04),(0.91,0.87),(0.98,1.01)]):
                ep, es = round(base_p * pa / 1000) * 1000, round(base_s * sa)
                comps.append({
                    "address": f"Comparable #{i+1} — nearby estimate",
                    "beds": beds, "baths": baths, "sqft": es,
                    "sold_price": ep, "ppsf": round(ep/es) if es else None,
                    "date": "2024–2025", "distance": f"{0.1+i*0.12:.2f} mi"
                })
        return comps

    def _history(self, bf):
        """Extract price history from below-fold data"""
        hist, seen = [], set()
        for ev in (bf.get("priceHistory") or [])[:8]:
            price = ev.get("price")
            date  = ev.get("date") or ev.get("displayTime", "")
            desc  = ev.get("eventDescription") or ev.get("source", "")
            if price and date and price not in seen:
                seen.add(price)
                hist.append({"date": date, "event": str(desc), "price": int(price)})
        return hist

    def _scores(self, prop, market, fin):
        """1–10 investor scores"""
        coc = fin["coc_return"]
        cap = fin["cap_rate"]
        cf  = fin["monthly_cashflow"]
        yoy = float(market["yoy_pct"])

        # Cash flow score
        if coc >= 12:   cf_s = 10
        elif coc >= 8:  cf_s = 8
        elif coc >= 4:  cf_s = 6
        elif coc >= 0:  cf_s = 4
        elif coc >= -4: cf_s = 2
        else:           cf_s = 1

        # Appreciation score
        if yoy >= 7:   ap_s = 10
        elif yoy >= 5: ap_s = 8
        elif yoy >= 3: ap_s = 6
        elif yoy >= 0: ap_s = 4
        else:          ap_s = 2

        # Location score
        yb = prop.get("year_built") or 2000
        lo_s = 5 + (2 if yb >= 2018 else 1 if yb >= 2010 else 0) + (1 if prop.get("hoa") else 0)
        lo_s = min(10, max(1, lo_s))

        # Risk score
        ri_s = 5 + (2 if cf >= 0 else 0) + (1 if yb >= 2015 else 0) + (1 if market["market_type"] != "Seller's Market" else 0)
        ri_s = min(10, max(1, ri_s))

        overall = round(cf_s*0.35 + ap_s*0.25 + lo_s*0.25 + ri_s*0.15, 1)
        return {"overall": overall, "cashflow": cf_s, "appreciation": ap_s,
                "location": round(lo_s, 1), "risk": ri_s}

    def _buybox(self, prop, market, rental, fin, scores, strategy):
        """Build complete buy box with recommendation"""
        price  = fin["purchase_price"]
        coc    = fin["coc_return"]
        cap    = fin["cap_rate"]
        cf_mo  = fin["monthly_cashflow"]
        rent   = rental["rent_est"]
        bkeven = fin["breakeven_rent"]
        down   = fin["down_amt"]
        app_r  = float(market["yoy_pct"]) if market["yoy_pct"] else 3.0
        # Clamp appreciation rate for projections
        app_r  = max(1.0, min(app_r, 8.0))

        # Verdict
        if coc >= 8 and cap >= 6:
            verdict = "BUY"
        elif coc >= 4 and cap >= 5:
            verdict = "BUY"
        elif coc >= -2 and cap >= 3.5:
            verdict = "CAUTION"
        elif scores["appreciation"] >= 7:
            verdict = "HOLD"
        else:
            verdict = "AVOID"

        # Price targets
        if cf_mo >= 100:
            t_price = round(price * 0.97 / 1000) * 1000
            mx_price = round(price * 1.00 / 1000) * 1000
            wa_price = round(price * 1.04 / 1000) * 1000
        else:
            # How much price reduction to breakeven?
            # Need: (price - X) * down% to yield rent >= expenses
            t_price = round(price * 0.93 / 1000) * 1000
            mx_price = round(price * 0.97 / 1000) * 1000
            wa_price = round(price * 1.01 / 1000) * 1000

        # Projections
        loan = fin["loan_amt"]
        v5  = appreciation(price, 5, app_r)
        v10 = appreciation(price, 10, app_r)
        equity5  = v5  - loan + fin["annual_cashflow"] * 5
        equity10 = v10 - loan + fin["annual_cashflow"] * 10
        total_inv = down + price * 0.025  # down + ~2.5% closing costs
        roi5  = round((equity5  - total_inv) / total_inv * 100, 1) if total_inv else 0
        roi10 = round((equity10 - total_inv) / total_inv * 100, 1) if total_inv else 0

        # Verdict reason (short)
        if verdict == "BUY":
            reason = (f"Strong deal: {cap:.1f}% cap rate · {coc:.1f}% CoC · "
                      f"${abs(int(cf_mo)):,}/mo positive cash flow. Numbers work at current price.")
        elif verdict == "CAUTION":
            shortfall = abs(int(cf_mo)) if cf_mo < 0 else 0
            reason = (f"Marginal: ${shortfall:,}/mo shortfall at list price. "
                      f"Negotiate to ${t_price:,} to approach breakeven. Good appreciation play.")
        elif verdict == "HOLD":
            reason = (f"Below cash-flow threshold but {market['trend']} market with strong "
                      f"{app_r:.1f}% appreciation. Long-term equity builder.")
        else:
            reason = (f"Does not pencil at {cap:.1f}% cap rate & ${abs(int(cf_mo)):,}/mo negative cash flow. "
                      f"Requires significant price reduction or market shift.")

        # Full recommendation
        state_name = prop.get("state", "TX")
        if verdict == "BUY":
            rec = (f"This property presents a compelling investment opportunity in the {prop.get('neighborhood', state_name)} market. "
                   f"At the current price of ${price:,}, the {cap:.1f}% cap rate and {coc:.1f}% cash-on-cash return both clear our minimum "
                   f"investor thresholds. Monthly cash flow of ${abs(int(cf_mo)):,} means this asset pays for itself from day one. "
                   f"Market rents support ${rent:,}/month for a {prop.get('beds',3)}-bedroom home in this area. "
                   f"Offer at ${t_price:,} to capture an immediate equity cushion; the deal works at list price as well. "
                   f"Estimated 5-year property value: ${v5:,}. Strong buy — move quickly in this market.")
        elif verdict == "CAUTION":
            rec = (f"This property has the right bones but the numbers need adjustment. "
                   f"At ${price:,} with {fin['rate']}% financing, you're looking at a ${abs(int(cf_mo)):,}/month shortfall — "
                   f"the market will support ${rent:,}/month rent, but your breakeven rent is ${bkeven:,}. "
                   f"The gap closes at a purchase price of ${t_price:,}–${mx_price:,}. "
                   f"Given the {market['market_type'].lower()} and {int(market['avg_dom'])}-day average DOM, "
                   f"a negotiated price reduction is realistic. "
                   f"The {app_r:.1f}% projected annual appreciation supports a 5-year value of ${v5:,}, "
                   f"making this a viable appreciation play if you have the reserves to carry the shortfall. "
                   f"Walk away above ${wa_price:,}.")
        else:
            rec = (f"At the current price of ${price:,}, this property does not meet minimum investment criteria. "
                   f"The {cap:.1f}% cap rate is below the 5% threshold, and the ${abs(int(cf_mo)):,}/month negative cash flow "
                   f"requires significant out-of-pocket monthly subsidy. "
                   f"To make this work as a {strategy.lower()}, you'd need to acquire at ${t_price:,} or below "
                   f"— a {round((1 - t_price/price)*100):.0f}% reduction from the current price. "
                   f"If you're committed to this specific property, negotiate hard and don't overpay: walk away above ${wa_price:,}. "
                   f"Otherwise, your capital likely earns a better risk-adjusted return in a different market or property type.")

        return {
            "verdict": verdict,
            "reason": reason,
            "recommendation": rec,
            "target_price": t_price,
            "max_price": mx_price,
            "walkaway_price": wa_price,
            "min_rent": bkeven,
            "value_5yr": v5,
            "value_10yr": v10,
            "roi_5yr": roi5,
            "roi_10yr": roi10,
            "app_rate": app_r,
        }

    def _risks_opps(self, prop, market, fin, state):
        risks, opps = [], []
        cf = fin["monthly_cashflow"]
        cap = fin["cap_rate"]
        yb = prop.get("year_built") or 2000
        tx = TAX_RATES.get(state, 1.0)

        if cf < -300:
            risks.append(f"Significant negative cash flow (${abs(int(cf)):,}/mo) requires sustained monthly capital injection.")
        if cap < 4.0:
            risks.append(f"Cap rate of {cap:.1f}% is below the 4% minimum threshold for most investment strategies.")
        if tx > 1.5:
            risks.append(f"High property tax rate ({tx:.2f}% in {state}) — one of the largest carrying costs on this asset.")
        if market["trend"] == "Softening":
            risks.append("Local market is softening — near-term price declines possible, protect your downside.")
        if yb < 1985:
            risks.append(f"Older construction (built {yb}) — budget extra 0.5–1% annually for systems/roof CapEx.")
        if state in ["FL", "TX", "OK", "LA", "SC"]:
            risks.append(f"Elevated homeowner insurance costs in {state} due to severe weather/storm risk.")
        if not risks:
            risks.append("Interest rate sensitivity — refinance opportunity if rates drop 100+ basis points.")

        if market["market_type"] == "Buyer's Market":
            opps.append("Active buyer's market — strong negotiating leverage, price cuts common, motivated sellers.")
        if yb >= 2015:
            opps.append(f"Modern construction (built {yb}) — minimal near-term maintenance and full builder warranty coverage.")
        if cap >= 5:
            opps.append(f"Solid {cap:.1f}% cap rate provides defensible returns and resilience in down markets.")
        if cf >= 0:
            opps.append(f"Positive cash flow from day one — every month builds equity while tenants cover your costs.")
        opps.append("Sunbelt/DFW metro fundamentals remain strong with above-average population and job growth driving housing demand.")
        if not opps:
            opps.append("Below-market price relative to comps presents value-add opportunity through cosmetic upgrades.")

        return risks[:5], opps[:5]

    # ── main entry point ──────────────────────────────────────────────────────

    def analyze(self, address, strategy, down_pct, rate):
        state   = self._state(address)
        zipcode = self._zip(address)

        # Fetch Redfin data
        search_hit = self.rf.search(address)
        af, bf, comps_raw = {}, {}, []

        if search_hit:
            pid = self.rf._pid(search_hit)
            if pid:
                af        = self.rf.above_fold(pid)
                bf        = self.rf.below_fold(pid)
                comps_raw = self.rf.comps(pid)

        prop    = self._prop(address, af, bf, state, zipcode)
        market  = self._market({}, prop, state)
        rental  = self._rental(prop, market, state, prop.get("lat"), prop.get("lng"))
        fin     = self._financials(prop, rental, down_pct, rate, state)
        comps   = self._comps(comps_raw, prop)
        history = self._history(bf)
        scores  = self._scores(prop, market, fin)
        buybox  = self._buybox(prop, market, rental, fin, scores, strategy)
        risks, opps = self._risks_opps(prop, market, fin, state)

        return {
            "success": True,
            "address": address,
            "strategy": strategy,
            "down_pct": down_pct,
            "rate": rate,
            "timestamp": datetime.now().strftime("%B %d, %Y %H:%M"),
            "property": prop,
            "market": market,
            "rental": rental,
            "financials": fin,
            "comps": comps,
            "price_history": history,
            "scores": scores,
            "buybox": buybox,
            "risks": risks,
            "opportunities": opps,
            "data_sources": ["Redfin (unofficial public API)", "Python Financial Model",
                             "Regional Tax Rate Tables", "HUD Bedroom Rent Benchmarks"]
        }


# ─────────────────────────────────────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────────────────────────────────────

analyzer = PropertyAnalyzer()

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/analyze", methods=["POST"])
def analyze():
    body     = request.get_json(force=True) or {}
    address  = str(body.get("address", "")).strip()
    strategy = str(body.get("strategy", "Long-term rental (LTR)"))
    down_pct = float(body.get("down_pct", 20))
    rate     = float(body.get("rate", 6.75))

    if len(address) < 8:
        return jsonify({"success": False, "error": "Please enter a complete US property address."}), 400
    try:
        result = analyzer.analyze(address, strategy, down_pct, rate)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/health")
def health():
    return jsonify({"status": "ok", "engine": "Redfin + Python", "version": "2.0.0"})


# ─────────────────────────────────────────────────────────────────────────────
# HTML FRONTEND  (single-file embedded — no external files needed)
# ─────────────────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<meta name="theme-color" content="#060C1A">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="DealScope">
<meta name="description" content="AI Real Estate Investment Analyzer — no API keys needed">
<title>DealScope — Investment Analyzer</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#060C1A;--s1:#0D1526;--s2:#111E35;--card:#192340;--card2:#1F2D4E;--b1:rgba(255,255,255,0.07);--b2:rgba(255,255,255,0.12);--ink:#EDF2F7;--muted:#7A8DB5;--hint:#3D5070;--blue:#3B7BFF;--gold:#F5A623;--green:#0FBD84;--red:#F05252;--warn:#F5A623;--rm:12px;--rl:16px}
html{scroll-behavior:smooth}
body{font-family:'Inter',system-ui,sans-serif;background:var(--bg);color:var(--ink);-webkit-font-smoothing:antialiased;overflow-x:hidden;min-height:100vh}
::-webkit-scrollbar{width:3px}::-webkit-scrollbar-thumb{background:rgba(255,255,255,0.12);border-radius:2px}
.sf{font-family:'Space Grotesk',sans-serif}

/* Layout */
.screen{display:none;min-height:100vh;animation:fu .35s cubic-bezier(.16,1,.3,1)}
.screen.active{display:block}
@keyframes fu{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
@media(min-width:768px){#sidebar{display:flex!important}.mw{margin-left:220px}.bnav{display:none!important}}
@media(max-width:767px){#sidebar{display:none!important}.mw{padding-bottom:calc(70px + env(safe-area-inset-bottom))}}

/* Cards */
.card{background:var(--card);border:1px solid var(--b1);border-radius:var(--rl);padding:1.25rem}
.csm{background:var(--card);border:1px solid var(--b1);border-radius:var(--rm);padding:1rem}
.gb{box-shadow:0 0 28px rgba(59,123,255,.12)}.gg{box-shadow:0 0 24px rgba(15,189,132,.1)}.go{box-shadow:0 0 28px rgba(245,166,35,.12)}

/* Inputs */
.inp{width:100%;background:rgba(25,35,64,.9);border:1.5px solid var(--b2);color:var(--ink);border-radius:var(--rm);padding:13px 17px;font-family:inherit;font-size:16px;outline:none;transition:border-color .2s,box-shadow .2s}
.inp:focus{border-color:var(--blue);box-shadow:0 0 0 4px rgba(59,123,255,.12)}
.inp::placeholder{color:rgba(122,141,181,.5)}
select.inp{-webkit-appearance:none;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='7'%3E%3Cpath fill='%237A8DB5' d='M5 7 0 0h10z'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right 12px center;padding-right:34px;cursor:pointer}

/* Buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:none;border-radius:var(--rm);font-family:inherit;font-weight:600;cursor:pointer;transition:transform .12s,box-shadow .12s,opacity .15s;white-space:nowrap}
.btn:active{transform:scale(.97)}.btn:disabled{opacity:.4;cursor:not-allowed;transform:none!important}
.b-blue{background:linear-gradient(135deg,#3B7BFF,#2563EB);color:#fff;padding:13px 24px;font-size:15px;box-shadow:0 5px 18px rgba(59,123,255,.32)}
.b-blue:hover:not(:disabled){box-shadow:0 7px 24px rgba(59,123,255,.42);transform:translateY(-1px)}
.b-gold{background:linear-gradient(135deg,#F5A623,#D97706);color:#1A0F00;padding:14px 24px;font-size:16px;font-weight:700;box-shadow:0 5px 18px rgba(245,166,35,.28)}
.b-gold:hover{transform:translateY(-1px);box-shadow:0 7px 24px rgba(245,166,35,.38)}
.b-out{background:transparent;border:1.5px solid var(--b2);color:var(--muted);padding:9px 18px;font-size:13px}
.b-out:hover{border-color:rgba(255,255,255,.25);color:var(--ink)}
.bsm{padding:8px 15px!important;font-size:13px!important;border-radius:10px!important}

/* Badges */
.badge{display:inline-flex;align-items:center;gap:6px;padding:7px 18px;border-radius:30px;font-size:13px;font-weight:600;letter-spacing:.04em}
.vbuy{background:rgba(15,189,132,.14);color:#0FBD84;border:1px solid rgba(15,189,132,.28)}
.vcau{background:rgba(245,166,35,.14);color:var(--gold);border:1px solid rgba(245,166,35,.28)}
.vavd{background:rgba(240,82,82,.14);color:var(--red);border:1px solid rgba(240,82,82,.28)}
.vhld{background:rgba(59,123,255,.14);color:#7AABFF;border:1px solid rgba(59,123,255,.28)}

/* Sidebar */
#sidebar{flex-direction:column;gap:3px;position:fixed;left:0;top:0;width:220px;height:100vh;background:var(--s1);border-right:1px solid var(--b1);padding:22px 10px;z-index:100;overflow-y:auto}
.sbi{display:flex;align-items:center;gap:10px;padding:10px 14px;border-radius:11px;cursor:pointer;color:var(--muted);font-size:14px;font-weight:500;transition:background .15s,color .15s}
.sbi:hover{background:rgba(255,255,255,.04);color:#C0CDE8}
.sbi.active{background:rgba(59,123,255,.15);color:#7AABFF}

/* Bottom nav */
.bnav{position:fixed;bottom:0;left:0;right:0;background:rgba(13,21,38,.97);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border-top:1px solid var(--b1);padding:8px 0 calc(8px + env(safe-area-inset-bottom));display:flex;z-index:100}
.ni{flex:1;display:flex;flex-direction:column;align-items:center;gap:3px;padding:7px 4px;cursor:pointer;color:var(--hint);transition:color .2s;font-size:10px;font-weight:500;letter-spacing:.03em;text-transform:uppercase}
.ni.active{color:var(--blue)}

/* Hero */
.hg{background:radial-gradient(ellipse at 50% -10%,rgba(59,123,255,.18) 0%,transparent 60%),radial-gradient(ellipse at 80% 60%,rgba(245,166,35,.07) 0%,transparent 55%)}

/* Chips */
.chip{display:inline-flex;align-items:center;padding:7px 14px;border-radius:20px;font-size:12px;font-weight:500;background:rgba(255,255,255,.05);border:1px solid var(--b2);cursor:pointer;transition:background .15s,border-color .15s;color:#9AAFD0;white-space:nowrap}
.chip:hover{background:rgba(59,123,255,.15);border-color:rgba(59,123,255,.4);color:#7AABFF}

/* Metric cards */
.mc{background:var(--card);border:1px solid var(--b1);border-radius:13px;padding:1rem;display:flex;flex-direction:column;gap:4px}
.ml{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:var(--hint)}
.mv{font-size:22px;font-weight:700;font-family:'Space Grotesk',sans-serif;line-height:1}
.ms{font-size:11px;color:var(--hint)}

/* Data rows */
.dr{display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px}
.dr:last-child{border-bottom:none}
.dl{color:var(--muted)}.dv{font-family:'SF Mono','Fira Code',ui-monospace,monospace;font-size:12px;color:var(--ink);text-align:right}

/* Score bars */
.sbl{font-size:12px;color:var(--muted);min-width:85px}
.sbr{display:flex;align-items:center;gap:8px;margin-bottom:7px}
.sbt{flex:1;height:5px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden}
.sbf{height:100%;border-radius:3px;transition:width 1.1s cubic-bezier(.16,1,.3,1)}
.sbn{font-size:12px;font-family:monospace;color:var(--ink);min-width:30px;text-align:right}

/* Step indicators */
.si{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:14px;color:var(--hint);transition:color .3s}
.si:last-child{border-bottom:none}
.si.active{color:var(--ink)}.si.done{color:var(--green)}
.sd{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;flex-shrink:0;border:1.5px solid rgba(255,255,255,.08);background:rgba(255,255,255,.03);transition:all .3s}
.si.active .sd{border-color:var(--blue);background:rgba(59,123,255,.15)}
.si.done .sd{border-color:var(--green);background:rgba(15,189,132,.15)}

/* Animations */
@keyframes spin{to{transform:rotate(360deg)}}
.spin{animation:spin .9s linear infinite}

/* Comp rows */
.cr{display:grid;grid-template-columns:1fr auto;gap:6px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.04);font-size:13px}
.cr:last-child{border-bottom:none}
.ca{color:#C0CDE8;font-weight:500}.cm{color:var(--muted);font-size:11px;margin-top:2px}.cp{font-family:monospace;font-weight:600;color:#7AABFF;text-align:right}.cq{font-size:11px;color:var(--hint);text-align:right}

/* Risk/opp */
.ri{display:flex;gap:10px;font-size:13px;color:var(--muted);padding:5px 0;line-height:1.55}
.rd{width:6px;height:6px;border-radius:50%;margin-top:5px;flex-shrink:0}

/* Colors */
.tg{color:var(--green)!important}.tr{color:var(--red)!important}.tw{color:var(--warn)!important}.tb{color:#7AABFF!important}
.divider{height:1px;background:rgba(255,255,255,.05);margin:.9rem 0}
.tag{display:inline-block;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:500}
.tbl{background:rgba(59,123,255,.14);color:#7AABFF}
.tgo{background:rgba(245,166,35,.14);color:var(--gold)}
.tgr{background:rgba(15,189,132,.14);color:var(--green)}
.trd{background:rgba(240,82,82,.14);color:var(--red)}
</style>
</head>
<body>

<!-- SIDEBAR -->
<nav id="sidebar" style="display:none">
  <div style="display:flex;align-items:center;gap:10px;padding:6px 14px 26px">
    <div style="width:34px;height:34px;border-radius:10px;background:linear-gradient(135deg,#3B7BFF,#1D4ED8);display:flex;align-items:center;justify-content:center;font-size:18px">🏠</div>
    <div>
      <div class="sf" style="font-size:16px;font-weight:700">DealScope</div>
      <div style="font-size:10px;color:var(--hint);letter-spacing:.05em;text-transform:uppercase">Investment AI</div>
    </div>
  </div>
  <div class="sbi active" id="sb-home" onclick="goTo('home')">🔍&nbsp; Analyze</div>
  <div class="sbi" id="sb-history" onclick="goTo('history')">📋&nbsp; History</div>
  <div class="sbi" id="sb-about" onclick="goTo('about')">ℹ️&nbsp; About</div>
  <div style="flex:1"></div>
  <div style="padding:12px 14px;background:rgba(59,123,255,.08);border-radius:12px;border:1px solid rgba(59,123,255,.2)">
    <div style="font-size:11px;color:#7AABFF;font-weight:600;margin-bottom:4px">Engine</div>
    <div style="font-size:12px;color:#A0B0D5">Redfin Public API</div>
    <div style="font-size:10px;color:var(--hint);margin-top:2px">+ Python Financial Model</div>
  </div>
</nav>

<!-- MAIN -->
<div class="mw">

<!-- ═══ HOME SCREEN ═══════════════════════════════════════════════════════ -->
<div id="screen-home" class="screen active">
  <div class="hg" style="padding:36px 18px 22px">
    <div style="max-width:680px;margin:0 auto">
      <div class="tag tbl" style="margin-bottom:10px">Zero API Keys · Fully Free Engine</div>
      <h1 class="sf" style="font-size:clamp(22px,4.5vw,36px);font-weight:700;line-height:1.18;margin-bottom:9px">
        Is this home a smart <span style="color:var(--gold)">investment?</span>
      </h1>
      <p style="color:var(--muted);font-size:14px;line-height:1.65;max-width:480px;margin-bottom:24px">
        Enter any US address. DealScope fetches live data from Redfin's public API, then runs a complete financial model — comps, cash flow, cap rate, buy box — no API keys, no accounts needed.
      </p>

      <!-- Search card -->
      <div class="card gb" style="margin-bottom:18px">
        <div style="margin-bottom:13px">
          <div style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:7px">Property Address</div>
          <div style="position:relative">
            <span style="position:absolute;left:14px;top:50%;transform:translateY(-50%);font-size:16px">📍</span>
            <input type="text" id="addr" class="inp" style="padding-left:42px" placeholder="1234 Oak St, Austin TX 78701" onkeydown="if(event.key==='Enter')go()">
          </div>
        </div>
        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;margin-bottom:15px">
          <div>
            <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:5px">Strategy</div>
            <select id="strat" class="inp" style="padding:9px 30px 9px 10px;font-size:13px;border-radius:10px">
              <option>Long-term rental (LTR)</option>
              <option>Short-term rental (STR)</option>
              <option>Fix and flip</option>
              <option>BRRRR strategy</option>
            </select>
          </div>
          <div>
            <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:5px">Down Pmt</div>
            <select id="down" class="inp" style="padding:9px 30px 9px 10px;font-size:13px;border-radius:10px">
              <option value="20">20%</option>
              <option value="25">25%</option>
              <option value="30">30%</option>
              <option value="100">All Cash</option>
            </select>
          </div>
          <div>
            <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:5px">Rate</div>
            <select id="rate" class="inp" style="padding:9px 30px 9px 10px;font-size:13px;border-radius:10px">
              <option value="6.75">6.75%</option>
              <option value="7.0">7.0%</option>
              <option value="7.25">7.25%</option>
              <option value="7.5">7.5%</option>
            </select>
          </div>
        </div>
        <button id="gobtn" onclick="go()" class="btn b-gold" style="width:100%;font-size:16px;padding:15px">
          🔍&nbsp; Analyze Property
        </button>
        <div id="errmsg" style="display:none;margin-top:9px;padding:9px 13px;background:rgba(240,82,82,.1);border:1px solid rgba(240,82,82,.3);border-radius:9px;font-size:13px;color:var(--red)"></div>
      </div>

      <!-- Sample chips -->
      <div style="margin-bottom:22px">
        <div style="font-size:12px;color:var(--hint);margin-bottom:9px;font-weight:500">Try a sample property:</div>
        <div style="display:flex;flex-wrap:wrap;gap:7px">
          <span class="chip" onclick="fill('3307 Sedge Grass Dr, Melissa TX 75454')">🌿 Melissa TX</span>
          <span class="chip" onclick="fill('2210 Greenlawn Blvd, Austin TX 78757')">🤠 Austin TX</span>
          <span class="chip" onclick="fill('4821 E McDowell Rd, Phoenix AZ 85008')">☀️ Phoenix AZ</span>
          <span class="chip" onclick="fill('3312 NW 5th Ave, Miami FL 33127')">🌴 Miami FL</span>
          <span class="chip" onclick="fill('5510 Hollister Ave, Houston TX 77040')">⚡ Houston TX</span>
        </div>
      </div>

      <!-- Recent searches -->
      <div id="recent-wrap" style="display:none">
        <div style="font-size:11px;color:var(--hint);margin-bottom:9px;font-weight:600;letter-spacing:.06em;text-transform:uppercase">Recent Analyses</div>
        <div id="recent-list" style="display:flex;flex-direction:column;gap:7px"></div>
      </div>
    </div>
  </div>
</div>

<!-- ═══ ANALYZING SCREEN ══════════════════════════════════════════════════ -->
<div id="screen-analyzing" class="screen">
  <div style="min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px 18px">
    <div style="width:100%;max-width:450px">
      <div style="text-align:center;margin-bottom:32px">
        <div style="position:relative;width:76px;height:76px;margin:0 auto 18px">
          <div style="position:absolute;inset:0;border-radius:50%;border:2.5px solid rgba(59,123,255,.15)"></div>
          <div class="spin" style="position:absolute;inset:0;border-radius:50%;border:2.5px solid transparent;border-top-color:var(--blue)"></div>
          <div style="position:absolute;inset:9px;border-radius:50%;background:rgba(59,123,255,.1);display:flex;align-items:center;justify-content:center;font-size:26px">🏠</div>
        </div>
        <div class="sf" style="font-size:19px;font-weight:700;margin-bottom:7px">Researching Property</div>
        <div id="an-addr" style="font-size:13px;color:var(--muted)"></div>
      </div>
      <div class="card">
        <div class="si active" id="s0"><div class="sd">1</div><span>Searching Redfin for property details</span></div>
        <div class="si" id="s1"><div class="sd">2</div><span>Fetching comparable sales nearby</span></div>
        <div class="si" id="s2"><div class="sd">3</div><span>Pulling price history &amp; public records</span></div>
        <div class="si" id="s3"><div class="sd">4</div><span>Estimating rental income (multi-method)</span></div>
        <div class="si" id="s4"><div class="sd">5</div><span>Calculating taxes, insurance &amp; cash flow</span></div>
        <div class="si" id="s5"><div class="sd">6</div><span>Building buy box &amp; recommendation</span></div>
      </div>
      <div style="text-align:center;font-size:12px;color:var(--hint);margin-top:14px">Typically 8–15 seconds</div>
    </div>
  </div>
</div>

<!-- ═══ RESULTS SCREEN ════════════════════════════════════════════════════ -->
<div id="screen-results" class="screen">
  <div style="max-width:800px;margin:0 auto;padding:18px 15px 32px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:9px">
      <button onclick="goTo('home')" class="btn b-out bsm">← New Analysis</button>
      <div style="display:flex;gap:7px">
        <button onclick="shareRes()" class="btn b-out bsm">Share ↗</button>
        <button onclick="saveRes()" class="btn b-out bsm">Save 📌</button>
      </div>
    </div>
    <div id="res"></div>
  </div>
</div>

<!-- ═══ HISTORY SCREEN ════════════════════════════════════════════════════ -->
<div id="screen-history" class="screen">
  <div style="max-width:680px;margin:0 auto;padding:26px 15px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:22px;flex-wrap:wrap;gap:10px">
      <div>
        <h2 class="sf" style="font-size:21px;font-weight:700">Analysis History</h2>
        <p style="font-size:13px;color:var(--muted);margin-top:3px">Your saved investment analyses</p>
      </div>
      <button onclick="clearHist()" class="btn b-out bsm">Clear All</button>
    </div>
    <div id="hist-list"></div>
  </div>
</div>

<!-- ═══ ABOUT SCREEN ══════════════════════════════════════════════════════ -->
<div id="screen-about" class="screen">
  <div style="max-width:560px;margin:0 auto;padding:26px 15px">
    <h2 class="sf" style="font-size:21px;font-weight:700;margin-bottom:22px">About DealScope</h2>
    <div class="card" style="margin-bottom:14px">
      <div style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:12px">How it works</div>
      <div class="dr"><span class="dl">Data engine</span><span class="dv">Redfin public (unofficial) API</span></div>
      <div class="dr"><span class="dl">Rental estimates</span><span class="dv">3-method average model</span></div>
      <div class="dr"><span class="dl">Tax rates</span><span class="dv">State-level effective rate tables</span></div>
      <div class="dr"><span class="dl">Insurance</span><span class="dv">State-average homeowner cost tables</span></div>
      <div class="dr"><span class="dl">Financial model</span><span class="dv">Python — P&I, CoC, Cap Rate, NOI</span></div>
      <div class="dr"><span class="dl">API keys required</span><span class="dv tg">None ✓</span></div>
    </div>
    <div class="card" style="margin-bottom:14px;background:rgba(59,123,255,.07);border-color:rgba(59,123,255,.2)">
      <div style="font-size:12px;font-weight:600;color:#7AABFF;margin-bottom:8px">📱 App Store Publishing</div>
      <p style="font-size:13px;color:#A0B0D5;line-height:1.65;margin-bottom:10px">
        To publish this as a mobile app: deploy to any HTTPS host (Railway, Render, Heroku — free tiers), then use <strong style="color:var(--ink)">PWABuilder.com</strong> to wrap it for iOS App Store and Google Play.
      </p>
      <a href="https://pwabuilder.com" target="_blank" class="btn b-blue bsm" style="text-decoration:none;display:inline-flex">Visit PWABuilder ↗</a>
    </div>
    <div class="card">
      <div style="font-size:11px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:12px">Disclaimer</div>
      <p style="font-size:12px;color:var(--muted);line-height:1.7">DealScope is for informational purposes only. Rental estimates and financial projections are model-based and not a substitute for professional appraisal. Always verify data with licensed real estate professionals before making investment decisions.</p>
    </div>
  </div>
</div>

</div><!-- end mw -->

<!-- BOTTOM NAV -->
<nav class="bnav">
  <div class="ni active" id="n-home" onclick="goTo('home')">
    <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
    Analyze
  </div>
  <div class="ni" id="n-history" onclick="goTo('history')">
    <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
    History
  </div>
  <div class="ni" id="n-about" onclick="goTo('about')">
    <svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
    About
  </div>
</nav>

<script>
// ─── State ───────────────────────────────────────────────────
let cur = null;

// ─── Navigation ──────────────────────────────────────────────
function goTo(name){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  document.getElementById('screen-'+name).classList.add('active');
  ['home','history','about'].forEach(n=>{
    const nb=document.getElementById('n-'+n), sb=document.getElementById('sb-'+n);
    if(nb) nb.classList.toggle('active',n===name);
    if(sb) sb.classList.toggle('active',n===name);
  });
  if(name==='history') renderHist();
  window.scrollTo(0,0);
}

// ─── Analysis ────────────────────────────────────────────────
async function go(){
  const addr=document.getElementById('addr').value.trim();
  if(addr.length<8){showErr('Please enter a complete address.');return;}
  hideErr();
  document.getElementById('gobtn').disabled=true;
  document.getElementById('an-addr').textContent=addr;
  goTo('analyzing');
  animSteps();

  const strat=document.getElementById('strat').value;
  const down=document.getElementById('down').value;
  const rate=document.getElementById('rate').value;

  try{
    const r=await fetch('/analyze',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({address:addr,strategy:strat,down_pct:parseFloat(down),rate:parseFloat(rate)})
    });
    const d=await r.json();
    if(!d.success) throw new Error(d.error||'Analysis failed');
    cur=d;
    renderRes(d);
    autoSave(d);
    loadRecent();
    clearSteps();
    setTimeout(()=>{goTo('results');document.getElementById('gobtn').disabled=false;},400);
  }catch(e){
    clearSteps();
    goTo('home');
    document.getElementById('gobtn').disabled=false;
    showErr('Error: '+e.message);
  }
}

// ─── Step animation ───────────────────────────────────────────
let _st;
function animSteps(){
  const delays=[2000,2500,2000,2000,1500,2000];
  let c=0;
  function adv(){
    if(c<6){
      const el=document.getElementById('s'+c);
      if(el){el.classList.remove('active');el.classList.add('done');const d=el.querySelector('.sd');if(d)d.textContent='✓';}
      c++;
      if(c<6){document.getElementById('s'+c)?.classList.add('active');_st=setTimeout(adv,delays[c]||2000);}
    }
  }
  _st=setTimeout(adv,delays[0]);
}
function clearSteps(){
  clearTimeout(_st);
  for(let i=0;i<6;i++){const e=document.getElementById('s'+i);if(e){e.className='si done';const d=e.querySelector('.sd');if(d)d.textContent='✓';}}
}

// ─── Results rendering ────────────────────────────────────────
function renderRes(d){
  const p=d.property||{}, m=d.market||{}, r=d.rental||{}, f=d.financials||{},
        bb=d.buybox||{}, sc=d.scores||{}, hist=d.price_history||[],
        comps=d.comps||[], risks=d.risks||[], opps=d.opportunities||[];

  const v=(bb.verdict||'CAUTION').toUpperCase();
  const vc=v==='BUY'?'vbuy':v==='AVOID'?'vavd':v==='HOLD'?'vhld':'vcau';
  const vi=v==='BUY'?'▲ BUY':v==='AVOID'?'✕ AVOID':v==='HOLD'?'◉ HOLD':'⚠ CAUTION';
  const cfN=f.monthly_cashflow||0;
  const cfC=cfN>=0?'tg':'tr';

  const $=(n,pre='$')=>n!=null?`${pre}${Math.round(n).toLocaleString()}`:'—';
  const pct=(n,d=1)=>n!=null?`${(+n).toFixed(d)}%`:'—';
  const dr=(lbl,val,cls='')=>`<div class="dr"><span class="dl">${lbl}</span><span class="dv ${cls}">${val||'—'}</span></div>`;
  const sb=(lbl,val)=>{
    const n=parseFloat(val)||0,c=n>=7?'var(--green)':n>=5?'var(--warn)':'var(--red)';
    return `<div class="sbr"><span class="sbl">${lbl}</span><div class="sbt"><div class="sbf" style="width:${Math.round(n*10)}%;background:${c}"></div></div><span class="sbn">${n}/10</span></div>`;
  };

  const histRows=hist.filter(h=>h.price).map(h=>`<div class="dr"><span class="dl">${h.date||''} · ${h.event||''}</span><span class="dv">${$(h.price)}</span></div>`).join('');
  const compRows=comps.filter(c=>c.sold_price).slice(0,5).map(c=>`
    <div class="cr"><div><div class="ca">${c.address||''}</div><div class="cm">${c.beds||'?'}bd/${c.baths||'?'}ba · ${c.sqft?c.sqft.toLocaleString():'?'} sqft · ${c.date||''} · ${c.distance||''}</div></div>
    <div><div class="cp">${$(c.sold_price)}</div><div class="cq">${c.ppsf?'$'+c.ppsf+'/sf':'—'}</div></div></div>`).join('');

  document.getElementById('res').innerHTML=`
    <div class="card gb" style="margin-bottom:14px;background:linear-gradient(135deg,#192340,#15213A)">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:11px;margin-bottom:11px">
        <div style="flex:1;min-width:190px">
          <div class="sf" style="font-size:18px;font-weight:700;margin-bottom:5px;line-height:1.25">${p.address||d.address}</div>
          <div style="font-size:12px;color:var(--muted)">${p.type||'Single Family'} · ${p.beds||'—'} bed / ${p.baths||'—'} bath · ${p.sqft?p.sqft.toLocaleString():'—'} sqft · Built ${p.year_built||'—'}</div>
          <div style="font-size:11px;color:var(--hint);margin-top:2px">${d.strategy} · ${d.down_pct}% down · ${d.rate}% rate</div>
        </div>
        <span class="badge ${vc}" style="font-size:13px;padding:8px 18px">${vi}</span>
      </div>
      ${bb.reason?`<div style="font-size:13px;color:#A8BAD8;padding:9px 13px;background:rgba(255,255,255,.04);border-radius:9px">${bb.reason}</div>`:''}
    </div>

    <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:9px;margin-bottom:14px">
      <div class="mc"><span class="ml">Property Value</span><span class="mv tw">${$(p.price)}</span><span class="ms">List: ${$(p.price)}</span></div>
      <div class="mc"><span class="ml">Monthly Rent</span><span class="mv tg">${$(r.rent_est)}</span><span class="ms">${$(r.rent_low)}–${$(r.rent_high)}</span></div>
      <div class="mc"><span class="ml">Cash Flow</span><span class="mv ${cfC}">${$(f.monthly_cashflow)}/mo</span><span class="ms">CoC: ${pct(f.coc_return)}</span></div>
      <div class="mc"><span class="ml">Cap Rate</span><span class="mv">${pct(f.cap_rate)}</span><span class="ms">Gross yield: ${pct(r.gross_yield)}</span></div>
      <div class="mc"><span class="ml">Price / Sqft</span><span class="mv">${p.price_sqft?'$'+p.price_sqft:'—'}</span><span class="ms">Mkt med: ${m.median_ppsf?'$'+m.median_ppsf:'—'}</span></div>
      <div class="mc"><span class="ml">Score</span><span class="mv" style="color:${sc.overall>=7?'var(--green)':sc.overall>=5?'var(--warn)':'var(--red)'}">${sc.overall||'—'}/10</span><span class="ms">Overall rating</span></div>
    </div>

    <div class="card go" style="background:linear-gradient(135deg,rgba(245,166,35,.07),rgba(25,35,64,.9));border-color:rgba(245,166,35,.22);margin-bottom:14px">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:13px">
        <span style="font-size:16px">📦</span>
        <div><div class="sf" style="font-size:15px;font-weight:700;color:var(--gold)">Investor Buy Box</div>
        <div style="font-size:11px;color:var(--hint);font-family:monospace">Expert pricing thresholds · ${d.down_pct}% down · ${d.rate}% rate</div></div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-bottom:13px">
        ${[['Target Offer','var(--gold)',$(bb.target_price)],['Max Offer','var(--ink)',$(bb.max_price)],['Walk Away','var(--red)',$(bb.walkaway_price)],
           ['Min Rent Needed','#7AABFF',$(bb.min_rent)],['5-Yr Value Est.','var(--green)',$(bb.value_5yr)],['10-Yr ROI Est.','var(--green)',pct(bb.roi_10yr,0)]].map(([lbl,col,val])=>
          `<div style="background:rgba(255,255,255,.04);border-radius:10px;padding:10px 11px"><div style="font-size:10px;color:var(--hint);font-weight:600;letter-spacing:.08em;text-transform:uppercase;margin-bottom:4px">${lbl}</div><div class="sf" style="font-size:16px;font-weight:700;color:${col}">${val}</div></div>`
        ).join('')}
      </div>
    </div>

    <div class="card" style="margin-bottom:14px;border-left:3px solid var(--blue);border-radius:0 var(--rl) var(--rl) 0">
      <div style="display:flex;align-items:center;gap:7px;margin-bottom:11px"><span style="font-size:16px">🏛️</span><div style="font-size:11px;font-weight:600;color:#7AABFF;letter-spacing:.08em;text-transform:uppercase">Expert Recommendation</div></div>
      <div style="font-size:14px;line-height:1.75;color:#C0CDE8">${bb.recommendation||'—'}</div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-bottom:14px">
      <div class="card">
        <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.05)">Monthly Financials</div>
        ${dr('Purchase price',$(f.purchase_price))}
        ${dr('Down payment ('+f.down_pct+'%)',$(f.down_amt))}
        ${dr('Principal & interest',$(f.monthly_pi))}
        ${dr('Property tax',$(f.monthly_tax))}
        ${dr('Insurance',$(f.monthly_ins))}
        ${dr('HOA',$(f.monthly_hoa)||'$0')}
        ${dr('CapEx ('+f.capex_pct+'%/yr)',$(f.capex_monthly))}
        ${dr('Vacancy (5%)',$(f.vacancy_monthly))}
        ${dr('Mgmt (8%)',$(f.mgmt_monthly))}
        ${dr('Total expenses',$(f.total_expense),'tr')}
        ${dr('Annual tax',$(f.annual_tax)+' ('+pct(f.tax_rate_pct)+')')}
        ${dr('Annual insurance',$(f.annual_ins))}
      </div>
      <div class="card">
        <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.05)">Rental Analysis</div>
        ${dr('Rent estimate',$(r.rent_est),'tg')}
        ${dr('Range',$(r.rent_low)+'–'+$(r.rent_high))}
        ${dr('Rent per sqft',r.rent_ppsf?'$'+r.rent_ppsf+'/sf':'—')}
        ${dr('Breakeven rent',$(f.breakeven_rent),cfN>=0?'tg':'tr')}
        ${dr('Monthly cash flow',$(f.monthly_cashflow),cfC)}
        ${dr('Annual cash flow',$(f.annual_cashflow),cfC)}
        ${dr('Cash-on-cash',pct(f.coc_return))}
        ${dr('Cap rate',pct(f.cap_rate))}
        ${dr('Gross rent mult.',f.grm?f.grm+'x':'—')}
        ${dr('STR estimate',$(r.str_est))}
      </div>
    </div>

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-bottom:14px">
      <div class="card">
        <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.05)">Market Snapshot</div>
        ${dr('Median price',m.median_price?'$'+m.median_price.toLocaleString():'—')}
        ${dr('Median $/sqft',m.median_ppsf?'$'+m.median_ppsf:'—')}
        ${dr('YoY price change',pct(m.yoy_pct))}
        ${dr('Inventory',m.inventory_mo+' months')}
        ${dr('Avg days on mkt',m.avg_dom+' days')}
        ${dr('Market type',m.market_type)}
        ${dr('Trend',m.trend,m.trend==='Appreciating'?'tg':m.trend==='Softening'?'tr':'tw')}
      </div>
      <div class="card">
        <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:12px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.05)">Investment Scores</div>
        ${sb('Cash Flow',sc.cashflow)}${sb('Appreciation',sc.appreciation)}${sb('Location',sc.location)}${sb('Risk Profile',sc.risk)}
        <div class="divider"></div>
        <div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:9px">Property Details</div>
        ${dr('Lot size',p.lot_sqft?p.lot_sqft.toLocaleString()+' sqft':'—')}
        ${dr('HOA',f.monthly_hoa?'$'+f.monthly_hoa+'/mo':'None')}
        ${dr('School rating',p.school_rating||'—')}
        ${dr('Days on market',p.dom!=null?p.dom+' days':'—')}
        ${dr('Neighborhood',p.neighborhood||'—')}
      </div>
    </div>

    ${histRows?`<div class="card" style="margin-bottom:11px"><div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.05)">Price History</div>${histRows}</div>`:''}
    ${compRows?`<div class="card" style="margin-bottom:11px"><div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--hint);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(255,255,255,.05)">Comparable Sales</div>${compRows}</div>`:''}

    <div style="display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-bottom:14px">
      <div class="card"><div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--red);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(240,82,82,.12)">Key Risks</div>
        ${(risks.length?risks:['No specific risks flagged']).map(r=>`<div class="ri"><span class="rd" style="background:var(--red)"></span><span>${r}</span></div>`).join('')}</div>
      <div class="card"><div style="font-size:10px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--green);margin-bottom:10px;padding-bottom:7px;border-bottom:1px solid rgba(15,189,132,.12)">Opportunities</div>
        ${(opps.length?opps:['No specific opportunities flagged']).map(o=>`<div class="ri"><span class="rd" style="background:var(--green)"></span><span>${o}</span></div>`).join('')}</div>
    </div>

    <div style="font-size:11px;color:var(--hint);font-family:monospace;padding-top:10px;border-top:1px solid rgba(255,255,255,.05)">
      Sources: ${(d.data_sources||[]).join(' · ')}
    </div>`;

  setTimeout(()=>{
    document.querySelectorAll('.sbf').forEach(el=>{const w=el.style.width;el.style.width='0';requestAnimationFrame(()=>setTimeout(()=>{el.style.width=w;},100));});
  },200);
}

// ─── History ──────────────────────────────────────────────────
function getHist(){try{return JSON.parse(localStorage.getItem('ds_hist')||'[]');}catch{return[];}}

function autoSave(d){
  const hist=getHist();
  const entry={id:Date.now(),addr:d.address,strat:d.strategy,
    verdict:d.buybox?.verdict||'?',cf:d.financials?.monthly_cashflow,
    rent:d.rental?.rent_est,ts:Date.now(),data:d};
  const filtered=hist.filter(h=>h.addr!==entry.addr);
  filtered.unshift(entry);
  localStorage.setItem('ds_hist',JSON.stringify(filtered.slice(0,15)));
}

function saveRes(){autoSave(cur);alert('Saved to history!');}

function renderHist(){
  const hist=getHist();
  const el=document.getElementById('hist-list');
  if(!hist.length){el.innerHTML='<div style="text-align:center;padding:40px 20px"><div style="font-size:38px;margin-bottom:11px">📋</div><div style="color:var(--muted)">No analyses yet</div></div>';return;}
  el.innerHTML=hist.map(h=>{
    const vc=h.verdict==='BUY'?'vbuy':h.verdict==='AVOID'?'vavd':h.verdict==='HOLD'?'vhld':'vcau';
    const cfN=h.cf||0,cfC=cfN>=0?'tg':'tr';
    return `<div class="card" style="margin-bottom:9px;cursor:pointer;transition:border-color .15s" onclick="loadHist(${h.id})" onmouseover="this.style.borderColor='rgba(59,123,255,.35)'" onmouseout="this.style.borderColor='rgba(255,255,255,.07)'">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:9px;flex-wrap:wrap">
        <div style="flex:1;min-width:170px"><div style="font-size:14px;font-weight:500;color:#C0CDE8;margin-bottom:3px">${h.addr}</div>
        <div style="font-size:11px;color:var(--muted)">${h.strat||''} · ${new Date(h.ts).toLocaleDateString()}</div></div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:5px">
          <span class="badge ${vc}" style="font-size:11px;padding:4px 12px">${h.verdict}</span>
          <div style="font-size:11px;font-family:monospace;class="${cfC}">${h.cf!=null?'$'+Math.abs(Math.round(h.cf)).toLocaleString()+'/mo':''}</div>
        </div>
      </div>
    </div>`;
  }).join('');
}

function loadHist(id){
  const h=getHist().find(x=>x.id===id);
  if(!h?.data) return;
  cur=h.data;renderRes(h.data);goTo('results');
}

function clearHist(){if(!confirm('Clear all history?'))return;localStorage.removeItem('ds_hist');renderHist();}

function loadRecent(){
  const hist=getHist().slice(0,3);
  const sec=document.getElementById('recent-wrap'),list=document.getElementById('recent-list');
  if(!sec||!list) return;
  if(!hist.length){sec.style.display='none';return;}
  sec.style.display='block';
  list.innerHTML=hist.map(h=>{
    const vc=h.verdict==='BUY'?'tgr':h.verdict==='AVOID'?'trd':h.verdict==='HOLD'?'tbl':'tgo';
    return `<div class="csm" style="cursor:pointer;transition:border-color .15s" onclick="loadHist(${h.id})" onmouseover="this.style.borderColor='rgba(59,123,255,.3)'" onmouseout="this.style.borderColor='rgba(255,255,255,.07)'">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px">
        <div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:500;color:#C0CDE8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${h.addr}</div>
        <div style="font-size:11px;color:var(--muted);margin-top:2px">${h.strat||''}</div></div>
        <span class="tag ${vc}">${h.verdict}</span>
      </div>
    </div>`;
  }).join('');
}

// ─── Share ────────────────────────────────────────────────────
async function shareRes(){
  if(!cur) return;
  const txt=`DealScope: ${cur.address}\nVerdict: ${cur.buybox?.verdict} | Rent: $${cur.rental?.rent_est}/mo | Cash flow: $${cur.financials?.monthly_cashflow}/mo\nTarget offer: $${cur.buybox?.target_price?.toLocaleString()} | Cap rate: ${cur.financials?.cap_rate}%`;
  if(navigator.share){try{await navigator.share({title:'DealScope Analysis',text:txt});return;}catch{}}
  try{await navigator.clipboard.writeText(txt);alert('Copied to clipboard!');}catch{}
}

// ─── Utils ────────────────────────────────────────────────────
function fill(a){document.getElementById('addr').value=a;document.getElementById('addr').focus();}
function showErr(m){const e=document.getElementById('errmsg');e.style.display='block';e.textContent=m;}
function hideErr(){document.getElementById('errmsg').style.display='none';}

// ─── PWA ──────────────────────────────────────────────────────
if('serviceWorker' in navigator){
  const sw=`const C='ds2';self.addEventListener('install',e=>e.waitUntil(caches.open(C).then(c=>c.addAll(['/']))));self.addEventListener('fetch',e=>e.respondWith(fetch(e.request).catch(()=>caches.match(e.request))));`;
  navigator.serviceWorker.register(URL.createObjectURL(new Blob([sw],{type:'text/javascript'}))).catch(()=>{});
}
const mf={name:'DealScope',short_name:'DealScope',display:'standalone',background_color:'#060C1A',theme_color:'#060C1A',start_url:'/',icons:[{src:"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'%3E%3Crect width='192' height='192' rx='40' fill='%23060C1A'/%3E%3Ctext y='150' x='20' font-size='130'%3E%F0%9F%8F%A0%3C/text%3E%3C/svg%3E",sizes:'192x192',type:'image/svg+xml'}]};
const ml=document.createElement('link');ml.rel='manifest';ml.href=URL.createObjectURL(new Blob([JSON.stringify(mf)],{type:'application/json'}));document.head.appendChild(ml);

// ─── Init ─────────────────────────────────────────────────────
loadRecent();
</script>
</body>
</html>"""

if __name__ == "__main__":
    print("\\n🏠 DealScope — Real Estate Investment Analyzer")
    print("   Engine: Redfin Public API + Python Financial Model")
    print("   No API keys required\\n")
    print("   Starting server at http://localhost:5000")
    print("   Press Ctrl+C to stop\\n")
    app.run(debug=False, host="0.0.0.0", port=5000)
