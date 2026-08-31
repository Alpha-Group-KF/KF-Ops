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
    FROM expenses ORDER BY expense_date DESC,