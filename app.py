"""
Kulfi Ops - multi-user data entry app for the kulfi cart business.
"""

import streamlit as st
import altair as alt
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import textwrap
import hmac
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Kulfi Ops", page_icon="🍦", layout="wide")

st.html(
    textwrap.dedent(
        """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
    /* Full responsive layout */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0 !important;
        max-width: 100% !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 1rem !important;
    }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    h1, h2, h3 { font-family: 'Fraunces', serif !important; color: #8A5E17 !important; letter-spacing: -0.01em; }
    h1 { font-size: 1.6rem !important; margin-top: 0 !important; }
    h2 { font-size: 1.3rem !important; }
    h3 { font-size: 1.1rem !important; }
    p, span, label, .stMarkdown { color: #2A1B10; }

    /* ---------- Mobile Flavor Card Grid ---------- */
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

    /* ---------- Sidebar Navigation & Jump-To Menu ---------- */
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
    section[data-testid="stSidebar"] .stRadio label p { 
        font-size: 15px !important; 
        font-weight: 600; 
    }
    section[data-testid="stSidebar"] .stButton button { 
        font-size: 14px !important; 
        border-radius: 8px !important; 
    }

    .dash-jump { 
        background: #FFFBF2; 
        border: 1px solid #E3CBA0; 
        border-radius: 8px; 
        padding: 8px 10px; 
        margin-top: 6px; 
    }
    .dash-jump b { 
        font-size: 13px !important; 
        font-weight: 800; 
        color: #7A5A34; 
    }
    .dash-jump a { 
        display: block; 
        padding: 3px 0 3px 6px; 
        font-size: 12.5px !important; 
        color: #8A5E17 !important; 
        text-decoration: none; 
        border-radius: 4px; 
        line-height: 1.35;
    }
    .dash-jump a:hover { 
        background: #F0D9A6; 
        text-decoration: none; 
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
        font-size: 1.25rem !important; 
        color: #4A2418; 
    }

    /* High Contrast Bold Table Headers across Reports */
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
        font-size: 14px !important;
    }
    div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
        text-align: center !important;
        font-size: 13px !important;
    }
    div[data-testid="stDataFrame"] [role="columnheader"], div[data-testid="stDataEditor"] [role="columnheader"] {
        font-weight: 900 !important;
        color: #FFFFFF !important;
        background-color: #70440E !important;
        text-align: center !important;
    }

    hr { border-color: #E3CBA0 !important; margin: 0.4rem 0 !important; }
    </style>
    """
    )
)

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
CARTS = ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"][cite: 1, 2]
CITY = "HOSUR"[cite: 1, 2]

FLAVORS = [
    ("ML", "Malai", 40, 22),
    ("MM", "Mini Malai", 30, 18),
    ("PS", "Pista", 40, 22),
    ("MN", "Mango", 40, 22),
    ("KB", "Kesar Badam", 50, 27.5),
    ("BM", "Badam Matka", 80, 44),
    ("SG", "Shahi Gulab", 50, 27.5),
    ("CH", "Chocolate", 50, 27.5),
    ("RA", "Roasted Almond", 60, 33),
][cite: 1, 2]
FLAVOR_CODES = [f[0] for f in FLAVORS][cite: 1, 2]
N_FLAVORS = len(FLAVORS)[cite: 1, 2]

PAYMENT_STATUSES = ["Pending", "Partial", "Complete"][cite: 1, 2]

EXPENSE_CATEGORIES = [
    "Cost of Goods",
    "Labour Charges",
    "Leakage Expense",
    "Initial Set-up Expense",
    "Miscellaneous Expense",
    "Initial Investment",
][cite: 1, 2]
PAYMENT_MODES = ["Cash", "UPI / Bank Transfer"][cite: 1, 2]

DAILY_HEADER_ROWS = 2[cite: 1, 2]
# 4 prefix + 36 flavor cols + 4 suffix + 3 staff/food fields = 47 columns
DAILY_TOTAL_COLS = 47
EXPENSE_HEADER_ROWS = 3[cite: 1, 2]
STOCK_HEADER_ROWS = 4[cite: 1, 2]
STOCK_TOTAL_COLS = 60[cite: 1, 2]

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"][cite: 1, 2]


def _num(x):
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if s == "":
        return 0.0
    s = s.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        v = float(s)
    except ValueError:
        return 0.0
    return -v if neg else v[cite: 1, 2]


def _pad(row, n):
    if len(row) < n:
        return row + [""] * (n - len(row))
    return row[cite: 1, 2]


def _row_has_data(r):
    return any(str(c).strip() != "" for c in r[4:44])[cite: 1]


# ----------------------------------------------------------------------
# Google Sheets connection
# ----------------------------------------------------------------------
@st.cache_resource
def get_client():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )[cite: 1, 2]
    return gspread.authorize(creds)[cite: 1, 2]


@st.cache_resource
def get_workbook():
    return get_client().open_by_key(st.secrets["sheet_id"])[cite: 1, 2]


def get_ws(tab_name):
    return get_workbook().worksheet(tab_name)[cite: 1, 2]


# ----------------------------------------------------------------------
# Modal Alert Helper
# ----------------------------------------------------------------------
@st.dialog("Notification")
def show_success_modal(message):
    st.success(message)
    if st.button("OK", type="primary", use_container_width=True):
        st.rerun()


# ----------------------------------------------------------------------
# Assumptions Helpers (Staff List from A51:C56, Active status in C)
# ----------------------------------------------------------------------
def load_active_staff_list():
    try:
        ws = get_ws("Assumptions")
        values = ws.get_values("A51:C56")
        staff_names = []
        for row in values:
            if not row or not row[0].strip():
                continue
            name = row[0].strip()
            status = row[2].strip().lower() if len(row) >= 3 else "active"
            if status == "active":
                staff_names.append(name)
        return ["Select Staff"] + staff_names
    except Exception:
        return ["Select Staff"]


# ----------------------------------------------------------------------
# Daily Data As Shared helpers
# ----------------------------------------------------------------------
def load_daily_raw():
    ws = get_ws("Daily Data As Shared")[cite: 1, 2]
    values = ws.get_all_values()[cite: 1, 2]
    rows = values[DAILY_HEADER_ROWS:][cite: 1, 2]
    return ws, rows[cite: 1, 2]


def _col_letter(n):
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)[cite: 1, 2]
        letters = chr(65 + rem) + letters[cite: 1, 2]
    return letters[cite: 1, 2]


def _update_row(tab_name, row_number, values):
    ws = get_ws(tab_name)[cite: 1, 2]
    end_col = _col_letter(len(values))[cite: 1, 2]
    ws.update(range_name=f"A{row_number}:{end_col}{row_number}", values=[values], value_input_option="USER_ENTERED")[cite: 1]


def get_opening_balance(cart_name, before_date=None):
    _, rows = load_daily_raw()[cite: 1, 2]
    latest = None[cite: 1, 2]
    latest_date = None[cite: 1, 2]
    for raw_r in rows:[cite: 1, 2]
        r = _pad(raw_r, DAILY_TOTAL_COLS)[cite: 1, 2]
        if not r[0].strip() or r[1].strip() != cart_name or not _row_has_data(r):[cite: 1, 2]
            continue[cite: 1, 2]
        try:
            d = pd.to_datetime(r[0])[cite: 1]
            if pd.isna(d):[cite: 1]
                continue[cite: 1]
            d = d.date()[cite: 1]
        except Exception:
            continue[cite: 1, 2]
        if before_date is not None and d >= before_date:[cite: 1]
            continue[cite: 1]
        if latest_date is None or d > latest_date:[cite: 1, 2]
            latest_date = d[cite: 1, 2]
            latest = r[cite: 1, 2]
    if latest is None:[cite: 1, 2]
        return [0] * N_FLAVORS[cite: 1, 2]
    closing_start = 4 + 9 * 3[cite: 1, 2]
    return [int(_num(latest[closing_start + i])) for i in range(N_FLAVORS)][cite: 1, 2]


def update_daily_entry(row_number, entry_date, cart_name, added, closing, opening, total, phonepe, cash, remarks, staff_name="", staff_advance=0.0, food_tea_cash=0.0):
    sold = [opening[i] + added[i] - closing[i] for i in range(N_FLAVORS)][cite: 1]
    date_str = entry_date.strftime("%Y-%m-%d")[cite: 1, 2]
    date_cart_id = f"{date_str}||{cart_name}"[cite: 1, 2]
    row = (
        [date_str, cart_name, CITY, date_cart_id][cite: 1, 2]
        + [int(x) for x in opening][cite: 1]
        + [int(x) for x in added][cite: 1]
        + [int(x) for x in sold][cite: 1]
        + [int(x) for x in closing][cite: 1]
        + [float(total), float(phonepe), float(cash), str(remarks), str(staff_name), float(staff_advance), float(food_tea_cash)]
    )
    _update_row("Daily Data As Shared", row_number, row)[cite: 1]
    return sold[cite: 1]


def list_daily_entries():
    _, rows = load_daily_raw()[cite: 1, 2]
    out = [][cite: 1, 2]
    added_start = 4 + 9 * 1[cite: 1, 2]
    sold_start = 4 + 9 * 2[cite: 1, 2]
    closing_start = 4 + 9 * 3[cite: 1]
    for idx, raw_r in enumerate(rows):[cite: 1, 2]
        r = _pad(raw_r, DAILY_TOTAL_COLS)[cite: 1, 2]
        if not r[0].strip() or not _row_has_data(r):[cite: 1, 2]
            continue[cite: 1, 2]
        try:
            d = pd.to_datetime(r[0])[cite: 1, 2]
        except Exception:
            continue[cite: 1, 2]
        out.append(
            {
                "row": DAILY_HEADER_ROWS + idx + 1,
                "date": d,
                "cart": r[1].strip(),
                "opening": [int(_num(r[4 + i])) for i in range(N_FLAVORS)],
                "added": [int(_num(r[added_start + i])) for i in range(N_FLAVORS)],
                "sold": [int(_num(r[sold_start + i])) for i in range(N_FLAVORS)],
                "closing": [int(_num(r[closing_start + i])) for i in range(N_FLAVORS)],
                "total": _num(r[40]),
                "phonepe": _num(r[41]),
                "cash": _num(r[42]),
                "remarks": r[43].strip() if len(r) > 43 else "",
                "staff_name": r[44].strip() if len(r) > 44 else "",
                "staff_advance": _num(r[45]) if len(r) > 45 else 0.0,
                "food_tea_cash": _num(r[46]) if len(r) > 46 else 0.0,
            }
        )
    out.sort(key=lambda x: (x["date"], x["cart"]), reverse=True)[cite: 1, 2]
    return out[cite: 1, 2]


# ----------------------------------------------------------------------
# Expenses helpers
# ----------------------------------------------------------------------
def append_expense(exp_date, description, amount, category, mode, ref_no, paid_to, remarks):
    row = [
        exp_date.strftime("%Y-%m-%d"),
        description,
        float(amount),
        category,
        mode,
        ref_no,
        paid_to,
        remarks,
    ][cite: 1]
    ws = get_ws("Expenses")[cite: 1, 2]
    ws.append_row(row, value_input_option="USER_ENTERED")[cite: 1, 2]


def update_expense(row_number, exp_date, description, amount, category, mode, ref_no, paid_to, remarks):
    row = [
        exp_date.strftime("%Y-%m-%d"),
        description,
        float(amount),
        category,
        mode,
        ref_no,
        paid_to,
        remarks,
    ][cite: 1]
    _update_row("Expenses", row_number, row)[cite: 1, 2]


def list_expense_entries():
    ws = get_ws("Expenses")[cite: 1, 2]
    values = ws.get_all_values()[cite: 1, 2]
    cols_n = 8[cite: 1, 2]
    out = [][cite: 1, 2]
    for idx, raw_r in enumerate(values[EXPENSE_HEADER_ROWS:]):[cite: 1, 2]
        r = _pad(raw_r, cols_n)[cite: 1, 2]
        if not any(c.strip() for c in r):[cite: 1, 2]
            continue[cite: 1, 2]
        try:
            d = pd.to_datetime(r[0])[cite: 1, 2]
        except Exception:
            continue[cite: 1, 2]
        out.append(
            {
                "row": EXPENSE_HEADER_ROWS + idx + 1,
                "date": d,
                "description": r[1].strip(),
                "amount": _num(r[2]),
                "category": r[3].strip(),
                "mode": r[4].strip(),
                "ref_no": r[5].strip(),
                "paid_to": r[6].strip(),
                "remarks": r[7].strip(),
            }
        )[cite: 1, 2]
    out.sort(key=lambda x: (x["date"], x["row"]), reverse=True)[cite: 1, 2]
    return out[cite: 1, 2]


def load_expenses_df():
    ws = get_ws("Expenses")[cite: 1, 2]
    values = ws.get_all_values()[cite: 1, 2]
    cols = ["Date", "Description", "Amount", "Category", "Mode", "Ref No", "Paid To", "Remarks"][cite: 1, 2]
    rows = [_pad(r, len(cols)) for r in values[EXPENSE_HEADER_ROWS:] if any(c.strip() for c in r)][cite: 1, 2]
    df = pd.DataFrame(rows, columns=cols)[cite: 1, 2]
    if not df.empty:[cite: 1, 2]
        df["Amount"] = df["Amount"].apply(_num)[cite: 1, 2]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")[cite: 1, 2]
        df["Category"] = df["Category"].astype(str).str.strip()[cite: 1, 2]
        df["Mode"] = df["Mode"].astype(str).str.strip()[cite: 1, 2]
    return df[cite: 1, 2]


def load_daily_df():
    _, rows = load_daily_raw()[cite: 1, 2]
    records = [][cite: 1, 2]
    for raw_r in rows:[cite: 1, 2]
        r = _pad(raw_r, DAILY_TOTAL_COLS)[cite: 1, 2]
        if not r[0].strip() or not _row_has_data(r):[cite: 1, 2]
            continue[cite: 1, 2]
        try:
            d = pd.to_datetime(r[0])[cite: 1, 2]
        except Exception:
            continue[cite: 1, 2]
        closing_start = 4 + 9 * 3[cite: 1, 2]
        closing = [int(_num(r[closing_start + i])) for i in range(N_FLAVORS)][cite: 1, 2]
        sold_start = 4 + 9 * 2
        sold = [int(_num(r[sold_start + i])) for i in range(N_FLAVORS)][cite: 1, 2]
        added_start = 4 + 9 * 1[cite: 1, 2]
        added = [int(_num(r[added_start + i])) for i in range(N_FLAVORS)][cite: 1, 2]
        records.append(
            {
                "Date": d,
                "Cart": r[1],
                "Sold_Total": sum(sold),
                "Closing_Total": sum(closing),
                "Added_By_Flavor": added,
                "Sold_By_Flavor": sold,
                "Total_Collection": _num(r[40]),
                "PhonePe": _num(r[41]),
                "Cash": _num(r[42]),
                "Remarks": r[43].strip() if len(r) > 43 else "",
                "Staff_Name": r[44].strip() if len(r) > 44 else "",
                "Staff_Advance": _num(r[45]) if len(r) > 45 else 0.0,
                "Food_Tea_Cash": _num(r[46]) if len(r) > 46 else 0.0,
            }
        )
    return pd.DataFrame(records)[cite: 1, 2]


# ----------------------------------------------------------------------
# Stock Received helpers
# ----------------------------------------------------------------------
def load_stock_raw():
    ws = get_ws("Stock Received")[cite: 1, 2]
    values = ws.get_all_values()[cite: 1, 2]
    rows = values[STOCK_HEADER_ROWS:][cite: 1, 2]
    return ws, rows[cite: 1, 2]


def _build_stock_row(
    order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    diff = [received[i] - ordered[i] for i in range(N_FLAVORS)][cite: 1, 2]
    date_loc_id = f"{received_date.strftime('%Y-%m-%d')}||{location}"[cite: 1, 2]
    return (
        [order_date.strftime("%Y-%m-%d"), received_date.strftime("%Y-%m-%d"), location, date_loc_id][cite: 1, 2]
        + ordered + [sum(ordered)][cite: 1, 2]
        + received + [sum(received)][cite: 1, 2]
        + diff + [sum(diff)][cite: 1, 2]
        + cost + [sum(cost)][cite: 1, 2]
        + [payment_amount, payment_status, payment_date.strftime("%Y-%m-%d") if payment_date else "", payment_details][cite: 1, 2]
        + damaged + [sum(damaged)][cite: 1, 2]
        + [damaged_returned_on.strftime("%Y-%m-%d") if damaged_returned_on else "", notes][cite: 1, 2]
    )[cite: 1, 2]


def append_stock_entry(
    order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    row = _build_stock_row(
        order_date, received_date, location, ordered, received, cost, damaged,
        payment_amount, payment_status, payment_date, payment_details, damaged_returned_on, notes,
    )[cite: 1, 2]
    ws = get_ws("Stock Received")[cite: 1, 2]
    ws.append_row(row, value_input_option="USER_ENTERED")[cite: 1, 2]


def update_stock_entry(
    row_number, order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    row = _build_stock_row(
        order_date, received_date, location, ordered, received, cost, damaged,
        payment_amount, payment_status, payment_date, payment_details, damaged_returned_on, notes,
    )[cite: 1, 2]
    _update_row("Stock Received", row_number, row)[cite: 1, 2]


def list_stock_entries():
    _, rows = load_stock_raw()[cite: 1, 2]
    out = [][cite: 1, 2]
    for idx, raw_r in enumerate(rows):[cite: 1, 2]
        r = _pad(raw_r, STOCK_TOTAL_COLS)[cite: 1, 2]
        if not r[0].strip() and not r[1].strip():[cite: 1, 2]
            continue[cite: 1, 2]
        try:
            d = pd.to_datetime(r[1]) if r[1].strip() else pd.to_datetime(r[0])[cite: 1, 2]
        except Exception:
            continue[cite: 1, 2]
        out.append(
            {
                "row": STOCK_HEADER_ROWS + idx + 1,
                "order_date": r[0].strip(),
                "received_date": d,
                "location": r[2].strip(),
                "ordered": [int(_num(r[4 + i])) for i in range(N_FLAVORS)],
                "received": [int(_num(r[14 + i])) for i in range(N_FLAVORS)],
                "cost": [_num(r[34 + i]) for i in range(N_FLAVORS)],
                "damaged": [int(_num(r[48 + i])) for i in range(N_FLAVORS)],
                "payment_amount": _num(r[44]),
                "payment_status": r[45].strip(),
                "payment_date": r[46].strip(),
                "payment_details": r[47].strip(),
                "damaged_returned_on": r[58].strip(),
                "notes": r[59].strip() if len(r) > 59 else "",
            }
        )[cite: 1, 2]
    out.sort(key=lambda x: (x["received_date"], x["row"]), reverse=True)[cite: 1, 2]
    return out[cite: 1, 2]


def get_freezer_stock():
    _, stock_rows = load_stock_raw()[cite: 1, 2]
    received_totals = [0.0] * N_FLAVORS[cite: 1, 2]
    recv_start = 14[cite: 1, 2]
    for raw_r in stock_rows:[cite: 1, 2]
        r = _pad(raw_r, STOCK_TOTAL_COLS)[cite: 1, 2]
        if not r[0].strip():[cite: 1, 2]
            continue[cite: 1, 2]
        for i in range(N_FLAVORS):[cite: 1, 2]
            received_totals[i] += _num(r[recv_start + i])[cite: 1, 2]

    daily_df = load_daily_df()[cite: 1, 2]
    added_totals = [0.0] * N_FLAVORS[cite: 1, 2]
    if not daily_df.empty:[cite: 1, 2]
        for added in daily_df["Added_By_Flavor"]:[cite: 1, 2]
            for i in range(N_FLAVORS):[cite: 1, 2]
                added_totals[i] += added[i][cite: 1, 2]

    return [int(received_totals[i] - added_totals[i]) for i in range(N_FLAVORS)][cite: 1, 2]


# ----------------------------------------------------------------------
# Login
# ----------------------------------------------------------------------
def check_login():
    if st.session_state.get("authenticated", False):[cite: 1, 2]
        return True[cite: 1, 2]

    _, col_form, _ = st.columns([1, 1.2, 1])[cite: 1, 2]

    with col_form:
        try:
            st.image("assets/logo.png", width=220)[cite: 1, 2]
        except Exception:
            st.title("🍦 Kulfi Ops")[cite: 1, 2]

        st.subheader("Sign in")[cite: 1, 2]
        with st.form("login_form"):[cite: 1, 2]
            username = st.text_input("Username")[cite: 1, 2]
            password = st.text_input("Password", type="password")[cite: 1, 2]
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)[cite: 1, 2]

        if submitted:[cite: 1, 2]
            valid_user = st.secrets.get("app_username", "admin")[cite: 1, 2]
            valid_pass = st.secrets.get("app_password", None)[cite: 1, 2]

            if valid_pass is None:[cite: 1, 2]
                st.error("No `app_password` set in Secrets. Please add credentials to Secrets.")[cite: 1, 2]
            elif (
                hmac.compare_digest(username.strip(), valid_user.strip())
                and hmac.compare_digest(password, valid_pass)
            ):[cite: 1, 2]
                st.session_state["authenticated"] = True[cite: 1, 2]
                st.rerun()[cite: 1, 2]
            else:
                st.error("Incorrect username or password — try again.")[cite: 1, 2]

    return False[cite: 1, 2]


if not check_login():[cite: 1, 2]
    st.stop()[cite: 1, 2]

# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------
with st.sidebar:
    try:
        st.image("assets/logo.png", use_container_width=True)[cite: 1, 2]
    except Exception:
        st.markdown("## 🍦 Kulfi Ops")[cite: 1, 2]
    page = st.radio(
        "Go to",
        ["Dashboard", "Daily Entry", "Freezer Stock", "Freezer Analysis", "Expenses"],
        label_visibility="collapsed",
    )[cite: 1, 2]
    if page == "Dashboard":[cite: 2]
        st.markdown(
            textwrap.dedent(
                """
            <div class="dash-jump">
            <b>Jump to</b><br>
            <a href="#last-3-days">Last 3 days</a>
            <a href="#revenue-trend">Revenue trend (14 days)</a>
            <a href="#reports">Reports (date range)</a>
            <a href="#cart-wise-comparison">&nbsp;&nbsp;Cart-wise comparison</a>
            <a href="#cart-wise-day-of-week">&nbsp;&nbsp;Sales by day of week</a>
            <a href="#flavour-wise-performance">&nbsp;&nbsp;Flavour-wise performance</a>
            <a href="#profit-loss-summary">&nbsp;&nbsp;Profit &amp; loss summary</a>
            <a href="#expense-breakdown">&nbsp;&nbsp;Expense breakdown</a>
            <a href="#cash-vs-phonepe">&nbsp;&nbsp;Cash vs PhonePe</a>
            <a href="#sales-in-range">&nbsp;&nbsp;Sales table</a>
            <a href="#inventory-status">Current Inventory Status</a>
            <a href="#freezer-stock-current">&nbsp;&nbsp;Freezer stock (current)</a>
            <a href="#latest-stock-per-cart">&nbsp;&nbsp;Latest stock per cart</a>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )[cite: 2]
    st.markdown("---")[cite: 1, 2]
    if st.button("Log out", use_container_width=True):[cite: 1, 2]
        st.session_state["authenticated"] = False[cite: 1, 2]
        st.rerun()[cite: 1, 2]

st.title(f"🍦 Kulfi Ops — {page}")[cite: 1, 2]

# ---------------- DAILY ENTRY ----------------
if page == "Daily Entry":[cite: 1, 2]
    st.subheader("Cart restock & daily sales")[cite: 1, 2]

    try:
        daily_entries = list_daily_entries()[cite: 1, 2]
    except Exception as e:
        daily_entries = [][cite: 1, 2]
        st.warning(f"Could not load entries ({e}).")

    if not daily_entries:
        st.info("No past entries found in the sheet.")
    else:
        top_c1, top_c2 = st.columns([1.3, 1])

        labels = [f"{e['date'].strftime('%d %b %Y')} — {e['cart']}" for e in daily_entries][cite: 1, 2]
        with top_c1:
            sel = st.selectbox("Select entry to update sales", labels, key="daily_update_select")
        loaded = daily_entries[labels.index(sel)][cite: 1, 2]
        editing_row = loaded["row"][cite: 1, 2]
        entry_date = loaded["date"].date()
        cart_name = loaded["cart"]

        data_key_suffix = f"_{editing_row}"

        k_tot = f"daily_total{data_key_suffix}"
        k_ph = f"daily_phonepe{data_key_suffix}"
        k_cs = f"daily_cash{data_key_suffix}"
        k_adv = f"daily_adv{data_key_suffix}"
        k_food = f"daily_food{data_key_suffix}"
        k_staff = f"daily_staff{data_key_suffix}"
        k_prev_calc = f"daily_prev_calc{data_key_suffix}"

        staff_options = load_active_staff_list()

        # Retain previous day's staff name for this specific cart if empty
        default_staff_name = loaded.get("staff_name", "")
        if not default_staff_name:
            for past_e in daily_entries:
                if past_e["cart"] == cart_name and past_e.get("staff_name"):
                    default_staff_name = past_e["staff_name"]
                    break

        if default_staff_name and default_staff_name not in staff_options:
            staff_options.append(default_staff_name)

        default_staff_idx = staff_options.index(default_staff_name) if default_staff_name in staff_options else 0
        with top_c2:
            staff_name = st.selectbox("Cart staff name", staff_options, index=default_staff_idx, key=k_staff)

        opening = loaded["opening"][cite: 1, 2]

        st.write("Enter units **added to the cart** and the **actual closing count** observed:")[cite: 1]

        added = [0] * N_FLAVORS
        closing = [0] * N_FLAVORS

        # Render 100% responsive flavor cards
        for i, f in enumerate(FLAVORS):
            k_add = f"add_{editing_row}_{i}"
            k_cls = f"cls_{editing_row}_{i}"
            if k_add not in st.session_state:
                st.session_state[k_add] = loaded["added"][i]
            if k_cls not in st.session_state:
                st.session_state[k_cls] = loaded["closing"][i]

            cur_add = st.session_state[k_add]
            cur_cls = st.session_state[k_cls]
            cur_sold = opening[i] + cur_add - cur_cls

            st.markdown(
                f"""
                <div class="flavor-entry-row">
                    <div class="flavor-title-bar">
                        <span class="flavor-name">{f[1]} (₹{f[2]})</span>
                        <div>
                            <span class="badge-open">Opening: {opening[i]}</span>
                            <span class="badge-sold">Sold: {cur_sold}</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col_a, col_b = st.columns(2)
            with col_a:
                added_val = st.number_input("+ Added Stock", min_value=0, step=1, key=k_add)
            with col_b:
                closing_val = st.number_input("Closing Count", min_value=0, step=1, key=k_cls)

            added[i] = int(added_val)
            closing[i] = int(closing_val)

        sold = [opening[i] + added[i] - closing[i] for i in range(N_FLAVORS)][cite: 1]

        tot_open, tot_add, tot_close, tot_sold = sum(opening), sum(added), sum(closing), sum(sold)[cite: 1]
        m1, m2, m3, m4 = st.columns(4)[cite: 1]
        m1.metric("Opening Balance", f"{tot_open} units")[cite: 1]
        m2.metric("Stock Added", f"{tot_add} units")[cite: 1]
        m3.metric("Closing Balance", f"{tot_close} units")[cite: 1]
        m4.metric("Total Sold", f"{tot_sold} units")[cite: 1]

        if any(s < 0 for s in sold):[cite: 1]
            st.error("Today's sales works out negative for at least one flavour - closing count is higher than opening + added.")[cite: 1]

        calculated_mrp_total = float(sum(sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS)))[cite: 1]

        if k_tot not in st.session_state or st.session_state.get(k_prev_calc) != calculated_mrp_total:
            st.session_state[k_tot] = f"{calculated_mrp_total:.2f}"
            st.session_state[k_prev_calc] = calculated_mrp_total

        if k_ph not in st.session_state:
            st.session_state[k_ph] = f"{loaded['phonepe']:.2f}"

        if k_adv not in st.session_state:
            st.session_state[k_adv] = f"{loaded['staff_advance']:.2f}" if "staff_advance" in loaded else "0.00"

        if k_food not in st.session_state:
            st.session_state[k_food] = f"{loaded['food_tea_cash']:.2f}" if "food_tea_cash" in loaded else "0.00"

        if k_cs not in st.session_state:
            st.session_state[k_cs] = f"{loaded['cash']:.2f}"

        st.markdown("---")[cite: 1, 2]
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

        # Cash Leakage = Total Collection - PhonePe - Advance to staff - cash paid for Food/Tea - Cash Collected
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
            if sum(added) == 0 and closing == opening:[cite: 1]
                st.error("Enter a stock addition or a closing count that differs from yesterday's balance before saving.")[cite: 1]
            elif any(s < 0 for s in sold):[cite: 1]
                st.error("Today's sales works out negative for at least one flavour - fix closing count before saving.")[cite: 1]
            elif has_leakage and not remarks.strip():
                st.error("Remarks is mandatory when there is a cash leakage. Please enter a reason.")
            else:
                try:
                    selected_staff = "" if staff_name == "Select Staff" else staff_name
                    saved_sold = update_daily_entry(
                        editing_row, entry_date, cart_name, added, closing, opening, 
                        total_collection_val, phonepe_val, cash_val, remarks, selected_staff, staff_advance_val, food_tea_val
                    )
                    st.cache_resource.clear()[cite: 1, 2]
                    show_success_modal(f"Saved successfully! Sales updated for {cart_name} on {entry_date.strftime('%d %b %Y')}. Total Sold: {sum(saved_sold)} units.")
                except Exception as e:
                    st.error(f"Could not save - {e}")[cite: 1, 2]

# ---------------- FREEZER STOCK ----------------
elif page == "Freezer Stock":[cite: 1, 2]
    st.subheader("Stock received into freezer")[cite: 1, 2]

    stock_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="stock_mode")[cite: 1, 2]

    stock_loaded = None[cite: 1, 2]
    stock_editing_row = None[cite: 1, 2]
    if stock_mode == "Edit past entry":[cite: 1, 2]
        try:
            stock_entries = list_stock_entries()[cite: 1, 2]
        except Exception as e:
            stock_entries = [][cite: 1, 2]
            st.warning(f"Could not load past entries ({e}).")[cite: 1, 2]
        if not stock_entries:[cite: 1, 2]
            st.info("No past entries found yet.")[cite: 1, 2]
        else:
            def _fmt_order_date(s):
                if not s or not str(s).strip():[cite: 1, 2]
                    return "no order date"[cite: 1, 2]
                try:
                    d = pd.to_datetime(s)[cite: 1, 2]
                    return f"ordered {d.strftime('%d %b %Y')}" if not pd.isna(d) else "no order date"[cite: 1, 2]
                except Exception:
                    return "no order date"[cite: 1, 2]

            stock_labels = [
                f"Received {e['received_date'].strftime('%d %b %Y')} ({_fmt_order_date(e['order_date'])}) — {e['location']}"
                for e in stock_entries
            ][cite: 1, 2]
            stock_sel = st.selectbox("Select entry to edit", stock_labels, key="stock_edit_select")[cite: 1, 2]
            stock_loaded = stock_entries[stock_labels.index(stock_sel)][cite: 1, 2]
            stock_editing_row = stock_loaded["row"][cite: 1, 2]
            st.caption("Loaded - edit fields below, then click Update entry.")[cite: 1, 2]

    sk = f"_{stock_editing_row}" if stock_editing_row else "_new"[cite: 1, 2]
    st.caption("Log a supplier delivery. Ordered and Damaged are optional.")[cite: 1]

    def _parse_date_or(s, fallback):
        if not s or not str(s).strip():[cite: 1, 2]
            return fallback[cite: 1, 2]
        try:
            d = pd.to_datetime(s)[cite: 1, 2]
            return fallback if pd.isna(d) else d.date()[cite: 1, 2]
        except Exception:
            return fallback[cite: 1, 2]

    c1, c2, c3 = st.columns(3)[cite: 1, 2]
    with c1:
        order_date = st.date_input(
            "Order date",
            value=_parse_date_or(stock_loaded["order_date"], date.today()) if stock_loaded else date.today(),
            key=f"stock_order_date{sk}",
        )[cite: 1, 2]
    with c2:
        received_date = st.date_input(
            "Received date",
            value=stock_loaded["received_date"].date() if stock_loaded else date.today(),
            key=f"stock_received_date{sk}",
        )[cite: 1, 2]
    with c3:
        location = st.text_input("Location", value=(stock_loaded["location"] if stock_loaded else CITY), key=f"stock_location{sk}")[cite: 1, 2]

    flavor_names = [f[1] for f in FLAVORS][cite: 1, 2]
    df_init = pd.DataFrame(
        {
            "Flavour": flavor_names,
            "Ordered": stock_loaded["ordered"] if stock_loaded else [0] * N_FLAVORS,
            "Received": stock_loaded["received"] if stock_loaded else [0] * N_FLAVORS,
            "Cost (₹, total)": stock_loaded["cost"] if stock_loaded else [0.0] * N_FLAVORS,
            "Damaged": stock_loaded["damaged"] if stock_loaded else [0] * N_FLAVORS,
        }
    )[cite: 1, 2]
    st.write("Enter units per flavour:")[cite: 1, 2]
    stock_edited = st.data_editor(
        df_init,
        column_config={
            "Flavour": st.column_config.TextColumn(disabled=True),
            "Ordered": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            "Received": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
            "Cost (₹, total)": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="₹%.2f"),
            "Damaged": st.column_config.NumberColumn(min_value=0, step=1, format="%d"),
        },
        hide_index=True,
        use_container_width=True,
        key=f"stock_editor{sk}",
    )[cite: 1, 2]

    ordered = stock_edited["Ordered"].fillna(0).astype(int).tolist()[cite: 1, 2]
    received = stock_edited["Received"].fillna(0).astype(int).tolist()[cite: 1, 2]
    cost = stock_edited["Cost (₹, total)"].fillna(0).astype(float).tolist()[cite: 1, 2]
    damaged = stock_edited["Damaged"].fillna(0).astype(int).tolist()[cite: 1, 2]

    st.caption(
        "Standard cost price per unit — Malai ₹22, Mini Malai ₹18, Pista ₹22, Mango ₹22, "
        "Kesar Badam ₹27.5, Badam Matka ₹44, Shahi Gulab ₹27.5, Chocolate ₹27.5, Roasted Almond ₹33."
    )[cite: 1]

    st.markdown("---")[cite: 1, 2]
    st.write("**Payment**")[cite: 1, 2]
    c4, c5 = st.columns(2)[cite: 1, 2]
    with c4:
        default_payment_amount = stock_loaded["payment_amount"] if stock_loaded else float(sum(cost))[cite: 1, 2]
        payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=float(default_payment_amount), step=10.0, key=f"stock_pay_amt{sk}")[cite: 1, 2]
    with c5:
        default_status_idx = PAYMENT_STATUSES.index(stock_loaded["payment_status"]) if stock_loaded and stock_loaded["payment_status"] in PAYMENT_STATUSES else 0[cite: 1, 2]
        payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=default_status_idx, key=f"stock_pay_status{sk}")[cite: 1, 2]

    has_payment_date = st.checkbox("Add payment date", value=bool(stock_loaded and stock_loaded["payment_date"]), key=f"stock_has_paydate{sk}")[cite: 1, 2]
    payment_date = (
        st.date_input(
            "Payment date",
            value=_parse_date_or(stock_loaded["payment_date"], date.today()) if (stock_loaded and stock_loaded["payment_date"]) else date.today(),
            key=f"stock_payment_date{sk}",
        )
        if has_payment_date
        else None
    )[cite: 1, 2]
    payment_details = st.text_input("Payment details (optional)", value=(stock_loaded["payment_details"] if stock_loaded else ""), key=f"stock_pay_details{sk}")[cite: 1, 2]

    has_damaged_return = st.checkbox("Damaged items were returned", value=bool(stock_loaded and stock_loaded["damaged_returned_on"]), key=f"stock_has_damret{sk}")[cite: 1, 2]
    damaged_returned_on = (
        st.date_input(
            "Damaged items returned on",
            value=_parse_date_or(stock_loaded["damaged_returned_on"], date.today()) if (stock_loaded and stock_loaded["damaged_returned_on"]) else date.today(),
            key=f"stock_damaged_date{sk}",
        )
        if has_damaged_return
        else None
    )[cite: 1, 2]

    notes = st.text_input("Notes (optional)", value=(stock_loaded["notes"] if stock_loaded else ""), key=f"stock_notes{sk}")[cite: 1, 2]

    stock_button_label = "Update entry" if stock_editing_row else "Save stock received"[cite: 1, 2]
    if st.button(stock_button_label, type="primary", use_container_width=True):[cite: 1, 2]
        if sum(received) == 0:[cite: 1, 2]
            st.error("Enter at least one quantity received before saving.")[cite: 1, 2]
        else:
            try:
                if stock_editing_row:[cite: 1, 2]
                    update_stock_entry(
                        stock_editing_row, order_date, received_date, location,
                        ordered, received, cost, damaged,
                        payment_amount, payment_status, payment_date, payment_details,
                        damaged_returned_on, notes,
                    )[cite: 1, 2]
                    st.cache_resource.clear()[cite: 1, 2]
                    show_success_modal(f"Saved successfully! Updated entry for {received_date.strftime('%d %b %Y')} at {location}.")
                else:
                    append_stock_entry(
                        order_date, received_date, location,
                        ordered, received, cost, damaged,
                        payment_amount, payment_status, payment_date, payment_details,
                        damaged_returned_on, notes,
                    )[cite: 1, 2]
                    st.cache_resource.clear()[cite: 1, 2]
                    show_success_modal(f"Saved successfully! Logged {sum(received)} units received on {received_date.strftime('%d %b %Y')}.")
            except Exception as e:
                st.error(f"Could not save - {e}")[cite: 1, 2]

# ---------------- FREEZER ANALYSIS ----------------
elif page == "Freezer Analysis":[cite: 1, 2]
    st.subheader("Freezer stock analysis & reorder planner")[cite: 1, 2]
    st.caption("Uses recent sales pace to estimate when freezer stock runs low.")[cite: 1]

    ac1, ac2, ac3 = st.columns(3)[cite: 1, 2]
    with ac1:
        lookback_days = st.number_input("Lookback window for avg. daily sales (days)", min_value=3, max_value=90, value=14, step=1)[cite: 1, 2]
    with ac2:
        buffer_days = st.number_input("Minimum buffer to maintain (days)", min_value=0, max_value=14, value=3, step=1)[cite: 1, 2]
    with ac3:
        cover_days = st.number_input("Next order should cover (days)", min_value=1, max_value=30, value=7, step=1)[cite: 1, 2]

    try:
        daily_df_fa = load_daily_df()[cite: 1, 2]
        freezer_stock_fa = get_freezer_stock()[cite: 1, 2]
    except Exception as e:
        daily_df_fa = pd.DataFrame()[cite: 1, 2]
        freezer_stock_fa = [0] * N_FLAVORS[cite: 1, 2]
        st.warning(f"Could not load data yet ({e}).")[cite: 1, 2]

    if daily_df_fa.empty:[cite: 1]
        st.info("No sales logged yet.")[cite: 1]
    else:
        today_fa = date.today()[cite: 1, 2]
        cutoff_fa = today_fa - timedelta(days=lookback_days - 1)[cite: 1, 2]
        window_df = daily_df_fa[(daily_df_fa["Date"].dt.date >= cutoff_fa) & (daily_df_fa["Date"].dt.date <= today_fa)][cite: 1, 2]

        flavor_sold_window = [0] * N_FLAVORS[cite: 1, 2]
        for arr in window_df["Sold_By_Flavor"]:[cite: 1, 2]
            for i in range(N_FLAVORS):[cite: 1, 2]
                flavor_sold_window[i] += arr[i][cite: 1, 2]
        avg_daily = [s / lookback_days for s in flavor_sold_window][cite: 1, 2]

        rows = [][cite: 1, 2]
        trigger_dates = [][cite: 1, 2]
        for i, f in enumerate(FLAVORS):[cite: 1, 2]
            stock = freezer_stock_fa[i][cite: 1, 2]
            rate = avg_daily[i][cite: 1, 2]
            if rate <= 0:[cite: 1, 2]
                days_left = None[cite: 1, 2]
                status = "No recent sales"[cite: 1, 2]
                trigger_date = None[cite: 1, 2]
                suggested_qty = 0[cite: 1, 2]
            else:
                days_left = stock / rate[cite: 1, 2]
                trigger_date = today_fa + timedelta(days=max(0, days_left - buffer_days))[cite: 1, 2]
                trigger_dates.append(trigger_date)[cite: 1, 2]
                if days_left <= buffer_days:[cite: 1, 2]
                    status = "Order now"[cite: 1, 2]
                elif days_left <= buffer_days + 2:[cite: 1, 2]
                    status = "Order soon"[cite: 1, 2]
                else:
                    status = "OK"[cite: 1, 2]
                suggested_qty = int(round(rate * cover_days / 10.0)) * 10[cite: 1, 2]

            rows.append(
                {
                    "Flavour": f[1],
                    "Freezer stock": stock,
                    "Avg. daily sales": round(rate),
                    "Days of stock left": round(days_left) if days_left is not None else "—",
                    "Status": status,
                    f"Suggested next order ({cover_days}d)": suggested_qty,
                }
            )[cite: 1, 2]

        analysis_df = pd.DataFrame(rows)[cite: 1, 2]
        total_stock = sum(freezer_stock_fa)[cite: 1, 2]
        total_rate = sum(avg_daily)[cite: 1, 2]
        overall_days_left = (total_stock / total_rate) if total_rate > 0 else None[cite: 1, 2]
        overall_order_date = min(trigger_dates) if trigger_dates else None[cite: 1, 2]

        st.markdown("### Overall picture")[cite: 1, 2]
        oc1, oc2, oc3 = st.columns(3)[cite: 1, 2]
        oc1.metric("Total freezer stock", f"{total_stock} units")[cite: 1, 2]
        oc2.metric("Avg. daily sales (all flavours)", f"{total_rate:.0f} units/day")[cite: 1, 2]
        oc3.metric("Overall days of stock left", f"{overall_days_left:.0f}" if overall_days_left is not None else "—")[cite: 1, 2]

        if overall_order_date is not None:[cite: 1, 2]
            if overall_order_date <= today_fa:[cite: 1, 2]
                st.error(f"**Place your next order now** — at least one flavour is at or below your {buffer_days}-day buffer.")[cite: 1, 2]
            else:
                days_until = (overall_order_date - today_fa).days[cite: 1, 2]
                st.success(f"**Next order by {overall_order_date.strftime('%d %b %Y')}** (in {days_until} days).")[cite: 1]

        st.markdown("### Per-flavour breakdown")[cite: 1, 2]
        st.dataframe(analysis_df, hide_index=True, use_container_width=True)[cite: 1]

        st.markdown("### Suggested next order")[cite: 1, 2]
        order_df = analysis_df[["Flavour", f"Suggested next order ({cover_days}d)"]].rename(
            columns={f"Suggested next order ({cover_days}d)": "Units to order"}
        )[cite: 1, 2]
        st.dataframe(order_df, hide_index=True, use_container_width=True)[cite: 1, 2]

        st.markdown("### Days of stock left, by flavour")[cite: 1, 2]
        chart_df = analysis_df[analysis_df["Days of stock left"] != "—"].copy()[cite: 1, 2]
        if not chart_df.empty:[cite: 1, 2]
            chart_df["Days of stock left"] = chart_df["Days of stock left"].astype(float)[cite: 1, 2]
            days_chart = (
                alt.Chart(chart_df)
                .mark_bar()
                .encode(
                    x=alt.X("Flavour:N", sort="-y"),
                    y=alt.Y("Days of stock left:Q"),
                    color=alt.condition(
                        alt.datum["Days of stock left"] <= buffer_days,
                        alt.value("#C43D17"),
                        alt.value("#C9932E"),
                    ),
                    tooltip=["Flavour", "Days of stock left"],
                )
                .properties(height=280)
            )[cite: 1, 2]
            rule = alt.Chart(pd.DataFrame({"y": [buffer_days]})).mark_rule(color="#4A2418", strokeDash=[4, 4]).encode(y="y:Q")[cite: 1, 2]
            st.altair_chart(days_chart + rule, use_container_width=True)[cite: 1, 2]

# ---------------- EXPENSES ----------------
elif page == "Expenses":[cite: 1, 2]
    st.subheader("Log an expense")[cite: 1, 2]

    exp_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="exp_mode")[cite: 1, 2]

    exp_loaded = None[cite: 1, 2]
    exp_editing_row = None[cite: 1, 2]
    if exp_mode == "Edit past entry":[cite: 1, 2]
        try:
            expense_entries = list_expense_entries()[cite: 1, 2]
        except Exception as e:
            expense_entries = [][cite: 1, 2]
            st.warning(f"Could not load past entries ({e}).")[cite: 1, 2]
        if not expense_entries:[cite: 1, 2]
            st.info("No past entries found yet.")[cite: 1, 2]
        else:
            exp_labels = [f"{e['date'].strftime('%d %b %Y')} — {e['description'] or e['category']} (₹{e['amount']:,.0f})" for e in expense_entries][cite: 1, 2]
            exp_sel = st.selectbox("Select entry to edit", exp_labels, key="exp_edit_select")[cite: 1, 2]
            exp_loaded = expense_entries[exp_labels.index(exp_sel)][cite: 1, 2]
            exp_editing_row = exp_loaded["row"][cite: 1, 2]
            st.caption("Loaded - edit fields below, then click Update entry.")[cite: 1, 2]

    ek = f"_{exp_editing_row}" if exp_editing_row else "_new"[cite: 1, 2]

    c1, c2 = st.columns(2)[cite: 1, 2]
    with c1:
        exp_date = st.date_input("Date", value=(exp_loaded["date"].date() if exp_loaded else date.today()), key=f"exp_date{ek}")[cite: 1, 2]
    with c2:
        default_cat_idx = EXPENSE_CATEGORIES.index(exp_loaded["category"]) if exp_loaded and exp_loaded["category"] in EXPENSE_CATEGORIES else 0[cite: 1, 2]
        category = st.selectbox("Category", EXPENSE_CATEGORIES, index=default_cat_idx, key=f"exp_category{ek}")[cite: 1, 2]

    description = st.text_input("Description", value=(exp_loaded["description"] if exp_loaded else ""), key=f"exp_desc{ek}")[cite: 1, 2]
    amount = st.number_input("Amount (₹)", min_value=0.0, value=(float(exp_loaded["amount"]) if exp_loaded else 0.0), step=10.0, key=f"exp_amount{ek}")[cite: 1, 2]

    c3, c4 = st.columns(2)[cite: 1, 2]
    with c3:
        default_mode_idx = PAYMENT_MODES.index(exp_loaded["mode"]) if exp_loaded and exp_loaded["mode"] in PAYMENT_MODES else 0[cite: 1, 2]
        mode = st.selectbox("Payment mode", PAYMENT_MODES, index=default_mode_idx, key=f"exp_mode_select{ek}")[cite: 1, 2]
    with c4:
        ref_no = st.text_input("Transaction ref. no. (optional)", value=(exp_loaded["ref_no"] if exp_loaded else ""), key=f"exp_ref{ek}")[cite: 1, 2]

    paid_to = st.text_input("Paid to (optional)", value=(exp_loaded["paid_to"] if exp_loaded else ""), key=f"exp_paidto{ek}")[cite: 1, 2]
    exp_remarks = st.text_input("Remarks (optional)", value=(exp_loaded["remarks"] if exp_loaded else ""), key=f"exp_remarks{ek}")[cite: 1, 2]

    exp_button_label = "Update entry" if exp_editing_row else "Save expense"[cite: 1, 2]
    if st.button(exp_button_label, type="primary", use_container_width=True):[cite: 1, 2]
        if amount <= 0:[cite: 1, 2]
            st.error("Enter an amount greater than 0.")[cite: 1, 2]
        else:
            try:
                if exp_editing_row:[cite: 1, 2]
                    update_expense(exp_editing_row, exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)[cite: 1, 2]
                    st.cache_resource.clear()[cite: 1, 2]
                    show_success_modal(f"Saved successfully! Updated ₹{amount:,.0f} expense under {category}.")
                else:
                    append_expense(exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)[cite: 1, 2]
                    st.cache_resource.clear()[cite: 1, 2]
                    show_success_modal(f"Saved successfully! Logged ₹{amount:,.0f} expense under {category}.")
            except Exception as e:
                st.error(f"Could not save - {e}")[cite: 1, 2]

# ---------------- DASHBOARD ----------------
elif page == "Dashboard":[cite: 1, 2]
    st.subheader("Quick view")[cite: 1, 2]

    try:
        daily_df = load_daily_df()[cite: 1, 2]
        exp_df = load_expenses_df()[cite: 1, 2]
    except Exception as e:
        daily_df = pd.DataFrame()[cite: 1, 2]
        exp_df = pd.DataFrame()[cite: 1, 2]
        st.warning(f"Could not load data yet ({e}).")[cite: 1, 2]

    today = pd.Timestamp(date.today())[cite: 1, 2]
    day_labels = [today - pd.Timedelta(days=3), today - pd.Timedelta(days=2), today - pd.Timedelta(days=1)][cite: 1, 2]
    if not daily_df.empty:[cite: 1, 2]
        day_rows = [daily_df[daily_df["Date"].dt.date == d.date()] for d in day_labels][cite: 1, 2]
        day_rev = [r["Total_Collection"].sum() for r in day_rows][cite: 1, 2]
        day_units = [int(r["Sold_Total"].sum()) for r in day_rows][cite: 1, 2]

        col_names = [d.strftime("%d %b") for d in day_labels][cite: 1, 2]
        col_names[-1] = col_names[-1] + " (Yesterday)"[cite: 1, 2]

        compare_df = pd.DataFrame(
            {
                "Metric": ["Revenue", "Units sold"],
                col_names[0]: [f"₹{day_rev[0]:,.0f}", f"{day_units[0]}"],
                col_names[1]: [f"₹{day_rev[1]:,.0f}", f"{day_units[1]}"],
                col_names[2]: [f"₹{day_rev[2]:,.0f}", f"{day_units[2]}"],
            }
        )[cite: 1, 2]
        st.markdown('<div id="last-3-days"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("**Last 3 days**")[cite: 1, 2]
        st.dataframe(compare_df, hide_index=True, use_container_width=True)[cite: 1, 2]

        st.markdown('<div id="revenue-trend"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("**Revenue, last 14 days**")[cite: 1, 2]
        trend_df = (
            daily_df.assign(Day=daily_df["Date"].dt.normalize())
            .groupby("Day", as_index=False)["Total_Collection"]
            .sum()
            .sort_values("Day")
            .tail(14)
        )[cite: 1, 2]
        trend_chart = (
            alt.Chart(trend_df)
            .mark_bar(color="#E8542A")
            .encode(
                x=alt.X("Day:T", title="", axis=alt.Axis(format="%d %b", labelAngle=-45)),
                y=alt.Y("Total_Collection:Q", title="Revenue (₹)"),
                tooltip=[alt.Tooltip("Day:T", title="Date", format="%d %b %Y"), alt.Tooltip("Total_Collection:Q", title="Revenue", format=",.0f")],
            )
            .properties(height=280)
        )[cite: 1]
        st.altair_chart(trend_chart, use_container_width=True)[cite: 1, 2]
    else:
        st.info("No sales logged yet.")[cite: 1]

    # ------------------ Date-range reports ------------------
    if not daily_df.empty or not exp_df.empty:[cite: 2]
        st.markdown("---")[cite: 1, 2]
        st.markdown('<div id="reports"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("## Reports")[cite: 2]

        all_dates = [][cite: 2]
        if not daily_df.empty:[cite: 2]
            all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()][cite: 2]
        if not exp_df.empty and exp_df["Date"].notna().any():[cite: 2]
            all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()][cite: 2]
        min_d, max_d = min(all_dates), max(all_dates)[cite: 2]
        default_start = max(min_d, max_d - timedelta(days=29))[cite: 2]

        if "applied_start" not in st.session_state:[cite: 2]
            st.session_state["applied_start"] = default_start[cite: 2]
        if "applied_end" not in st.session_state:[cite: 2]
            st.session_state["applied_end"] = max_d[cite: 2]
        st.session_state["applied_start"] = min(max(st.session_state["applied_start"], min_d), max_d)[cite: 2]
        st.session_state["applied_end"] = min(max(st.session_state["applied_end"], min_d), max_d)[cite: 2]

        with st.form("date_range_form"):[cite: 2]
            rc1, rc2, rc3 = st.columns([2, 2, 1])[cite: 2]
            with rc1:
                pending_start = st.date_input("From", value=st.session_state["applied_start"], min_value=min_d, max_value=max_d)[cite: 2]
            with rc2:
                pending_end = st.date_input("To", value=st.session_state["applied_end"], min_value=min_d, max_value=max_d)[cite: 2]
            with rc3:
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)[cite: 2]
                apply_clicked = st.form_submit_button("Apply", type="primary", use_container_width=True)[cite: 2]

        if apply_clicked:[cite: 2]
            st.session_state["applied_start"] = pending_start[cite: 2]
            st.session_state["applied_end"] = pending_end[cite: 2]

        range_start = st.session_state["applied_start"][cite: 2]
        range_end = st.session_state["applied_end"][cite: 2]

        if range_start > range_end:[cite: 2]
            st.error("'From' date is after 'To' date - swap them and click Apply again.")[cite: 2]
            range_start, range_end = range_end, range_start[cite: 2]

        st.caption(f"Showing: {range_start.strftime('%d %b %Y')} – {range_end.strftime('%d %b %Y')}")[cite: 2]

        range_df = daily_df[(daily_df["Date"].dt.date >= range_start) & (daily_df["Date"].dt.date <= range_end)] if not daily_df.empty else daily_df[cite: 2]
        range_exp = exp_df[(exp_df["Date"].dt.date >= range_start) & (exp_df["Date"].dt.date <= range_end)] if not exp_df.empty else exp_df[cite: 2]

        total_rev = range_df["Total_Collection"].sum() if not range_df.empty else 0.0[cite: 2]
        total_units = int(range_df["Sold_Total"].sum()) if not range_df.empty else 0[cite: 2]
        total_exp_all = range_exp["Amount"].sum() if not range_exp.empty else 0.0[cite: 2]

        mc1, mc2, mc3 = st.columns(3)[cite: 2]
        mc1.metric("Revenue in range", f"₹{total_rev:,.0f}")[cite: 2]
        mc2.metric("Units sold in range", f"{total_units}")[cite: 2]
        mc3.metric("Expenses in range", f"₹{total_exp_all:,.0f}")[cite: 2]

        # ---- Cart-wise comparison ----
        st.markdown('<div id="cart-wise-comparison"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Cart-wise comparison")[cite: 2]
        if not range_df.empty:[cite: 2]
            cart_grp = (
                range_df.groupby("Cart")
                .agg(**{"Revenue (₹)": ("Total_Collection", "sum"), "Units sold": ("Sold_Total", "sum")})
                .reset_index()
                .sort_values("Revenue (₹)", ascending=False)
            )[cite: 2]
            st.dataframe(cart_grp, hide_index=True, use_container_width=True)[cite: 2]
            st.bar_chart(cart_grp.set_index("Cart")["Revenue (₹)"])[cite: 2]
        else:
            st.caption("No sales in this date range.")[cite: 2]

        # ---- Cart-wise x day-of-week sales ----
        st.markdown('<div id="cart-wise-day-of-week"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Cart-wise average sales by day of the week")[cite: 2]
        if not range_df.empty:[cite: 2]
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][cite: 2]
            dow_df = range_df[range_df["Sold_Total"] > 0].copy()[cite: 2]
            dow_df["Day"] = dow_df["Date"].dt.day_name()[cite: 2]

            if dow_df.empty:[cite: 2]
                st.caption("No days with actual sales in this date range.")[cite: 2]
            else:
                units_pivot = dow_df.pivot_table(
                    index="Cart", columns="Day", values="Sold_Total", aggfunc="mean", fill_value=0, margins=True, margins_name="All carts"
                )[cite: 2]
                day_cols = [d for d in day_order if d in units_pivot.columns] + ["All carts"][cite: 2]
                units_pivot = units_pivot.reindex(columns=day_cols)[cite: 2]

                rev_pivot = dow_df.pivot_table(
                    index="Cart", columns="Day", values="Total_Collection", aggfunc="mean", fill_value=0, margins=True, margins_name="All carts"
                )[cite: 2]
                rev_pivot = rev_pivot.reindex(columns=day_cols)[cite: 2]

                st.write("**Avg. units sold** (rows = cart, columns = day of week)")[cite: 2]
                st.dataframe(units_pivot.round(1), use_container_width=True)[cite: 2]

                st.write("**Avg. revenue (₹)** (rows = cart, columns = day of week)")[cite: 2]
                st.dataframe(rev_pivot.round(0).astype(int), use_container_width=True)[cite: 2]

                st.caption("Zero-sales days are excluded, so each cell is the average over the days that weekday actually had sales. 'All carts' shows the overall average across carts / days.")[cite: 2]
        else:
            st.caption("No sales in this date range.")[cite: 2]

        # ---- Flavour-wise performance ----
        st.markdown('<div id="flavour-wise-performance"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Flavour-wise performance")[cite: 2]
        if not range_df.empty:[cite: 2]
            flavor_sold = [0] * N_FLAVORS[cite: 2]
            for arr in range_df["Sold_By_Flavor"]:[cite: 2]
                for i in range(N_FLAVORS):[cite: 2]
                    flavor_sold[i] += arr[i][cite: 2]
            flavor_df = pd.DataFrame(
                {
                    "Flavour": [f[1] for f in FLAVORS],
                    "Units sold": flavor_sold,
                    "Est. revenue (₹)": [flavor_sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS)],
                }
            ).sort_values("Units sold", ascending=False)[cite: 2]
            st.dataframe(flavor_df, hide_index=True, use_container_width=True)[cite: 2]
            st.bar_chart(flavor_df.set_index("Flavour")["Units sold"])[cite: 2]
            st.caption("Estimated revenue = units sold × MRP per flavour; actual collections may vary slightly (discounts, complementary pieces etc).")[cite: 2]
        else:
            st.caption("No sales in this date range.")[cite: 2]

        # ---- Profit & Loss summary ----
        st.markdown('<div id="profit-loss-summary"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Profit & loss summary")[cite: 2]
        cogs = range_exp[range_exp["Category"] == "Cost of Goods"]["Amount"].sum() if not range_exp.empty else 0.0[cite: 2]
        opex_cats = ["Labour Charges", "Leakage Expense", "Miscellaneous Expense"][cite: 2]
        opex = range_exp[range_exp["Category"].isin(opex_cats)]["Amount"].sum() if not range_exp.empty else 0.0[cite: 2]
        capital_cats = ["Initial Investment", "Initial Set-up Expense"][cite: 2]
        capital = range_exp[range_exp["Category"].isin(capital_cats)]["Amount"].sum() if not range_exp.empty else 0.0[cite: 2]
        gross_profit = total_rev - cogs[cite: 2]
        net_profit = gross_profit - opex[cite: 2]

        pnl_df = pd.DataFrame(
            {
                "Line item": ["Revenue", "Cost of Goods", "Gross profit", "Operating expenses (labour, leakage, misc.)", "Net profit"],
                "Amount (₹)": [total_rev, -cogs, gross_profit, -opex, net_profit],
            }
        )[cite: 2]
        st.dataframe(pnl_df, hide_index=True, use_container_width=True)[cite: 2]
        pc1, pc2 = st.columns(2)[cite: 2]
        pc1.metric("Net profit", f"₹{net_profit:,.0f}")[cite: 2]
        pc2.metric("Margin", f"{(net_profit / total_rev * 100) if total_rev else 0:.1f}%")[cite: 2]
        if capital > 0:[cite: 2]
            st.caption(f"₹{capital:,.0f} of one-time capital/setup costs fell in this range and is shown separately below, not deducted above.")[cite: 2]

        # ---- Expense breakdown ----
        st.markdown('<div id="expense-breakdown"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Expense breakdown by category")[cite: 2]
        if not range_exp.empty:[cite: 2]
            by_cat = range_exp.groupby("Category")["Amount"].sum().sort_values(ascending=False)[cite: 2]
            st.dataframe(
                by_cat.reset_index().rename(columns={"Amount": "₹"}),
                hide_index=True,
                use_container_width=True,
                column_config={"₹": st.column_config.ProgressColumn("Share", format="₹%.0f", min_value=0, max_value=float(by_cat.max()))},
            )[cite: 2]
            st.bar_chart(by_cat)[cite: 2]
        else:
            st.caption("No expenses logged in this date range.")[cite: 2]

        # ---- Cash vs PhonePe vs Advance vs Food/Tea ----
        st.markdown('<div id="cash-vs-phonepe"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Cash vs PhonePe / UPI vs Advance vs Food/Tea")
        if not range_df.empty:[cite: 2]
            total_cash = range_df["Cash"].sum()[cite: 2]
            total_phonepe = range_df["PhonePe"].sum()[cite: 2]
            total_advance = range_df["Staff_Advance"].sum() if "Staff_Advance" in range_df.columns else 0.0
            total_food = range_df["Food_Tea_Cash"].sum() if "Food_Tea_Cash" in range_df.columns else 0.0

            cc1, cc2, cc3, cc4 = st.columns(4)
            cc1.metric("Cash", f"₹{total_cash:,.0f}")[cite: 2]
            cc2.metric("PhonePe / UPI", f"₹{total_phonepe:,.0f}")[cite: 2]
            cc3.metric("Staff Advance", f"₹{total_advance:,.0f}")
            cc4.metric("Food / Tea", f"₹{total_food:,.0f}")

            split_df = pd.DataFrame({
                "Mode": ["Cash", "PhonePe / UPI", "Staff Advance", "Food / Tea"], 
                "Amount (₹)": [total_cash, total_phonepe, total_advance, total_food]
            })
            st.bar_chart(split_df.set_index("Mode")["Amount (₹)"])[cite: 2]
        else:
            st.caption("No collections in this date range.")[cite: 2]

        # ---- Date-range sales table ----
        st.markdown('<div id="sales-in-range"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("### Sales in this range")[cite: 2]
        if not range_df.empty:[cite: 2]
            display_cols = ["Date", "Cart", "Sold_Total", "Total_Collection", "PhonePe", "Cash", "Staff_Name", "Staff_Advance", "Food_Tea_Cash"]
            sales_table = range_df.sort_values(["Date", "Cart"])[display_cols].rename(
                columns={
                    "Sold_Total": "Units sold", 
                    "Total_Collection": "Revenue (₹)",
                    "PhonePe": "PhonePe (₹)",
                    "Cash": "Cash (₹)",
                    "Staff_Name": "Staff Name",
                    "Staff_Advance": "Staff Advance (₹)",
                    "Food_Tea_Cash": "Food / Tea (₹)"
                }
            )[cite: 2]
            sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")[cite: 2]
            st.dataframe(sales_table, hide_index=True, use_container_width=True)[cite: 2]
        else:
            st.caption("No sales in this date range.")[cite: 2]

    # ------------------ Current Inventory Status ------------------
    if not daily_df.empty:[cite: 2]
        st.markdown("---")[cite: 1, 2]
        st.markdown('<div id="inventory-status"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("## Current Inventory Status")[cite: 2]

        st.metric("Stock across carts", f"{int(daily_df.sort_values('Date').groupby('Cart').tail(1)['Closing_Total'].sum())}")[cite: 2]

        try:
            freezer_stock = get_freezer_stock()[cite: 1, 2]
            st.markdown('<div id="freezer-stock-current"></div>', unsafe_allow_html=True)[cite: 2]
            st.markdown("**Freezer stock (current)**")[cite: 2]
            freezer_df = pd.DataFrame({"Flavour": [f[1] for f in FLAVORS], "Units in freezer": freezer_stock})[cite: 2]
            st.dataframe(freezer_df, hide_index=True, use_container_width=True)[cite: 2]
        except Exception as e:
            st.caption(f"Could not compute freezer stock ({e}).")[cite: 2]

        st.markdown('<div id="latest-stock-per-cart"></div>', unsafe_allow_html=True)[cite: 2]
        st.markdown("**Latest stock per cart**")[cite: 2]
        latest_per_cart = daily_df.sort_values("Date").groupby("Cart").tail(1)[["Cart", "Date", "Closing_Total"]][cite: 2]
        st.dataframe(latest_per_cart, hide_index=True, use_container_width=True)[cite: 2]