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
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Manrope:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0 !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 1.5rem !important;
    }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    h1, h2, h3 { font-family: 'Fraunces', serif !important; color: #8A5E17 !important; letter-spacing: -0.01em; }
    h1 { font-size: 2.3rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }
    p, span, label, .stMarkdown { color: #2A1B10; }

    section[data-testid="stSidebar"] { font-size: 17px; border-right: 1px solid #E3CBA0; }
    section[data-testid="stSidebar"] h2 { font-size: 23px !important; color: #8A5E17 !important; }
    section[data-testid="stSidebar"] .stRadio > div { gap: 4px; }
    section[data-testid="stSidebar"] .stRadio label {
        background: #FFFBF2;
        border: 1px solid #E3CBA0;
        border-radius: 10px;
        padding: 8px 12px !important;
        margin-bottom: 2px;
        transition: background .15s ease, border-color .15s ease;
    }
    section[data-testid="stSidebar"] .stRadio label:hover { background: #F0D9A6; border-color: #E8542A; }
    section[data-testid="stSidebar"] .stRadio label p { font-size: 17px !important; font-weight: 600; }
    section[data-testid="stSidebar"] .stButton button { font-size: 16px !important; border-radius: 10px !important; }

    .dash-jump { background: #FFFBF2; border: 1px solid #E3CBA0; border-radius: 10px; padding: 6px 10px; margin-top: 6px; }
    .dash-jump b { font-size: 15px !important; color: #7A5A34; }
    .dash-jump a { display:block; padding: 5px 0 5px 6px; font-size: 15px !important;
                   color:#8A5E17 !important; text-decoration:none; border-radius: 6px; }
    .dash-jump a:hover { background: #F0D9A6; text-decoration:none; }

    .stButton button, [data-testid="stFormSubmitButton"] button, [data-testid="baseButton-primary"] {
        border-radius: 10px !important;
        font-weight: 700 !important;
        border: none !important;
    }
    .stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
        background: #E8542A !important;
        box-shadow: 0 2px 6px rgba(232,84,42,0.3);
    }
    .stButton button[kind="primary"]:hover { background: #C43D17 !important; }

    div[data-testid="stMetric"] {
        background: #FFFBF2;
        border: 1px solid #E3CBA0;
        border-radius: 14px;
        padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] { font-weight: 700; color: #7A5A34; }
    div[data-testid="stMetricValue"] { font-family: 'Fraunces', serif; color: #4A2418; }

    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        border-radius: 12px;
        border: 1px solid #E3CBA0;
    }

    .stRadio > div[role="radiogroup"] { gap: 8px; }
    div[role="radiogroup"] label {
        border: 1px solid #E3CBA0;
        border-radius: 20px;
        padding: 4px 14px !important;
        background: #FFFBF2;
    }

    hr { border-color: #E3CBA0 !important; }
    [data-testid="stExpander"] { border: 1px solid #E3CBA0 !important; border-radius: 12px !important; }
    div[data-testid="stForm"] { border: 1px solid #E3CBA0; border-radius: 12px; padding: 16px; background: #FFFBF2; }
    </style>
    """
)

# ----------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------
CARTS = ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"]
CITY = "HOSUR"

STAFF_MEMBERS = ["Select Staff", "Staff 1", "Staff 2", "Staff 3", "Other"]

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
]
FLAVOR_CODES = [f[0] for f in FLAVORS]
N_FLAVORS = len(FLAVORS)

PAYMENT_STATUSES = ["Pending", "Partial", "Complete"]

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
DAILY_TOTAL_COLS = 46

EXPENSE_HEADER_ROWS = 3

STOCK_HEADER_ROWS = 4
STOCK_TOTAL_COLS = 60

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


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
    return -v if neg else v


def _pad(row, n):
    if len(row) < n:
        return row + [""] * (n - len(row))
    return row


def _row_has_data(r):
    return any(str(c).strip() != "" for c in r[4:44])


# ----------------------------------------------------------------------
# Google Sheets connection
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


# ----------------------------------------------------------------------
# Daily Data As Shared helpers
# ----------------------------------------------------------------------
def load_daily_raw():
    ws = get_ws("Daily Data As Shared")
    values = ws.get_all_values()
    rows = values[DAILY_HEADER_ROWS:]
    return ws, rows


def _col_letter(n):
    letters = ""
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(65 + rem) + letters
    return letters


def _update_row(tab_name, row_number, values):
    ws = get_ws(tab_name)
    end_col = _col_letter(len(values))
    ws.update(range_name=f"A{row_number}:{end_col}{row_number}", values=[values], value_input_option="USER_ENTERED")


def get_opening_balance(cart_name, before_date=None):
    _, rows = load_daily_raw()
    latest = None
    latest_date = None
    for raw_r in rows:
        r = _pad(raw_r, DAILY_TOTAL_COLS)
        if not r[0].strip() or r[1].strip() != cart_name or not _row_has_data(r):
            continue
        try:
            d = pd.to_datetime(r[0])
            if pd.isna(d):
                continue
            d = d.date()
        except Exception:
            continue
        if before_date is not None and d >= before_date:
            continue
        if latest_date is None or d > latest_date:
            latest_date = d
            latest = r
    if latest is None:
        return [0] * N_FLAVORS
    closing_start = 4 + 9 * 3
    return [int(_num(latest[closing_start + i])) for i in range(N_FLAVORS)]


def update_daily_entry(row_number, entry_date, cart_name, added, closing, opening, total, phonepe, cash, remarks, staff_name="", staff_advance=0.0):
    sold = [opening[i] + added[i] - closing[i] for i in range(N_FLAVORS)]
    date_str = entry_date.strftime("%Y-%m-%d")
    date_cart_id = f"{date_str}||{cart_name}"
    row = (
        [date_str, cart_name, CITY, date_cart_id]
        + [int(x) for x in opening]
        + [int(x) for x in added]
        + [int(x) for x in sold]
        + [int(x) for x in closing]
        + [float(total), float(phonepe), float(cash), str(remarks), str(staff_name), float(staff_advance)]
    )
    _update_row("Daily Data As Shared", row_number, row)
    return sold


def list_daily_entries():
    _, rows = load_daily_raw()
    out = []
    added_start = 4 + 9 * 1
    sold_start = 4 + 9 * 2
    closing_start = 4 + 9 * 3
    for idx, raw_r in enumerate(rows):
        r = _pad(raw_r, DAILY_TOTAL_COLS)
        if not r[0].strip() or not _row_has_data(r):
            continue
        try:
            d = pd.to_datetime(r[0])
        except Exception:
            continue
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
            }
        )
    out.sort(key=lambda x: (x["date"], x["cart"]), reverse=True)
    return out


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
    ]
    ws = get_ws("Expenses")
    ws.append_row(row, value_input_option="USER_ENTERED")


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
    ]
    _update_row("Expenses", row_number, row)


def list_expense_entries():
    ws = get_ws("Expenses")
    values = ws.get_all_values()
    cols_n = 8
    out = []
    for idx, raw_r in enumerate(values[EXPENSE_HEADER_ROWS:]):
        r = _pad(raw_r, cols_n)
        if not any(c.strip() for c in r):
            continue
        try:
            d = pd.to_datetime(r[0])
        except Exception:
            continue
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
        )
    out.sort(key=lambda x: (x["date"], x["row"]), reverse=True)
    return out


def load_expenses_df():
    ws = get_ws("Expenses")
    values = ws.get_all_values()
    cols = ["Date", "Description", "Amount", "Category", "Mode", "Ref No", "Paid To", "Remarks"]
    rows = [_pad(r, len(cols)) for r in values[EXPENSE_HEADER_ROWS:] if any(c.strip() for c in r)]
    df = pd.DataFrame(rows, columns=cols)
    if not df.empty:
        df["Amount"] = df["Amount"].apply(_num)
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df["Category"] = df["Category"].astype(str).str.strip()
        df["Mode"] = df["Mode"].astype(str).str.strip()
    return df


def load_daily_df():
    _, rows = load_daily_raw()
    records = []
    for raw_r in rows:
        r = _pad(raw_r, DAILY_TOTAL_COLS)
        if not r[0].strip() or not _row_has_data(r):
            continue
        try:
            d = pd.to_datetime(r[0])
        except Exception:
            continue
        closing_start = 4 + 9 * 3
        closing = [int(_num(r[closing_start + i])) for i in range(N_FLAVORS)]
        sold_start = 4 + 9 * 2
        sold = [int(_num(r[sold_start + i])) for i in range(N_FLAVORS)]
        added_start = 4 + 9 * 1
        added = [int(_num(r[added_start + i])) for i in range(N_FLAVORS)]
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
            }
        )
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# Stock Received helpers
# ----------------------------------------------------------------------
def load_stock_raw():
    ws = get_ws("Stock Received")
    values = ws.get_all_values()
    rows = values[STOCK_HEADER_ROWS:]
    return ws, rows


def _build_stock_row(
    order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    diff = [received[i] - ordered[i] for i in range(N_FLAVORS)]
    date_loc_id = f"{received_date.strftime('%Y-%m-%d')}||{location}"
    return (
        [order_date.strftime("%Y-%m-%d"), received_date.strftime("%Y-%m-%d"), location, date_loc_id]
        + ordered + [sum(ordered)]
        + received + [sum(received)]
        + diff + [sum(diff)]
        + cost + [sum(cost)]
        + [payment_amount, payment_status, payment_date.strftime("%Y-%m-%d") if payment_date else "", payment_details]
        + damaged + [sum(damaged)]
        + [damaged_returned_on.strftime("%Y-%m-%d") if damaged_returned_on else "", notes]
    )


def append_stock_entry(
    order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    row = _build_stock_row(
        order_date, received_date, location, ordered, received, cost, damaged,
        payment_amount, payment_status, payment_date, payment_details, damaged_returned_on, notes,
    )
    ws = get_ws("Stock Received")
    ws.append_row(row, value_input_option="USER_ENTERED")


def update_stock_entry(
    row_number, order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    row = _build_stock_row(
        order_date, received_date, location, ordered, received, cost, damaged,
        payment_amount, payment_status, payment_date, payment_details, damaged_returned_on, notes,
    )
    _update_row("Stock Received", row_number, row)


def list_stock_entries():
    _, rows = load_stock_raw()
    out = []
    for idx, raw_r in enumerate(rows):
        r = _pad(raw_r, STOCK_TOTAL_COLS)
        if not r[0].strip() and not r[1].strip():
            continue
        try:
            d = pd.to_datetime(r[1]) if r[1].strip() else pd.to_datetime(r[0])
        except Exception:
            continue
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
        )
    out.sort(key=lambda x: (x["received_date"], x["row"]), reverse=True)
    return out


def get_freezer_stock():
    _, stock_rows = load_stock_raw()
    received_totals = [0.0] * N_FLAVORS
    recv_start = 14
    for raw_r in stock_rows:
        r = _pad(raw_r, STOCK_TOTAL_COLS)
        if not r[0].strip():
            continue
        for i in range(N_FLAVORS):
            received_totals[i] += _num(r[recv_start + i])

    daily_df = load_daily_df()
    added_totals = [0.0] * N_FLAVORS
    if not daily_df.empty:
        for added in daily_df["Added_By_Flavor"]:
            for i in range(N_FLAVORS):
                added_totals[i] += added[i]

    return [int(received_totals[i] - added_totals[i]) for i in range(N_FLAVORS)]


# ----------------------------------------------------------------------
# Login
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
            valid_user = st.secrets.get("app_username", "admin")
            valid_pass = st.secrets.get("app_password", None)

            if valid_pass is None:
                st.error("No `app_password` set in Secrets. Please add credentials to Secrets.")
            elif (
                hmac.compare_digest(username.strip(), valid_user.strip())
                and hmac.compare_digest(password, valid_pass)
            ):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect username or password — try again.")

    return False


if not check_login():
    st.stop()

# ----------------------------------------------------------------------
# Navigation
# ----------------------------------------------------------------------
with st.sidebar:
    try:
        st.image("assets/logo.png", use_container_width=True)
    except Exception:
        st.markdown("## 🍦 Kulfi Ops")
    page = st.radio(
        "Go to",
        ["Dashboard", "Daily Entry", "Freezer Stock", "Freezer Analysis", "Expenses"],
        label_visibility="collapsed",
    )
    if page == "Dashboard":
        st.markdown(
            textwrap.dedent(
                """
            <div class="dash-jump">
            <b style="font-size:15px;">Jump to</b><br>
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
        )
    st.markdown("---")
    if st.button("Log out", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()

st.title(f"🍦 Kulfi Ops — {page}")

# ---------------- DAILY ENTRY ----------------
if page == "Daily Entry":
    st.subheader("Cart restock & daily sales")

    try:
        daily_entries = list_daily_entries()
    except Exception as e:
        daily_entries = []
        st.warning(f"Could not load entries ({e}).")

    if not daily_entries:
        st.info("No past entries found in the sheet.")
    else:
        labels = [f"{e['date'].strftime('%d %b %Y')} — {e['cart']}" for e in daily_entries]
        sel = st.selectbox("Select entry to update sales", labels, key="daily_update_select")
        loaded = daily_entries[labels.index(sel)]
        editing_row = loaded["row"]

        key_suffix = f"_{editing_row}"
        st.caption("Review and update restock and sales counts for this entry.")

        c1, c2 = st.columns(2)
        with c1:
            entry_date = st.date_input("Date", value=loaded["date"].date(), key=f"daily_date{key_suffix}")
        with c2:
            default_cart_idx = CARTS.index(loaded["cart"]) if loaded["cart"] in CARTS else 0
            cart_name = st.selectbox("Cart", CARTS, index=default_cart_idx, key=f"daily_cart{key_suffix}")

        data_key_suffix = f"_{editing_row}"

        k_tot = f"daily_total{data_key_suffix}"
        k_ph = f"daily_phonepe{data_key_suffix}"
        k_cs = f"daily_cash{data_key_suffix}"
        k_adv = f"daily_adv{data_key_suffix}"
        k_staff = f"daily_staff{data_key_suffix}"
        k_prev_calc = f"daily_prev_calc{data_key_suffix}"

        staff_options = list(STAFF_MEMBERS)
        if loaded.get("staff_name") and loaded["staff_name"] not in staff_options:
            staff_options.append(loaded["staff_name"])

        default_staff_idx = staff_options.index(loaded["staff_name"]) if loaded.get("staff_name") in staff_options else 0
        staff_name = st.selectbox("Cart staff name", staff_options, index=default_staff_idx, key=k_staff)

        opening = loaded["opening"]

        flavor_names = [f[1] for f in FLAVORS]
        df_init = pd.DataFrame(
            {
                "Flavour": flavor_names,
                "Cart balance from yesterday": opening,
                "Stock addition to cart today": loaded["added"],
                "Closing cart balance": loaded["closing"],
            }
        )

        st.write("Enter units **added to the cart** and the **actual closing count** observed:")
        
        # SINGLE EDITABLE TABLE ONLY
        edited = st.data_editor(
            df_init,
            column_config={
                "Flavour": st.column_config.TextColumn(disabled=True),
                "Cart balance from yesterday": st.column_config.NumberColumn(disabled=True),
                "Stock addition to cart today": st.column_config.NumberColumn(min_value=0, step=1),
                "Closing cart balance": st.column_config.NumberColumn(min_value=0, step=1),
            },
            hide_index=True,
            use_container_width=True,
            key=f"daily_editor{data_key_suffix}",
        )

        added = edited["Stock addition to cart today"].fillna(0).astype(int).tolist()
        closing = edited["Closing cart balance"].fillna(0).astype(int).tolist()
        sold = [opening[i] + added[i] - closing[i] for i in range(N_FLAVORS)]

        # Dynamic metrics
        tot_open, tot_add, tot_close, tot_sold = sum(opening), sum(added), sum(closing), sum(sold)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Opening Balance", f"{tot_open} units")
        m2.metric("Stock Added", f"{tot_add} units")
        m3.metric("Closing Balance", f"{tot_close} units")
        m4.metric("Total Sold", f"{tot_sold} units")

        if any(s < 0 for s in sold):
            st.error("Today's sales works out negative for at least one flavour - closing count is higher than opening + added.")

        # 1. Total Collection Auto-calc using MRP from assumptions
        calculated_mrp_total = float(sum(sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS)))

        # Auto calculate cash based on: Cash = Total - PhonePe - Staff Advance
        def recalculate_cash():
            tot = float(st.session_state.get(k_tot, 0.0))
            ph = float(st.session_state.get(k_ph, 0.0))
            adv = float(st.session_state.get(k_adv, 0.0))
            st.session_state[k_cs] = max(0.0, tot - ph - adv)

        if k_tot not in st.session_state or st.session_state.get(k_prev_calc) != calculated_mrp_total:
            st.session_state[k_tot] = float(loaded["total"]) if k_tot not in st.session_state else max(0.0, calculated_mrp_total)
            st.session_state[k_prev_calc] = calculated_mrp_total

        if k_ph not in st.session_state:
            st.session_state[k_ph] = float(loaded["phonepe"])

        if k_adv not in st.session_state:
            st.session_state[k_adv] = float(loaded["staff_advance"])

        if k_cs not in st.session_state:
            st.session_state[k_cs] = float(loaded["cash"])

        st.markdown("---")
        st.write("**Today's collection & Staff Advance**")

        c3, c4, c5, c6 = st.columns(4)
        with c3:
            total_collection = st.number_input(
                "Total collection (₹)",
                min_value=0.0,
                step=10.0,
                key=k_tot,
                on_change=recalculate_cash
            )
        with c4:
            phonepe = st.number_input(
                "PhonePe / UPI (₹)",
                min_value=0.0,
                step=10.0,
                key=k_ph,
                on_change=recalculate_cash
            )
        with c5:
            staff_advance = st.number_input(
                "Advance to staff (₹)",
                min_value=0.0,
                step=10.0,
                key=k_adv,
                on_change=recalculate_cash
            )
        with c6:
            cash = st.number_input(
                "Cash (₹)",
                min_value=0.0,
                step=10.0,
                key=k_cs
            )

        if abs((phonepe + cash + staff_advance) - total_collection) > 0.5:
            st.warning(f"PhonePe + Cash + Advance (₹{phonepe + cash + staff_advance:,.0f}) doesn't match Total collection (₹{total_collection:,.0f}) - adjust if unintentional.")

        remarks = st.text_input("Remarks (optional)", value=loaded["remarks"], key=f"daily_remarks{data_key_suffix}")

        if st.button("Update sales", type="primary", use_container_width=True):
            if sum(added) == 0 and closing == opening:
                st.error("Enter a stock addition or a closing count that differs from yesterday's balance before saving.")
            elif any(s < 0 for s in sold):
                st.error("Today's sales works out negative for at least one flavour - fix closing count before saving.")
            else:
                try:
                    selected_staff = "" if staff_name == "Select Staff" else staff_name
                    saved_sold = update_daily_entry(
                        editing_row, entry_date, cart_name, added, closing, opening, 
                        total_collection, phonepe, cash, remarks, selected_staff, staff_advance
                    )
                    st.success(f"Updated sales for {cart_name} on {entry_date.strftime('%d %b %Y')}. Sales: {sum(saved_sold)} units.")
                    st.cache_resource.clear()
                except Exception as e:
                    st.error(f"Could not save - {e}")

# ---------------- FREEZER STOCK ----------------
elif page == "Freezer Stock":
    st.subheader("Stock received into freezer")

    stock_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="stock_mode")

    stock_loaded = None
    stock_editing_row = None
    if stock_mode == "Edit past entry":
        try:
            stock_entries = list_stock_entries()
        except Exception as e:
            stock_entries = []
            st.warning(f"Could not load past entries ({e}).")
        if not stock_entries:
            st.info("No past entries found yet.")
        else:
            def _fmt_order_date(s):
                if not s or not str(s).strip():
                    return "no order date"
                try:
                    d = pd.to_datetime(s)
                    return f"ordered {d.strftime('%d %b %Y')}" if not pd.isna(d) else "no order date"
                except Exception:
                    return "no order date"

            stock_labels = [
                f"Received {e['received_date'].strftime('%d %b %Y')} ({_fmt_order_date(e['order_date'])}) — {e['location']}"
                for e in stock_entries
            ]
            stock_sel = st.selectbox("Select entry to edit", stock_labels, key="stock_edit_select")
            stock_loaded = stock_entries[stock_labels.index(stock_sel)]
            stock_editing_row = stock_loaded["row"]
            st.caption("Loaded - edit fields below, then click Update entry.")

    sk = f"_{stock_editing_row}" if stock_editing_row else "_new"
    st.caption("Log a supplier delivery. Ordered and Damaged are optional.")

    def _parse_date_or(s, fallback):
        if not s or not str(s).strip():
            return fallback
        try:
            d = pd.to_datetime(s)
            return fallback if pd.isna(d) else d.date()
        except Exception:
            return fallback

    c1, c2, c3 = st.columns(3)
    with c1:
        order_date = st.date_input(
            "Order date",
            value=_parse_date_or(stock_loaded["order_date"], date.today()) if stock_loaded else date.today(),
            key=f"stock_order_date{sk}",
        )
    with c2:
        received_date = st.date_input(
            "Received date",
            value=stock_loaded["received_date"].date() if stock_loaded else date.today(),
            key=f"stock_received_date{sk}",
        )
    with c3:
        location = st.text_input("Location", value=(stock_loaded["location"] if stock_loaded else CITY), key=f"stock_location{sk}")

    flavor_names = [f[1] for f in FLAVORS]
    df_init = pd.DataFrame(
        {
            "Flavour": flavor_names,
            "Ordered": stock_loaded["ordered"] if stock_loaded else [0] * N_FLAVORS,
            "Received": stock_loaded["received"] if stock_loaded else [0] * N_FLAVORS,
            "Cost (₹, total)": stock_loaded["cost"] if stock_loaded else [0.0] * N_FLAVORS,
            "Damaged": stock_loaded["damaged"] if stock_loaded else [0] * N_FLAVORS,
        }
    )
    st.write("Enter units per flavour:")
    stock_edited = st.data_editor(
        df_init,
        column_config={
            "Flavour": st.column_config.TextColumn(disabled=True),
            "Ordered": st.column_config.NumberColumn(min_value=0, step=1),
            "Received": st.column_config.NumberColumn(min_value=0, step=1),
            "Cost (₹, total)": st.column_config.NumberColumn(min_value=0.0, step=10.0),
            "Damaged": st.column_config.NumberColumn(min_value=0, step=1),
        },
        hide_index=True,
        use_container_width=True,
        key=f"stock_editor{sk}",
    )

    ordered = stock_edited["Ordered"].fillna(0).astype(int).tolist()
    received = stock_edited["Received"].fillna(0).astype(int).tolist()
    cost = stock_edited["Cost (₹, total)"].fillna(0).astype(float).tolist()
    damaged = stock_edited["Damaged"].fillna(0).astype(int).tolist()

    st.caption(
        "Standard cost price per unit — Malai ₹22, Mini Malai ₹18, Pista ₹22, Mango ₹22, "
        "Kesar Badam ₹27.5, Badam Matka ₹44, Shahi Gulab ₹27.5, Chocolate ₹27.5, Roasted Almond ₹33."
    )

    st.markdown("---")
    st.write("**Payment**")
    c4, c5 = st.columns(2)
    with c4:
        default_payment_amount = stock_loaded["payment_amount"] if stock_loaded else float(sum(cost))
        payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=float(default_payment_amount), step=10.0, key=f"stock_pay_amt{sk}")
    with c5:
        default_status_idx = PAYMENT_STATUSES.index(stock_loaded["payment_status"]) if stock_loaded and stock_loaded["payment_status"] in PAYMENT_STATUSES else 0
        payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=default_status_idx, key=f"stock_pay_status{sk}")

    has_payment_date = st.checkbox("Add payment date", value=bool(stock_loaded and stock_loaded["payment_date"]), key=f"stock_has_paydate{sk}")
    payment_date = (
        st.date_input(
            "Payment date",
            value=_parse_date_or(stock_loaded["payment_date"], date.today()) if (stock_loaded and stock_loaded["payment_date"]) else date.today(),
            key=f"stock_payment_date{sk}",
        )
        if has_payment_date
        else None
    )
    payment_details = st.text_input("Payment details (optional)", value=(stock_loaded["payment_details"] if stock_loaded else ""), key=f"stock_pay_details{sk}")

    has_damaged_return = st.checkbox("Damaged items were returned", value=bool(stock_loaded and stock_loaded["damaged_returned_on"]), key=f"stock_has_damret{sk}")
    damaged_returned_on = (
        st.date_input(
            "Damaged items returned on",
            value=_parse_date_or(stock_loaded["damaged_returned_on"], date.today()) if (stock_loaded and stock_loaded["damaged_returned_on"]) else date.today(),
            key=f"stock_damaged_date{sk}",
        )
        if has_damaged_return
        else None
    )

    notes = st.text_input("Notes (optional)", value=(stock_loaded["notes"] if stock_loaded else ""), key=f"stock_notes{sk}")

    stock_button_label = "Update entry" if stock_editing_row else "Save stock received"
    if st.button(stock_button_label, type="primary", use_container_width=True):
        if sum(received) == 0:
            st.error("Enter at least one quantity received before saving.")
        else:
            try:
                if stock_editing_row:
                    update_stock_entry(
                        stock_editing_row, order_date, received_date, location,
                        ordered, received, cost, damaged,
                        payment_amount, payment_status, payment_date, payment_details,
                        damaged_returned_on, notes,
                    )
                    st.success(f"Updated entry for {received_date.strftime('%d %b %Y')} at {location}.")
                else:
                    append_stock_entry(
                        order_date, received_date, location,
                        ordered, received, cost, damaged,
                        payment_amount, payment_status, payment_date, payment_details,
                        damaged_returned_on, notes,
                    )
                    st.success(f"Saved {sum(received)} units received on {received_date.strftime('%d %b %Y')}.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Could not save - {e}")

# ---------------- FREEZER ANALYSIS ----------------
elif page == "Freezer Analysis":
    st.subheader("Freezer stock analysis & reorder planner")
    st.caption("Uses recent sales pace to estimate when freezer stock runs low.")

    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        lookback_days = st.number_input("Lookback window for avg. daily sales (days)", min_value=3, max_value=90, value=14, step=1)
    with ac2:
        buffer_days = st.number_input("Minimum buffer to maintain (days)", min_value=0, max_value=14, value=3, step=1)
    with ac3:
        cover_days = st.number_input("Next order should cover (days)", min_value=1, max_value=30, value=7, step=1)

    try:
        daily_df_fa = load_daily_df()
        freezer_stock_fa = get_freezer_stock()
    except Exception as e:
        daily_df_fa = pd.DataFrame()
        freezer_stock_fa = [0] * N_FLAVORS
        st.warning(f"Could not load data yet ({e}).")

    if daily_df_fa.empty:
        st.info("No sales logged yet.")
    else:
        today_fa = date.today()
        cutoff_fa = today_fa - timedelta(days=lookback_days - 1)
        window_df = daily_df_fa[(daily_df_fa["Date"].dt.date >= cutoff_fa) & (daily_df_fa["Date"].dt.date <= today_fa)]

        flavor_sold_window = [0] * N_FLAVORS
        for arr in window_df["Sold_By_Flavor"]:
            for i in range(N_FLAVORS):
                flavor_sold_window[i] += arr[i]
        avg_daily = [s / lookback_days for s in flavor_sold_window]

        rows = []
        trigger_dates = []
        for i, f in enumerate(FLAVORS):
            stock = freezer_stock_fa[i]
            rate = avg_daily[i]
            if rate <= 0:
                days_left = None
                status = "No recent sales"
                trigger_date = None
                suggested_qty = 0
            else:
                days_left = stock / rate
                trigger_date = today_fa + timedelta(days=max(0, days_left - buffer_days))
                trigger_dates.append(trigger_date)
                if days_left <= buffer_days:
                    status = "Order now"
                elif days_left <= buffer_days + 2:
                    status = "Order soon"
                else:
                    status = "OK"
                suggested_qty = int(round(rate * cover_days / 10.0)) * 10

            rows.append(
                {
                    "Flavour": f[1],
                    "Freezer stock": stock,
                    "Avg. daily sales": round(rate),
                    "Days of stock left": round(days_left) if days_left is not None else "—",
                    "Status": status,
                    f"Suggested next order ({cover_days}d)": suggested_qty,
                }
            )

        analysis_df = pd.DataFrame(rows)
        total_stock = sum(freezer_stock_fa)
        total_rate = sum(avg_daily)
        overall_days_left = (total_stock / total_rate) if total_rate > 0 else None
        overall_order_date = min(trigger_dates) if trigger_dates else None

        st.markdown("### Overall picture")
        oc1, oc2, oc3 = st.columns(3)
        oc1.metric("Total freezer stock", f"{total_stock} units")
        oc2.metric("Avg. daily sales (all flavours)", f"{total_rate:.0f} units/day")
        oc3.metric("Overall days of stock left", f"{overall_days_left:.0f}" if overall_days_left is not None else "—")

        if overall_order_date is not None:
            if overall_order_date <= today_fa:
                st.error(f"**Place your next order now** — at least one flavour is at or below your {buffer_days}-day buffer.")
            else:
                days_until = (overall_order_date - today_fa).days
                st.success(f"**Next order by {overall_order_date.strftime('%d %b %Y')}** (in {days_until} days).")

        st.markdown("### Per-flavour breakdown")
        st.dataframe(analysis_df, hide_index=True, use_container_width=True)

        st.markdown("### Suggested next order")
        order_df = analysis_df[["Flavour", f"Suggested next order ({cover_days}d)"]].rename(
            columns={f"Suggested next order ({cover_days}d)": "Units to order"}
        )
        st.dataframe(order_df, hide_index=True, use_container_width=True)

        st.markdown("### Days of stock left, by flavour")
        chart_df = analysis_df[analysis_df["Days of stock left"] != "—"].copy()
        if not chart_df.empty:
            chart_df["Days of stock left"] = chart_df["Days of stock left"].astype(float)
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
            )
            rule = alt.Chart(pd.DataFrame({"y": [buffer_days]})).mark_rule(color="#4A2418", strokeDash=[4, 4]).encode(y="y:Q")
            st.altair_chart(days_chart + rule, use_container_width=True)

# ---------------- EXPENSES ----------------
elif page == "Expenses":
    st.subheader("Log an expense")

    exp_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="exp_mode")

    exp_loaded = None
    exp_editing_row = None
    if exp_mode == "Edit past entry":
        try:
            expense_entries = list_expense_entries()
        except Exception as e:
            expense_entries = []
            st.warning(f"Could not load past entries ({e}).")
        if not expense_entries:
            st.info("No past entries found yet.")
        else:
            exp_labels = [f"{e['date'].strftime('%d %b %Y')} — {e['description'] or e['category']} (₹{e['amount']:,.0f})" for e in expense_entries]
            exp_sel = st.selectbox("Select entry to edit", exp_labels, key="exp_edit_select")
            exp_loaded = expense_entries[exp_labels.index(exp_sel)]
            exp_editing_row = exp_loaded["row"]
            st.caption("Loaded - edit fields below, then click Update entry.")

    ek = f"_{exp_editing_row}" if exp_editing_row else "_new"

    c1, c2 = st.columns(2)
    with c1:
        exp_date = st.date_input("Date", value=(exp_loaded["date"].date() if exp_loaded else date.today()), key=f"exp_date{ek}")
    with c2:
        default_cat_idx = EXPENSE_CATEGORIES.index(exp_loaded["category"]) if exp_loaded and exp_loaded["category"] in EXPENSE_CATEGORIES else 0
        category = st.selectbox("Category", EXPENSE_CATEGORIES, index=default_cat_idx, key=f"exp_category{ek}")

    description = st.text_input("Description", value=(exp_loaded["description"] if exp_loaded else ""), key=f"exp_desc{ek}")
    amount = st.number_input("Amount (₹)", min_value=0.0, value=(float(exp_loaded["amount"]) if exp_loaded else 0.0), step=10.0, key=f"exp_amount{ek}")

    c3, c4 = st.columns(2)
    with c3:
        default_mode_idx = PAYMENT_MODES.index(exp_loaded["mode"]) if exp_loaded and exp_loaded["mode"] in PAYMENT_MODES else 0
        mode = st.selectbox("Payment mode", PAYMENT_MODES, index=default_mode_idx, key=f"exp_mode_select{ek}")
    with c4:
        ref_no = st.text_input("Transaction ref. no. (optional)", value=(exp_loaded["ref_no"] if exp_loaded else ""), key=f"exp_ref{ek}")

    paid_to = st.text_input("Paid to (optional)", value=(exp_loaded["paid_to"] if exp_loaded else ""), key=f"exp_paidto{ek}")
    exp_remarks = st.text_input("Remarks (optional)", value=(exp_loaded["remarks"] if exp_loaded else ""), key=f"exp_remarks{ek}")

    exp_button_label = "Update entry" if exp_editing_row else "Save expense"
    if st.button(exp_button_label, type="primary", use_container_width=True):
        if amount <= 0:
            st.error("Enter an amount greater than 0.")
        else:
            try:
                if exp_editing_row:
                    update_expense(exp_editing_row, exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)
                    st.success(f"Updated ₹{amount:,.0f} expense under {category}.")
                else:
                    append_expense(exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)
                    st.success(f"Saved ₹{amount:,.0f} expense under {category}.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Could not save - {e}")

# ---------------- DASHBOARD ----------------
elif page == "Dashboard":
    st.subheader("Quick view")

    try:
        daily_df = load_daily_df()
        exp_df = load_expenses_df()
    except Exception as e:
        daily_df = pd.DataFrame()
        exp_df = pd.DataFrame()
        st.warning(f"Could not load data yet ({e}).")

    today = pd.Timestamp(date.today())
    day_labels = [today - pd.Timedelta(days=3), today - pd.Timedelta(days=2), today - pd.Timedelta(days=1)]
    if not daily_df.empty:
        day_rows = [daily_df[daily_df["Date"].dt.date == d.date()] for d in day_labels]
        day_rev = [r["Total_Collection"].sum() for r in day_rows]
        day_units = [int(r["Sold_Total"].sum()) for r in day_rows]

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
        st.info("No sales logged yet.")

    # ------------------ Date-range reports ------------------
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

        st.caption(f"Showing: {range_start.strftime('%d %b %Y')} – {range_end.strftime('%d %b %Y')}")

        range_df = daily_df[(daily_df["Date"].dt.date >= range_start) & (daily_df["Date"].dt.date <= range_end)] if not daily_df.empty else daily_df
        range_exp = exp_df[(exp_df["Date"].dt.date >= range_start) & (exp_df["Date"].dt.date <= range_end)] if not exp_df.empty else exp_df

        total_rev = range_df["Total_Collection"].sum() if not range_df.empty else 0.0
        total_units = int(range_df["Sold_Total"].sum()) if not range_df.empty else 0
        total_exp_all = range_exp["Amount"].sum() if not range_exp.empty else 0.0

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Revenue in range", f"₹{total_rev:,.0f}")
        mc2.metric("Units sold in range", f"{total_units}")
        mc3.metric("Expenses in range", f"₹{total_exp_all:,.0f}")

        # ---- Cart-wise comparison ----
        st.markdown('<div id="cart-wise-comparison"></div>', unsafe_allow_html=True)
        st.markdown("### Cart-wise comparison")
        if not range_df.empty:
            cart_grp = (
                range_df.groupby("Cart")
                .agg(**{"Revenue (₹)": ("Total_Collection", "sum"), "Units sold": ("Sold_Total", "sum")})
                .reset_index()
                .sort_values("Revenue (₹)", ascending=False)
            )
            st.dataframe(cart_grp, hide_index=True, use_container_width=True)
            st.bar_chart(cart_grp.set_index("Cart")["Revenue (₹)"])
        else:
            st.caption("No sales in this date range.")

        # ---- Cart-wise x day-of-week sales ----
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
                st.dataframe(units_pivot.round(1), use_container_width=True)

                st.write("**Avg. revenue (₹)** (rows = cart, columns = day of week)")
                st.dataframe(rev_pivot.round(0).astype(int), use_container_width=True)

                st.caption("Zero-sales days are excluded, so each cell is the average over the days that weekday actually had sales. 'All carts' shows the overall average across carts / days.")
        else:
            st.caption("No sales in this date range.")

        # ---- Flavour-wise performance ----
        st.markdown('<div id="flavour-wise-performance"></div>', unsafe_allow_html=True)
        st.markdown("### Flavour-wise performance")
        if not range_df.empty:
            flavor_sold = [0] * N_FLAVORS
            for arr in range_df["Sold_By_Flavor"]:
                for i in range(N_FLAVORS):
                    flavor_sold[i] += arr[i]
            flavor_df = pd.DataFrame(
                {
                    "Flavour": [f[1] for f in FLAVORS],
                    "Units sold": flavor_sold,
                    "Est. revenue (₹)": [flavor_sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS)],
                }
            ).sort_values("Units sold", ascending=False)
            st.dataframe(flavor_df, hide_index=True, use_container_width=True)
            st.bar_chart(flavor_df.set_index("Flavour")["Units sold"])
            st.caption("Estimated revenue = units sold × MRP per flavour; actual collections may vary slightly (discounts, complementary pieces etc).")
        else:
            st.caption("No sales in this date range.")

        # ---- Profit & Loss summary ----
        st.markdown('<div id="profit-loss-summary"></div>', unsafe_allow_html=True)
        st.markdown("### Profit & loss summary")
        cogs = range_exp[range_exp["Category"] == "Cost of Goods"]["Amount"].sum() if not range_exp.empty else 0.0
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
        if capital > 0:
            st.caption(f"₹{capital:,.0f} of one-time capital/setup costs fell in this range and is shown separately below, not deducted above.")

        # ---- Expense breakdown ----
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

        # ---- Cash vs PhonePe vs Advance ----
        st.markdown('<div id="cash-vs-phonepe"></div>', unsafe_allow_html=True)
        st.markdown("### Cash vs PhonePe / UPI vs Staff Advance")
        if not range_df.empty:
            total_cash = range_df["Cash"].sum()
            total_phonepe = range_df["PhonePe"].sum()
            total_advance = range_df["Staff_Advance"].sum() if "Staff_Advance" in range_df.columns else 0.0
            cc1, cc2, cc3 = st.columns(3)
            cc1.metric("Cash", f"₹{total_cash:,.0f}")
            cc2.metric("PhonePe / UPI", f"₹{total_phonepe:,.0f}")
            cc3.metric("Staff Advance", f"₹{total_advance:,.0f}")
            split_df = pd.DataFrame({
                "Mode": ["Cash", "PhonePe / UPI", "Staff Advance"], 
                "Amount (₹)": [total_cash, total_phonepe, total_advance]
            })
            st.bar_chart(split_df.set_index("Mode")["Amount (₹)"])
        else:
            st.caption("No collections in this date range.")

        # ---- Date-range sales table ----
        st.markdown('<div id="sales-in-range"></div>', unsafe_allow_html=True)
        st.markdown("### Sales in this range")
        if not range_df.empty:
            display_cols = ["Date", "Cart", "Sold_Total", "Total_Collection", "PhonePe", "Cash", "Staff_Name", "Staff_Advance"]
            sales_table = range_df.sort_values(["Date", "Cart"])[display_cols].rename(
                columns={
                    "Sold_Total": "Units sold", 
                    "Total_Collection": "Revenue (₹)",
                    "PhonePe": "PhonePe (₹)",
                    "Cash": "Cash (₹)",
                    "Staff_Name": "Staff Name",
                    "Staff_Advance": "Staff Advance (₹)"
                }
            )
            sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")
            st.dataframe(sales_table, hide_index=True, use_container_width=True)
        else:
            st.caption("No sales in this date range.")

    # ------------------ Current Inventory Status ------------------
    if not daily_df.empty:
        st.markdown("---")
        st.markdown('<div id="inventory-status"></div>', unsafe_allow_html=True)
        st.markdown("## Current Inventory Status")

        st.metric("Stock across carts", f"{int(daily_df.sort_values('Date').groupby('Cart').tail(1)['Closing_Total'].sum())}")

        try:
            freezer_stock = get_freezer_stock()
            st.markdown('<div id="freezer-stock-current"></div>', unsafe_allow_html=True)
            st.markdown("**Freezer stock (current)**")
            freezer_df = pd.DataFrame({"Flavour": [f[1] for f in FLAVORS], "Units in freezer": freezer_stock})
            st.dataframe(freezer_df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.caption(f"Could not compute freezer stock ({e}).")

        st.markdown('<div id="latest-stock-per-cart"></div>', unsafe_allow_html=True)
        st.markdown("**Latest stock per cart**")
        latest_per_cart = daily_df.sort_values("Date").groupby("Cart").tail(1)[["Cart", "Date", "Closing_Total"]]
        st.dataframe(latest_per_cart, hide_index=True, use_container_width=True)