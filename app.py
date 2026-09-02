"""
Kulfi Ops - multi-user data entry app for the kulfi cart business.
- Mobile-friendly data entry with single-source PostgreSQL backend.
- Auto-prefill for yesterday (today - 1) from previous day's closing balances.
- Zero daily sales allowed (e.g. cart closed or no sales made).
- Purchase Order Estimator & Management with editable overall discount.
- Stock Received with editable overall discount and net cost calculation.
- Stock Removed (Wastage / Return) integrated into Available Freezer Stock.
- Freezer Analysis variance computed against physical audit date.
- Remodeled Expenses & Payments (Bills vs. Cash Outflows).
- Automatic creation of Labour Charges expenses on Daily Entry advance/food cash.
- Staff & Payroll Module (KYC, leaves, compensation plans, and settlement).
- Payslip Generator Screen & PDF Download with itemized deductions.
- Dashboard with COGS, net margin tracking, and inventory status.
"""

import streamlit as st
import altair as alt
import pandas as pd
import hmac
import re
import calendar
import os
import io
from datetime import date, datetime, timedelta
from sqlalchemy import text

# Try importing reportlab for PDF generation
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

st.set_page_config(page_title="Kulfi Ops", page_icon="🍦", layout="wide")

# ----------------------------------------------------------------------
# GLOBAL UI STYLES
# ----------------------------------------------------------------------
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
.block-container {
    padding-top: 0.8rem !important;
    padding-bottom: 1.2rem !important;
    margin-top: 0 !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] {
    background-color: transparent !important;
    height: 1rem !important;
}
html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; color: #8A5E17 !important; letter-spacing: -0.01em; }
h1 { font-size: 1.45rem !important; margin-top: 0 !important; }
h2 { font-size: 1.2rem !important; }
h3 { font-size: 1.05rem !important; }
p, span, label, .stMarkdown { color: #2A1B10; }

/* Hide stepper buttons on number inputs */
input[type=number]::-webkit-inner-spin-button, 
input[type=number]::-webkit-outer-spin-button { 
    -webkit-appearance: none !important;
    margin: 0 !important; 
}
input[type=number] { -moz-appearance: textfield !important; }
div[data-testid="stNumberInput"] button { display: none !important; }

/* High-Contrast Section Headers */
.header-box-sales {
    background: #FFF2DC;
    color: #4A2206 !important;
    border: 1.5px solid #DEB887;
    border-radius: 8px;
    padding: 7px 12px;
    font-weight: 800;
    font-size: 13px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

.header-box-restock {
    background: #EAF4EC;
    color: #124A1D !important;
    border: 1.5px solid #A8D5AF;
    border-radius: 8px;
    padding: 7px 12px;
    font-weight: 800;
    font-size: 13px;
    margin-bottom: 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}

/* Compact Flavor Card Grid */
.flavor-entry-row {
    background: #FFFFFF;
    border: 1.2px solid #E6D4B5;
    border-radius: 8px;
    padding: 5px 8px;
    margin-bottom: 5px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.flavor-title-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2px;
}
.flavor-name {
    font-weight: 800;
    font-size: 12.5px;
    color: #4A2418;
}
.badge-open {
    background: #F4E8D3;
    color: #5A3E1B;
    font-weight: 700;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 6px;
}
.badge-sold {
    background: #FCE8E2;
    color: #C43D17;
    font-weight: 800;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 6px;
}
.badge-today-open {
    background: #E8F5E9;
    color: #19692C;
    font-weight: 800;
    font-size: 11.5px;
    padding: 2px 7px;
    border-radius: 6px;
    border: 1px solid #C8E6C9;
    display: inline-block;
}

/* Compact Inputs */
.stTextInput div[data-baseweb="input"], .stNumberInput div[data-baseweb="input"] {
    min-height: 28px !important;
    height: 28px !important;
    border-radius: 6px !important;
}
.stTextInput input, .stNumberInput input {
    padding: 2px 6px !important;
    font-size: 12px !important;
    text-align: left !important;
    font-weight: 600 !important;
}
.stNumberInput label, .stTextInput label {
    font-size: 10.5px !important;
    font-weight: 700 !important;
    margin-bottom: 1px !important;
    text-align: left !important;
}

section[data-testid="stSidebar"] { 
    font-size: 14px !important; 
    border-right: 1px solid #E3CBA0; 
}
section[data-testid="stSidebar"] h2 { 
    font-size: 18px !important; 
    color: #8A5E17 !important; 
}
section[data-testid="stSidebar"] .stRadio > div { 
    gap: 3px; 
}
section[data-testid="stSidebar"] .stRadio label {
    background: #FFFBF2;
    border: 1px solid #E3CBA0;
    border-radius: 6px;
    padding: 5px 8px !important;
    margin-bottom: 2px;
}

/* Buttons */
.stButton button, [data-testid="stFormSubmitButton"] button, [data-testid="baseButton-primary"] {
    border-radius: 6px !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 0.35rem 0.75rem !important;
}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
    background: #E8542A !important;
    box-shadow: 0 2px 6px rgba(232,84,42,0.3);
}
.stButton button[kind="primary"]:hover { 
    background: #C43D17 !important; 
}

/* Metric Cards */
div[data-testid="stMetric"] {
    background: #FFFBF2;
    border: 1px solid #E3CBA0;
    border-radius: 8px;
    padding: 6px 10px; /* Slightly increased box padding */
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    height: 100%; /* Ensures all cards in a row stretch evenly */
}
div[data-testid="stMetricLabel"] { 
    font-weight: 700; 
    font-size: 10.5px !important; /* Slightly decreased font size */
    color: #7A5A34; 
    white-space: normal !important; /* Forces text to wrap instead of cutting off */
    line-height: 1.3 !important;
    height: auto !important;
    min-height: 28px; /* Ensures alignment even if some wrap and others don't */
}
div[data-testid="stMetricLabel"] > div {
    white-space: normal !important;
    overflow: visible !important;
}
div[data-testid="stMetricValue"] { 
    font-family: 'Fraunces', serif; 
    font-size: 1.05rem !important; 
    color: #4A2418; 
    margin-top: 4px;
}

/* Tables */
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
    border-radius: 8px;
    border: 1.5px solid #8A5E17 !important;
    overflow: hidden;
}
div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
    font-weight: 900 !important;
    color: #FFFFFF !important;
    background-color: #70440E !important;
    text-align: center !important;
    font-size: 12px !important;
}
div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
    text-align: center !important;
    font-size: 11.5px !important;
}
hr { border-color: #E3CBA0 !important; margin: 0.35rem 0 !important; }
</style>
""")

# ----------------------------------------------------------------------
# CONFIG & CANONICAL MAPPINGS
# ----------------------------------------------------------------------
CARTS = ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"]
CITY = "HOSUR"

PAYMENT_STATUSES = ["Pending", "Partial", "Complete"]
PO_STATUSES = ["Placed", "Pending", "In Transit", "Completed", "Cancelled"]

EXPENSE_TYPES = ["OPEX", "COGS", "CAPEX"]
EXPENSE_CATEGORIES = [
    "Cost of Goods",
    "Labour Charges",
    "Logistics & Transport",
    "Rent & Utilities",
    "Maintenance & Repairs",
    "Permits & Compliance",
    "Leakage Expense",
    "Initial Set-up Expense",
    "Initial Investment",
    "Miscellaneous Expense",
]
ATTRIBUTED_OPTIONS = ["Central / Freezer"] + CARTS
EXPENSE_STATUSES = ["Pending", "Partially Paid", "Paid", "Not Applicable", "Cancelled"]
PAYMENT_MODES = ["UPI / Bank Transfer", "Cash"]
STAFF_STATUSES = ["active", "inactive", "on_leave"]
LEAVE_STATUS_OPTIONS = ["Leave", "Sick Leave", "Casual Leave", "Absent"]
LEAVE_TYPE_OPTIONS = ["Unpaid", "Paid"]

DEFAULT_FLAVORS = [
    ("ML", "Malai", 40.0, 22.0, "ml_units"),
    ("MM", "Mini Malai", 30.0, 18.0, "mm_units"),
    ("PS", "Pista", 40.0, 22.0, "ps_units"),
    ("MN", "Mango", 40.0, 22.0, "mn_units"),
    ("KB", "Kesar Badam", 50.0, 27.5, "kb_units"),
    ("BM", "Badam Matka", 80.0, 44.0, "bm_units"),
    ("SG", "Shahi Gulab", 50.0, 27.5, "sg_units"),
    ("CH", "Chocolate", 50.0, 27.5, "ch_units"),
    ("RA", "Roasted Almond", 60.0, 33.0, "ra_units"),
]
FLAVOR_CODES = [f[0] for f in DEFAULT_FLAVORS]
N_FLAVORS = len(FLAVOR_CODES)

def _num(x):
    if x is None or pd.isna(x): return 0.0
    if isinstance(x, (int, float)): return float(x)
    s = str(x).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    neg = s.startswith("(") and s.endswith(")")
    if neg: s = s[1:-1]
    try: return -float(s) if neg else float(s)
    except ValueError: return 0.0

def _int_num(x):
    return int(round(_num(x)))

# ----------------------------------------------------------------------
# DATABASE CONNECTION
# ----------------------------------------------------------------------
try:
    db_conn = st.connection("postgresql", type="sql")
except Exception:
    db_conn = None

@st.dialog("Notification")
def show_success_modal(message):
    st.success(message)
    if st.button("OK", type="primary", use_container_width=True):
        st.rerun()

# ----------------------------------------------------------------------
# DATABASE LOADERS & HELPERS
# ----------------------------------------------------------------------
def get_flavor_meta_by_code():
    meta = {
        code: {"name": name, "mrp": float(mrp), "cost_price": float(cost), "audit_col": acol}
        for code, name, mrp, cost, acol in DEFAULT_FLAVORS
    }
    if db_conn is not None:
        try:
            df = db_conn.query("SELECT code, name, mrp, cost_price FROM flavors;", ttl="1m")
            for _, r in df.iterrows():
                code = str(r["code"]).strip()
                if code in meta:
                    meta[code]["name"] = str(r["name"])
                    meta[code]["mrp"] = float(r["mrp"])
                    meta[code]["cost_price"] = float(r["cost_price"])
        except Exception:
            pass
    return meta

FLAVOR_MAP = get_flavor_meta_by_code()

def load_active_staff_list():
    if db_conn is not None:
        try:
            df = db_conn.query("SELECT name FROM staff WHERE status = 'active' ORDER BY name ASC;", ttl="1m")
            if not df.empty:
                return ["Select Staff"] + df["name"].tolist()
        except Exception:
            pass
    return ["Select Staff"]

def get_latest_cart_closing_state(cart_name, before_date):
    if db_conn is None: return {}, ""
    query = """
    SELECT e.staff_name, json_agg(json_build_object('code', i.flavor_code, 'close', i.closing_units)) AS items
    FROM daily_cart_entries e
    LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
    WHERE e.cart_name = :cart AND e.entry_date < :bdate
    GROUP BY e.id, e.entry_date, e.staff_name ORDER BY e.entry_date DESC LIMIT 1;
    """
    try:
        df = db_conn.query(query, params={"cart": cart_name, "bdate": before_date}, ttl="0s")
        if not df.empty:
            r = df.iloc[0]
            staff = str(r["staff_name"]) if pd.notna(r["staff_name"]) else ""
            items = r["items"] if isinstance(r["items"], list) else []
            closings = {str(itm.get("code")).strip(): int(itm.get("close") or 0) for itm in items if isinstance(itm, dict) and itm.get("code")}
            return closings, staff
    except Exception:
        pass
    return {}, ""

def list_daily_entries_with_prefill():
    entries = []
    if db_conn is not None:
        query = """
        SELECT e.id AS db_id, e.entry_date, e.cart_name, e.staff_name, e.total_collection, e.phonepe, e.cash, e.staff_advance, e.food_tea_cash, e.remarks,
            json_agg(json_build_object('code', i.flavor_code, 'open', i.opening_units, 'add', i.added_units, 'sold', i.sold_units, 'close', i.closing_units)) AS items
        FROM daily_cart_entries e
        LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
        GROUP BY e.id, e.entry_date, e.cart_name, e.staff_name, e.total_collection, e.phonepe, e.cash, e.staff_advance, e.food_tea_cash, e.remarks
        ORDER BY e.entry_date DESC, e.cart_name ASC;
        """
        df = db_conn.query(query, ttl="0s")
        if not df.empty:
            for _, r in df.iterrows():
                raw_items = r.get("items") or []
                items_by_code = {str(itm.get("code")).strip(): itm for itm in raw_items if isinstance(itm, dict) and itm.get("code")}
                
                entries.append({
                    "db_id": r["db_id"], "date": pd.to_datetime(r["entry_date"]), "cart": str(r["cart_name"]).strip(),
                    "by_code": {code: {"opening": int(items_by_code.get(code, {}).get("open") or 0), "added": int(items_by_code.get(code, {}).get("add") or 0), "sold": int(items_by_code.get(code, {}).get("sold") or 0), "closing": int(items_by_code.get(code, {}).get("close") or 0)} for code in FLAVOR_CODES},
                    "total": float(r["total_collection"]) if pd.notna(r["total_collection"]) else 0.0, "phonepe": float(r["phonepe"]) if pd.notna(r["phonepe"]) else 0.0, "cash": float(r["cash"]) if pd.notna(r["cash"]) else 0.0, "remarks": str(r["remarks"]) if pd.notna(r["remarks"]) else "",
                    "staff_name": str(r["staff_name"]) if pd.notna(r["staff_name"]) else "", "staff_advance": float(r["staff_advance"]) if pd.notna(r["staff_advance"]) else 0.0, "food_tea_cash": float(r["food_tea_cash"]) if pd.notna(r["food_tea_cash"]) else 0.0, "is_prefill": False
                })

    yesterday = date.today() - timedelta(days=1)
    existing_yesterday_carts = {e["cart"] for e in entries if e["date"].date() == yesterday}

    for cart in CARTS:
        if cart not in existing_yesterday_carts:
            prev_closings, prev_staff = get_latest_cart_closing_state(cart, yesterday)
            by_code = {code: {"opening": prev_closings.get(code, 0), "added": 0, "closing": prev_closings.get(code, 0), "sold": 0} for code in FLAVOR_CODES}
            entries.append({
                "db_id": f"prefill_{cart}_{yesterday.strftime('%Y%m%d')}", "date": pd.Timestamp(yesterday), "cart": cart, "by_code": by_code,
                "total": 0.0, "phonepe": 0.0, "cash": 0.0, "remarks": "", "staff_name": prev_staff, "staff_advance": 0.0, "food_tea_cash": 0.0, "is_prefill": True
            })

    entries.sort(key=lambda x: (x["date"], x["cart"]), reverse=True)
    return entries

def sync_daily_entry(entry_date, cart_name, added_map, closing_map, opening_map, sold_map, total, phonepe, cash, remarks, staff_name="", staff_advance=0.0, food_tea_cash=0.0):
    if db_conn is not None:
        with db_conn.session as s:
            res = s.execute(
                text("""
                INSERT INTO daily_cart_entries (entry_date, cart_name, city, staff_name, total_collection, phonepe, cash, staff_advance, food_tea_cash, remarks)
                VALUES (:date, :cart, :city, :staff, :tot, :ph, :cash, :adv, :food, :rem)
                ON CONFLICT (entry_date, cart_name) DO UPDATE 
                SET staff_name = EXCLUDED.staff_name, total_collection = EXCLUDED.total_collection, phonepe = EXCLUDED.phonepe, cash = EXCLUDED.cash, staff_advance = EXCLUDED.staff_advance, food_tea_cash = EXCLUDED.food_tea_cash, remarks = EXCLUDED.remarks
                RETURNING id;
                """),
                {"date": entry_date, "cart": cart_name, "city": CITY, "staff": staff_name, "tot": float(total), "ph": float(phonepe), "cash": float(cash), "adv": float(staff_advance), "food": float(food_tea_cash), "rem": str(remarks)}
            )
            daily_id = res.scalar()
            
            s.execute(text("DELETE FROM daily_cart_items WHERE daily_entry_id = :id;"), {"id": daily_id})
            for code in FLAVOR_CODES:
                s.execute(
                    text("""
                    INSERT INTO daily_cart_items (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
                    VALUES (:eid, :code, :open, :add, :sold, :close);
                    """),
                    {"eid": daily_id, "code": code, "open": int(opening_map[code]), "add": int(added_map[code]), "sold": int(sold_map[code]), "close": int(closing_map[code])}
                )

            s.execute(text("DELETE FROM expenses WHERE remarks LIKE :tag;"), {"tag": f"[Auto: Daily Entry #{daily_id}]%"})

            if float(staff_advance) > 0 and staff_name:
                res_adv = s.execute(
                    text("""
                    INSERT INTO expenses (expense_date, expense_type, category, sub_category, description, total_amount, attributed_to, vendor_name, staff_name, status, recorded_by, remarks) 
                    VALUES (:ed, 'OPEX', 'Labour Charges', 'Staff Advance', :desc, :amt, :attr, :vendor, :staff, 'Paid', 'Daily Entry Auto', :rem) RETURNING id;
                    """),
                    {"ed": entry_date, "desc": f"Daily Cart Cash Advance - {staff_name} ({cart_name})", "amt": float(staff_advance), "attr": cart_name, "vendor": staff_name, "staff": staff_name, "rem": f"[Auto: Daily Entry #{daily_id}] Staff Advance"}
                )
                exp_adv_id = res_adv.scalar()
                s.execute(
                    text("""
                    INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes) 
                    VALUES (:eid, :pdate, :pamt, 'Cash', :pref, :pto, 'Cart Cash', :notes);
                    """),
                    {"eid": exp_adv_id, "pdate": entry_date, "pamt": float(staff_advance), "pref": f"CART-ADV-{entry_date.strftime('%Y%m%d')}", "pto": staff_name, "notes": f"Cash advance disbursed from daily sales collection at {cart_name}"}
                )

            if float(food_tea_cash) > 0 and staff_name:
                res_food = s.execute(
                    text("""
                    INSERT INTO expenses (expense_date, expense_type, category, sub_category, description, total_amount, attributed_to, vendor_name, staff_name, status, recorded_by, remarks) 
                    VALUES (:ed, 'OPEX', 'Labour Charges', 'Food & Tea', :desc, :amt, :attr, :vendor, :staff, 'Paid', 'Daily Entry Auto', :rem) RETURNING id;
                    """),
                    {"ed": entry_date, "desc": f"Daily Food & Tea Allowance - {staff_name} ({cart_name})", "amt": float(food_tea_cash), "attr": cart_name, "vendor": staff_name, "staff": staff_name, "rem": f"[Auto: Daily Entry #{daily_id}] Food & Tea Cash"}
                )
                exp_food_id = res_food.scalar()
                s.execute(
                    text("""
                    INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes) 
                    VALUES (:eid, :pdate, :pamt, 'Cash', :pref, :pto, 'Cart Cash', :notes);
                    """),
                    {"eid": exp_food_id, "pdate": entry_date, "pamt": float(food_tea_cash), "pref": f"CART-FOOD-{entry_date.strftime('%Y%m%d')}", "pto": staff_name, "notes": f"Daily food and tea cash allowance disbursed from cart collection at {cart_name}"}
                )
            s.commit()

def sync_today_restock_entry(today_date, cart_name, staff_name, today_prev_closing_map, today_added_map):
    if db_conn is not None:
        with db_conn.session as s:
            res = s.execute(
                text("SELECT id FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :cart;"),
                {"dt": today_date, "cart": cart_name}
            ).fetchone()
            
            if res:
                today_id = res[0]
                if staff_name:
                    s.execute(text("UPDATE daily_cart_entries SET staff_name = COALESCE(NULLIF(:st, ''), staff_name) WHERE id = :id;"), {"st": staff_name, "id": today_id})
            else:
                res_ins = s.execute(
                    text("""
                    INSERT INTO daily_cart_entries (entry_date, cart_name, city, staff_name, total_collection, phonepe, cash, staff_advance, food_tea_cash, remarks)
                    VALUES (:dt, :cart, :city, :st, 0, 0, 0, 0, 0, '') RETURNING id;
                    """),
                    {"dt": today_date, "cart": cart_name, "city": CITY, "st": staff_name}
                )
                today_id = res_ins.scalar()

            for code in FLAVOR_CODES:
                open_u = int(today_prev_closing_map[code])
                add_u = int(today_added_map.get(code, 0))
                close_u = open_u + add_u
                
                item_res = s.execute(
                    text("SELECT id FROM daily_cart_items WHERE daily_entry_id = :eid AND flavor_code = :code;"),
                    {"eid": today_id, "code": code}
                ).fetchone()
                
                if item_res:
                    s.execute(
                        text("""
                        UPDATE daily_cart_items
                        SET opening_units = :open, added_units = :add, closing_units = :close, sold_units = GREATEST(0, :open + :add - :close)
                        WHERE daily_entry_id = :eid AND flavor_code = :code;
                        """),
                        {"eid": today_id, "code": code, "open": open_u, "add": add_u, "close": close_u}
                    )
                else:
                    s.execute(
                        text("""
                        INSERT INTO daily_cart_items (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
                        VALUES (:eid, :code, :open, :add, 0, :close);
                        """),
                        {"eid": today_id, "code": code, "open": open_u, "add": add_u, "close": close_u}
                    )
            s.commit()

def load_db_daily_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT e.entry_date AS "Date", e.cart_name AS "Cart", e.total_collection AS "Total_Collection", e.phonepe AS "PhonePe", e.cash AS "Cash", e.staff_name AS "Staff_Name", e.staff_advance AS "Staff_Advance", e.food_tea_cash AS "Food_Tea_Cash", e.remarks AS "Remarks", COALESCE(SUM(i.sold_units), 0) AS "Sold_Total", COALESCE(SUM(i.closing_units), 0) AS "Closing_Total"
    FROM daily_cart_entries e LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
    GROUP BY e.id, e.entry_date, e.cart_name, e.total_collection, e.phonepe, e.cash, e.staff_name, e.staff_advance, e.food_tea_cash, e.remarks ORDER BY e.entry_date DESC;
    """
    df = db_conn.query(query, ttl="0s")
    if not df.empty: df["Date"] = pd.to_datetime(df["Date"])
    return df

def load_db_flavor_sales(start_date=None, end_date=None):
    if db_conn is None: return pd.DataFrame()
    where_clauses, params = [], {}
    if start_date: where_clauses.append("e.entry_date >= :sdate"); params["sdate"] = start_date
    if end_date: where_clauses.append("e.entry_date <= :edate"); params["edate"] = end_date
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    query = f"""
    SELECT f.code, f.name AS "Flavour", f.mrp, f.cost_price, COALESCE(SUM(i.sold_units), 0) AS "Units sold", COALESCE(SUM(i.sold_units), 0) * f.mrp AS "Est. revenue (₹)", COALESCE(SUM(i.sold_units), 0) * f.cost_price AS "COGS (₹)"
    FROM flavors f LEFT JOIN daily_cart_items i ON f.code = i.flavor_code LEFT JOIN daily_cart_entries e ON i.daily_entry_id = e.id {where_sql}
    GROUP BY f.code, f.name, f.mrp, f.cost_price ORDER BY "Units sold" DESC;
    """
    return db_conn.query(query, params=params, ttl="0s")

def load_db_expenses_list():
    if db_conn is None: return []
    query = """
    SELECT id, expense_date AS "Date", description AS "Description", total_amount AS "Amount", category AS "Category", sub_category AS "Sub_Category", expense_type AS "Expense_Type", attributed_to AS "Attributed_To", vendor_name AS "Vendor", staff_name AS "Staff_Name", status AS "Status", remarks AS "Remarks"
    FROM expenses ORDER BY expense_date DESC, id DESC;
    """
    try:
        df = db_conn.query(query, ttl="0s")
        if df.empty: return []
        df["Date"] = pd.to_datetime(df["Date"])
        df["Amount"] = df["Amount"].astype(float)
        return df.to_dict("records")
    except Exception: return []

def load_db_expenses_summary_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT e.id, e.expense_date, e.expense_type, e.category, e.sub_category, e.description, e.total_amount, e.attributed_to, e.vendor_name, e.staff_name, e.purchase_order_id, e.status, e.remarks, COALESCE(SUM(p.amount_paid), 0) AS total_paid, e.total_amount - COALESCE(SUM(p.amount_paid), 0) AS balance_due, COUNT(p.id) AS payment_count
    FROM expenses e LEFT JOIN expense_payments p ON e.id = p.expense_id
    GROUP BY e.id, e.expense_date, e.expense_type, e.category, e.sub_category, e.description, e.total_amount, e.attributed_to, e.vendor_name, e.staff_name, e.purchase_order_id, e.status, e.remarks ORDER BY e.expense_date DESC, e.id DESC;
    """
    try: return db_conn.query(query, ttl="0s")
    except Exception: return pd.DataFrame()

def load_db_payments_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT p.id, p.expense_id, p.payment_date, p.amount_paid, p.payment_mode, p.ref_no, p.paid_to, p.paid_by, p.notes, e.category, e.sub_category, e.description AS expense_desc, e.total_amount AS expense_total, e.staff_name
    FROM expense_payments p JOIN expenses e ON p.expense_id = e.id ORDER BY p.payment_date DESC, p.id DESC;
    """
    try: return db_conn.query(query, ttl="0s")
    except Exception: return pd.DataFrame()

def load_full_staff_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT s.id, s.name, s.full_name, s.status, s.phone_number, s.emergency_contact_name, s.emergency_contact_phone, s.date_of_birth, s.pan_number, s.aadhaar_number, s.current_address, s.permanent_address, s.date_of_joining, s.date_of_leaving, s.notes, c.monthly_fixed_salary, c.commission_threshold_daily, c.commission_percentage, c.allowance_weekday, c.allowance_sunday
    FROM staff s LEFT JOIN LATERAL (SELECT * FROM staff_compensation_plans WHERE staff_id = s.id ORDER BY effective_from DESC, id DESC LIMIT 1) c ON true ORDER BY s.status ASC, s.name ASC;
    """
    try: return db_conn.query(query, ttl="0s")
    except Exception: return pd.DataFrame()

def load_staff_compensation_history(staff_id):
    if db_conn is None: return pd.DataFrame()
    try: return db_conn.query("SELECT id, staff_id, effective_from, effective_to, monthly_fixed_salary, commission_threshold_daily, commission_percentage, allowance_weekday, allowance_sunday, created_at FROM staff_compensation_plans WHERE staff_id = :sid ORDER BY effective_from DESC, id DESC;", params={"sid": staff_id}, ttl="0s")
    except Exception: return pd.DataFrame()

def load_staff_attendance_df(start_date=None, end_date=None):
    if db_conn is None: return pd.DataFrame()
    where_clauses, params = [], {}
    if start_date: where_clauses.append("a.attendance_date >= :sdate"); params["sdate"] = start_date
    if end_date: where_clauses.append("a.attendance_date <= :edate"); params["edate"] = end_date
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    try: return db_conn.query(f"SELECT a.id, a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type, a.reason, a.recorded_by, a.created_at FROM staff_attendance a JOIN staff s ON a.staff_id = s.id {where_sql} ORDER BY a.attendance_date DESC, a.id DESC;", params=params, ttl="0s")
    except Exception: return pd.DataFrame()

def calculate_incurred_labour_for_range(start_date, end_date):
    if db_conn is None: return 0.0, 0.0, 0.0, {}
    staff_df = load_full_staff_df()
    if staff_df.empty: return 0.0, 0.0, 0.0, {}
    
    entries_df = db_conn.query("SELECT entry_date, cart_name, staff_name, total_collection FROM daily_cart_entries WHERE entry_date >= :sdate AND entry_date <= :edate AND staff_name IS NOT NULL AND staff_name != '' AND staff_name != 'Select Staff';", params={"sdate": start_date, "edate": end_date}, ttl="0s")
    att_df = db_conn.query("SELECT a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type FROM staff_attendance a JOIN staff s ON a.staff_id = s.id WHERE a.attendance_date >= :sdate AND a.attendance_date <= :edate;", params={"sdate": start_date, "edate": end_date}, ttl="0s")
    pay_df = db_conn.query("SELECT p.amount_paid, e.staff_name FROM expense_payments p JOIN expenses e ON p.expense_id = e.id WHERE e.category = 'Labour Charges' AND p.payment_date >= :sdate AND p.payment_date <= :edate;", params={"sdate": start_date, "edate": end_date}, ttl="0s")
    
    exp_ledger_df = db_conn.query("""
        SELECT expense_date, staff_name, sub_category, total_amount 
        FROM expenses 
        WHERE category = 'Labour Charges' 
          AND status = 'Paid'
          AND expense_date >= :sdate 
          AND expense_date <= :edate;
    """, params={"sdate": start_date, "edate": end_date}, ttl="0s")
    
    total_labour_incurred, total_labour_paid, breakdown_by_staff = 0.0, 0.0, {}
    
    for _, s_row in staff_df.iterrows():
        st_name = str(s_row["name"]).strip()
        doj = s_row.get("date_of_joining")
        monthly_sal = float(_num(s_row.get("monthly_fixed_salary")) or 18000.0)
        daily_rate = monthly_sal / 30.0
        comm_thresh = float(_num(s_row.get("commission_threshold_daily")) or 3000.0)
        comm_pct = float(_num(s_row.get("commission_percentage")) or 15.0)
        allow_wd = float(_num(s_row.get("allowance_weekday")) or 210.0)
        allow_sun = float(_num(s_row.get("allowance_sunday")) or 250.0)
        
        st_shifts = entries_df[entries_df["staff_name"] == st_name] if not entries_df.empty else pd.DataFrame()
        st_leaves = att_df[att_df["staff_name"] == st_name] if not att_df.empty else pd.DataFrame()
        st_pay = pay_df[pay_df["staff_name"] == st_name] if not pay_df.empty else pd.DataFrame()
        st_exp = exp_ledger_df[exp_ledger_df["staff_name"] == st_name] if not exp_ledger_df.empty else pd.DataFrame()
        
        shift_sal, shift_comm, shift_allow, days_worked, detailed_ledger = 0.0, 0.0, 0.0, 0, []
        
        leave_map = {}
        if not st_leaves.empty:
            for _, l_row in st_leaves.iterrows():
                l_dt = pd.to_datetime(l_row["attendance_date"]).date()
                leave_map[l_dt] = str(l_row.get("leave_type", "Unpaid"))

        shift_map = {}
        if not st_shifts.empty:
            for _, sh in st_shifts.iterrows():
                s_dt = pd.to_datetime(sh["entry_date"]).date()
                if s_dt not in shift_map:
                    shift_map[s_dt] = []
                shift_map[s_dt].append({
                    "cart": sh["cart_name"],
                    "collection": float(_num(sh["total_collection"]))
                })
                
        exp_map = {}
        if not st_exp.empty:
            for _, e_row in st_exp.iterrows():
                e_dt = pd.to_datetime(e_row["expense_date"]).date()
                if e_dt not in exp_map:
                    exp_map[e_dt] = {"advance": 0.0, "food": 0.0}
                
                subcat = str(e_row.get("sub_category") or "").strip().lower()
                amt = float(_num(e_row["total_amount"]))
                
                if 'food' in subcat or 'tea' in subcat or 'allow' in subcat:
                    exp_map[e_dt]["food"] += amt
                elif 'advance' in subcat:
                    exp_map[e_dt]["advance"] += amt

        all_dates = set(leave_map.keys()).union(set(shift_map.keys())).union(set(exp_map.keys()))
        paid_leaves_cnt = 0

        for d in sorted(all_dates):
            is_leave = d in leave_map
            leave_type = leave_map.get(d)
            day_allow_rate = allow_sun if (d.weekday() == 6) else allow_wd
            
            day_adv = exp_map.get(d, {}).get("advance", 0.0)
            day_food = exp_map.get(d, {}).get("food", 0.0)
            exp_attached = False
            
            if is_leave:
                if leave_type == "Paid":
                    paid_leaves_cnt += 1
                    shift_sal += daily_rate
                    shift_allow += day_allow_rate
                    detailed_ledger.append({
                        "date": d, "type": "Paid Leave", "cart": "—", 
                        "collection": 0.0, "fixed_salary": daily_rate, 
                        "commission": 0.0, "allowance": day_allow_rate,
                        "advance_taken": day_adv, "food_taken": day_food
                    })
                    exp_attached = True
                else:
                    detailed_ledger.append({
                        "date": d, "type": "Unpaid Leave", "cart": "—", 
                        "collection": 0.0, "fixed_salary": 0.0, 
                        "commission": 0.0, "allowance": 0.0,
                        "advance_taken": day_adv, "food_taken": day_food
                    })
                    exp_attached = True
                
                if d in shift_map:
                    for cart_shift in shift_map[d]:
                        s_col = cart_shift["collection"]
                        day_comm = max(0.0, s_col - comm_thresh) * (comm_pct / 100.0)
                        shift_comm += day_comm
                        detailed_ledger.append({
                            "date": d, "type": "Sales on Leave Day", "cart": cart_shift["cart"], 
                            "collection": s_col, "fixed_salary": 0.0, 
                            "commission": day_comm, "allowance": 0.0,
                            "advance_taken": 0.0 if exp_attached else day_adv, 
                            "food_taken": 0.0 if exp_attached else day_food
                        })
                        exp_attached = True

            elif d in shift_map:
                days_worked += 1
                shift_sal += daily_rate
                shift_allow += day_allow_rate
                
                for idx, cart_shift in enumerate(shift_map[d]):
                    s_col = cart_shift["collection"]
                    day_comm = max(0.0, s_col - comm_thresh) * (comm_pct / 100.0)
                    shift_comm += day_comm
                    
                    if idx == 0:
                        detailed_ledger.append({
                            "date": d, "type": "Worked Day", "cart": cart_shift["cart"], 
                            "collection": s_col, "fixed_salary": daily_rate, 
                            "commission": day_comm, "allowance": day_allow_rate,
                            "advance_taken": day_adv if not exp_attached else 0.0,
                            "food_taken": day_food if not exp_attached else 0.0
                        })
                        exp_attached = True
                    else:
                        detailed_ledger.append({
                            "date": d, "type": "Extra Cart Shift", "cart": cart_shift["cart"], 
                            "collection": s_col, "fixed_salary": 0.0, 
                            "commission": day_comm, "allowance": 0.0,
                            "advance_taken": 0.0, "food_taken": 0.0
                        })
            else:
                detailed_ledger.append({
                    "date": d, "type": "Expense Recorded", "cart": "—", 
                    "collection": 0.0, "fixed_salary": 0.0, 
                    "commission": 0.0, "allowance": 0.0,
                    "advance_taken": day_adv, "food_taken": day_food
                })
        
        detailed_ledger.sort(key=lambda x: x["date"])
        
        staff_incurred = shift_sal + shift_comm + shift_allow
        staff_paid = float(st_pay["amount_paid"].sum()) if not st_pay.empty else 0.0
        staff_due = staff_incurred - staff_paid
        total_labour_incurred += staff_incurred
        total_labour_paid += staff_paid
        
        breakdown_by_staff[st_name] = {
            "monthly_fixed_salary": monthly_sal, "daily_rate": daily_rate, "days_worked": days_worked, "paid_leaves": paid_leaves_cnt, 
            "salary": shift_sal, "commissions": shift_comm, "allowances": shift_allow, "incurred": staff_incurred, 
            "paid": staff_paid, "due": staff_due, "detailed_ledger": detailed_ledger, "doj": doj
        }
        
    return total_labour_incurred, total_labour_paid, total_labour_incurred - total_labour_paid, breakdown_by_staff

def generate_payslip_pdf(staff_name, start_date, end_date, data_dict):
    if not REPORTLAB_AVAILABLE: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story, styles = [], getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#8A5E17'), alignment=1)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#2A1B10'), alignment=1)
    
    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        try:
            img = RLImage(logo_path, width=50, height=50)
            header_table = Table([[img, Paragraph("<b>Kulfi Factory - Hosur Franchise</b><br/>Staff Salary Payslip", title_style)]], colWidths=[60, 470])
        except Exception:
            header_table = Table([[Paragraph("<b>Kulfi Factory</b>", title_style), Paragraph("<b>Kulfi Factory - Hosur Franchise</b><br/>Staff Salary Payslip", title_style)]], colWidths=[80, 450])
    else: header_table = Table([[Paragraph("<b>Kulfi Factory</b>", title_style), Paragraph("<b>Kulfi Factory - Hosur Franchise</b><br/>Staff Salary Payslip", title_style)]], colWidths=[80, 450])
    
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'CENTER')]))
    header_table.hAlign = 'LEFT'
    story.append(header_table); story.append(Spacer(1, 10))
    
    doj_val = data_dict.get('doj')
    doj_str = pd.to_datetime(doj_val).strftime('%d %b %Y') if pd.notna(doj_val) and str(doj_val).strip() else "N/A"
    month_str = start_date.strftime('%B %Y')
    
    story.append(Paragraph(f"<b>Staff Member:</b> {staff_name} &nbsp;|&nbsp; <b>Date of Joining:</b> {doj_str} &nbsp;|&nbsp; <b>Payslip for the month:</b> {month_str}", sub_style))
    story.append(Spacer(1, 12))
    
    summary_data = [
        ["Salary Component", "Basis / Calculation Details", "Amount (Rs.)"],
        ["Monthly Fixed Salary", "Standard Monthly Base Plan", f"Rs. {data_dict['monthly_fixed_salary']:,.2f}"],
        ["Total Days Worked", f"{data_dict['days_worked']} days worked + {data_dict['paid_leaves']} paid leaves", f"{data_dict['days_worked'] + data_dict['paid_leaves']} days"],
        ["Pro-rata Fixed Salary", f"({data_dict['days_worked']} + {data_dict['paid_leaves']}) days @ Rs. {data_dict.get('daily_rate', 600):.0f}/day", f"Rs. {data_dict['salary']:,.2f}"],
        ["Sales Commissions", "15% on daily collections exceeding threshold", f"Rs. {data_dict['commissions']:,.2f}"],
        ["Food & Tea Allowances", "Entitled weekday & Sunday daily allowances", f"Rs. {data_dict['allowances']:,.2f}"],
        ["Gross Payable Earnings", "Total entitled earnings for the period", f"Rs. {data_dict['incurred']:,.2f}"],
        ["Already Paid / Disbursed", "Cash advances & direct payments recorded", f"-Rs. {data_dict['paid']:,.2f}"],
        ["Net Balance Payable Now", "Final cash settlement due", f"Rs. {data_dict['due']:,.2f}"]
    ]
    
    t_summary = Table(summary_data, colWidths=[150, 250, 100])
    t_summary.hAlign = 'LEFT'
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#70440E')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 9.5),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FFF2DC')), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E3CBA0')), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,1), (-1,-2), 'Helvetica'), ('FONTSIZE', (0,1), (-1,-1), 9), ('TOPPADDING', (0,1), (-1,-1), 4), ('BOTTOMPADDING', (0,1), (-1,-1), 4)
    ]))
    story.append(t_summary); story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Detailed Commission & Allowance Entitlement Ledger</b>", ParagraphStyle('SubHeader', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#8A5E17'), alignment=0)))
    story.append(Spacer(1, 4))
    
    line_t = Table([['']], colWidths=[525])
    line_t.setStyle(TableStyle([('LINEABOVE', (0,0), (-1,-1), 0.75, colors.HexColor('#8A5E17'))]))
    line_t.hAlign = 'LEFT'
    story.append(line_t)
    story.append(Spacer(1, 6))
    
    ledger_rows = [["Date", "Type", "Cart", "Sales", "Salary", "Comm.", "Allow.", "Adv. Taken", "Allow. Taken"]]
    for item in data_dict.get("detailed_ledger", []):
        ledger_rows.append([
            item["date"].strftime("%d %b %Y"), item["type"], item["cart"],
            f"{item['collection']:,.0f}" if item['collection'] > 0 else "—",
            f"{item['fixed_salary']:,.0f}",
            f"{item['commission']:,.0f}" if item['commission'] > 0 else "—",
            f"{item['allowance']:,.0f}" if item['allowance'] > 0 else "—",
            f"{item['advance_taken']:,.0f}" if item.get('advance_taken', 0) > 0 else "—",
            f"{item['food_taken']:,.0f}" if item.get('food_taken', 0) > 0 else "—"
        ])
    if len(ledger_rows) == 1: ledger_rows.append(["No records", "—", "—", "—", "—", "—", "—", "—", "—"])
    
    t_ledger = Table(ledger_rows, colWidths=[55, 65, 100, 45, 45, 45, 45, 60, 60])
    t_ledger.hAlign = 'LEFT'
    t_ledger.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#124A1D')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#A8D5AF')), ('ALIGN', (3,0), (-1,-1), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)
    ]))
    
    story.append(t_ledger); story.append(Spacer(1, 15))
    story.append(Paragraph("<i>This is a computer-generated payslip for Kulfi Factory - Hosur Franchise.</i>", ParagraphStyle('Footer', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.gray, alignment=1)))
    doc.build(story); buffer.seek(0); return buffer.getvalue()

# ----------------------------------------------------------------------
# AUTHENTICATION
# ----------------------------------------------------------------------
def check_login():
    if st.session_state.get("authenticated", False): return True
    _, col_form, _ = st.columns([1, 1.2, 1])
    with col_form:
        try: st.image("assets/logo.png", width=220)
        except Exception: st.title("🍦 Kulfi Ops")
        st.subheader("Sign in")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
        if submitted:
            user_clean = str(username).strip().lower()
            pass_clean = str(password).strip()
            admin_user = str(st.secrets.get("app_username", "admin")).strip().lower()
            admin_pass = str(st.secrets.get("app_password", "")).strip()
            entry_user = str(st.secrets.get("entry_username", "entry")).strip().lower()
            entry_pass = str(st.secrets.get("entry_password", "")).strip()
            if admin_pass and hmac.compare_digest(user_clean, admin_user) and hmac.compare_digest(pass_clean, admin_pass):
                st.session_state["authenticated"] = True; st.session_state["user_role"] = "admin"; st.rerun()
            elif entry_pass and hmac.compare_digest(user_clean, entry_user) and hmac.compare_digest(pass_clean, entry_pass):
                st.session_state["authenticated"] = True; st.session_state["user_role"] = "entry"; st.rerun()
            else: st.error("Incorrect username or password — try again.")
    return False

if not check_login(): st.stop()

# ----------------------------------------------------------------------
# NAVIGATION & ROLE CONFIG
# ----------------------------------------------------------------------
user_role = st.session_state.get("user_role", "admin")

if user_role == "entry":
    page = "Daily Entry"
    top_nav_c1, top_nav_c2 = st.columns([6, 1])
    with top_nav_c1: st.title("🍦 Kulfi Ops — Daily Entry")
    with top_nav_c2:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🚪 Log out", type="secondary", use_container_width=True):
            st.session_state["authenticated"] = False; st.session_state["user_role"] = None; st.rerun()
else:
    with st.sidebar:
        try: st.image("assets/logo.png", use_container_width=True)
        except Exception: st.markdown("## 🍦 Kulfi Ops")
        nav_options = ["Dashboard", "Daily Entry", "Live Cart Tracking", "Purchase Orders", "Freezer Stock", "Freezer Analysis", "Stock Removed", "Expenses", "Staff & Payroll", "Payslip Generator"]
        page = st.radio("Go to", nav_options, label_visibility="collapsed")
        st.markdown("---")
        if st.button("Log out", use_container_width=True):
            st.session_state["authenticated"] = False; st.session_state["user_role"] = None; st.rerun()
    st.title(f"🍦 Kulfi Ops — {page}")

# ======================================================================
# PAGE ROUTING
# ======================================================================

if page == "Daily Entry":
    if "active_daily_cart" not in st.session_state:
        st.session_state["active_daily_cart"] = None

    if not st.session_state["active_daily_cart"]:
        st.subheader("Select Cart for Daily Entry")
        st.caption("Click on a cart below to record sales or restock inventory:")
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        c_btn1, c_btn2, c_btn3 = st.columns(3, gap="medium")
        for i, cart_name in enumerate(CARTS):
            with [c_btn1, c_btn2, c_btn3][i]:
                if st.button(f"🛒 {cart_name}", use_container_width=True, type="primary"):
                    st.session_state["active_daily_cart"] = cart_name; st.rerun()
    else:
        cart_name = st.session_state["active_daily_cart"]
        
        if st.button("⬅ Back to Cart Selection", type="primary", use_container_width=False):
            st.session_state["active_daily_cart"] = None; st.rerun()

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        st.subheader(f"Cart Restock & Daily Sales — {cart_name}")

        try:
            all_entries = list_daily_entries_with_prefill()
            cart_entries = [e for e in all_entries if e["cart"] == cart_name]
        except Exception as e:
            cart_entries = []; st.warning(f"Could not load entries from database ({e}).")

        if user_role == "entry" and cart_entries:
            allowed_dates = {date.today() - timedelta(days=d) for d in range(1, 4)}
            cart_entries = [e for e in cart_entries if e["date"].date() in allowed_dates]

        if not cart_entries: st.info(f"No entries found for {cart_name}.")
        else:
            top_c1, top_c2 = st.columns([1.3, 1])
            labels = [f"{e['date'].strftime('%d %b %Y')}" for e in cart_entries]
            with top_c1: sel_date_label = st.selectbox("Select entry date to update sales", labels, key=f"date_sel_{cart_name}")
            loaded = cart_entries[labels.index(sel_date_label)]
            entry_id, entry_date, today_val = loaded["db_id"], loaded["date"].date(), date.today()
            data_key_suffix = f"_{entry_id}"

            staff_options = load_active_staff_list()
            default_staff_name = loaded.get("staff_name", "")
            if default_staff_name and default_staff_name not in staff_options: staff_options.append(default_staff_name)
            with top_c2: staff_name = st.selectbox("Cart staff assigned", staff_options, index=staff_options.index(default_staff_name) if default_staff_name in staff_options else 0, key=f"daily_staff{data_key_suffix}")

            existing_today_added = {}
            if db_conn is not None:
                try:
                    t_res = db_conn.query("SELECT i.flavor_code, i.added_units FROM daily_cart_entries e JOIN daily_cart_items i ON e.id = i.daily_entry_id WHERE e.entry_date = :tdt AND e.cart_name = :cart;", params={"tdt": today_val, "cart": cart_name}, ttl="0s")
                    if not t_res.empty: existing_today_added = dict(zip(t_res["flavor_code"], t_res["added_units"]))
                except Exception: pass

            col_box_left, col_box_right = st.columns(2, gap="medium")
            added_map, closing_map, sold_map = {}, {}, {}
            opening_map = {code: loaded["by_code"][code]["opening"] for code in FLAVOR_CODES}

            with col_box_left:
                st.markdown(f"<div class='header-box-sales'><span>📅 1. Sales & Closing Entry — {entry_date.strftime('%a, %d %b %Y')}</span><span><b>{cart_name}</b></span></div>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.caption(f"Record **closing counts** and daytime stock additions for **{entry_date.strftime('%d %b %Y')}**:")
                    for code in FLAVOR_CODES:
                        f_info = FLAVOR_MAP[code]
                        k_add, k_cls = f"add_{entry_id}_{code}", f"cls_{entry_id}_{code}"
                        if k_add not in st.session_state: st.session_state[k_add] = loaded["by_code"][code]["added"]
                        if k_cls not in st.session_state: st.session_state[k_cls] = loaded["by_code"][code]["closing"]
                        cur_open = opening_map[code]
                        cur_add, cur_cls = _int_num(st.session_state[k_add]), _int_num(st.session_state[k_cls])
                        cur_sold = cur_open + cur_add - cur_cls
                        added_map[code], closing_map[code], sold_map[code] = cur_add, cur_cls, cur_sold

                        st.markdown(f"<div class='flavor-entry-row'><div class='flavor-title-bar'><span class='flavor-name'>{f_info['name']} (₹{f_info['mrp']:.0f})</span><div><span class='badge-open'>Opening: {cur_open}</span> <span class='badge-sold'>Sold: {cur_sold}</span></div></div></div>", unsafe_allow_html=True)
                        col_a, col_b = st.columns(2)
                        with col_a: st.number_input("+ Added during day", min_value=0, step=1, format="%d", key=k_add)
                        with col_b: st.number_input("Closing count", min_value=0, step=1, format="%d", key=k_cls)

                    tot_open, tot_add, tot_close, tot_sold = sum(opening_map.values()), sum(added_map.values()), sum(closing_map.values()), sum(sold_map.values())
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Opening", f"{tot_open} pcs"); m2.metric("Added", f"{tot_add} pcs"); m3.metric("Closing", f"{tot_close} pcs"); m4.metric("Total Sold", f"{tot_sold} pcs")

                    if any(s < 0 for s in sold_map.values()): st.error(f"Sales negative for at least one flavour on {entry_date.strftime('%d %b %Y')} - check closing count.")

                    calculated_mrp_total = float(sum(sold_map[code] * FLAVOR_MAP[code]["mrp"] for code in FLAVOR_CODES))
                    k_tot, k_prev_calc = f"daily_total{data_key_suffix}", f"daily_prev_calc{data_key_suffix}"
                    if k_tot not in st.session_state or st.session_state.get(k_prev_calc) != calculated_mrp_total:
                        st.session_state[k_tot] = f"{loaded['total']:.2f}" if (loaded["total"] > 0 and not loaded.get("is_prefill")) else f"{calculated_mrp_total:.2f}"
                        st.session_state[k_prev_calc] = calculated_mrp_total
                    if f"daily_phonepe{data_key_suffix}" not in st.session_state: st.session_state[f"daily_phonepe{data_key_suffix}"] = f"{loaded['phonepe']:.2f}"
                    if f"daily_adv{data_key_suffix}" not in st.session_state: st.session_state[f"daily_adv{data_key_suffix}"] = f"{loaded['staff_advance']:.2f}" if "staff_advance" in loaded else "0.00"
                    if f"daily_food{data_key_suffix}" not in st.session_state: st.session_state[f"daily_food{data_key_suffix}"] = f"{loaded['food_tea_cash']:.2f}" if "food_tea_cash" in loaded else "0.00"
                    if f"daily_cash{data_key_suffix}" not in st.session_state: st.session_state[f"daily_cash{data_key_suffix}"] = f"{loaded['cash']:.2f}"

                    st.markdown("---")
                    st.write(f"**Cash, UPI & Advance Collection ({entry_date.strftime('%d %b')})**")
                    c3, c4 = st.columns(2)
                    with c3:
                        total_collection_val = _num(st.text_input("Total collection (₹)", key=k_tot))
                        staff_advance_val = _num(st.text_input("Advance to staff (₹)", key=f"daily_adv{data_key_suffix}"))
                        food_tea_val = _num(st.text_input("Cash Food / Tea (₹)", key=f"daily_food{data_key_suffix}"))
                    with c4:
                        phonepe_val = _num(st.text_input("PhonePe / UPI (₹)", key=f"daily_phonepe{data_key_suffix}"))
                        cash_val = _num(st.text_input("Cash Collected (₹)", key=f"daily_cash{data_key_suffix}"))

                    cash_leakage = total_collection_val - phonepe_val - staff_advance_val - food_tea_val - cash_val
                    has_leakage = cash_leakage > 0.001
                    if has_leakage: st.markdown(f"<div style='margin-top:2px;'><label style='font-size:11px; font-weight:700;'>Cash Leakage:</label> <b style='color:#C41C1C; font-size:14px;'>₹{cash_leakage:,.2f}</b></div><p style='color:#C41C1C; font-weight:bold; font-size:11.5px; margin: 2px 0 !important;'>⚠️ Cash leakage detected - enter reason in remarks</p>", unsafe_allow_html=True)
                    else: st.markdown(f"<div style='margin-top:2px;'><label style='font-size:11px; font-weight:700;'>Cash Leakage:</label> <b style='color:#2A1B10; font-size:13px;'>₹{cash_leakage:,.2f}</b></div>", unsafe_allow_html=True)
                    remarks = st.text_input("Remarks", value=loaded["remarks"], key=f"daily_remarks{data_key_suffix}", placeholder="Enter remarks (mandatory if cash leakage)...")

            today_added_map, today_opening_map, today_db_opening_map = {}, {}, {}
            with col_box_right:
                st.markdown(f"<div class='header-box-restock'><span>🚀 2. Today's Restock & Opening — {today_val.strftime('%a, %d %b %Y')}</span><span><b>{cart_name}</b></span></div>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.caption(f"Enter **stock added for today ({today_val.strftime('%d %b')})**.")
                    for code in FLAVOR_CODES:
                        f_info = FLAVOR_MAP[code]
                        k_today_add = f"today_add_{cart_name}_{code}"
                        prev_close_count = closing_map.get(code, 0)
                        default_added_val = int(existing_today_added.get(code, 0))

                        with st.container(border=True):
                            st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;'><span style='font-weight: 800; font-size: 12.5px; color: #124A1D;'>{f_info['name']} (₹{f_info['mrp']:.0f})</span><span class='badge-open'>Opening: {prev_close_count} pcs</span></div>", unsafe_allow_html=True)
                            c_flv_l, c_flv_r = st.columns([1.1, 0.9])
                            with c_flv_l: today_add_input = st.number_input("+ Restock", min_value=0, value=default_added_val, step=1, format="%d", key=k_today_add)
                            
                            today_added_map[code] = int(today_add_input)
                            today_db_opening_map[code] = prev_close_count
                            calc_today_open_display = prev_close_count + int(today_add_input)
                            today_opening_map[code] = calc_today_open_display

                            with c_flv_r:
                                st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)
                                st.markdown(f"<div style='text-align: right; margin-bottom: 2px;'><span class='badge-today-open'>Opening + Restock: <b>{calc_today_open_display} pcs</b></span></div>", unsafe_allow_html=True)

                    tot_today_added, tot_today_open_display = sum(today_added_map.values()), sum(today_opening_map.values())
                    st.markdown("---")
                    tm1, tm2 = st.columns(2)
                    tm1.metric("Stock Added for Today", f"{tot_today_added} pcs")
                    tm2.metric("Today's Total Opening (Display)", f"{tot_today_open_display} pcs")

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            if st.button("💾 Submit Daily Sales & Today's Restock Entry", type="primary", use_container_width=True):
                if any(s < 0 for s in sold_map.values()): st.error("Sales works out negative for at least one flavour on previous day - fix closing count before saving.")
                elif has_leakage and not remarks.strip(): st.error("Remarks is mandatory when there is a cash leakage. Please enter a reason.")
                else:
                    try:
                        selected_staff = "" if staff_name == "Select Staff" else staff_name
                        sync_daily_entry(entry_date, cart_name, added_map, closing_map, opening_map, sold_map, total_collection_val, phonepe_val, cash_val, remarks, selected_staff, staff_advance_val, food_tea_val)
                        sync_today_restock_entry(today_val, cart_name, selected_staff, today_db_opening_map, today_added_map)
                        st.cache_resource.clear()
                        st.session_state["active_daily_cart"] = None
                        success_msg = f"Record Saved successfully:\n\n{entry_date.strftime('%d %b %Y')} : Total sold units {tot_sold} units\n\n{today_val.strftime('%d %b %Y')} : Opening balance after restock {tot_today_open_display} units"
                        show_success_modal(success_msg)
                    except Exception as e:
                        st.error(f"Could not save entries - {e}")

elif page == "Payslip Generator" and user_role == "admin":
    p_h_col1, p_h_col2 = st.columns([1, 6])
    with p_h_col1:
        if os.path.exists("assets/logo.png"): st.image("assets/logo.png", width=90)
    with p_h_col2:
        st.subheader("Staff Payslip Generator & Detailed Ledger")
        st.caption("Kulfi Factory - Hosur Franchise")

    staff_df = load_full_staff_df()
    if staff_df.empty: st.info("No staff records found in the database.")
    else:
        pc1, pc2, pc3 = st.columns([1.2, 1, 1])
        with pc1: sel_staff_payslip = st.selectbox("Select Staff Member", staff_df["name"].tolist(), key="payslip_staff_sel")
        with pc2: payslip_start = st.date_input("Start Date", value=date.today().replace(day=1), key="payslip_start_dt")
        with pc3: payslip_end = st.date_input("End Date", value=date.today(), key="payslip_end_dt")

        if payslip_start > payslip_end: st.error("Start date must be before or equal to end date.")
        else:
            _, _, _, breakdown_dict = calculate_incurred_labour_for_range(payslip_start, payslip_end)
            staff_data = breakdown_dict.get(sel_staff_payslip, {
                "monthly_fixed_salary": 18000.0, "days_worked": 0, "paid_leaves": 0, "salary": 0.0,
                "commissions": 0.0, "allowances": 0.0, "incurred": 0.0, "paid": 0.0, "due": 0.0, "detailed_ledger": [], "doj": None
            })

            doj_val = staff_data.get('doj')
            doj_str = pd.to_datetime(doj_val).strftime('%d %b %Y') if pd.notna(doj_val) and str(doj_val).strip() else "N/A"
            month_str = payslip_start.strftime('%B %Y')

            st.markdown("---")
            st.markdown(f"#### Salary Statement Summary — {sel_staff_payslip}")
            st.markdown(f"**Date of Joining:** {doj_str} &nbsp;|&nbsp; **Payslip for the month:** {month_str}")
            
            summary_table_data = [
                ["Salary Component", "Basis / Calculation Details", "Amount (₹)"],
                ["Monthly Fixed Salary", "Standard Monthly Base Plan", f"₹{staff_data['monthly_fixed_salary']:,.2f}"],
                ["Total Days Worked", f"{staff_data['days_worked']} days worked + {staff_data['paid_leaves']} paid leaves", f"{staff_data['days_worked'] + staff_data['paid_leaves']} days"],
                ["Pro-rata Fixed Salary", f"({staff_data['days_worked']} + {staff_data['paid_leaves']}) days @ ₹{staff_data.get('daily_rate', 600):.0f}/day", f"₹{staff_data['salary']:,.2f}"],
                ["Sales Commissions", "15% on daily collections exceeding threshold", f"₹{staff_data['commissions']:,.2f}"],
                ["Food & Tea Allowances", "Entitled weekday & Sunday daily allowances", f"₹{staff_data['allowances']:,.2f}"],
                ["Gross Payable Earnings", "Total entitled earnings for the period", f"₹{staff_data['incurred']:,.2f}"],
                ["Already Paid / Disbursed", "Cash advances & direct payments recorded", f"-₹{staff_data['paid']:,.2f}"],
                ["Net Balance Payable Now", "Final cash settlement due", f"₹{staff_data['due']:,.2f}"]
            ]
            
            summary_df = pd.DataFrame(summary_table_data[1:], columns=summary_table_data[0])
            
            def style_bold_rows(row):
                if row["Salary Component"] in ["Gross Payable Earnings", "Net Balance Payable Now"]:
                    return ["font-weight: bold;"] * len(row)
                return [""] * len(row)
                
            st.dataframe(summary_df.style.apply(style_bold_rows, axis=1), hide_index=True, use_container_width=True)

            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
            st.markdown(f"#### Detailed Commission & Allowance Entitlement Ledger")
            st.caption(f"Payslip for the month: {month_str} (Itemized daily breakdown)")

            ledger_list = staff_data.get("detailed_ledger", [])
            if ledger_list:
                ledger_df = pd.DataFrame(ledger_list)
                ledger_df["Date"] = pd.to_datetime(ledger_df["date"]).dt.strftime("%d %b %Y")
                ledger_df["Type"] = ledger_df["type"]
                ledger_df["Cart"] = ledger_df["cart"]
                ledger_df["Collection (₹)"] = ledger_df["collection"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                ledger_df["Salary (₹)"] = ledger_df["fixed_salary"].apply(lambda v: f"₹{v:,.2f}")
                ledger_df["Commission (₹)"] = ledger_df["commission"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                ledger_df["Allowance (₹)"] = ledger_df["allowance"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                ledger_df["Advance Taken (₹)"] = ledger_df["advance_taken"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                ledger_df["Allow. Taken (₹)"] = ledger_df["food_taken"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                
                st.dataframe(
                    ledger_df[["Date", "Type", "Cart", "Collection (₹)", "Salary (₹)", "Commission (₹)", "Allowance (₹)", "Advance Taken (₹)", "Allow. Taken (₹)"]], 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Cart": st.column_config.TextColumn(width="medium")
                    }
                )
            else:
                st.info("No active days or leave records found within the selected date range.")

            st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

            if REPORTLAB_AVAILABLE:
                pdf_bytes = generate_payslip_pdf(sel_staff_payslip, payslip_start, payslip_end, staff_data)
                if pdf_bytes:
                    st.download_button(
                        label="📥 Download Official Payslip as PDF",
                        data=pdf_bytes,
                        file_name=f"Payslip_{sel_staff_payslip.replace(' ', '_')}_{month_str.replace(' ', '_')}.pdf",
                        mime="application/pdf", type="primary", use_container_width=True
                    )
            else:
                st.warning("`reportlab` library is not installed in the Python environment for binary PDF downloads.")

# ======================================================================
# PAGE: LIVE CART TRACKING (Admin View)
# ======================================================================
elif page == "Live Cart Tracking" and user_role == "admin":
    st.subheader("Live Cart Operations Tracker")
    st.caption("Monitor real-time sales pouring in from the mobile cart apps.")

    if st.button("🔄 Manual Refresh Live Data"):
        st.rerun()
    
    st.markdown("---")

    active_shifts_df = db_conn.query("""
        SELECT s.id, s.cart_name, s.staff_name, s.started_at, s.status,
               COALESCE(SUM(t.total_amount), 0) AS gross_sales,
               COALESCE(SUM(t.cash_amount), 0) AS total_cash,
               COALESCE(SUM(t.phonepe_amount), 0) AS total_phonepe,
               COUNT(t.id) AS transaction_count
        FROM live_cart_shifts s
        LEFT JOIN live_cart_transactions t ON s.id = t.shift_id
        WHERE s.shift_date = CURRENT_DATE
        GROUP BY s.id ORDER BY s.started_at DESC;
    """, ttl="0s")

    if active_shifts_df.empty:
        st.info("No active shifts or live carts operating today yet.")
    else:
        for _, shift in active_shifts_df.iterrows():
            with st.container(border=True):
                status_color = "🟢" if shift["status"] == "Active" else "🔴"
                st.markdown(f"#### {status_color} {shift['cart_name']} &nbsp;|&nbsp; Staff: {shift['staff_name']} &nbsp;|&nbsp; Status: {shift['status']}")
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Gross Live Sales", f"₹{float(shift['gross_sales']):,.2f}")
                c2.metric("Total PhonePe", f"₹{float(shift['total_phonepe']):,.2f}")
                c3.metric("Total Cash", f"₹{float(shift['total_cash']):,.2f}")
                c4.metric("Transactions Today", int(shift["transaction_count"]))

                items_df = db_conn.query("""
                    SELECT f.name AS flavor_name, SUM(i.quantity) as qty_sold, SUM(i.subtotal) as rev
                    FROM live_transaction_items i
                    JOIN live_cart_transactions t ON i.transaction_id = t.id
                    JOIN flavors f ON i.flavor_code = f.code
                    WHERE t.shift_id = :sid
                    GROUP BY f.name ORDER BY qty_sold DESC;
                """, params={"sid": int(shift["id"])}, ttl="0s")

                if not items_df.empty:
                    with st.expander("View Flavour Breakdown"):
                        st.dataframe(items_df.rename(columns={"flavor_name": "Flavour", "qty_sold": "Units Sold", "rev": "Revenue (₹)"}), hide_index=True, use_container_width=True)

elif page == "Purchase Orders" and user_role == "admin":
    st.subheader("Purchase Order Estimator & Order Management")
    st.caption("Plan order quantities, apply overall discounts, calculate net payable cost, and manage orders.")

    po_mode = st.radio("Mode", ["Create New Order", "Edit / Track Existing Orders"], horizontal=True, key="po_screen_mode")

    if po_mode == "Create New Order":
        st.write("Enter details and specify quantities per flavor to calculate the estimated purchase cost.")

        c1, c2, c3 = st.columns(3)
        with c1: order_date = st.date_input("Order Date", value=date.today(), key="new_po_order_date")
        with c2: expected_date = st.date_input("Expected Delivery Date", value=date.today() + timedelta(days=2), key="new_po_exp_date")
        with c3: location = st.text_input("Delivery Location", value=CITY, key="new_po_loc")

        c4, c5 = st.columns(2)
        with c4: order_status = st.selectbox("Order Status", PO_STATUSES, index=0, key="new_po_status")
        with c5: discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="new_po_discount")

        grid_rows = []
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            grid_rows.append({"Flavour": f_info["name"], "Code": code, "Unit Cost (₹)": float(f_info["cost_price"]), "Order Quantity": 0})

        st.write("Enter order quantities per flavour:")
        po_editor_df = st.data_editor(pd.DataFrame(grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Order Quantity": st.column_config.NumberColumn(min_value=0, step=10, format="%d")}, hide_index=True, use_container_width=True, key="new_po_editor")

        total_units = int(po_editor_df["Order Quantity"].sum())
        gross_cost = float(sum(po_editor_df["Order Quantity"] * po_editor_df["Unit Cost (₹)"]))
        discount_amount = gross_cost * (discount_pct / 100.0)
        final_amount = gross_cost - discount_amount

        st.markdown("#### Dynamic Price & Discount Calculation")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Ordered Units", f"{total_units} units")
        m2.metric("Gross Cost", f"₹{gross_cost:,.2f}")
        m3.metric(f"Discount ({discount_pct:.1f}%)", f"-₹{discount_amount:,.2f}")
        m4.metric("Final Amount to Pay", f"₹{final_amount:,.2f}")

        po_notes = st.text_input("Order Notes / Supplier Remarks (Optional)", key="new_po_notes", placeholder="e.g. Regular weekly replenishment order...")

        if st.button("🚀 Submit Purchase Order", type="primary", use_container_width=True):
            if total_units <= 0: st.error("Please enter a quantity greater than 0 for at least one flavour before placing the order.")
            else:
                try:
                    combined_notes = po_notes.strip()
                    if discount_pct > 0: combined_notes = f"[Discount: {discount_pct:.2f}% | Final: ₹{final_amount:,.2f}] {combined_notes}".strip()
                    with db_conn.session as s:
                        res = s.execute(text("INSERT INTO purchase_orders (order_date, expected_date, location, order_status, notes) VALUES (:od, :ed, :loc, :stat, :notes) RETURNING id;"), {"od": order_date, "ed": expected_date, "loc": location, "stat": order_status, "notes": combined_notes})
                        new_poid = res.scalar()
                        for _, row in po_editor_df.iterrows():
                            qty = int(row["Order Quantity"])
                            if qty > 0: s.execute(text("INSERT INTO purchase_order_items (order_id, flavor_code, ordered_units) VALUES (:poid, :code, :qty);"), {"poid": new_poid, "code": row["Code"], "qty": qty})
                        s.commit()
                    show_success_modal(f"Purchase Order #{new_poid} created successfully! Total: {total_units} units | Final Amount: ₹{final_amount:,.2f} ({discount_pct:.1f}% off).")
                except Exception as e: st.error(f"Could not save purchase order to database: {e}")

    elif po_mode == "Edit / Track Existing Orders":
        po_query_df = db_conn.query("SELECT p.id, p.order_date, p.expected_date, p.location, p.order_status, p.notes, json_agg(json_build_object('code', pi.flavor_code, 'qty', pi.ordered_units)) AS items FROM purchase_orders p LEFT JOIN purchase_order_items pi ON p.id = pi.order_id GROUP BY p.id ORDER BY p.order_date DESC, p.id DESC;", ttl="0s")
        if po_query_df.empty: st.info("No purchase orders found in the database.")
        else:
            po_records = po_query_df.to_dict("records")
            po_labels = [f"PO #{r['id']} — {pd.to_datetime(r['order_date']).strftime('%d %b %Y')} ({r['location']}) — Status: {r['order_status']}" for r in po_records]
            selected_po_label = st.selectbox("Select Purchase Order to edit", po_labels, key="edit_po_select")
            loaded_po = po_records[po_labels.index(selected_po_label)]
            loaded_po_id = loaded_po["id"]
            existing_notes = str(loaded_po.get("notes") or "")
            default_disc, clean_notes = 0.0, existing_notes
            disc_match = re.search(r"\[Discount:\s*([\d.]+)%[^\]]*\]", existing_notes)
            if disc_match:
                try: default_disc = float(re.search(r"([\d.]+)", disc_match.group(0)).group(1)); clean_notes = re.sub(r"\[Discount:[^\]]*\]\s*", "", existing_notes).strip()
                except Exception: default_disc = 0.0

            c1, c2, c3 = st.columns(3)
            with c1: e_order_date = st.date_input("Order Date", value=pd.to_datetime(loaded_po["order_date"]).date() if loaded_po.get("order_date") else date.today(), key=f"edit_po_od_{loaded_po_id}")
            with c2: e_expected_date = st.date_input("Expected Delivery Date", value=pd.to_datetime(loaded_po["expected_date"]).date() if loaded_po.get("expected_date") else date.today() + timedelta(days=2), key=f"edit_po_ed_{loaded_po_id}")
            with c3: e_location = st.text_input("Delivery Location", value=str(loaded_po.get("location", CITY)), key=f"edit_po_loc_{loaded_po_id}")

            c4, c5 = st.columns(2)
            with c4: e_status = st.selectbox("Order Status", PO_STATUSES, index=PO_STATUSES.index(loaded_po.get("order_status", "Placed")) if loaded_po.get("order_status", "Placed") in PO_STATUSES else 0, key=f"edit_po_stat_{loaded_po_id}")
            with c5: e_discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=default_disc, step=0.5, format="%.2f", key=f"edit_po_disc_{loaded_po_id}")

            items_by_code = {itm["code"]: itm.get("qty", 0) for itm in loaded_po.get("items", []) if isinstance(itm, dict) and "code" in itm} if loaded_po.get("items") and isinstance(loaded_po["items"], list) else {}
            edit_grid_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Order Quantity": int(items_by_code.get(code) or 0)} for code in FLAVOR_CODES]

            st.write("Modify order quantities per flavour:")
            po_edit_editor_df = st.data_editor(pd.DataFrame(edit_grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Order Quantity": st.column_config.NumberColumn(min_value=0, step=10, format="%d")}, hide_index=True, use_container_width=True, key=f"edit_po_editor_{loaded_po_id}")

            e_total_units = int(po_edit_editor_df["Order Quantity"].sum())
            e_gross_cost = float(sum(po_edit_editor_df["Order Quantity"] * po_edit_editor_df["Unit Cost (₹)"]))
            e_discount_amount = e_gross_cost * (e_discount_pct / 100.0)
            e_final_amount = e_gross_cost - e_discount_amount

            st.markdown("#### Updated Order Summary")
            em1, em2, em3, em4 = st.columns(4)
            em1.metric("Total Ordered Units", f"{e_total_units} units"); em2.metric("Gross Cost", f"₹{e_gross_cost:,.2f}"); em3.metric(f"Discount ({e_discount_pct:.1f}%)", f"-₹{e_discount_amount:,.2f}"); em4.metric("Final Amount to Pay", f"₹{e_final_amount:,.2f}")
            e_notes = st.text_input("Order Notes", value=clean_notes, key=f"edit_po_notes_{loaded_po_id}")

            if st.button("💾 Update Purchase Order", type="primary", use_container_width=True):
                if e_total_units <= 0: st.error("Please specify at least one quantity for the order.")
                else:
                    try:
                        combined_edit_notes = e_notes.strip()
                        if e_discount_pct > 0: combined_edit_notes = f"[Discount: {e_discount_pct:.2f}% | Final: ₹{e_final_amount:,.2f}] {combined_edit_notes}".strip()
                        with db_conn.session as s:
                            s.execute(text("UPDATE purchase_orders SET order_date = :od, expected_date = :ed, location = :loc, order_status = :stat, notes = :notes WHERE id = :id;"), {"od": e_order_date, "ed": e_expected_date, "loc": e_location, "stat": e_status, "notes": combined_edit_notes, "id": loaded_po_id})
                            s.execute(text("DELETE FROM purchase_order_items WHERE order_id = :id;"), {"id": loaded_po_id})
                            for _, row in po_edit_editor_df.iterrows():
                                qty = int(row["Order Quantity"])
                                if qty > 0: s.execute(text("INSERT INTO purchase_order_items (order_id, flavor_code, ordered_units) VALUES (:poid, :code, :qty);"), {"poid": loaded_po_id, "code": row["Code"], "qty": qty})
                            s.commit()
                        show_success_modal(f"Purchase Order #{loaded_po_id} updated successfully! Final Amount: ₹{e_final_amount:,.2f}.")
                    except Exception as e: st.error(f"Could not update purchase order: {e}")

elif page == "Freezer Stock" and user_role == "admin":
    st.subheader("Freezer Stock Management")
    st.caption("All entries are persisted directly to PostgreSQL as the single source of truth.")

    freezer_tab_choice = st.radio("Section", ["Stock Received (Inward)", "Stock Audit (Physical Count)"], horizontal=True)

    if freezer_tab_choice == "Stock Received (Inward)":
        stock_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="db_stock_mode")

        past_receipts_df = db_conn.query("SELECT r.id, r.received_date, r.location, r.purchase_order_id, r.payment_amount, r.payment_status, r.payment_date, r.payment_details, r.damaged_returned_on, r.notes, json_agg(json_build_object('code', i.flavor_code, 'rec', i.received_units, 'dam', i.damaged_units, 'cost', i.unit_cost_price)) AS items FROM stock_received r LEFT JOIN stock_received_items i ON r.id = i.received_id GROUP BY r.id ORDER BY r.received_date DESC, r.id DESC;", ttl="0s")
        past_receipts = past_receipts_df.to_dict("records") if not past_receipts_df.empty else []

        stock_loaded, loaded_id = None, None
        if stock_mode == "Edit past entry":
            if not past_receipts: st.info("No past delivery receipts found in database.")
            else:
                labels = [f"Receipt #{r['id']} — {pd.to_datetime(r['received_date']).strftime('%d %b %Y')} ({r['location']})" for r in past_receipts]
                selected_rec = st.selectbox("Select delivery receipt to edit", labels, key="db_stock_select")
                stock_loaded = past_receipts[labels.index(selected_rec)]; loaded_id = stock_loaded["id"]

        sk = f"_{loaded_id}" if loaded_id else "_new"
        existing_rec_notes = str(stock_loaded.get("notes") or "") if stock_loaded else ""
        default_rec_disc, clean_rec_notes = 2.0, existing_rec_notes
        if stock_loaded:
            disc_match = re.search(r"\[Discount:\s*([\d.]+)%[^\]]*\]", existing_rec_notes)
            if disc_match:
                try: default_rec_disc = float(re.search(r"([\d.]+)", disc_match.group(0)).group(1)); clean_rec_notes = re.sub(r"\[Discount:[^\]]*\]\s*", "", existing_rec_notes).strip()
                except Exception: default_rec_disc = 2.0

        pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders WHERE order_status != 'Completed' ORDER BY order_date DESC;", ttl="0s")
        po_options = ["None (Ad-hoc delivery)"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d %b')})" for _, r in pos_df.iterrows()]
        
        default_po_idx = 0
        poid_raw = stock_loaded.get("purchase_order_id") if stock_loaded else None
        if poid_raw is not None and pd.notna(poid_raw) and str(poid_raw).strip() != "":
            try:
                poid_int = int(float(poid_raw))
                for idx, opt in enumerate(po_options):
                    if opt.startswith(f"PO #{poid_int} "): default_po_idx = idx; break
            except Exception: default_po_idx = 0

        c1, c2, c3, c4 = st.columns(4)
        with c1: received_date = st.date_input("Received date", value=pd.to_datetime(stock_loaded["received_date"]).date() if (stock_loaded and stock_loaded.get("received_date")) else date.today(), key=f"rec_date{sk}")
        with c2: location = st.text_input("Location", value=str(stock_loaded["location"]) if (stock_loaded and stock_loaded.get("location")) else CITY, key=f"rec_loc{sk}")
        with c3: selected_po = st.selectbox("Link to Purchase Order (Optional)", po_options, index=default_po_idx, key=f"rec_po{sk}")
        with c4: rec_discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=default_rec_disc, step=0.5, format="%.2f", key=f"rec_disc{sk}")

        items_map = {itm["code"]: itm for itm in stock_loaded["items"] if isinstance(itm, dict) and "code" in itm} if stock_loaded and stock_loaded.get("items") and isinstance(stock_loaded["items"], list) else {}
        grid_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost Price (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Received": int(items_map[code]["rec"]) if (code in items_map and items_map[code].get("rec") is not None) else 0, "Damaged": int(items_map[code]["dam"]) if (code in items_map and items_map[code].get("dam") is not None) else 0} for code in FLAVOR_CODES]

        st.write("Enter units received per flavour:")
        stock_edited = st.data_editor(pd.DataFrame(grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost Price (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Received": st.column_config.NumberColumn(min_value=0, step=1, format="%d"), "Damaged": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, key=f"db_stock_editor{sk}")

        tot_received, tot_damaged = int(stock_edited["Received"].sum()), int(stock_edited["Damaged"].sum())
        gross_cost_val = float(sum(stock_edited["Received"] * stock_edited["Unit Cost Price (₹)"]))
        rec_discount_amount = gross_cost_val * (rec_discount_pct / 100.0)
        net_cost_val = gross_cost_val - rec_discount_amount

        st.markdown("#### Entry Summary")
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)
        s_col1.metric("Total Received", f"{tot_received} units"); s_col2.metric("Total Damaged", f"{tot_damaged} units"); s_col3.metric("Gross Cost", f"₹{gross_cost_val:,.2f}"); s_col4.metric(f"Net Cost ({rec_discount_pct:.1f}% off)", f"₹{net_cost_val:,.2f}")

        st.markdown("---"); st.write("**Payment & Logistics**")
        c5, c6 = st.columns(2)
        with c5: payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=float(stock_loaded["payment_amount"]) if (stock_loaded and stock_loaded.get("payment_amount") is not None) else float(net_cost_val), step=10.0, key=f"db_rec_pay{sk}")
        with c6: payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(stock_loaded["payment_status"]) if (stock_loaded and stock_loaded.get("payment_status") in PAYMENT_STATUSES) else 0, key=f"db_rec_status{sk}")

        has_payment_date = st.checkbox("Add payment date", value=bool(stock_loaded and stock_loaded.get("payment_date")), key=f"db_rec_has_pdate{sk}")
        payment_date = st.date_input("Payment date", value=pd.to_datetime(stock_loaded["payment_date"]).date() if (stock_loaded and stock_loaded.get("payment_date")) else date.today(), key=f"db_rec_pdate{sk}") if has_payment_date else None
        payment_details = st.text_input("Payment details (optional)", value=str(stock_loaded["payment_details"]) if (stock_loaded and stock_loaded.get("payment_details")) else "", key=f"db_rec_pdet{sk}")
        has_dam_ret = st.checkbox("Damaged items were returned", value=bool(stock_loaded and stock_loaded.get("damaged_returned_on")), key=f"db_rec_has_dam{sk}")
        damaged_returned_on = st.date_input("Damaged returned date", value=pd.to_datetime(stock_loaded["damaged_returned_on"]).date() if (stock_loaded and stock_loaded.get("damaged_returned_on")) else date.today(), key=f"db_rec_damdate{sk}") if has_dam_ret else None
        notes = st.text_input("Notes (optional)", value=clean_rec_notes, key=f"db_rec_notes{sk}")

        if st.button("Update delivery entry" if loaded_id else "Save stock received", type="primary", use_container_width=True):
            if tot_received == 0: st.error("Enter at least one quantity received before saving.")
            else:
                po_id = int(selected_po.split("#")[1].split(" ")[0]) if "PO #" in selected_po else None
                try:
                    combined_rec_notes = notes.strip()
                    if rec_discount_pct > 0: combined_rec_notes = f"[Discount: {rec_discount_pct:.2f}% | Net: ₹{net_cost_val:,.2f}] {combined_rec_notes}".strip()
                    with db_conn.session as s:
                        if loaded_id:
                            s.execute(text("UPDATE stock_received SET received_date = :rd, location = :loc, purchase_order_id = :poid, payment_amount = :amt, payment_status = :stat, payment_date = :pdate, payment_details = :pdet, damaged_returned_on = :dret, notes = :notes WHERE id = :id;"), {"rd": received_date, "loc": location, "poid": po_id, "amt": payment_amount, "stat": payment_status, "pdate": payment_date, "pdet": payment_details, "dret": damaged_returned_on, "notes": combined_rec_notes, "id": loaded_id})
                            s.execute(text("DELETE FROM stock_received_items WHERE received_id = :id;"), {"id": loaded_id})
                            rec_id = loaded_id
                        else:
                            res = s.execute(text("INSERT INTO stock_received (received_date, location, purchase_order_id, payment_amount, payment_status, payment_date, payment_details, damaged_returned_on, notes) VALUES (:rd, :loc, :poid, :amt, :stat, :pdate, :pdet, :dret, :notes) RETURNING id;"), {"rd": received_date, "loc": location, "poid": po_id, "amt": payment_amount, "stat": payment_status, "pdate": payment_date, "pdet": payment_details, "dret": damaged_returned_on, "notes": combined_rec_notes})
                            rec_id = res.scalar()
                        for _, row in stock_edited.iterrows():
                            if int(row["Received"]) > 0 or int(row["Damaged"]) > 0: s.execute(text("INSERT INTO stock_received_items (received_id, flavor_code, received_units, damaged_units, unit_cost_price) VALUES (:rid, :code, :rec, :dam, :cost);"), {"rid": rec_id, "code": row["Code"], "rec": int(row["Received"]), "dam": int(row["Damaged"]), "cost": float(row["Unit Cost Price (₹)"])})
                        s.commit()
                    show_success_modal(f"Stock delivery #{rec_id} saved successfully! Logged {tot_received} units (Net Cost: ₹{net_cost_val:,.2f}).")
                except Exception as e: st.error(f"Could not save to database: {e}")

    elif freezer_tab_choice == "Stock Audit (Physical Count)":
        st.write("Log a physical stock count from the freezer to calculate inventory variance.")
        aud_c1, aud_c2, aud_c3 = st.columns(3)
        with aud_c1: audit_date = st.date_input("Audit date", value=date.today(), key="audit_dt_entry")
        with aud_c2: audit_location = st.text_input("Freezer / Location", value=CITY, key="audit_loc_entry")
        with aud_c3: audited_by = st.text_input("Audited by", value="Admin", key="audit_by_entry")

        freezer_curr_df = get_db_freezer_stock()
        sys_stock_map = dict(zip(freezer_curr_df["code"], freezer_curr_df["Units in freezer"])) if not freezer_curr_df.empty else {}

        audit_grid = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Current System Stock": int(sys_stock_map.get(code, 0)), "Physical Counted Units": int(sys_stock_map.get(code, 0))} for code in FLAVOR_CODES]
        audit_edited = st.data_editor(pd.DataFrame(audit_grid), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Current System Stock": st.column_config.NumberColumn(disabled=True, format="%d"), "Physical Counted Units": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, key="audit_editor_grid")
        audit_remarks = st.text_input("Audit remarks / observation notes", key="audit_remarks_input")

        if st.button("Save stock audit", type="primary", use_container_width=True):
            try:
                phys_by_code = {row["Code"]: int(row["Physical Counted Units"]) for _, row in audit_edited.iterrows()}
                with db_conn.session as s:
                    res = s.execute(text("INSERT INTO stock_audits_wide (audit_date, location, audited_by, remarks, ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units) VALUES (:adt, :loc, :by, :rem, :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra) RETURNING audit_id;"), {"adt": audit_date, "loc": audit_location, "by": audited_by, "rem": audit_remarks, "ml": phys_by_code.get("ML", 0), "mm": phys_by_code.get("MM", 0), "ps": phys_by_code.get("PS", 0), "mn": phys_by_code.get("MN", 0), "kb": phys_by_code.get("KB", 0), "bm": phys_by_code.get("BM", 0), "sg": phys_by_code.get("SG", 0), "ch": phys_by_code.get("CH", 0), "ra": phys_by_code.get("RA", 0)})
                    aid = res.scalar()
                    s.commit()
                show_success_modal(f"Stock Audit #{aid} logged successfully into PostgreSQL!")
            except Exception as e: st.error(f"Could not save audit to database: {e}")

elif page == "Freezer Analysis" and user_role == "admin":
    st.subheader("Freezer Stock Analysis & Reorder Planner")
    st.caption("Live comparison of Physical Audit vs Calculated Stock with velocity-based reorder recommendations.")

    ac1, ac2, ac3 = st.columns(3)
    with ac1: lookback_days = st.number_input("Sales Velocity Window (days)", min_value=3, max_value=90, value=14, step=1)
    with ac2: buffer_days = st.number_input("Safety Buffer Threshold (days)", min_value=0, max_value=14, value=3, step=1)
    with ac3: cover_days = st.number_input("Reorder Coverage Target (days)", min_value=1, max_value=30, value=7, step=1)

    try:
        today_fa = date.today()
        cutoff_fa = today_fa - timedelta(days=int(lookback_days) - 1)
        flavor_sales_df = load_db_flavor_sales(start_date=cutoff_fa, end_date=today_fa)
        sales_pace_map = dict(zip(flavor_sales_df["code"], flavor_sales_df["Units sold"])) if not flavor_sales_df.empty else {}

        latest_audit_df = db_conn.query("SELECT * FROM stock_audits_wide ORDER BY audit_date DESC, audit_id DESC LIMIT 1;", ttl="0s")
        if not latest_audit_df.empty:
            audit_row = latest_audit_df.iloc[0]
            audit_date_val = pd.to_datetime(audit_row["audit_date"]).date()
            audit_map = {code: int(audit_row.get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES}
            audit_date_str = pd.to_datetime(audit_row["audit_date"]).strftime("%d %b %Y")
        else:
            audit_date_val, audit_map, audit_date_str = None, {}, "No audits logged"

        rec_df = db_conn.query("SELECT flavor_code, SUM(received_units) AS total_recv FROM stock_received_items GROUP BY flavor_code;", ttl="0s")
        rec_map = dict(zip(rec_df["flavor_code"], rec_df["total_recv"])) if not rec_df.empty else {}

        added_df = db_conn.query("SELECT flavor_code, SUM(added_units) AS total_added FROM daily_cart_items GROUP BY flavor_code;", ttl="0s")
        added_map = dict(zip(added_df["flavor_code"], added_df["total_added"])) if not added_df.empty else {}

        rem_map = get_db_stock_removed_map()

        if audit_date_val is not None:
            rec_audit_df = db_conn.query("SELECT ri.flavor_code, COALESCE(SUM(ri.received_units), 0) AS total_recv FROM stock_received_items ri JOIN stock_received r ON ri.received_id = r.id WHERE r.received_date <= :adate GROUP BY ri.flavor_code;", params={"adate": audit_date_val}, ttl="0s")
            rec_map_audit = dict(zip(rec_audit_df["flavor_code"], rec_audit_df["total_recv"])) if not rec_audit_df.empty else {}
            added_audit_df = db_conn.query("SELECT i.flavor_code, COALESCE(SUM(i.added_units), 0) AS total_added FROM daily_cart_items i JOIN daily_cart_entries e ON i.daily_entry_id = e.id WHERE e.entry_date <= :adate GROUP BY i.flavor_code;", params={"adate": audit_date_val}, ttl="0s")
            added_map_audit = dict(zip(added_audit_df["flavor_code"], added_audit_df["total_added"])) if not added_audit_df.empty else {}
            rem_audit_df = db_conn.query("SELECT COALESCE(SUM(ml_units), 0) AS ml_units, COALESCE(SUM(mm_units), 0) AS mm_units, COALESCE(SUM(ps_units), 0) AS ps_units, COALESCE(SUM(mn_units), 0) AS mn_units, COALESCE(SUM(kb_units), 0) AS kb_units, COALESCE(SUM(bm_units), 0) AS bm_units, COALESCE(SUM(sg_units), 0) AS sg_units, COALESCE(SUM(ch_units), 0) AS ch_units, COALESCE(SUM(ra_units), 0) AS ra_units FROM stock_removed WHERE removal_date <= :adate;", params={"adate": audit_date_val}, ttl="0s")
            rem_map_audit = {code: int(rem_audit_df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES} if not rem_audit_df.empty else {code: 0 for code in FLAVOR_CODES}
        else:
            rec_map_audit, added_map_audit, rem_map_audit = rec_map, added_map, rem_map
    except Exception as e:
        st.error(f"Could not load analysis transactions from database: {e}")
        sales_pace_map, rec_map, added_map, rem_map, audit_map, rec_map_audit, added_map_audit, rem_map_audit, audit_date_str = {}, {}, {}, {}, {}, {}, {}, {}, "N/A"

    st.markdown("---"); st.markdown(f"### 1. Physical Stock vs Calculated Freezer Stock &nbsp; *(As on Audit Date: {audit_date_str})*")
    comparison_rows = []
    tot_rec_a, tot_issued_a, tot_removed_a, tot_calc_a, tot_phys, has_audit = 0, 0, 0, 0, 0, bool(audit_map)

    for code in FLAVOR_CODES:
        f_info = FLAVOR_MAP[code]
        recv_units, issued_units, removed_units = int(rec_map_audit.get(code, 0)), int(added_map_audit.get(code, 0)), int(rem_map_audit.get(code, 0))
        calc_stock = recv_units - issued_units - removed_units
        tot_rec_a += recv_units; tot_issued_a += issued_units; tot_removed_a += removed_units; tot_calc_a += calc_stock

        phys_stock = audit_map.get(code, None)
        if phys_stock is not None:
            phys_stock = int(phys_stock); tot_phys += phys_stock; var_qty = phys_stock - calc_stock
            var_status = "✅ Match" if var_qty == 0 else (f"🟢 +{var_qty}" if var_qty > 0 else f"🔴 {var_qty}")
            phys_display, var_display = str(phys_stock), str(var_qty)
        else: phys_display, var_display, var_status = "—", "—", "⚪ Missing"

        comparison_rows.append({"Flavour": f_info["name"], "Received (In)": recv_units, "Issued (Carts)": issued_units, "Removed": removed_units, "Calc. Stock": calc_stock, "Physical Audit": phys_display, "Variance": var_display, "Audit Status": var_status})

    c_m1, c_m2, c_m3, c_m4, c_m5, c_m6 = st.columns(6)
    c_m1.metric("Inward (at Audit)", f"{tot_rec_a} pcs"); c_m2.metric("Issued (at Audit)", f"{tot_issued_a} pcs"); c_m3.metric("Removed (at Audit)", f"{tot_removed_a} pcs"); c_m4.metric("Calc. Stock (at Audit)", f"{tot_calc_a} pcs"); c_m5.metric("Physical Audited", f"{tot_phys} pcs" if has_audit else "Not Available")
    net_var = tot_phys - tot_calc_a if has_audit else 0
    c_m6.metric("Net Variance", f"{net_var:+d} pcs" if has_audit else "N/A")

    comp_df = pd.DataFrame(comparison_rows)
    comp_df = pd.concat([comp_df, pd.DataFrame([{"Flavour": "🔥 OVERALL TOTAL", "Received (In)": tot_rec_a, "Issued (Carts)": tot_issued_a, "Removed": tot_removed_a, "Calc. Stock": tot_calc_a, "Physical Audit": str(tot_phys) if has_audit else "—", "Variance": f"{net_var:+d}" if has_audit else "—", "Audit Status": "✅ Match" if net_var == 0 and has_audit else (f"⚠️ {net_var:+d}" if has_audit else "—")}])], ignore_index=True)
    st.dataframe(comp_df, hide_index=True, use_container_width=True, height=370)

    st.markdown("---"); st.markdown("### 2. Suggested Orders & Inventory Runway &nbsp; *(Calculated from Live Freezer Stock Today)*")
    reorder_rows, trigger_dates, tot_calc_active, tot_rate, tot_suggested_units, tot_order_cost = [], [], 0, 0.0, 0, 0.0

    for code in FLAVOR_CODES:
        f_info = FLAVOR_MAP[code]
        avail_stock = int(rec_map.get(code, 0)) - int(added_map.get(code, 0)) - int(rem_map.get(code, 0))
        tot_calc_active += avail_stock
        rate = float(sales_pace_map.get(code, 0)) / lookback_days
        tot_rate += rate
        target_req = int(round(rate * (buffer_days + cover_days)))

        if rate <= 0: status, days_left, suggested_qty, reason = "⚪ No Sales", None, 0, "No active sales logged"
        else:
            days_left = avail_stock / rate
            trigger_dates.append(today_fa + timedelta(days=max(0, int(days_left - buffer_days))))
            if avail_stock <= (rate * buffer_days): status, suggested_qty, reason = "🔴 Order Now", max(0, int(round((target_req - avail_stock) / 10.0)) * 10), f"Stock below {buffer_days}d buffer"
            elif avail_stock <= (rate * (buffer_days + 2)): status, suggested_qty, reason = "🟡 Order Soon", max(0, int(round((target_req - avail_stock) / 10.0)) * 10), f"Reaches buffer in < 2 days"
            else: status, suggested_qty, reason = "🟢 OK", 0, f"Stock covers {int(round(days_left))} days"

        tot_suggested_units += suggested_qty; tot_order_cost += (suggested_qty * f_info["cost_price"])
        reorder_rows.append({"Flavour": f_info["name"], "Calculated Stock": avail_stock, "Daily Pace": f"{rate:.1f} /d", "Runway": f"{int(round(days_left))} days" if days_left is not None else "—", "Target Buffer": target_req, "Suggested Order": int(suggested_qty), "Urgency": status, "Rationale": reason})

    r_m1, r_m2, r_m3, r_m4 = st.columns(4)
    overall_order_date = min(trigger_dates) if trigger_dates else None
    r_m1.metric("Calculated Active Stock", f"{tot_calc_active} units"); r_m2.metric("Daily Velocity", f"{tot_rate:.1f} units/day"); r_m3.metric("Total Order Quantity", f"{tot_suggested_units} pcs"); r_m4.metric("Estimated PO Cost", f"₹{tot_order_cost:,.2f}")

    if overall_order_date is not None:
        if overall_order_date <= today_fa: st.error(f"🚨 **Action Required:** At least one flavor has breached the safety buffer based on calculated stock. Place replenishment order today!")
        else: st.info(f"📅 **Next Order Milestone:** Estimated order placement on **{overall_order_date.strftime('%d %b %Y')}** ({(overall_order_date - today_fa).days} days remaining).")

    reorder_df = pd.DataFrame(reorder_rows)
    reorder_df = pd.concat([reorder_df, pd.DataFrame([{"Flavour": "🔥 OVERALL TOTAL", "Calculated Stock": tot_calc_active, "Daily Pace": f"{tot_rate:.1f} /d", "Runway": f"{(tot_calc_active / tot_rate):.0f} days" if tot_rate > 0 else "—", "Target Buffer": int(round(tot_rate * (buffer_days + cover_days))), "Suggested Order": tot_suggested_units, "Urgency": "🔴 Order Now" if overall_order_date and overall_order_date <= today_fa else "🟢 Stable", "Rationale": f"Est Cost: ₹{tot_order_cost:,.0f}"}])], ignore_index=True)
    st.dataframe(reorder_df, hide_index=True, use_container_width=True, height=370)

    st.markdown("---"); st.markdown("### 3. Detailed Stock Movement Logs")
    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["📋 Purchase Orders", "📦 Received Deliveries", "🔍 Physical Stock Audits", "🗑️ Stock Removed"])

    with m_tab1:
        po_query_df = db_conn.query("SELECT p.id AS \"PO #\", p.order_date AS \"Order Date\", p.expected_date AS \"Expected Date\", p.location AS \"Location\", p.order_status AS \"Status\", json_agg(json_build_object('code', pi.flavor_code, 'qty', pi.ordered_units)) AS items FROM purchase_orders p LEFT JOIN purchase_order_items pi ON p.id = pi.order_id GROUP BY p.id ORDER BY p.order_date DESC;", ttl="0s")
        if not po_query_df.empty:
            po_display = []
            for _, r in po_query_df.iterrows():
                items_dict = {itm['code']: itm['qty'] for itm in r['items']} if r['items'] else {}
                row_data = {"PO #": f"PO #{r['PO #']}", "Order Date": pd.to_datetime(r['Order Date']).strftime("%d %b %Y"), "Expected": pd.to_datetime(r['Expected Date']).strftime("%d %b %Y") if pd.notna(r['Expected Date']) else "—", "Location": r['Location'], "Status": r['Status'], "Total Qty": sum(int(q or 0) for q in items_dict.values())}
                for code in FLAVOR_CODES: row_data[code] = items_dict.get(code, 0)
                po_display.append(row_data)
            st.dataframe(pd.DataFrame(po_display), hide_index=True, use_container_width=True)
        else: st.caption("No purchase orders found in database.")

    with m_tab2:
        rec_query_df = db_conn.query("SELECT r.id AS \"Receipt #\", r.received_date AS \"Received Date\", r.location AS \"Location\", r.purchase_order_id AS \"PO Ref\", r.payment_status AS \"Payment\", json_agg(json_build_object('code', ri.flavor_code, 'rec', ri.received_units)) AS items FROM stock_received r LEFT JOIN stock_received_items ri ON r.id = ri.received_id GROUP BY r.id ORDER BY r.received_date DESC;", ttl="0s")
        if not rec_query_df.empty:
            rec_display = []
            for _, r in rec_query_df.iterrows():
                items_dict = {itm['code']: itm['rec'] for itm in r['items']} if r['items'] else {}
                row_data = {"Receipt #": f"#{r['Receipt #']}", "Received Date": pd.to_datetime(r['Received Date']).strftime("%d %b %Y"), "Location": r['Location'], "Linked PO": f"PO #{r['PO Ref']}" if pd.notna(r['PO Ref']) else "Ad-hoc", "Payment Status": r['Payment'], "Total Received": sum(int(q or 0) for q in items_dict.values())}
                for code in FLAVOR_CODES: row_data[code] = items_dict.get(code, 0)
                rec_display.append(row_data)
            st.dataframe(pd.DataFrame(rec_display), hide_index=True, use_container_width=True)
        else: st.caption("No stock receipts recorded in database.")

    with m_tab3:
        audit_query_df = db_conn.query("SELECT audit_id AS \"Audit #\", audit_date AS \"Audit Date\", location AS \"Location\", audited_by AS \"Auditor\", total_physical_units AS \"Total Count\", remarks AS \"Remarks\", ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units FROM stock_audits_wide ORDER BY audit_date DESC, audit_id DESC;", ttl="0s")
        if not audit_query_df.empty:
            aud_display = []
            for _, r in audit_query_df.iterrows():
                row_data = {"Audit #": f"#{r['Audit #']}", "Audit Date": pd.to_datetime(r['Audit Date']).strftime("%d %b %Y"), "Location": r['Location'], "Audited By": r['Auditor'], "Total Count": r['Total Count'], "Remarks": r['Remarks']}
                for code in FLAVOR_CODES: row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                aud_display.append(row_data)
            st.dataframe(pd.DataFrame(aud_display), hide_index=True, use_container_width=True)
        else: st.caption("No physical stock audits recorded in database.")

    with m_tab4:
        rem_query_df = db_conn.query("SELECT id AS \"ID\", removal_date AS \"Date\", location AS \"Location\", ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, total_units AS \"Total Units\", cost_price_of_removed_items AS \"Cost (₹)\", reason_for_removal AS \"Reason\", removed_by AS \"Removed By\", verified_by AS \"Verified By\" FROM stock_removed ORDER BY removal_date DESC, id DESC;", ttl="0s")
        if not rem_query_df.empty:
            rem_display = []
            for _, r in rem_query_df.iterrows():
                row_data = {"ID": f"#{r['ID']}", "Date": pd.to_datetime(r['Date']).strftime("%d %b %Y"), "Location": r['Location'], "Total Units": int(r['Total Units']) if pd.notna(r['Total Units']) else sum(int(r.get(FLAVOR_MAP[c]['audit_col'], 0)) for c in FLAVOR_CODES), "Cost (₹)": float(r['Cost (₹)']), "Reason": r['Reason'], "Removed By": r['Removed By'] if pd.notna(r['Removed By']) else "", "Verified By": r['Verified By']}
                for code in FLAVOR_CODES: row_data[code] = int(r.get(FLAVOR_MAP[c]['audit_col'], 0))
                rem_display.append(row_data)
            st.dataframe(pd.DataFrame(rem_display), hide_index=True, use_container_width=True)
        else: st.caption("No stock removals recorded in database.")

elif page == "Stock Removed" and user_role == "admin":
    st.subheader("Stock Removed / Wastage Log")
    st.caption("Record units removed from the freezer (damages, expiry, sampling, staff consumption, or supplier returns).")

    rem_mode = st.radio("Mode", ["New Entry", "View Entries", "Edit Past Entry"], horizontal=True, key="rem_screen_mode")

    if rem_mode == "New Entry":
        st.write("Enter details and specify quantities removed per flavour:")
        c1, c2, c3, c4 = st.columns(4)
        with c1: removal_date = st.date_input("Removal Date", value=date.today(), key="new_rem_date")
        with c2: location = st.text_input("Location", value=CITY, key="new_rem_loc")
        with c3: removed_by = st.text_input("Removed By", placeholder="e.g. Staff / Cart Boy", key="new_rem_rby")
        with c4: verified_by = st.text_input("Verified By", value="Admin", key="new_rem_vby")

        reason_for_removal = st.text_input("Reason for Removal (Mandatory)", key="new_rem_reason", placeholder="e.g. Broken packaging, expired batch, festival sampling...")
        rem_grid_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Units Removed": 0} for code in FLAVOR_CODES]

        st.write("Enter units removed per flavour:")
        rem_editor_df = st.data_editor(pd.DataFrame(rem_grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Units Removed": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, key="new_rem_editor")

        tot_rem_units = int(rem_editor_df["Units Removed"].sum())
        tot_rem_cost = float(sum(rem_editor_df["Units Removed"] * rem_editor_df["Unit Cost (₹)"]))

        st.markdown("#### Removal Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Units Removed", f"{tot_rem_units} units"); m2.metric("Total Cost Value", f"₹{tot_rem_cost:,.2f}"); m3.metric("Date of Removal", removal_date.strftime("%d %b %Y"))

        if st.button("🗑️ Save Stock Removal", type="primary", use_container_width=True):
            if tot_rem_units <= 0: st.error("Please enter at least one quantity greater than 0 before saving.")
            elif not reason_for_removal.strip(): st.error("Reason for removal is mandatory. Please provide a brief explanation.")
            else:
                try:
                    units_map = dict(zip(rem_editor_df["Code"], rem_editor_df["Units Removed"]))
                    with db_conn.session as s:
                        res = s.execute(text("INSERT INTO stock_removed (removal_date, location, ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, cost_price_of_removed_items, reason_for_removal, removed_by, verified_by) VALUES (:rd, :loc, :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra, :cost, :reason, :rby, :vby) RETURNING id;"), {"rd": removal_date, "loc": location, "ml": int(units_map.get("ML", 0)), "mm": int(units_map.get("MM", 0)), "ps": int(units_map.get("PS", 0)), "mn": int(units_map.get("MN", 0)), "kb": int(units_map.get("KB", 0)), "bm": int(units_map.get("BM", 0)), "sg": int(units_map.get("SG", 0)), "ch": int(units_map.get("CH", 0)), "ra": int(units_map.get("RA", 0)), "cost": tot_rem_cost, "reason": reason_for_removal.strip(), "rby": removed_by.strip(), "vby": verified_by.strip()})
                        new_rem_id = res.scalar()
                        s.commit()
                    show_success_modal(f"Stock Removal #{new_rem_id} recorded successfully! Logged {tot_rem_units} units (₹{tot_rem_cost:,.2f}).")
                except Exception as e: st.error(f"Could not save stock removal to database: {e}")

    elif rem_mode == "View Entries":
        rem_query_df = db_conn.query("SELECT id AS \"ID\", removal_date AS \"Date\", location AS \"Location\", ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, total_units AS \"Total Units\", cost_price_of_removed_items AS \"Cost (₹)\", reason_for_removal AS \"Reason\", removed_by AS \"Removed By\", verified_by AS \"Verified By\" FROM stock_removed ORDER BY removal_date DESC, id DESC;", ttl="0s")
        if rem_query_df.empty: st.info("No stock removal logs found in the database.")
        else:
            total_logs = len(rem_query_df)
            total_removed_units = int(rem_query_df["Total Units"].sum()) if "Total Units" in rem_query_df.columns else 0
            total_removed_cost = float(rem_query_df["Cost (₹)"].sum())

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Removal Events", f"{total_logs}"); k2.metric("Total Units Removed", f"{total_removed_units} pcs"); k3.metric("Total Value of Removed Stock", f"₹{total_removed_cost:,.2f}")

            display_rem_list = []
            for _, r in rem_query_df.iterrows():
                row_data = {"ID": f"#{r['ID']}", "Date": pd.to_datetime(r['Date']).strftime("%d %b %Y"), "Location": r['Location'], "Total Units": int(r['Total Units']) if pd.notna(r['Total Units']) else sum(int(r.get(FLAVOR_MAP[c]['audit_col'], 0)) for c in FLAVOR_CODES), "Cost (₹)": float(r['Cost (₹)']), "Reason": r['Reason'], "Removed By": r['Removed By'] if pd.notna(r['Removed By']) else "", "Verified By": r['Verified By']}
                for code in FLAVOR_CODES: row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                display_rem_list.append(row_data)

            st.dataframe(pd.DataFrame(display_rem_list), hide_index=True, use_container_width=True, column_config={"Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f")})

    elif rem_mode == "Edit Past Entry":
        rem_query_df = db_conn.query("SELECT id, removal_date, location, ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, cost_price_of_removed_items, reason_for_removal, removed_by, verified_by FROM stock_removed ORDER BY removal_date DESC, id DESC;", ttl="0s")
        if rem_query_df.empty: st.info("No past stock removals found in database.")
        else:
            rem_records = rem_query_df.to_dict("records")
            rem_labels = [f"Removal #{r['id']} — {pd.to_datetime(r['removal_date']).strftime('%d %b %Y')} ({r['location']}) — {str(r['reason_for_removal'])[:25]} (₹{float(r['cost_price_of_removed_items']):,.0f})" for r in rem_records]
            sel_rem_label = st.selectbox("Select removal entry to edit", rem_labels, key="edit_rem_select")
            loaded_rem = rem_records[rem_labels.index(sel_rem_label)]
            loaded_rem_id = loaded_rem["id"]

            c1, c2, c3, c4 = st.columns(4)
            with c1: e_rem_date = st.date_input("Removal Date", value=pd.to_datetime(loaded_rem["removal_date"]).date() if loaded_rem.get("removal_date") else date.today(), key=f"edit_rem_date_{loaded_rem_id}")
            with c2: e_rem_loc = st.text_input("Location", value=str(loaded_rem.get("location", CITY)), key=f"edit_rem_loc_{loaded_rem_id}")
            with c3: e_rem_rby = st.text_input("Removed By", value=str(loaded_rem.get("removed_by") or ""), key=f"edit_rem_rby_{loaded_rem_id}")
            with c4: e_rem_vby = st.text_input("Verified By", value=str(loaded_rem.get("verified_by", "Admin")), key=f"edit_rem_vby_{loaded_rem_id}")

            e_rem_reason = st.text_input("Reason for Removal", value=str(loaded_rem.get("reason_for_removal") or ""), key=f"edit_rem_reason_{loaded_rem_id}")
            edit_rem_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Units Removed": int(loaded_rem.get(FLAVOR_MAP[code]["audit_col"], 0))} for code in FLAVOR_CODES]

            st.write("Modify units removed per flavour:")
            rem_edit_editor_df = st.data_editor(pd.DataFrame(edit_rem_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Units Removed": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, key=f"edit_rem_editor_{loaded_rem_id}")

            e_tot_rem_units = int(rem_edit_editor_df["Units Removed"].sum())
            e_tot_rem_cost = float(sum(rem_edit_editor_df["Units Removed"] * rem_edit_editor_df["Unit Cost (₹)"]))

            st.markdown("#### Updated Summary")
            em1, em2, em3 = st.columns(3)
            em1.metric("Total Units Removed", f"{e_tot_rem_units} units"); em2.metric("Total Cost Value", f"₹{e_tot_rem_cost:,.2f}"); em3.metric("Date", e_rem_date.strftime("%d %b %Y"))

            if st.button("💾 Update Stock Removal", type="primary", use_container_width=True):
                if e_tot_rem_units <= 0: st.error("Please enter at least one quantity greater than 0.")
                elif not e_rem_reason.strip(): st.error("Reason for removal cannot be empty.")
                else:
                    try:
                        e_units_map = dict(zip(rem_edit_editor_df["Code"], rem_edit_editor_df["Units Removed"]))
                        with db_conn.session as s:
                            s.execute(text("UPDATE stock_removed SET removal_date = :rd, location = :loc, ml_units = :ml, mm_units = :mm, ps_units = :ps, mn_units = :mn, kb_units = :kb, bm_units = :bm, sg_units = :sg, ch_units = :ch, ra_units = :ra, cost_price_of_removed_items = :cost, reason_for_removal = :reason, removed_by = :rby, verified_by = :vby, updated_at = NOW() WHERE id = :id;"), {"rd": e_rem_date, "loc": e_rem_loc, "ml": int(e_units_map.get("ML", 0)), "mm": int(e_units_map.get("MM", 0)), "ps": int(e_units_map.get("PS", 0)), "mn": int(e_units_map.get("MN", 0)), "kb": int(e_units_map.get("KB", 0)), "bm": int(e_units_map.get("BM", 0)), "sg": int(e_units_map.get("SG", 0)), "ch": int(e_units_map.get("CH", 0)), "ra": int(e_units_map.get("RA", 0)), "cost": e_tot_rem_cost, "reason": e_rem_reason.strip(), "rby": e_rem_rby.strip(), "vby": e_rem_vby.strip(), "id": loaded_rem_id})
                            s.commit()
                        show_success_modal(f"Stock Removal #{loaded_rem_id} updated successfully! Final Value: ₹{e_tot_rem_cost:,.2f}.")
                    except Exception as e: st.error(f"Could not update stock removal entry: {e}")

elif page == "Expenses" and user_role == "admin":
    st.subheader("Expenses & Payments Management")
    st.caption("Manage supplier bills, operating expenses, payments (Cash vs UPI), and settlement balances.")
    exp_nav = st.radio("Section", ["📋 Expenses (Bills / Invoices)", "💳 Payments (Cash Outflows)", "📊 Summary & Date Reports"], horizontal=True, key="exp_nav_sec")

    if exp_nav == "📋 Expenses (Bills / Invoices)":
        e_sub_mode = st.radio("Action", ["View Expenses", "Add New Expense", "Edit Past Expense"], horizontal=True, key="e_sub_mode_rad")
        expenses_summary_df = load_db_expenses_summary_df()

        if e_sub_mode == "Add New Expense":
            st.write("Record a new bill or obligation incurred:")
            pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders ORDER BY order_date DESC;", ttl="0s") if db_conn else pd.DataFrame()
            po_opts = ["None"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d %b')})" for _, r in pos_df.iterrows()] if not pos_df.empty else ["None"]
            staff_opts = load_active_staff_list()

            c1, c2, c3, c4 = st.columns(4)
            with c1: e_date = st.date_input("Expense Date", value=date.today(), key="add_e_date")
            with c2: e_type = st.selectbox("Expense Type", EXPENSE_TYPES, index=0, key="add_e_type")
            with c3: e_cat = st.selectbox("Category", EXPENSE_CATEGORIES, index=0, key="add_e_cat")
            with c4: e_subcat = st.text_input("Sub-Category (Optional)", placeholder="e.g. Dry Ice, Fuel, Repair", key="add_e_subcat")

            c5, c6, c7 = st.columns(3)
            with c5: e_amount = st.number_input("Total Amount (₹)", min_value=0.0, step=10.0, key="add_e_amt")
            with c6: e_attr = st.selectbox("Attributed To", ATTRIBUTED_OPTIONS, index=0, key="add_e_attr")
            with c7: e_vendor = st.text_input("Vendor / Supplier Name", placeholder="e.g. Deep Freeze Services", key="add_e_vendor")

            c8, c9, c10 = st.columns(3)
            with c8: e_staff = st.selectbox("Linked Staff (Optional)", staff_opts, index=0, key="add_e_staff")
            with c9: e_po = st.selectbox("Linked PO (Optional)", po_opts, index=0, key="add_e_po")
            with c10: e_stat = st.selectbox("Initial Status", EXPENSE_STATUSES, index=0, key="add_e_stat")

            e_desc = st.text_input("Description", placeholder="Brief description of the purchase...", key="add_e_desc")
            e_remarks = st.text_input("Remarks / Notes (Optional)", key="add_e_remarks")

            st.markdown("---")
            has_direct_pay = st.checkbox("Record immediate payment now", value=False, key="add_e_direct_pay")
            p_date, p_amt, p_mode, p_ref, p_to, p_notes = None, 0.0, "UPI / Bank Transfer", "", "", ""
            if has_direct_pay:
                p1, p2, p3 = st.columns(3)
                with p1: p_date = st.date_input("Payment Date", value=e_date, key="add_p_date")
                with p2: p_amt = st.number_input("Amount Paid (₹)", min_value=0.0, value=float(e_amount), step=10.0, key="add_p_amt")
                with p3: p_mode = st.selectbox("Payment Mode", PAYMENT_MODES, index=0, key="add_p_mode")
                p4, p5 = st.columns(2)
                with p4: p_ref = st.text_input("Ref / UTR No.", placeholder="e.g. UPI Ref, Txn ID", key="add_p_ref")
                with p5: p_to = st.text_input("Paid To", value=e_vendor, key="add_p_to")
                p_notes = st.text_input("Payment Notes", placeholder="Optional payment note...", key="add_p_notes")

            if st.button("💾 Save Expense Entry", type="primary", use_container_width=True):
                if e_amount <= 0: st.error("Please enter an expense amount greater than 0.")
                else:
                    try:
                        p_po_id = int(e_po.split("#")[1].split(" ")[0]) if "PO #" in e_po else None
                        sel_staff = None if e_staff == "Select Staff" else e_staff
                        computed_status = "Paid" if (has_direct_pay and p_amt >= e_amount) else ("Partially Paid" if (has_direct_pay and p_amt > 0) else e_stat)
                        with db_conn.session as s:
                            res = s.execute(text("INSERT INTO expenses (expense_date, expense_type, category, sub_category, description, total_amount, attributed_to, vendor_name, staff_name, purchase_order_id, status, recorded_by, remarks) VALUES (:ed, :et, :cat, :subcat, :desc, :amt, :attr, :vendor, :staff, :poid, :stat, :recby, :rem) RETURNING id;"), {"ed": e_date, "et": e_type, "cat": e_cat, "subcat": e_subcat.strip(), "desc": e_desc.strip(), "amt": float(e_amount), "attr": e_attr, "vendor": e_vendor.strip(), "staff": sel_staff, "poid": p_po_id, "stat": computed_status, "recby": "Admin", "rem": e_remarks.strip()})
                            new_exp_id = res.scalar()
                            if has_direct_pay and p_amt > 0: s.execute(text("INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes) VALUES (:eid, :pdate, :pamt, :pmode, :pref, :pto, :pby, :notes);"), {"eid": new_exp_id, "pdate": p_date, "pamt": float(p_amt), "pmode": p_mode, "pref": p_ref.strip(), "pto": p_to.strip(), "pby": "Admin", "notes": p_notes.strip()})
                            s.commit()
                        show_success_modal(f"Expense #{new_exp_id} of ₹{e_amount:,.2f} recorded successfully!")
                    except Exception as e: st.error(f"Could not save expense: {e}")

        elif e_sub_mode == "View Expenses":
            if expenses_summary_df.empty: st.info("No expenses found in database.")
            else:
                ek1, ek2, ek3 = st.columns(3)
                ek1.metric("Total Expenses Incurred", f"₹{float(expenses_summary_df['total_amount'].sum()):,.2f}"); ek2.metric("Total Amount Paid", f"₹{float(expenses_summary_df['total_paid'].sum()):,.2f}"); ek3.metric("Outstanding Balance Due", f"₹{float(expenses_summary_df['balance_due'].sum()):,.2f}")
                display_exp = expenses_summary_df.copy()
                display_exp["expense_date"] = pd.to_datetime(display_exp["expense_date"]).dt.strftime("%d %b %Y")
                display_exp["PO Link"] = display_exp["purchase_order_id"].apply(lambda p: f"PO #{int(p)}" if pd.notna(p) else "—")
                st.dataframe(display_exp[["id", "expense_date", "expense_type", "category", "sub_category", "description", "total_amount", "total_paid", "balance_due", "status", "attributed_to", "vendor_name", "PO Link"]].rename(columns={"id": "ID", "expense_date": "Date", "expense_type": "Type", "category": "Category", "sub_category": "Sub-Category", "description": "Description", "total_amount": "Total (₹)", "total_paid": "Paid (₹)", "balance_due": "Balance (₹)", "status": "Status", "attributed_to": "Attributed To", "vendor_name": "Vendor"}), hide_index=True, use_container_width=True, column_config={"Total (₹)": st.column_config.NumberColumn(format="₹%,.2f"), "Paid (₹)": st.column_config.NumberColumn(format="₹%,.2f"), "Balance (₹)": st.column_config.NumberColumn(format="₹%,.2f")})

        elif e_sub_mode == "Edit Past Expense":
            if expenses_summary_df.empty: st.info("No expenses found to edit.")
            else:
                exp_records = expenses_summary_df.to_dict("records")
                exp_labels = [f"#{r['id']} — {pd.to_datetime(r['expense_date']).strftime('%d %b %Y')} — {r['category']} (Total: ₹{float(r['total_amount']):,.0f} | Due: ₹{float(r['balance_due']):,.0f})" for r in exp_records]
                sel_exp_label = st.selectbox("Select Expense to Edit", exp_labels, key="edit_exp_select")
                loaded_exp = exp_records[exp_labels.index(sel_exp_label)]; loaded_exp_id = loaded_exp["id"]
                pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders ORDER BY order_date DESC;", ttl="0s") if db_conn else pd.DataFrame()
                po_opts = ["None"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d %b')})" for _, r in pos_df.iterrows()] if not pos_df.empty else ["None"]
                default_po_idx = next((i for i, o in enumerate(po_opts) if o.startswith(f"PO #{int(loaded_exp['purchase_order_id'])} ")), 0) if loaded_exp.get("purchase_order_id") and pd.notna(loaded_exp["purchase_order_id"]) else 0
                staff_opts = load_active_staff_list(); curr_staff = str(loaded_exp.get("staff_name") or "Select Staff")
                if curr_staff not in staff_opts: staff_opts.append(curr_staff)

                c1, c2, c3, c4 = st.columns(4)
                with c1: e_edit_date = st.date_input("Expense Date", value=pd.to_datetime(loaded_exp["expense_date"]).date(), key=f"ee_date_{loaded_exp_id}")
                with c2: e_edit_type = st.selectbox("Expense Type", EXPENSE_TYPES, index=EXPENSE_TYPES.index(loaded_exp["expense_type"]) if loaded_exp["expense_type"] in EXPENSE_TYPES else 0, key=f"ee_type_{loaded_exp_id}")
                with c3: e_edit_cat = st.selectbox("Category", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(loaded_exp["category"]) if loaded_exp["category"] in EXPENSE_CATEGORIES else 0, key=f"ee_cat_{loaded_exp_id}")
                with c4: e_edit_subcat = st.text_input("Sub-Category", value=str(loaded_exp.get("sub_category") or ""), key=f"ee_subcat_{loaded_exp_id}")

                c5, c6, c7 = st.columns(3)
                with c5: e_edit_amount = st.number_input("Total Amount (₹)", min_value=0.0, value=float(loaded_exp["total_amount"]), step=10.0, key=f"ee_amt_{loaded_exp_id}")
                with c6: e_edit_attr = st.selectbox("Attributed To", ATTRIBUTED_OPTIONS, index=ATTRIBUTED_OPTIONS.index(loaded_exp["attributed_to"]) if loaded_exp["attributed_to"] in ATTRIBUTED_OPTIONS else 0, key=f"ee_attr_{loaded_exp_id}")
                with c7: e_edit_vendor = st.text_input("Vendor Name", value=str(loaded_exp.get("vendor_name") or ""), key=f"ee_vendor_{loaded_exp_id}")

                c8, c9, c10 = st.columns(3)
                with c8: e_edit_staff = st.selectbox("Linked Staff", staff_opts, index=staff_opts.index(curr_staff), key=f"ee_staff_{loaded_exp_id}")
                with c9: e_edit_po = st.selectbox("Linked PO", po_opts, index=default_po_idx, key=f"ee_po_{loaded_exp_id}")
                with c10: e_edit_stat = st.selectbox("Status", EXPENSE_STATUSES, index=EXPENSE_STATUSES.index(loaded_exp.get("status", "Pending")) if loaded_exp.get("status", "Pending") in EXPENSE_STATUSES else 0, key=f"ee_stat_{loaded_exp_id}")

                e_edit_desc = st.text_input("Description", value=str(loaded_exp.get("description") or ""), key=f"ee_desc_{loaded_exp_id}")
                e_edit_remarks = st.text_input("Remarks", value=str(loaded_exp.get("remarks") or ""), key=f"ee_rem_{loaded_exp_id}")

                if st.button("💾 Update Expense", type="primary", use_container_width=True):
                    if e_edit_amount <= 0: st.error("Amount must be greater than 0.")
                    else:
                        try:
                            p_po_id = int(e_edit_po.split("#")[1].split(" ")[0]) if "PO #" in e_edit_po else None
                            sel_staff = None if e_edit_staff == "Select Staff" else e_edit_staff
                            with db_conn.session as s:
                                s.execute(text("UPDATE expenses SET expense_date = :ed, expense_type = :et, category = :cat, sub_category = :subcat, description = :desc, total_amount = :amt, attributed_to = :attr, vendor_name = :vendor, staff_name = :staff, purchase_order_id = :poid, status = :stat, remarks = :rem, updated_at = NOW() WHERE id = :id;"), {"ed": e_edit_date, "et": e_edit_type, "cat": e_edit_cat, "subcat": e_edit_subcat.strip(), "desc": e_edit_desc.strip(), "amt": float(e_edit_amount), "attr": e_edit_attr, "vendor": e_edit_vendor.strip(), "staff": sel_staff, "poid": p_po_id, "stat": e_edit_stat, "rem": e_edit_remarks.strip(), "id": loaded_exp_id})
                                s.commit()
                            show_success_modal(f"Expense #{loaded_exp_id} updated successfully!")
                        except Exception as e: st.error(f"Could not update expense: {e}")

    elif exp_nav == "💳 Payments (Cash Outflows)":
        p_sub_mode = st.radio("Action", ["Record New Payment", "View Payments", "Edit Past Payment"], horizontal=True, key="p_sub_mode_rad")
        payments_df, expenses_summary_df = load_db_payments_df(), load_db_expenses_summary_df()

        if p_sub_mode == "Record New Payment":
            st.write("Record a disbursement / payment against an existing bill:")
            if expenses_summary_df.empty: st.info("No expenses found to make payment against.")
            else:
                unpaid_filter = st.checkbox("Show only expenses with pending balance", value=True, key="filter_unpaid_exp")
                filtered_exp = expenses_summary_df[expenses_summary_df["balance_due"] > 0] if unpaid_filter else expenses_summary_df
                if filtered_exp.empty: st.success("🎉 All logged expenses are fully settled!")
                else:
                    f_records = filtered_exp.to_dict("records")
                    f_labels = [f"Expense #{r['id']} — {r['category']} — {r['description'] or r['vendor_name']} (Total: ₹{float(r['total_amount']):,.0f} | Due: ₹{float(r['balance_due']):,.0f})" for r in f_records]
                    target_exp = f_records[f_labels.index(st.selectbox("Select Expense to Pay", f_labels, key="pay_target_select"))]; target_exp_id, curr_due = target_exp["id"], float(target_exp["balance_due"])

                    m1, m2, m3 = st.columns(3)
                    m1.metric("Bill Total", f"₹{float(target_exp['total_amount']):,.2f}"); m2.metric("Already Paid", f"₹{float(target_exp['total_paid']):,.2f}"); m3.metric("Outstanding Balance", f"₹{curr_due:,.2f}")

                    c1, c2, c3 = st.columns(3)
                    with c1: new_p_date = st.date_input("Payment Date", value=date.today(), key="rec_p_date")
                    with c2: new_p_amount = st.number_input("Amount to Pay (₹)", min_value=0.0, value=max(0.0, curr_due), step=10.0, key="rec_p_amt")
                    with c3: new_p_mode = st.selectbox("Payment Mode", PAYMENT_MODES, index=0, key="rec_p_mode")

                    c4, c5 = st.columns(2)
                    with c4: new_p_ref = st.text_input("Transaction / UTR Ref No.", placeholder="e.g. UPI Ref, IMPS Txn ID", key="rec_p_ref")
                    with c5: new_p_to = st.text_input("Paid To", value=str(target_exp.get("vendor_name") or ""), key="rec_p_to")
                    new_p_notes = st.text_input("Payment Notes / Remarks", placeholder="e.g. Part payment tranche 1...", key="rec_p_notes")

                    if st.button("💳 Disburse Payment", type="primary", use_container_width=True):
                        if new_p_amount <= 0: st.error("Please enter a payment amount greater than 0.")
                        else:
                            try:
                                with db_conn.session as s:
                                    s.execute(text("INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes) VALUES (:eid, :pdate, :pamt, :pmode, :pref, :pto, :pby, :notes);"), {"eid": target_exp_id, "pdate": new_p_date, "pamt": float(new_p_amount), "pmode": new_p_mode, "pref": new_p_ref.strip(), "pto": new_p_to.strip(), "pby": "Admin", "notes": new_p_notes.strip()})
                                    new_status = "Paid" if (float(target_exp["total_paid"]) + float(new_p_amount)) >= float(target_exp["total_amount"]) else "Partially Paid"
                                    s.execute(text("UPDATE expenses SET status = :stat, updated_at = NOW() WHERE id = :id;"), {"stat": new_status, "id": target_exp_id})
                                    s.commit()
                                show_success_modal(f"Payment of ₹{new_p_amount:,.2f} recorded successfully for Expense #{target_exp_id}!")
                            except Exception as e: st.error(f"Could not record payment: {e}")

        elif p_sub_mode == "View Payments":
            if payments_df.empty: st.info("No payment transactions found in database.")
            else:
                st.metric("Total Payments Disbursed", f"₹{float(payments_df['amount_paid'].sum()):,.2f}")
                disp_pay = payments_df.copy(); disp_pay["payment_date"] = pd.to_datetime(disp_pay["payment_date"]).dt.strftime("%d %b %Y"); disp_pay["Expense Link"] = disp_pay.apply(lambda r: f"#{r['expense_id']} — {r['category']} (₹{float(r['expense_total']):,.0f})", axis=1)
                st.dataframe(disp_pay[["id", "payment_date", "Expense Link", "amount_paid", "payment_mode", "ref_no", "paid_to", "paid_by", "notes"]].rename(columns={"id": "Payment ID", "payment_date": "Date", "amount_paid": "Amount (₹)", "payment_mode": "Mode", "ref_no": "Ref / UTR", "paid_to": "Paid To", "paid_by": "Paid By", "notes": "Notes"}), hide_index=True, use_container_width=True, column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%,.2f")})

        elif p_sub_mode == "Edit Past Payment":
            if payments_df.empty: st.info("No payments recorded to edit.")
            else:
                pay_records = payments_df.to_dict("records")
                pay_labels = [f"Payment #{r['id']} — {pd.to_datetime(r['payment_date']).strftime('%d %b %Y')} — For Expense #{r['expense_id']} ({r['category']}) (₹{float(r['amount_paid']):,.2f})" for r in pay_records]
                loaded_pay = pay_records[pay_labels.index(st.selectbox("Select Payment to Edit", pay_labels, key="edit_pay_select"))]; loaded_pay_id = loaded_pay["id"]

                c1, c2, c3 = st.columns(3)
                with c1: ep_date = st.date_input("Payment Date", value=pd.to_datetime(loaded_pay["payment_date"]).date(), key=f"ep_dt_{loaded_pay_id}")
                with c2: ep_amt = st.number_input("Amount Paid (₹)", min_value=0.0, value=float(loaded_pay["amount_paid"]), step=10.0, key=f"ep_amt_{loaded_pay_id}")
                with c3: ep_mode = st.selectbox("Payment Mode", PAYMENT_MODES, index=PAYMENT_MODES.index(loaded_pay["payment_mode"]) if loaded_pay["payment_mode"] in PAYMENT_MODES else 0, key=f"ep_mode_{loaded_pay_id}")

                c4, c5 = st.columns(2)
                with c4: ep_ref = st.text_input("Transaction / UTR Ref No.", value=str(loaded_pay.get("ref_no") or ""), key=f"ep_ref_{loaded_pay_id}")
                with c5: ep_to = st.text_input("Paid To", value=str(loaded_pay.get("paid_to") or ""), key=f"ep_to_{loaded_pay_id}")
                ep_notes = st.text_input("Payment Notes", value=str(loaded_pay.get("notes") or ""), key=f"ep_notes_{loaded_pay_id}")

                if st.button("💾 Update Payment", type="primary", use_container_width=True):
                    if ep_amt <= 0: st.error("Amount must be greater than 0.")
                    else:
                        try:
                            with db_conn.session as s:
                                s.execute(text("UPDATE expense_payments SET payment_date = :pdate, amount_paid = :pamt, payment_mode = :pmode, ref_no = :pref, paid_to = :pto, notes = :notes WHERE id = :id;"), {"pdate": ep_date, "pamt": float(ep_amt), "pmode": ep_mode, "pref": ep_ref.strip(), "pto": ep_to.strip(), "notes": ep_notes.strip(), "id": loaded_pay_id})
                                s.commit()
                            show_success_modal(f"Payment #{loaded_pay_id} updated successfully!")
                        except Exception as e: st.error(f"Could not update payment: {e}")

    elif exp_nav == "📊 Summary & Date Reports":
        st.write("Analyze expense obligations, actual disbursements, and settlement ratios over any time window:")
        expenses_summary_df, payments_df = load_db_expenses_summary_df(), load_db_payments_df()

        if expenses_summary_df.empty and payments_df.empty: st.info("No expense or payment records found in database.")
        else:
            all_dts = []
            if not expenses_summary_df.empty: all_dts += [pd.to_datetime(expenses_summary_df["expense_date"]).min().date(), pd.to_datetime(expenses_summary_df["expense_date"]).max().date()]
            if not payments_df.empty: all_dts += [pd.to_datetime(payments_df["payment_date"]).min().date(), pd.to_datetime(payments_df["payment_date"]).max().date()]
            min_exp_d, max_exp_d = min(all_dts), max(all_dts)

            rc1, rc2 = st.columns(2)
            with rc1: rpt_start = st.date_input("From Date", value=max(min_exp_d, max_exp_d - timedelta(days=29)), min_value=min_exp_d, max_value=max_exp_d, key="exp_rpt_start")
            with rc2: rpt_end = st.date_input("To Date", value=max_exp_d, min_value=min_exp_d, max_value=max_exp_d, key="exp_rpt_end")
            if rpt_start > rpt_end: st.error("'From' date must be before 'To' date."); rpt_start, rpt_end = rpt_end, rpt_start

            f_exp = expenses_summary_df[(pd.to_datetime(expenses_summary_df["expense_date"]).dt.date >= rpt_start) & (pd.to_datetime(expenses_summary_df["expense_date"]).dt.date <= rpt_end)] if not expenses_summary_df.empty else pd.DataFrame()
            f_pay = payments_df[(pd.to_datetime(payments_df["payment_date"]).dt.date >= rpt_start) & (pd.to_datetime(payments_df["payment_date"]).dt.date <= rpt_end)] if not payments_df.empty else pd.DataFrame()

            m1, m2, m3 = st.columns(3)
            m1.metric("Expenses Incurred (In Range)", f"₹{float(f_exp['total_amount'].sum()) if not f_exp.empty else 0.0:,.2f}")
            m2.metric("Actual Cash Paid Out", f"₹{float(f_pay['amount_paid'].sum()) if not f_pay.empty else 0.0:,.2f}")
            m3.metric("Outstanding Unpaid Dues", f"₹{float(f_exp['balance_due'].sum()) if not f_exp.empty else 0.0:,.2f}")

            st.markdown("---"); ch_col1, ch_col2 = st.columns(2)
            with ch_col1:
                st.markdown("#### Expenses by Category")
                if not f_exp.empty: st.altair_chart(alt.Chart(f_exp.groupby("category")["total_amount"].sum().reset_index()).mark_bar(color="#70440E").encode(x=alt.X("category:N", title="", sort="-y", axis=alt.Axis(labelAngle=-30)), y=alt.Y("total_amount:Q", title="Incurred (₹)"), tooltip=[alt.Tooltip("category", title="Category"), alt.Tooltip("total_amount:Q", title="Amount", format=",.2f")]).properties(height=260), use_container_width=True)
                else: st.caption("No expenses in this range.")
            with ch_col2:
                st.markdown("#### Expenses by Cart / Attribution")
                if not f_exp.empty: st.altair_chart(alt.Chart(f_exp.groupby("attributed_to")["total_amount"].sum().reset_index()).mark_bar(color="#E8542A").encode(x=alt.X("attributed_to:N", title="", sort="-y", axis=alt.Axis(labelAngle=-20)), y=alt.Y("total_amount:Q", title="Total (₹)"), tooltip=[alt.Tooltip("attributed_to", title="Entity"), alt.Tooltip("total_amount:Q", title="Amount", format=",.2f")]).properties(height=260), use_container_width=True)
                else: st.caption("No expenses in this range.")

            st.markdown("#### Payments Disbursed by Mode")
            if not f_pay.empty: st.dataframe(f_pay.groupby("payment_mode")["amount_paid"].sum().reset_index().rename(columns={"payment_mode": "Payment Mode", "amount_paid": "Amount Paid (₹)"}), hide_index=True, use_container_width=True, column_config={"Amount Paid (₹)": st.column_config.NumberColumn(format="₹%,.2f")})
            else: st.caption("No payments in this range.")

# ======================================================================
# PAGE 7: STAFF & PAYROLL (KYC, Leaves, Plans & Settlement)
# ======================================================================
elif page == "Staff & Payroll" and user_role == "admin":
    st.subheader("Staff & Payroll Management")
    st.caption("Manage staff profile & KYC records, leaves & attendance, versioned compensation plans, and live monthly dues settlements.")

    staff_tab_sel = st.radio(
        "Section", 
        ["👥 Staff Directory & KYC", "📅 Attendance & Leave", "⚙️ Compensation Plans", "💵 Monthly Dues & Settlement"], 
        horizontal=True, 
        key="staff_top_nav"
    )

    staff_df = load_full_staff_df()

    if staff_tab_sel == "👥 Staff Directory & KYC":
        st_mode = st.radio("Mode", ["View All Staff", "Add New Staff", "Edit Staff Profile & KYC"], horizontal=True, key="staff_dir_mode")

        if st_mode == "Add New Staff":
            st.write("Register a new staff member and configure their starting compensation package:")

            with st.form("new_staff_form"):
                sc1, sc2, sc3 = st.columns(3)
                with sc1:
                    new_s_name = st.text_input("Display Name (App) *", placeholder="e.g. Ramesh", key="add_s_name")
                with sc2:
                    new_s_fullname = st.text_input("Full Legal Name", placeholder="e.g. Ramesh Kumar", key="add_s_fname")
                with sc3:
                    new_s_phone = st.text_input("Mobile Number", placeholder="e.g. 9876543210", key="add_s_phone")

                sc4, sc5, sc6, sc_dol = st.columns(4)
                with sc4:
                    new_s_status = st.selectbox("Status", STAFF_STATUSES, index=0, key="add_s_status")
                with sc5:
                    new_s_doj = st.date_input("Date of Joining", value=date.today(), key="add_s_doj")
                with sc6:
                    new_s_dob = st.date_input("Date of Birth", value=date(1995, 1, 1), key="add_s_dob")
                with sc_dol:
                    new_s_dol = st.date_input("Date of Leaving", value=None, key="add_s_dol")

                sc7, sc8 = st.columns(2)
                with sc7:
                    new_s_pan = st.text_input("PAN Number", placeholder="e.g. ABCDE1234F", key="add_s_pan")
                with sc8:
                    new_s_aadhaar = st.text_input("Aadhaar Number", placeholder="12-digit Aadhaar", key="add_s_aadhaar")

                sc9, sc10 = st.columns(2)
                with sc9:
                    new_s_cur_addr = st.text_area("Current Residential Address", height=68, key="add_s_caddr")
                with sc10:
                    new_s_perm_addr = st.text_area("Permanent Address", height=68, key="add_s_paddr")

                sc11, sc12 = st.columns(2)
                with sc11:
                    new_s_emg_name = st.text_input("Emergency Contact Person", placeholder="e.g. Brother / Father", key="add_s_emgn")
                with sc12:
                    new_s_emg_phone = st.text_input("Emergency Contact Number", placeholder="e.g. 9123456789", key="add_s_emgp")

                st.markdown("#### Starting Compensation Package")
                cp1, cp2, cp3 = st.columns(3)
                with cp1:
                    new_s_salary = st.number_input("Monthly Fixed Salary (₹)", min_value=0.0, value=18000.0, step=500.0, key="add_s_sal")
                with cp2:
                    new_s_thresh = st.number_input("Daily Sales Threshold for Commission (₹)", min_value=0.0, value=3000.0, step=100.0, key="add_s_thresh")
                with cp3:
                    new_s_comm_pct = st.number_input("Commission Percentage (%)", min_value=0.0, max_value=100.0, value=15.0, step=0.5, key="add_s_comm")

                cp4, cp5 = st.columns(2)
                with cp4:
                    new_s_allow_wd = st.number_input("Food & Tea Allowance: Mon to Sat (₹/day)", min_value=0.0, value=210.0, step=10.0, key="add_s_awd")
                with cp5:
                    new_s_allow_sun = st.number_input("Food & Tea Allowance: Sunday (₹/day)", min_value=0.0, value=250.0, step=10.0, key="add_s_asun")

                new_s_notes = st.text_input("Notes / Background Remarks (Optional)", key="add_s_notes")

                submit_staff = st.form_submit_button("👤 Register Staff Member", type="primary", use_container_width=True)

            if submit_staff:
                if not new_s_name.strip():
                    st.error("Display Name is mandatory.")
                else:
                    try:
                        with db_conn.session as s:
                            res = s.execute(
                                text("""
                                INSERT INTO staff (
                                    name, full_name, status, phone_number, emergency_contact_name, emergency_contact_phone,
                                    date_of_birth, pan_number, aadhaar_number, current_address,
                                    permanent_address, date_of_joining, date_of_leaving, notes
                                ) VALUES (
                                    :name, :full_name, :status, :phone, :emg_n, :emg_p,
                                    :dob, :pan, :aadhaar, :caddr,
                                    :paddr, :doj, :dol, :notes
                                ) RETURNING id;
                                """),
                                {
                                    "name": new_s_name.strip(), "full_name": new_s_fullname.strip(), "status": new_s_status, 
                                    "phone": re.sub(r'[^\d+]', '', new_s_phone),
                                    "emg_n": new_s_emg_name.strip(), "emg_p": re.sub(r'[^\d+]', '', new_s_emg_phone),
                                    "dob": new_s_dob, "pan": new_s_pan.strip().upper(), "aadhaar": re.sub(r'\D', '', new_s_aadhaar),
                                    "caddr": new_s_cur_addr.strip(), "paddr": new_s_perm_addr.strip(), 
                                    "doj": new_s_doj, "dol": new_s_dol, "notes": new_s_notes.strip()
                                }
                            )
                            new_sid = res.scalar()

                            s.execute(
                                text("""
                                INSERT INTO staff_compensation_plans (
                                    staff_id, effective_from, monthly_fixed_salary,
                                    commission_threshold_daily, commission_percentage,
                                    allowance_weekday, allowance_sunday
                                ) VALUES (
                                    :sid, :efrom, :sal, :thresh, :comm, :awd, :asun
                                );
                                """),
                                {
                                    "sid": new_sid, "efrom": new_s_doj, "sal": float(new_s_salary),
                                    "thresh": float(new_s_thresh), "comm": float(new_s_comm_pct),
                                    "awd": float(new_s_allow_wd), "asun": float(new_s_allow_sun)
                                }
                            )
                            s.commit()
                        st.cache_data.clear()
                        show_success_modal(f"Staff member '{new_s_name}' registered successfully with ID #{new_sid}!")
                    except Exception as e:
                        st.error(f"Could not register staff: {e}")

        elif st_mode == "View All Staff":
            if staff_df.empty:
                st.info("No staff records found in database.")
            else:
                active_cnt = len(staff_df[staff_df["status"] == "active"])
                st.metric("Total Staff Registered", f"{len(staff_df)} ({active_cnt} Active)")

                disp_staff = staff_df.copy()
                disp_staff["Daily Fixed Rate"] = disp_staff["monthly_fixed_salary"].apply(lambda v: f"₹600/day (₹{_num(v):,.0f}/mo)")
                disp_staff["Commission"] = disp_staff.apply(lambda r: f"{_num(r['commission_percentage']):.0f}% > ₹{_num(r['commission_threshold_daily']):,.0f}", axis=1)
                disp_staff["Daily Food/Tea"] = disp_staff.apply(lambda r: f"₹{_num(r['allowance_weekday']):.0f} / ₹{_num(r['allowance_sunday']):.0f}", axis=1)
                disp_staff["Joined"] = pd.to_datetime(disp_staff["date_of_joining"]).dt.strftime("%d %b %Y")

                summary_cols = ["id", "name", "status", "phone_number", "Joined", "Daily Fixed Rate", "Commission", "Daily Food/Tea", "emergency_contact_phone"]
                st.dataframe(
                    disp_staff[summary_cols].rename(columns={
                        "id": "ID", "name": "Name", "status": "Status", "phone_number": "Phone",
                        "emergency_contact_phone": "Emergency Phone"
                    }),
                    hide_index=True,
                    use_container_width=True
                )

                st.markdown("---")
                st.markdown("#### Detailed KYC Inspection")
                sel_inspect = st.selectbox("Select staff member to inspect KYC profile", staff_df["name"].tolist(), key="inspect_staff_sel")
                s_row = staff_df[staff_df["name"] == sel_inspect].iloc[0]

                k1, k2, k3 = st.columns(3)
                k1.write(f"**Full Legal Name:** {s_row.get('full_name') or '—'}")
                k1.write(f"**Date of Birth:** {pd.to_datetime(s_row['date_of_birth']).strftime('%d %b %Y') if pd.notna(s_row['date_of_birth']) else '—'}")
                
                k2.write(f"**PAN Number:** {s_row['pan_number'] or '—'}")
                k2.write(f"**Aadhaar Number:** [Aadhaar Redacted]")
                
                k3.write(f"**Emergency Contact:** {s_row['emergency_contact_name'] or '—'} ({s_row['emergency_contact_phone'] or '—'})")
                k3.write(f"**Date of Leaving:** {pd.to_datetime(s_row['date_of_leaving']).strftime('%d %b %Y') if pd.notna(s_row['date_of_leaving']) else '—'}")

                st.write(f"**Current Address:** {s_row['current_address'] or '—'}")
                st.write(f"**Permanent Address:** {s_row['permanent_address'] or '—'}")
                if s_row.get("notes"):
                    st.caption(f"Remarks: {s_row['notes']}")

        elif st_mode == "Edit Staff Profile & KYC":
            if staff_df.empty:
                st.info("No staff records found to edit.")
            else:
                staff_names = staff_df["name"].tolist()
                sel_edit_name = st.selectbox("Select Staff to Edit", staff_names, key="edit_staff_picker")
                s_edit = staff_df[staff_df["name"] == sel_edit_name].iloc[0]
                s_id = int(s_edit["id"])

                with st.form("edit_staff_form"):
                    ec1, ec2, ec3 = st.columns(3)
                    with ec1:
                        e_name = st.text_input("Display Name (App) *", value=str(s_edit["name"]), key=f"e_name_{s_id}")
                    with ec2:
                        e_fullname = st.text_input("Full Legal Name", value=str(s_edit.get("full_name") or ""), key=f"e_fname_{s_id}")
                    with ec3:
                        e_phone = st.text_input("Mobile Number", value=str(s_edit.get("phone_number") or ""), key=f"e_phone_{s_id}")

                    ec4, ec5, ec6, ec_dol = st.columns(4)
                    with ec4:
                        stat_idx = STAFF_STATUSES.index(s_edit["status"]) if s_edit["status"] in STAFF_STATUSES else 0
                        e_status = st.selectbox("Status", STAFF_STATUSES, index=stat_idx, key=f"e_status_{s_id}")
                    with ec5:
                        doj_val = pd.to_datetime(s_edit["date_of_joining"]).date() if pd.notna(s_edit["date_of_joining"]) else date.today()
                        e_doj = st.date_input("Date of Joining", value=doj_val, key=f"e_doj_{s_id}")
                    with ec6:
                        dob_val = pd.to_datetime(s_edit["date_of_birth"]).date() if pd.notna(s_edit["date_of_birth"]) else date(1995, 1, 1)
                        e_dob = st.date_input("Date of Birth", value=dob_val, key=f"e_dob_{s_id}")
                    with ec_dol:
                        dol_val = pd.to_datetime(s_edit["date_of_leaving"]).date() if pd.notna(s_edit["date_of_leaving"]) else None
                        e_dol = st.date_input("Date of Leaving", value=dol_val, key=f"e_dol_{s_id}")

                    ec7, ec8 = st.columns(2)
                    with ec7:
                        e_pan = st.text_input("PAN Number", value=str(s_edit.get("pan_number") or ""), key=f"e_pan_{s_id}")
                    with ec8:
                        e_aadhaar = st.text_input("Aadhaar Number", value="", placeholder="[Aadhaar Redacted]", key=f"e_aadhaar_{s_id}")

                    ec9, ec10 = st.columns(2)
                    with ec9:
                        e_caddr = st.text_area("Current Address", value=str(s_edit.get("current_address") or ""), height=68, key=f"e_caddr_{s_id}")
                    with ec10:
                        e_paddr = st.text_area("Permanent Address", value=str(s_edit.get("permanent_address") or ""), height=68, key=f"e_paddr_{s_id}")

                    ec11, ec12 = st.columns(2)
                    with ec11:
                        e_emg_n = st.text_input("Emergency Contact Name", value=str(s_edit.get("emergency_contact_name") or ""), key=f"e_emgn_{s_id}")
                    with ec12:
                        e_emg_p = st.text_input("Emergency Contact Phone", value=str(s_edit.get("emergency_contact_phone") or ""), key=f"e_emgp_{s_id}")

                    e_notes = st.text_input("Notes", value=str(s_edit.get("notes") or ""), key=f"e_notes_{s_id}")

                    save_edit_staff = st.form_submit_button("💾 Save Profile Changes", type="primary", use_container_width=True)

                if save_edit_staff:
                    if not e_name.strip():
                        st.error("Display Name cannot be blank.")
                    else:
                        try:
                            with db_conn.session as s:
                                update_params = {
                                    "name": e_name.strip(), "full_name": e_fullname.strip(), "status": e_status, 
                                    "phone": re.sub(r'[^\d+]', '', e_phone),
                                    "emg_n": e_emg_n.strip(), "emg_p": re.sub(r'[^\d+]', '', e_emg_p), 
                                    "dob": e_dob, "pan": e_pan.strip().upper(),
                                    "caddr": e_caddr.strip(), "paddr": e_paddr.strip(), "doj": e_doj, "dol": e_dol,
                                    "notes": e_notes.strip(), "id": s_id
                                }
                                aadhaar_update_sql = ""
                                if e_aadhaar.strip() and e_aadhaar.strip() != "[Aadhaar Redacted]":
                                    update_params["aadhaar"] = re.sub(r'\D', '', e_aadhaar)
                                    aadhaar_update_sql = ", aadhaar_number = :aadhaar"

                                s.execute(
                                    text(f"""
                                    UPDATE staff
                                    SET name = :name, full_name = :full_name, status = :status, phone_number = :phone,
                                        emergency_contact_name = :emg_n, emergency_contact_phone = :emg_p,
                                        date_of_birth = :dob, pan_number = :pan,
                                        current_address = :caddr, permanent_address = :paddr,
                                        date_of_joining = :doj, date_of_leaving = :dol, notes = :notes, updated_at = NOW()
                                        {aadhaar_update_sql}
                                    WHERE id = :id;
                                    """),
                                    update_params
                                )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"Staff profile for '{e_name}' updated successfully!")
                        except Exception as e:
                            st.error(f"Could not update staff profile: {e}")

    elif staff_tab_sel == "📅 Attendance & Leave":
        st.write("Record and manage staff leaves and absences for payroll deductions and day-wise attendance:")

        att_mode = st.radio("Action", ["Record Staff Leave / Absence", "View Attendance & Leaves", "Edit Past Leave Entry"], horizontal=True, key="att_sub_nav")

        if att_mode == "Record Staff Leave / Absence":
            if staff_df.empty:
                st.info("No staff registered yet.")
            else:
                st_names = staff_df["name"].tolist()
                with st.form("add_leave_form"):
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        att_staff_name = st.selectbox("Staff Member *", st_names, key="leave_sname")
                    with ac2:
                        att_date = st.date_input("Leave Date *", value=date.today(), key="leave_dt")

                    ac3, ac4 = st.columns(2)
                    with ac3:
                        att_status = st.selectbox("Status", LEAVE_STATUS_OPTIONS, index=0, key="leave_stat")
                    with ac4:
                        att_type = st.selectbox("Leave Type", LEAVE_TYPE_OPTIONS, index=0, key="leave_type")

                    att_reason = st.text_input("Reason / Observation", placeholder="e.g. Family function, unwell, uninformed absence...", key="leave_reason")

                    submit_leave = st.form_submit_button("📝 Record Leave Entry", type="primary", use_container_width=True)

                if submit_leave:
                    try:
                        target_s_id = int(staff_df[staff_df["name"] == att_staff_name].iloc[0]["id"])
                        with db_conn.session as s:
                            s.execute(
                                text("""
                                INSERT INTO staff_attendance (
                                    staff_id, attendance_date, status, leave_type, reason, recorded_by
                                ) VALUES (
                                    :sid, :adate, :stat, :ltype, :reason, :recby
                                )
                                ON CONFLICT (staff_id, attendance_date) DO UPDATE
                                SET status = EXCLUDED.status, leave_type = EXCLUDED.leave_type,
                                    reason = EXCLUDED.reason, updated_at = NOW();
                                """),
                                {
                                    "sid": target_s_id, "adate": att_date, "stat": att_status,
                                    "ltype": att_type, "reason": att_reason.strip(), "recby": "Admin"
                                }
                            )
                            s.commit()
                        show_success_modal(f"{att_status} ({att_type}) recorded for {att_staff_name} on {att_date.strftime('%d %b %Y')}!")
                    except Exception as e:
                        st.error(f"Could not record attendance: {e}")

        elif att_mode == "View Attendance & Leaves":
            att_df = load_staff_attendance_df()
            if att_df.empty:
                st.info("No leave records logged.")
            else:
                k1, k2, k3 = st.columns(3)
                k1.metric("Total Leave Logs", len(att_df))
                k2.metric("Unpaid Leaves", len(att_df[att_df["leave_type"] == "Unpaid"]))
                k3.metric("Paid Leaves", len(att_df[att_df["leave_type"] == "Paid"]))

                disp_att = att_df.copy()
                disp_att["attendance_date"] = pd.to_datetime(disp_att["attendance_date"]).dt.strftime("%d %b %Y")
                
                st.dataframe(
                    disp_att[["id", "staff_name", "attendance_date", "status", "leave_type", "reason", "recorded_by"]].rename(columns={
                        "id": "ID", "staff_name": "Staff Name", "attendance_date": "Date", "status": "Status",
                        "leave_type": "Leave Type", "reason": "Reason", "recorded_by": "Recorded By"
                    }),
                    hide_index=True,
                    use_container_width=True
                )

        elif att_mode == "Edit Past Leave Entry":
            att_df = load_staff_attendance_df()
            if att_df.empty:
                st.info("No attendance records to edit.")
            else:
                att_records = att_df.to_dict("records")
                att_labels = [
                    f"#{r['id']} — {r['staff_name']} on {pd.to_datetime(r['attendance_date']).strftime('%d %b %Y')} ({r['status']} - {r['leave_type']})"
                    for r in att_records
                ]
                sel_att_label = st.selectbox("Select Leave Entry to Edit", att_labels, key="edit_att_select")
                loaded_att = att_records[att_labels.index(sel_att_label)]
                loaded_att_id = loaded_att["id"]

                c1, c2 = st.columns(2)
                with c1:
                    e_att_date = st.date_input("Leave Date", value=pd.to_datetime(loaded_att["attendance_date"]).date(), key=f"e_att_dt_{loaded_att_id}")
                with c2:
                    e_att_stat = st.selectbox("Status", LEAVE_STATUS_OPTIONS, index=LEAVE_STATUS_OPTIONS.index(loaded_att["status"]) if loaded_att["status"] in LEAVE_STATUS_OPTIONS else 0, key=f"e_att_st_{loaded_att_id}")

                c3, c4 = st.columns(2)
                with c3:
                    e_att_type = st.selectbox("Leave Type", LEAVE_TYPE_OPTIONS, index=LEAVE_TYPE_OPTIONS.index(loaded_att["leave_type"]) if loaded_att["leave_type"] in LEAVE_TYPE_OPTIONS else 0, key=f"e_att_tp_{loaded_att_id}")
                with c4:
                    e_att_reason = st.text_input("Reason", value=str(loaded_att.get("reason") or ""), key=f"e_att_rs_{loaded_att_id}")

                if st.button("💾 Update Leave Entry", type="primary", use_container_width=True):
                    try:
                        with db_conn.session as s:
                            s.execute(
                                text("""
                                UPDATE staff_attendance
                                SET attendance_date = :adate, status = :stat, leave_type = :ltype,
                                    reason = :reason, updated_at = NOW()
                                WHERE id = :id;
                                """),
                                {
                                    "adate": e_att_date, "stat": e_att_stat, "ltype": e_att_type,
                                    "reason": e_att_reason.strip(), "id": loaded_att_id
                                }
                            )
                            s.commit()
                        show_success_modal(f"Attendance record #{loaded_att_id} updated successfully!")
                    except Exception as e:
                        st.error(f"Could not update attendance: {e}")

    elif staff_tab_sel == "⚙️ Compensation Plans":
        st.write("View and assign effective-dated salary, commission slabs, and food/tea allowances:")

        if staff_df.empty:
            st.info("No staff records found in database.")
        else:
            sel_s_plan = st.selectbox("Select Staff Member", staff_df["name"].tolist(), key="staff_comp_sel")
            target_s_row = staff_df[staff_df["name"] == sel_s_plan].iloc[0]
            target_s_id = int(target_s_row["id"])

            st.markdown(f"#### Active Plan for {sel_s_plan}")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Daily Base Rate", "₹600.00/day", "Apportioned per day worked")
            m2.metric("Commission Threshold", f"₹{_num(target_s_row['commission_threshold_daily']):,.2f}/day")
            m3.metric("Commission Rate", f"{_num(target_s_row['commission_percentage']):.1f}%")
            m4.metric("Daily Allowances", f"₹{_num(target_s_row['allowance_weekday']):.0f} (W) | ₹{_num(target_s_row['allowance_sunday']):.0f} (S)")

            st.markdown("---")
            st.markdown("#### Revision / Add New Compensation Plan")
            st.caption("Adding a new plan sets an effective starting date without altering past calculation history.")

            with st.form("new_comp_plan_form"):
                cp1, cp2 = st.columns(2)
                with cp1:
                    plan_eff_from = st.date_input("Effective From Date", value=date.today())
                with cp2:
                    plan_salary = st.number_input("Monthly Fixed Salary (₹)", min_value=0.0, value=float(_num(target_s_row['monthly_fixed_salary']) or 18000.0), step=500.0)

                cp3, cp4 = st.columns(2)
                with cp3:
                    plan_threshold = st.number_input("Daily Sales Threshold (₹)", min_value=0.0, value=float(_num(target_s_row['commission_threshold_daily']) or 3000.0), step=100.0)
                with cp4:
                    plan_comm_pct = st.number_input("Commission Rate (%)", min_value=0.0, max_value=100.0, value=float(_num(target_s_row['commission_percentage']) or 15.0), step=0.5)

                cp5, cp6 = st.columns(2)
                with cp5:
                    plan_allow_wd = st.number_input("Food/Tea Allowance: Mon to Sat (₹/day)", min_value=0.0, value=float(_num(target_s_row['allowance_weekday']) or 210.0), step=10.0)
                with cp6:
                    plan_allow_sun = st.number_input("Food & Tea Allowance: Sunday (₹/day)", min_value=0.0, value=float(_num(target_s_row['allowance_sunday']) or 250.0), step=10.0)

                submit_plan = st.form_submit_button("💾 Save & Activate Compensation Plan", type="primary", use_container_width=True)

            if submit_plan:
                try:
                    with db_conn.session as s:
                        s.execute(
                            text("""
                            UPDATE staff_compensation_plans
                            SET effective_to = :prev_end
                            WHERE staff_id = :sid AND effective_to IS NULL AND effective_from < :new_start;
                            """),
                            {"prev_end": plan_eff_from - timedelta(days=1), "sid": target_s_id, "new_start": plan_eff_from}
                        )
                        s.execute(
                            text("""
                            INSERT INTO staff_compensation_plans (
                                staff_id, effective_from, monthly_fixed_salary,
                                commission_threshold_daily, commission_percentage,
                                allowance_weekday, allowance_sunday
                            ) VALUES (
                                :sid, :efrom, :sal, :thresh, :comm, :awd, :asun
                            );
                            """),
                            {
                                "sid": target_s_id, "efrom": plan_eff_from, "sal": float(plan_salary),
                                "thresh": float(plan_threshold), "comm": float(plan_comm_pct),
                                "awd": float(plan_allow_wd), "asun": float(plan_allow_sun)
                            }
                        )
                        s.commit()
                    show_success_modal(f"New compensation plan activated for {sel_s_plan} from {plan_eff_from.strftime('%d %b %Y')}!")
                except Exception as e:
                    st.error(f"Could not save compensation plan: {e}")

            st.markdown("---")
            st.markdown("#### Historical Plans")
            hist_df = load_staff_compensation_history(target_s_id)
            if not hist_df.empty:
                disp_hist = hist_df.copy()
                disp_hist["effective_from"] = pd.to_datetime(disp_hist["effective_from"]).dt.strftime("%d %b %Y")
                disp_hist["effective_to"] = disp_hist["effective_to"].apply(lambda d: pd.to_datetime(d).strftime("%d %b %Y") if pd.notna(d) else "Active Present")
                st.dataframe(
                    disp_hist[["effective_from", "effective_to", "monthly_fixed_salary", "commission_threshold_daily", "commission_percentage", "allowance_weekday", "allowance_sunday"]].rename(columns={
                        "effective_from": "From", "effective_to": "To", "monthly_fixed_salary": "Fixed Salary (₹)",
                        "commission_threshold_daily": "Threshold (₹)", "commission_percentage": "Commission (%)",
                        "allowance_weekday": "Weekday Allw. (₹)", "allowance_sunday": "Sunday Allw. (₹)"
                    }),
                    hide_index=True,
                    use_container_width=True
                )

    elif staff_tab_sel == "💵 Monthly Dues & Settlement":
        st.write("Calculate monthly dues with fixed salary apportioned at **Rs 600/day worked**, commissions (15% > Rs 3,000), daily food/tea allowances, and deductions backed by the Payments table:")

        now = date.today()
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            month_names = list(calendar.month_name)[1:]
            sel_month_name = st.selectbox("Select Settlement Month", month_names, index=now.month - 1, key="pay_calc_month")
            sel_month_idx = month_names.index(sel_month_name) + 1
        with m_col2:
            sel_year = st.number_input("Select Year", min_value=2024, max_value=2030, value=now.year, step=1, key="pay_calc_year")

        num_days_in_month = calendar.monthrange(sel_year, sel_month_idx)[1]
        m_start_dt = date(sel_year, sel_month_idx, 1)
        m_end_dt = date(sel_year, sel_month_idx, num_days_in_month)

        st.caption(f"Calculating for period: **{m_start_dt.strftime('%d %b %Y')}** to **{m_end_dt.strftime('%d %b %Y')}** ({num_days_in_month} Days in Month)")

        daily_month_df = pd.DataFrame()
        att_month_df = pd.DataFrame()
        staff_payments_df = pd.DataFrame()
        exp_ledger_df = pd.DataFrame()

        if db_conn is not None:
            query_month = """
            SELECT entry_date, cart_name, staff_name, total_collection
            FROM daily_cart_entries
            WHERE entry_date >= :sdate AND entry_date <= :edate AND staff_name IS NOT NULL AND staff_name != '' AND staff_name != 'Select Staff';
            """
            daily_month_df = db_conn.query(query_month, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="0s")

            query_att_m = """
            SELECT a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type, a.reason
            FROM staff_attendance a
            JOIN staff s ON a.staff_id = s.id
            WHERE a.attendance_date >= :sdate AND a.attendance_date <= :edate;
            """
            att_month_df = db_conn.query(query_att_m, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="0s")

            query_labour_payments = """
            SELECT 
                p.id AS payment_id, p.expense_id, p.payment_date, p.amount_paid, p.payment_mode, p.ref_no, p.paid_to, p.notes,
                e.category, e.sub_category, e.description, e.staff_name, e.attributed_to
            FROM expense_payments p
            JOIN expenses e ON p.expense_id = e.id
            WHERE e.category = 'Labour Charges' AND e.staff_name IS NOT NULL AND e.staff_name != '' AND p.payment_date >= :sdate AND p.payment_date <= :edate;
            """
            staff_payments_df = db_conn.query(query_labour_payments, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="0s")

            query_exp_ledger = """
            SELECT expense_date, staff_name, sub_category, total_amount 
            FROM expenses 
            WHERE category = 'Labour Charges' AND status = 'Paid' AND expense_date >= :sdate AND expense_date <= :edate;
            """
            exp_ledger_df = db_conn.query(query_exp_ledger, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="0s")

        if staff_df.empty:
            st.info("No staff records found.")
        else:
            settlement_summary_rows = []
            detailed_staff_logs = {}
            detailed_staff_payments = {}

            for _, s_row in staff_df.iterrows():
                st_name = str(s_row["name"]).strip()
                monthly_sal = float(_num(s_row.get("monthly_fixed_salary")) or 18000.0)
                daily_rate = monthly_sal / 30.0
                comm_thresh = float(_num(s_row.get("commission_threshold_daily")) or 3000.0)
                comm_pct = float(_num(s_row.get("commission_percentage")) or 15.0)
                allow_wd = float(_num(s_row.get("allowance_weekday")) or 210.0)
                allow_sun = float(_num(s_row.get("allowance_sunday")) or 250.0)

                st_shifts = daily_month_df[daily_month_df["staff_name"] == st_name].copy() if not daily_month_df.empty else pd.DataFrame()
                st_leaves = att_month_df[att_month_df["staff_name"] == st_name].copy() if not att_month_df.empty else pd.DataFrame()
                st_payments = staff_payments_df[staff_payments_df["staff_name"] == st_name].copy() if not staff_payments_df.empty else pd.DataFrame()
                st_exp = exp_ledger_df[exp_ledger_df["staff_name"] == st_name] if not exp_ledger_df.empty else pd.DataFrame()

                exp_map = {}
                if not st_exp.empty:
                    for _, e_row in st_exp.iterrows():
                        e_dt = pd.to_datetime(e_row["expense_date"]).date()
                        if e_dt not in exp_map: exp_map[e_dt] = {"advance": 0.0, "food": 0.0}
                        subcat = str(e_row.get("sub_category") or "").strip().lower()
                        amt = float(_num(e_row["total_amount"]))
                        if 'food' in subcat or 'tea' in subcat or 'allow' in subcat:
                            exp_map[e_dt]["food"] += amt
                        elif 'advance' in subcat:
                            exp_map[e_dt]["advance"] += amt

                total_sales_done = 0.0
                total_comm_earned = 0.0
                total_allow_entitled = 0.0
                weekdays_worked = 0
                sundays_worked = 0
                staff_shift_records = []

                if not st_shifts.empty:
                    st_shifts["entry_date"] = pd.to_datetime(st_shifts["entry_date"])
                    st_shifts = st_shifts.sort_values(by="entry_date")

                    for _, shift in st_shifts.iterrows():
                        s_dt = shift["entry_date"].date()
                        is_sun = (s_dt.weekday() == 6)
                        if is_sun:
                            sundays_worked += 1
                            day_allow = allow_sun
                        else:
                            weekdays_worked += 1
                            day_allow = allow_wd

                        s_col = float(_num(shift["total_collection"]))
                        day_comm = max(0.0, s_col - comm_thresh) * (comm_pct / 100.0)

                        total_sales_done += s_col
                        total_comm_earned += day_comm
                        total_allow_entitled += day_allow
                        
                        day_adv = exp_map.get(s_dt, {}).get("advance", 0.0)
                        day_food = exp_map.get(s_dt, {}).get("food", 0.0)
                        if s_dt in exp_map: del exp_map[s_dt]

                        staff_shift_records.append({
                            "Date": s_dt.strftime("%d %b %Y"),
                            "Day": s_dt.strftime("%A"),
                            "Staff Name": st_name,
                            "Cart Operated": shift["cart_name"],
                            "Shift Status": "Worked",
                            "Daily Sales (₹)": s_col,
                            "Salary Apportioned (₹)": daily_rate,
                            "Commission (₹)": day_comm,
                            "Allowance Entitled (₹)": day_allow,
                            "Advance Taken (₹)": day_adv,
                            "Allow. Taken (₹)": day_food,
                            "Total Entitled (₹)": daily_rate + day_comm + day_allow
                        })

                paid_leave_cnt = 0
                unpaid_leave_cnt = 0
                if not st_leaves.empty:
                    st_leaves["attendance_date"] = pd.to_datetime(st_leaves["attendance_date"])
                    for _, l_row in st_leaves.iterrows():
                        l_dt = l_row["attendance_date"].date()
                        l_type = str(l_row.get("leave_type", "Unpaid"))
                        if l_type == "Paid":
                            paid_leave_cnt += 1
                            day_sal = daily_rate
                        else:
                            unpaid_leave_cnt += 1
                            day_sal = 0.0
                            
                        day_adv = exp_map.get(l_dt, {}).get("advance", 0.0)
                        day_food = exp_map.get(l_dt, {}).get("food", 0.0)
                        if l_dt in exp_map: del exp_map[l_dt]

                        staff_shift_records.append({
                            "Date": l_dt.strftime("%d %b %Y"),
                            "Day": l_dt.strftime("%A"),
                            "Staff Name": st_name,
                            "Cart Operated": "— (On Leave)",
                            "Shift Status": f"{l_row['status']} ({l_type})",
                            "Daily Sales (₹)": 0.0,
                            "Salary Apportioned (₹)": day_sal,
                            "Commission (₹)": 0.0,
                            "Allowance Entitled (₹)": 0.0,
                            "Advance Taken (₹)": day_adv,
                            "Allow. Taken (₹)": day_food,
                            "Total Entitled (₹)": day_sal
                        })
                        
                for d, vals in exp_map.items():
                    staff_shift_records.append({
                        "Date": d.strftime("%d %b %Y"),
                        "Day": d.strftime("%A"),
                        "Staff Name": st_name,
                        "Cart Operated": "— (Expense)",
                        "Shift Status": "Manual Entry",
                        "Daily Sales (₹)": 0.0,
                        "Salary Apportioned (₹)": 0.0,
                        "Commission (₹)": 0.0,
                        "Allowance Entitled (₹)": 0.0,
                        "Advance Taken (₹)": vals["advance"],
                        "Allow. Taken (₹)": vals["food"],
                        "Total Entitled (₹)": 0.0
                    })

                total_payments_disbursed = float(st_payments["amount_paid"].sum()) if not st_payments.empty else 0.0
                days_worked = weekdays_worked + sundays_worked
                apportioned_base_salary = (days_worked + paid_leave_cnt) * daily_rate
                gross_earnings = apportioned_base_salary + total_comm_earned + total_allow_entitled
                net_payable_due = gross_earnings - total_payments_disbursed

                settlement_summary_rows.append({
                    "Staff Name": st_name,
                    "Status": s_row["status"],
                    "Days Worked": f"{days_worked} ({weekdays_worked}W / {sundays_worked}S)",
                    "Leaves Logged": f"{len(st_leaves)} ({paid_leave_cnt}P / {unpaid_leave_cnt}U)",
                    "Apportioned Salary (₹)": apportioned_base_salary,
                    "Daily Rate Used (₹)": f"₹{daily_rate:.0f}/day",
                    "Total Sales (₹)": total_sales_done,
                    "Commission Earned (₹)": total_comm_earned,
                    "Allowances Entitled (₹)": total_allow_entitled,
                    "Gross Payable (₹)": gross_earnings,
                    "Total Paid / Deductions (₹)": total_payments_disbursed,
                    "Net Amount Due (₹)": net_payable_due
                })

                if staff_shift_records:
                    s_ledger_df = pd.DataFrame(staff_shift_records)
                    s_ledger_df["dt_sort"] = pd.to_datetime(s_ledger_df["Date"], format="%d %b %Y")
                    detailed_staff_logs[st_name] = s_ledger_df.sort_values(by="dt_sort").drop(columns=["dt_sort"])
                else:
                    detailed_staff_logs[st_name] = pd.DataFrame()

                detailed_staff_payments[st_name] = st_payments

            settlement_df = pd.DataFrame(settlement_summary_rows)

            tot_gross = float(settlement_df["Gross Payable (₹)"].sum())
            tot_ded = float(settlement_df["Total Paid / Deductions (₹)"].sum())
            tot_net = float(settlement_df["Net Amount Due (₹)"].sum())
            tot_comm = float(settlement_df["Commission Earned (₹)"].sum())

            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Total Gross Entitled", f"₹{tot_gross:,.2f}")
            kpi2.metric("Total Commissions", f"₹{tot_comm:,.2f}")
            kpi3.metric("Total Payments Disbursed", f"-₹{tot_ded:,.2f}", "From Payments Table")
            kpi4.metric("Net Total Payable", f"₹{tot_net:,.2f}")

            st.markdown("---")
            st.markdown("#### Staff Settlement Summary Table")
            st.dataframe(
                settlement_df,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Apportioned Salary (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                    "Total Sales (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                    "Commission Earned (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                    "Allowances Entitled (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                    "Gross Payable (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                    "Total Paid / Deductions (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                    "Net Amount Due (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                }
            )

            st.markdown("---")
            sel_staff_drill = st.selectbox("Select Staff Member for Detailed Inspection", staff_df["name"].tolist(), key="drill_staff_sel")
            target_staff_log = detailed_staff_logs.get(sel_staff_drill, pd.DataFrame())
            target_staff_pay = detailed_staff_payments.get(sel_staff_drill, pd.DataFrame())

            tab_drill1, tab_drill2 = st.tabs(["📋 Day-Wise Shifts & Attendance", "💳 Labour Payments & Deductions Disbursed"])

            with tab_drill1:
                st.write(f"Itemized daily shifts and attendance records for **{sel_staff_drill}**:")
                if target_staff_log.empty:
                    st.info(f"No shifts or leave records logged for {sel_staff_drill} in {sel_month_name} {sel_year}.")
                else:
                    st.dataframe(
                        target_staff_log,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Daily Sales (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                            "Salary Apportioned (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                            "Commission (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                            "Allowance Entitled (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                            "Advance Taken (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                            "Allow. Taken (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                            "Total Entitled (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                        }
                    )

            with tab_drill2:
                st.write(f"Actual disbursements and deductions recorded in `expense_payments` for **{sel_staff_drill}**:")
                if target_staff_pay.empty:
                    st.info(f"No disbursements / payments recorded for {sel_staff_drill} in {sel_month_name} {sel_year}.")
                else:
                    disp_sp = target_staff_pay.copy()
                    disp_sp["payment_date"] = pd.to_datetime(disp_sp["payment_date"]).dt.strftime("%d %b %Y")
                    st.dataframe(
                        disp_sp[["payment_id", "payment_date", "sub_category", "description", "amount_paid", "payment_mode", "ref_no", "notes"]].rename(columns={
                            "payment_id": "Payment ID", "payment_date": "Date", "sub_category": "Type",
                            "description": "Description", "amount_paid": "Amount Paid (₹)", "payment_mode": "Mode",
                            "ref_no": "Ref / UTR", "notes": "Notes"
                        }),
                        hide_index=True,
                        use_container_width=True,
                        column_config={"Amount Paid (₹)": st.column_config.NumberColumn(format="₹%,.2f")}
                    )

# ======================================================================
# PAGE 8: DASHBOARD (100% Supabase PostgreSQL Powered)
# ======================================================================
elif page == "Dashboard" and user_role == "admin":
    st.subheader("Quick view")
    try:
        daily_df = load_db_daily_df()
        exp_list = load_db_expenses_list()
        exp_df = pd.DataFrame(exp_list)
    except Exception as e:
        daily_df, exp_df = pd.DataFrame(), pd.DataFrame()
        st.warning(f"Could not load data from database ({e}).")

    today = pd.Timestamp(date.today())
    day_labels = [today - pd.Timedelta(days=3), today - pd.Timedelta(days=2), today - pd.Timedelta(days=1)]
    if not daily_df.empty:
        day_rows = [daily_df[daily_df["Date"].dt.date == d.date()] for d in day_labels]
        day_rev = [r["Total_Collection"].sum() for r in day_rows]
        day_units = [int(round(r["Sold_Total"].sum())) for r in day_rows]
        col_names = [d.strftime("%d %b") for d in day_labels]
        col_names[-1] = col_names[-1] + " (Yesterday)"
        compare_df = pd.DataFrame({
            "Metric": ["Revenue", "Units sold"], col_names[0]: [f"₹{day_rev[0]:,.0f}", f"{day_units[0]}"],
            col_names[1]: [f"₹{day_rev[1]:,.0f}", f"{day_units[1]}"], col_names[2]: [f"₹{day_rev[2]:,.0f}", f"{day_units[2]}"],
        })
        st.markdown('<div id="last-3-days"></div>', unsafe_allow_html=True)
        st.markdown("**Last 3 days**")
        st.dataframe(compare_df, hide_index=True, use_container_width=True)

        st.markdown('<div id="revenue-trend"></div>', unsafe_allow_html=True)
        st.markdown("**Revenue, last 14 days**")
        
        # Stacked bar graph for PhonePe vs Gross Cash
        trend_agg = daily_df.assign(Day=daily_df["Date"].dt.normalize()).groupby("Day", as_index=False).agg({
            "PhonePe": "sum", 
            "Total_Collection": "sum"
        }).sort_values("Day").tail(14)
        
        trend_agg["Gross Cash"] = trend_agg["Total_Collection"] - trend_agg["PhonePe"]
        trend_melt = trend_agg.melt(id_vars=["Day"], value_vars=["PhonePe", "Gross Cash"], var_name="Mode", value_name="Amount")
        
        trend_chart = alt.Chart(trend_melt).mark_bar(width=16).encode(
            x=alt.X("Day:T", title="", axis=alt.Axis(format="%d %b", labelAngle=-45)),
            y=alt.Y("Amount:Q", title="Revenue (₹)"),
            color=alt.Color("Mode:N", scale=alt.Scale(range=["#8A5E17", "#E8542A"])),
            tooltip=[
                alt.Tooltip("Day:T", title="Date", format="%d %b %Y"), 
                "Mode", 
                alt.Tooltip("Amount:Q", title="Amount", format=",.0f")
            ]
        ).properties(height=200)
        
        st.altair_chart(trend_chart, use_container_width=True)
    else: 
        st.info("No sales logged in database yet.")

    if not daily_df.empty or not exp_df.empty:
        st.markdown("---")
        st.markdown('<div id="reports"></div>', unsafe_allow_html=True)
        st.markdown("## Reports & Performance Analytics")
        today_cur = date.today()
        month_start_cur = today_cur.replace(day=1)
        default_end_cur = today_cur - timedelta(days=1)
        if default_end_cur < month_start_cur:
            default_end_cur = month_start_cur

        all_dates = [today_cur, month_start_cur]
        if not daily_df.empty: all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()]
        if not exp_df.empty and exp_df["Date"].notna().any(): all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()]
        min_d, max_d = min(all_dates), max(today_cur, max(all_dates))

        if "applied_start" not in st.session_state: st.session_state["applied_start"] = month_start_cur
        if "applied_end" not in st.session_state: st.session_state["applied_end"] = default_end_cur
        st.session_state["applied_start"] = min(max(st.session_state["applied_start"], min_d), max_d)
        st.session_state["applied_end"] = min(max(st.session_state["applied_end"], min_d), max_d)

        with st.form("date_range_form"):
            rc1, rc2, rc3 = st.columns([2, 2, 1])
            with rc1: pending_start = st.date_input("From", value=st.session_state["applied_start"], min_value=min_d, max_value=max_d)
            with rc2: pending_end = st.date_input("To", value=st.session_state["applied_end"], min_value=min_d, max_value=max_d)
            with rc3: 
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                apply_clicked = st.form_submit_button("Apply", type="primary", use_container_width=True)

        if apply_clicked: 
            st.session_state["applied_start"] = pending_start
            st.session_state["applied_end"] = pending_end
        range_start, range_end = st.session_state["applied_start"], st.session_state["applied_end"]
        
        if range_start > range_end: 
            st.error("'From' date is after 'To' date - swap them and click Apply again.")
            range_start, range_end = range_end, range_start
            
        st.caption(f"Showing performance for: **{range_start.strftime('%d %b %Y')}** – **{range_end.strftime('%d %b %Y')}**")

        range_df = daily_df[(daily_df["Date"].dt.date >= range_start) & (daily_df["Date"].dt.date <= range_end)] if not daily_df.empty else daily_df
        range_exp = exp_df[(exp_df["Date"].dt.date >= range_start) & (exp_df["Date"].dt.date <= range_end)] if not exp_df.empty else exp_df

        flavor_range_df = load_db_flavor_sales(start_date=range_start, end_date=range_end)
        exact_cogs_sold = float(flavor_range_df["COGS (₹)"].sum()) if not flavor_range_df.empty else 0.0

        total_rev = range_df["Total_Collection"].sum() if not range_df.empty else 0.0
        total_units = int(round(range_df["Sold_Total"].sum())) if not range_df.empty else 0

        tot_labour_incurred, tot_labour_paid, tot_labour_due, _ = calculate_incurred_labour_for_range(range_start, range_end)

        non_labour_opex_df = range_exp[(range_exp["Category"] != "Labour Charges") & ((range_exp.get("Expense_Type") == "OPEX") | (range_exp["Category"].isin(["Leakage Expense", "Logistics & Transport", "Rent & Utilities", "Maintenance & Repairs", "Permits & Compliance", "Miscellaneous Expense"])))] if not range_exp.empty else pd.DataFrame()
        other_opex_total = float(non_labour_opex_df["Amount"].sum()) if not non_labour_opex_df.empty else 0.0

        total_incurred_opex = tot_labour_incurred + other_opex_total
        capex_total = float(range_exp[range_exp["Expense_Type"] == "CAPEX"]["Amount"].sum()) if not range_exp.empty and "Expense_Type" in range_exp.columns else 0.0
        if capex_total == 0.0 and not range_exp.empty: 
            capex_total = float(range_exp[range_exp["Category"].isin(["Initial Investment", "Initial Set-up Expense"])]["Amount"].sum())

        gross_profit = total_rev - exact_cogs_sold
        gross_margin = (gross_profit / total_rev * 100) if total_rev > 0 else 0.0
        net_profit = gross_profit - total_incurred_opex
        net_margin = (net_profit / total_rev * 100) if total_rev > 0 else 0.0
        opex_margin = (total_incurred_opex / total_rev * 100) if total_rev > 0 else 0.0

        st.markdown("### 1. Revenue Cycle Management & Financial Performance")
        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
        mc1.metric("Revenue in Range", f"₹{total_rev:,.0f}")
        mc2.metric("Units Sold", f"{total_units}")
        mc3.metric("COGS (Exact Goods Sold)", f"₹{exact_cogs_sold:,.0f}")
        mc4.metric(f"Gross Profit ({gross_margin:.1f}% Margin)", f"₹{gross_profit:,.0f}")
        mc5.metric(f"Total OPEX Incurred ({opex_margin:.1f}% of Rev)", f"₹{total_incurred_opex:,.0f}")
        mc6.metric(f"Net Profit ({net_margin:.1f}% Margin)", f"₹{net_profit:,.0f}")

        st.markdown("#### Daily Revenue Trend")
        if not range_df.empty:
            line_chart = alt.Chart(range_df.groupby("Date", as_index=False)["Total_Collection"].sum()).mark_line(point=True, color="#E8542A").encode(
                x=alt.X("Date:T", title="Date", axis=alt.Axis(format="%d %b")),
                y=alt.Y("Total_Collection:Q", title="Revenue (₹)"),
                tooltip=[alt.Tooltip("Date:T", format="%d %b %Y", title="Date"), alt.Tooltip("Total_Collection:Q", format=",.2f", title="Revenue (₹)")]
            ).properties(height=300)
            st.altair_chart(line_chart, use_container_width=True)
        else:
            st.caption("No revenue data available for this range to plot.")

        pl_c1, pl_c2 = st.columns([1.1, 1.2])
        with pl_c1:
            st.markdown("#### Profit & Loss Statement (P&L)")
            pnl_df = pd.DataFrame({
                "Financial Line Item": ["1. Gross Revenue", "2. COGS (Exact Goods Sold)", "3. Gross Profit (1 - 2)", "4. Staff Labour Charges (Incurred: Paid + Due)", "5. Other Operating Expenses (Rent, Logistics, etc.)", "6. Total Incurred OPEX (4 + 5)", "7. Net Operating Profit (3 - 6)"], 
                "Amount (₹)": [total_rev, -exact_cogs_sold, gross_profit, -tot_labour_incurred, -other_opex_total, -total_incurred_opex, net_profit]
            })
            st.dataframe(pnl_df, hide_index=True, use_container_width=True, column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%,.2f")})
            st.caption(f"ℹ️ **Labour breakdown:** ₹{tot_labour_paid:,.0f} disbursed / paid + ₹{tot_labour_due:,.0f} accrued / yet to be paid.")

        with pl_c2:
            st.markdown("#### Cost Distribution: COGS, OPEX & CAPEX")
            cost_dist_df = pd.DataFrame({"Cost Bucket": ["COGS (Goods Sold)", "Operating Expenses (OPEX)", "Capital Expenditure (CAPEX)"], "Amount (₹)": [exact_cogs_sold, total_incurred_opex, capex_total]})
            cost_chart = alt.Chart(cost_dist_df).mark_bar(width=28).encode(x=alt.X("Cost Bucket:N", title="", sort=None, axis=alt.Axis(labelAngle=-15)), y=alt.Y("Amount (₹):Q", title="Amount (₹)"), color=alt.Color("Cost Bucket:N", scale=alt.Scale(domain=["COGS (Goods Sold)", "Operating Expenses (OPEX)", "Capital Expenditure (CAPEX)"], range=["#C43D17", "#8A5E17", "#4A2418"]), legend=None), tooltip=[alt.Tooltip("Cost Bucket:N", title="Type"), alt.Tooltip("Amount (₹):Q", format=",.2f", title="Amount")]).properties(height=200)
            st.altair_chart(cost_chart, use_container_width=True)

        st.markdown("#### Revenue in Range - Breakdown")
        if not range_df.empty:
            total_phonepe = range_df["PhonePe"].sum()
            gross_cash = total_rev - total_phonepe
            
            # Calculate Paid Allowances from the expenses table safely and robustly
            adv_paid = 0.0
            food_paid = 0.0
            
            if not range_exp.empty and "Status" in range_exp.columns and "Sub_Category" in range_exp.columns:
                # Filter to only Paid expenses
                paid_exp = range_exp[range_exp["Status"].astype(str).str.strip().str.lower() == "paid"]
                
                if not paid_exp.empty:
                    # Use str.contains to robustly catch variations in Sub_Category naming
                    adv_mask = paid_exp["Sub_Category"].astype(str).str.contains("Advance", case=False, na=False)
                    food_mask = paid_exp["Sub_Category"].astype(str).str.contains("Food|Tea", case=False, na=False)
                    
                    adv_paid = paid_exp[adv_mask]["Amount"].sum()
                    food_paid = paid_exp[food_mask]["Amount"].sum()

            net_cash = gross_cash - adv_paid - food_paid

            # Pie Chart 1: Gross Cash vs PhonePe
            pie1_df = pd.DataFrame({"Category": ["Gross Cash", "PhonePe"], "Amount (₹)": [gross_cash, total_phonepe]})
            pie1_df = pie1_df[pie1_df["Amount (₹)"] > 0] # Clean up zeros
            
            pie1 = alt.Chart(pie1_df).mark_arc(innerRadius=0).encode(
                theta=alt.Theta(field="Amount (₹)", type="quantitative"),
                color=alt.Color(
                    field="Category", 
                    type="nominal", 
                    scale=alt.Scale(domain=["Gross Cash", "PhonePe"], range=["#2A9D8F", "#E76F51"])
                ),
                tooltip=["Category", alt.Tooltip("Amount (₹):Q", format="₹%,.2f")]
            ).properties(height=250)

            # Pie Chart 2: PhonePe, Net Cash, Staff Advance, Food/Tea
            pie2_df = pd.DataFrame({
                "Category": ["PhonePe", "Net Cash (In Hand)", "Staff Advance", "Food / Tea"], 
                "Amount (₹)": [total_phonepe, net_cash, adv_paid, food_paid]
            })
            pie2_df = pie2_df[pie2_df["Amount (₹)"] > 0] # Clean up zeros
            
            pie2 = alt.Chart(pie2_df).mark_arc(innerRadius=0).encode(
                theta=alt.Theta(field="Amount (₹)", type="quantitative"),
                color=alt.Color(
                    field="Category", 
                    type="nominal", 
                    scale=alt.Scale(
                        domain=["PhonePe", "Net Cash (In Hand)", "Staff Advance", "Food / Tea"], 
                        range=["#E76F51", "#2A9D8F", "#E9C46A", "#F4A261"]
                    )
                ),
                tooltip=["Category", alt.Tooltip("Amount (₹):Q", format="₹%,.2f")]
            ).properties(height=250)
            
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                st.write("**Gross Collection Split**")
                st.altair_chart(pie1, use_container_width=True)
            with c_p2:
                st.write("**Net Cash & Paid Allowances Breakdown**")
                st.altair_chart(pie2, use_container_width=True)
        else: 
            st.caption("No collection data in this period.")

        st.markdown("#### Incurred Operating Expense Breakdown by Category")
        exp_cat_list = []
        if tot_labour_incurred > 0: 
            exp_cat_list.append({"Category": "Labour Charges (Incurred)", "Amount (₹)": tot_labour_incurred})
        if not non_labour_opex_df.empty:
            for cat, amt in non_labour_opex_df.groupby("Category")["Amount"].sum().items(): 
                exp_cat_list.append({"Category": cat, "Amount (₹)": float(amt)})

        if exp_cat_list:
            exp_cat_df = pd.DataFrame(exp_cat_list)
            # Replaced Bar Chart with 2D Pie Chart
            exp_pie = alt.Chart(exp_cat_df).mark_arc(innerRadius=40).encode(
                theta=alt.Theta(field="Amount (₹)", type="quantitative"),
                color=alt.Color(field="Category", type="nominal", scale=alt.Scale(scheme="tableau10")), # Professional standard multi-color palette
                tooltip=["Category", alt.Tooltip("Amount (₹):Q", format=",.2f")]
            ).properties(height=300)
            st.altair_chart(exp_pie, use_container_width=True)
        else: 
            st.caption("No operating expenses incurred in this date range.")

        st.markdown("---")
        st.markdown("### 2. Comparative Cart Revenue")
        if not range_df.empty:
            cart_grp = range_df.groupby("Cart")["Total_Collection"].sum().reset_index().rename(columns={"Total_Collection": "Revenue (₹)"}).sort_values("Revenue (₹)", ascending=False)
            
            base = alt.Chart(cart_grp).encode(
                x=alt.X("Cart:N", title="", sort="-y", axis=alt.Axis(labelAngle=0, labelFontSize=13, labelPadding=10))
            )
            
            bars = base.mark_bar(color="#E8542A", cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=60).encode(
                y=alt.Y("Revenue (₹):Q", title="Total Revenue (₹)", axis=alt.Axis(grid=True, gridColor="#F0E5D1")),
                tooltip=["Cart", alt.Tooltip("Revenue (₹):Q", format=",.2f")]
            )
            
            text_labels = base.mark_text(align='center', baseline='bottom', dy=-5, color="#4A2418", fontWeight=700, fontSize=14).encode(
                y=alt.Y("Revenue (₹):Q"),
                text=alt.Text("Revenue (₹):Q", format=",.0f")
            )
            
            st.altair_chart((bars + text_labels).properties(height=300), use_container_width=True)
        else: 
            st.caption("No cart sales in this date range.")

        st.markdown("---")
        st.markdown("### 3. Day-Wise & Timing Patterns")
        if not range_df.empty:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dow_df = range_df[range_df["Sold_Total"] > 0].copy()
            dow_df["Day"] = dow_df["Date"].dt.day_name()
            
            if not dow_df.empty:
                dw1, dw2 = st.columns(2)
                with dw1: 
                    st.write("**Average Units Sold per Day of Week**")
                    units_pivot = dow_df.pivot_table(index="Cart", columns="Day", values="Sold_Total", aggfunc="mean", fill_value=0)
                    day_cols = [d for d in day_order if d in units_pivot.columns]
                    units_pivot = units_pivot.reindex(columns=day_cols)
                    st.dataframe(units_pivot.round(0).astype(int), use_container_width=True)
                with dw2: 
                    st.write("**Average Revenue (₹) per Day of Week**")
                    rev_pivot = dow_df.pivot_table(index="Cart", columns="Day", values="Total_Collection", aggfunc="mean", fill_value=0)
                    rev_pivot = rev_pivot.reindex(columns=day_cols)
                    st.dataframe(rev_pivot.round(0).astype(int), use_container_width=True)
            else: 
                st.caption("No active selling days found in this range.")

            st.markdown("#### Date-Wise Daily Sales Log")
            date_wise_agg = range_df.groupby("Date").agg({
                "Sold_Total": "sum",
                "Total_Collection": "sum",
                "PhonePe": "sum",
                "Cash": "sum",
                "Staff_Advance": "sum",
                "Food_Tea_Cash": "sum"
            }).reset_index().sort_values("Date", ascending=False)
            
            date_wise_table = date_wise_agg.rename(columns={
                "Sold_Total": "Units Sold",
                "Total_Collection": "Revenue (₹)",
                "PhonePe": "PhonePe (₹)",
                "Cash": "Cash (₹)",
                "Staff_Advance": "Staff Advance (₹)",
                "Food_Tea_Cash": "Food / Tea (₹)"
            })
            date_wise_table["Units Sold"] = date_wise_table["Units Sold"].apply(lambda x: int(round(x)))
            date_wise_table["Date"] = date_wise_table["Date"].dt.strftime("%d %b %Y")
            st.dataframe(date_wise_table, hide_index=True, use_container_width=True, column_config={
                "Revenue (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                "PhonePe (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                "Cash (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                "Staff Advance (₹)": st.column_config.NumberColumn(format="₹%,.2f"),
                "Food / Tea (₹)": st.column_config.NumberColumn(format="₹%,.2f")
            })

            st.markdown("#### Itemized Daily Cart Sales Log")
            display_cols = ["Date", "Cart", "Sold_Total", "Total_Collection", "PhonePe", "Cash", "Staff_Name", "Staff_Advance", "Food_Tea_Cash", "Remarks"]
            sales_table = range_df.sort_values(["Date", "Cart"])[display_cols].rename(columns={"Sold_Total": "Units Sold", "Total_Collection": "Revenue (₹)", "PhonePe": "PhonePe (₹)", "Cash": "Cash (₹)", "Staff_Name": "Staff Name", "Staff_Advance": "Staff Advance (₹)", "Food_Tea_Cash": "Food / Tea (₹)"})
            sales_table["Units Sold"] = sales_table["Units Sold"].apply(lambda x: int(round(x)))
            sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")
            st.dataframe(
                sales_table, 
                hide_index=True, 
                use_container_width=True, 
                column_config={
                    "Revenue (₹)": st.column_config.NumberColumn(format="₹%,.2f"), 
                    "PhonePe (₹)": st.column_config.NumberColumn(format="₹%,.2f"), 
                    "Cash (₹)": st.column_config.NumberColumn(format="₹%,.2f"), 
                    "Staff Advance (₹)": st.column_config.NumberColumn(format="₹%,.2f"), 
                    "Food / Tea (₹)": st.column_config.NumberColumn(format="₹%,.2f")
                }
            )
        else: 
            st.caption("No sales data recorded in this period.")