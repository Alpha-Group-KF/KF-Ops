"""
Kulfi Ops - multi-user data entry app for the kulfi cart business.
- Mobile-friendly data entry with dual-write (Google Sheets + Supabase PostgreSQL).
- Auto-prefill for yesterday (today - 1) from previous day's closing balances.
- Zero daily sales allowed (e.g. cart closed or no sales made).
- Purchase Order Estimator & Management with editable overall discount and net payable recalculation.
- Stock Removed (Wastage / Return / Tasting log) integrated into Available Freezer Stock calculations.
- Dashboard with COGS So Far (All-Time) & Outstanding Freezer Stock Valuation.
- Freezer Stock, Freezer Analysis, Dashboard, and Expenses powered 100% by Supabase PostgreSQL.
"""

import streamlit as st
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import hmac
import re
from datetime import date, datetime, timedelta
from sqlalchemy import text

st.set_page_config(page_title="Kulfi Ops", page_icon="🍦", layout="wide")

# ----------------------------------------------------------------------
# GLOBAL UI STYLES
# ----------------------------------------------------------------------
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1.5rem !important;
    margin-top: 0 !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] {
    background-color: transparent !important;
    height: 1rem !important;
}
html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
h1, h2, h3 { font-family: 'Fraunces', serif !important; color: #8A5E17 !important; letter-spacing: -0.01em; }
h1 { font-size: 1.5rem !important; margin-top: 0 !important; }
h2 { font-size: 1.25rem !important; }
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

/* Mobile Flavor Card Grid */
.flavor-entry-row {
    background: #FFFDF8;
    border: 1.5px solid #E3CBA0;
    border-radius: 10px;
    padding: 8px 10px;
    margin-bottom: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.03);
}
.flavor-title-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
}
.flavor-name {
    font-weight: 800;
    font-size: 14px;
    color: #4A2418;
}
.badge-open {
    background: #EFE4CF;
    color: #5A3E1B;
    font-weight: 700;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 12px;
}
.badge-sold {
    background: #FCE8E2;
    color: #C43D17;
    font-weight: 800;
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 12px;
}

/* Inputs */
.stTextInput div[data-baseweb="input"], .stNumberInput div[data-baseweb="input"] {
    min-height: 32px !important;
    height: 32px !important;
    border-radius: 8px !important;
}
.stTextInput input, .stNumberInput input {
    padding: 3px 8px !important;
    font-size: 13px !important;
    text-align: left !important;
    font-weight: 600 !important;
}
.stNumberInput label, .stTextInput label {
    font-size: 11px !important;
    font-weight: 700 !important;
    margin-bottom: 2px !important;
    text-align: left !important;
}

section[data-testid="stSidebar"] { 
    font-size: 15px !important; 
    border-right: 1px solid #E3CBA0; 
}
section[data-testid="stSidebar"] h2 { 
    font-size: 20px !important; 
    color: #8A5E17 !important; 
}
section[data-testid="stSidebar"] .stRadio > div { 
    gap: 4px; 
}
section[data-testid="stSidebar"] .stRadio label {
    background: #FFFBF2;
    border: 1px solid #E3CBA0;
    border-radius: 8px;
    padding: 6px 10px !important;
    margin-bottom: 2px;
    transition: background .15s ease, border-color .15s ease;
}
section[data-testid="stSidebar"] .stRadio label:hover { 
    background: #F0D9A6; 
    border-color: #E8542A; 
}

/* Buttons */
.stButton button, [data-testid="stFormSubmitButton"] button, [data-testid="baseButton-primary"] {
    border-radius: 8px !important;
    font-weight: 700 !important;
    border: none !important;
    padding: 0.4rem 0.8rem !important;
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
    border-radius: 10px;
    padding: 6px 12px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
div[data-testid="stMetricLabel"] { 
    font-weight: 700; 
    font-size: 12px !important; 
    color: #7A5A34; 
}
div[data-testid="stMetricValue"] { 
    font-family: 'Fraunces', serif; 
    font-size: 1.2rem !important; 
    color: #4A2418; 
}

/* Tables */
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
    border-radius: 10px;
    border: 2px solid #8A5E17 !important;
    overflow: hidden;
}
div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
    font-weight: 900 !important;
    color: #FFFFFF !important;
    background-color: #70440E !important;
    text-align: center !important;
    font-size: 13px !important;
}
div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
    text-align: center !important;
    font-size: 12.5px !important;
}
hr { border-color: #E3CBA0 !important; margin: 0.4rem 0 !important; }
</style>
""")

# ----------------------------------------------------------------------
# CONFIG & CANONICAL MAPPINGS
# ----------------------------------------------------------------------
CARTS = ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"]
CITY = "HOSUR"

PAYMENT_STATUSES = ["Pending", "Partial", "Complete"]
PO_STATUSES = ["Placed", "Pending", "In Transit", "Completed", "Cancelled"]
EXPENSE_CATEGORIES = [
    "Cost of Goods",
    "Labour Charges",
    "Leakage Expense",
    "Initial Set-up Expense",
    "Miscellaneous Expense",
    "Initial Investment",
]
PAYMENT_MODES = ["Cash", "UPI / Bank Transfer"]

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
    if x is None or pd.isna(x):
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip().replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        return -float(s) if neg else float(s)
    except ValueError:
        return 0.0


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
# FLAVORS & STAFF LOADERS
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


# ----------------------------------------------------------------------
# DATABASE LOADERS & PRE-FILL HELPERS
# ----------------------------------------------------------------------
def get_latest_cart_closing_state(cart_name, before_date):
    """Fetches the latest closing units by flavor code and staff name for a cart before a given date."""
    if db_conn is None:
        return {}, ""
    query = """
    SELECT 
        e.staff_name,
        json_agg(json_build_object(
            'code', i.flavor_code,
            'close', i.closing_units
        )) AS items
    FROM daily_cart_entries e
    LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
    WHERE e.cart_name = :cart AND e.entry_date < :bdate
    GROUP BY e.id, e.entry_date, e.staff_name
    ORDER BY e.entry_date DESC
    LIMIT 1;
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
    """
    Loads daily entries from the database.
    If yesterday (today - 1) has no record for any of the 3 carts, pre-fills a default record
    where Opening = previous Closing, Closing = Opening (Sold = 0), and Staff = previous Staff.
    """
    entries = []
    if db_conn is not None:
        query = """
        SELECT 
            e.id AS db_id,
            e.entry_date,
            e.cart_name,
            e.staff_name,
            e.total_collection,
            e.phonepe,
            e.cash,
            e.staff_advance,
            e.food_tea_cash,
            e.remarks,
            json_agg(json_build_object(
                'code', i.flavor_code,
                'open', i.opening_units,
                'add', i.added_units,
                'sold', i.sold_units,
                'close', i.closing_units
            )) AS items
        FROM daily_cart_entries e
        LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
        GROUP BY e.id, e.entry_date, e.cart_name, e.staff_name, e.total_collection, e.phonepe, e.cash, e.staff_advance, e.food_tea_cash, e.remarks
        ORDER BY e.entry_date DESC, e.cart_name ASC;
        """
        df = db_conn.query(query, ttl="0s")
        if not df.empty:
            for _, r in df.iterrows():
                items_by_code = {
                    itm["code"]: itm for itm in r["items"] if isinstance(itm, dict) and "code" in itm
                } if (r["items"] and isinstance(r["items"], list)) else {}

                entries.append({
                    "db_id": r["db_id"],
                    "date": pd.to_datetime(r["entry_date"]),
                    "cart": str(r["cart_name"]).strip(),
                    "by_code": {
                        code: {
                            "opening": int(items_by_code.get(code, {}).get("open") or 0),
                            "added": int(items_by_code.get(code, {}).get("add") or 0),
                            "sold": int(items_by_code.get(code, {}).get("sold") or 0),
                            "closing": int(items_by_code.get(code, {}).get("close") or 0),
                        }
                        for code in FLAVOR_CODES
                    },
                    "total": float(r["total_collection"]) if pd.notna(r["total_collection"]) else 0.0,
                    "phonepe": float(r["phonepe"]) if pd.notna(r["phonepe"]) else 0.0,
                    "cash": float(r["cash"]) if pd.notna(r["cash"]) else 0.0,
                    "remarks": str(r["remarks"]) if pd.notna(r["remarks"]) else "",
                    "staff_name": str(r["staff_name"]) if pd.notna(r["staff_name"]) else "",
                    "staff_advance": float(r["staff_advance"]) if pd.notna(r["staff_advance"]) else 0.0,
                    "food_tea_cash": float(r["food_tea_cash"]) if pd.notna(r["food_tea_cash"]) else 0.0,
                    "is_prefill": False
                })

    yesterday = date.today() - timedelta(days=1)
    existing_yesterday_carts = {
        e["cart"] for e in entries if e["date"].date() == yesterday
    }

    # For any cart missing yesterday, create a default pre-fill entry
    for cart in CARTS:
        if cart not in existing_yesterday_carts:
            prev_closings, prev_staff = get_latest_cart_closing_state(cart, yesterday)
            by_code = {}
            for code in FLAVOR_CODES:
                prev_close = prev_closings.get(code, 0)
                by_code[code] = {
                    "opening": prev_close,
                    "added": 0,
                    "closing": prev_close,  # Closing = Opening ensures Sold = 0
                    "sold": 0,
                }

            entries.append({
                "db_id": f"prefill_{cart}_{yesterday.strftime('%Y%m%d')}",
                "date": pd.Timestamp(yesterday),
                "cart": cart,
                "by_code": by_code,
                "total": 0.0,
                "phonepe": 0.0,
                "cash": 0.0,
                "remarks": "",
                "staff_name": prev_staff,
                "staff_advance": 0.0,
                "food_tea_cash": 0.0,
                "is_prefill": True
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
                SET staff_name = EXCLUDED.staff_name, total_collection = EXCLUDED.total_collection,
                    phonepe = EXCLUDED.phonepe, cash = EXCLUDED.cash, staff_advance = EXCLUDED.staff_advance,
                    food_tea_cash = EXCLUDED.food_tea_cash, remarks = EXCLUDED.remarks
                RETURNING id;
                """),
                {
                    "date": entry_date, "cart": cart_name, "city": CITY, "staff": staff_name,
                    "tot": float(total), "ph": float(phonepe), "cash": float(cash),
                    "adv": float(staff_advance), "food": float(food_tea_cash), "rem": str(remarks)
                }
            )
            daily_id = res.scalar()
            s.execute(text("DELETE FROM daily_cart_items WHERE daily_entry_id = :id;"), {"id": daily_id})
            for code in FLAVOR_CODES:
                s.execute(
                    text("""
                    INSERT INTO daily_cart_items (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
                    VALUES (:eid, :code, :open, :add, :sold, :close);
                    """),
                    {
                        "eid": daily_id, "code": code,
                        "open": int(opening_map[code]), "add": int(added_map[code]),
                        "sold": int(sold_map[code]), "close": int(closing_map[code])
                    }
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
            [date_str, cart_name, CITY, date_cart_id]
            + [int(opening_map[code]) for code in FLAVOR_CODES]
            + [int(added_map[code]) for code in FLAVOR_CODES]
            + [int(sold_map[code]) for code in FLAVOR_CODES]
            + [int(closing_map[code]) for code in FLAVOR_CODES]
            + [float(total), float(phonepe), float(cash), str(remarks), str(staff_name), float(staff_advance), float(food_tea_cash)]
        )
        if target_row:
            _update_sheet_row("Daily Data As Shared", target_row, sheet_row)
        else:
            ws.append_row(sheet_row, value_input_option="USER_ENTERED")
    except Exception as e:
        st.warning(f"Saved to database, but Google Sheets sync encountered an issue: {e}")


def load_db_daily_df():
    if db_conn is None:
        return pd.DataFrame()
    query = """
    SELECT 
        e.entry_date AS "Date",
        e.cart_name AS "Cart",
        e.total_collection AS "Total_Collection",
        e.phonepe AS "PhonePe",
        e.cash AS "Cash",
        e.staff_name AS "Staff_Name",
        e.staff_advance AS "Staff_Advance",
        e.food_tea_cash AS "Food_Tea_Cash",
        e.remarks AS "Remarks",
        COALESCE(SUM(i.sold_units), 0) AS "Sold_Total",
        COALESCE(SUM(i.closing_units), 0) AS "Closing_Total"
    FROM daily_cart_entries e
    LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
    GROUP BY e.id, e.entry_date, e.cart_name, e.total_collection, e.phonepe, e.cash, e.staff_name, e.staff_advance, e.food_tea_cash, e.remarks
    ORDER BY e.entry_date DESC;
    """
    df = db_conn.query(query, ttl="0s")
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_db_flavor_sales(start_date=None, end_date=None):
    if db_conn is None:
        return pd.DataFrame()
    where_clauses = []
    params = {}
    if start_date:
        where_clauses.append("e.entry_date >= :sdate")
        params["sdate"] = start_date
    if end_date:
        where_clauses.append("e.entry_date <= :edate")
        params["edate"] = end_date
        
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    query = f"""
    SELECT 
        f.code,
        f.name AS "Flavour",
        f.mrp,
        COALESCE(SUM(i.sold_units), 0) AS "Units sold",
        COALESCE(SUM(i.sold_units), 0) * f.mrp AS "Est. revenue (₹)"
    FROM flavors f
    LEFT JOIN daily_cart_items i ON f.code = i.flavor_code
    LEFT JOIN daily_cart_entries e ON i.daily_entry_id = e.id {where_sql}
    GROUP BY f.code, f.name, f.mrp
    ORDER BY "Units sold" DESC;
    """
    return db_conn.query(query, params=params, ttl="0s")


def load_db_expenses_list():
    if db_conn is None:
        return []
    query = """
    SELECT 
        id,
        expense_date AS "Date",
        description AS "Description",
        amount AS "Amount",
        category AS "Category",
        payment_mode AS "Mode",
        ref_no AS "Ref No",
        paid_to AS "Paid To",
        remarks AS "Remarks"
    FROM expenses
    ORDER BY expense_date DESC, id DESC;
    """
    df = db_conn.query(query, ttl="0s")
    if df.empty:
        return []
    df["Date"] = pd.to_datetime(df["Date"])
    df["Amount"] = df["Amount"].astype(float)
    return df.to_dict("records")


def get_db_stock_removed_map():
    """Returns a dictionary of cumulative stock removed per flavor code."""
    if db_conn is None:
        return {code: 0 for code in FLAVOR_CODES}
    try:
        df = db_conn.query("""
            SELECT 
                COALESCE(SUM(ml_units), 0) AS ml_units,
                COALESCE(SUM(mm_units), 0) AS mm_units,
                COALESCE(SUM(ps_units), 0) AS ps_units,
                COALESCE(SUM(mn_units), 0) AS mn_units,
                COALESCE(SUM(kb_units), 0) AS kb_units,
                COALESCE(SUM(bm_units), 0) AS bm_units,
                COALESCE(SUM(sg_units), 0) AS sg_units,
                COALESCE(SUM(ch_units), 0) AS ch_units,
                COALESCE(SUM(ra_units), 0) AS ra_units
            FROM stock_removed;
        """, ttl="0s")
        if not df.empty:
            r = df.iloc[0]
            return {code: int(r.get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES}
    except Exception:
        pass
    return {code: 0 for code in FLAVOR_CODES}


def get_db_freezer_stock():
    """
    Computes live available units in the freezer:
    Units in Freezer = Received (Inward) - Issued (Carts) - Stock Removed (Wastage / Returns)
    """
    if db_conn is None:
        return pd.DataFrame()
    try:
        recv_df = db_conn.query("SELECT flavor_code, COALESCE(SUM(received_units), 0) AS total_recv FROM stock_received_items GROUP BY flavor_code;", ttl="0s")
        rec_map = dict(zip(recv_df["flavor_code"], recv_df["total_recv"])) if not recv_df.empty else {}

        added_df = db_conn.query("SELECT flavor_code, COALESCE(SUM(added_units), 0) AS total_added FROM daily_cart_items GROUP BY flavor_code;", ttl="0s")
        added_map = dict(zip(added_df["flavor_code"], added_df["total_added"])) if not added_df.empty else {}

        rem_map = get_db_stock_removed_map()

        rows = []
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            in_u = int(rec_map.get(code, 0))
            out_u = int(added_map.get(code, 0))
            rem_u = int(rem_map.get(code, 0))
            curr_freezer = in_u - out_u - rem_u

            rows.append({
                "code": code,
                "Flavour": f_info["name"],
                "mrp": float(f_info["mrp"]),
                "cost_price": float(f_info["cost_price"]),
                "Units in freezer": curr_freezer
            })
        return pd.DataFrame(rows).sort_values(by=["mrp", "Flavour"], ascending=[True, True])
    except Exception:
        return pd.DataFrame()


# ----------------------------------------------------------------------
# AUTHENTICATION
# ----------------------------------------------------------------------
def check_login():
    if st.session_state.get("authenticated", False):
        return True

    _, col_form, _ = st.columns([1, 1.2, 1])

    with col_form:
        try:
            st.image("assets/logo.png", width=220)
        except Exception:
            st.title("🍦 Kulfi Ops")

        st.subheader("Sign in")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)

        if submitted:
            user_clean = str(username).strip()
            pass_clean = str(password).strip()

            admin_user = str(st.secrets.get("app_username", "admin")).strip()
            admin_pass = str(st.secrets.get("app_password", "")).strip()

            entry_user = str(st.secrets.get("entry_username", "entry")).strip()
            entry_pass = str(st.secrets.get("entry_password", "")).strip()

            if admin_pass and hmac.compare_digest(user_clean, admin_user) and hmac.compare_digest(pass_clean, admin_pass):
                st.session_state["authenticated"] = True
                st.session_state["user_role"] = "admin"
                st.rerun()
            elif entry_pass and hmac.compare_digest(user_clean, entry_user) and hmac.compare_digest(pass_clean, entry_pass):
                st.session_state["authenticated"] = True
                st.session_state["user_role"] = "entry"
                st.rerun()
            else:
                st.error("Incorrect username or password — try again.")

    return False


if not check_login():
    st.stop()

# ----------------------------------------------------------------------
# NAVIGATION
# ----------------------------------------------------------------------
user_role = st.session_state.get("user_role", "admin")

with st.sidebar:
    try:
        st.image("assets/logo.png", use_container_width=True)
    except Exception:
        st.markdown("## 🍦 Kulfi Ops")

    if user_role == "admin":
        nav_options = ["Dashboard", "Daily Entry", "Purchase Orders", "Freezer Stock", "Freezer Analysis", "Stock Removed", "Expenses"]
        page = st.radio("Go to", nav_options, label_visibility="collapsed")
    else:
        page = "Daily Entry"
        st.info("Logged in as Data Entry Staff")

    st.markdown("---")
    if st.button("Log out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["user_role"] = None
        st.rerun()

st.title(f"🍦 Kulfi Ops — {page}")

# ======================================================================
# PAGE 1: DAILY ENTRY (Mobile Flavor Cards + DB Lookup + 0 Sales Allowed)
# ======================================================================
if page == "Daily Entry":
    st.subheader("Cart restock & daily sales")

    try:
        daily_entries = list_daily_entries_with_prefill()
    except Exception as e:
        daily_entries = []
        st.warning(f"Could not load entries from database ({e}).")

    if user_role == "entry" and daily_entries:
        today_val = date.today()
        allowed_dates = {
            today_val - timedelta(days=1),
            today_val - timedelta(days=2),
            today_val - timedelta(days=3),
        }
        daily_entries = [e for e in daily_entries if e["date"].date() in allowed_dates]

    if not daily_entries:
        st.info("No entries found in database for the active period.")
    else:
        top_c1, top_c2 = st.columns([1.3, 1])

        labels = [f"{e['date'].strftime('%d %b %Y')} — {e['cart']}" for e in daily_entries]
        with top_c1:
            sel = st.selectbox("Select entry to update sales", labels, key="daily_update_select")
        loaded = daily_entries[labels.index(sel)]
        entry_id = loaded["db_id"]
        entry_date = loaded["date"].date()
        cart_name = loaded["cart"]

        data_key_suffix = f"_{entry_id}"

        k_tot = f"daily_total{data_key_suffix}"
        k_ph = f"daily_phonepe{data_key_suffix}"
        k_cs = f"daily_cash{data_key_suffix}"
        k_adv = f"daily_adv{data_key_suffix}"
        k_food = f"daily_food{data_key_suffix}"
        k_staff = f"daily_staff{data_key_suffix}"
        k_prev_calc = f"daily_prev_calc{data_key_suffix}"

        staff_options = load_active_staff_list()

        default_staff_name = loaded.get("staff_name", "")
        if default_staff_name and default_staff_name not in staff_options:
            staff_options.append(default_staff_name)

        default_staff_idx = staff_options.index(default_staff_name) if default_staff_name in staff_options else 0
        with top_c2:
            staff_name = st.selectbox("Cart staff name", staff_options, index=default_staff_idx, key=k_staff)

        st.write("Enter units **added to the cart** and the **actual closing count** observed:")

        added_map = {}
        closing_map = {}
        sold_map = {}
        opening_map = {code: loaded["by_code"][code]["opening"] for code in FLAVOR_CODES}

        # Mobile Card View Loop with live Sold calculations
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            k_add = f"add_{entry_id}_{code}"
            k_cls = f"cls_{entry_id}_{code}"

            if k_add not in st.session_state:
                st.session_state[k_add] = loaded["by_code"][code]["added"]
            if k_cls not in st.session_state:
                st.session_state[k_cls] = loaded["by_code"][code]["closing"]

            cur_open = opening_map[code]
            cur_add = _int_num(st.session_state[k_add])
            cur_cls = _int_num(st.session_state[k_cls])
            cur_sold = cur_open + cur_add - cur_cls

            added_map[code] = cur_add
            closing_map[code] = cur_cls
            sold_map[code] = cur_sold

            st.markdown(
                f"""
                <div class="flavor-entry-row">
                    <div class="flavor-title-bar">
                        <span class="flavor-name">{f_info['name']} (₹{f_info['mrp']:.0f})</span>
                        <div>
                            <span class="badge-open">Opening: {cur_open}</span>
                            <span class="badge-sold">Sold: {cur_sold}</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_a, col_b = st.columns(2)
            with col_a:
                st.number_input("+ Added Stock", min_value=0, step=1, format="%d", key=k_add)
            with col_b:
                st.number_input("Closing Count", min_value=0, step=1, format="%d", key=k_cls)

        tot_open = sum(opening_map.values())
        tot_add = sum(added_map.values())
        tot_close = sum(closing_map.values())
        tot_sold = sum(sold_map.values())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Opening Balance", f"{tot_open} units")
        m2.metric("Stock Added", f"{tot_add} units")
        m3.metric("Closing Balance", f"{tot_close} units")
        m4.metric("Total Sold", f"{tot_sold} units")

        if any(s < 0 for s in sold_map.values()):
            st.error("Today's sales works out negative for at least one flavour - closing count is higher than opening + added.")

        calculated_mrp_total = float(sum(sold_map[code] * FLAVOR_MAP[code]["mrp"] for code in FLAVOR_CODES))

        if k_tot not in st.session_state or st.session_state.get(k_prev_calc) != calculated_mrp_total:
            default_tot = loaded["total"] if (loaded["total"] > 0 and not loaded.get("is_prefill", False)) else calculated_mrp_total
            st.session_state[k_tot] = f"{default_tot:.2f}"
            st.session_state[k_prev_calc] = calculated_mrp_total

        if k_ph not in st.session_state:
            st.session_state[k_ph] = f"{loaded['phonepe']:.2f}"

        if k_adv not in st.session_state:
            st.session_state[k_adv] = f"{loaded['staff_advance']:.2f}" if "staff_advance" in loaded else "0.00"

        if k_food not in st.session_state:
            st.session_state[k_food] = f"{loaded['food_tea_cash']:.2f}" if "food_tea_cash" in loaded else "0.00"

        if k_cs not in st.session_state:
            st.session_state[k_cs] = f"{loaded['cash']:.2f}"

        st.markdown("---")
        st.write("**Today's collection & Cash Breakdown**")

        c3, c4 = st.columns(2)
        with c3:
            total_collection_str = st.text_input("Total collection (₹)", key=k_tot)
            staff_advance_str = st.text_input("Advance to staff (₹)", key=k_adv)
            food_tea_str = st.text_input("Cash paid for Food / Tea (₹)", key=k_food)
        with c4:
            phonepe_str = st.text_input("PhonePe / UPI (₹)", key=k_ph)
            cash_str = st.text_input("Cash Collected (₹)", key=k_cs)

        total_collection_val = _num(total_collection_str)
        phonepe_val = _num(phonepe_str)
        staff_advance_val = _num(staff_advance_str)
        food_tea_val = _num(food_tea_str)
        cash_val = _num(cash_str)

        cash_leakage = total_collection_val - phonepe_val - staff_advance_val - food_tea_val - cash_val
        has_leakage = cash_leakage > 0.001

        if has_leakage:
            st.markdown(
                f"<div style='margin-top:2px;'><label style='font-size:12px; font-weight:700;'>Cash Leakage:</label> "
                f"<b style='color:#C41C1C; font-size:16px;'>₹{cash_leakage:,.2f}</b></div>"
                '<p style="color:#C41C1C; font-weight:bold; font-size:13px; margin: 4px 0 !important;">'
                '⚠️ There is a cash leakage - please correct or enter reason in remarks field'
                '</p>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f"<div style='margin-top:2px;'><label style='font-size:12px; font-weight:700;'>Cash Leakage:</label> "
                f"<b style='color:#2A1B10; font-size:14px;'>₹{cash_leakage:,.2f}</b></div>",
                unsafe_allow_html=True
            )

        remarks = st.text_input("Remarks", value=loaded["remarks"], key=f"daily_remarks{data_key_suffix}", placeholder="Enter remarks (mandatory if cash leakage)...")

        if st.button("Update sales", type="primary", use_container_width=True):
            if any(s < 0 for s in sold_map.values()):
                st.error("Today's sales works out negative for at least one flavour - fix closing count before saving.")
            elif has_leakage and not remarks.strip():
                st.error("Remarks is mandatory when there is a cash leakage. Please enter a reason.")
            else:
                try:
                    selected_staff = "" if staff_name == "Select Staff" else staff_name
                    sync_daily_entry(
                        entry_date, cart_name, added_map, closing_map, opening_map, sold_map, 
                        total_collection_val, phonepe_val, cash_val, remarks, selected_staff, staff_advance_val, food_tea_val
                    )
                    st.cache_resource.clear()
                    show_success_modal(f"Saved successfully to Database & Sheets! Sales updated for {cart_name} on {entry_date.strftime('%d %b %Y')}. Total Sold: {tot_sold} units.")
                except Exception as e:
                    st.error(f"Could not save - {e}")

# ======================================================================
# PAGE 2: PURCHASE ORDERS (Estimator, Dynamic Discount & Order Editing)
# ======================================================================
elif page == "Purchase Orders" and user_role == "admin":
    st.subheader("Purchase Order Estimator & Order Management")
    st.caption("Plan order quantities, apply overall discounts, calculate net payable cost, and manage orders.")

    po_mode = st.radio("Mode", ["Create New Order", "Edit / Track Existing Orders"], horizontal=True, key="po_screen_mode")

    if po_mode == "Create New Order":
        st.write("Enter details and specify quantities per flavor to calculate the estimated purchase cost.")

        c1, c2, c3 = st.columns(3)
        with c1:
            order_date = st.date_input("Order Date", value=date.today(), key="new_po_order_date")
        with c2:
            expected_date = st.date_input("Expected Delivery Date", value=date.today() + timedelta(days=2), key="new_po_exp_date")
        with c3:
            location = st.text_input("Delivery Location", value=CITY, key="new_po_loc")

        c4, c5 = st.columns(2)
        with c4:
            order_status = st.selectbox("Order Status", PO_STATUSES, index=0, key="new_po_status")
        with c5:
            discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="new_po_discount")

        grid_rows = []
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            grid_rows.append({
                "Flavour": f_info["name"],
                "Code": code,
                "Unit Cost (₹)": float(f_info["cost_price"]),
                "Order Quantity": 0
            })

        st.write("Enter order quantities per flavour:")
        po_editor_df = st.data_editor(
            pd.DataFrame(grid_rows),
            column_config={
                "Flavour": st.column_config.TextColumn(disabled=True),
                "Code": st.column_config.TextColumn(disabled=True),
                "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
                "Order Quantity": st.column_config.NumberColumn(min_value=0, step=10, format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            key="new_po_editor"
        )

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
            if total_units <= 0:
                st.error("Please enter a quantity greater than 0 for at least one flavour before placing the order.")
            else:
                try:
                    combined_notes = po_notes.strip()
                    if discount_pct > 0:
                        combined_notes = f"[Discount: {discount_pct:.2f}% | Final: ₹{final_amount:,.2f}] {combined_notes}".strip()

                    with db_conn.session as s:
                        res = s.execute(
                            text("""
                            INSERT INTO purchase_orders (order_date, expected_date, location, order_status, notes)
                            VALUES (:od, :ed, :loc, :stat, :notes)
                            RETURNING id;
                            """),
                            {"od": order_date, "ed": expected_date, "loc": location, "stat": order_status, "notes": combined_notes}
                        )
                        new_poid = res.scalar()

                        for _, row in po_editor_df.iterrows():
                            qty = int(row["Order Quantity"])
                            if qty > 0:
                                s.execute(
                                    text("""
                                    INSERT INTO purchase_order_items (order_id, flavor_code, ordered_units)
                                    VALUES (:poid, :code, :qty);
                                    """),
                                    {"poid": new_poid, "code": row["Code"], "qty": qty}
                                )
                        s.commit()
                    show_success_modal(f"Purchase Order #{new_poid} created successfully! Total: {total_units} units | Final Amount: ₹{final_amount:,.2f} ({discount_pct:.1f}% off).")
                except Exception as e:
                    st.error(f"Could not save purchase order to database: {e}")

    elif po_mode == "Edit / Track Existing Orders":
        po_query_df = db_conn.query("""
            SELECT p.id, p.order_date, p.expected_date, p.location, p.order_status, p.notes,
                   json_agg(json_build_object('code', pi.flavor_code, 'qty', pi.ordered_units)) AS items
            FROM purchase_orders p
            LEFT JOIN purchase_order_items pi ON p.id = pi.order_id
            GROUP BY p.id ORDER BY p.order_date DESC, p.id DESC;
        """, ttl="0s")

        if po_query_df.empty:
            st.info("No purchase orders found in the database.")
        else:
            po_records = po_query_df.to_dict("records")
            po_labels = [
                f"PO #{r['id']} — {pd.to_datetime(r['order_date']).strftime('%d %b %Y')} ({r['location']}) — Status: {r['order_status']}"
                for r in po_records
            ]
            selected_po_label = st.selectbox("Select Purchase Order to edit", po_labels, key="edit_po_select")
            loaded_po = po_records[po_labels.index(selected_po_label)]
            loaded_po_id = loaded_po["id"]

            existing_notes = str(loaded_po.get("notes") or "")
            default_disc = 0.0
            clean_notes = existing_notes
            disc_match = re.search(r"\[Discount:\s*([\d.]+)%[^\]]*\]", existing_notes)
            if disc_match:
                try:
                    default_disc = float(re.search(r"([\d.]+)", disc_match.group(0)).group(1))
                    clean_notes = re.sub(r"\[Discount:[^\]]*\]\s*", "", existing_notes).strip()
                except Exception:
                    default_disc = 0.0

            c1, c2, c3 = st.columns(3)
            with c1:
                e_order_date = st.date_input(
                    "Order Date", 
                    value=pd.to_datetime(loaded_po["order_date"]).date() if loaded_po.get("order_date") else date.today(),
                    key=f"edit_po_od_{loaded_po_id}"
                )
            with c2:
                e_expected_date = st.date_input(
                    "Expected Delivery Date", 
                    value=pd.to_datetime(loaded_po["expected_date"]).date() if loaded_po.get("expected_date") else date.today() + timedelta(days=2),
                    key=f"edit_po_ed_{loaded_po_id}"
                )
            with c3:
                e_location = st.text_input("Delivery Location", value=str(loaded_po.get("location", CITY)), key=f"edit_po_loc_{loaded_po_id}")

            c4, c5 = st.columns(2)
            with c4:
                curr_status = loaded_po.get("order_status", "Placed")
                def_stat_idx = PO_STATUSES.index(curr_status) if curr_status in PO_STATUSES else 0
                e_status = st.selectbox("Order Status", PO_STATUSES, index=def_stat_idx, key=f"edit_po_stat_{loaded_po_id}")
            with c5:
                e_discount_pct = st.number_input(
                    "Overall Discount (%)", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=default_disc, 
                    step=0.5, 
                    format="%.2f", 
                    key=f"edit_po_disc_{loaded_po_id}"
                )

            items_by_code = {}
            if loaded_po.get("items") and isinstance(loaded_po["items"], list):
                for itm in loaded_po["items"]:
                    if isinstance(itm, dict) and "code" in itm:
                        items_by_code[itm["code"]] = itm.get("qty", 0)

            edit_grid_rows = []
            for code in FLAVOR_CODES:
                f_info = FLAVOR_MAP[code]
                edit_grid_rows.append({
                    "Flavour": f_info["name"],
                    "Code": code,
                    "Unit Cost (₹)": float(f_info["cost_price"]),
                    "Order Quantity": int(items_by_code.get(code) or 0)
                })

            st.write("Modify order quantities per flavour:")
            po_edit_editor_df = st.data_editor(
                pd.DataFrame(edit_grid_rows),
                column_config={
                    "Flavour": st.column_config.TextColumn(disabled=True),
                    "Code": st.column_config.TextColumn(disabled=True),
                    "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
                    "Order Quantity": st.column_config.NumberColumn(min_value=0, step=10, format="%d"),
                },
                hide_index=True,
                use_container_width=True,
                key=f"edit_po_editor_{loaded_po_id}"
            )

            e_total_units = int(po_edit_editor_df["Order Quantity"].sum())
            e_gross_cost = float(sum(po_edit_editor_df["Order Quantity"] * po_edit_editor_df["Unit Cost (₹)"]))
            e_discount_amount = e_gross_cost * (e_discount_pct / 100.0)
            e_final_amount = e_gross_cost - e_discount_amount

            st.markdown("#### Updated Order Summary")
            em1, em2, em3, em4 = st.columns(4)
            em1.metric("Total Ordered Units", f"{e_total_units} units")
            em2.metric("Gross Cost", f"₹{e_gross_cost:,.2f}")
            em3.metric(f"Discount ({e_discount_pct:.1f}%)", f"-₹{e_discount_amount:,.2f}")
            em4.metric("Final Amount to Pay", f"₹{e_final_amount:,.2f}")

            e_notes = st.text_input("Order Notes", value=clean_notes, key=f"edit_po_notes_{loaded_po_id}")

            if st.button("💾 Update Purchase Order", type="primary", use_container_width=True):
                if e_total_units <= 0:
                    st.error("Please specify at least one quantity for the order.")
                else:
                    try:
                        combined_edit_notes = e_notes.strip()
                        if e_discount_pct > 0:
                            combined_edit_notes = f"[Discount: {e_discount_pct:.2f}% | Final: ₹{e_final_amount:,.2f}] {combined_edit_notes}".strip()

                        with db_conn.session as s:
                            s.execute(
                                text("""
                                UPDATE purchase_orders
                                SET order_date = :od, expected_date = :ed, location = :loc, order_status = :stat, notes = :notes
                                WHERE id = :id;
                                """),
                                {"od": e_order_date, "ed": e_expected_date, "loc": e_location, "stat": e_status, "notes": combined_edit_notes, "id": loaded_po_id}
                            )
                            s.execute(text("DELETE FROM purchase_order_items WHERE order_id = :id;"), {"id": loaded_po_id})

                            for _, row in po_edit_editor_df.iterrows():
                                qty = int(row["Order Quantity"])
                                if qty > 0:
                                    s.execute(
                                        text("""
                                        INSERT INTO purchase_order_items (order_id, flavor_code, ordered_units)
                                        VALUES (:poid, :code, :qty);
                                        """),
                                        {"poid": loaded_po_id, "code": row["Code"], "qty": qty}
                                    )
                            s.commit()
                        show_success_modal(f"Purchase Order #{loaded_po_id} updated successfully! Final Amount: ₹{e_final_amount:,.2f}.")
                    except Exception as e:
                        st.error(f"Could not update purchase order: {e}")

# ======================================================================
# PAGE 3: FREEZER STOCK (100% Database Powered)
# ======================================================================
elif page == "Freezer Stock" and user_role == "admin":
    st.subheader("Freezer Stock Management")
    st.caption("All entries are persisted directly to PostgreSQL as the single source of truth.")

    freezer_tab_choice = st.radio("Section", ["Stock Received (Inward)", "Stock Audit (Physical Count)"], horizontal=True)

    if freezer_tab_choice == "Stock Received (Inward)":
        stock_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="db_stock_mode")

        past_receipts_df = db_conn.query("""
            SELECT r.id, r.received_date, r.location, r.purchase_order_id, r.payment_amount,
                   r.payment_status, r.payment_date, r.payment_details, r.damaged_returned_on, r.notes,
                   json_agg(json_build_object('code', i.flavor_code, 'rec', i.received_units, 'dam', i.damaged_units, 'cost', i.unit_cost_price)) AS items
            FROM stock_received r
            LEFT JOIN stock_received_items i ON r.id = i.received_id
            GROUP BY r.id ORDER BY r.received_date DESC, r.id DESC;
        """, ttl="0s")

        past_receipts = past_receipts_df.to_dict("records") if not past_receipts_df.empty else []

        stock_loaded = None
        loaded_id = None
        if stock_mode == "Edit past entry":
            if not past_receipts:
                st.info("No past delivery receipts found in database.")
            else:
                labels = [f"Receipt #{r['id']} — {pd.to_datetime(r['received_date']).strftime('%d %b %Y')} ({r['location']})" for r in past_receipts]
                selected_rec = st.selectbox("Select delivery receipt to edit", labels, key="db_stock_select")
                stock_loaded = past_receipts[labels.index(selected_rec)]
                loaded_id = stock_loaded["id"]

        sk = f"_{loaded_id}" if loaded_id else "_new"

        pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders WHERE order_status != 'Completed' ORDER BY order_date DESC;", ttl="0s")
        po_options = ["None (Ad-hoc delivery)"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d %b')})" for _, r in pos_df.iterrows()]
        
        default_po_idx = 0
        poid_raw = stock_loaded.get("purchase_order_id") if stock_loaded else None
        if poid_raw is not None and pd.notna(poid_raw) and str(poid_raw).strip() != "":
            try:
                poid_int = int(float(poid_raw))
                for idx, opt in enumerate(po_options):
                    if opt.startswith(f"PO #{poid_int} "):
                        default_po_idx = idx
                        break
            except Exception:
                default_po_idx = 0

        c1, c2, c3 = st.columns(3)
        with c1:
            rec_default_date = pd.to_datetime(stock_loaded["received_date"]).date() if (stock_loaded and stock_loaded.get("received_date")) else date.today()
            received_date = st.date_input("Received date", value=rec_default_date, key=f"rec_date{sk}")
        with c2:
            loc_default = str(stock_loaded["location"]) if (stock_loaded and stock_loaded.get("location")) else CITY
            location = st.text_input("Location", value=loc_default, key=f"rec_loc{sk}")
        with c3:
            selected_po = st.selectbox("Link to Purchase Order (Optional)", po_options, index=default_po_idx, key=f"rec_po{sk}")

        items_map = {}
        if stock_loaded and stock_loaded.get("items") and isinstance(stock_loaded["items"], list):
            for itm in stock_loaded["items"]:
                if isinstance(itm, dict) and "code" in itm:
                    items_map[itm["code"]] = itm

        grid_rows = []
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            rec_units = items_map[code]["rec"] if (code in items_map and items_map[code].get("rec") is not None) else 0
            dam_units = items_map[code]["dam"] if (code in items_map and items_map[code].get("dam") is not None) else 0
            grid_rows.append({
                "Flavour": f_info["name"],
                "Code": code,
                "Unit Cost Price (₹)": float(f_info["cost_price"]),
                "Received": int(rec_units),
                "Damaged": int(dam_units),
            })

        st.write("Enter units received per flavour:")
        stock_edited = st.data_editor(
            pd.DataFrame(grid_rows),
            column_config={
                "Flavour": st.column_config.TextColumn(disabled=True),
                "Code": st.column_config.TextColumn(disabled=True),
                "Unit Cost Price (₹)": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
                "Received": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
                "Damaged": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            key=f"db_stock_editor{sk}",
        )

        tot_received = int(stock_edited["Received"].sum())
        tot_damaged = int(stock_edited["Damaged"].sum())
        tot_cost_val = float(sum(stock_edited["Received"] * stock_edited["Unit Cost Price (₹)"]))

        st.markdown("#### Entry Summary")
        s_col1, s_col2, s_col3 = st.columns(3)
        s_col1.metric("Total Received", f"{tot_received} units")
        s_col2.metric("Total Damaged", f"{tot_damaged} units")
        s_col3.metric("Total Cost of Goods", f"₹{tot_cost_val:,.2f}")

        st.markdown("---")
        st.write("**Payment & Logistics**")
        c4, c5 = st.columns(2)
        with c4:
            default_payment = float(stock_loaded["payment_amount"]) if (stock_loaded and stock_loaded.get("payment_amount") is not None) else float(tot_cost_val)
            payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=default_payment, step=10.0, key=f"db_rec_pay{sk}")
        with c5:
            def_stat = stock_loaded["payment_status"] if (stock_loaded and stock_loaded.get("payment_status") in PAYMENT_STATUSES) else "Pending"
            payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(def_stat), key=f"db_rec_status{sk}")

        has_payment_date = st.checkbox(
            "Add payment date", 
            value=bool(stock_loaded and stock_loaded.get("payment_date")), 
            key=f"db_rec_has_pdate{sk}",
        )
        payment_date = (
            st.date_input(
                "Payment date", 
                value=(pd.to_datetime(stock_loaded["payment_date"]).date() if (stock_loaded and stock_loaded.get("payment_date")) else date.today()), 
                key=f"db_rec_pdate{sk}",
            ) 
            if has_payment_date else None
        )
        payment_details = st.text_input(
            "Payment details (optional)", 
            value=(str(stock_loaded["payment_details"]) if (stock_loaded and stock_loaded.get("payment_details")) else ""), 
            key=f"db_rec_pdet{sk}",
        )

        has_dam_ret = st.checkbox(
            "Damaged items were returned", 
            value=bool(stock_loaded and stock_loaded.get("damaged_returned_on")), 
            key=f"db_rec_has_dam{sk}",
        )
        damaged_returned_on = (
            st.date_input(
                "Damaged returned date", 
                value=(pd.to_datetime(stock_loaded["damaged_returned_on"]).date() if (stock_loaded and stock_loaded.get("damaged_returned_on")) else date.today()), 
                key=f"db_rec_damdate{sk}",
            ) 
            if has_dam_ret else None
        )

        notes = st.text_input(
            "Notes (optional)", 
            value=(str(stock_loaded["notes"]) if (stock_loaded and stock_loaded.get("notes")) else ""), 
            key=f"db_rec_notes{sk}",
        )

        btn_label = "Update delivery entry" if loaded_id else "Save stock received"
        if st.button(btn_label, type="primary", use_container_width=True):
            if tot_received == 0:
                st.error("Enter at least one quantity received before saving.")
            else:
                po_id = int(selected_po.split("#")[1].split(" ")[0]) if "PO #" in selected_po else None
                try:
                    with db_conn.session as s:
                        if loaded_id:
                            s.execute(
                                text("""
                                UPDATE stock_received
                                SET received_date = :rd, location = :loc, purchase_order_id = :poid,
                                    payment_amount = :amt, payment_status = :stat, payment_date = :pdate,
                                    payment_details = :pdet, damaged_returned_on = :dret, notes = :notes
                                WHERE id = :id;
                                """),
                                {
                                    "rd": received_date, "loc": location, "poid": po_id, "amt": payment_amount,
                                    "stat": payment_status, "pdate": payment_date, "pdet": payment_details,
                                    "dret": damaged_returned_on, "notes": notes, "id": loaded_id
                                }
                            )
                            s.execute(text("DELETE FROM stock_received_items WHERE received_id = :id;"), {"id": loaded_id})
                            rec_id = loaded_id
                        else:
                            res = s.execute(
                                text("""
                                INSERT INTO stock_received (received_date, location, purchase_order_id, payment_amount, payment_status, payment_date, payment_details, damaged_returned_on, notes)
                                VALUES (:rd, :loc, :poid, :amt, :stat, :pdate, :pdet, :dret, :notes)
                                RETURNING id;
                                """),
                                {
                                    "rd": received_date, "loc": location, "poid": po_id, "amt": payment_amount,
                                    "stat": payment_status, "pdate": payment_date, "pdet": payment_details,
                                    "dret": damaged_returned_on, "notes": notes
                                }
                            )
                            rec_id = res.scalar()

                        for _, row in stock_edited.iterrows():
                            if int(row["Received"]) > 0 or int(row["Damaged"]) > 0:
                                s.execute(
                                    text("""
                                    INSERT INTO stock_received_items (received_id, flavor_code, received_units, damaged_units, unit_cost_price)
                                    VALUES (:rid, :code, :rec, :dam, :cost);
                                    """),
                                    {"rid": rec_id, "code": row["Code"], "rec": int(row["Received"]), "dam": int(row["Damaged"]), "cost": float(row["Unit Cost Price (₹)"])}
                                )
                        s.commit()
                    show_success_modal(f"Stock delivery #{rec_id} saved successfully! Logged {tot_received} units into freezer.")
                except Exception as e:
                    st.error(f"Could not save to database: {e}")

    elif freezer_tab_choice == "Stock Audit (Physical Count)":
        st.write("Log a physical stock count from the freezer to calculate inventory variance.")
        
        aud_c1, aud_c2, aud_c3 = st.columns(3)
        with aud_c1:
            audit_date = st.date_input("Audit date", value=date.today(), key="audit_dt_entry")
        with aud_c2:
            audit_location = st.text_input("Freezer / Location", value=CITY, key="audit_loc_entry")
        with aud_c3:
            audited_by = st.text_input("Audited by", value="Admin", key="audit_by_entry")

        freezer_curr_df = get_db_freezer_stock()
        sys_stock_map = dict(zip(freezer_curr_df["code"], freezer_curr_df["Units in freezer"])) if not freezer_curr_df.empty else {}

        audit_grid = []
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            audit_grid.append({
                "Flavour": f_info["name"],
                "Code": code,
                "Current System Stock": int(sys_stock_map.get(code, 0)),
                "Physical Counted Units": int(sys_stock_map.get(code, 0)),
            })

        audit_edited = st.data_editor(
            pd.DataFrame(audit_grid),
            column_config={
                "Flavour": st.column_config.TextColumn(disabled=True),
                "Code": st.column_config.TextColumn(disabled=True),
                "Current System Stock": st.column_config.NumberColumn(disabled=True, format="%d"),
                "Physical Counted Units": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            key="audit_editor_grid",
        )

        audit_remarks = st.text_input("Audit remarks / observation notes", key="audit_remarks_input")

        if st.button("Save stock audit", type="primary", use_container_width=True):
            try:
                phys_by_code = {row["Code"]: int(row["Physical Counted Units"]) for _, row in audit_edited.iterrows()}
                with db_conn.session as s:
                    res = s.execute(
                        text("""
                        INSERT INTO stock_audits_wide (audit_date, location, audited_by, remarks,
                                                      ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units)
                        VALUES (:adt, :loc, :by, :rem,
                                :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra)
                        RETURNING audit_id;
                        """),
                        {
                            "adt": audit_date, "loc": audit_location, "by": audited_by, "rem": audit_remarks,
                            "ml": phys_by_code.get("ML", 0), "mm": phys_by_code.get("MM", 0), "ps": phys_by_code.get("PS", 0),
                            "mn": phys_by_code.get("MN", 0), "kb": phys_by_code.get("KB", 0), "bm": phys_by_code.get("BM", 0),
                            "sg": phys_by_code.get("SG", 0), "ch": phys_by_code.get("CH", 0), "ra": phys_by_code.get("RA", 0),
                        }
                    )
                    aid = res.scalar()
                    s.commit()
                show_success_modal(f"Stock Audit #{aid} logged successfully into PostgreSQL!")
            except Exception as e:
                st.error(f"Could not save audit to database: {e}")

# ======================================================================
# PAGE 4: FREEZER ANALYSIS (Single-View Compact, Orders from Calc Stock)
# ======================================================================
elif page == "Freezer Analysis" and user_role == "admin":
    st.subheader("Freezer Stock Analysis & Reorder Planner")
    st.caption("Live comparison of Physical Audit vs Calculated Stock with velocity-based reorder recommendations.")

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        lookback_days = st.number_input("Sales Velocity Window (days)", min_value=3, max_value=90, value=14, step=1)
    with ac2:
        buffer_days = st.number_input("Safety Buffer Threshold (days)", min_value=0, max_value=14, value=3, step=1)
    with ac3:
        cover_days = st.number_input("Reorder Coverage Target (days)", min_value=1, max_value=30, value=7, step=1)

    try:
        today_fa = date.today()
        cutoff_fa = today_fa - timedelta(days=int(lookback_days) - 1)
        flavor_sales_df = load_db_flavor_sales(start_date=cutoff_fa, end_date=today_fa)
        sales_pace_map = dict(zip(flavor_sales_df["code"], flavor_sales_df["Units sold"])) if not flavor_sales_df.empty else {}

        # Inward Received
        rec_df = db_conn.query("SELECT flavor_code, SUM(received_units) AS total_recv FROM stock_received_items GROUP BY flavor_code;", ttl="0s")
        rec_map = dict(zip(rec_df["flavor_code"], rec_df["total_recv"])) if not rec_df.empty else {}

        # Outward Cart Additions
        added_df = db_conn.query("SELECT flavor_code, SUM(added_units) AS total_added FROM daily_cart_items GROUP BY flavor_code;", ttl="0s")
        added_map = dict(zip(added_df["flavor_code"], added_df["total_added"])) if not added_df.empty else {}

        # Stock Removed (Wastage / Returns / Samples)
        rem_map = get_db_stock_removed_map()

        # Latest Physical Audit from stock_audits_wide
        latest_audit_df = db_conn.query("""
            SELECT * FROM stock_audits_wide
            ORDER BY audit_date DESC, audit_id DESC
            LIMIT 1;
        """, ttl="0s")
        
        if not latest_audit_df.empty:
            audit_row = latest_audit_df.iloc[0]
            audit_map = {code: int(audit_row.get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES}
            audit_date_str = pd.to_datetime(audit_row["audit_date"]).strftime("%d %b %Y")
        else:
            audit_map = {}
            audit_date_str = "No audits logged"
    except Exception as e:
        st.error(f"Could not load analysis transactions from database: {e}")
        sales_pace_map, rec_map, added_map, rem_map, audit_map = {}, {}, {}, {}, {}
        audit_date_str = "N/A"

    # --- SECTION 1: STOCK RECONCILIATION & TOTALS ---
    st.markdown("---")
    st.markdown(f"### 1. Physical Stock vs Calculated Freezer Stock &nbsp; *(Latest Audit: {audit_date_str})*")

    comparison_rows = []
    tot_rec, tot_issued, tot_removed, tot_calc, tot_phys = 0, 0, 0, 0, 0
    has_audit = bool(audit_map)

    for code in FLAVOR_CODES:
        f_info = FLAVOR_MAP[code]
        recv_units = int(rec_map.get(code, 0))
        issued_units = int(added_map.get(code, 0))
        removed_units = int(rem_map.get(code, 0))
        calc_stock = recv_units - issued_units - removed_units

        tot_rec += recv_units
        tot_issued += issued_units
        tot_removed += removed_units
        tot_calc += calc_stock

        phys_stock = audit_map.get(code, None)
        if phys_stock is not None:
            phys_stock = int(phys_stock)
            tot_phys += phys_stock
            var_qty = phys_stock - calc_stock
            if var_qty == 0:
                var_status = "✅ Match"
            elif var_qty > 0:
                var_status = f"🟢 +{var_qty}"
            else:
                var_status = f"🔴 {var_qty}"
            phys_display = str(phys_stock)
            var_display = str(var_qty)
        else:
            phys_display = "—"
            var_display = "—"
            var_status = "⚪ Missing"

        comparison_rows.append({
            "Flavour": f_info["name"],
            "Received (In)": recv_units,
            "Issued (Carts)": issued_units,
            "Removed": removed_units,
            "Calc. Stock": calc_stock,
            "Physical Audit": phys_display,
            "Variance": var_display,
            "Audit Status": var_status
        })

    # Metric Banner for Reconciliation
    c_m1, c_m2, c_m3, c_m4, c_m5, c_m6 = st.columns(6)
    c_m1.metric("Total Inward", f"{tot_rec} pcs")
    c_m2.metric("Issued to Carts", f"{tot_issued} pcs")
    c_m3.metric("Stock Removed", f"{tot_removed} pcs")
    c_m4.metric("Calculated Freezer", f"{tot_calc} pcs")
    c_m5.metric("Physical Audited", f"{tot_phys} pcs" if has_audit else "Not Available")
    net_var = tot_phys - tot_calc if has_audit else 0
    c_m6.metric("Net Variance", f"{net_var:+d} pcs" if has_audit else "N/A")

    # Summary Total Row
    comp_df = pd.DataFrame(comparison_rows)
    total_row_comp = {
        "Flavour": "🔥 OVERALL TOTAL",
        "Received (In)": tot_rec,
        "Issued (Carts)": tot_issued,
        "Removed": tot_removed,
        "Calc. Stock": tot_calc,
        "Physical Audit": str(tot_phys) if has_audit else "—",
        "Variance": f"{net_var:+d}" if has_audit else "—",
        "Audit Status": "✅ Match" if net_var == 0 and has_audit else (f"⚠️ {net_var:+d}" if has_audit else "—")
    }
    comp_df = pd.concat([comp_df, pd.DataFrame([total_row_comp])], ignore_index=True)

    # Render without scrolling
    st.dataframe(comp_df, hide_index=True, use_container_width=True, height=370)

    # --- SECTION 2: UPCOMING ORDER RECOMMENDATIONS (BASED STRICTLY ON CALC STOCK) ---
    st.markdown("---")
    st.markdown("### 2. Suggested Orders & Inventory Runway &nbsp; *(Calculated from Live Freezer Stock)*")

    reorder_rows = []
    trigger_dates = []
    tot_calc_active = 0
    tot_rate = 0.0
    tot_suggested_units = 0
    tot_order_cost = 0.0

    for code in FLAVOR_CODES:
        f_info = FLAVOR_MAP[code]
        calc_stock = int(rec_map.get(code, 0)) - int(added_map.get(code, 0)) - int(rem_map.get(code, 0))
        avail_stock = calc_stock  # Strictly based on Calculated Stock after accounting for removed items
        tot_calc_active += avail_stock

        recent_sold = float(sales_pace_map.get(code, 0))
        rate = recent_sold / lookback_days
        tot_rate += rate
        target_req = int(round(rate * (buffer_days + cover_days)))

        if rate <= 0:
            status = "⚪ No Sales"
            days_left = None
            suggested_qty = 0
            reason = "No active sales logged"
        else:
            days_left = avail_stock / rate
            trigger_date = today_fa + timedelta(days=max(0, int(days_left - buffer_days)))
            trigger_dates.append(trigger_date)

            if avail_stock <= (rate * buffer_days):
                status = "🔴 Order Now"
                suggested_qty = max(0, int(round((target_req - avail_stock) / 10.0)) * 10)
                reason = f"Stock below {buffer_days}d buffer"
            elif avail_stock <= (rate * (buffer_days + 2)):
                status = "🟡 Order Soon"
                suggested_qty = max(0, int(round((target_req - avail_stock) / 10.0)) * 10)
                reason = f"Reaches buffer in < 2 days"
            else:
                status = "🟢 OK"
                suggested_qty = 0
                reason = f"Stock covers {int(round(days_left))} days"

        tot_suggested_units += suggested_qty
        tot_order_cost += (suggested_qty * f_info["cost_price"])

        reorder_rows.append({
            "Flavour": f_info["name"],
            "Calculated Stock": avail_stock,
            "Daily Pace": f"{rate:.1f} /d",
            "Runway": f"{int(round(days_left))} days" if days_left is not None else "—",
            "Target Buffer": target_req,
            "Suggested Order": int(suggested_qty),
            "Urgency": status,
            "Rationale": reason
        })

    # Metric Banner for Orders
    r_m1, r_m2, r_m3, r_m4 = st.columns(4)
    overall_order_date = min(trigger_dates) if trigger_dates else None
    r_m1.metric("Calculated Active Stock", f"{tot_calc_active} units")
    r_m2.metric("Daily Velocity", f"{tot_rate:.1f} units/day")
    r_m3.metric("Total Order Quantity", f"{tot_suggested_units} pcs")
    r_m4.metric("Estimated PO Cost", f"₹{tot_order_cost:,.2f}")

    if overall_order_date is not None:
        if overall_order_date <= today_fa:
            st.error(f"🚨 **Action Required:** At least one flavor has breached the safety buffer based on calculated stock. Place replenishment order today!")
        else:
            days_until = (overall_order_date - today_fa).days
            st.info(f"📅 **Next Order Milestone:** Estimated order placement on **{overall_order_date.strftime('%d %b %Y')}** ({days_until} days remaining).")

    # Summary Total Row to Reorder Table
    reorder_df = pd.DataFrame(reorder_rows)
    total_row_reorder = {
        "Flavour": "🔥 OVERALL TOTAL",
        "Calculated Stock": tot_calc_active,
        "Daily Pace": f"{tot_rate:.1f} /d",
        "Runway": f"{(tot_calc_active / tot_rate):.0f} days" if tot_rate > 0 else "—",
        "Target Buffer": int(round(tot_rate * (buffer_days + cover_days))),
        "Suggested Order": tot_suggested_units,
        "Urgency": "🔴 Order Now" if overall_order_date and overall_order_date <= today_fa else "🟢 Stable",
        "Rationale": f"Est Cost: ₹{tot_order_cost:,.0f}"
    }
    reorder_df = pd.concat([reorder_df, pd.DataFrame([total_row_reorder])], ignore_index=True)

    # Render without scrolling
    st.dataframe(reorder_df, hide_index=True, use_container_width=True, height=370)

    # --- SECTION 3: DETAILED STOCK MOVEMENT LEDGERS ---
    st.markdown("---")
    st.markdown("### 3. Detailed Stock Movement Logs")

    m_tab1, m_tab2, m_tab3, m_tab4 = st.tabs(["📋 Purchase Orders", "📦 Received Deliveries", "🔍 Physical Stock Audits", "🗑️ Stock Removed"])

    with m_tab1:
        po_query_df = db_conn.query("""
            SELECT p.id AS "PO #", p.order_date AS "Order Date", p.expected_date AS "Expected Date",
                   p.location AS "Location", p.order_status AS "Status",
                   json_agg(json_build_object('code', pi.flavor_code, 'qty', pi.ordered_units)) AS items
            FROM purchase_orders p
            LEFT JOIN purchase_order_items pi ON p.id = pi.order_id
            GROUP BY p.id ORDER BY p.order_date DESC;
        """, ttl="0s")
        if not po_query_df.empty:
            po_display = []
            for _, r in po_query_df.iterrows():
                items_dict = {itm['code']: itm['qty'] for itm in r['items']} if r['items'] else {}
                row_data = {
                    "PO #": f"PO #{r['PO #']}",
                    "Order Date": pd.to_datetime(r['Order Date']).strftime("%d %b %Y"),
                    "Expected": pd.to_datetime(r['Expected Date']).strftime("%d %b %Y") if pd.notna(r['Expected Date']) else "—",
                    "Location": r['Location'],
                    "Status": r['Status'],
                    "Total Qty": sum(int(q or 0) for q in items_dict.values())
                }
                for code in FLAVOR_CODES:
                    row_data[code] = items_dict.get(code, 0)
                po_display.append(row_data)
            st.dataframe(pd.DataFrame(po_display), hide_index=True, use_container_width=True)
        else:
            st.caption("No purchase orders found in database.")

    with m_tab2:
        rec_query_df = db_conn.query("""
            SELECT r.id AS "Receipt #", r.received_date AS "Received Date", r.location AS "Location",
                   r.purchase_order_id AS "PO Ref", r.payment_status AS "Payment",
                   json_agg(json_build_object('code', ri.flavor_code, 'rec', ri.received_units)) AS items
            FROM stock_received r
            LEFT JOIN stock_received_items ri ON r.id = ri.received_id
            GROUP BY r.id ORDER BY r.received_date DESC;
        """, ttl="0s")
        if not rec_query_df.empty:
            rec_display = []
            for _, r in rec_query_df.iterrows():
                items_dict = {itm['code']: itm['rec'] for itm in r['items']} if r['items'] else {}
                row_data = {
                    "Receipt #": f"#{r['Receipt #']}",
                    "Received Date": pd.to_datetime(r['Received Date']).strftime("%d %b %Y"),
                    "Location": r['Location'],
                    "Linked PO": f"PO #{r['PO Ref']}" if pd.notna(r['PO Ref']) else "Ad-hoc",
                    "Payment Status": r['Payment'],
                    "Total Received": sum(int(q or 0) for q in items_dict.values())
                }
                for code in FLAVOR_CODES:
                    row_data[code] = items_dict.get(code, 0)
                rec_display.append(row_data)
            st.dataframe(pd.DataFrame(rec_display), hide_index=True, use_container_width=True)
        else:
            st.caption("No stock receipts recorded in database.")

    with m_tab3:
        audit_query_df = db_conn.query("""
            SELECT audit_id AS "Audit #", audit_date AS "Audit Date", location AS "Location",
                   audited_by AS "Auditor", total_physical_units AS "Total Count", remarks AS "Remarks",
                   ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units
            FROM stock_audits_wide
            ORDER BY audit_date DESC, audit_id DESC;
        """, ttl="0s")
        if not audit_query_df.empty:
            aud_display = []
            for _, r in audit_query_df.iterrows():
                row_data = {
                    "Audit #": f"#{r['Audit #']}",
                    "Audit Date": pd.to_datetime(r['Audit Date']).strftime("%d %b %Y"),
                    "Location": r['Location'],
                    "Audited By": r['Auditor'],
                    "Total Count": r['Total Count'],
                    "Remarks": r['Remarks']
                }
                for code in FLAVOR_CODES:
                    col_name = FLAVOR_MAP[code]["audit_col"]
                    row_data[code] = r.get(col_name, 0)
                aud_display.append(row_data)
            st.dataframe(pd.DataFrame(aud_display), hide_index=True, use_container_width=True)
        else:
            st.caption("No physical stock audits recorded in database.")

    with m_tab4:
        rem_query_df = db_conn.query("""
            SELECT id AS "ID", removal_date AS "Date", location AS "Location",
                   ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                   total_units AS "Total Units", cost_price_of_removed_items AS "Cost (₹)",
                   reason_for_removal AS "Reason", removed_by AS "Removed By", verified_by AS "Verified By"
            FROM stock_removed
            ORDER BY removal_date DESC, id DESC;
        """, ttl="0s")
        if not rem_query_df.empty:
            rem_display = []
            for _, r in rem_query_df.iterrows():
                row_data = {
                    "ID": f"#{r['ID']}",
                    "Date": pd.to_datetime(r['Date']).strftime("%d %b %Y"),
                    "Location": r['Location'],
                    "Total Units": int(r['Total Units']) if pd.notna(r['Total Units']) else sum(int(r.get(FLAVOR_MAP[c]['audit_col'], 0)) for c in FLAVOR_CODES),
                    "Cost (₹)": float(r['Cost (₹)']),
                    "Reason": r['Reason'],
                    "Removed By": r['Removed By'] if pd.notna(r['Removed By']) else "",
                    "Verified By": r['Verified By']
                }
                for code in FLAVOR_CODES:
                    col_name = FLAVOR_MAP[code]["audit_col"]
                    row_data[code] = int(r.get(col_name, 0))
                rem_display.append(row_data)
            st.dataframe(pd.DataFrame(rem_display), hide_index=True, use_container_width=True)
        else:
            st.caption("No stock removals recorded in database.")

# ======================================================================
# PAGE 5: STOCK REMOVED (Wastage / Return / Tasting Logs)
# ======================================================================
elif page == "Stock Removed" and user_role == "admin":
    st.subheader("Stock Removed / Wastage Log")
    st.caption("Record units removed from the freezer (damages, expiry, sampling, staff consumption, or supplier returns).")

    rem_mode = st.radio("Mode", ["New Entry", "View Entries", "Edit Past Entry"], horizontal=True, key="rem_screen_mode")

    if rem_mode == "New Entry":
        st.write("Enter details and specify quantities removed per flavour:")

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            removal_date = st.date_input("Removal Date", value=date.today(), key="new_rem_date")
        with c2:
            location = st.text_input("Location", value=CITY, key="new_rem_loc")
        with c3:
            removed_by = st.text_input("Removed By", placeholder="e.g. Staff / Cart Boy", key="new_rem_rby")
        with c4:
            verified_by = st.text_input("Verified By", value="Admin", key="new_rem_vby")

        reason_for_removal = st.text_input("Reason for Removal (Mandatory)", key="new_rem_reason", placeholder="e.g. Broken packaging, expired batch, festival sampling...")

        rem_grid_rows = []
        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            rem_grid_rows.append({
                "Flavour": f_info["name"],
                "Code": code,
                "Unit Cost (₹)": float(f_info["cost_price"]),
                "Units Removed": 0
            })

        st.write("Enter units removed per flavour:")
        rem_editor_df = st.data_editor(
            pd.DataFrame(rem_grid_rows),
            column_config={
                "Flavour": st.column_config.TextColumn(disabled=True),
                "Code": st.column_config.TextColumn(disabled=True),
                "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
                "Units Removed": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            },
            hide_index=True,
            use_container_width=True,
            key="new_rem_editor"
        )

        tot_rem_units = int(rem_editor_df["Units Removed"].sum())
        tot_rem_cost = float(sum(rem_editor_df["Units Removed"] * rem_editor_df["Unit Cost (₹)"]))

        st.markdown("#### Removal Summary")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Units Removed", f"{tot_rem_units} units")
        m2.metric("Total Cost Value", f"₹{tot_rem_cost:,.2f}")
        m3.metric("Date of Removal", removal_date.strftime("%d %b %Y"))

        if st.button("🗑️ Save Stock Removal", type="primary", use_container_width=True):
            if tot_rem_units <= 0:
                st.error("Please enter at least one quantity greater than 0 before saving.")
            elif not reason_for_removal.strip():
                st.error("Reason for removal is mandatory. Please provide a brief explanation.")
            else:
                try:
                    units_map = dict(zip(rem_editor_df["Code"], rem_editor_df["Units Removed"]))
                    with db_conn.session as s:
                        res = s.execute(
                            text("""
                            INSERT INTO stock_removed (
                                removal_date, location, 
                                ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                                cost_price_of_removed_items, reason_for_removal, removed_by, verified_by
                            ) VALUES (
                                :rd, :loc,
                                :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra,
                                :cost, :reason, :rby, :vby
                            ) RETURNING id;
                            """),
                            {
                                "rd": removal_date, "loc": location,
                                "ml": int(units_map.get("ML", 0)), "mm": int(units_map.get("MM", 0)), "ps": int(units_map.get("PS", 0)),
                                "mn": int(units_map.get("MN", 0)), "kb": int(units_map.get("KB", 0)), "bm": int(units_map.get("BM", 0)),
                                "sg": int(units_map.get("SG", 0)), "ch": int(units_map.get("CH", 0)), "ra": int(units_map.get("RA", 0)),
                                "cost": tot_rem_cost, "reason": reason_for_removal.strip(), "rby": removed_by.strip(), "vby": verified_by.strip()
                            }
                        )
                        new_rem_id = res.scalar()
                        s.commit()
                    show_success_modal(f"Stock Removal #{new_rem_id} recorded successfully! Logged {tot_rem_units} units (₹{tot_rem_cost:,.2f}).")
                except Exception as e:
                    st.error(f"Could not save stock removal to database: {e}")

    elif rem_mode == "View Entries":
        rem_query_df = db_conn.query("""
            SELECT id AS "ID", removal_date AS "Date", location AS "Location",
                   ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                   total_units AS "Total Units", cost_price_of_removed_items AS "Cost (₹)",
                   reason_for_removal AS "Reason", removed_by AS "Removed By", verified_by AS "Verified By"
            FROM stock_removed
            ORDER BY removal_date DESC, id DESC;
        """, ttl="0s")

        if rem_query_df.empty:
            st.info("No stock removal logs found in the database.")
        else:
            total_logs = len(rem_query_df)
            total_removed_units = int(rem_query_df["Total Units"].sum()) if "Total Units" in rem_query_df.columns else 0
            total_removed_cost = float(rem_query_df["Cost (₹)"].sum())

            k1, k2, k3 = st.columns(3)
            k1.metric("Total Removal Events", f"{total_logs}")
            k2.metric("Total Units Removed", f"{total_removed_units} pcs")
            k3.metric("Total Value of Removed Stock", f"₹{total_removed_cost:,.2f}")

            display_rem_list = []
            for _, r in rem_query_df.iterrows():
                row_data = {
                    "ID": f"#{r['ID']}",
                    "Date": pd.to_datetime(r['Date']).strftime("%d %b %Y"),
                    "Location": r['Location'],
                    "Total Units": int(r['Total Units']) if pd.notna(r['Total Units']) else sum(int(r.get(FLAVOR_MAP[c]['audit_col'], 0)) for c in FLAVOR_CODES),
                    "Cost (₹)": float(r['Cost (₹)']),
                    "Reason": r['Reason'],
                    "Removed By": r['Removed By'] if pd.notna(r['Removed By']) else "",
                    "Verified By": r['Verified By']
                }
                for code in FLAVOR_CODES:
                    col_name = FLAVOR_MAP[code]["audit_col"]
                    row_data[FLAVOR_MAP[code]["name"]] = int(r.get(col_name, 0))
                display_rem_list.append(row_data)

            rem_table_df = pd.DataFrame(display_rem_list)
            st.dataframe(
                rem_table_df, 
                hide_index=True, 
                use_container_width=True,
                column_config={"Cost (₹)": st.column_config.NumberColumn(format="₹%.2f")}
            )

    elif rem_mode == "Edit Past Entry":
        rem_query_df = db_conn.query("""
            SELECT id, removal_date, location, ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                   cost_price_of_removed_items, reason_for_removal, removed_by, verified_by
            FROM stock_removed
            ORDER BY removal_date DESC, id DESC;
        """, ttl="0s")

        if rem_query_df.empty:
            st.info("No past stock removals found in database.")
        else:
            rem_records = rem_query_df.to_dict("records")
            rem_labels = [
                f"Removal #{r['id']} — {pd.to_datetime(r['removal_date']).strftime('%d %b %Y')} ({r['location']}) — {str(r['reason_for_removal'])[:25]} (₹{float(r['cost_price_of_removed_items']):,.0f})"
                for r in rem_records
            ]
            sel_rem_label = st.selectbox("Select removal entry to edit", rem_labels, key="edit_rem_select")
            loaded_rem = rem_records[rem_labels.index(sel_rem_label)]
            loaded_rem_id = loaded_rem["id"]

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                e_rem_date = st.date_input(
                    "Removal Date", 
                    value=pd.to_datetime(loaded_rem["removal_date"]).date() if loaded_rem.get("removal_date") else date.today(),
                    key=f"edit_rem_date_{loaded_rem_id}"
                )
            with c2:
                e_rem_loc = st.text_input("Location", value=str(loaded_rem.get("location", CITY)), key=f"edit_rem_loc_{loaded_rem_id}")
            with c3:
                e_rem_rby = st.text_input("Removed By", value=str(loaded_rem.get("removed_by") or ""), key=f"edit_rem_rby_{loaded_rem_id}")
            with c4:
                e_rem_vby = st.text_input("Verified By", value=str(loaded_rem.get("verified_by", "Admin")), key=f"edit_rem_vby_{loaded_rem_id}")

            e_rem_reason = st.text_input("Reason for Removal", value=str(loaded_rem.get("reason_for_removal") or ""), key=f"edit_rem_reason_{loaded_rem_id}")

            edit_rem_rows = []
            for code in FLAVOR_CODES:
                f_info = FLAVOR_MAP[code]
                col_name = f_info["audit_col"]
                edit_rem_rows.append({
                    "Flavour": f_info["name"],
                    "Code": code,
                    "Unit Cost (₹)": float(f_info["cost_price"]),
                    "Units Removed": int(loaded_rem.get(col_name, 0))
                })

            st.write("Modify units removed per flavour:")
            rem_edit_editor_df = st.data_editor(
                pd.DataFrame(edit_rem_rows),
                column_config={
                    "Flavour": st.column_config.TextColumn(disabled=True),
                    "Code": st.column_config.TextColumn(disabled=True),
                    "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%.2f", disabled=True),
                    "Units Removed": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
                },
                hide_index=True,
                use_container_width=True,
                key=f"edit_rem_editor_{loaded_rem_id}"
            )

            e_tot_rem_units = int(rem_edit_editor_df["Units Removed"].sum())
            e_tot_rem_cost = float(sum(rem_edit_editor_df["Units Removed"] * rem_edit_editor_df["Unit Cost (₹)"]))

            st.markdown("#### Updated Summary")
            em1, em2, em3 = st.columns(3)
            em1.metric("Total Units Removed", f"{e_tot_rem_units} units")
            em2.metric("Total Cost Value", f"₹{e_tot_rem_cost:,.2f}")
            em3.metric("Date", e_rem_date.strftime("%d %b %Y"))

            if st.button("💾 Update Stock Removal", type="primary", use_container_width=True):
                if e_tot_rem_units <= 0:
                    st.error("Please enter at least one quantity greater than 0.")
                elif not e_rem_reason.strip():
                    st.error("Reason for removal cannot be empty.")
                else:
                    try:
                        e_units_map = dict(zip(rem_edit_editor_df["Code"], rem_edit_editor_df["Units Removed"]))
                        with db_conn.session as s:
                            s.execute(
                                text("""
                                UPDATE stock_removed
                                SET removal_date = :rd, location = :loc,
                                    ml_units = :ml, mm_units = :mm, ps_units = :ps, mn_units = :mn,
                                    kb_units = :kb, bm_units = :bm, sg_units = :sg, ch_units = :ch, ra_units = :ra,
                                    cost_price_of_removed_items = :cost,
                                    reason_for_removal = :reason,
                                    removed_by = :rby,
                                    verified_by = :vby,
                                    updated_at = NOW()
                                WHERE id = :id;
                                """),
                                {
                                    "rd": e_rem_date, "loc": e_rem_loc,
                                    "ml": int(e_units_map.get("ML", 0)), "mm": int(e_units_map.get("MM", 0)), "ps": int(e_units_map.get("PS", 0)),
                                    "mn": int(e_units_map.get("MN", 0)), "kb": int(e_units_map.get("KB", 0)), "bm": int(e_units_map.get("BM", 0)),
                                    "sg": int(e_units_map.get("SG", 0)), "ch": int(e_units_map.get("CH", 0)), "ra": int(e_units_map.get("RA", 0)),
                                    "cost": e_tot_rem_cost, "reason": e_rem_reason.strip(), "rby": e_rem_rby.strip(), "vby": e_rem_vby.strip(),
                                    "id": loaded_rem_id
                                }
                            )
                            s.commit()
                        show_success_modal(f"Stock Removal #{loaded_rem_id} updated successfully! Final Value: ₹{e_tot_rem_cost:,.2f}.")
                    except Exception as e:
                        st.error(f"Could not update stock removal entry: {e}")

# ======================================================================
# PAGE 6: EXPENSES (100% Supabase PostgreSQL Powered)
# ======================================================================
elif page == "Expenses" and user_role == "admin":
    st.subheader("Log an expense")

    exp_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="db_exp_mode")

    expenses_list = load_db_expenses_list()

    exp_loaded = None
    exp_editing_id = None
    if exp_mode == "Edit past entry":
        if not expenses_list:
            st.info("No expenses found in database yet.")
        else:
            exp_labels = [f"#{r['id']} — {r['Date'].strftime('%d %b %Y')} — {r['Description'] or r['Category']} (₹{r['Amount']:,.0f})" for r in expenses_list]
            exp_sel = st.selectbox("Select expense to edit", exp_labels, key="db_exp_select")
            exp_loaded = expenses_list[exp_labels.index(exp_sel)]
            exp_editing_id = exp_loaded["id"]

    ek = f"_{exp_editing_id}" if exp_editing_id else "_new"

    c1, c2 = st.columns(2)
    with c1:
        exp_date_val = exp_loaded["Date"].date() if (exp_loaded and exp_loaded.get("Date")) else date.today()
        exp_date = st.date_input("Date", value=exp_date_val, key=f"db_exp_date{ek}")
    with c2:
        default_cat_idx = EXPENSE_CATEGORIES.index(exp_loaded["Category"]) if (exp_loaded and exp_loaded.get("Category") in EXPENSE_CATEGORIES) else 0
        category = st.selectbox("Category", EXPENSE_CATEGORIES, index=default_cat_idx, key=f"db_exp_category{ek}")

    description = st.text_input("Description", value=(str(exp_loaded["Description"]) if (exp_loaded and exp_loaded.get("Description")) else ""), key=f"db_exp_desc{ek}")
    amount = st.number_input("Amount (₹)", min_value=0.0, value=(float(exp_loaded["Amount"]) if (exp_loaded and exp_loaded.get("Amount") is not None) else 0.0), step=10.0, key=f"db_exp_amt{ek}")

    c3, c4 = st.columns(2)
    with c3:
        default_mode_idx = PAYMENT_MODES.index(exp_loaded["Mode"]) if (exp_loaded and exp_loaded.get("Mode") in PAYMENT_MODES) else 0
        mode = st.selectbox("Payment mode", PAYMENT_MODES, index=default_mode_idx, key=f"db_exp_mode_sel{ek}")
    with c4:
        ref_no = st.text_input("Transaction ref. no. (optional)", value=(str(exp_loaded["Ref No"]) if (exp_loaded and exp_loaded.get("Ref No")) else ""), key=f"db_exp_ref{ek}")

    paid_to = st.text_input("Paid to (optional)", value=(str(exp_loaded["Paid To"]) if (exp_loaded and exp_loaded.get("Paid To")) else ""), key=f"db_exp_paidto{ek}")
    exp_remarks = st.text_input("Remarks (optional)", value=(str(exp_loaded["Remarks"]) if (exp_loaded and exp_loaded.get("Remarks")) else ""), key=f"db_exp_remarks{ek}")

    exp_btn_label = "Update expense" if exp_editing_id else "Save expense"
    if st.button(exp_btn_label, type="primary", use_container_width=True):
        if amount <= 0:
            st.error("Enter an amount greater than 0.")
        else:
            try:
                with db_conn.session as s:
                    if exp_editing_id:
                        s.execute(
                            text("""
                            UPDATE expenses
                            SET expense_date = :d, description = :desc, amount = :amt, category = :cat,
                                payment_mode = :m, ref_no = :ref, paid_to = :paid, remarks = :rem
                            WHERE id = :id;
                            """),
                            {
                                "d": exp_date, "desc": description, "amt": amount, "cat": category,
                                "m": mode, "ref": ref_no, "paid": paid_to, "rem": exp_remarks, "id": exp_editing_id
                            },
                        )
                    else:
                        s.execute(
                            text("""
                            INSERT INTO expenses (expense_date, description, amount, category, payment_mode, ref_no, paid_to, remarks)
                            VALUES (:d, :desc, :amt, :cat, :m, :ref, :paid, :rem);
                            """),
                            {
                                "d": exp_date, "desc": description, "amt": amount, "cat": category,
                                "m": mode, "ref": ref_no, "paid": paid_to, "rem": exp_remarks
                            },
                        )
                    s.commit()
                show_success_modal(f"Expense of ₹{amount:,.0f} saved under {category}!")
            except Exception as e:
                st.error(f"Could not save expense to database: {e}")

# ======================================================================
# PAGE 7: DASHBOARD (100% Supabase PostgreSQL Powered)
# ======================================================================
elif page == "Dashboard" and user_role == "admin":
    st.subheader("Quick view")

    try:
        daily_df = load_db_daily_df()
        exp_list = load_db_expenses_list()
        exp_df = pd.DataFrame(exp_list)
        freezer_df = get_db_freezer_stock()
    except Exception as e:
        daily_df = pd.DataFrame()
        exp_df = pd.DataFrame()
        freezer_df = pd.DataFrame()
        st.warning(f"Could not load data from database ({e}).")

    # Calculate live freezer stock valuation (already accounts for removed items)
    if not freezer_df.empty:
        freezer_df["cost_price"] = freezer_df["code"].map(lambda c: FLAVOR_MAP.get(c, {}).get("cost_price", 0.0))
        freezer_df["Stock_Value"] = freezer_df["Units in freezer"] * freezer_df["cost_price"]
        total_freezer_val = float(freezer_df["Stock_Value"].sum())
        total_freezer_units = int(freezer_df["Units in freezer"].sum())
    else:
        total_freezer_val = 0.0
        total_freezer_units = 0

    # Total COGS all-time so far from expenses
    total_cogs_all_time = float(exp_df[exp_df["Category"] == "Cost of Goods"]["Amount"].sum()) if not exp_df.empty else 0.0

    today = pd.Timestamp(date.today())
    day_labels = [today - pd.Timedelta(days=3), today - pd.Timedelta(days=2), today - pd.Timedelta(days=1)]
    if not daily_df.empty:
        day_rows = [daily_df[daily_df["Date"].dt.date == d.date()] for d in day_labels]
        day_rev = [r["Total_Collection"].sum() for r in day_rows]
        day_units = [int(round(r["Sold_Total"].sum())) for r in day_rows]

        col_names = [d.strftime("%d %b") for d in day_labels]
        col_names[-1] = col_names[-1] + " (Yesterday)"

        compare_df = pd.DataFrame(
            {
                "Metric": ["Revenue", "Units sold"],
                col_names[0]: [f"₹{day_rev[0]:,.0f}", f"{day_units[0]}"],
                col_names[1]: [f"₹{day_rev[1]:,.0f}", f"{day_units[1]}"],
                col_names[2]: [f"₹{day_rev[2]:,.0f}", f"{day_units[2]}"],
            }
        )
        st.markdown('<div id="last-3-days"></div>', unsafe_allow_html=True)
        st.markdown("**Last 3 days**")
        st.dataframe(compare_df, hide_index=True, use_container_width=True)

        st.markdown('<div id="revenue-trend"></div>', unsafe_allow_html=True)
        st.markdown("**Revenue, last 14 days**")
        trend_df = (
            daily_df.assign(Day=daily_df["Date"].dt.normalize())
            .groupby("Day", as_index=False)["Total_Collection"]
            .sum()
            .sort_values("Day")
            .tail(14)
        )
        trend_chart = (
            alt.Chart(trend_df)
            .mark_bar(color="#E8542A")
            .encode(
                x=alt.X("Day:T", title="", axis=alt.Axis(format="%d %b", labelAngle=-45)),
                y=alt.Y("Total_Collection:Q", title="Revenue (₹)"),
                tooltip=[alt.Tooltip("Day:T", title="Date", format="%d %b %Y"), alt.Tooltip("Total_Collection:Q", title="Revenue", format=",.0f")],
            )
            .properties(height=280)
        )
        st.altair_chart(trend_chart, use_container_width=True)
    else:
        st.info("No sales logged in database yet.")

    # Date-range reports
    if not daily_df.empty or not exp_df.empty:
        st.markdown("---")
        st.markdown('<div id="reports"></div>', unsafe_allow_html=True)
        st.markdown("## Reports")

        all_dates = []
        if not daily_df.empty:
            all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()]
        if not exp_df.empty and exp_df["Date"].notna().any():
            all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()]
        min_d, max_d = min(all_dates), max(all_dates)
        default_start = max(min_d, max_d - timedelta(days=29))

        if "applied_start" not in st.session_state:
            st.session_state["applied_start"] = default_start
        if "applied_end" not in st.session_state:
            st.session_state["applied_end"] = max_d
        st.session_state["applied_start"] = min(max(st.session_state["applied_start"], min_d), max_d)
        st.session_state["applied_end"] = min(max(st.session_state["applied_end"], min_d), max_d)

        with st.form("date_range_form"):
            rc1, rc2, rc3 = st.columns([2, 2, 1])
            with rc1:
                pending_start = st.date_input("From", value=st.session_state["applied_start"], min_value=min_d, max_value=max_d)
            with rc2:
                pending_end = st.date_input("To", value=st.session_state["applied_end"], min_value=min_d, max_value=max_d)
            with rc3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
                apply_clicked = st.form_submit_button("Apply", type="primary", use_container_width=True)

        if apply_clicked:
            st.session_state["applied_start"] = pending_start
            st.session_state["applied_end"] = pending_end

        range_start = st.session_state["applied_start"]
        range_end = st.session_state["applied_end"]

        if range_start > range_end:
            st.error("'From' date is after 'To' date - swap them and click Apply again.")
            range_start, range_end = range_end, range_start

        st.caption(f"Showing (PostgreSQL Data): {range_start.strftime('%d %b %Y')} – {range_end.strftime('%d %b %Y')}")

        range_df = daily_df[(daily_df["Date"].dt.date >= range_start) & (daily_df["Date"].dt.date <= range_end)] if not daily_df.empty else daily_df
        range_exp = exp_df[(exp_df["Date"].dt.date >= range_start) & (exp_df["Date"].dt.date <= range_end)] if not exp_df.empty else exp_df

        total_rev = range_df["Total_Collection"].sum() if not range_df.empty else 0.0
        total_units = int(round(range_df["Sold_Total"].sum())) if not range_df.empty else 0
        total_exp_all = range_exp["Amount"].sum() if not range_exp.empty else 0.0
        cogs_in_range = range_exp[range_exp["Category"] == "Cost of Goods"]["Amount"].sum() if not range_exp.empty else 0.0

        # Metric Banner for Reports including COGS so far & Freezer Valuation
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)
        mc1.metric("Revenue in range", f"₹{total_rev:,.0f}")
        mc2.metric("Units sold in range", f"{total_units}")
        mc3.metric("COGS (In Range)", f"₹{cogs_in_range:,.0f}")
        mc4.metric("COGS So Far (All-Time)", f"₹{total_cogs_all_time:,.0f}")
        mc5.metric("Freezer Stock Value", f"₹{total_freezer_val:,.0f}")

        # Cart-wise comparison
        st.markdown('<div id="cart-wise-comparison"></div>', unsafe_allow_html=True)
        st.markdown("### Cart-wise comparison")
        if not range_df.empty:
            cart_grp = (
                range_df.groupby("Cart")
                .agg(**{"Revenue (₹)": ("Total_Collection", "sum"), "Units sold": ("Sold_Total", "sum")})
                .reset_index()
                .sort_values("Revenue (₹)", ascending=False)
            )
            cart_grp["Units sold"] = cart_grp["Units sold"].apply(lambda x: int(round(x)))
            st.dataframe(cart_grp, hide_index=True, use_container_width=True)
            st.bar_chart(cart_grp.set_index("Cart")["Revenue (₹)"])
        else:
            st.caption("No sales in this date range.")

        # Cart-wise average sales by day of week
        st.markdown('<div id="cart-wise-day-of-week"></div>', unsafe_allow_html=True)
        st.markdown("### Cart-wise average sales by day of the week")
        if not range_df.empty:
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dow_df = range_df[range_df["Sold_Total"] > 0].copy()
            dow_df["Day"] = dow_df["Date"].dt.day_name()

            if dow_df.empty:
                st.caption("No days with actual sales in this date range.")
            else:
                units_pivot = dow_df.pivot_table(
                    index="Cart", columns="Day", values="Sold_Total", aggfunc="mean", fill_value=0, margins=True, margins_name="All carts"
                )
                day_cols = [d for d in day_order if d in units_pivot.columns] + ["All carts"]
                units_pivot = units_pivot.reindex(columns=day_cols)

                rev_pivot = dow_df.pivot_table(
                    index="Cart", columns="Day", values="Total_Collection", aggfunc="mean", fill_value=0, margins=True, margins_name="All carts"
                )
                rev_pivot = rev_pivot.reindex(columns=day_cols)

                st.write("**Avg. units sold** (rows = cart, columns = day of week)")
                st.dataframe(units_pivot.round(0).astype(int), use_container_width=True)

                st.write("**Avg. revenue (₹)** (rows = cart, columns = day of week)")
                st.dataframe(rev_pivot.round(0).astype(int), use_container_width=True)
        else:
            st.caption("No sales in this date range.")

        # Flavour-wise performance
        st.markdown('<div id="flavour-wise-performance"></div>', unsafe_allow_html=True)
        st.markdown("### Flavour-wise performance")
        flavor_range_df = load_db_flavor_sales(start_date=range_start, end_date=range_end)
        if not flavor_range_df.empty and flavor_range_df["Units sold"].sum() > 0:
            st.dataframe(flavor_range_df[["Flavour", "Units sold", "Est. revenue (₹)"]], hide_index=True, use_container_width=True)
            st.bar_chart(flavor_range_df.set_index("Flavour")["Units sold"])
            st.caption("Estimated revenue = units sold × MRP per flavour; actual collections may vary slightly.")
        else:
            st.caption("No sales in this date range.")

        # Profit & Loss summary
        st.markdown('<div id="profit-loss-summary"></div>', unsafe_allow_html=True)
        st.markdown("### Profit & loss summary")
        cogs = cogs_in_range
        opex_cats = ["Labour Charges", "Leakage Expense", "Miscellaneous Expense"]
        opex = range_exp[range_exp["Category"].isin(opex_cats)]["Amount"].sum() if not range_exp.empty else 0.0
        capital_cats = ["Initial Investment", "Initial Set-up Expense"]
        capital = range_exp[range_exp["Category"].isin(capital_cats)]["Amount"].sum() if not range_exp.empty else 0.0
        gross_profit = total_rev - cogs
        net_profit = gross_profit - opex

        pnl_df = pd.DataFrame(
            {
                "Line item": ["Revenue", "Cost of Goods", "Gross profit", "Operating expenses (labour, leakage, misc.)", "Net profit"],
                "Amount (₹)": [total_rev, -cogs, gross_profit, -opex, net_profit],
            }
        )
        st.dataframe(pnl_df, hide_index=True, use_container_width=True)
        pc1, pc2 = st.columns(2)
        pc1.metric("Net profit", f"₹{net_profit:,.0f}")
        pc2.metric("Margin", f"{(net_profit / total_rev * 100) if total_rev else 0:.1f}%")

        # Expense breakdown
        st.markdown('<div id="expense-breakdown"></div>', unsafe_allow_html=True)
        st.markdown("### Expense breakdown by category")
        if not range_exp.empty:
            by_cat = range_exp.groupby("Category")["Amount"].sum().sort_values(ascending=False)
            st.dataframe(
                by_cat.reset_index().rename(columns={"Amount": "₹"}),
                hide_index=True,
                use_container_width=True,
                column_config={"₹": st.column_config.ProgressColumn("Share", format="₹%.0f", min_value=0, max_value=float(by_cat.max()))},
            )
            st.bar_chart(by_cat)
        else:
            st.caption("No expenses logged in this date range.")

        # Cash vs PhonePe vs Advance vs Food/Tea
        st.markdown('<div id="cash-vs-phonepe"></div>', unsafe_allow_html=True)
        st.markdown("### Cash vs PhonePe / UPI vs Advance vs Food/Tea")
        if not range_df.empty:
            total_cash = range_df["Cash"].sum()
            total_phonepe = range_df["PhonePe"].sum()
            total_advance = range_df["Staff_Advance"].sum() if "Staff_Advance" in range_df.columns else 0.0
            total_food = range_df["Food_Tea_Cash"].sum() if "Food_Tea_Cash" in range_df.columns else 0.0

            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Cash", f"₹{total_cash:,.0f}")
            cc2.metric("PhonePe / UPI", f"₹{total_phonepe:,.0f}")
            cc3.metric("Staff Advance", f"₹{total_advance:,.0f}")
            cc4.metric("Food / Tea", f"₹{total_food:,.0f}")

            split_df = pd.DataFrame({
                "Mode": ["Cash", "PhonePe / UPI", "Staff Advance", "Food / Tea"], 
                "Amount (₹)": [total_cash, total_phonepe, total_advance, total_food],
            })
            st.bar_chart(split_df.set_index("Mode")["Amount (₹)"])
        else:
            st.caption("No collections in this date range.")

        # Sales table
        st.markdown('<div id="sales-in-range"></div>', unsafe_allow_html=True)
        st.markdown("### Sales in this range")
        if not range_df.empty:
            display_cols = ["Date", "Cart", "Sold_Total", "Total_Collection", "PhonePe", "Cash", "Staff_Name", "Staff_Advance", "Food_Tea_Cash"]
            sales_table = range_df.sort_values(["Date", "Cart"])[display_cols].rename(
                columns={
                    "Sold_Total": "Units sold", 
                    "Total_Collection": "Revenue (₹)",
                    "PhonePe": "PhonePe (₹)",
                    "Cash": "Cash (₹)",
                    "Staff_Name": "Staff Name",
                    "Staff_Advance": "Staff Advance (₹)",
                    "Food_Tea_Cash": "Food / Tea (₹)",
                }
            )
            sales_table["Units sold"] = sales_table["Units sold"].apply(lambda x: int(round(x)))
            sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")
            st.dataframe(sales_table, hide_index=True, use_container_width=True)
        else:
            st.caption("No sales in this date range.")

    # Current Inventory Status
    if not daily_df.empty:
        st.markdown("---")
        st.markdown('<div id="inventory-status"></div>', unsafe_allow_html=True)
        st.markdown("## Current Inventory Status")

        inv_c1, inv_c2, inv_c3 = st.columns(3)
        cart_stock_tot = int(round(daily_df.sort_values('Date').groupby('Cart').tail(1)['Closing_Total'].sum()))
        inv_c1.metric("Stock across carts", f"{cart_stock_tot} units")
        inv_c2.metric("Units in Freezer", f"{total_freezer_units} units")
        inv_c3.metric("Freezer Stock Valuation", f"₹{total_freezer_val:,.2f}")

        try:
            if not freezer_df.empty:
                st.markdown('<div id="freezer-stock-current"></div>', unsafe_allow_html=True)
                st.markdown("**Freezer stock breakdown & cost valuation**")
                
                disp_freezer = freezer_df.rename(columns={
                    "cost_price": "Unit Cost (₹)",
                    "Stock_Value": "Stock Value (₹)"
                })[["Flavour", "Units in freezer", "Unit Cost (₹)", "Stock Value (₹)"]]
                
                st.dataframe(
                    disp_freezer, 
                    hide_index=True, 
                    use_container_width=True,
                    column_config={
                        "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                        "Stock Value (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                    }
                )
        except Exception as e:
            st.caption(f"Could not compute freezer stock from DB ({e}).")

        st.markdown('<div id="latest-stock-per-cart"></div>', unsafe_allow_html=True)
        st.markdown("**Latest stock per cart**")
        latest_per_cart = daily_df.sort_values("Date").groupby("Cart").tail(1)[["Cart", "Date", "Closing_Total"]].copy()
        latest_per_cart["Closing_Total"] = latest_per_cart["Closing_Total"].apply(lambda x: int(round(x)))
        latest_per_cart["Date"] = latest_per_cart["Date"].dt.strftime("%d %b %Y")
        st.dataframe(latest_per_cart, hide_index=True, use_container_width=True)