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
from datetime import date, datetime, timedelta

st.set_page_config(page_title="Kulfi Ops", page_icon="🍦", layout="centered")

# ----------------------------------------------------------------------
# CONFIG - edit these if your cart names / flavours / sheet ever change
# ----------------------------------------------------------------------
CARTS = ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"]
CITY = "HOSUR"

# (code, full name, MRP per unit, cost price per unit) - order matches the
# column order used across all tabs (ML, MM, PS, MN, KB, BM, SG, CH, RA)
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

# Fixed column layout of "Daily Data As Shared" (1-indexed, A=1).
# Date | Cart | City | DATE CART ID | Opening x9 | Added x9 | Sold x9 | Closing x9 | Total | PhonePe | Cash | Remarks
DAILY_HEADER_ROWS = 2          # two header rows before data starts
DAILY_TOTAL_COLS = 4 + 9 * 4 + 4  # = 44

EXPENSE_HEADER_ROWS = 3

# Fixed column layout of "Stock Received" (1-indexed cols A-BH, 60 total).
# OrderDate|RecvDate|Location|DATE LOC ID | Ordered x9+Total | Received x9+Total
# | Diff x9+Total | Cost x9+Total | PaymentAmt|Status|PayDate|PayDetails
# | Damaged x9+Total | DamagedReturnedOn | Notes
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
    """The sheet has pre-filled placeholder rows (date + cart already filled
    in) for future dates that haven't happened yet - every quantity/collection
    cell on those is blank. Treat a row as 'real' only if at least one of its
    numeric cells (opening balance through Cash) actually has something in it."""
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


def get_opening_balance(cart_name):
    """Find the most recent closing balance for this cart -> becomes opening balance for today."""
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
    closing_start = 4 + 9 * 3  # index of first closing-balance column (0-indexed)
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


def append_stock_entry(
    order_date, received_date, location,
    ordered, received, cost, damaged,
    payment_amount, payment_status, payment_date, payment_details,
    damaged_returned_on, notes,
):
    diff = [received[i] - ordered[i] for i in range(N_FLAVORS)]
    date_loc_id = f"{received_date.strftime('%Y-%m-%d')}||{location}"
    row = (
        [order_date.strftime("%Y-%m-%d"), received_date.strftime("%Y-%m-%d"), location, date_loc_id]
        + ordered + [sum(ordered)]
        + received + [sum(received)]
        + diff + [sum(diff)]
        + cost + [sum(cost)]
        + [payment_amount, payment_status, payment_date.strftime("%Y-%m-%d") if payment_date else "", payment_details]
        + damaged + [sum(damaged)]
        + [damaged_returned_on.strftime("%Y-%m-%d") if damaged_returned_on else "", notes]
    )
    ws = get_ws("Stock Received")
    ws.append_row(row, value_input_option="USER_ENTERED")


def get_freezer_stock():
    """Freezer balance per flavour = total ever received into freezer, minus
    total ever moved out to carts (from Daily Data As Shared)."""
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
# UI
# ----------------------------------------------------------------------
st.title("🍦 Kulfi Ops")

tab_sale, tab_stock, tab_expense, tab_dash = st.tabs(["Daily Entry", "Freezer Stock", "Expenses", "Dashboard"])

# ---------------- DAILY ENTRY ----------------
with tab_sale:
    st.subheader("Cart restock & daily sales")
    st.caption("One entry per cart per day. Only fill in flavours that actually moved.")

    c1, c2 = st.columns(2)
    with c1:
        entry_date = st.date_input("Date", value=date.today(), key="daily_date")
    with c2:
        cart_name = st.selectbox("Cart", CARTS, key="daily_cart")

    try:
        opening = get_opening_balance(cart_name)
        opening_ok = True
    except Exception as e:
        opening = [0] * N_FLAVORS
        opening_ok = False
        st.warning(f"Could not fetch opening balance automatically ({e}). Starting from 0 - check your figures.")

    flavor_names = [f[1] for f in FLAVORS]
    df_init = pd.DataFrame(
        {
            "Flavour": flavor_names,
            "Opening (in cart)": opening,
            "Added today": [0] * N_FLAVORS,
            "Sold today": [0] * N_FLAVORS,
        }
    )
    st.write("Enter units **added to the cart** (restock) and **units sold**, per flavour:")
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
        key="daily_editor",
    )

    added = edited["Added today"].fillna(0).astype(int).tolist()
    sold = edited["Sold today"].fillna(0).astype(int).tolist()
    projected_closing = [opening[i] + added[i] - sold[i] for i in range(N_FLAVORS)]
    if any(c < 0 for c in projected_closing):
        st.error("Closing balance would go negative for at least one flavour - double check the numbers above.")

    suggested_total = sum(sold[i] * FLAVORS[i][2] for i in range(N_FLAVORS))
    st.markdown("---")
    st.write("**Today's collection**")
    c3, c4, c5 = st.columns(3)
    with c3:
        total_collection = st.number_input("Total collection (₹)", min_value=0.0, value=float(suggested_total), step=10.0)
    with c4:
        phonepe = st.number_input("PhonePe / UPI (₹)", min_value=0.0, value=0.0, step=10.0)
    with c5:
        cash = st.number_input("Cash (₹)", min_value=0.0, value=float(total_collection), step=10.0)

    if abs((phonepe + cash) - total_collection) > 0.5:
        st.warning(f"PhonePe + Cash (₹{phonepe + cash:,.0f}) doesn't match Total collection (₹{total_collection:,.0f}) - fine if intentional, otherwise adjust.")

    remarks = st.text_input("Remarks (optional)", key="daily_remarks")

    if st.button("Save daily entry", type="primary", use_container_width=True):
        if sum(added) == 0 and sum(sold) == 0:
            st.error("Enter at least one quantity added or sold before saving.")
        else:
            try:
                closing = append_daily_entry(entry_date, cart_name, added, sold, opening, total_collection, phonepe, cash, remarks)
                st.success(f"Saved for {cart_name} on {entry_date.strftime('%d %b %Y')}. Closing stock: {sum(closing)} units.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Could not save - {e}")

# ---------------- FREEZER STOCK ----------------
with tab_stock:
    st.subheader("Stock received into freezer")
    st.caption("Log a new supplier delivery. Ordered and Damaged are optional - fill in what you have.")

    c1, c2, c3 = st.columns(3)
    with c1:
        order_date = st.date_input("Order date", value=date.today(), key="stock_order_date")
    with c2:
        received_date = st.date_input("Received date", value=date.today(), key="stock_received_date")
    with c3:
        location = st.text_input("Location", value=CITY, key="stock_location")

    flavor_names = [f[1] for f in FLAVORS]
    default_cost = [f[3] for f in FLAVORS]
    df_init = pd.DataFrame(
        {
            "Flavour": flavor_names,
            "Ordered": [0] * N_FLAVORS,
            "Received": [0] * N_FLAVORS,
            "Cost (₹, total)": [0.0] * N_FLAVORS,
            "Damaged": [0] * N_FLAVORS,
        }
    )
    st.write("Enter units per flavour:")
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
        key="stock_editor",
    )

    ordered = stock_edited["Ordered"].fillna(0).astype(int).tolist()
    received = stock_edited["Received"].fillna(0).astype(int).tolist()
    cost = stock_edited["Cost (₹, total)"].fillna(0).astype(float).tolist()
    damaged = stock_edited["Damaged"].fillna(0).astype(int).tolist()

    st.caption(
        "Standard cost price per unit — Malai ₹22, Mini Malai ₹18, Pista ₹22, Mango ₹22, "
        "Kesar Badam ₹27.5, Badam Matka ₹44, Shahi Gulab ₹27.5, Chocolate ₹27.5, Roasted Almond ₹33 "
        "— multiply by units received for a quick cost estimate per flavour."
    )

    st.markdown("---")
    st.write("**Payment**")
    c4, c5 = st.columns(2)
    with c4:
        payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=float(sum(cost)), step=10.0)
    with c5:
        payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=0)

    has_payment_date = st.checkbox("Add payment date", value=False)
    payment_date = st.date_input("Payment date", value=date.today(), key="stock_payment_date") if has_payment_date else None
    payment_details = st.text_input("Payment details (optional)", placeholder="e.g. UPI ref / who paid")

    has_damaged_return = st.checkbox("Damaged items were returned", value=False)
    damaged_returned_on = st.date_input("Damaged items returned on", value=date.today(), key="stock_damaged_date") if has_damaged_return else None

    notes = st.text_input("Notes (optional)", key="stock_notes")

    if st.button("Save stock received", type="primary", use_container_width=True):
        if sum(received) == 0:
            st.error("Enter at least one quantity received before saving.")
        else:
            try:
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

# ---------------- EXPENSES ----------------
with tab_expense:
    st.subheader("Log an expense")

    c1, c2 = st.columns(2)
    with c1:
        exp_date = st.date_input("Date", value=date.today(), key="exp_date")
    with c2:
        category = st.selectbox("Category", EXPENSE_CATEGORIES)

    description = st.text_input("Description", placeholder="e.g. Kulfi stock from supplier")
    amount = st.number_input("Amount (₹)", min_value=0.0, step=10.0)

    c3, c4 = st.columns(2)
    with c3:
        mode = st.selectbox("Payment mode", PAYMENT_MODES)
    with c4:
        ref_no = st.text_input("Transaction ref. no. (optional)")

    paid_to = st.text_input("Paid to (optional)")
    exp_remarks = st.text_input("Remarks (optional)", key="exp_remarks")

    if st.button("Save expense", type="primary", use_container_width=True):
        if amount <= 0:
            st.error("Enter an amount greater than 0.")
        else:
            try:
                append_expense(exp_date, description, amount, category, mode, ref_no, paid_to, exp_remarks)
                st.success(f"Saved ₹{amount:,.0f} expense under {category}.")
                st.cache_resource.clear()
            except Exception as e:
                st.error(f"Could not save - {e}")

# ---------------- DASHBOARD ----------------
with tab_dash:
    st.subheader("Quick view")

    with st.expander("Data health check — tap here if the dashboard looks empty"):
        try:
            wb = get_workbook()
            tab_names = [ws.title for ws in wb.worksheets()]
            st.write("Tabs found in your connected Google Sheet:")
            st.code("\n".join(tab_names))
        except Exception as e:
            tab_names = []
            st.error(f"Could not connect to the Google Sheet at all: {e}")

        for label, tab in [
            ("Daily Data As Shared", "Daily Data As Shared"),
            ("Stock Received", "Stock Received"),
            ("Expenses", "Expenses"),
        ]:
            st.markdown(f"**{label}**")
            if tab not in tab_names:
                st.warning(f"No tab named exactly `{tab}` was found. Check for a trailing space, "
                            f"a renamed tab, or extra hidden characters in the tab name in your Google Sheet.")
                continue
            try:
                if tab == "Daily Data As Shared":
                    _, raw_rows = load_daily_raw()
                    padded = [_pad(r, DAILY_TOTAL_COLS) for r in raw_rows if r and r[0].strip()]
                    real = [r for r in padded if _row_has_data(r)]
                    st.write(f"{len(padded)} row(s) with a date, {len(real)} of those have actual sales/stock data "
                              f"(the rest are blank future placeholder rows already in your sheet).")
                    if real:
                        st.write("Most recent real entry:", real[-1][:2])
                    continue
                elif tab == "Stock Received":
                    _, raw_rows = load_stock_raw()
                else:
                    ws = get_ws("Expenses")
                    raw_rows = ws.get_all_values()[EXPENSE_HEADER_ROWS:]
                non_empty = [r for r in raw_rows if r and r[0].strip()]
                st.write(f"{len(non_empty)} data row(s) found.")
                if non_empty:
                    st.write("First row's first few cells:", non_empty[0][:4])
                    st.write("Last row's first few cells:", non_empty[-1][:4])
            except Exception as e:
                st.error(f"Error reading `{tab}`: {e}")

    try:
        daily_df = load_daily_df()
        exp_df = load_expenses_df()
    except Exception as e:
        daily_df = pd.DataFrame()
        exp_df = pd.DataFrame()
        st.warning(f"Could not load data yet ({e}).")

    today = pd.Timestamp(date.today())
    if not daily_df.empty:
        today_rows = daily_df[daily_df["Date"].dt.date == today.date()]
        c1, c2, c3 = st.columns(3)
        c1.metric("Revenue today", f"₹{today_rows['Total_Collection'].sum():,.0f}")
        c2.metric("Units sold today", f"{int(today_rows['Sold_Total'].sum())}")
        c3.metric("Stock across carts", f"{int(daily_df.sort_values('Date').groupby('Cart').tail(1)['Closing_Total'].sum())}")

        try:
            freezer_stock = get_freezer_stock()
            st.markdown("**Freezer stock (current)**")
            freezer_df = pd.DataFrame({"Flavour": [f[1] for f in FLAVORS], "Units in freezer": freezer_stock})
            st.dataframe(freezer_df, hide_index=True, use_container_width=True)
        except Exception as e:
            st.caption(f"Could not compute freezer stock ({e}).")

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
            .mark_bar(color="#3E6B4F")
            .encode(
                x=alt.X("Day:T", title="", axis=alt.Axis(format="%d %b", labelAngle=-45)),
                y=alt.Y("Total_Collection:Q", title="Revenue (₹)", scale=alt.Scale(domain=[0, 25000])),
                tooltip=[alt.Tooltip("Day:T", title="Date", format="%d %b %Y"), alt.Tooltip("Total_Collection:Q", title="Revenue", format=",.0f")],
            )
            .properties(height=280)
        )
        st.altair_chart(trend_chart, use_container_width=True)

        st.markdown("**Latest stock per cart**")
        latest_per_cart = daily_df.sort_values("Date").groupby("Cart").tail(1)[["Cart", "Date", "Closing_Total"]]
        st.dataframe(latest_per_cart, hide_index=True, use_container_width=True)
    else:
        st.info("No sales logged yet - entries you save in the Daily Entry tab will show up here.")

    # ------------------ Date-range reports ------------------
    if not daily_df.empty or not exp_df.empty:
        st.markdown("---")
        st.markdown("## Reports")

        all_dates = []
        if not daily_df.empty:
            all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()]
        if not exp_df.empty and exp_df["Date"].notna().any():
            all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()]
        min_d, max_d = min(all_dates), max(all_dates)
        default_start = max(min_d, max_d - timedelta(days=29))

        rc1, rc2 = st.columns(2)
        with rc1:
            range_start = st.date_input("From", value=default_start, min_value=min_d, max_value=max_d, key="report_start")
        with rc2:
            range_end = st.date_input("To", value=max_d, min_value=min_d, max_value=max_d, key="report_end")

        if range_start > range_end:
            st.error("'From' date is after 'To' date - swap them.")
            range_start, range_end = range_end, range_start

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

        # ---- Cash vs PhonePe ----
        st.markdown("### Cash vs PhonePe / UPI")
        if not range_df.empty:
            total_cash = range_df["Cash"].sum()
            total_phonepe = range_df["PhonePe"].sum()
            cc1, cc2 = st.columns(2)
            cc1.metric("Cash", f"₹{total_cash:,.0f}")
            cc2.metric("PhonePe / UPI", f"₹{total_phonepe:,.0f}")
            split_df = pd.DataFrame({"Mode": ["Cash", "PhonePe / UPI"], "Amount (₹)": [total_cash, total_phonepe]})
            st.bar_chart(split_df.set_index("Mode")["Amount (₹)"])
        else:
            st.caption("No collections in this date range.")

        # ---- Date-range sales table ----
        st.markdown("### Sales in this range")
        if not range_df.empty:
            sales_table = range_df.sort_values(["Date", "Cart"])[["Date", "Cart", "Sold_Total", "Total_Collection"]].rename(
                columns={"Sold_Total": "Units sold", "Total_Collection": "Revenue (₹)"}
            )
            sales_table["Date"] = sales_table["Date"].dt.strftime("%d %b %Y")
            st.dataframe(sales_table, hide_index=True, use_container_width=True)
        else:
            st.caption("No sales in this date range.")

