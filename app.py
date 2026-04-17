import re, json, math, os
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ─────────────────────────────────────────────────────────────────────────────
# REGIONAL DATA TABLES
# ─────────────────────────────────────────────────────────────────────────────

TAX_RATES = {'AL':0.39,'AK':1.17,'AZ':0.62,'AR':0.63,'CA':0.74,'CO':0.48,'CT':2.14,'DE':0.56,'FL':0.89,'GA':0.83,'HI':0.28,'ID':0.63,'IL':2.07,'IN':0.84,'IA':1.52,'KS':1.33,'KY':0.86,'LA':0.55,'ME':1.09,'MD':1.08,'MA':1.14,'MI':1.32,'MN':1.11,'MS':0.64,'MO':0.96,'MT':0.74,'NE':1.54,'NV':0.55,'NH':2.09,'NJ':2.23,'NM':0.67,'NY':1.40,'NC':0.78,'ND':0.98,'OH':1.59,'OK':0.89,'OR':0.91,'PA':1.49,'RI':1.53,'SC':0.57,'SD':1.17,'TN':0.66,'TX':1.63,'UT':0.52,'VT':1.78,'VA':0.75,'WA':0.92,'WV':0.59,'WI':1.73,'WY':0.57}
INS_RATES = {'AL':0.55,'AK':0.38,'AZ':0.45,'AR':0.70,'CA':0.42,'CO':0.58,'CT':0.60,'DE':0.43,'FL':1.30,'GA':0.65,'HI':0.30,'ID':0.45,'IL':0.62,'IN':0.72,'IA':0.78,'KS':1.25,'KY':0.75,'LA':1.10,'ME':0.70,'MD':0.55,'MA':0.68,'MI':0.82,'MN':0.88,'MS':0.90,'MO':0.95,'MT':0.50,'NE':1.00,'NV':0.38,'NH':0.60,'NJ':0.68,'NM':0.48,'NY':0.58,'NC':0.72,'ND':0.80,'OH':0.70,'OK':1.30,'OR':0.40,'PA':0.55,'RI':0.75,'SC':0.75,'SD':0.78,'TN':0.72,'TX':1.55,'UT':0.40,'VT':0.55,'VA':0.52,'WA':0.44,'WV':0.65,'WI':0.56,'WY':0.50}
RENT_PRICE_RATIO = {'TX':0.0070,'FL':0.0082,'AZ':0.0075,'GA':0.0078,'NC':0.0074,'OH':0.0098,'MI':0.0095,'PA':0.0082,'IL':0.0079,'CO':0.0062,'WA':0.0060,'CA':0.0052,'NY':0.0058,'NV':0.0070,'TN':0.0078,'VA':0.0065,'SC':0.0076,'MO':0.0085,'IN':0.0090,'KY':0.0088,'AL':0.0085,'MS':0.0090,'AR':0.0088,'LA':0.0080}
STATE_COST = {'TX':1.05,'FL':1.18,'CA':1.95,'NY':1.80,'CO':1.40,'WA':1.50,'AZ':1.10,'GA':1.02,'NC':0.95,'OH':0.88,'MI':0.85,'IL':1.08,'PA':0.97,'NV':1.12,'TN':0.90,'VA':1.15,'SC':0.93,'NJ':1.55,'MA':1.65,'MD':1.25,'OR':1.28}
BASE_RENTS = {1:1100, 2:1420, 3:1850, 4:2300, 5:2900}
MARKET_TRENDS = {'TX':2.0,'FL':0.5,'AZ':3.5,'GA':4.0,'NC':4.5,'OH':4.0,'MI':3.5,'PA':3.0,'IL':2.5,'CO':1.0,'WA':2.0,'CA':-1.0,'NY':2.0,'NV':3.0,'TN':3.5,'VA':3.5,'SC':4.0,'NJ':4.5,'MA':3.0,'MD':3.5}

# ─────────────────────────────────────────────────────────────────────────────
# ENGINES
# ─────────────────────────────────────────────────────────────────────────────

class RedfinEngine:
    STINGRAY = "https://www.redfin.com/stingray"
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

    def _json(self, resp):
        if not resp: return {}
        try:
            text = resp.text
            return json.loads(text[4:] if text.startswith("{}&&") else text)
        except: return {}

    def search(self, address):
        r = self.s.get(f"{self.STINGRAY}/do/location-autocomplete", params={"location": address, "v": 2})
        data = self._json(r).get("payload", {})
        exact = data.get("exactMatch")
        if exact: return exact
        for sec in data.get("sections", []):
            if sec.get("rows"): return sec["rows"][0]
        return None

    def _pid(self, result):
        if not result: return None
        id_str = str(result.get("id", ""))
        if ";" in id_str: return id_str.split(";")[0]
        m = re.search(r"/home/(\d+)", result.get("url", ""))
        return m.group(1) if m else None

    def get_details(self, pid):
        af = self._json(self.s.get(f"{self.STINGRAY}/api/home/details/aboveTheFold", params={"propertyId": pid, "accessLevel": 3}))
        bf = self._json(self.s.get(f"{self.STINGRAY}/api/home/details/belowTheFold", params={"propertyId": pid, "accessLevel": 3}))
        comps = self._json(self.s.get(f"{self.STINGRAY}/api/home/details/comps", params={"propertyId": pid, "numComps": 6}))
        return af.get("payload", {}), bf.get("payload", {}), comps.get("payload", {}).get("comps", [])

class PropertyAnalyzer:
    def __init__(self):
        self.rf = RedfinEngine()

    def _g(self, obj, *keys, default=None):
        for k in keys:
            if not isinstance(obj, dict): return default
            obj = obj.get(k, {})
        return obj if obj not in ({}, [], None, "") else default

    def analyze(self, address, strategy, down_pct, rate):
        hit = self.rf.search(address)
        if not hit: raise ValueError("Property not found. Please check the address.")
        
        pid = self.rf._pid(hit)
        if not pid: raise ValueError("Could not extract Property ID.")
        
        af, bf, comps_raw = self.rf.get_details(pid)
        state = re.search(r"\b([A-Z]{2})\b", address.upper())
        state = state.group(1) if state else "TX"
        
        # Extraction
        price = self._g(af, "listPrice", "value") or self._g(af, "priceInfo", "amount") or 400000
        sqft = self._g(af, "sqFt", "value") or 1800
        beds = int(self._g(af, "beds") or 3)
        
        # Financials
        down = round(price * down_pct / 100)
        loan = price - down
        r = rate / 100 / 12
        pi = round(loan * r * (1 + r)**360 / ((1 + r)**360 - 1)) if r > 0 else round(loan / 360)
        
        # Rental Est
        rent = round((price * RENT_PRICE_RATIO.get(state, 0.007) * 0.5 + BASE_RENTS.get(beds, 1800) * STATE_COST.get(state, 1.0) * 0.5) / 25) * 25
        
        # Expenses
        tax = round((price * TAX_RATES.get(state, 1.2) / 100) / 12)
        ins = round((price * INS_RATES.get(state, 0.6) / 100) / 12)
        hoa = self._g(af, "hoa", "value") or 0
        capex, vac, mgmt = round(price*0.01/12), round(rent*0.05), round(rent*0.08)
        total_exp = pi + tax + ins + hoa + capex + vac + mgmt
        cf = rent - total_exp
        
        return {
            "success": True,
            "address": address,
            "property": {"price": price, "beds": beds, "sqft": sqft, "type": self._g(af, "propertyType") or "Single Family"},
            "financials": {"monthly_cashflow": cf, "cap_rate": round(((cf + pi) * 12) / price * 100, 2), "down_amt": down, "monthly_pi": pi},
            "rental": {"rent_est": rent},
            "buybox": {"verdict": "BUY" if cf > 0 else "CAUTION", "reason": f"Cash flow is ${cf}/mo."}
        }

analyzer = PropertyAnalyzer()

@app.route("/")
def index(): return render_template_string(HTML)

@app.route("/analyze", methods=["POST"])
def analyze_route():
    try:
        data = request.get_json()
        return jsonify(analyzer.analyze(data['address'], data.get('strategy'), float(data.get('down_pct', 20)), float(data.get('rate', 7.0))))
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# Placeholder for your HTML string - ensure it matches your original design
HTML = """...[Your original HTML content here]...""" 

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)