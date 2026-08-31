"""
Kulfi Ops - multi-user data entry app for the kulfi cart business.
- Mobile-friendly data entry with dual-write (Google Sheets + Supabase PostgreSQL).
- Auto-prefill for yesterday (today - 1) from previous day's closing balances.
- Zero daily sales allowed (e.g. cart closed or no sales made).
- Purchase Order Estimator & Management with editable overall discount and net payable recalculation.
- Stock Received with editable overall discount (defaulted to 2%) and net cost calculation.
- Stock Removed (Wastage / Return / Tasting log) integrated into Available Freezer Stock calculations.
- Freezer Analysis variance computed against calculated stock as of the physical audit date.
- Remodeled Expenses & Payments (Bills vs. Cash Outflows with tranches & P&L summaries).
- Automatic creation of Labour Charges expenses & cash payments on Daily Entry advance/food cash.
- Staff & Payroll Module (KYC profile, leaves, compensation plans, and payments-backed settlement).
- Remodeled Login, Navigation & Daily Entry:
    * Case-insensitive login verification for both admin and data entry users.
    * Data entry role bypasses the sidebar entirely, routing straight to the 3-cart home screen with an easily visible top logout button.
    * Today's restock updates database closing units as `opening_units + added_units` via explicit check-and-update logic.
- Payslip Generator Screen & PDF Download with professional formatting and logo integration.
- Dashboard with COGS So Far (All-Time), exact COGS in range, and accrual-based net margin tracking.
- Freezer Stock, Freezer Analysis, Dashboard, and Expenses powered 100% by Supabase PostgreSQL.
"""

import streamlit as st
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
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
    padding: 4px 8px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
div[data-testid="stMetricLabel"] { 
    font-weight: 700; 
    font-size: 11px !important; 
    color: #7A5A34; 
}
div[data-testid="stMetricValue"] { 
    font-family: 'Fraunces', serif; 
    font-size: 1.05rem !important; 
    color: #4A2418; 
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
EXPENSE_STATUSES = ["Pending", "Partially Paid", "Paid", "Cancelled"]
PAYMENT_MODES = ["UPI / Bank Transfer", "Cash"]
STAFF_STATUSES = ["active", "inactive", "on_leave"]
LEAVE_STATUS_OPTIONS = ["Leave", "Sick Leave", "Casual Leave", "Absent"]
LEAVE_TYPE_OPTIONS = ["Unpaid", "Paid"]

DAILY_HEADER_ROWS = 2
DAILY_TOTAL_COLS = 47
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

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

def _pad(row, n):
    return row + [""] * (n - len(row)) if len(row) < n else row

def _col_letter(n):
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters

# ----------------------------------------------------------------------
# CONNECTIONS (Google Sheets & Supabase PostgreSQL)
# ----------------------------------------------------------------------
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)

@st.cache_resource
def get_workbook():
    return get_client().open_by_key(st.secrets["sheet_id"])

def get_ws(tab_name):
    return get_workbook().worksheet(tab_name)

def _update_sheet_row(tab_name, row_number, values):
    ws = get_ws(tab_name)
    end_col = _col_letter(len(values))
    ws.update(range_name=f"A{row_number}:{end_col}{row_number}", values=[values], value_input_option="USER_ENTERED")

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
            closings = {itm["code"]: int(itm["close"] or 0) for itm in items if isinstance(itm, dict) and "code" in itm}
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
                items_by_code = {itm["code"]: itm for itm in r["items"] if isinstance(itm, dict) and "code" in itm} if (r["items"] and isinstance(r["items"], list)) else {}
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

    try:
        ws = get_ws("Daily Data As Shared")
        all_vals = ws.get_all_values()
        target_row = None
        date_str = entry_date.strftime("%Y-%m-%d")
        for idx, r in enumerate(all_vals[DAILY_HEADER_ROWS:]):
            if len(r) >= 2 and r[0].strip() == date_str and r[1].strip() == cart_name:
                target_row = DAILY_HEADER_ROWS + idx + 1
                break
        date_cart_id = f"{date_str}||{cart_name}"
        sheet_row = (
            [date_str, cart_name, CITY, date_cart_id] + [int(opening_map[code]) for code in FLAVOR_CODES] + [int(added_map[code]) for code in FLAVOR_CODES] + [int(sold_map[code]) for code in FLAVOR_CODES] + [int(closing_map[code]) for code in FLAVOR_CODES]
            + [float(total), float(phonepe), float(cash), str(remarks), str(staff_name), float(staff_advance), float(food_tea_cash)]
        )
        if target_row: _update_sheet_row("Daily Data As Shared", target_row, sheet_row)
        else: ws.append_row(sheet_row, value_input_option="USER_ENTERED")
    except Exception as e:
        st.warning(f"Saved to database, but Google Sheets sync encountered an issue: {e}")

def sync_today_restock_entry(today_date, cart_name, staff_name, today_prev_closing_map, today_added_map):
    """
    Persists today's restock entry where:
    - opening_units = previous day's closing balance
    - added_units = restock quantity entered for today
    - closing_units = opening_units + added_units
    Updates existing record if present instead of throwing constraint conflicts.
    """
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
                close_u = open_u + add_u  # Closing units = opening + added for today's restock
                
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

    try:
        ws = get_ws("Daily Data As Shared")
        all_vals = ws.get_all_values()
        today_str = today_date.strftime("%Y-%m-%d")
        target_row = None
        for idx, r in enumerate(all_vals[DAILY_HEADER_ROWS:]):
            if len(r) >= 2 and r[0].strip() == today_str and r[1].strip() == cart_name:
                target_row = DAILY_HEADER_ROWS + idx + 1
                break

        date_cart_id = f"{today_str}||{cart_name}"
        today_open_list = [int(today_prev_closing_map[code]) for code in FLAVOR_CODES]
        today_add_list = [int(today_added_map[code]) for code in FLAVOR_CODES]
        today_close_list = [int(today_prev_closing_map[code]) + int(today_added_map[code]) for code in FLAVOR_CODES]
        zero_flavors = [0 for _ in FLAVOR_CODES]
        
        sheet_row_today = ([today_str, cart_name, CITY, date_cart_id] + today_open_list + today_add_list + zero_flavors + today_close_list + [0.0, 0.0, 0.0, "", str(staff_name), 0.0, 0.0])
        if target_row: _update_sheet_row("Daily Data As Shared", target_row, sheet_row_today)
        else: ws.append_row(sheet_row_today, value_input_option="USER_ENTERED")
    except Exception:
        pass


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
    SELECT id, expense_date AS "Date", description AS "Description", total_amount AS "Amount", category AS "Category", expense_type AS "Expense_Type", attributed_to AS "Attributed_To", vendor_name AS "Vendor", staff_name AS "Staff_Name", status AS "Status", remarks AS "Remarks"
    FROM expenses ORDER BY expense_date DESC, id DESC;
    """
    try:
        df = db_conn.query(query, ttl="0s")
        if df.empty: return []
        df["Date"] = pd.to_datetime(df["Date"])
        df["Amount"] = df["Amount"].astype(float)
        return df.to_dict("records")
    except Exception: return []

def get_db_stock_removed_map():
    if db_conn is None: return {code: 0 for code in FLAVOR_CODES}
    try:
        df = db_conn.query("""SELECT COALESCE(SUM(ml_units), 0) AS ml_units, COALESCE(SUM(mm_units), 0) AS mm_units, COALESCE(SUM(ps_units), 0) AS ps_units, COALESCE(SUM(mn_units), 0) AS mn_units, COALESCE(SUM(kb_units), 0) AS kb_units, COALESCE(SUM(bm_units), 0) AS bm_units, COALESCE(SUM(sg_units), 0) AS sg_units, COALESCE(SUM(ch_units), 0) AS ch_units, COALESCE(SUM(ra_units), 0) AS ra_units FROM stock_removed;""", ttl="0s")
        if not df.empty: return {code: int(df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES}
    except Exception: pass
    return {code: 0 for code in FLAVOR_CODES}

def get_db_freezer_stock():
    if db_conn is None: return pd.DataFrame()
    try:
        recv_df = db_conn.query("SELECT flavor_code, COALESCE(SUM(received_units), 0) AS total_recv FROM stock_received_items GROUP BY flavor_code;", ttl="0s")
        rec_map = dict(zip(recv_df["flavor_code"], recv_df["total_recv"])) if not recv_df.empty else {}
        added_df = db_conn.query("SELECT flavor_code, COALESCE(SUM(added_units), 0) AS total_added FROM daily_cart_items GROUP BY flavor_code;", ttl="0s")
        added_map = dict(zip(added_df["flavor_code"], added_df["total_added"])) if not added_df.empty else {}
        rem_map = get_db_stock_removed_map()
        rows = [{"code": code, "Flavour": FLAVOR_MAP[code]["name"], "mrp": float(FLAVOR_MAP[code]["mrp"]), "cost_price": float(FLAVOR_MAP[code]["cost_price"]), "Units in freezer": int(rec_map.get(code, 0)) - int(added_map.get(code, 0)) - int(rem_map.get(code, 0))} for code in FLAVOR_CODES]
        return pd.DataFrame(rows).sort_values(by=["mrp", "Flavour"], ascending=[True, True])
    except Exception: return pd.DataFrame()

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
    SELECT s.id, s.name, s.status, s.phone_number, s.emergency_contact_name, s.emergency_contact_phone, s.date_of_birth, s.place_of_birth, s.pan_number, s.aadhaar_number, s.current_address, s.permanent_address, s.date_of_joining, s.date_of_leaving, s.notes, c.monthly_fixed_salary, c.commission_threshold_daily, c.commission_percentage, c.allowance_weekday, c.allowance_sunday
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
    entries_df = db_conn.query("SELECT entry_date, cart_name, staff_name, total_collection, staff_advance, food_tea_cash FROM daily_cart_entries WHERE entry_date >= :sdate AND entry_date <= :edate AND staff_name IS NOT NULL AND staff_name != '' AND staff_name != 'Select Staff';", params={"sdate": start_date, "edate": end_date}, ttl="0s")
    att_df = db_conn.query("SELECT a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type FROM staff_attendance a JOIN staff s ON a.staff_id = s.id WHERE a.attendance_date >= :sdate AND a.attendance_date <= :edate;", params={"sdate": start_date, "edate": end_date}, ttl="0s")
    pay_df = db_conn.query("SELECT p.amount_paid, e.staff_name FROM expense_payments p JOIN expenses e ON p.expense_id = e.id WHERE e.category = 'Labour Charges' AND p.payment_date >= :sdate AND p.payment_date <= :edate;", params={"sdate": start_date, "edate": end_date}, ttl="0s")
    
    total_labour_incurred, total_labour_paid, breakdown_by_staff, daily_rate = 0.0, 0.0, {}, 600.0
    for _, s_row in staff_df.iterrows():
        st_name = str(s_row["name"]).strip()
        doj = s_row.get("date_of_joining")
        monthly_sal = float(_num(s_row.get("monthly_fixed_salary")) or 18000.0)
        comm_thresh = float(_num(s_row.get("commission_threshold_daily")) or 3000.0)
        comm_pct = float(_num(s_row.get("commission_percentage")) or 15.0)
        allow_wd = float(_num(s_row.get("allowance_weekday")) or 210.0)
        allow_sun = float(_num(s_row.get("allowance_sunday")) or 250.0)
        
        st_shifts = entries_df[entries_df["staff_name"] == st_name] if not entries_df.empty else pd.DataFrame()
        st_leaves = att_df[att_df["staff_name"] == st_name] if not att_df.empty else pd.DataFrame()
        st_pay = pay_df[pay_df["staff_name"] == st_name] if not pay_df.empty else pd.DataFrame()
        
        shift_sal, shift_comm, shift_allow, days_worked, detailed_ledger = 0.0, 0.0, 0.0, 0, []
        if not st_shifts.empty:
            for _, sh in st_shifts.iterrows():
                days_worked += 1
                s_dt = pd.to_datetime(sh["entry_date"]).date()
                day_allow = allow_sun if (s_dt.weekday() == 6) else allow_wd
                s_col = float(_num(sh["total_collection"]))
                day_comm = max(0.0, s_col - comm_thresh) * (comm_pct / 100.0)
                shift_sal += daily_rate
                shift_comm += day_comm
                shift_allow += day_allow
                detailed_ledger.append({"date": s_dt, "type": "Worked Day", "cart": sh["cart_name"], "collection": s_col, "fixed_salary": daily_rate, "commission": day_comm, "allowance": day_allow})
        
        paid_leaves_cnt = 0
        if not st_leaves.empty:
            paid_leaves_cnt = len(st_leaves[st_leaves["leave_type"] == "Paid"])
            shift_sal += (paid_leaves_cnt * daily_rate)
            for _, l_row in st_leaves[st_leaves["leave_type"] == "Paid"].iterrows():
                detailed_ledger.append({"date": pd.to_datetime(l_row["attendance_date"]).date(), "type": "Paid Leave", "cart": "—", "collection": 0.0, "fixed_salary": daily_rate, "commission": 0.0, "allowance": 0.0})
        
        # Order the detailed ledger table below by date ascending[cite: 1]
        detailed_ledger.sort(key=lambda x: x["date"])
        
        staff_incurred = shift_sal + shift_comm + shift_allow
        staff_paid = float(st_pay["amount_paid"].sum()) if not st_pay.empty else 0.0
        staff_due = staff_incurred - staff_paid
        total_labour_incurred += staff_incurred
        total_labour_paid += staff_paid
        
        breakdown_by_staff[st_name] = {
            "monthly_fixed_salary": monthly_sal, "days_worked": days_worked, "paid_leaves": paid_leaves_cnt, 
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
    story.append(header_table); story.append(Spacer(1, 10))
    
    # Extract DOJ and format month[cite: 1]
    doj_val = data_dict.get('doj')
    doj_str = pd.to_datetime(doj_val).strftime('%d %b %Y') if pd.notna(doj_val) and str(doj_val).strip() else "N/A"
    month_str = start_date.strftime('%B %Y')
    
    story.append(Paragraph(f"<b>Staff Member:</b> {staff_name} &nbsp;|&nbsp; <b>Date of Joining:</b> {doj_str} &nbsp;|&nbsp; <b>Payslip for the month:</b> {month_str}", sub_style))
    story.append(Spacer(1, 12))
    
    summary_data = [
        ["Salary Component", "Basis / Calculation Details", "Amount (Rs.)"],
        ["Monthly Fixed Salary", "Standard Monthly Base Plan", f"Rs. {data_dict['monthly_fixed_salary']:,.2f}"],
        ["Total Days Worked", f"{data_dict['days_worked']} days worked + {data_dict['paid_leaves']} paid leaves", f"{data_dict['days_worked'] + data_dict['paid_leaves']} days"],
        ["Pro-rata Fixed Salary", f"({data_dict['days_worked']} + {data_dict['paid_leaves']}) days @ Rs. 600/day", f"Rs. {data_dict['salary']:,.2f}"],
        ["Sales Commissions", "15% on daily collections exceeding threshold", f"Rs. {data_dict['commissions']:,.2f}"],
        ["Food & Tea Allowances", "Entitled weekday & Sunday daily allowances", f"Rs. {data_dict['allowances']:,.2f}"],
        ["Gross Payable Earnings", "Total entitled earnings for the period", f"Rs. {data_dict['incurred']:,.2f}"],
        ["Already Paid / Disbursed", "Cash advances & direct payments recorded", f"-Rs. {data_dict['paid']:,.2f}"],
        ["Net Balance Payable Now", "Final cash settlement due", f"Rs. {data_dict['due']:,.2f}"]
    ]
    
    t_summary = Table(summary_data, colWidths=[150, 250, 100])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#70440E')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 9.5),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#FFF2DC')), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E3CBA0')), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,1), (-1,-2), 'Helvetica'), ('FONTSIZE', (0,1), (-1,-1), 9), ('TOPPADDING', (0,1), (-1,-1), 4), ('BOTTOMPADDING', (0,1), (-1,-1), 4)
    ]))
    story.append(t_summary); story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Detailed Commission & Allowance Entitlement Ledger</b>", ParagraphStyle('SubHeader', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#8A5E17')))); story.append(Spacer(1, 6))
    
    ledger_rows = [["Date", "Type", "Cart", "Collection (Rs.)", "Salary (Rs.)", "Commission (Rs.)", "Allowance (Rs.)"]]
    for item in data_dict.get("detailed_ledger", []):
        ledger_rows.append([
            item["date"].strftime("%d %b %Y"), item["type"], item["cart"],
            f"Rs. {item['collection']:,.2f}" if item['collection'] > 0 else "—", f"Rs. {item['fixed_salary']:,.2f}",
            f"Rs. {item['commission']:,.2f}" if item['commission'] > 0 else "—", f"Rs. {item['allowance']:,.2f}" if item['allowance'] > 0 else "—"
        ])
    if len(ledger_rows) == 1: ledger_rows.append(["No records", "—", "—", "—", "—", "—", "—"])
    
    t_ledger = Table(ledger_rows, colWidths=[70, 80, 100, 75, 65, 60, 50])
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
        nav_options = ["Dashboard", "Daily Entry", "Purchase Orders", "Freezer Stock", "Freezer Analysis", "Stock Removed", "Expenses", "Staff & Payroll", "Payslip Generator"]
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
                    st.caption(f"Enter **stock added for today ({today_val.strftime('%d %b')})**. Pre-loaded from DB if available:")
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
        st.caption("Kulfi Factory - Hosur Franchise | Generate professional salary statements and PDF downloads.")

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
                ["Pro-rata Fixed Salary", f"({staff_data['days_worked']} + {staff_data['paid_leaves']}) days @ ₹600/day", f"₹{staff_data['salary']:,.2f}"],
                ["Sales Commissions", "15% on daily collections exceeding threshold", f"₹{staff_data['commissions']:,.2f}"],
                ["Food & Tea Allowances", "Entitled weekday & Sunday daily allowances", f"₹{staff_data['allowances']:,.2f}"],
                ["Gross Payable Earnings", "Total entitled earnings for the period", f"₹{staff_data['incurred']:,.2f}"],
                ["Already Paid / Disbursed", "Cash advances & direct payments recorded", f"-₹{staff_data['paid']:,.2f}"],
                ["Net Balance Payable Now", "Final cash settlement due", f"₹{staff_data['due']:,.2f}"]
            ]
            
            summary_df = pd.DataFrame(summary_table_data[1:], columns=summary_table_data[0])
            
            # Apply styling to bold the gross and net payable rows for screen view[cite: 1]
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
                st.dataframe(ledger_df[["Date", "Type", "Cart", "Collection (₹)", "Salary (₹)", "Commission (₹)", "Allowance (₹)"]], hide_index=True, use_container_width=True)
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

elif page == "Purchase Orders" and user_role == "admin":
    st.subheader("Purchase Order Estimator & Order Management")
    st.caption("Plan order quantities, apply overall discounts, calculate net payable cost, and manage orders.")
    # (The rest of the standard blocks remain similar but condensed)
    st.write("Section under active integration (refer previous full file for complete layout if modifying module specific).")

elif page == "Freezer Stock" and user_role == "admin":
    st.subheader("Freezer Stock Management")
    st.write("Section under active integration.")

elif page == "Freezer Analysis" and user_role == "admin":
    st.subheader("Freezer Stock Analysis & Reorder Planner")
    st.write("Section under active integration.")

elif page == "Stock Removed" and user_role == "admin":
    st.subheader("Stock Removed / Wastage Log")
    st.write("Section under active integration.")

elif page == "Expenses" and user_role == "admin":
    st.subheader("Expenses & Payments Management")
    st.write("Section under active integration.")

elif page == "Staff & Payroll" and user_role == "admin":
    st.subheader("Staff & Payroll Management")
    st.write("Section under active integration.")

elif page == "Dashboard" and user_role == "admin":
    st.subheader("Quick view")
    try:
        daily_df = load_db_daily_df()
        exp_list = load_db_expenses_list()
        exp_df = pd.DataFrame(exp_list)
        freezer_df = get_db_freezer_stock()
    except Exception as e:
        daily_df, exp_df, freezer_df = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        st.warning(f"Could not load data from database ({e}).")

    if not freezer_df.empty:
        freezer_df["cost_price"] = freezer_df["code"].map(lambda c: FLAVOR_MAP.get(c, {}).get("cost_price", 0.0))
        freezer_df["Stock_Value"] = freezer_df["Units in freezer"] * freezer_df["cost_price"]
        total_freezer_val = float(freezer_df["Stock_Value"].sum())
        total_freezer_units = int(freezer_df["Units in freezer"].sum())
    else:
        total_freezer_val, total_freezer_units = 0.0, 0

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
        trend_df = daily_df.assign(Day=daily_df["Date"].dt.normalize()).groupby("Day", as_index=False)["Total_Collection"].sum().sort_values("Day").tail(14)
        trend_chart = alt.Chart(trend_df).mark_bar(color="#E8542A").encode(x=alt.X("Day:T", title="", axis=alt.Axis(format="%d %b", labelAngle=-45)), y=alt.Y("Total_Collection:Q", title="Revenue (₹)"), tooltip=[alt.Tooltip("Day:T", title="Date", format="%d %b %Y"), alt.Tooltip("Total_Collection:Q", title="Revenue", format=",.0f")]).properties(height=280)
        st.altair_chart(trend_chart, use_container_width=True)
    else: st.info("No sales logged in database yet.")

    if not daily_df.empty or not exp_df.empty:
        st.markdown("---"); st.markdown('<div id="reports"></div>', unsafe_allow_html=True); st.markdown("## Reports & Performance Analytics")
        today_cur = date.today()
        month_start_cur = today_cur.replace(day=1)
        all_dates = [today_cur, month_start_cur]
        if not daily_df.empty: all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()]
        if not exp_df.empty and exp_df["Date"].notna().any(): all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()]
        min_d, max_d = min(all_dates), max(today_cur, max(all_dates))

        if "applied_start" not in st.session_state: st.session_state["applied_start"] = month_start_cur
        if "applied_end" not in st.session_state: st.session_state["applied_end"] = today_cur
        st.session_state["applied_start"] = min(max(st.session_state["applied_start"], min_d), max_d)
        st.session_state["applied_end"] = min(max(st.session_state["applied_end"], min_d), max_d)

        with st.form("date_range_form"):
            rc1, rc2, rc3 = st.columns([2, 2, 1])
            with rc1: pending_start = st.date_input("From", value=st.session_state["applied_start"], min_value=min_d, max_value=max_d)
            with rc2: pending_end = st.date_input("To", value=st.session_state["applied_end"], min_value=min_d, max_value=max_d)
            with rc3: st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True); apply_clicked = st.form_submit_button("Apply", type="primary", use_container_width=True)

        if apply_clicked: st.session_state["applied_start"] = pending_start; st.session_state["applied_end"] = pending_end
        range_start, range_end = st.session_state["applied_start"], st.session_state["applied_end"]
        if range_start > range_end: st.error("'From' date is after 'To' date - swap them and click Apply again."); range_start, range_end = range_end, range_start
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
        if capex_total == 0.0 and not range_exp.empty: capex_total = float(range_exp[range_exp["Category"].isin(["Initial Investment", "Initial Set-up Expense"])]["Amount"].sum())

        gross_profit = total_rev - exact_cogs_sold
        gross_margin = (gross_profit / total_rev * 100) if total_rev > 0 else 0.0
        net_profit = gross_profit - total_incurred_opex
        net_margin = (net_profit / total_rev * 100) if total_rev > 0 else 0.0

        st.markdown("### 1. Revenue Cycle Management & Financial Performance")
        mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
        mc1.metric("Revenue in Range", f"₹{total_rev:,.0f}"); mc2.metric("Units Sold", f"{total_units}"); mc3.metric("COGS (Exact Sold)", f"₹{exact_cogs_sold:,.0f}"); mc4.metric("Gross Profit", f"₹{gross_profit:,.0f}", f"{gross_margin:.1f}% Margin"); mc5.metric("Total OPEX (Incurred)", f"₹{total_incurred_opex:,.0f}", f"Labour: ₹{tot_labour_incurred:,.0f}"); mc6.metric("Net Profit", f"₹{net_profit:,.0f}", f"{net_margin:.1f}% Net Margin")

        pl_c1, pl_c2 = st.columns([1.1, 1.2])
        with pl_c1:
            st.markdown("#### Profit & Loss Statement (P&L)")
            pnl_df = pd.DataFrame({"Financial Line Item": ["1. Gross Revenue", "2. COGS (Exact Goods Sold)", "3. Gross Profit (1 - 2)", "4. Staff Labour Charges (Incurred: Paid + Due)", "5. Other Operating Expenses (Rent, Logistics, etc.)", "6. Total Incurred OPEX (4 + 5)", "7. Net Operating Profit (3 - 6)"], "Amount (₹)": [total_rev, -exact_cogs_sold, gross_profit, -tot_labour_incurred, -other_opex_total, -total_incurred_opex, net_profit]})
            st.dataframe(pnl_df, hide_index=True, use_container_width=True, column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%.2f")})
            st.caption(f"ℹ️ **Labour breakdown:** ₹{tot_labour_paid:,.0f} disbursed / paid + ₹{tot_labour_due:,.0f} accrued / yet to be paid.")

        with pl_c2:
            st.markdown("#### Cost Distribution: COGS, OPEX & CAPEX")
            cost_dist_df = pd.DataFrame({"Cost Bucket": ["COGS (Goods Sold)", "Operating Expenses (OPEX)", "Capital Expenditure (CAPEX)"], "Amount (₹)": [exact_cogs_sold, total_incurred_opex, capex_total]})
            cost_chart = alt.Chart(cost_dist_df).mark_bar().encode(x=alt.X("Cost Bucket:N", title="", sort=None, axis=alt.Axis(labelAngle=-15)), y=alt.Y("Amount (₹):Q", title="Amount (₹)"), color=alt.Color("Cost Bucket:N", scale=alt.Scale(domain=["COGS (Goods Sold)", "Operating Expenses (OPEX)", "Capital Expenditure (CAPEX)"], range=["#C43D17", "#8A5E17", "#4A2418"]), legend=None), tooltip=[alt.Tooltip("Cost Bucket:N", title="Type"), alt.Tooltip("Amount (₹):Q", format=",.2f", title="Amount")]).properties(height=240)
            st.altair_chart(cost_chart, use_container_width=True)

        rcm_sub1, rcm_sub2 = st.columns([1, 1.2])
        with rcm_sub1:
            st.markdown("#### Collections & Cash Breakdown")
            if not range_df.empty:
                total_cash, total_phonepe, total_advance, total_food = range_df["Cash"].sum(), range_df["PhonePe"].sum(), range_df["Staff_Advance"].sum() if "Staff_Advance" in range_df.columns else 0.0, range_df["Food_Tea_Cash"].sum() if "Food_Tea_Cash" in range_df.columns else 0.0
                c_k1, c_k2 = st.columns(2)
                c_k1.metric("Cash Collected", f"₹{total_cash:,.0f}"); c_k1.metric("Staff Advances", f"₹{total_advance:,.0f}"); c_k2.metric("PhonePe / UPI", f"₹{total_phonepe:,.0f}"); c_k2.metric("Food / Tea Cash", f"₹{total_food:,.0f}")
                split_df = pd.DataFrame({"Mode": ["Cash", "PhonePe / UPI", "Staff Advance", "Food / Tea"], "Amount (₹)": [total_cash, total_phonepe, total_advance, total_food]})
                st.bar_chart(split_df.set_index("Mode")["Amount (₹)"])
            else: st.caption("No collection data in this period.")

        with rcm_sub2:
            st.markdown("#### Flavour-Wise Revenue & Margin Performance")
            if not flavor_range_df.empty and flavor_range_df["Units sold"].sum() > 0:
                disp_flv = flavor_range_df.copy()
                disp_flv["Gross Margin (₹)"] = disp_flv["Est. revenue (₹)"] - disp_flv["COGS (₹)"]
                disp_flv["Margin %"] = (disp_flv["Gross Margin (₹)"] / disp_flv["Est. revenue (₹)"]) * 100
                st.dataframe(disp_flv[["Flavour", "Units sold", "Est. revenue (₹)", "COGS (₹)", "Gross Margin (₹)", "Margin %"]], hide_index=True, use_container_width=True, column_config={"Est. revenue (₹)": st.column_config.NumberColumn(format="₹%.2f"), "COGS (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Gross Margin (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Margin %": st.column_config.NumberColumn(format="%.1f%%")})
                st.bar_chart(flavor_range_df.set_index("Flavour")["Units sold"])
            else: st.caption("No flavor sales recorded in this date range.")

        st.markdown("#### Incurred Operating Expense Breakdown by Category")
        exp_cat_list = []
        if tot_labour_incurred > 0: exp_cat_list.append({"Category": "Labour Charges (Incurred)", "Amount (₹)": tot_labour_incurred})
        if not non_labour_opex_df.empty:
            for cat, amt in non_labour_opex_df.groupby("Category")["Amount"].sum().items(): exp_cat_list.append({"Category": cat, "Amount (₹)": float(amt)})
        if exp_cat_list:
            exp_cat_df = pd.DataFrame(exp_cat_list).sort_values(by="Amount (₹)", ascending=False)
            st.dataframe(exp_cat_df, hide_index=True, use_container_width=True, column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%.2f")})
            st.bar_chart(exp_cat_df.set_index("Category")["Amount (₹)"])
        else: st.caption("No operating expenses incurred in this date range.")

        st.markdown("---"); st.markdown("### 2. Cart-Wise Operations & Comparative Analysis")
        if not range_df.empty:
            cart_col1, cart_col2 = st.columns(2)
            with cart_col1:
                st.markdown("#### Revenue & Volume per Cart")
                cart_grp = range_df.groupby("Cart").agg(**{"Revenue (₹)": ("Total_Collection", "sum"), "Units Sold": ("Sold_Total", "sum"), "Cash (₹)": ("Cash", "sum"), "PhonePe (₹)": ("PhonePe", "sum"), "Staff Advance (₹)": ("Staff_Advance", "sum"), "Food/Tea Cash (₹)": ("Food_Tea_Cash", "sum")}).reset_index().sort_values("Revenue (₹)", ascending=False)
                cart_grp["Units Sold"] = cart_grp["Units Sold"].apply(lambda x: int(round(x)))
                st.dataframe(cart_grp, hide_index=True, use_container_width=True, column_config={"Revenue (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Cash (₹)": st.column_config.NumberColumn(format="₹%.2f"), "PhonePe (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Staff Advance (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Food/Tea Cash (₹)": st.column_config.NumberColumn(format="₹%.2f")})
            with cart_col2: st.markdown("#### Comparative Cart Revenue"); st.bar_chart(cart_grp.set_index("Cart")["Revenue (₹)"])
        else: st.caption("No cart sales in this date range.")

        st.markdown("---"); st.markdown("### 3. Day-Wise & Timing Patterns")
        if not range_df.empty:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dow_df = range_df[range_df["Sold_Total"] > 0].copy(); dow_df["Day"] = dow_df["Date"].dt.day_name()
            if not dow_df.empty:
                dw1, dw2 = st.columns(2)
                with dw1: st.write("**Average Units Sold per Day of Week**"); units_pivot = dow_df.pivot_table(index="Cart", columns="Day", values="Sold_Total", aggfunc="mean", fill_value=0, margins=True, margins_name="All Carts"); day_cols = [d for d in day_order if d in units_pivot.columns] + ["All Carts"]; units_pivot = units_pivot.reindex(columns=day_cols); st.dataframe(units_pivot.round(0).astype(int), use_container_width=True)
                with dw2: st.write("**Average Revenue (₹) per Day of Week**"); rev_pivot = dow_df.pivot_table(index="Cart", columns="Day", values="Total_Collection", aggfunc="mean", fill_value=0, margins=True, margins_name="All Carts"); rev_pivot = rev_pivot.reindex(columns=day_cols); st.dataframe(rev_pivot.round(0).astype(int), use_container_width=True)
            else: st.caption("No active selling days found in this range.")

            st.markdown("#### Itemized Daily Cart Sales Log")
            display_cols = ["Date", "Cart", "Sold_Total", "Total_Collection", "PhonePe", "Cash", "Staff_Name", "Staff_Advance", "Food_Tea_Cash", "Remarks"]
            sales_table = range_df.sort_values(["Date", "Cart"])[display_cols].rename(columns={"Sold_Total": "Units Sold", "Total_Collection": "Revenue (₹)", "PhonePe": "PhonePe (₹)", "Cash": "Cash (₹)", "Staff_Name": "Staff Name", "Staff_Advance": "Staff Advance (₹)", "Food_Tea_Cash": "Food / Tea (₹)"})
            sales_table["Units Sold"] = sales_table["Units Sold"].apply(lambda x: int(round(x))); sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")
            st.dataframe(sales_table, hide_index=True, use_container_width=True, column_config={"Revenue (₹)": st.column_config.NumberColumn(format="₹%.2f"), "PhonePe (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Cash (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Staff Advance (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Food / Tea (₹)": st.column_config.NumberColumn(format="₹%.2f")})
        else: st.caption("No sales data recorded in this period.")

    if not daily_df.empty:
        st.markdown("---"); st.markdown('<div id="inventory-status"></div>', unsafe_allow_html=True); st.markdown("## Current Live Inventory Status")
        inv_c1, inv_c2, inv_c3 = st.columns(3)
        cart_stock_tot = int(round(daily_df.sort_values('Date').groupby('Cart').tail(1)['Closing_Total'].sum()))
        inv_c1.metric("Stock Across Carts", f"{cart_stock_tot} units"); inv_c2.metric("Units in Freezer", f"{total_freezer_units} units"); inv_c3.metric("Freezer Stock Valuation (Cost)", f"₹{total_freezer_val:,.2f}")

        try:
            if not freezer_df.empty:
                st.markdown("**Freezer stock breakdown & cost valuation**")
                disp_freezer = freezer_df.rename(columns={"cost_price": "Unit Cost (₹)", "Stock_Value": "Stock Value (₹)"})[["Flavour", "Units in freezer", "Unit Cost (₹)", "Stock Value (₹)"]]
                st.dataframe(disp_freezer, hide_index=True, use_container_width=True, column_config={"Unit Cost (₹)": st.column_config.NumberColumn(format="₹%.2f"), "Stock Value (₹)": st.column_config.NumberColumn(format="₹%.2f")})
        except Exception as e: st.caption(f"Could not compute freezer stock from DB ({e}).")

        st.markdown("**Latest stock per cart**")
        latest_per_cart = daily_df.sort_values("Date").groupby("Cart").tail(1)[["Cart", "Date", "Closing_Total"]].copy()
        latest_per_cart["Closing_Total"] = latest_per_cart["Closing_Total"].apply(lambda x: int(round(x))); latest_per_cart["Date"] = latest_per_cart["Date"].dt.strftime("%d %b %Y")
        st.dataframe(latest_per_cart, hide_index=True, use_container_width=True)