"""
Kulfi Ops - simple multi-user data entry app for the kulfi cart business.

Reads/writes directly into the SAME Google Sheet tabs your Excel tracker uses:
  - "Daily Data As Shared"  (cart restock + daily sales + collections)
  - "Expenses"              (expense log)

This means your 20 days of existing history stays exactly where it is -
this app just appends new rows in the same format going forward.
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
    /* ---------- Remove top spacing ---------- */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
        margin-top: 0 !important;
    }
    header[data-testid="stHeader"] {
        background-color: transparent !important;
        height: 1.5rem !important;
    }

    /* ---------- Fonts & base ---------- */
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; }
    h1, h2, h3 { font-family: 'Fraunces', serif !important; color: #8A5E17 !important; letter-spacing: -0.01em; }
    h1 { font-size: 2.3rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }
    p, span, label, .stMarkdown { color: #2A1B10; }

    /* ---------- Sidebar ---------- */
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

    /* Jump-to sub-menu */
    .dash-jump { background: #FFFBF2; border: 1px solid #E3CBA0; border-radius: 10px; padding: 6px 10px; margin-top: 6px; }
    .dash-jump b { font-size: 15px !important; color: #7A5A34; }
    .dash-jump a { display:block; padding: 5px 0 5px 6px; font-size: 15px !important;
                   color:#8A5E17 !important; text-decoration:none; border-radius: 6px; }
    .dash-jump a:hover { background: #F0D9A6; text-decoration:none; }

    /* ---------- Buttons ---------- */
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

    /* ---------- Metric cards ---------- */
    div[data-testid="stMetric"] {
        background: #FFFBF2;
        border: 1px solid #E3CBA0;
        border-radius: 14px;
        padding: 14px 18px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetricLabel"] { font-weight: 700; color: #7A5A34; }
    div[data-testid="stMetricValue"] { font-family: 'Fraunces', serif; color: #4A2418; }

    /* ---------- Tables & data editors ---------- */
    div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #E3CBA0;
    }

    /* ---------- Tabs / radio pills used inside forms ---------- */
    .stRadio > div[role="radiogroup"] { gap: 8px; }
    div[role="radiogroup"] label {
        border: 1px solid #E3CBA0;
        border-radius: 20px;
        padding: 4px 14px !important;
        background: #FFFBF2;
    }

    /* ---------- Misc ---------- */
    hr { border-color: #E3CBA0 !important; }
    [data-testid="stExpander"] { border: 1px solid #E3CBA0 !important; border-radius: 12px !important; }
    div[data-testid="stForm"] { border: 1px solid #E3CBA0; border-radius: 12px; padding: 16px; background: #FFFBF2; }
    </style>
    """
    )
)

# ----------------------------------------------------------------------
# CONFIG - edit these if your cart names / flavours / sheet ever change
# ----------------------------------------------------------------------
CARTS = ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"]
CITY = "HOSUR"

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
DAILY_TOTAL_COLS = 4 + 9 * 4 + 4

EXPENSE_HEADER_ROWS = 3

STOCK_HEADER_ROWS = 4
STOCK_TOTAL_COLS = 60

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _num(x):
    """Turn a sheet cell (possibly '7,130', ' ₹ 500 ', '(200)', '', or already
    a number) into a float. Returns 0.0 for anything unparseable/blank."""
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
    """Google Sheets trims trailing empty cells per row, so a row with a blank
    Remarks column can come back shorter than expected. Pad it back out."""
    if len(row) < n:
        return row + [""] * (n - len(row))
    return row


def _row_has_data(r):
    """Treat a row as 'real' only if at least one of its numeric cells has data."""
    return any(str(c).strip() != "" for c in r[4:43])


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
    ws.update(f"A{row_number}:{end_col}{row_number}", [values], value_input_option="USER_ENTERED")


def get_opening_balance(cart_name):
    _, rows = load_daily_raw()
    latest = None
    latest_date = None
    for raw_r in rows:
        r = _pad(raw_r, DAILY_TOTAL_COLS)
        if not r[0].strip() or r[1].strip() != cart_name or not _row_has_data(r):
            continue
        try:
            d = datetime.strptime(r[0].split(" ")[0], "%Y-%m-%d")
        except Exception:
            try:
                d = datetime.strptime(r[0], "%d/%m/%Y")
            except Exception:
                continue
        if latest_date is None or d > latest_date:
            latest_date = d
            latest = r
    if latest is None:
        return [0] * N_FLAVORS
    closing_start = 4 + 9 * 3
    return [int(_num(latest[closing_start + i])) for i in range(N_FLAVORS)]


def append_daily_entry(entry_date, cart_name, added, sold, opening, total, phonepe, cash, remarks):
    closing = [opening[i] + added[i] - sold[i] for i in range(N_FLAVORS)]
    date_str = entry_date.strftime("%Y-%m-%d")
    date_cart_id = f"{date_str}||{cart_name}"
    row = (
        [date_str, cart_name, CITY, date_cart_id]
        + opening
        + added
        + sold
        + closing
        + [total, phonepe, cash, remarks]
    )
    ws = get_ws("Daily Data As Shared")
    ws.append_row(row, value_input_option="USER_ENTERED")
    return closing


def update_daily_entry(row_number, entry_date, cart_name, added, sold, opening, total, phonepe, cash, remarks):
    closing = [opening[i] + added[i] - sold[i] for i in range(N_FLAVORS)]
    date_str = entry_date.strftime("%Y-%m-%d")
    date_cart_id = f"{date_str}||{cart_name}"
    row = (
        [date_str, cart_name, CITY, date_cart_id]
        + opening
        + added
        + sold
        + closing
        + [total, phonepe, cash, remarks]
    )
    _update_row("Daily Data As Shared", row_number, row)
    return closing


def list_daily_entries():
    _, rows = load_daily_raw()
    out = []
    added_start = 4 + 9 * 1
    sold_start = 4 + 9 * 2
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
                "total": _num(r[40]),
                "phonepe": _num(r[41]),
                "cash": _num(r[42]),
                "remarks": r[43].strip() if len(r) > 43 else "",
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
        amount,
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
        amount,
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
            }
        )
    return pd.DataFrame(records)


# ----------------------------------------------------------------------
# Stock Received (freezer stock-in) helpers
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
# Login (shared credentials & narrowed centered form)
# ----------------------------------------------------------------------
def check_login():
    if st.session_state.get("authenticated", False):
        return True

    _, col_form, _ = st.columns([1, 1.2, 1])

    with col_form:
        try:
            st.image("assets/logo.png", width=220)
        except Exception:
            st.title("🍦 Kulfi Ops")[cite: 1]

        st.subheader("Sign in")[cite: 1]
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")[cite: 1]
            submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)[cite: 1]

        if submitted:
            valid_user = st.secrets.get("app_username", "admin")
            valid_pass = st.secrets.get("app_password", None)[cite: 1]

            if valid_pass is None:
                st.error("No `app_password` set in Secrets. Please add credentials to Secrets.")
            elif (
                hmac.compare_digest(username.strip(), valid_user.strip())
                and hmac.compare_digest(password, valid_pass)
            ):
                st.session_state["authenticated"] = True[cite: 1]
                st.rerun()[cite: 1]
            else:
                st.error("Incorrect username or password — try again.")

    return False


if not check_login():
    st.stop()[cite: 1]

# ----------------------------------------------------------------------
# UI
# ----------------------------------------------------------------------
with st.sidebar:
    try:
        st.image("assets/logo.png", use_container_width=True)[cite: 1]
    except Exception:
        st.markdown("## 🍦 Kulfi Ops")[cite: 1]
    page = st.radio(
        "Go to",
        ["Dashboard", "Daily Entry", "Freezer Stock", "Freezer Analysis", "Expenses"],
        label_visibility="collapsed",
    )[cite: 1]
    if page == "Dashboard":[cite: 1]
        st.markdown(
            textwrap.dedent(
                """
            <div class="dash-jump">
            <b style="font-size:15px;">Jump to</b><br>
            <a href="#last-3-days">Last 3 days</a>
            <a href="#freezer-stock-current">Freezer stock (current)</a>
            <a href="#latest-stock-per-cart">Latest stock per cart</a>
            <a href="#revenue-trend">Revenue trend (14 days)</a>
            <a href="#reports">Reports (date range)</a>
            <a href="#cart-wise-comparison">&nbsp;&nbsp;Cart-wise comparison</a>
            <a href="#cart-wise-day-of-week">&nbsp;&nbsp;Sales by day of week</a>
            <a href="#flavour-wise-performance">&nbsp;&nbsp;Flavour-wise performance</a>
            <a href="#profit-loss-summary">&nbsp;&nbsp;Profit &amp; loss summary</a>
            <a href="#expense-breakdown">&nbsp;&nbsp;Expense breakdown</a>
            <a href="#cash-vs-phonepe">&nbsp;&nbsp;Cash vs PhonePe</a>
            <a href="#sales-in-range">&nbsp;&nbsp;Sales table</a>
            </div>
            """
            ),
            unsafe_allow_html=True,
        )[cite: 1]
    st.markdown("---")[cite: 1]
    if st.button("Log out", use_container_width=True):[cite: 1]
        st.session_state["authenticated"] = False[cite: 1]
        st.rerun()[cite: 1]

st.title(f"🍦 Kulfi Ops — {page}")[cite: 1]

# ---------------- DAILY ENTRY ----------------
if page == "Daily Entry":[cite: 1]
    st.subheader("Cart restock & daily sales")[cite: 1]

    mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="daily_mode")[cite: 1]

    loaded = None[cite: 1]
    editing_row = None[cite: 1]
    if mode == "Edit past entry":[cite: 1]
        try:
            daily_entries = list_daily_entries()[cite: 1]
        except Exception as e:
            daily_entries = [][cite: 1]
            st.warning(f"Could not load past entries ({e}).")[cite: 1]
        if not daily_entries:[cite: 1]
            st.info("No past entries found yet.")[cite: 1]
        else:
            labels = [f"{e['date'].strftime('%d %b %Y')} — {e['cart']}" for e in daily_entries][cite: 1]
            sel = st.selectbox("Select entry to edit", labels, key="daily_edit_select")[cite: 1]
            loaded = daily_entries[labels.index(sel)][cite: 1]
            editing_row = loaded["row"][cite: 1]
            st.caption("Loaded - edit the fields below, then click Update entry to save changes to this same row.")[cite: 1]

    key_suffix = f"_{editing_row}" if editing_row else "_new"[cite: 1]
    st.caption("One entry per cart per day. Only fill in flavours that actually moved.")[cite: 1]

    c1, c2 = st.columns(2)[cite: 1]
    with c1:[cite: 1]
        entry_date = st.date_input("Date", value=(loaded["date"].date() if loaded else date.today()), key=f"daily_date{key_suffix}")[cite: 1]
    with c2:[cite: 1]
        default_cart_idx = CARTS.index(loaded["cart"]) if loaded and loaded["cart"] in CARTS else 0[cite: 1]
        cart_name = st.selectbox("Cart", CARTS, index=default_cart_idx, key=f"daily_cart{key_suffix}")[cite: 1]

    if loaded:[cite: 1]
        opening = loaded["opening"][cite: 1]
    else:
        try:
            opening = get_opening_balance(cart_name)[cite: 1]
        except Exception as e:
            opening = [0] * N_FLAVORS[cite: 1]
            st.warning(f"Could not fetch opening balance automatically ({e}). Starting from 0 - check your figures.")[cite: 1]

    flavor_names = [f[1] for f in FLAVORS][cite: 1]
    df_init = pd.DataFrame(
        {
            "Flavour": flavor_names,
            "Opening (in cart)": opening,
            "Added today": loaded["added"] if loaded else [0] * N_FLAVORS,
            "Sold today": loaded["sold"] if loaded else [0] * N_FLAVORS,
        }
    )[cite: 1]
    st.write("Enter units **added to the cart** (restock) and **units sold**, per flavour:")[cite: 1]
    edited = st.data_editor(
        df_init,
        column_config={
            "Flavour": st.column_config.TextColumn(disabled=True),
            "Opening (in cart)": st.column_config.NumberColumn(disabled=True),
            "Added today": st.column_config.NumberColumn(min_value=0, step=1),
            "Sold today": st.column_config.NumberColumn(min_value=0, step=1),
        },
        hide_index=True,
        use_container_width=True,
        key=f"daily_editor{key_suffix}",
    )[cite: 1]

    added = edited["Added today"].fillna(0).astype(int).tolist()[cite: 1]
    sold = edited["Sold today"].fillna(0).astype(int).tolist()[cite: 1]
    projected_closing = [opening[i] + added[i] - sold[i] for i in range(N_FLAVORS)][cite: 1]
    if any(c < 0 for c in projected_closing):[cite: 1]
        st.error("Closing balance would go negative for at least one flavour - double check the numbers above.")[cite: 1]

    suggested_total = sum(sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS))[cite: 1]
    default_total = loaded["total"] if loaded else float(suggested_total)[cite: 1]
    default_phonepe = loaded["phonepe"] if loaded else 0.0[cite: 1]
    default_cash = loaded["cash"] if loaded else default_total[cite: 1]

    st.markdown("---")[cite: 1]
    st.write("**Today's collection**")[cite: 1]
    c3, c4, c5 = st.columns(3)[cite: 1]
    with c3:[cite: 1]
        total_collection = st.number_input("Total collection (₹)", min_value=0.0, value=float(default_total), step=10.0, key=f"daily_total{key_suffix}")[cite: 1]
    with c4:[cite: 1]
        phonepe = st.number_input("PhonePe / UPI (₹)", min_value=0.0, value=float(default_phonepe), step=10.0, key=f"daily_phonepe{key_suffix}")[cite: 1]
    with c5:[cite: 1]
        cash = st.number_input("Cash (₹)", min_value=0.0, value=float(default_cash), step=10.0, key=f"daily_cash{key_suffix}")[cite: 1]

    if abs((phonepe + cash) - total_collection) > 0.5:[cite: 1]
        st.warning(f"PhonePe + Cash (₹{phonepe + cash:,.0f}) doesn't match Total collection (₹{total_collection:,.0f}) - fine if intentional, otherwise adjust.")[cite: 1]

    remarks = st.text_input("Remarks (optional)", value=(loaded["remarks"] if loaded else ""), key=f"daily_remarks{key_suffix}")[cite: 1]

    button_label = "Update entry" if editing_row else "Save daily entry"[cite: 1]
    if st.button(button_label, type="primary", use_container_width=True):[cite: 1]
        if sum(added) == 0 and sum(sold) == 0:[cite: 1]
            st.error("Enter at least one quantity added or sold before saving.")[cite: 1]
        else:
            try:
                if editing_row:[cite: 1]
                    closing = update_daily_entry(editing_row, entry_date, cart_name, added, sold, opening, total_collection, phonepe, cash, remarks)[cite: 1]
                    st.success(f"Updated entry for {cart_name} on {entry_date.strftime('%d %b %Y')}. Closing stock: {sum(closing)} units.")[cite: 1]
                else:
                    closing = append_daily_entry(entry_date, cart_name, added, sold, opening, total_collection, phonepe, cash, remarks)[cite: 1]
                    st.success(f"Saved for {cart_name} on {entry_date.strftime('%d %b %Y')}. Closing stock: {sum(closing)} units.")[cite: 1]
                st.cache_resource.clear()[cite: 1]
            except Exception as e:
                st.error(f"Could not save - {e}")[cite: 1]

    if editing_row:[cite: 1]
        st.caption("Note: editing a day that isn't the most recent entry for this cart won't automatically recalculate later days' opening/closing balances - check the days after this one if the correction is significant.")[cite: 1]

# ---------------- FREEZER STOCK ----------------
elif page == "Freezer Stock":[cite: 1]
    st.subheader("Stock received into freezer")[cite: 1]

    stock_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="stock_mode")[cite: 1]

    stock_loaded = None[cite: 1]
    stock_editing_row = None[cite: 1]
    if stock_mode == "Edit past entry":[cite: 1]
        try:
            stock_entries = list_stock_entries()[cite: 1]
        except Exception as e:
            stock_entries = [][cite: 1]
            st.warning(f"Could not load past entries ({e}).")[cite: 1]
        if not stock_entries:[cite: 1]
            st.info("No past entries found yet.")[cite: 1]
        else:
            def _fmt_order_date(s):[cite: 1]
                if not s or not str(s).strip():[cite: 1]
                    return "no order date"[cite: 1]
                try:
                    d = pd.to_datetime(s)[cite: 1]
                    return f"ordered {d.strftime('%d %b %Y')}" if not pd.isna(d) else "no order date"[cite: 1]
                except Exception:
                    return "no order date"[cite: 1]

            stock_labels = [
                f"Received {e['received_date'].strftime('%d %b %Y')} ({_fmt_order_date(e['order_date'])}) — {e['location']}"
                for e in stock_entries
            ][cite: 1]
            stock_sel = st.selectbox("Select entry to edit", stock_labels, key="stock_edit_select")[cite: 1]
            stock_loaded = stock_entries[stock_labels.index(stock_sel)][cite: 1]
            stock_editing_row = stock_loaded["row"][cite: 1]
            st.caption("Loaded - edit the fields below, then click Update entry to save changes to this same row.")[cite: 1]

    sk = f"_{stock_editing_row}" if stock_editing_row else "_new"[cite: 1]
    st.caption("Log a supplier delivery. Ordered and Damaged are optional - fill in what you have.")[cite: 1]

    def _parse_date_or(s, fallback):[cite: 1]
        if not s or not str(s).strip():[cite: 1]
            return fallback[cite: 1]
        try:
            d = pd.to_datetime(s)[cite: 1]
            return fallback if pd.isna(d) else d.date()[cite: 1]
        except Exception:
            return fallback[cite: 1]

    c1, c2, c3 = st.columns(3)[cite: 1]
    with c1:[cite: 1]
        order_date = st.date_input(
            "Order date",
            value=_parse_date_or(stock_loaded["order_date"], date.today()) if stock_loaded else date.today(),
            key=f"stock_order_date{sk}",
        )[cite: 1]
    with c2:[cite: 1]
        received_date = st.date_input(
            "Received date",
            value=stock_loaded["received_date"].date() if stock_loaded else date.today(),
            key=f"stock_received_date{sk}",
        )[cite: 1]
    with c3:[cite: 1]
        location = st.text_input("Location", value=(stock_loaded["location"] if stock_loaded else CITY), key=f"stock_location{sk}")[cite: 1]

    flavor_names = [f[1] for f in FLAVORS][cite: 1]
    default_cost = [f[3] for f in FLAVORS][cite: 1]
    df_init = pd.DataFrame(
        {
            "Flavour": flavor_names,
            "Ordered": stock_loaded["ordered"] if stock_loaded else [0] * N_FLAVORS,
            "Received": stock_loaded["received"] if stock_loaded else [0] * N_FLAVORS,
            "Cost (₹, total)": stock_loaded["cost"] if stock_loaded else [0.0] * N_FLAVORS,
            "Damaged": stock_loaded["damaged"] if stock_loaded else [0] * N_FLAVORS,
        }
    )[cite: 1]
    st.write("Enter units per flavour:")[cite: 1]
    stock_edited = st.data_editor(
        df_init,
        column_config={
            "Flavour": st.column_config.TextColumn(disabled=True),
            "Ordered": st.column_config.NumberColumn(min_value=0, step=1),
            "Received": st.column_config.NumberColumn(min_value=0, step=1),
            "Cost (₹, total)": st.column_config.NumberColumn(min_value=0.0, step=10.0, help="Total cost for the received quantity of this flavour"),
            "Damaged": st.column_config.NumberColumn(min_value=0, step=1),
        },
        hide_index=True,
        use_container_width=True,
        key=f"stock_editor{sk}",
    )[cite: 1]

    ordered = stock_edited["Ordered"].fillna(0).astype(int).tolist()[cite: 1]
    received = stock_edited["Received"].fillna(0).astype(int).tolist()[cite: 1]
    cost = stock_edited["Cost (₹, total)"].fillna(0).astype(float).tolist()[cite: 1]
    damaged = stock_edited["Damaged"].fillna(0).astype(int).tolist()[cite: 1]

    st.caption(
        "Standard cost price per unit — Malai ₹22, Mini Malai ₹18, Pista ₹22, Mango ₹22, "
        "Kesar Badam ₹27.5, Badam Matka ₹44, Shahi Gulab ₹27.5, Chocolate ₹27.5, Roasted Almond ₹33 "
        "— multiply by units received for a quick cost estimate per flavour."
    )[cite: 1]

    st.markdown("---")[cite: 1]
    st.write("**Payment**")[cite: 1]
    c4, c5 = st.columns(2)[cite: 1]
    with c4:[cite: 1]
        default_payment_amount = stock_loaded["payment_amount"] if stock_loaded else float(sum(cost))[cite: 1]
        payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=float(default_payment_amount), step=10.0, key=f"stock_pay_amt{sk}")[cite: 1]
    with c5:[cite: 1]
        default_status_idx = PAYMENT_STATUSES.index(stock_loaded["payment_status"]) if stock_loaded and stock_loaded["payment_status"] in PAYMENT_STATUSES else 0[cite: 1]
        payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=default_status_idx, key=f"stock_pay_status{sk}")[cite: 1]

    has_payment_date = st.checkbox("Add payment date", value=bool(stock_loaded and stock_loaded["payment_date"]), key=f"stock_has_paydate{sk}")[cite: 1]
    payment_date = (
        st.date_input(
            "Payment date",
            value=_parse_date_or(stock_loaded["payment_date"], date.today()) if (stock_loaded and stock_loaded["payment_date"]) else date.today(),
            key=f"stock_payment_date{sk}",
        )
        if has_payment_date
        else None
    )[cite: 1]
    payment_details = st.text_input("Payment details (optional)", value=(stock_loaded["payment_details"] if stock_loaded else ""), placeholder="e.g. UPI ref / who paid", key=f"stock_pay_details{sk}")[cite: 1]

    has_damaged_return = st.checkbox("Damaged items were returned", value=bool(stock_loaded and stock_loaded["damaged_returned_on"]), key=f"stock_has_damret{sk}")[cite: 1]
    damaged_returned_on = (
        st.date_input(
            "Damaged items returned on",
            value=_parse_date_or(stock_loaded["damaged_returned_on"], date.today()) if (stock_loaded and stock_loaded["damaged_returned_on"]) else date.today(),
            key=f"stock_damaged_date{sk}",
        )
        if has_damaged_return
        else None
    )[cite: 1]

    notes = st.text_input("Notes (optional)", value=(stock_loaded["notes"] if stock_loaded else ""), key=f"stock_notes{sk}")[cite: 1]

    stock_button_label = "Update entry" if stock_editing_row else "Save stock received"[cite: 1]
    if st.button(stock_button_label, type="primary", use_container_width=True):[cite: 1]
        if sum(received) == 0:[cite: 1]
            st.error("Enter at least one quantity received before saving.")[cite: 1]
        else:
            try:
                if stock_editing_row:[cite: 1]
                    update_stock_entry(
                        stock_editing_row, order_date, received_date, location,
                        ordered, received, cost, damaged,
                        payment_amount, payment_status, payment_date, payment_details,
                        damaged_returned_on, notes,
                    )[cite: 1]
                    st.success(f"Updated entry for {received_date.strftime('%d %b %Y')} at {location}.")[cite: 1]
                else:
                    append_stock_entry(
                        order_date, received_date, location,
                        ordered, received, cost, damaged,
                        payment_amount, payment_status, payment_date, payment_details,
                        damaged_returned_on, notes,
                    )[cite: 1]
                    st.success(f"Saved {sum(received)} units received on {received_date.strftime('%d %b %Y')}.")[cite: 1]
                st.cache_resource.clear()[cite: 1]
            except Exception as e:
                st.error(f"Could not save - {e}")[cite: 1]

# ---------------- FREEZER ANALYSIS ----------------
elif page == "Freezer Analysis":[cite: 1]
    st.subheader("Freezer stock analysis & reorder planner")[cite: 1]
    st.caption("Uses your recent sales pace to estimate when the freezer will run low, and what to order next.")[cite: 1]

    ac1, ac2, ac3 = st.columns(3)[cite: 1]
    with ac1:[cite: 1]
        lookback_days = st.number_input("Lookback window for avg. daily sales (days)", min_value=3, max_value=90, value=14, step=1)[cite: 1]
    with ac2:[cite: 1]
        buffer_days = st.number_input("Minimum buffer to maintain (days)", min_value=0, max_value=14, value=3, step=1)[cite: 1]
    with ac3:[cite: 1]
        cover_days = st.number_input("Next order should cover (days)", min_value=1, max_value=30, value=7, step=1)[cite: 1]

    try:
        daily_df_fa = load_daily_df()[cite: 1]
        freezer_stock_fa = get_freezer_stock()[cite: 1]
    except Exception as e:
        daily_df_fa = pd.DataFrame()[cite: 1]
        freezer_stock_fa = [0] * N_FLAVORS[cite: 1]
        st.warning(f"Could not load data yet ({e}).")[cite: 1]

    if daily_df_fa.empty:[cite: 1]
        st.info("No sales logged yet - once you've saved a few days of sales, this tab will estimate freezer run-out dates.")[cite: 1]
    else:
        today_fa = date.today()[cite: 1]
        cutoff_fa = today_fa - timedelta(days=lookback_days - 1)[cite: 1]
        window_df = daily_df_fa[(daily_df_fa["Date"].dt.date >= cutoff_fa) & (daily_df_fa["Date"].dt.date <= today_fa)][cite: 1]

        flavor_sold_window = [0] * N_FLAVORS[cite: 1]
        for arr in window_df["Sold_By_Flavor"]:[cite: 1]
            for i in range(N_FLAVORS):[cite: 1]
                flavor_sold_window[i] += arr[i][cite: 1]
        avg_daily = [s / lookback_days for s in flavor_sold_window][cite: 1]

        rows = [][cite: 1]
        trigger_dates = [][cite: 1]
        for i, f in enumerate(FLAVORS):[cite: 1]
            stock = freezer_stock_fa[i][cite: 1]
            rate = avg_daily[i][cite: 1]
            if rate <= 0:[cite: 1]
                days_left = None[cite: 1]
                status = "No recent sales"[cite: 1]
                trigger_date = None[cite: 1]
                suggested_qty = 0[cite: 1]
            else:
                days_left = stock / rate[cite: 1]
                trigger_date = today_fa + timedelta(days=max(0, days_left - buffer_days))[cite: 1]
                trigger_dates.append(trigger_date)[cite: 1]
                if days_left <= buffer_days:[cite: 1]
                    status = "Order now"[cite: 1]
                elif days_left <= buffer_days + 2:[cite: 1]
                    status = "Order soon"[cite: 1]
                else:
                    status = "OK"[cite: 1]
                suggested_qty = int(round(rate * cover_days / 10.0)) * 10[cite: 1]

            rows.append(
                {
                    "Flavour": f[1],
                    "Freezer stock": stock,
                    "Avg. daily sales": round(rate),
                    "Days of stock left": round(days_left) if days_left is not None else "—",
                    "Status": status,
                    f"Suggested next order ({cover_days}d)": suggested_qty,
                }
            )[cite: 1]

        analysis_df = pd.DataFrame(rows)[cite: 1]

        total_stock = sum(freezer_stock_fa)[cite: 1]
        total_rate = sum(avg_daily)[cite: 1]
        overall_days_left = (total_stock / total_rate) if total_rate > 0 else None[cite: 1]
        overall_order_date = min(trigger_dates) if trigger_dates else None[cite: 1]

        st.markdown("### Overall picture")[cite: 1]
        oc1, oc2, oc3 = st.columns(3)[cite: 1]
        oc1.metric("Total freezer stock", f"{total_stock} units")[cite: 1]
        oc2.metric("Avg. daily sales (all flavours)", f"{total_rate:.0f} units/day")[cite: 1]
        oc3.metric("Overall days of stock left", f"{overall_days_left:.0f}" if overall_days_left is not None else "—")[cite: 1]

        if overall_order_date is not None:[cite: 1]
            if overall_order_date <= today_fa:[cite: 1]
                st.error(f"**Place your next order now** — at least one flavour is already at or below your {buffer_days}-day buffer.")[cite: 1]
            else:
                days_until = (overall_order_date - today_fa).days[cite: 1]
                st.success(f"**Next order should be placed by {overall_order_date.strftime('%d %b %Y')}** (in {days_until} day{'s' if days_until != 1 else ''}) to keep every flavour above your {buffer_days}-day buffer.")[cite: 1]
        else:
            st.caption("Not enough recent sales data to estimate a reorder date yet.")[cite: 1]

        st.markdown("### Per-flavour breakdown")[cite: 1]
        st.dataframe(
            analysis_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Status": st.column_config.TextColumn(help="Order now: at/below buffer. Order soon: within 2 days of buffer. OK: comfortably above buffer."),
            },
        )[cite: 1]

        st.markdown("### Suggested next order (flavour mix based on recent sales)")[cite: 1]
        order_df = analysis_df[["Flavour", f"Suggested next order ({cover_days}d)"]].rename(
            columns={f"Suggested next order ({cover_days}d)": "Units to order"}
        )[cite: 1]
        total_suggested = int(order_df["Units to order"].sum())[cite: 1]
        st.dataframe(order_df, hide_index=True, use_container_width=True)[cite: 1]
        st.caption(
            f"Total suggested order: {total_suggested} units, split across flavours in the same proportion as your last "
            f"{lookback_days} days of sales — so your best-sellers get restocked the most. Adjust the controls above to "
            f"widen/narrow the sales window, change your buffer, or size the order differently."
        )[cite: 1]

        st.markdown("### Days of stock left, by flavour")[cite: 1]
        chart_df = analysis_df[analysis_df["Days of stock left"] != "—"].copy()[cite: 1]
        if not chart_df.empty:[cite: 1]
            chart_df["Days of stock left"] = chart_df["Days of stock left"].astype(float)[cite: 1]
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
            )[cite: 1]
            rule = alt.Chart(pd.DataFrame({"y": [buffer_days]})).mark_rule(color="#4A2418", strokeDash=[4, 4]).encode(y="y:Q")[cite: 1]
            st.altair_chart(days_chart + rule, use_container_width=True)[cite: 1]
            st.caption(f"Dashed line marks your {buffer_days}-day buffer. Red bars are at or below it.")[cite: 1]

# ---------------- EXPENSES ----------------
elif page == "Expenses":[cite: 1]
    st.subheader("Log an expense")[cite: 1]

    exp_mode = st.radio("Mode", ["New entry", "Edit past entry"], horizontal=True, key="exp_mode")[cite: 1]

    exp_loaded = None[cite: 1]
    exp_editing_row = None[cite: 1]
    if exp_mode == "Edit past entry":[cite: 1]
        try:
            expense_entries = list_expense_entries()[cite: 1]
        except Exception as e:
            expense_entries = [][cite: 1]
            st.warning(f"Could not load past entries ({e}).")[cite: 1]
        if not expense_entries:[cite: 1]
            st.info("No past entries found yet.")[cite: 1]
        else:
            exp_labels = [f"{e['date'].strftime('%d %b %Y')} — {e['description'] or e['category']} (₹{e['amount']:,.0f})" for e in expense_entries][cite: 1]
            exp_sel = st.selectbox("Select entry to edit", exp_labels, key="exp_edit_select")[cite: 1]
            exp_loaded = expense_entries[exp_labels.index(exp_sel)][cite: 1]
            exp_editing_row = exp_loaded["row"][cite: 1]
            st.caption("Loaded - edit the fields below, then click Update entry to save changes to this same row.")[cite: 1]

    ek = f"_{exp_editing_row}" if exp_editing_row else "_new"[cite: 1]

    c1, c2 = st.columns(2)[cite: 1]
    with c1:[cite: 1]
        exp_date = st.date_input("Date", value=(exp_loaded["date"].date() if exp_loaded else date.today()), key=f"exp_date{ek}")[cite: 1]
    with c2:[cite: 1]
        default_cat_idx = EXPENSE_CATEGORIES.index(exp_loaded["category"]) if exp_loaded and exp_loaded["category"] in EXPENSE_CATEGORIES else 0[cite: 1]
        category = st.selectbox("Category", EXPENSE_CATEGORIES, index=default_cat_idx, key=f"exp_category{ek}")[cite: 1]

    description = st.text_input("Description", value=(exp_loaded["description"] if exp_loaded else ""), placeholder="e.g. Kulfi stock from supplier", key=f"exp_desc{ek}")[cite: 1]
    amount = st.number_input("Amount (₹)", min_value=0.0, value=(exp_loaded["amount"] if exp_loaded else 0.0), step=10.0, key=f"exp_amount{ek}")[cite: 1]

    c3, c4 = st.columns(2)[cite: 1]
    with c3:[cite: 1]
        default_mode_idx = PAYMENT_MODES.index(exp_loaded["mode"]) if exp_loaded and exp_loaded["mode"] in PAYMENT_MODES else 0[cite: 1]
        mode = st.selectbox("Payment mode", PAYMENT_MODES, index=default_mode_idx, key=f"exp_mode_select{ek}")[cite: 1]
    with c4:[cite: 1]
        ref_no = st.text_input("Transaction ref. no. (optional)", value=(exp_loaded["ref_no"] if exp_loaded else ""), key=f"exp_ref{ek}")[cite: 1]

    paid_to = st.text_input("Paid to (optional)", value=(exp_loaded["paid_to"] if exp_loaded else ""), key=f"exp_paidto{ek}")[cite: 1]
    exp_remarks = st.text_input("Remarks (optional)", value=(exp_loaded["remarks"] if exp_loaded else ""), key=f"exp_remarks{ek}")[cite: 1]

    exp_button_label = "Update entry" if exp_editing_row else "Save expense"[cite: 1]
    if st.button(exp_button_label, type="primary", use_container_width=True):[cite: 1]
        if amount <= 0:[cite: 1]
            st.error("Enter an amount greater than 0.")[cite: 1]
        else:
            try:
                if exp_editing_row:[cite: 1]
                    update_expense(exp_editing_row, exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)[cite: 1]
                    st.success(f"Updated ₹{amount:,.0f} expense under {category}.")[cite: 1]
                else:
                    append_expense(exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)[cite: 1]
                    st.success(f"Saved ₹{amount:,.0f} expense under {category}.")[cite: 1]
                st.cache_resource.clear()[cite: 1]
            except Exception as e:
                st.error(f"Could not save - {e}")[cite: 1]

# ---------------- DASHBOARD ----------------
elif page == "Dashboard":[cite: 1]
    st.subheader("Quick view")[cite: 1]

    with st.expander("Data health check — tap here if the dashboard looks empty"):[cite: 1]
        try:
            wb = get_workbook()[cite: 1]
            tab_names = [ws.title for ws in wb.worksheets()][cite: 1]
            st.write("Tabs found in your connected Google Sheet:")[cite: 1]
            st.code("\n".join(tab_names))[cite: 1]
        except Exception as e:
            tab_names = [][cite: 1]
            st.error(f"Could not connect to the Google Sheet at all: {e}")[cite: 1]

        for label, tab in [
            ("Daily Data As Shared", "Daily Data As Shared"),
            ("Stock Received", "Stock Received"),
            ("Expenses", "Expenses"),
        ]:[cite: 1]
            st.markdown(f"**{label}**")[cite: 1]
            if tab not in tab_names:[cite: 1]
                st.warning(f"No tab named exactly `{tab}` was found. Check for a trailing space, "
                            f"a renamed tab, or extra hidden characters in the tab name in your Google Sheet.")[cite: 1]
                continue[cite: 1]
            try:
                if tab == "Daily Data As Shared":[cite: 1]
                    _, raw_rows = load_daily_raw()[cite: 1]
                    padded = [_pad(r, DAILY_TOTAL_COLS) for r in raw_rows if r and r[0].strip()][cite: 1]
                    real = [r for r in padded if _row_has_data(r)][cite: 1]
                    st.write(f"{len(padded)} row(s) with a date, {len(real)} of those have actual sales/stock data "
                              f"(the rest are blank future placeholder rows already in your sheet).")[cite: 1]
                    if real:[cite: 1]
                        st.write("Most recent real entry:", real[-1][:2])[cite: 1]
                    continue[cite: 1]
                elif tab == "Stock Received":[cite: 1]
                    _, raw_rows = load_stock_raw()[cite: 1]
                else:
                    ws = get_ws("Expenses")[cite: 1]
                    raw_rows = ws.get_all_values()[EXPENSE_HEADER_ROWS:][cite: 1]
                non_empty = [r for r in raw_rows if r and r[0].strip()][cite: 1]
                st.write(f"{len(non_empty)} data row(s) found.")[cite: 1]
                if non_empty:[cite: 1]
                    st.write("First row's first few cells:", non_empty[0][:4])[cite: 1]
                    st.write("Last row's first few cells:", non_empty[-1][:4])[cite: 1]
            except Exception as e:
                st.error(f"Error reading `{tab}`: {e}")[cite: 1]

    try:
        daily_df = load_daily_df()[cite: 1]
        exp_df = load_expenses_df()[cite: 1]
    except Exception as e:
        daily_df = pd.DataFrame()[cite: 1]
        exp_df = pd.DataFrame()[cite: 1]
        st.warning(f"Could not load data yet ({e}).")[cite: 1]

    today = pd.Timestamp(date.today())[cite: 1]
    day_labels = [today - pd.Timedelta(days=3), today - pd.Timedelta(days=2), today - pd.Timedelta(days=1)][cite: 1]
    if not daily_df.empty:[cite: 1]
        day_rows = [daily_df[daily_df["Date"].dt.date == d.date()] for d in day_labels][cite: 1]
        day_rev = [r["Total_Collection"].sum() for r in day_rows][cite: 1]
        day_units = [int(r["Sold_Total"].sum()) for r in day_rows][cite: 1]

        col_names = [d.strftime("%d %b") for d in day_labels][cite: 1]
        col_names[-1] = col_names[-1] + " (Yesterday)"[cite: 1]

        compare_df = pd.DataFrame(
            {
                "Metric": ["Revenue", "Units sold"],
                col_names[0]: [f"₹{day_rev[0]:,.0f}", f"{day_units[0]}"],
                col_names[1]: [f"₹{day_rev[1]:,.0f}", f"{day_units[1]}"],
                col_names[2]: [f"₹{day_rev[2]:,.0f}", f"{day_units[2]}"],
            }
        )[cite: 1]
        st.markdown('<div id="last-3-days"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("**Last 3 days**")[cite: 1]
        st.dataframe(compare_df, hide_index=True, use_container_width=True)[cite: 1]

        st.metric("Stock across carts", f"{int(daily_df.sort_values('Date').groupby('Cart').tail(1)['Closing_Total'].sum())}")[cite: 1]

        try:
            freezer_stock = get_freezer_stock()[cite: 1]
            st.markdown('<div id="freezer-stock-current"></div>', unsafe_allow_html=True)[cite: 1]
            st.markdown("**Freezer stock (current)**")[cite: 1]
            freezer_df = pd.DataFrame({"Flavour": [f[1] for f in FLAVORS], "Units in freezer": freezer_stock})[cite: 1]
            st.dataframe(freezer_df, hide_index=True, use_container_width=True)[cite: 1]
        except Exception as e:
            st.caption(f"Could not compute freezer stock ({e}).")[cite: 1]

        st.markdown('<div id="revenue-trend"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("**Revenue, last 14 days**")[cite: 1]
        trend_df = (
            daily_df.assign(Day=daily_df["Date"].dt.normalize())
            .groupby("Day", as_index=False)["Total_Collection"]
            .sum()
            .sort_values("Day")
            .tail(14)
        )[cite: 1]
        trend_chart = (
            alt.Chart(trend_df)
            .mark_bar(color="#E8542A")
            .encode(
                x=alt.X("Day:T", title="", axis=alt.Axis(format="%d %b", labelAngle=-45)),
                y=alt.Y("Total_Collection:Q", title="Revenue (₹)", scale=alt.Scale(domain=[0, 25000])),
                tooltip=[alt.Tooltip("Day:T", title="Date", format="%d %b %Y"), alt.Tooltip("Total_Collection:Q", title="Revenue", format=",.0f")],
            )
            .properties(height=280)
        )[cite: 1]
        st.altair_chart(trend_chart, use_container_width=True)[cite: 1]

        st.markdown('<div id="latest-stock-per-cart"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("**Latest stock per cart**")[cite: 1]
        latest_per_cart = daily_df.sort_values("Date").groupby("Cart").tail(1)[["Cart", "Date", "Closing_Total"]][cite: 1]
        st.dataframe(latest_per_cart, hide_index=True, use_container_width=True)[cite: 1]
    else:
        st.info("No sales logged yet - entries you save in the Daily Entry tab will show up here.")[cite: 1]

    # ------------------ Date-range reports ------------------
    if not daily_df.empty or not exp_df.empty:[cite: 1]
        st.markdown("---")[cite: 1]
        st.markdown('<div id="reports"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("## Reports")[cite: 1]

        all_dates = [][cite: 1]
        if not daily_df.empty:[cite: 1]
            all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()][cite: 1]
        if not exp_df.empty and exp_df["Date"].notna().any():[cite: 1]
            all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()][cite: 1]
        min_d, max_d = min(all_dates), max(all_dates)[cite: 1]
        default_start = max(min_d, max_d - timedelta(days=29))[cite: 1]

        if "applied_start" not in st.session_state:[cite: 1]
            st.session_state["applied_start"] = default_start[cite: 1]
        if "applied_end" not in st.session_state:[cite: 1]
            st.session_state["applied_end"] = max_d[cite: 1]
        st.session_state["applied_start"] = min(max(st.session_state["applied_start"], min_d), max_d)[cite: 1]
        st.session_state["applied_end"] = min(max(st.session_state["applied_end"], min_d), max_d)[cite: 1]

        with st.form("date_range_form"):[cite: 1]
            rc1, rc2, rc3 = st.columns([2, 2, 1])[cite: 1]
            with rc1:[cite: 1]
                pending_start = st.date_input("From", value=st.session_state["applied_start"], min_value=min_d, max_value=max_d)[cite: 1]
            with rc2:[cite: 1]
                pending_end = st.date_input("To", value=st.session_state["applied_end"], min_value=min_d, max_value=max_d)[cite: 1]
            with rc3:[cite: 1]
                st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)[cite: 1]
                apply_clicked = st.form_submit_button("Apply", type="primary", use_container_width=True)[cite: 1]

        if apply_clicked:[cite: 1]
            st.session_state["applied_start"] = pending_start[cite: 1]
            st.session_state["applied_end"] = pending_end[cite: 1]

        range_start = st.session_state["applied_start"][cite: 1]
        range_end = st.session_state["applied_end"][cite: 1]

        if range_start > range_end:[cite: 1]
            st.error("'From' date is after 'To' date - swap them and click Apply again.")[cite: 1]
            range_start, range_end = range_end, range_start[cite: 1]

        st.caption(f"Showing: {range_start.strftime('%d %b %Y')} – {range_end.strftime('%d %b %Y')}")[cite: 1]

        range_df = daily_df[(daily_df["Date"].dt.date >= range_start) & (daily_df["Date"].dt.date <= range_end)] if not daily_df.empty else daily_df[cite: 1]
        range_exp = exp_df[(exp_df["Date"].dt.date >= range_start) & (exp_df["Date"].dt.date <= range_end)] if not exp_df.empty else exp_df[cite: 1]

        total_rev = range_df["Total_Collection"].sum() if not range_df.empty else 0.0[cite: 1]
        total_units = int(range_df["Sold_Total"].sum()) if not range_df.empty else 0[cite: 1]
        total_exp_all = range_exp["Amount"].sum() if not range_exp.empty else 0.0[cite: 1]

        mc1, mc2, mc3 = st.columns(3)[cite: 1]
        mc1.metric("Revenue in range", f"₹{total_rev:,.0f}")[cite: 1]
        mc2.metric("Units sold in range", f"{total_units}")[cite: 1]
        mc3.metric("Expenses in range", f"₹{total_exp_all:,.0f}")[cite: 1]

        # ---- Cart-wise comparison ----
        st.markdown('<div id="cart-wise-comparison"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Cart-wise comparison")[cite: 1]
        if not range_df.empty:[cite: 1]
            cart_grp = (
                range_df.groupby("Cart")
                .agg(**{"Revenue (₹)": ("Total_Collection", "sum"), "Units sold": ("Sold_Total", "sum")})
                .reset_index()
                .sort_values("Revenue (₹)", ascending=False)
            )[cite: 1]
            st.dataframe(cart_grp, hide_index=True, use_container_width=True)[cite: 1]
            st.bar_chart(cart_grp.set_index("Cart")["Revenue (₹)"])[cite: 1]
        else:
            st.caption("No sales in this date range.")[cite: 1]

        # ---- Cart-wise x day-of-week sales ----
        st.markdown('<div id="cart-wise-day-of-week"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Cart-wise average sales by day of the week")[cite: 1]
        if not range_df.empty:[cite: 1]
            day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][cite: 1]
            dow_df = range_df[range_df["Sold_Total"] > 0].copy()[cite: 1]
            dow_df["Day"] = dow_df["Date"].dt.day_name()[cite: 1]

            if dow_df.empty:[cite: 1]
                st.caption("No days with actual sales in this date range.")[cite: 1]
            else:
                units_pivot = dow_df.pivot_table(
                    index="Cart", columns="Day", values="Sold_Total", aggfunc="mean", fill_value=0, margins=True, margins_name="All carts"
                )[cite: 1]
                day_cols = [d for d in day_order if d in units_pivot.columns] + ["All carts"][cite: 1]
                units_pivot = units_pivot.reindex(columns=day_cols)[cite: 1]

                rev_pivot = dow_df.pivot_table(
                    index="Cart", columns="Day", values="Total_Collection", aggfunc="mean", fill_value=0, margins=True, margins_name="All carts"
                )[cite: 1]
                rev_pivot = rev_pivot.reindex(columns=day_cols)[cite: 1]

                st.write("**Avg. units sold** (rows = cart, columns = day of week)")[cite: 1]
                st.dataframe(units_pivot.round(1), use_container_width=True)[cite: 1]

                st.write("**Avg. revenue (₹)** (rows = cart, columns = day of week)")[cite: 1]
                st.dataframe(rev_pivot.round(0).astype(int), use_container_width=True)[cite: 1]

                st.caption("Zero-sales days are excluded, so each cell is the average over the days that weekday actually had sales. 'All carts' shows the overall average across carts / days.")[cite: 1]
        else:
            st.caption("No sales in this date range.")[cite: 1]

        # ---- Flavour-wise performance ----
        st.markdown('<div id="flavour-wise-performance"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Flavour-wise performance")[cite: 1]
        if not range_df.empty:[cite: 1]
            flavor_sold = [0] * N_FLAVORS[cite: 1]
            for arr in range_df["Sold_By_Flavor"]:[cite: 1]
                for i in range(N_FLAVORS):[cite: 1]
                    flavor_sold[i] += arr[i][cite: 1]
            flavor_df = pd.DataFrame(
                {
                    "Flavour": [f[1] for f in FLAVORS],
                    "Units sold": flavor_sold,
                    "Est. revenue (₹)": [flavor_sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS)],
                }
            ).sort_values("Units sold", ascending=False)[cite: 1]
            st.dataframe(flavor_df, hide_index=True, use_container_width=True)[cite: 1]
            st.bar_chart(flavor_df.set_index("Flavour")["Units sold"])[cite: 1]
            st.caption("Estimated revenue = units sold × MRP per flavour; actual collections may vary slightly (discounts, complementary pieces etc).")[cite: 1]
        else:
            st.caption("No sales in this date range.")[cite: 1]

        # ---- Profit & Loss summary ----
        st.markdown('<div id="profit-loss-summary"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Profit & loss summary")[cite: 1]
        cogs = range_exp[range_exp["Category"] == "Cost of Goods"]["Amount"].sum() if not range_exp.empty else 0.0[cite: 1]
        opex_cats = ["Labour Charges", "Leakage Expense", "Miscellaneous Expense"][cite: 1]
        opex = range_exp[range_exp["Category"].isin(opex_cats)]["Amount"].sum() if not range_exp.empty else 0.0[cite: 1]
        capital_cats = ["Initial Investment", "Initial Set-up Expense"][cite: 1]
        capital = range_exp[range_exp["Category"].isin(capital_cats)]["Amount"].sum() if not range_exp.empty else 0.0[cite: 1]
        gross_profit = total_rev - cogs[cite: 1]
        net_profit = gross_profit - opex[cite: 1]

        pnl_df = pd.DataFrame(
            {
                "Line item": ["Revenue", "Cost of Goods", "Gross profit", "Operating expenses (labour, leakage, misc.)", "Net profit"],
                "Amount (₹)": [total_rev, -cogs, gross_profit, -opex, net_profit],
            }
        )[cite: 1]
        st.dataframe(pnl_df, hide_index=True, use_container_width=True)[cite: 1]
        pc1, pc2 = st.columns(2)[cite: 1]
        pc1.metric("Net profit", f"₹{net_profit:,.0f}")[cite: 1]
        pc2.metric("Margin", f"{(net_profit / total_rev * 100) if total_rev else 0:.1f}%")[cite: 1]
        if capital > 0:[cite: 1]
            st.caption(f"₹{capital:,.0f} of one-time capital/setup costs fell in this range and is shown separately below, not deducted above.")[cite: 1]

        # ---- Expense breakdown ----
        st.markdown('<div id="expense-breakdown"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Expense breakdown by category")[cite: 1]
        if not range_exp.empty:[cite: 1]
            by_cat = range_exp.groupby("Category")["Amount"].sum().sort_values(ascending=False)[cite: 1]
            st.dataframe(
                by_cat.reset_index().rename(columns={"Amount": "₹"}),
                hide_index=True,
                use_container_width=True,
                column_config={"₹": st.column_config.ProgressColumn("Share", format="₹%.0f", min_value=0, max_value=float(by_cat.max()))},
            )[cite: 1]
            st.bar_chart(by_cat)[cite: 1]
        else:
            st.caption("No expenses logged in this date range.")[cite: 1]

        # ---- Cash vs PhonePe ----
        st.markdown('<div id="cash-vs-phonepe"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Cash vs PhonePe / UPI")[cite: 1]
        if not range_df.empty:[cite: 1]
            total_cash = range_df["Cash"].sum()[cite: 1]
            total_phonepe = range_df["PhonePe"].sum()[cite: 1]
            cc1, cc2 = st.columns(2)[cite: 1]
            cc1.metric("Cash", f"₹{total_cash:,.0f}")[cite: 1]
            cc2.metric("PhonePe / UPI", f"₹{total_phonepe:,.0f}")[cite: 1]
            split_df = pd.DataFrame({"Mode": ["Cash", "PhonePe / UPI"], "Amount (₹)": [total_cash, total_phonepe]})[cite: 1]
            st.bar_chart(split_df.set_index("Mode")["Amount (₹)"])[cite: 1]
        else:
            st.caption("No collections in this date range.")[cite: 1]

        # ---- Date-range sales table ----
        st.markdown('<div id="sales-in-range"></div>', unsafe_allow_html=True)[cite: 1]
        st.markdown("### Sales in this range")[cite: 1]
        if not range_df.empty:[cite: 1]
            sales_table = range_df.sort_values(["Date", "Cart"])[["Date", "Cart", "Sold_Total", "Total_Collection"]].rename(
                columns={"Sold_Total": "Units sold", "Total_Collection": "Revenue (₹)"}
            )[cite: 1]
            sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")[cite: 1]
            st.dataframe(sales_table, hide_index=True, use_container_width=True)[cite: 1]
        else:
            st.caption("No sales in this date range.")[cite: 1]