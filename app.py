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
import json
import calendar
import os
import io
import base64
from html import escape
from urllib.parse import quote
from urllib.parse import quote
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

st.set_page_config(page_title="Kulfi Ops", page_icon="🍦", layout="wide", initial_sidebar_state="collapsed")

# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# GLOBAL UI STYLES — DEPOSITO WAREHOUSE ADMIN DASHBOARD THEME
# ----------------------------------------------------------------------
st.html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
/* Cool Sky-Aqua Outer Backdrop */
.stApp, [data-testid="stAppViewContainer"], .main {
    background: linear-gradient(135deg, #BEE3F8 0%, #D8EEF9 45%, #E6F3FB 100%) !important;
    color: #0F172A !important;
}

/* Completely disable & pass-through Streamlit top header overlay so top-row buttons are 100% clickable everywhere */
header[data-testid="stHeader"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"] {
    background: transparent !important;
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    overflow: hidden !important;
    pointer-events: none !important;
    z-index: -1 !important;
    display: none !important;
}

/* Completely hide the default Streamlit left sidebar and toggle button */
section[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
    width: 0 !important;
    min-width: 0 !important;
}

/* Main Dashboard Shell */
.block-container,
div[data-testid="stMainBlockContainer"] {
    background: linear-gradient(180deg, #F4F7FB 0%, #EDF2F8 100%) !important;
    border: 1.5px solid #FFFFFF !important;
    outline: 1px solid rgba(30, 34, 82, 0.08) !important;
    border-radius: 18px !important;
    box-shadow:
        inset 0 1px 0 #FFFFFF,
        0 14px 36px rgba(23, 27, 66, 0.12) !important;
    padding-top: 0.7rem !important;
    padding-bottom: 0.75rem !important;
    padding-left: 1.15rem !important;
    padding-right: 1.15rem !important;
    margin-top: 0.45rem !important;
    margin-bottom: 0.45rem !important;
    margin-left: auto !important;
    margin-right: auto !important;
    width: 95% !important;
    max-width: 1420px !important;
}
@media (max-width: 992px) {
    .block-container,
    div[data-testid="stMainBlockContainer"] {
        width: 98% !important;
        max-width: 98% !important;
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }
}
div[data-testid="stVerticalBlock"] {
    gap: 0.48rem !important;
}
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Manrope', sans-serif;
    font-variant-numeric: tabular-nums;
    color: #0F172A;
}
h1, h2, h3, h4 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #1E2252 !important;
    letter-spacing: -0.015em;
    font-weight: 800 !important;
}
h1 { font-size: 1.28rem !important; margin-top: 0 !important; }
h2 { font-size: 1.10rem !important; }
h3 { font-size: 0.98rem !important; }
p, span, label, .stMarkdown { color: #0F172A; }

/* Hide stepper buttons on number inputs */
input[type=number]::-webkit-inner-spin-button, 
input[type=number]::-webkit-outer-spin-button { 
    -webkit-appearance: none !important;
    margin: 0 !important; 
}
input[type=number] { -moz-appearance: textfield !important; }
div[data-testid="stNumberInput"] button { display: none !important; }

/* Crisp White Elevated Cards, Expanders & Tabs */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 12px !important;
    box-shadow: 0 3px 12px rgba(30, 34, 82, 0.04) !important;
    padding: 9px 12px !important;
}
div[data-testid="stExpander"] {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 10px !important;
    box-shadow: 0 2px 8px rgba(30, 34, 82, 0.04) !important;
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    background: linear-gradient(90deg, #EFF6FF 0%, #E0E7FF 100%) !important;
    padding: 6px 12px !important;
    font-weight: 800 !important;
    color: #1E2252 !important;
    border-bottom: 1px solid #CBD5E1 !important;
}
div[data-testid="stExpander"] summary p,
div[data-testid="stExpander"] summary span,
div[data-testid="stExpander"] summary svg {
    color: #1E2252 !important;
    fill: #1E2252 !important;
    font-weight: 800 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 6px !important;
    background: #E2E8F0 !important;
    padding: 4px 5px !important;
    border-radius: 9px !important;
    border: 1px solid #CBD5E1 !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 7px !important;
    padding: 5px 12px !important;
    font-weight: 700 !important;
    color: #334155 !important;
    transition: all 0.14s ease !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"] p {
    color: #334155 !important;
    font-weight: 700 !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #DBEAFE 0%, #93C5FD 100%) !important;
    color: #111111 !important;
    border-color: #2563EB !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.18) !important;
}
div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] p {
    color: #111111 !important;
    font-weight: 800 !important;
}

/* ======================================================================
   UNIFIED TOP HEADER BAR — FULL SURFACE BUTTON CLICKABILITY
   ====================================================================== */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kulfi-top-cmd-bar-scope) {
    background: #FFFFFF !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 12px !important;
    padding: 8px 14px !important;
    margin-bottom: 8px !important;
    box-shadow: 0 3px 12px rgba(30, 34, 82, 0.06) !important;
    position: relative !important;
    z-index: 20 !important;
    overflow: visible !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kulfi-top-cmd-bar-scope) > div,
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kulfi-top-cmd-bar-scope) div[data-testid="stVerticalBlock"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kulfi-top-cmd-bar-scope) div[data-testid="stElementContainer"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kulfi-top-cmd-bar-scope) div[data-testid="stMarkdown"],
div[data-testid="stVerticalBlockBorderWrapper"]:has(.kulfi-top-cmd-bar-scope) div[data-testid="stMarkdownContainer"] {
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kulfi-top-cmd-bar-scope) {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    align-items: center !important;
    box-shadow: none !important;
    position: relative !important;
    z-index: 20 !important;
}
div[data-testid="stHorizontalBlock"]:has(.kulfi-top-cmd-bar-scope) > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"]:has(.kulfi-top-cmd-bar-scope) > div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    margin: 0 !important;
    padding-top: 0 !important;
    padding-bottom: 0 !important;
}
.kulfi-cmd-left {
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    flex-wrap: nowrap !important;
    margin: 0 !important;
    padding: 2px 2px !important;
    min-height: 40px !important;
    overflow: visible !important;
}
.kulfi-cmd-logo-sq {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: linear-gradient(145deg, #FFFFFF 0%, #F1F5F9 100%);
    border: 1.5px solid #CBD5E1;
    box-shadow: 0 2px 6px rgba(30, 34, 82, 0.10);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    flex-shrink: 0;
    padding: 1.5px;
}
.kulfi-cmd-logo-sq img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    border-radius: 6px;
    display: block;
}
.kulfi-cmd-crest {
    width: 36px;
    height: 36px;
    border-radius: 8px;
    background: linear-gradient(135deg, #1E2252 0%, #3B82F6 100%);
    border: 1.5px solid #1E2252;
    box-shadow: 0 2px 6px rgba(30, 34, 82, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    color: #FFFFFF;
    flex-shrink: 0;
    margin: 0 !important;
}
.kulfi-cmd-text {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    margin: 0 !important;
    padding: 0 !important;
}
.kulfi-cmd-title-row {
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}
.kulfi-cmd-title {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.98rem !important;
    font-weight: 800 !important;
    color: #111111 !important;
    letter-spacing: -0.01em;
    line-height: 1.1 !important;
    margin: 0 !important;
    padding: 0 !important;
    white-space: nowrap;
}
.kulfi-cmd-sub {
    font-size: 10px !important;
    font-weight: 700 !important;
    color: #475569 !important;
    letter-spacing: 0.01em;
    line-height: 1.15 !important;
    margin: 1px 0 0 0 !important;
    padding: 0 !important;
    display: flex;
    align-items: center;
    gap: 6px;
}
.kulfi-top-pill {
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
    padding: 0px 6px;
    border-radius: 999px;
    font-size: 9.5px;
    font-weight: 800;
}

/* Ensure all buttons and popovers across the top bar and entire app are clickable across their entire face */
[data-testid="stPopover"] {
    width: 100% !important;
}
.stButton > button,
[data-testid="stFormSubmitButton"] > button,
.stDownloadButton > button,
[data-testid="stLinkButton"] > a,
[data-testid="stPopover"] > div > button,
[data-testid="stPopoverButton"] {
    background: linear-gradient(180deg, #FFFFFF 0%, #F1F5F9 100%) !important;
    color: #111111 !important;
    border: 1.5px solid #CBD5E1 !important;
    border-radius: 5px !important;
    font-weight: 700 !important;
    font-size: 11.5px !important;
    min-height: 30px !important;
    height: 30px !important;
    padding: 3px 12px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    box-sizing: border-box !important;
    margin: 0 !important;
    text-decoration: none !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05) !important;
    transition: all 0.12s ease !important;
    cursor: pointer !important;
    pointer-events: auto !important;
    position: relative !important;
    z-index: 5 !important;
}
[data-testid="stPopover"] > div > button,
[data-testid="stPopoverButton"] {
    width: 100% !important;
}
/* Crucial: child text/icons inside buttons must not intercept pointer events */
.stButton > button *,
[data-testid="stFormSubmitButton"] > button *,
.stDownloadButton > button *,
[data-testid="stPopover"] > div > button *,
[data-testid="stPopoverButton"] * {
    pointer-events: none !important;
    color: #111111 !important;
    font-weight: 700 !important;
}
.stButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover,
.stDownloadButton > button:hover,
[data-testid="stLinkButton"] > a:hover,
[data-testid="stPopover"] > div > button:hover,
[data-testid="stPopoverButton"]:hover {
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%) !important;
    border-color: #2563EB !important;
    color: #111111 !important;
    transform: translateY(-1px) !important;
}

/* Primary Action & Submit Buttons — Smaller, Sharper, Non-Full-Width by Default */
.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button,
.stDownloadButton > button[kind="primary"],
[data-testid="baseButton-primary"] {
    background: linear-gradient(135deg, #93C5FD 0%, #60A5FA 100%) !important;
    color: #111111 !important;
    border: 1.5px solid #1D4ED8 !important;
    border-radius: 4px !important;
    min-height: 29px !important;
    height: 29px !important;
    padding: 2px 16px !important;
    font-size: 11.5px !important;
    letter-spacing: 0.01em !important;
    box-shadow: 0 1px 4px rgba(37, 99, 235, 0.16) !important;
}
/* Center entry submit buttons horizontally beneath the table & constrain width */
div[class*="st-key-submit_"] {
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
    width: 100% !important;
    margin-top: 3px !important;
}
[data-testid="stFormSubmitButton"],
div[class*="st-key-submit_"] .stButton,
div[class*="st-key-btn_save_"] .stButton,
div[class*="st-key-btn_upd_"] .stButton,
div[class*="st-key-btn_disburse_"] .stButton,
div[class*="st-key-confirm_cash_"] .stButton,
div[class*="st-key-cash_handover_button_"] .stButton,
div[class*="st-key-fa_create_order"] .stButton,
div[class*="st-key-update_audit_"] .stButton {
    width: auto !important;
    display: inline-flex !important;
    justify-content: center !important;
}
[data-testid="stFormSubmitButton"] > button,
div[class*="st-key-submit_"] .stButton > button,
div[class*="st-key-btn_save_"] .stButton > button,
div[class*="st-key-btn_upd_"] .stButton > button,
div[class*="st-key-btn_disburse_"] .stButton > button,
div[class*="st-key-confirm_cash_"] .stButton > button,
div[class*="st-key-cash_handover_button_"] .stButton > button,
div[class*="st-key-fa_create_order"] .stButton > button,
div[class*="st-key-update_audit_"] .stButton > button {
    width: auto !important;
    min-width: 155px !important;
    max-width: 240px !important;
    border-radius: 4px !important;
    min-height: 29px !important;
    height: 29px !important;
    padding: 2px 16px !important;
}
.stButton > button[kind="primary"] *,
[data-testid="stFormSubmitButton"] > button[kind="primary"] *,
[data-testid="stFormSubmitButton"] > button *,
.stDownloadButton > button[kind="primary"] * {
    color: #111111 !important;
    font-weight: 800 !important;
}

/* ======================================================================
   DEPOSITO LEFT-HAND VERTICAL NAVIGATION PANE (ALL ADMIN PAGES)
   ====================================================================== */
/* Keep outer 2-column master layout top-aligned on EVERY page (prevents vertical shift on tall tables) */
div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-deposito_dock_btn_"]) {
    align-items: flex-start !important;
}
div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-deposito_dock_btn_"]) > div[data-testid="stColumn"]:first-child,
div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-deposito_dock_btn_"]) > div[data-testid="column"]:first-child {
    align-self: flex-start !important;
    justify-content: flex-start !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-deposito_dock_btn_"]) {
    background: linear-gradient(180deg, #F8FAFC 0%, #EFF6FF 55%, #E0E7FF 100%) !important;
    border: 1.5px solid #BFDBFE !important;
    border-radius: 14px !important;
    padding: 10px 10px !important;
    box-shadow: 0 6px 18px rgba(30, 34, 82, 0.07) !important;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(div[class*="st-key-deposito_dock_btn_"]) div[data-testid="stVerticalBlock"] {
    gap: 0.28rem !important;
}

/* Compact single-row Daily Entry top mode buttons */
div[class*="st-key-de_top_mode_"] {
    margin: 0 !important;
    padding: 0 !important;
}
div[class*="st-key-de_top_mode_"] > div > button,
div[class*="st-key-de_top_mode_"] button {
    min-height: 31px !important;
    height: 31px !important;
    padding: 2px 8px !important;
    border-radius: 7px !important;
    font-size: 11.5px !important;
    font-weight: 800 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
div[class*="st-key-de_top_mode_"] button * {
    font-size: 11.5px !important;
    font-weight: 800 !important;
    white-space: nowrap !important;
}
div[class*="st-key-de_top_mode_staging_sales"] button[kind="secondary"] {
    background: linear-gradient(180deg, #FFFBEB 0%, #FEF3C7 100%) !important;
    border-color: #F59E0B !important;
}
div[class*="st-key-de_top_mode_staging_restock"] button[kind="secondary"] {
    background: linear-gradient(180deg, #ECFDF5 0%, #D1FAE5 100%) !important;
    border-color: #10B981 !important;
}
div[class*="st-key-deposito_dock_btn_"] {
    margin-bottom: 0 !important;
}
div[class*="st-key-deposito_dock_btn_"] > div > button,
div[class*="st-key-deposito_dock_btn_"] button {
    background: #FFFFFF !important;
    border: 1px solid #CBD5E1 !important;
    border-radius: 9px !important;
    min-height: 36px !important;
    height: 36px !important;
    padding: 4px 10px !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    text-align: left !important;
    color: #0F172A !important;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04) !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    line-height: 1.2 !important;
    transition: all 0.14s ease !important;
}
div[class*="st-key-deposito_dock_btn_"] button * {
    color: #0F172A !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    line-height: 1.2 !important;
    text-align: left !important;
}
div[class*="st-key-deposito_dock_btn_"] button:hover {
    background: #DBEAFE !important;
    border-color: #2563EB !important;
    transform: translateX(2px) !important;
}
div[class*="st-key-deposito_dock_btn_"] button[kind="primary"] {
    background: linear-gradient(135deg, #FDE68A 0%, #FBBF24 100%) !important;
    border: 1.5px solid #D97706 !important;
    color: #111111 !important;
    box-shadow: 0 2px 6px rgba(217, 119, 6, 0.22) !important;
}
div[class*="st-key-deposito_dock_btn_"] button[kind="primary"] * {
    color: #111111 !important;
    font-weight: 800 !important;
}

/* ======================================================================
   DEPOSITO LANDING PAGE STACKED CARDS & WIDGETS
   ====================================================================== */
.deposito-kpi-strip {
    display: grid;
    grid-template-columns: 0.92fr 1.12fr 1.42fr 1.52fr 1.28fr;
    gap: 10px;
    margin-bottom: 12px !important;
}
@media (max-width: 1100px) {
    .deposito-kpi-strip {
        grid-template-columns: repeat(2, 1fr);
    }
}
.dep-kpi-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 8px 11px;
    box-shadow: 0 2px 8px rgba(30, 34, 82, 0.04);
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 62px;
}
.dep-kpi-dual {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    align-items: center;
}
.dep-kpi-dual > div:first-child {
    border-right: 1px solid #E2E8F0;
    padding-right: 6px;
}
.dep-kpi-dual > div:last-child {
    padding-left: 4px;
}
.dep-kpi-num {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1.04rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.12;
    white-space: nowrap;
}
.dep-kpi-lbl {
    font-size: 9.8px;
    font-weight: 700;
    color: #64748B;
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.dep-time-pill {
    display: inline-block;
    background: #DBEAFE;
    color: #1D4ED8;
    font-size: 10px;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 6px;
    margin-top: 3px;
    text-align: center;
}

/* Emerald Green Capacity Utilization Card */
.dep-emerald-card {
    background: linear-gradient(160deg, #059669 0%, #047857 60%, #065F46 100%);
    border-radius: 14px;
    padding: 12px 14px 10px 14px;
    color: #FFFFFF;
    box-shadow: 0 6px 16px rgba(4, 120, 87, 0.18);
    position: relative;
    min-height: 256px;
    height: auto;
    margin-bottom: 10px !important;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}
.dep-emerald-hdr {
    text-align: right;
    font-size: 11.5px;
    font-weight: 800;
    color: #ECFDF5;
}
.dep-emerald-float-strip {
    position: absolute;
    left: 0;
    top: 48%;
    transform: translateY(-50%);
    background: #FFFFFF;
    border-radius: 0 7px 7px 0;
    padding: 4px 4px;
    display: flex;
    flex-direction: column;
    gap: 4px;
    box-shadow: 2px 3px 8px rgba(0, 0, 0, 0.14);
}
.dep-emerald-float-dot {
    width: 15px;
    height: 15px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
}
.dep-emerald-footer {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 6px;
    border-top: 1px solid rgba(255, 255, 255, 0.18);
    padding-top: 7px;
    text-align: center;
}
.dep-emerald-ft-lbl {
    font-size: 9.5px;
    color: #A7F3D0;
    font-weight: 700;
}
.dep-emerald-ft-val {
    font-size: 11.5px;
    color: #FFFFFF;
    font-weight: 800;
    margin-top: 1px;
}

/* White "Last 7 day sales" Center Matrix Card */
.dep-matrix-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 11px 14px 10px 14px;
    box-shadow: 0 3px 12px rgba(30, 34, 82, 0.04);
    min-height: 256px;
    height: auto;
    margin-bottom: 10px !important;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}
.dep-matrix-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #F1F5F9;
    padding-bottom: 5px;
    margin-bottom: 6px;
}
.dep-date-badge {
    background: #F1F5F9;
    color: #334155;
    font-size: 10px;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid #E2E8F0;
}

/* Column-based 7-Day Sales Matrix so the Latest Day Column has a single continuous border */
.dep-sales7-grid {
    display: grid;
    grid-template-columns: 142px repeat(7, minmax(0, 1fr));
    gap: 6px;
    align-items: stretch;
}
.dep-sales7-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 3px;
    border-radius: 8px;
    border: 1.5px solid transparent;
}
/* Border around the latest sale day column */
.dep-sales7-col.latest-day-col {
    border: 2px solid #1E2252 !important;
    background: rgba(37, 99, 235, 0.04) !important;
    box-shadow: 0 2px 8px rgba(30, 34, 82, 0.10) !important;
}
.dep-sales7-lbl-cell {
    height: 24px;
    display: flex;
    align-items: center;
    font-size: 10px;
    font-weight: 800;
    color: #1E2252;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    padding-left: 2px;
}
/* Darker Date Header Row */
.dep-sales7-hdr-cell {
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    font-weight: 800;
    color: #FFFFFF;
    background: #334155;
    border: 1px solid #1E293B;
    border-radius: 5px;
    white-space: nowrap;
}
.dep-sales7-col.latest-day-col .dep-sales7-hdr-cell {
    background: #1E2252;
    border-color: #1E2252;
}
.dep-sales7-tile {
    height: 24px;
    border-radius: 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 10.2px;
    font-weight: 800;
    white-space: nowrap;
    padding: 0 3px;
}
/* Lighter Total Row in Emerald Theme */
.dep-sales7-tile.total-row {
    background: #ECFDF5;
    color: #065F46;
    border: 1px solid #A7F3D0;
    font-weight: 900;
}
/* Uniform Lighter Shade for All Cart Sales Rows */
.dep-sales7-tile.cart-row {
    background: #FEF9C3;
    color: #1E293B;
    border: 1px solid #FDE68A;
    font-weight: 700;
}
.dep-sales7-tile.cart-zero {
    background: #F8FAFC;
    color: #94A3B8;
    border: 1px dashed #E2E8F0;
    font-weight: 600;
}
/* Lighter PhonePe & Cash Split Rows */
.dep-sales7-tile.phonepe-row {
    background: #F5F3FF;
    color: #4C1D95;
    border: 1px solid #DDD6FE;
    font-weight: 700;
}
.dep-sales7-tile.cash-row {
    background: #F0F9FF;
    color: #1E3A8A;
    border: 1px solid #BAE6FD;
    font-weight: 700;
}

/* Bottom 3 Analytical Cards */
.dep-bottom-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
    padding: 10px 13px;
    box-shadow: 0 3px 12px rgba(30, 34, 82, 0.04);
    min-height: 176px;
    height: auto;
    margin-bottom: 10px !important;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}
.dep-bottom-hdr {
    font-size: 11.5px;
    font-weight: 800;
    color: #1E2252;
    text-align: right;
    border-bottom: 1px solid #F1F5F9;
    padding-bottom: 4px;
    margin-bottom: 6px;
}

/* Crisp Finance Performance Card Grid (Zero Sub-Text) */
.dep-fin-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 5px;
}
.dep-fin-item {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 3px solid #3B82F6;
    border-radius: 7px;
    padding: 4px 8px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
.dep-fin-lbl {
    font-size: 9.8px;
    font-weight: 700;
    color: #475569;
    white-space: nowrap;
}
.dep-fin-val {
    font-size: 10.2px;
    font-weight: 800;
    color: #0F172A;
    white-space: nowrap;
}
.dep-fin-net-bar {
    margin-top: 5px;
    background: linear-gradient(90deg, #ECFDF5 0%, #D1FAE5 100%);
    border: 1px solid #6EE7B7;
    border-left: 3.5px solid #059669;
    border-radius: 7px;
    padding: 5px 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* ======================================================================
   LAUNCHPAD SECTION HEADERS & QUICK ENTRY PANEL BUTTONS
   ====================================================================== */
.launchpad-section-hdr {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 10px !important;
    font-weight: 800 !important;
    color: #1E2252 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin: 0 0 4px 0 !important;
    padding: 2px 8px;
    background: linear-gradient(90deg, #EFF6FF 0%, #F8FAFC 100%);
    border-left: 3.5px solid #3B82F6;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 6px;
}
div[data-testid="stElementContainer"]:has(.kulfi-clickable-card-grid),
div[data-testid="stElementContainer"]:has(.kulfi-card-set-1),
div[data-testid="stElementContainer"]:has(.kulfi-card-set-2),
div[data-testid="stElementContainer"]:has(.kulfi-card-set-3),
div[data-testid="stElementContainer"]:has(.kulfi-card-set-4) {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stVerticalBlock"]:has(.kulfi-clickable-card-grid):not(:has(.kulfi-top-cmd-bar-scope)):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stButton > button,
div[data-testid="stHorizontalBlock"]:has(.kulfi-clickable-card-grid):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stButton > button {
    background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%) !important;
    border: 1.5px solid #CBD5E1 !important;
    border-left: 4px solid #3B82F6 !important;
    border-radius: 9px !important;
    padding: 5px 10px !important;
    min-height: 36px !important;
    height: 36px !important;
    width: 100% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    text-align: left !important;
    white-space: nowrap !important;
    box-shadow: 0 1px 4px rgba(30, 34, 82, 0.05) !important;
}

/* Compact 30px inline action buttons (Edit, Copy, Delete) inside .ledger-cell table rows */
div[data-testid="stHorizontalBlock"]:has(.ledger-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stButton,
div[data-testid="stHorizontalBlock"]:has(.ledger-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) [data-testid="stTooltipHoverTarget"] {
    width: 100% !important;
    display: flex !important;
    justify-content: center !important;
}
div[data-testid="stHorizontalBlock"]:has(.ledger-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stButton > button,
div[class*="st-key-row_edit_"] button,
div[class*="st-key-row_clone_"] button,
div[class*="st-key-row_del_"] button {
    padding: 0 2px !important;
    min-width: 28px !important;
    width: 100% !important;
    min-height: 30px !important;
    height: 30px !important;
    font-size: 13px !important;
    line-height: 1 !important;
    border-radius: 6px !important;
    border: 1px solid #93C5FD !important;
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%) !important;
    color: #111111 !important;
}
div[class*="st-key-row_clone_"] button {
    background: linear-gradient(180deg, #F8FAFC 0%, #E2E8F0 100%) !important;
    border-color: #CBD5E1 !important;
}
div[class*="st-key-row_del_"] button {
    background: linear-gradient(180deg, #FEF2F2 0%, #FECACA 100%) !important;
    border-color: #FCA5A5 !important;
}

/* ======================================================================
   80% PAGE WIDTH & SINGLE-PAGE NO-SCROLL COMPACT SCOPE FOR ENTRY SCREENS
   ====================================================================== */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) {
    width: 80% !important;
    max-width: 980px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    gap: 0.18rem !important;
}
div[data-testid="stColumn"] div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope),
div[data-testid="column"] div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) {
    width: 100% !important;
    max-width: 100% !important;
    margin-left: 0 !important;
    margin-right: 0 !important;
}
@media (max-width: 992px) {
    div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) {
        width: 98% !important;
        max-width: 98% !important;
    }
}
div[data-testid="stElementContainer"]:has(.kulfi-entry-80-scope) {
    display: none !important;
    height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stVerticalBlock"] {
    gap: 0.18rem !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stVerticalBlockBorderWrapper"] {
    padding: 6px 10px !important;
    border-radius: 9px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stMetric"] {
    padding: 4px 8px !important;
    min-height: 44px !important;
    border-radius: 8px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stMetricValue"] {
    font-size: 0.96rem !important;
    margin-top: 0px !important;
}

/* Section Headers for Sales & Restock (Compact 28px Single-Page Fit) */
.header-box-sales {
    background: linear-gradient(90deg, #1E2252 0%, #2D337A 100%);
    color: #FFFFFF !important;
    border: 1px solid #1E2252;
    border-radius: 7px;
    padding: 4px 11px;
    min-height: 28px;
    font-weight: 800;
    font-size: 12px;
    margin-bottom: 3px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 6px rgba(30, 34, 82, 0.12);
}
.header-box-sales span, .header-box-sales b {
    color: #FFFFFF !important;
}
.header-box-restock {
    background: linear-gradient(90deg, #059669 0%, #047857 100%);
    color: #FFFFFF !important;
    border: 1px solid #047857;
    border-radius: 7px;
    padding: 4px 11px;
    min-height: 28px;
    font-weight: 800;
    font-size: 12px;
    margin-bottom: 3px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 2px 6px rgba(5, 150, 105, 0.12);
}
.header-box-restock span, .header-box-restock b {
    color: #FFFFFF !important;
}

/* Compact Flavor Card Grid */
.flavor-entry-row {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 3px 6px;
    margin-bottom: 3px;
}
.flavor-title-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1px;
}
.flavor-name {
    font-weight: 800;
    font-size: 11.5px;
    color: #1E2252;
}
.badge-open {
    background: #F1F5F9;
    color: #1E2252;
    border: 1px solid #CBD5E1;
    font-weight: 800;
    font-size: 10.5px;
    padding: 1px 5px;
    border-radius: 5px;
}
.badge-sold {
    background: #FEF2F2;
    color: #991B1B;
    font-weight: 800;
    font-size: 10.5px;
    padding: 1px 5px;
    border-radius: 5px;
}
.badge-today-open {
    background: #ECFDF5;
    color: #065F46;
    font-weight: 800;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 5px;
    border: 1px solid #6EE7B7;
    display: inline-block;
}

/* Consistent Compact Input Heights & Slate-Blue Borders (Targeting data-testid for Streamlit 1.38+) */
.stSelectbox div[data-baseweb="select"] > div,
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
.stDateInput div[data-baseweb="input"],
div[data-testid="stDateInput"] div[data-baseweb="input"],
div[data-testid="stDateInput"] div[data-baseweb="base-input"],
.stTimeInput div[data-baseweb="input"],
div[data-testid="stTimeInput"] div[data-baseweb="input"],
div[data-testid="stTimeInput"] div[data-baseweb="base-input"],
.stTextInput div[data-baseweb="input"],
div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stTextInput"] div[data-baseweb="base-input"],
.stNumberInput div[data-baseweb="input"],
div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[data-testid="stNumberInputContainer"] {
    min-height: 32px !important;
    height: 32px !important;
    max-height: 32px !important;
    border-radius: 5px !important;
    background-color: #FFFFFF !important;
    border: 1.5px solid #CBD5E1 !important;
    box-sizing: border-box !important;
    align-items: center !important;
}
/* Prevent double border on nested base-input inside input */
div[data-testid="stTextInput"] div[data-baseweb="input"] > div[data-baseweb="base-input"],
div[data-testid="stDateInput"] div[data-baseweb="input"] > div[data-baseweb="base-input"],
div[data-testid="stTimeInput"] div[data-baseweb="input"] > div[data-baseweb="base-input"],
div[data-testid="stNumberInput"] div[data-baseweb="input"] > div[data-baseweb="base-input"] {
    border: none !important;
    background: transparent !important;
    min-height: 30px !important;
    height: 30px !important;
    max-height: 30px !important;
}
.stTextInput input, .stNumberInput input, .stDateInput input, .stTimeInput input,
div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stTimeInput"] input {
    padding: 0px 8px !important;
    font-size: 11.5px !important;
    text-align: left !important;
    font-weight: 700 !important;
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    height: 30px !important;
    min-height: 30px !important;
    line-height: 30px !important;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    padding-top: 0px !important;
    padding-bottom: 0px !important;
    font-size: 11.5px !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}
.stNumberInput label, .stTextInput label, .stSelectbox label, .stDateInput label, .stTimeInput label,
div[data-testid="stNumberInput"] label[data-testid="stWidgetLabel"],
div[data-testid="stTextInput"] label[data-testid="stWidgetLabel"],
div[data-testid="stSelectbox"] label[data-testid="stWidgetLabel"],
div[data-testid="stDateInput"] label[data-testid="stWidgetLabel"],
div[data-testid="stTimeInput"] label[data-testid="stWidgetLabel"] {
    font-size: 10.5px !important;
    font-weight: 700 !important;
    min-height: 16px !important;
    height: auto !important;
    margin-bottom: 3px !important;
    line-height: 1.25 !important;
    overflow: visible !important;
    text-align: left !important;
    color: #334155 !important;
}

/* Top Row of Entry Screens (Scoped to Entry Screens): Match exact 32px control height & bottom baseline */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) {
    align-items: flex-end !important;
    margin-top: 2px !important;
    margin-bottom: 4px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) > div[data-testid="stColumn"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) > div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: flex-end !important;
    margin: 0px !important;
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) div[data-testid="stSelectbox"] div[data-baseweb="select"] > div > div {
    min-height: 32px !important;
    height: 32px !important;
    max-height: 32px !important;
    display: flex !important;
    align-items: center !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) div[data-testid="stTextInput"] div[data-baseweb="base-input"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) div[data-testid="stDateInput"] div[data-baseweb="input"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(div[class*="st-key-back_to_entry_menu_"]) div[data-testid="stDateInput"] div[data-baseweb="base-input"] {
    min-height: 32px !important;
    height: 32px !important;
    max-height: 32px !important;
}
div[class*="st-key-back_to_entry_menu_"],
div[class*="st-key-refresh_rm_cart_"],
div[class*="st-key-btn_fzr_mode_"] {
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding: 0px !important;
    width: 100% !important;
}
div[class*="st-key-back_to_entry_menu_"] .stButton,
div[class*="st-key-back_to_entry_menu_"] .stButton > button,
div[class*="st-key-refresh_rm_cart_"] .stButton,
div[class*="st-key-refresh_rm_cart_"] .stButton > button,
div[class*="st-key-btn_fzr_mode_"] .stButton,
div[class*="st-key-btn_fzr_mode_"] .stButton > button {
    height: 32px !important;
    min-height: 32px !important;
    max-height: 32px !important;
    width: 100% !important;
    margin: 0px !important;
    padding: 0 10px !important;
    border-radius: 5px !important;
    font-size: 11.5px !important;
    font-weight: 800 !important;
    box-sizing: border-box !important;
}

/* Disabled Leakage Unexplained Text Input Styling (Matches sibling inputs 100% in height & alignment) */
div[class*="st-key-daily_leak_unexp_ro"] div[data-baseweb="input"] {
    background-color: #F8FAFC !important;
    border: 1.5px solid #CBD5E1 !important;
    opacity: 1 !important;
}
div[class*="st-key-daily_leak_unexp_ro"] input {
    color: #0F172A !important;
    -webkit-text-fill-color: #0F172A !important;
    font-weight: 800 !important;
    opacity: 1 !important;
}
div[class*="st-key-daily_leak_unexp_alert"] div[data-baseweb="input"] {
    background-color: #FFF0ED !important;
    border: 1.5px solid #FCA5A5 !important;
    opacity: 1 !important;
}
div[class*="st-key-daily_leak_unexp_alert"] input {
    color: #C41C1C !important;
    -webkit-text-fill-color: #C41C1C !important;
    font-weight: 800 !important;
    opacity: 1 !important;
}

/* Hide "Press Enter to apply" instructions so number inputs never shift or expand */
div[data-testid="InputInstructions"] {
    display: none !important;
    height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
}

/* Completely collapse hidden widget labels inside entry-grid rows (preserving checkbox labels) */
label[data-testid="stWidgetLabel"][aria-hidden="true"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) label[data-testid="stWidgetLabel"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) [data-testid="stWidgetLabel"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) label[data-testid="stWidgetLabel"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) [data-testid="stWidgetLabel"] {
    display: none !important;
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    margin: 0px !important;
    padding: 0px !important;
    border: none !important;
    overflow: hidden !important;
}

/* Eliminate Streamlit's default -1rem bottom margin on stMarkdownContainer inside entry grids so markdown cells and number inputs align on the exact same horizontal axis */
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdown"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdown"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdown"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdown"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stVerticalBlock"] {
    margin: 0px !important;
    margin-top: 0px !important;
    margin-bottom: 0px !important;
    padding: 0px !important;
    width: 100% !important;
    max-width: 100% !important;
    line-height: 1 !important;
}

/* Force all columns inside entry-grid header, flavour rows, and total rows to align on the exact same horizontal axis & match column widths 100% */
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) {
    align-items: center !important;
    gap: 6px !important;
    margin-top: 0px !important;
    margin-bottom: 2px !important;
}
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])),
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) {
    align-items: center !important;
    gap: 6px !important;
    margin-top: 0px !important;
    margin-bottom: 1px !important;
}
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) {
    align-items: center !important;
    gap: 6px !important;
    margin-top: 2px !important;
    margin-bottom: 4px !important;
}
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="column"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="stColumn"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-total-row):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) > div[data-testid="column"] {
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: stretch !important;
    margin: 0px !important;
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}

/* Ensure stNumberInput and its element-container wrappers inside entry-grid rows span 100% of their column width */
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="element-container"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .element-container,
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="element-container"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .element-container,
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stElementContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stNumberInput,
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stNumberInput {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
    align-self: stretch !important;
    margin: 0px !important;
    padding: 0px !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: flex !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInputContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"] div[data-baseweb="base-input"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stNumberInput div[data-baseweb="input"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInputContainer"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"] div[data-baseweb="input"],
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"] div[data-baseweb="base-input"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    flex: 1 1 100% !important;
    min-height: 28px !important;
    height: 28px !important;
    max-height: 28px !important;
    border-radius: 5px !important;
    margin: 0px !important;
    padding: 0px !important;
    box-sizing: border-box !important;
    display: flex !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"] input,
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stNumberInput input,
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stNumberInput"] input,
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) .stNumberInput input {
    width: 100% !important;
    max-width: 100% !important;
    flex: 1 1 100% !important;
    height: 26px !important;
    min-height: 26px !important;
    line-height: 26px !important;
    padding: 0 6px !important;
    margin: 0px !important;
    text-align: center !important;
    font-size: 11.5px !important;
    font-weight: 800 !important;
}

/* Entry-grid text inputs (used for Restock, Extra Stock, Remove Cart Stock, Freezer Sale): 100% column width, 28px height, centered */
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    margin: 0px !important;
    padding: 0px !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] div[data-baseweb="input"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] div[data-baseweb="input"] {
    width: 100% !important;
    min-height: 28px !important;
    height: 28px !important;
    max-height: 28px !important;
    border-radius: 5px !important;
    border: 1.5px solid #93C5FD !important;
    background-color: #FFFFFF !important;
    margin: 0px !important;
    padding: 0px !important;
    box-sizing: border-box !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] div[data-baseweb="base-input"],
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] div[data-baseweb="base-input"] {
    width: 100% !important;
    min-height: 26px !important;
    height: 26px !important;
    max-height: 26px !important;
    border: none !important;
    background: transparent !important;
    margin: 0px !important;
    padding: 0px !important;
}
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] input,
div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] .kulfi-entry-80-scope) div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stTextInput"] input {
    width: 100% !important;
    height: 26px !important;
    min-height: 26px !important;
    max-height: 26px !important;
    line-height: 26px !important;
    padding: 0 6px !important;
    margin: 0px !important;
    text-align: center !important;
    font-size: 11.5px !important;
    font-weight: 800 !important;
}

/* Center checkboxes cleanly inside Bulk Orders entry-grid rows */
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stCheckbox"] {
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    margin: 0px !important;
    padding: 0px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}
div[data-testid="stHorizontalBlock"]:has(.entry-grid-cell-flavour):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stCheckbox"] label {
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    margin: 0px !important;
    padding: 0px !important;
}

/* Metric Cards — Crisp White with Indigo/Blue Top Accent */
div[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-top: 3.5px solid #3B82F6 !important;
    border-radius: 12px !important;
    padding: 9px 11px !important;
    box-shadow: 0 3px 10px rgba(30, 34, 82, 0.04) !important;
    height: 100%;
}
div[data-testid="stMetricLabel"], 
div[data-testid="stMetricLabel"] > div, 
div[data-testid="stMetricLabel"] label,
div[data-testid="stMetricLabel"] p, 
div[data-testid="stMetricLabel"] span { 
    font-weight: 700 !important; 
    font-size: 11px !important; 
    color: #64748B !important; 
    white-space: normal !important; 
    word-wrap: break-word !important; 
    overflow: visible !important; 
    text-overflow: clip !important; 
    line-height: 1.3 !important;
}
div[data-testid="stMetricLabel"] {
    height: auto !important;
    min-height: 22px;
}
div[data-testid="stMetricValue"] { 
    font-family: 'Plus Jakarta Sans', sans-serif; 
    font-size: 1.15rem !important; 
    font-weight: 800 !important;
    color: #1E2252 !important; 
    margin-top: 2px;
}

/* Data Grids & Tables Across the Entire App */
div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {
    border-radius: 11px !important;
    border: 1px solid #CBD5E1 !important;
    background: #FFFFFF !important;
    box-shadow: 0 3px 10px rgba(30, 34, 82, 0.05) !important;
    overflow: hidden;
}
div[data-testid="stDataFrame"] th, div[data-testid="stDataEditor"] th {
    font-weight: 800 !important;
    color: #1E2252 !important;
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%) !important;
    border-bottom: 1.5px solid #93C5FD !important;
    text-align: center !important;
    font-size: 12px !important;
}
div[data-testid="stDataFrame"] td, div[data-testid="stDataEditor"] td {
    text-align: center !important;
    font-size: 11.5px !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}
.stMarkdown table {
    width: 100%;
    border-collapse: separate !important;
    border-spacing: 0 !important;
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 11px;
    overflow: hidden;
    box-shadow: 0 3px 10px rgba(30, 34, 82, 0.05);
    margin: 6px 0 12px 0;
}
.stMarkdown table th {
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%) !important;
    color: #1E2252 !important;
    font-weight: 800 !important;
    padding: 8px 10px !important;
    border-bottom: 1.5px solid #93C5FD !important;
    border-right: 1px solid #E2E8F0 !important;
    font-size: 11.5px !important;
}
.stMarkdown table td {
    padding: 7px 10px !important;
    border-bottom: 1px solid #F1F5F9 !important;
    border-right: 1px solid #F1F5F9 !important;
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #0F172A !important;
}
.stMarkdown table tr:nth-child(even) td {
    background: #F8FAFC !important;
}
.stMarkdown table tr:hover td {
    background: #EFF6FF !important;
}

hr { border-color: #CBD5E1 !important; opacity: 0.65 !important; margin: 0.35rem 0 !important; }

div[data-testid="stNumberInput"] div[data-baseweb="input"] {
    border: 1.5px solid #93C5FD !important;
    background-color: #FFFFFF !important;
    border-radius: 6px !important;
}
div[data-testid="stNumberInput"] div[data-baseweb="input"]:focus-within {
    border: 2px solid #2563EB !important;
    background-color: #EFF6FF !important;
}
div[data-testid="stNumberInput"] input {
    text-align: left !important;
    font-weight: 800 !important;
    color: #0F172A !important;
    padding-left: 8px !important;
}

/* Daily Entry & Stock Grid Cells — Matched 28px Compact Single-Page Height & 100% Width */
.entry-grid-header {
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%);
    color: #1E2252 !important;
    border: 1px solid #93C5FD;
    border-bottom: 1.5px solid #60A5FA;
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    padding: 0 8px !important;
    border-radius: 5px;
    font-size: 11px;
    font-weight: 800;
    text-align: center;
    display: flex !important;
    align-items: center !important;
    justify-content: center;
    box-sizing: border-box !important;
    margin: 0 !important;
    white-space: nowrap;
}
.entry-grid-header[style*="text-align:left"] {
    justify-content: flex-start !important;
}
.entry-grid-header[style*="text-align:right"] {
    justify-content: flex-end !important;
}
.entry-grid-cell {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center;
    font-size: 11.5px;
    font-weight: 800;
    color: #0F172A;
    box-sizing: border-box !important;
    margin: 0 !important;
}
.entry-grid-cell-flavour {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-left: 3.5px solid #3B82F6;
    border-radius: 5px;
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between;
    padding: 0 8px !important;
    font-size: 11.5px;
    font-weight: 800;
    color: #1E2252;
    box-sizing: border-box !important;
    margin: 0 !important;
}
.entry-grid-cell-sold {
    background: #FEF3C7;
    border: 1px solid #FCD34D;
    border-radius: 5px;
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center;
    font-size: 11.5px;
    font-weight: 900;
    color: #92400E;
    box-sizing: border-box !important;
    margin: 0 !important;
}
.entry-grid-cell-amount {
    background: #ECFDF5;
    border: 1px solid #6EE7B7;
    border-radius: 5px;
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-end;
    padding: 0 8px !important;
    font-size: 11.5px;
    font-weight: 900;
    color: #065F46;
    box-sizing: border-box !important;
    margin: 0 !important;
}
.entry-grid-cell-amount[style*="justify-content:center"],
.entry-grid-cell-amount[style*="text-align:center"] {
    justify-content: center !important;
}
.entry-grid-total-row {
    background: linear-gradient(90deg, #EFF6FF 0%, #E0E7FF 100%);
    border: 1.5px solid #93C5FD;
    border-radius: 6px;
    width: 100% !important;
    height: 30px !important;
    min-height: 30px !important;
    max-height: 30px !important;
    padding: 0 8px !important;
    margin: 0 !important;
    font-size: 11.5px;
    font-weight: 900;
    color: #1E2252;
    display: flex !important;
    align-items: center !important;
    justify-content: center;
    box-sizing: border-box !important;
}
.entry-grid-total-row[style*="text-align:left"] {
    justify-content: flex-start !important;
}
.entry-grid-total-row[style*="text-align:right"] {
    justify-content: flex-end !important;
}

/* Compact No-Scroll Ledger Rows for Expenses & Payments */
div[data-testid="stHorizontalBlock"]:has(.ledger-tbl-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) {
    margin-bottom: 10px !important;
    padding-bottom: 2px !important;
    align-items: center !important;
}
div[data-testid="stHorizontalBlock"]:has(.ledger-tbl-header):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdownContainer"],
div[data-testid="stHorizontalBlock"]:has(.ledger-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) div[data-testid="stMarkdownContainer"] {
    margin-bottom: 0px !important;
}
div[data-testid="stHorizontalBlock"]:has(.ledger-cell):not(:has(div[data-testid="stHorizontalBlock"])):not(:has(div[class*="st-key-deposito_dock_btn_"])) {
    margin-bottom: 3px !important;
    align-items: center !important;
}
.ledger-tbl-header {
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%);
    color: #1E2252 !important;
    border: 1px solid #93C5FD;
    border-bottom: 1.5px solid #60A5FA;
    padding: 5px 6px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    margin-bottom: 0px;
    display: flex;
    align-items: center;
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: ellipsis;
    min-height: 28px;
}
.ledger-cell {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    min-height: 30px;
    height: 30px;
    padding: 2px 6px;
    display: flex;
    align-items: center;
    font-size: 10.5px;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.15;
    white-space: nowrap !important;
    overflow: hidden;
    text-overflow: ellipsis;
}
.ledger-cell-desc {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-left: 3px solid #3B82F6;
    border-radius: 5px;
    min-height: 30px;
    height: 30px;
    padding: 2px 7px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    font-size: 10.5px;
    font-weight: 700;
    color: #0F172A;
    line-height: 1.12;
    overflow: hidden;
}
.ledger-cell-desc > span {
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    display: block;
    width: 100%;
}
.ledger-subtext {
    font-size: 9px;
    font-weight: 800;
    color: #4F46E5;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}
.ledger-amt-total {
    background: #F8FAFC;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    min-height: 30px;
    height: 30px;
    padding: 2px 6px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    font-size: 10.5px;
    font-weight: 800;
    color: #1E2252;
    white-space: nowrap !important;
}
.ledger-amt-paid {
    background: #ECFDF5;
    border: 1px solid #6EE7B7;
    border-radius: 5px;
    min-height: 30px;
    height: 30px;
    padding: 2px 6px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    font-size: 10.5px;
    font-weight: 800;
    color: #065F46;
    white-space: nowrap !important;
}
.ledger-amt-due {
    background: #FEF2F2;
    border: 1px solid #FCA5A5;
    border-radius: 5px;
    min-height: 30px;
    height: 30px;
    padding: 2px 6px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    font-size: 10.5px;
    font-weight: 800;
    color: #991B1B;
    white-space: nowrap !important;
}
.status-pill {
    padding: 1px 6px;
    border-radius: 999px;
    font-size: 9.5px;
    font-weight: 800;
    display: inline-block;
    text-align: center;
    white-space: nowrap !important;
}
.status-paid { background: #ECFDF5; color: #065F46; border: 1px solid #6EE7B7; }
.status-partial { background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }
.status-pending { background: #FEF2F2; color: #991B1B; border: 1px solid #FCA5A5; }
.status-other { background: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; }

/* Freezer Analysis Boxed Table Styling */
.fa-boxed-table-wrap {
    width: 100%;
    overflow-x: auto;
    margin: 8px 0 14px 0;
}
.fa-boxed-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    background: #FFFFFF;
    border: 1.5px solid #CBD5E1;
    border-radius: 12px;
    overflow: hidden;
    font-size: 12.5px;
    box-shadow: 0 4px 12px rgba(30, 34, 82, 0.06);
}
.fa-boxed-table th {
    background: linear-gradient(180deg, #EFF6FF 0%, #DBEAFE 100%);
    color: #1E2252 !important;
    font-weight: 800;
    padding: 9px 14px !important;
    text-align: center;
    font-size: 11.5px;
    letter-spacing: 0.02em;
    border-bottom: 1.5px solid #93C5FD;
    border-right: 1px solid #E2E8F0;
}
.fa-boxed-table td {
    padding: 9px 14px !important;
    border-bottom: 1px solid #F1F5F9;
    border-right: 1px solid #F1F5F9;
    text-align: center;
    font-weight: 700;
    color: #0F172A;
}
.fa-boxed-table tr:nth-child(even) td {
    background: #F8FAFC;
}
.fa-boxed-table tr:hover td {
    background: #EFF6FF;
}
.fa-boxed-table tr.fa-total-row td {
    background: linear-gradient(90deg, #DBEAFE 0%, #E0E7FF 100%) !important;
    border-top: 2px solid #3B82F6 !important;
    border-bottom: none !important;
    font-weight: 900 !important;
    color: #1E2252 !important;
    font-size: 13px;
}
.fa-box-audit-th { border-left: 2px solid #6366F1 !important; border-right: 2px solid #6366F1 !important; border-top: 2px solid #6366F1 !important; background: #E0E7FF !important; color: #1E2252 !important; }
.fa-box-audit-td { border-left: 1.5px solid #818CF8 !important; border-right: 1.5px solid #818CF8 !important; background: #F8FAFC !important; }
.fa-box-audit-tot { border-left: 2px solid #6366F1 !important; border-right: 2px solid #6366F1 !important; border-bottom: 2px solid #6366F1 !important; }

.fa-box-in-left-th { border-left: 2px solid #10B981 !important; border-top: 2px solid #10B981 !important; background: #D1FAE5 !important; color: #065F46 !important; }
.fa-box-in-right-th { border-right: 2px solid #10B981 !important; border-top: 2px solid #10B981 !important; background: #A7F3D0 !important; color: #065F46 !important; }
.fa-box-in-left-td { border-left: 1.5px solid #10B981 !important; background: #ECFDF5 !important; color: #065F46 !important; }
.fa-box-in-right-td { border-right: 1.5px solid #10B981 !important; background: #ECFDF5 !important; color: #065F46 !important; font-weight: 800 !important; }
.fa-box-in-left-tot { border-left: 2px solid #10B981 !important; border-bottom: 2px solid #10B981 !important; color: #065F46 !important; }
.fa-box-in-right-tot { border-right: 2px solid #10B981 !important; border-bottom: 2px solid #10B981 !important; color: #065F46 !important; }

.fa-box-out-left-th { border-left: 2px solid #F59E0B !important; border-top: 2px solid #F59E0B !important; background: #FEF3C7 !important; color: #78350F !important; }
.fa-box-out-mid-th { border-top: 2px solid #F59E0B !important; background: #FEF3C7 !important; color: #78350F !important; }
.fa-box-out-right-th { border-right: 2px solid #F59E0B !important; border-top: 2px solid #F59E0B !important; background: #FEF3C7 !important; color: #78350F !important; }
.fa-box-out-left-td { border-left: 1.5px solid #F59E0B !important; background: #FFFBEB !important; }
.fa-box-out-mid-td { background: #FFFBEB !important; color: #78350F !important; font-weight: 800 !important; }
.fa-box-out-right-td { border-right: 1.5px solid #F59E0B !important; background: #FFFBEB !important; }
.fa-box-out-left-tot { border-left: 2px solid #F59E0B !important; border-bottom: 2px solid #F59E0B !important; }
.fa-box-out-mid-tot { border-bottom: 2px solid #F59E0B !important; color: #78350F !important; }
.fa-box-out-right-tot { border-right: 2px solid #F59E0B !important; border-bottom: 2px solid #F59E0B !important; }

.fa-box-cur-only-th { border-left: 2px solid #2563EB !important; border-right: 2px solid #2563EB !important; border-top: 2px solid #2563EB !important; background: #DBEAFE !important; color: #1E2252 !important; }
.fa-box-cur-only-td { border-left: 1.5px solid #3B82F6 !important; border-right: 1.5px solid #3B82F6 !important; background: #EFF6FF !important; color: #1E2252 !important; font-weight: 900 !important; font-size: 13.5px !important; }
.fa-box-cur-only-tot { border-left: 2px solid #2563EB !important; border-right: 2px solid #2563EB !important; border-bottom: 2px solid #2563EB !important; color: #1E2252 !important; font-size: 14px !important; }

/* Read-only Live Sold cell in Sales Entry */
.entry-grid-cell-livesold {
    background: #EFF6FF;
    border: 1px solid #93C5FD;
    border-radius: 5px;
    width: 100% !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center;
    font-size: 11.5px;
    font-weight: 900;
    color: #1D4ED8;
    box-sizing: border-box !important;
    margin: 0 !important;
}

/* Bulk Order Planner Cards */
.bulk-kpi-strip {
    display: grid;
    grid-template-columns: repeat(6, minmax(0, 1fr));
    gap: 8px;
    margin: 10px 0 14px 0;
}
@media (max-width: 1200px) {
    .bulk-kpi-strip {
        grid-template-columns: repeat(3, minmax(0, 1fr));
    }
}
.bulk-kpi-card {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-top: 3.5px solid #3B82F6;
    border-radius: 10px;
    padding: 10px 12px;
    text-align: center;
    box-shadow: 0 3px 10px rgba(30, 34, 82, 0.05);
}
.bulk-kpi-label {
    font-size: 10.5px;
    font-weight: 800;
    text-transform: uppercase;
    color: #64748B;
    letter-spacing: 0.03em;
}
.bulk-kpi-val {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 17px;
    font-weight: 800;
    color: #1E2252;
    margin-top: 3px;
}
.bulk-kpi-sub {
    font-size: 10.5px;
    font-weight: 700;
    color: #3B82F6;
    margin-top: 2px;
}

/* Dashboard 7-Column KPI No-Wrap Styling */
.dashboard-kpi-row div[data-testid="stMetric"] {
    padding: 6px 6px !important;
    min-height: 58px !important;
}
.dashboard-kpi-row div[data-testid="stMetricLabel"] {
    min-height: 20px !important;
}
.dashboard-kpi-row div[data-testid="stMetricLabel"] label,
.dashboard-kpi-row div[data-testid="stMetricLabel"] p,
.dashboard-kpi-row div[data-testid="stMetricLabel"] span {
    font-size: 9.8px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    letter-spacing: -0.01em !important;
    line-height: 1.15 !important;
}
.dashboard-kpi-row div[data-testid="stMetricValue"] {
    font-size: 0.95rem !important;
    margin-top: 2px !important;
    white-space: nowrap !important;
}
</style>
""")

# ----------------------------------------------------------------------
# CONFIG & CANONICAL MAPPINGS
# ----------------------------------------------------------------------
DEFAULT_LOCATION_CARTS_MAP = {
    "HOSUR": ["HOSUR CART 01", "HOSUR CART 02", "HOSUR CART 03"],
}


# --- CASH CUSTODY MOBILE-PARITY HELPERS & MODALS ---
def _cc_fmt_date(val):
    """Format date/datetime/ISO string as dd-Mon-yyyy (matching mobile App.js)."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    try:
        dt = pd.to_datetime(val)
        if pd.isna(dt):
            return "—"
        return dt.strftime("%d-%b-%Y")
    except Exception:
        return str(val)


def _cc_fmt_inr(val):
    """Format numeric value as Indian Rupee string ₹X,XXX.XX."""
    try:
        v = float(val or 0.0)
    except Exception:
        v = 0.0
    sign = "-" if v < 0 else ""
    return f"{sign}₹{abs(v):,.2f}"


def _cc_apportion_spends_to_sales_dates(rows, spends, date_getter, gross_getter):
    """
    Exact Python port of mobile App.js `apportionOpsSpendsToSalesDates`.
    Two-pass apportionment:
      Pass 1 (Backward): salesDate <= spendDate, sorted salesDate DESC.
      Pass 2 (Forward fallback): salesDate > spendDate, sorted salesDate ASC.
    Returns dict keyed by row index -> {"spent": float, "notes": list[str]}.
    """
    pool = []
    for idx, r in enumerate(rows):
        d_raw = date_getter(r)
        try:
            d_str = pd.to_datetime(d_raw).strftime("%Y-%m-%d") if d_raw is not None and pd.notna(d_raw) else "1970-01-01"
        except Exception:
            d_str = str(d_raw or "1970-01-01")[:10]
        g = max(0.0, float(gross_getter(r) or 0.0))
        pool.append({
            "idx": idx,
            "salesDate": d_str,
            "rem": round(g, 2),
            "spent": 0.0,
            "notes": [],
        })

    def _spend_sort_key(sp):
        d_raw = sp.get("spend_date")
        try:
            d_str = pd.to_datetime(d_raw).strftime("%Y-%m-%d") if d_raw is not None and pd.notna(d_raw) else "1970-01-01"
        except Exception:
            d_str = str(d_raw or "1970-01-01")[:10]
        return (d_str, int(sp.get("id") or 0))

    sorted_spends = sorted(spends, key=_spend_sort_key)

    for sp in sorted_spends:
        rem_spend = round(float(sp.get("remaining_amount") or 0.0), 2)
        if rem_spend <= 0.001:
            continue
        d_raw = sp.get("spend_date")
        try:
            sp_date_str = pd.to_datetime(d_raw).strftime("%Y-%m-%d") if d_raw is not None and pd.notna(d_raw) else "1970-01-01"
        except Exception:
            sp_date_str = str(d_raw or "1970-01-01")[:10]
        sp_date_disp = _cc_fmt_date(d_raw)
        sp_notes = str(sp.get("notes") or "").strip()

        # Pass 1: Backward (salesDate <= spendDate, newest first)
        backward = [p for p in pool if p["salesDate"] <= sp_date_str and p["rem"] > 0.001]
        backward.sort(key=lambda x: x["salesDate"], reverse=True)
        for p in backward:
            if rem_spend <= 0.001:
                break
            take = round(min(rem_spend, p["rem"]), 2)
            if take <= 0.001:
                continue
            p["rem"] = round(p["rem"] - take, 2)
            p["spent"] = round(p["spent"] + take, 2)
            rem_spend = round(rem_spend - take, 2)
            note_suffix = f" ({sp_notes})" if sp_notes else ""
            p["notes"].append(f"{sp_date_disp}: {_cc_fmt_inr(take)}{note_suffix}")

        # Pass 2: Forward fallback (salesDate > spendDate, oldest first)
        if rem_spend > 0.001:
            forward = [p for p in pool if p["salesDate"] > sp_date_str and p["rem"] > 0.001]
            forward.sort(key=lambda x: x["salesDate"])
            for p in forward:
                if rem_spend <= 0.001:
                    break
                take = round(min(rem_spend, p["rem"]), 2)
                if take <= 0.001:
                    continue
                p["rem"] = round(p["rem"] - take, 2)
                p["spent"] = round(p["spent"] + take, 2)
                rem_spend = round(rem_spend - take, 2)
                note_suffix = f" ({sp_notes})" if sp_notes else ""
                p["notes"].append(f"{sp_date_disp}: {_cc_fmt_inr(take)}{note_suffix}")

    return {p["idx"]: {"spent": round(p["spent"], 2), "notes": p["notes"]} for p in pool}


@st.dialog("🧾 Ops & Admin 1 Cash Spends", width="large")
def _cc_show_spends_modal(all_spends, tagged_expense_map):
    if not all_spends:
        st.info("No cash spend entries recorded for this location yet.")
        return

    total_sp = sum(float(s.get("amount") or 0) for s in all_spends)
    unhanded_sp = sum(float(s.get("remaining_amount") or 0) for s in all_spends)
    st.markdown(
        f"""
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px;">
            <div style="flex:1;min-width:150px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:10px 14px;">
                <div style="font-size:11px;font-weight:700;color:#64748B;text-transform:uppercase;">Total Spends Listed</div>
                <div style="font-size:18px;font-weight:800;color:#1E2252;">{len(all_spends)} entries • {_cc_fmt_inr(total_sp)}</div>
            </div>
            <div style="flex:1;min-width:150px;background:#FEF2F2;border:1px solid #FECACA;border-radius:10px;padding:10px 14px;">
                <div style="font-size:11px;font-weight:700;color:#B91C1C;text-transform:uppercase;">Unhanded / Remaining</div>
                <div style="font-size:18px;font-weight:800;color:#C43D17;">{_cc_fmt_inr(unhanded_sp)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for s in all_spends:
        sid = int(s["id"])
        spent_by = str(s.get("spent_by") or "OPS_COORDINATOR").strip().upper()
        is_adm1 = spent_by == "ADMIN_1"
        role_bg = "#EFF6FF" if is_adm1 else "#FFFBEB"
        role_fg = "#1D4ED8" if is_adm1 else "#B45309"
        role_bd = "#BFDBFE" if is_adm1 else "#FDE68A"
        role_lbl = "Admin 1 (Yogesh)" if is_adm1 else "Ops Coordinator"
        s_dt = _cc_fmt_date(s.get("spend_date"))
        s_amt = float(s.get("amount") or 0)
        s_alloc = float(s.get("allocated_amount") or 0)
        s_rem = float(s.get("remaining_amount") or 0)
        s_notes = escape(str(s.get("notes") or "—"))
        linked = tagged_expense_map.get(sid)

        with st.container(border=True):
            c1, c2, c3 = st.columns([2.4, 1.3, 1.4], vertical_alignment="center")
            with c1:
                st.markdown(
                    f"""
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px;">
                        <span style="font-weight:800;color:#1E2252;font-size:14px;">Spend #{sid}</span>
                        <span style="background:{role_bg};color:{role_fg};border:1px solid {role_bd};border-radius:999px;padding:2px 8px;font-size:11px;font-weight:700;">{role_lbl}</span>
                        <span style="color:#64748B;font-size:12px;font-weight:600;">📅 {s_dt}</span>
                    </div>
                    <div style="font-size:13px;color:#334155;">{s_notes}</div>
                    """,
                    unsafe_allow_html=True,
                )
            with c2:
                st.markdown(
                    f"""
                    <div style="font-size:15px;font-weight:800;color:#C43D17;">{_cc_fmt_inr(s_amt)}</div>
                    <div style="font-size:11px;color:#64748B;">Allocated: {_cc_fmt_inr(s_alloc)}</div>
                    <div style="font-size:11px;color:{'#C43D17' if s_rem > 0.001 else '#059669'};font-weight:700;">Remaining: {_cc_fmt_inr(s_rem)}</div>
                    """,
                    unsafe_allow_html=True,
                )
            with c3:
                if linked:
                    st.markdown(
                        f"<div style='background:#ECFDF5;color:#047857;border:1px solid #A7F3D0;border-radius:8px;padding:4px 8px;font-size:11px;font-weight:700;text-align:center;margin-bottom:6px;'>✓ Expense #{int(linked['id'])} ({escape(str(linked.get('category') or ''))})</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        "<div style='background:#FFFBEB;color:#B45309;border:1px solid #FDE68A;border-radius:8px;padding:4px 8px;font-size:11px;font-weight:700;text-align:center;margin-bottom:6px;'>Pending Expense Entry</div>",
                        unsafe_allow_html=True,
                    )
                if st.button(
                    "🧾 Create Expense →" if not linked else "＋ Create Another →",
                    key=f"cc_modal_conv_spend_{sid}",
                    type="primary" if not linked else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["_pending_ops_spend_to_load"] = {
                        "id": sid,
                        "spend_date": s.get("spend_date"),
                        "amount": s_amt,
                        "notes": s.get("notes") or "",
                        "spent_by": spent_by,
                    }
                    st.session_state["_pending_page_nav"] = "Expenses"
                    st.session_state["_pending_exp_nav_sec"] = "📋 Expenses (Bills / Invoices)"
                    st.session_state["_pending_e_sub_mode_rad"] = "Add New Expense"
                    st.rerun()


@st.dialog("📚 Recently Confirmed Collections (Admin 2)", width="large")
def _cc_show_recent_collections_modal(recent_batches):
    if not recent_batches:
        st.info("No confirmed handovers to Admin 2 (Srilalitha) recorded yet.")
        return

    for b in recent_batches:
        bid = int(b["id"])
        ho_dt = _cc_fmt_date(b.get("handed_over_date") or b.get("collection_date"))
        s_dates = b.get("salesDates") or []
        if len(s_dates) == 1:
            dates_lbl = _cc_fmt_date(s_dates[0])
        elif len(s_dates) > 1:
            dates_lbl = f"{_cc_fmt_date(s_dates[0])} → {_cc_fmt_date(s_dates[-1])} ({len(s_dates)} days)"
        else:
            dates_lbl = _cc_fmt_date(b.get("collection_date"))

        gross = float(b.get("expected_amount") or 0)
        ops_sp = float(b.get("cash_spent_amount") or 0)
        adm1_sp = float(b.get("admin1_spent_amount") or 0)
        final_amt = float(b.get("actual_collected_amount") if b.get("actual_collected_amount") is not None else max(0.0, gross - ops_sp - adm1_sp))
        notes = escape(str(b.get("notes") or "").strip())
        ops_notes = escape(str(b.get("cash_spent_notes") or "").strip())
        adm1_notes = escape(str(b.get("admin1_spent_notes") or "").strip())

        notes_html = ""
        if ops_notes:
            notes_html += f"<div style='font-size:12px;color:#B91C1C;margin-top:4px;'><b>Ops Spent:</b> {ops_notes}</div>"
        if adm1_notes:
            notes_html += f"<div style='font-size:12px;color:#1D4ED8;margin-top:4px;'><b>Admin 1 Spent:</b> {adm1_notes}</div>"
        if notes:
            notes_html += f"<div style='font-size:12px;color:#475569;margin-top:4px;'><b>Notes:</b> {notes}</div>"

        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #E2E8F0;border-left:4px solid #059669;border-radius:12px;padding:12px 16px;margin-bottom:10px;box-shadow:0 1px 4px rgba(15,23,42,0.04);">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:6px;">
                    <div style="font-weight:800;color:#1E2252;font-size:14px;">Batch #{bid} &nbsp;•&nbsp; Sales: {escape(dates_lbl)}</div>
                    <span style="background:#ECFDF5;color:#047857;border:1px solid #A7F3D0;border-radius:999px;padding:2px 10px;font-size:11px;font-weight:700;">✓ Handed to Srilalitha on {ho_dt}</span>
                </div>
                <div style="display:grid;grid-template-columns:repeat(4,minmax(100px,1fr));gap:8px;margin-top:8px;">
                    <div style="background:#F8FAFC;border-radius:8px;padding:6px 10px;">
                        <div style="font-size:10px;font-weight:700;color:#64748B;text-transform:uppercase;">Gross Sales</div>
                        <div style="font-size:14px;font-weight:700;color:#0F172A;">{_cc_fmt_inr(gross)}</div>
                    </div>
                    <div style="background:#FEF2F2;border-radius:8px;padding:6px 10px;">
                        <div style="font-size:10px;font-weight:700;color:#B91C1C;text-transform:uppercase;">Ops Spent</div>
                        <div style="font-size:14px;font-weight:700;color:#C43D17;">{_cc_fmt_inr(ops_sp)}</div>
                    </div>
                    <div style="background:#EFF6FF;border-radius:8px;padding:6px 10px;">
                        <div style="font-size:10px;font-weight:700;color:#1D4ED8;text-transform:uppercase;">Admin 1 Spent</div>
                        <div style="font-size:14px;font-weight:700;color:#1E40AF;">{_cc_fmt_inr(adm1_sp)}</div>
                    </div>
                    <div style="background:#ECFDF5;border-radius:8px;padding:6px 10px;">
                        <div style="font-size:10px;font-weight:700;color:#047857;text-transform:uppercase;">Final Handed Over</div>
                        <div style="font-size:14px;font-weight:800;color:#059669;">{_cc_fmt_inr(final_amt)}</div>
                    </div>
                </div>
                {notes_html}
            </div>
            """,
            unsafe_allow_html=True,
        )


def get_active_location_filter():
    """Return 'ALL' when Admin selects All Locations (Aggregated), else the specific city uppercase."""
    loc = st.session_state.get("current_location", st.session_state.get("assigned_location", "HOSUR"))
    if not loc or str(loc).startswith("All Locations"):
        return "ALL"
    return str(loc).strip().upper()

def get_default_write_city():
    """Return concrete city name for INSERTs (defaults to HOSUR when viewing All Locations)."""
    loc = get_active_location_filter()
    return "HOSUR" if loc == "ALL" else loc

def get_loc_sql_clause(col_expr="city", param_name="active_loc"):
    """Return (sql_and_clause, params_dict) for filtering by active location."""
    loc = get_active_location_filter()
    if loc == "ALL":
        return "", {}
    return f" AND UPPER(TRIM(COALESCE({col_expr}, 'HOSUR'))) = :{param_name} ", {param_name: loc}

def load_configured_locations_list(include_inactive=False):
    """Load configured locations from public.operating_locations (with safe fallback)."""
    locs = ["HOSUR"]
    try:
        conn = globals().get("db_conn")
        if conn is not None:
            where_sql = "" if include_inactive else "WHERE is_active = true"
            df = conn.query(f"SELECT location_code FROM public.operating_locations {where_sql} ORDER BY location_code ASC;", ttl="10m")
            if not df.empty:
                locs = [str(x).strip().upper() for x in df["location_code"].dropna().tolist() if str(x).strip()]
    except Exception:
        pass
    return locs if locs else ["HOSUR"]

def get_carts_for_active_location(include_freezer=False):
    """Load active carts (and optionally freezers) from public.location_assets for the selected location."""
    loc = get_active_location_filter()
    try:
        conn = globals().get("db_conn")
        if conn is not None:
            type_clause = "AND asset_type IN ('CART', 'FREEZER')" if include_freezer else "AND asset_type = 'CART'"
            if loc == "ALL":
                df = conn.query(
                    f"SELECT asset_name FROM public.location_assets WHERE is_active = true {type_clause} ORDER BY location_code ASC, sort_order ASC, asset_name ASC;",
                    ttl="10m"
                )
            else:
                df = conn.query(
                    f"SELECT asset_name FROM public.location_assets WHERE is_active = true {type_clause} AND UPPER(TRIM(location_code)) = :loc ORDER BY sort_order ASC, asset_name ASC;",
                    params={"loc": loc},
                    ttl="10m"
                )
            if not df.empty:
                return [str(x).strip() for x in df["asset_name"].dropna().tolist() if str(x).strip()]
    except Exception:
        pass
    if loc == "ALL":
        return DEFAULT_LOCATION_CARTS_MAP["HOSUR"]
    return DEFAULT_LOCATION_CARTS_MAP.get(loc, [f"{loc} CART 01", f"{loc} CART 02", f"{loc} CART 03"])

def get_location_for_cart(cart_name):
    """Resolve the operating location code for a specific cart or freezer name."""
    c_clean = str(cart_name or "").strip()
    if not c_clean or c_clean == "Central / Freezer":
        return get_default_write_city()
    if db_conn is not None:
        try:
            df = db_conn.query(
                "SELECT location_code FROM public.location_assets WHERE UPPER(TRIM(asset_name)) = UPPER(TRIM(:cname)) LIMIT 1;",
                params={"cname": c_clean},
                ttl="10m"
            )
            if not df.empty and str(df.iloc[0]["location_code"]).strip():
                return str(df.iloc[0]["location_code"]).strip().upper()
        except Exception:
            pass
    c_upper = c_clean.upper()
    for loc_code in load_configured_locations_list(include_inactive=True):
        if c_upper.startswith(loc_code):
            return loc_code
    return get_default_write_city()

CITY = get_default_write_city()
CARTS = get_carts_for_active_location(include_freezer=False)

PAYMENT_STATUSES = ["Pending", "Partial", "Complete"]
PO_STATUSES = ["Draft", "Placed", "Pending", "In Transit", "Completed", "Cancelled"]

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
PAYMENT_MODES = ["UPI / Bank Transfer", "Cash","UPI / Bank Transfer + Cash", "Cheque / DD", "Credit Card / POS", "Other"]
STAFF_STATUSES = ["active", "inactive", "on_leave","on-boarding"]
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
    # Psycopg3 automatically prepares a statement after repeated executions.
    # Supabase/Supavisor transaction-pooled connections can reuse server-side
    # prepared-statement names, causing DuplicatePreparedStatement errors.
    # Disable automatic prepared statements for this connection.
    db_conn = st.connection(
        "postgresql",
        type="sql",
        connect_args={"prepare_threshold": None},
        pool_pre_ping=True,
    )
except Exception:
    db_conn = None

@st.dialog("WhatsApp Confirmation")
def show_whatsapp_order_confirmation():
    payload = st.session_state.get("wa_confirmation_payload")
    if not payload:
        st.error("Order details are no longer available. Please start again from Freezer Analysis.")
        return
    st.success("WhatsApp message has been opened. Please confirm that you sent the order message.")
    st.write(f"**Overall Units:** {payload['total_units']}")
    st.write("Would you like to place the order?")
    c1, c2 = st.columns(2)
    def save_po(status):
        notes = payload["notes"]
        if payload["discount_pct"] > 0: notes = f"[Discount: {payload['discount_pct']:.2f}% | Final: ₹{payload['final_amount']:,.2f}] {notes}".strip()
        with db_conn.session as s:
            res = s.execute(text("INSERT INTO purchase_orders (order_date, expected_date, location, order_status, notes) VALUES (:od, :ed, :loc, :stat, :notes) RETURNING id;"), {"od": payload["order_date"], "ed": payload["expected_date"], "loc": payload["location"], "stat": status, "notes": notes})
            poid = res.scalar()
            for code, qty in payload["items"]:
                s.execute(text("INSERT INTO purchase_order_items (order_id, flavor_code, ordered_units) VALUES (:poid, :code, :qty);"), {"poid": poid, "code": code, "qty": qty})
            s.commit()
        return poid
    with c1:
        if st.button("Yes — Place Order", type="primary", use_container_width=True, key="wa_place_order"):
            try:
                poid = save_po("Placed")
                st.session_state.pop("wa_confirmation_payload", None)
                st.session_state.pop("po_prefill_quantities", None)
                st.session_state["po_prefill_active"] = False
                st.session_state["_pending_page_nav"] = "Purchase Orders"
                st.session_state["_pending_po_screen_mode"] = "Edit / Track Existing Orders"
                st.session_state["po_success_message"] = f"Purchase Order #{poid} placed successfully!"
                st.rerun()
            except Exception as e: st.error(f"Could not place purchase order: {e}")
    with c2:
        if st.button("No — Save as Draft", use_container_width=True, key="wa_save_draft"):
            try:
                poid = save_po("Draft")
                st.session_state.pop("wa_confirmation_payload", None)
                st.session_state.pop("po_prefill_quantities", None)
                st.session_state.pop("new_po_editor", None)
                st.session_state.pop("po_whatsapp_number", None)
                st.session_state["po_prefill_active"] = False
                st.session_state["new_po_order_date"] = date.today()
                st.session_state["new_po_exp_date"] = date.today() + timedelta(days=2)
                st.session_state["new_po_loc"] = CITY
                st.session_state["new_po_status"] = "Placed"
                st.session_state["new_po_discount"] = 0.0
                st.session_state["new_po_notes"] = ""
                st.session_state["_pending_page_nav"] = "Purchase Orders"
                st.session_state["_pending_po_screen_mode"] = "Create New Order"
                st.session_state["po_success_message"] = f"Purchase Order #{poid} saved as Draft. A blank Create New Order screen is ready."
                st.rerun()
            except Exception as e: st.error(f"Could not save draft purchase order: {e}")


@st.dialog("Notification")
def show_success_modal(message):
    st.success(message)
    if st.button("OK", type="primary", use_container_width=True):
        st.rerun()

@st.dialog("Opening Stock Mismatch")
def show_opening_mismatch_modal(message):
    st.error(message)
    if st.button("OK", type="primary", use_container_width=True, key="opening_mismatch_ok_btn"):
        st.rerun()

@st.dialog("⚠️ Confirm Delete Stock Audit")
def confirm_delete_stock_audit_modal(audit_row):
    aid = int(audit_row["audit_id"])
    adt = pd.to_datetime(audit_row["audit_date"]).strftime("%d-%b-%Y")
    atm = str(audit_row.get("audit_time") or "")[:5] or "—"
    loc = str(audit_row.get("location") or CITY)
    by = str(audit_row.get("audited_by") or "—")
    phys_tot = sum(int(_num(audit_row.get(FLAVOR_MAP[c]["audit_col"], 0))) for c in FLAVOR_CODES)
    var_tot = int(_num(audit_row.get("total_variance_units", 0)))

    st.warning(f"Are you sure you want to permanently delete **Stock Audit #{aid}**?")
    st.markdown(
        f'''
        <div style="background:#FFF8F6;border:1px solid #FECACA;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:13px;">
            <div><b>Date:</b> {adt} &nbsp;|&nbsp; <b>Time:</b> {atm} &nbsp;|&nbsp; <b>Location:</b> {loc}</div>
            <div><b>Audited By:</b> {by} &nbsp;|&nbsp; <b>Physical Count:</b> {phys_tot} units &nbsp;|&nbsp; <b>Variance:</b> {var_tot:+d} units</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Yes, Delete Audit", type="primary", use_container_width=True, key=f"confirm_del_audit_{aid}"):
            try:
                with db_conn.session as s:
                    s.execute(text("DELETE FROM stock_audits_wide WHERE audit_id = :aid;"), {"aid": aid})
                    s.commit()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete stock audit: {e}")
    with c2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_del_audit_{aid}"):
            st.rerun()


@st.dialog("⚠️ Confirm Delete Expense")
def confirm_delete_expense_modal(exp_row):
    exp_id = int(exp_row["id"])
    exp_dt = pd.to_datetime(exp_row["expense_date"]).strftime("%d-%b-%Y")
    st.warning(f"Are you sure you want to permanently delete **Expense #{exp_id}**?")
    st.markdown(
        f'''
        <div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:13px;">
            <div><b>Date:</b> {exp_dt} &nbsp;|&nbsp; <b>Category:</b> {exp_row["category"]}</div>
            <div><b>Description:</b> {exp_row.get("description") or exp_row.get("vendor_name") or "—"}</div>
            <div><b>Total Amount:</b> ₹{float(exp_row["total_amount"]):,.2f} &nbsp;|&nbsp; <b>Paid:</b> ₹{float(exp_row.get("total_paid") or 0):,.2f}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    if int(exp_row.get("payment_count") or 0) > 0:
        st.caption(f"⚠️ Note: Deleting this expense will also delete its **{int(exp_row['payment_count'])}** linked payment record(s).")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Yes, Delete Expense", type="primary", use_container_width=True, key=f"confirm_del_exp_{exp_id}"):
            try:
                with db_conn.session as s:
                    s.execute(text("DELETE FROM staff_salary_payouts WHERE expense_id = :eid;"), {"eid": exp_id})
                    s.execute(text("DELETE FROM expense_payments WHERE expense_id = :eid;"), {"eid": exp_id})
                    s.execute(text("DELETE FROM expenses WHERE id = :eid;"), {"eid": exp_id})
                    s.commit()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete expense: {e}")
    with c2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_del_exp_{exp_id}"):
            st.rerun()


@st.dialog("⚠️ Confirm Delete Payment")
def confirm_delete_payment_modal(pay_row):
    pay_id = int(pay_row["id"])
    exp_id = int(pay_row["expense_id"])
    pay_dt = pd.to_datetime(pay_row["payment_date"]).strftime("%d-%b-%Y")
    st.warning(f"Are you sure you want to permanently delete **Payment #{pay_id}**?")
    st.markdown(
        f'''
        <div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:13px;">
            <div><b>Payment Date:</b> {pay_dt} &nbsp;|&nbsp; <b>Mode:</b> {pay_row["payment_mode"]}</div>
            <div><b>Linked Expense:</b> #{exp_id} ({pay_row.get("category") or "—"})</div>
            <div><b>Amount Paid:</b> ₹{float(pay_row["amount_paid"]):,.2f} &nbsp;|&nbsp; <b>Paid To:</b> {pay_row.get("paid_to") or "—"}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Yes, Delete Payment", type="primary", use_container_width=True, key=f"confirm_del_pay_{pay_id}"):
            try:
                with db_conn.session as s:
                    s.execute(text("UPDATE staff_salary_payouts SET payment_id = NULL WHERE payment_id = :pid;"), {"pid": pay_id})
                    s.execute(text("DELETE FROM expense_payments WHERE id = :pid;"), {"pid": pay_id})

                    rem = s.execute(
                        text('''
                            SELECT e.total_amount, COALESCE(SUM(p.amount_paid), 0) AS paid_sum
                            FROM expenses e
                            LEFT JOIN expense_payments p ON e.id = p.expense_id
                            WHERE e.id = :eid
                            GROUP BY e.id, e.total_amount;
                        '''),
                        {"eid": exp_id},
                    ).fetchone()
                    if rem:
                        tot_amt = float(rem[0] or 0.0)
                        paid_sum = float(rem[1] or 0.0)
                        new_status = "Paid" if paid_sum >= tot_amt - 0.001 else ("Partially Paid" if paid_sum > 0.001 else "Pending")
                        s.execute(
                            text("UPDATE expenses SET status = :stat, updated_at = NOW() WHERE id = :eid;"),
                            {"stat": new_status, "eid": exp_id},
                        )
                    s.commit()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete payment: {e}")
    with c2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_del_pay_{pay_id}"):
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
            df = db_conn.query("SELECT code, name, mrp, cost_price FROM flavors;", ttl="10m")
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
            loc_sql, loc_params = get_loc_sql_clause("location")
            df = db_conn.query(f"SELECT name FROM staff WHERE status = 'active' {loc_sql} ORDER BY name ASC;", params=loc_params, ttl="5m")
            if not df.empty:
                return ["Select Staff"] + df["name"].tolist()
        except Exception:
            pass
    return ["Select Staff"]

def get_latest_cart_closing_state_with_date(cart_name, before_date):
    if db_conn is None: return {}, "", None
    query = """
    SELECT e.entry_date, e.staff_name, json_agg(json_build_object('code', i.flavor_code, 'close', i.closing_units)) AS items
    FROM daily_cart_entries e
    LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
    WHERE e.cart_name = :cart AND e.entry_date < :bdate
    GROUP BY e.id, e.entry_date, e.staff_name ORDER BY e.entry_date DESC LIMIT 1;
    """
    try:
        df = db_conn.query(query, params={"cart": cart_name, "bdate": before_date}, ttl="60s")
        if not df.empty:
            r = df.iloc[0]
            prev_dt = pd.to_datetime(r["entry_date"]).date() if pd.notna(r["entry_date"]) else None
            staff = str(r["staff_name"]) if pd.notna(r["staff_name"]) else ""
            items = r["items"] if isinstance(r["items"], list) else []
            closings = {str(itm.get("code")).strip(): int(itm.get("close") or 0) for itm in items if isinstance(itm, dict) and itm.get("code")}
            return closings, staff, prev_dt
    except Exception:
        pass
    return {}, "", None

def get_latest_cart_closing_state(cart_name, before_date):
    closings, staff, _ = get_latest_cart_closing_state_with_date(cart_name, before_date)
    return closings, staff

def list_daily_entries_with_prefill():
    entries = []
    if db_conn is not None:
        query = """
        SELECT e.id AS db_id, e.entry_date, e.cart_name, e.staff_name, e.total_collection, e.phonepe, e.cash,
            e.staff_advance, e.food_tea_cash, e.cash_leakage,
            e.cash_leakage_explained, e.cash_leakage_unexplained, e.remarks,
            json_agg(json_build_object('code', i.flavor_code, 'open', i.opening_units, 'add', i.added_units, 'sold', i.sold_units, 'close', i.closing_units)) AS items
        FROM daily_cart_entries e
        LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
        WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :active_loc)
        GROUP BY e.id, e.entry_date, e.cart_name, e.staff_name, e.total_collection, e.phonepe, e.cash,
            e.staff_advance, e.food_tea_cash, e.cash_leakage, e.cash_leakage_explained,
            e.cash_leakage_unexplained, e.remarks
        ORDER BY e.entry_date DESC, e.cart_name ASC;
        """
        df = db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
        if not df.empty:
            for _, r in df.iterrows():
                raw_items = r.get("items") or []
                items_by_code = {str(itm.get("code")).strip(): itm for itm in raw_items if isinstance(itm, dict) and itm.get("code")}
                
                entries.append({
                    "db_id": r["db_id"], "date": pd.to_datetime(r["entry_date"]), "cart": str(r["cart_name"]).strip(),
                    "by_code": {code: {"opening": int(items_by_code.get(code, {}).get("open") or 0), "added": int(items_by_code.get(code, {}).get("add") or 0), "sold": int(items_by_code.get(code, {}).get("sold") or 0), "closing": int(items_by_code.get(code, {}).get("close") or 0)} for code in FLAVOR_CODES},
                    "total": float(r["total_collection"]) if pd.notna(r["total_collection"]) else 0.0, 
                    "phonepe": float(r["phonepe"]) if pd.notna(r["phonepe"]) else 0.0, 
                    "cash": float(r["cash"]) if pd.notna(r["cash"]) else 0.0, 
                    "cash_leakage": float(r["cash_leakage"]) if pd.notna(r["cash_leakage"]) else 0.0,
                    "cash_leakage_explained": float(r["cash_leakage_explained"]) if pd.notna(r["cash_leakage_explained"]) else 0.0,
                    "cash_leakage_unexplained": float(r["cash_leakage_unexplained"]) if pd.notna(r["cash_leakage_unexplained"]) else 0.0,
                    "remarks": str(r["remarks"]) if pd.notna(r["remarks"]) else "",
                    "staff_name": str(r["staff_name"]) if pd.notna(r["staff_name"]) else "", 
                    "staff_advance": float(r["staff_advance"]) if pd.notna(r["staff_advance"]) else 0.0, 
                    "food_tea_cash": float(r["food_tea_cash"]) if pd.notna(r["food_tea_cash"]) else 0.0, 
                    "is_prefill": False
                })

    yesterday = date.today() - timedelta(days=1)
    existing_yesterday_carts = {e["cart"] for e in entries if e["date"].date() == yesterday}

    for cart in CARTS:
        if cart not in existing_yesterday_carts:
            prev_closings, prev_staff = get_latest_cart_closing_state(cart, yesterday)
            by_code = {code: {"opening": prev_closings.get(code, 0), "added": 0, "closing": prev_closings.get(code, 0), "sold": 0} for code in FLAVOR_CODES}
            entries.append({
                "db_id": f"prefill_{cart}_{yesterday.strftime('%Y%m%d')}", "date": pd.Timestamp(yesterday), "cart": cart, "by_code": by_code,
                "total": 0.0, "phonepe": 0.0, "cash": 0.0, "cash_leakage": 0.0,
                "cash_leakage_explained": 0.0, "cash_leakage_unexplained": 0.0,
                "remarks": "[web app]", "staff_name": prev_staff, "staff_advance": 0.0, "food_tea_cash": 0.0, "is_prefill": True
            })

    entries.sort(key=lambda x: (x["date"], x["cart"]), reverse=True)
    return entries

def sync_daily_entry(entry_date, cart_name, added_map, closing_map, opening_map, sold_map, total, phonepe, cash, remarks,
                     staff_name="", staff_advance=0.0, food_tea_cash=0.0,
                     cash_leakage_explained=0.0, cash_leakage_unexplained=0.0):
    web_entry_tag = "[web app]"
    remarks_text = re.sub(r"\[(?:mobile\s*app|web\s*app)\]", "", str(remarks or ""), flags=re.IGNORECASE).strip()
    remarks_text = f"{remarks_text} {web_entry_tag}".strip()

    cash_leakage_explained = max(0.0, float(cash_leakage_explained or 0.0))
    cash_leakage_unexplained = max(0.0, float(cash_leakage_unexplained or 0.0))
    cash_leakage = cash_leakage_explained + cash_leakage_unexplained
    cart_loc = get_location_for_cart(cart_name)
    exp_month = list(calendar.month_name)[entry_date.month]

    if db_conn is not None:
        with db_conn.session as s:
            res = s.execute(
                text("""
                INSERT INTO daily_cart_entries (
                    entry_date, cart_name, city, staff_name, total_collection, phonepe, cash,
                    staff_advance, food_tea_cash, cash_leakage_explained, cash_leakage_unexplained,
                    cash_leakage, remarks
                )
                VALUES (
                    :date, :cart, :city, :staff, :tot, :ph, :cash,
                    :adv, :food, :leak_exp, :leak_unexp, :leak, :rem
                )
                ON CONFLICT (entry_date, cart_name) DO UPDATE 
                SET city = EXCLUDED.city,
                    staff_name = EXCLUDED.staff_name,
                    total_collection = EXCLUDED.total_collection,
                    phonepe = EXCLUDED.phonepe,
                    cash = EXCLUDED.cash,
                    staff_advance = EXCLUDED.staff_advance,
                    food_tea_cash = EXCLUDED.food_tea_cash,
                    cash_leakage_explained = EXCLUDED.cash_leakage_explained,
                    cash_leakage_unexplained = EXCLUDED.cash_leakage_unexplained,
                    cash_leakage = EXCLUDED.cash_leakage,
                    remarks = EXCLUDED.remarks
                RETURNING id;
                """),
                {
                    "date": entry_date, "cart": cart_name, "city": cart_loc, "staff": staff_name, 
                    "tot": float(total), "ph": float(phonepe), "cash": float(cash),
                    "adv": float(staff_advance), "food": float(food_tea_cash),
                    "leak_exp": cash_leakage_explained, "leak_unexp": cash_leakage_unexplained,
                    "leak": cash_leakage, "rem": remarks_text
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
                    {"eid": daily_id, "code": code, "open": int(opening_map[code]), "add": int(added_map[code]), "sold": int(sold_map[code]), "close": int(closing_map[code])}
                )

            s.execute(text("DELETE FROM expenses WHERE remarks LIKE :tag;"), {"tag": f"[Auto: Daily Entry #{daily_id}]%"})

            if float(staff_advance) > 0 and staff_name:
                res_adv = s.execute(
                    text("""
                    INSERT INTO expenses (expense_date, month, location, expense_type, category, sub_category, description, total_amount, attributed_to, vendor_name, staff_name, status, recorded_by, remarks) 
                    VALUES (:ed, :mo, :loc, 'OPEX', 'Labour Charges', 'Staff Advance', :desc, :amt, :attr, :vendor, :staff, 'Paid', 'Daily Entry Auto', :rem) RETURNING id;
                    """),
                    {"ed": entry_date, "mo": exp_month, "loc": cart_loc, "desc": f"Daily Cart Cash Advance - {staff_name} ({cart_name})", "amt": float(staff_advance), "attr": cart_name, "vendor": staff_name, "staff": staff_name, "rem": f"[Auto: Daily Entry #{daily_id}] Staff Advance"}
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
                    INSERT INTO expenses (expense_date, month, location, expense_type, category, sub_category, description, total_amount, attributed_to, vendor_name, staff_name, status, recorded_by, remarks) 
                    VALUES (:ed, :mo, :loc, 'OPEX', 'Labour Charges', 'Food & Tea', :desc, :amt, :attr, :vendor, :staff, 'Paid', 'Daily Entry Auto', :rem) RETURNING id;
                    """),
                    {"ed": entry_date, "mo": exp_month, "loc": cart_loc, "desc": f"Daily Food & Tea Allowance - {staff_name} ({cart_name})", "amt": float(food_tea_cash), "attr": cart_name, "vendor": staff_name, "staff": staff_name, "rem": f"[Auto: Daily Entry #{daily_id}] Food & Tea Cash"}
                )
                exp_food_id = res_food.scalar()
                s.execute(
                    text("""
                    INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes) 
                    VALUES (:eid, :pdate, :pamt, 'Cash', :pref, :pto, 'Cart Cash', :notes);
                    """),
                    {"eid": exp_food_id, "pdate": entry_date, "pamt": float(food_tea_cash), "pref": f"CART-FOOD-{entry_date.strftime('%Y%m%d')}", "pto": staff_name, "notes": f"Daily food and tea cash allowance disbursed from cart collection at {cart_name}"}
                )

            for leakage_kind, amount, leakage_staff in (
                ("Explained", cash_leakage_explained, None),
                ("Unexplained", cash_leakage_unexplained, staff_name or None),
            ):
                if amount > 0.001:
                    s.execute(
                        text("""
                        INSERT INTO expenses (expense_date, month, location, expense_type, category, sub_category,
                                              description, total_amount, attributed_to, vendor_name,
                                              staff_name, status, recorded_by, remarks)
                        VALUES (:ed, :mo, :loc, 'OPEX', 'Leakage Expense', 'Cash Leakage', :desc, :amt,
                                :attr, NULL, :staff, 'Not Applicable', 'Daily Entry Auto', :rem);
                        """),
                        {
                            "ed": entry_date,
                            "mo": exp_month,
                            "loc": cart_loc,
                            "desc": f"Cash Leakage ({leakage_kind}) recorded at {cart_name}",
                            "amt": float(amount),
                            "attr": cart_name,
                            "staff": leakage_staff,
                            "rem": f"[Auto: Daily Entry #{daily_id}] Leakage {leakage_kind}",
                        }
                    )

            s.commit()

def sync_today_restock_entry(today_date, cart_name, staff_name, today_prev_closing_map, today_added_map):
    cart_loc = get_location_for_cart(cart_name)
    if db_conn is not None:
        with db_conn.session as s:
            res = s.execute(
                text("SELECT id FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :cart;"),
                {"dt": today_date, "cart": cart_name}
            ).fetchone()
            
            if res:
                today_id = res[0]
                if staff_name:
                    s.execute(text("UPDATE daily_cart_entries SET city = :city, staff_name = COALESCE(NULLIF(:st, ''), staff_name) WHERE id = :id;"), {"city": cart_loc, "st": staff_name, "id": today_id})
            else:
                res_ins = s.execute(
                    text("""
                    INSERT INTO daily_cart_entries (entry_date, cart_name, city, staff_name, total_collection, phonepe, cash, staff_advance, food_tea_cash, remarks)
                    VALUES (:dt, :cart, :city, :st, 0, 0, 0, 0, 0, '') RETURNING id;
                    """),
                    {"dt": today_date, "cart": cart_name, "city": cart_loc, "st": staff_name}
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


def get_today_cart_stock_state(cart_name, today_date):
    """Return today's Daily Entry stock rows, falling back to the latest prior closing."""
    stock_state = {
        code: {"opening": 0, "added": 0, "sold": 0, "closing": 0}
        for code in FLAVOR_CODES
    }
    staff_name = ""

    prev_closings, prev_staff = get_latest_cart_closing_state(cart_name, today_date)
    staff_name = prev_staff or ""
    for code in FLAVOR_CODES:
        opening = int(prev_closings.get(code, 0))
        stock_state[code] = {
            "opening": opening,
            "added": 0,
            "sold": 0,
            "closing": opening,
        }

    if db_conn is None:
        return stock_state, staff_name

    try:
        entry_df = db_conn.query(
            """
            SELECT id, staff_name
            FROM daily_cart_entries
            WHERE entry_date = :dt AND cart_name = :cart
            LIMIT 1;
            """,
            params={"dt": today_date, "cart": cart_name},
            ttl="60s",
        )
        if entry_df.empty:
            return stock_state, staff_name

        today_id = int(entry_df.iloc[0]["id"])
        if pd.notna(entry_df.iloc[0].get("staff_name")) and str(entry_df.iloc[0].get("staff_name") or "").strip():
            staff_name = str(entry_df.iloc[0]["staff_name"]).strip()

        items_df = db_conn.query(
            """
            SELECT flavor_code, opening_units, added_units, sold_units, closing_units
            FROM daily_cart_items
            WHERE daily_entry_id = :eid;
            """,
            params={"eid": today_id},
            ttl="60s",
        )
        for _, row in items_df.iterrows():
            code = str(row.get("flavor_code") or "").strip()
            if code not in stock_state:
                continue
            opening = int(_num(row.get("opening_units")))
            added = int(_num(row.get("added_units")))
            sold = int(_num(row.get("sold_units")))
            closing_raw = row.get("closing_units")
            closing = (
                int(_num(closing_raw))
                if pd.notna(closing_raw)
                else max(0, opening + added - sold)
            )
            stock_state[code] = {
                "opening": opening,
                "added": added,
                "sold": sold,
                "closing": closing,
            }
    except Exception:
        pass

    return stock_state, staff_name


def get_cart_stock_view_data(cart_name, target_date):
    """
    Return read-only flavour-wise stock breakdown for (cart_name, target_date):
    Opening, Restock (total added_units including any extra stock), Extra Stock, and Sold Units.
    For today's date, Sold Units is always 0.
    """
    today_dt = date.today()
    is_today = (target_date == today_dt)

    prev_closings, prev_staff = get_latest_cart_closing_state(cart_name, target_date)
    staff_name = prev_staff or "—"

    opening_map = {code: int(prev_closings.get(code, 0)) for code in FLAVOR_CODES}
    restock_map = {code: 0 for code in FLAVOR_CODES}
    extra_map = {code: 0 for code in FLAVOR_CODES}
    sold_map = {code: 0 for code in FLAVOR_CODES}

    if db_conn is not None:
        try:
            entry_df = db_conn.query(
                """
                SELECT id, staff_name
                FROM daily_cart_entries
                WHERE entry_date = :dt AND cart_name = :cart
                LIMIT 1;
                """,
                params={"dt": target_date, "cart": cart_name},
                ttl="60s",
            )
            if not entry_df.empty:
                eid = int(entry_df.iloc[0]["id"])
                raw_st = str(entry_df.iloc[0].get("staff_name") or "").strip()
                if raw_st and raw_st != "Select Staff":
                    staff_name = raw_st

                items_df = db_conn.query(
                    """
                    SELECT flavor_code, opening_units, added_units, sold_units
                    FROM daily_cart_items
                    WHERE daily_entry_id = :eid;
                    """,
                    params={"eid": eid},
                    ttl="60s",
                )
                for _, r in items_df.iterrows():
                    code = str(r.get("flavor_code") or "").strip()
                    if code in FLAVOR_CODES:
                        opening_map[code] = int(_num(r.get("opening_units")))
                        restock_map[code] = int(_num(r.get("added_units")))
                        sold_map[code] = 0 if is_today else max(0, int(_num(r.get("sold_units"))))

            extra_df = db_conn.query(
                """
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
                FROM public.cart_extra_stock_logs
                WHERE entry_date = :dt AND cart_name = :cart;
                """,
                params={"dt": target_date, "cart": cart_name},
                ttl="60s",
            )
            if not extra_df.empty:
                erow = extra_df.iloc[0]
                for code in FLAVOR_CODES:
                    acol = FLAVOR_MAP[code]["audit_col"]
                    extra_map[code] = max(0, int(_num(erow.get(acol, 0))))
        except Exception:
            pass

    rows = []
    for code in FLAVOR_CODES:
        f_info = FLAVOR_MAP[code]
        rows.append({
            "code": code,
            "flavour": f_info["name"],
            "opening": int(opening_map.get(code, 0)),
            "restock": int(restock_map.get(code, 0)),
            "extra": int(extra_map.get(code, 0)),
            "sold": 0 if is_today else int(sold_map.get(code, 0)),
        })

    return rows, (staff_name if staff_name else "—")


def sync_today_opening_after_sales_update(today_date, cart_name, new_opening_map):
    """
    If today's Restock / Extra Stock row already exists, realign its opening stock
    after a correction to the previous day's Sales Entry while preserving today's
    accumulated added_units and sold_units.
    """
    if db_conn is None:
        return

    with db_conn.session as s:
        row = s.execute(
            text("SELECT id FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :cart;"),
            {"dt": today_date, "cart": cart_name},
        ).fetchone()
        if not row:
            return

        today_id = row[0]
        for code in FLAVOR_CODES:
            item = s.execute(
                text("""
                    SELECT id, added_units, sold_units
                    FROM daily_cart_items
                    WHERE daily_entry_id = :eid AND flavor_code = :code;
                """),
                {"eid": today_id, "code": code},
            ).fetchone()
            if not item:
                continue

            item_id, existing_added, existing_sold = item
            new_opening = int(new_opening_map.get(code, 0))
            existing_added = int(existing_added or 0)
            existing_sold = int(existing_sold or 0)
            new_closing = max(0, new_opening + existing_added - existing_sold)

            s.execute(
                text("""
                    UPDATE daily_cart_items
                    SET opening_units = :opening,
                        closing_units = :closing
                    WHERE id = :id;
                """),
                {"opening": new_opening, "closing": new_closing, "id": item_id},
            )
        s.commit()


def add_today_extra_stock_entry(today_date, cart_name, extra_map, staff_name=""):
    """Add Extra Stock incrementally to today's existing added_units / closing_units."""
    if db_conn is None:
        return

    prev_closings, prev_staff = get_latest_cart_closing_state(cart_name, today_date)
    staff_to_use = str(staff_name or prev_staff or "").strip()

    with db_conn.session as s:
        row = s.execute(
            text("SELECT id, staff_name FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :cart;"),
            {"dt": today_date, "cart": cart_name},
        ).fetchone()

        if row:
            today_id = row[0]
            if staff_to_use:
                s.execute(
                    text("UPDATE daily_cart_entries SET staff_name = COALESCE(NULLIF(:st, ''), staff_name) WHERE id = :id;"),
                    {"st": staff_to_use, "id": today_id},
                )
        else:
            ins = s.execute(
                text("""
                    INSERT INTO daily_cart_entries
                    (entry_date, cart_name, city, staff_name, total_collection, phonepe, cash,
                     staff_advance, food_tea_cash, cash_leakage_explained,
                     cash_leakage_unexplained, cash_leakage, remarks)
                    VALUES
                    (:dt, :cart, :city, :st, 0, 0, 0, 0, 0, 0, 0, 0, '')
                    RETURNING id;
                """),
                {"dt": today_date, "cart": cart_name, "city": get_location_for_cart(cart_name), "st": staff_to_use or None},
            )
            today_id = ins.scalar()

        for code in FLAVOR_CODES:
            extra_units = int(extra_map.get(code, 0) or 0)
            existing = s.execute(
                text("""
                    SELECT id, opening_units, added_units, sold_units, closing_units
                    FROM daily_cart_items
                    WHERE daily_entry_id = :eid AND flavor_code = :code;
                """),
                {"eid": today_id, "code": code},
            ).fetchone()

            if existing:
                if extra_units <= 0:
                    continue
                item_id, opening_units, added_units, sold_units, closing_units = existing
                opening_units = int(opening_units or 0)
                added_units = int(added_units or 0)
                sold_units = int(sold_units or 0)
                current_closing = (
                    int(closing_units)
                    if closing_units is not None
                    else max(0, opening_units + added_units - sold_units)
                )
                s.execute(
                    text("""
                        UPDATE daily_cart_items
                        SET added_units = :added,
                            closing_units = :closing
                        WHERE id = :id;
                    """),
                    {
                        "added": added_units + extra_units,
                        "closing": current_closing + extra_units,
                        "id": item_id,
                    },
                )
            else:
                opening_units = int(prev_closings.get(code, 0))
                s.execute(
                    text("""
                        INSERT INTO daily_cart_items
                        (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
                        VALUES (:eid, :code, :opening, :added, 0, :closing);
                    """),
                    {
                        "eid": today_id,
                        "code": code,
                        "opening": opening_units,
                        "added": extra_units,
                        "closing": opening_units + extra_units,
                    },
                )

        tot_extra_logged = sum(max(0, int(extra_map.get(c, 0) or 0)) for c in FLAVOR_CODES)
        if tot_extra_logged > 0:
            rec_role = "Ops Coordinator" if st.session_state.get("user_role") == "entry" else "Admin"
            s.execute(
                text("""
                    INSERT INTO public.cart_extra_stock_logs (
                        entry_date, cart_name, location, staff_name, daily_entry_id,
                        ml_units, mm_units, ps_units, mn_units, kb_units,
                        bm_units, sg_units, ch_units, ra_units,
                        recorded_by, source_app
                    ) VALUES (
                        :dt, :cart, :loc, :staff, :eid,
                        :ml, :mm, :ps, :mn, :kb,
                        :bm, :sg, :ch, :ra,
                        :recby, 'web app'
                    );
                """),
                {
                    "dt": today_date,
                    "cart": cart_name,
                    "loc": get_location_for_cart(cart_name),
                    "staff": staff_to_use or None,
                    "eid": today_id,
                    "ml": max(0, int(extra_map.get("ML", 0) or 0)),
                    "mm": max(0, int(extra_map.get("MM", 0) or 0)),
                    "ps": max(0, int(extra_map.get("PS", 0) or 0)),
                    "mn": max(0, int(extra_map.get("MN", 0) or 0)),
                    "kb": max(0, int(extra_map.get("KB", 0) or 0)),
                    "bm": max(0, int(extra_map.get("BM", 0) or 0)),
                    "sg": max(0, int(extra_map.get("SG", 0) or 0)),
                    "ch": max(0, int(extra_map.get("CH", 0) or 0)),
                    "ra": max(0, int(extra_map.get("RA", 0) or 0)),
                    "tot": tot_extra_logged,
                    "recby": rec_role,
                }
            )
        s.commit()


def remove_today_cart_stock_to_freezer(today_date, cart_name, return_map, staff_name=""):
    """
    Move unsold cart stock back to Freezer as of today_date:
    - Deducts returned units from today's cart stock (opening_units first, then added_units, and closing_units).
    - Logs the transfer in public.cart_to_freezer_logs so Freezer Analysis ('Frm Cart') adds it to Freezer stock.
    """
    if db_conn is None:
        return 0

    prev_closings, prev_staff = get_latest_cart_closing_state(cart_name, today_date)
    staff_to_use = str(staff_name or prev_staff or "").strip()
    actual_moved_map = {code: 0 for code in FLAVOR_CODES}

    with db_conn.session as s:
        row = s.execute(
            text("SELECT id, staff_name FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :cart;"),
            {"dt": today_date, "cart": cart_name},
        ).fetchone()

        if row:
            today_id = row[0]
            if not staff_to_use and row[1]:
                staff_to_use = str(row[1]).strip()
        else:
            ins = s.execute(
                text("""
                    INSERT INTO daily_cart_entries
                    (entry_date, cart_name, city, staff_name, total_collection, phonepe, cash,
                     staff_advance, food_tea_cash, cash_leakage_explained,
                     cash_leakage_unexplained, cash_leakage, remarks)
                    VALUES
                    (:dt, :cart, :city, :st, 0, 0, 0, 0, 0, 0, 0, 0, '')
                    RETURNING id;
                """),
                {"dt": today_date, "cart": cart_name, "city": get_location_for_cart(cart_name), "st": staff_to_use or None},
            )
            today_id = ins.scalar()

        for code in FLAVOR_CODES:
            req_move = max(0, int(return_map.get(code, 0) or 0))
            existing = s.execute(
                text("""
                    SELECT id, opening_units, added_units, sold_units, closing_units
                    FROM daily_cart_items
                    WHERE daily_entry_id = :eid AND flavor_code = :code;
                """),
                {"eid": today_id, "code": code},
            ).fetchone()

            if existing:
                item_id, opening_units, added_units, sold_units, closing_units = existing
                cur_open = max(0, int(opening_units or 0))
                cur_add = max(0, int(added_units or 0))
                cur_sold = max(0, int(sold_units or 0))
                cur_close = (
                    max(0, int(closing_units))
                    if closing_units is not None
                    else max(0, cur_open + cur_add - cur_sold)
                )
                actual_move = min(req_move, cur_close)
                actual_moved_map[code] = actual_move
                if actual_move <= 0:
                    continue

                deduct_open = min(cur_open, actual_move)
                deduct_add = max(0, actual_move - deduct_open)
                new_open = max(0, cur_open - deduct_open)
                new_add = max(0, cur_add - deduct_add)
                new_close = max(0, cur_close - actual_move)

                s.execute(
                    text("""
                        UPDATE daily_cart_items
                        SET opening_units = :opening,
                            added_units = :added,
                            closing_units = :closing
                        WHERE id = :id;
                    """),
                    {"opening": new_open, "added": new_add, "closing": new_close, "id": item_id},
                )
            else:
                cur_open = max(0, int(prev_closings.get(code, 0)))
                actual_move = min(req_move, cur_open)
                actual_moved_map[code] = actual_move
                new_open = max(0, cur_open - actual_move)
                s.execute(
                    text("""
                        INSERT INTO daily_cart_items
                        (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
                        VALUES (:eid, :code, :opening, 0, 0, :closing);
                    """),
                    {"eid": today_id, "code": code, "opening": new_open, "closing": new_open},
                )

        tot_moved = sum(actual_moved_map.values())
        if tot_moved > 0:
            rec_role = "Ops Coordinator" if st.session_state.get("user_role") == "entry" else "Admin"
            s.execute(
                text("""
                    INSERT INTO public.cart_to_freezer_logs (
                        entry_date, cart_name, location, staff_name, daily_entry_id,
                        ml_units, mm_units, ps_units, mn_units, kb_units,
                        bm_units, sg_units, ch_units, ra_units,
                        recorded_by, source_app
                    ) VALUES (
                        :dt, :cart, :loc, :staff, :eid,
                        :ml, :mm, :ps, :mn, :kb,
                        :bm, :sg, :ch, :ra,
                        :recby, 'web app'
                    );
                """),
                {
                    "dt": today_date,
                    "cart": cart_name,
                    "loc": get_location_for_cart(cart_name),
                    "staff": staff_to_use or None,
                    "eid": today_id,
                    "ml": int(actual_moved_map.get("ML", 0)),
                    "mm": int(actual_moved_map.get("MM", 0)),
                    "ps": int(actual_moved_map.get("PS", 0)),
                    "mn": int(actual_moved_map.get("MN", 0)),
                    "kb": int(actual_moved_map.get("KB", 0)),
                    "bm": int(actual_moved_map.get("BM", 0)),
                    "sg": int(actual_moved_map.get("SG", 0)),
                    "ch": int(actual_moved_map.get("CH", 0)),
                    "ra": int(actual_moved_map.get("RA", 0)),
                    "recby": rec_role,
                },
            )
        s.commit()
    return sum(actual_moved_map.values())


@st.dialog("❄️ Confirm Move Back to Freezer", width="small")
def confirm_move_cart_to_freezer_modal(today_date, cart_name, return_map, staff_name=""):
    tot_units = sum(max(0, int(v or 0)) for v in return_map.values())
    flv_lines = [
        f"<b>{escape(FLAVOR_MAP[c]['name'])} ({c})</b>: {int(return_map.get(c, 0))} pcs"
        for c in FLAVOR_CODES
        if int(return_map.get(c, 0) or 0) > 0
    ]
    st.markdown(
        f"""
        <div style='background:#F8FAFC;border:1.5px solid #CBD5E1;border-radius:10px;padding:12px 14px;margin-bottom:12px;'>
            <div style='font-weight:900;color:#1E2252;font-size:14px;margin-bottom:4px;'>
                Move {tot_units} pcs from {escape(cart_name)} back to Freezer?
            </div>
            <div style='font-size:12px;color:#475569;margin-bottom:8px;'>
                Date: <b>{today_date.strftime('%d-%b-%Y')}</b> &nbsp;|&nbsp; Staff: <b>{escape(staff_name or '—')}</b>
            </div>
            <div style='font-size:12px;color:#047857;line-height:1.5;'>
                {" &nbsp;•&nbsp; ".join(flv_lines)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("This will reduce today's stock in the selected cart and add these units to Freezer stock ('Frm Cart').")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅ Yes, Move to Freezer", type="primary", use_container_width=True, key="confirm_move_cart_fzr_yes"):
            try:
                moved_cnt = remove_today_cart_stock_to_freezer(today_date, cart_name, return_map, staff_name)
                for code in FLAVOR_CODES:
                    st.session_state[f"rm_cart_stock_{cart_name}_{code}"] = "0"
                st.session_state[f"rm_cart_empty_fill_{cart_name}"] = {}
                st.cache_data.clear()
                st.session_state["_rm_cart_success_msg"] = f"Moved {moved_cnt} units from {cart_name} back to Freezer!"
                st.rerun()
            except Exception as e:
                st.error(f"Could not move stock to Freezer: {e}")
    with c2:
        if st.button("Cancel", use_container_width=True, key="confirm_move_cart_fzr_no"):
            st.rerun()

def load_db_daily_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT e.entry_date AS "Date", e.cart_name AS "Cart", e.total_collection AS "Total_Collection", 
           e.phonepe AS "PhonePe", e.cash AS "Cash", e.staff_name AS "Staff_Name", 
           e.staff_advance AS "Staff_Advance", e.food_tea_cash AS "Food_Tea_Cash",
           e.cash_leakage_explained AS "Cash_Leakage_Explained",
           e.cash_leakage_unexplained AS "Cash_Leakage_Unexplained",
           e.cash_leakage AS "Cash_Leakage", e.remarks AS "Remarks", 
           COALESCE(SUM(i.sold_units), 0) AS "Sold_Total", 
           COALESCE(SUM(i.closing_units), 0) AS "Closing_Total"
    FROM daily_cart_entries e 
    LEFT JOIN daily_cart_items i ON e.id = i.daily_entry_id
    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :active_loc)
      AND LOWER(TRIM(COALESCE(e.cart_name, ''))) NOT LIKE '%test%'
    GROUP BY e.id, e.entry_date, e.cart_name, e.total_collection, e.phonepe, e.cash, 
             e.staff_name, e.staff_advance, e.food_tea_cash,
             e.cash_leakage_explained, e.cash_leakage_unexplained, e.cash_leakage, e.remarks 
    ORDER BY e.entry_date DESC;
    """
    df = db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
    if not df.empty: df["Date"] = pd.to_datetime(df["Date"])
    return df

def load_db_flavor_sales(start_date=None, end_date=None, allowed_carts=None):
    if db_conn is None: return pd.DataFrame()
    if allowed_carts is not None:
        _norm_carts = [str(c).strip().upper() for c in allowed_carts if str(c).strip()]
        if not _norm_carts:
            return pd.DataFrame()
    else:
        _norm_carts = None
    where_clauses, params = ["LOWER(TRIM(COALESCE(e.cart_name, ''))) NOT LIKE '%test%'"], {}
    active_loc = get_active_location_filter()
    if active_loc != "ALL":
        where_clauses.append("UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :active_loc")
        params["active_loc"] = active_loc
    if start_date: where_clauses.append("e.entry_date >= :sdate"); params["sdate"] = start_date
    if end_date: where_clauses.append("e.entry_date <= :edate"); params["edate"] = end_date
    if _norm_carts is not None:
        _c_placeholders = []
        for _ci, _cn in enumerate(_norm_carts):
            _pk = f"ac_{_ci}"
            _c_placeholders.append(f":{_pk}")
            params[_pk] = _cn
        where_clauses.append(f"UPPER(TRIM(COALESCE(e.cart_name, ''))) IN ({', '.join(_c_placeholders)})")
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    query = f"""
    SELECT f.code, f.name AS "Flavour", f.mrp, f.cost_price, COALESCE(SUM(i.sold_units), 0) AS "Units sold", COALESCE(SUM(i.sold_units), 0) * f.mrp AS "Est. revenue (₹)", COALESCE(SUM(i.sold_units), 0) * f.cost_price AS "COGS (₹)"
    FROM flavors f LEFT JOIN daily_cart_items i ON f.code = i.flavor_code LEFT JOIN daily_cart_entries e ON i.daily_entry_id = e.id {where_sql}
    GROUP BY f.code, f.name, f.mrp, f.cost_price ORDER BY "Units sold" DESC;
    """
    return db_conn.query(query, params=params, ttl="60s")

def apply_smart_filters(df, filter_columns, key_prefix):
    """Apply a small set of useful filters without cluttering every table."""
    if df is None or df.empty or not filter_columns:
        return df
    valid = [c for c in filter_columns if c in df.columns]
    if not valid:
        return df
    with st.expander("🔎 Filters", expanded=False):
        cols = st.columns(len(valid))
        filtered = df.copy()
        for i, col in enumerate(valid):
            values = filtered[col].dropna().astype(str).str.strip()
            values = sorted([v for v in values.unique().tolist() if v])
            with cols[i]:
                selected = st.selectbox(col, ["All"] + values, key=f"{key_prefix}_{i}")
            if selected != "All":
                filtered = filtered[filtered[col].fillna("").astype(str).str.strip() == selected]
        st.caption(f"Showing {len(filtered):,} of {len(df):,} rows")
        return filtered
    return df

def load_db_expenses_list():
    if db_conn is None: return []
    query = """
    SELECT id, expense_date AS "Date", month AS "Month", description AS "Description", total_amount AS "Amount", category AS "Category", sub_category AS "Sub_Category", expense_type AS "Expense_Type", attributed_to AS "Attributed_To", vendor_name AS "Vendor", staff_name AS "Staff_Name", status AS "Status", remarks AS "Remarks"
    FROM expenses WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc) ORDER BY expense_date DESC, id DESC;
    """
    try:
        df = db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
        if df.empty: return []
        df["Date"] = pd.to_datetime(df["Date"])
        df["Amount"] = df["Amount"].astype(float)
        return df.to_dict("records")
    except Exception: return []

def load_ops_cash_spend_entries_df():
    if db_conn is None:
        return pd.DataFrame()
    query = """
    SELECT
        s.id,
        s.spend_date,
        s.amount,
        COALESCE(s.allocated_amount, 0) AS allocated_amount,
        GREATEST(s.amount - COALESCE(s.allocated_amount, 0), 0) AS remaining_amount,
        s.notes,
        s.batch_id,
        COALESCE(s.spent_by, 'OPS_COORDINATOR') AS spent_by,
        s.created_at,
        e.id AS linked_expense_id,
        e.category AS linked_expense_category,
        e.sub_category AS linked_expense_subcategory
    FROM public.cash_ops_spend_entries s
    LEFT JOIN LATERAL (
        SELECT id, category, sub_category
        FROM public.expenses
        WHERE remarks ILIKE ('%[Ops Cash Spend #' || s.id::text || ']%')
           OR remarks ILIKE ('%[Admin 1 Cash Spend #' || s.id::text || ']%')
        ORDER BY id DESC
        LIMIT 1
    ) e ON true
    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc)
    ORDER BY s.spend_date DESC, s.id DESC;
    """
    try:
        return db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
    except Exception:
        return pd.DataFrame()


def load_db_expenses_summary_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT e.id, e.expense_date, e.month, e.expense_type, e.category, e.sub_category, e.description, e.total_amount, e.attributed_to, e.vendor_name, e.staff_name, e.purchase_order_id, e.status, e.remarks, COALESCE(SUM(p.amount_paid), 0) AS total_paid, e.total_amount - COALESCE(SUM(p.amount_paid), 0) AS balance_due, COUNT(p.id) AS payment_count
    FROM expenses e LEFT JOIN expense_payments p ON e.id = p.expense_id
    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.location, 'HOSUR'))) = :active_loc)
    GROUP BY e.id, e.expense_date, e.expense_type, e.category, e.sub_category, e.description, e.total_amount, e.attributed_to, e.vendor_name, e.staff_name, e.purchase_order_id, e.status, e.remarks ORDER BY e.expense_date DESC, e.id DESC;
    """
    try: return db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
    except Exception: return pd.DataFrame()

def prepare_payment_receipt(uploaded_file):
    """Return nullable receipt metadata + Base64 for an optional payment image."""
    if uploaded_file is None:
        return {
            "name": None,
            "mime": None,
            "size": None,
            "base64": None,
            "uploaded_at": None,
        }

    raw = uploaded_file.getvalue()
    max_bytes = int(3.5 * 1024 * 1024)
    if len(raw) > max_bytes:
        raise ValueError("Receipt / bill image must be 3.5 MB or smaller.")

    mime = str(getattr(uploaded_file, "type", "") or "").lower().strip()
    allowed_mimes = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if mime not in allowed_mimes:
        raise ValueError("Receipt / bill must be a JPG, JPEG, PNG or WEBP image.")

    return {
        "name": str(getattr(uploaded_file, "name", "") or "receipt-image"),
        "mime": mime,
        "size": int(len(raw)),
        "base64": base64.b64encode(raw).decode("ascii"),
        "uploaded_at": datetime.now(),
    }


def load_db_payments_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT p.id, p.expense_id, p.payment_date, p.amount_paid, p.payment_mode, p.ref_no, p.paid_to, p.paid_by, p.notes,
           p.receipt_file_name, p.receipt_mime_type, p.receipt_file_size_bytes, p.receipt_uploaded_at,
           e.category, e.sub_category, e.description AS expense_desc, e.total_amount AS expense_total, e.staff_name
    FROM expense_payments p JOIN expenses e ON p.expense_id = e.id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.location, 'HOSUR'))) = :active_loc) ORDER BY p.payment_date DESC, p.id DESC;
    """
    try: return db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
    except Exception: return pd.DataFrame()

def get_db_stock_removed_map():
    if db_conn is None: return {c: 0 for c in FLAVOR_CODES}
    query = """
    SELECT 
        COALESCE(SUM(ml_units), 0) AS ml_units, COALESCE(SUM(mm_units), 0) AS mm_units, 
        COALESCE(SUM(ps_units), 0) AS ps_units, COALESCE(SUM(mn_units), 0) AS mn_units, 
        COALESCE(SUM(kb_units), 0) AS kb_units, COALESCE(SUM(bm_units), 0) AS bm_units, 
        COALESCE(SUM(sg_units), 0) AS sg_units, COALESCE(SUM(ch_units), 0) AS ch_units, 
        COALESCE(SUM(ra_units), 0) AS ra_units 
    FROM stock_removed WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc);
    """
    try:
        df = db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
        if not df.empty:
            r = df.iloc[0]
            return {code: int(r.get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES}
    except Exception:
        pass
    return {code: 0 for code in FLAVOR_CODES}

def get_freezer_asset_name_for_location(loc_code=None):
    loc = str(loc_code or get_default_write_city()).strip().upper()
    if db_conn is not None:
        try:
            df = db_conn.query(
                "SELECT asset_name FROM public.location_assets WHERE is_active = true AND asset_type = 'FREEZER' AND UPPER(TRIM(location_code)) = :loc ORDER BY sort_order ASC, asset_name ASC LIMIT 1;",
                params={"loc": loc},
                ttl="10m"
            )
            if not df.empty and str(df.iloc[0]["asset_name"]).strip():
                return str(df.iloc[0]["asset_name"]).strip()
        except Exception:
            pass
    return "Freezer" if loc == "HOSUR" else f"{loc} FREEZER"

def is_freezer_cart_name_sql(col_expr="e.cart_name"):
    return f"(UPPER(TRIM(COALESCE({col_expr}, ''))) LIKE '%FREEZER%' OR UPPER(TRIM(COALESCE({col_expr}, ''))) IN (SELECT UPPER(TRIM(asset_name)) FROM public.location_assets WHERE asset_type = 'FREEZER'))"

def sync_freezer_sale_entry(sale_date, freezer_name, staff_name, sold_map, total_val, phonepe_val, cash_val, leakage_val, reason_text):
    web_tag = "[Freezer Sale] [web app]"
    clean_reason = str(reason_text or "").strip()
    leakage_val = max(0.0, float(leakage_val or 0.0))

    if db_conn is not None:
        with db_conn.session as s:
            existing_row = s.execute(
                text("""
                SELECT id, total_collection, phonepe, cash, cash_leakage, remarks
                FROM daily_cart_entries
                WHERE entry_date = :dt AND cart_name = :cart
                FOR UPDATE;
                """),
                {"dt": sale_date, "cart": freezer_name}
            ).fetchone()

            existing_sold_by_code = {}
            if existing_row:
                prev_id = int(existing_row[0])
                prev_tot = float(existing_row[1] or 0.0)
                prev_ph = float(existing_row[2] or 0.0)
                prev_cs = float(existing_row[3] or 0.0)
                prev_lk = float(existing_row[4] or 0.0)
                prev_rem_raw = str(existing_row[5] or "")
                prev_rem_clean = re.sub(r"\[(?:Freezer Sale|web app|mobile app)\]", "", prev_rem_raw, flags=re.IGNORECASE).strip()

                item_rows = s.execute(
                    text("SELECT flavor_code, sold_units FROM daily_cart_items WHERE daily_entry_id = :eid;"),
                    {"eid": prev_id}
                ).fetchall()
                for ir in item_rows:
                    existing_sold_by_code[str(ir[0]).strip()] = int(ir[1] or 0)
            else:
                prev_tot, prev_ph, prev_cs, prev_lk, prev_rem_clean = 0.0, 0.0, 0.0, 0.0, ""

            combined_tot = prev_tot + float(total_val or 0.0)
            combined_ph = prev_ph + float(phonepe_val or 0.0)
            combined_cs = prev_cs + float(cash_val or 0.0)
            combined_lk = prev_lk + leakage_val
            combined_reason = " | ".join([r for r in (prev_rem_clean, clean_reason) if r])
            remarks_text = f"{combined_reason} {web_tag}".strip() if combined_reason else web_tag

            res = s.execute(
                text("""
                INSERT INTO daily_cart_entries (
                    entry_date, cart_name, city, staff_name, total_collection, phonepe, cash,
                    staff_advance, food_tea_cash, cash_leakage_explained, cash_leakage_unexplained,
                    cash_leakage, remarks
                ) VALUES (
                    :dt, :cart, :city, :staff, :tot, :ph, :cash,
                    0, 0, :leak, 0, :leak, :rem
                )
                ON CONFLICT (entry_date, cart_name) DO UPDATE
                SET staff_name = EXCLUDED.staff_name,
                    total_collection = EXCLUDED.total_collection,
                    phonepe = EXCLUDED.phonepe,
                    cash = EXCLUDED.cash,
                    cash_leakage_explained = EXCLUDED.cash_leakage_explained,
                    cash_leakage_unexplained = 0,
                    cash_leakage = EXCLUDED.cash_leakage,
                    remarks = EXCLUDED.remarks
                RETURNING id;
                """),
                {
                    "dt": sale_date,
                    "cart": freezer_name,
                    "city": CITY,
                    "staff": staff_name or None,
                    "tot": combined_tot,
                    "ph": combined_ph,
                    "cash": combined_cs,
                    "leak": combined_lk,
                    "rem": remarks_text,
                }
            )
            daily_id = res.scalar()

            s.execute(text("DELETE FROM daily_cart_items WHERE daily_entry_id = :id;"), {"id": daily_id})
            for code in FLAVOR_CODES:
                new_sold_qty = int(existing_sold_by_code.get(code, 0)) + max(0, int(sold_map.get(code, 0)))
                s.execute(
                    text("""
                    INSERT INTO daily_cart_items (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
                    VALUES (:eid, :code, 0, 0, :sold, 0);
                    """),
                    {"eid": daily_id, "code": code, "sold": new_sold_qty}
                )

            # Log this individual transaction into public.freezer_sale_transactions
            tot_units_txn = sum(max(0, int(sold_map.get(c, 0))) for c in FLAVOR_CODES)
            rec_role = "Ops Coordinator" if st.session_state.get("user_role") == "entry" else "Admin"
            s.execute(
                text("""
                INSERT INTO public.freezer_sale_transactions (
                    sale_date, freezer_name, location, sold_by, daily_entry_id,
                    ml_units, mm_units, ps_units, mn_units, kb_units,
                    bm_units, sg_units, ch_units, ra_units,
                    total_units, total_value, phonepe, cash, leakage,
                    reason, recorded_by, source_app
                ) VALUES (
                    :dt, :fname, :loc, :staff, :eid,
                    :ml, :mm, :ps, :mn, :kb,
                    :bm, :sg, :ch, :ra,
                    :tunits, :tval, :ph, :cs, :lk,
                    :reason, :recby, 'web app'
                );
                """),
                {
                    "dt": sale_date,
                    "fname": freezer_name,
                    "loc": CITY,
                    "staff": staff_name or None,
                    "eid": daily_id,
                    "ml": max(0, int(sold_map.get("ML", 0))),
                    "mm": max(0, int(sold_map.get("MM", 0))),
                    "ps": max(0, int(sold_map.get("PS", 0))),
                    "mn": max(0, int(sold_map.get("MN", 0))),
                    "kb": max(0, int(sold_map.get("KB", 0))),
                    "bm": max(0, int(sold_map.get("BM", 0))),
                    "sg": max(0, int(sold_map.get("SG", 0))),
                    "ch": max(0, int(sold_map.get("CH", 0))),
                    "ra": max(0, int(sold_map.get("RA", 0))),
                    "tunits": tot_units_txn,
                    "tval": float(total_val or 0.0),
                    "ph": float(phonepe_val or 0.0),
                    "cs": float(cash_val or 0.0),
                    "lk": leakage_val,
                    "reason": clean_reason or None,
                    "recby": rec_role,
                }
            )

            s.execute(text("DELETE FROM expenses WHERE remarks LIKE :tag;"), {"tag": f"[Auto: Daily Entry #{daily_id}]%"})
            if combined_lk > 0.001:
                s.execute(
                    text("""
                    INSERT INTO expenses (
                        expense_date, month, location, expense_type, category, sub_category,
                        description, total_amount, attributed_to, vendor_name,
                        staff_name, status, recorded_by, remarks
                    ) VALUES (
                        :ed, :mo, :loc, 'OPEX', 'Leakage Expense', 'Cash Leakage',
                        :desc, :amt, :attr, NULL, :staff, 'Not Applicable', 'Freezer Sale Auto', :rem
                    );
                    """),
                    {
                        "ed": sale_date,
                        "mo": list(calendar.month_name)[sale_date.month],
                        "loc": get_location_for_cart(freezer_name),
                        "desc": f"Freezer Sale Leakage ({freezer_name}): {combined_reason}" if combined_reason else f"Freezer Sale Leakage ({freezer_name})",
                        "amt": float(combined_lk),
                        "attr": "Central / Freezer",
                        "staff": staff_name or None,
                        "rem": f"[Auto: Daily Entry #{daily_id}] Freezer Leakage",
                    }
                )
            s.commit()

def reconcile_freezer_daily_entry(s, sale_date, freezer_name, loc_code=None):
    """Recompute daily_cart_entries + daily_cart_items + auto leakage expense for (sale_date, freezer_name)
    from all remaining rows in public.freezer_sale_transactions."""
    web_tag = "[Freezer Sale] [web app]"
    loc_val = str(loc_code or CITY).strip().upper()

    txns = s.execute(
        text("""
        SELECT id, sold_by, ml_units, mm_units, ps_units, mn_units, kb_units,
               bm_units, sg_units, ch_units, ra_units,
               total_units, total_value, phonepe, cash, leakage, reason
        FROM public.freezer_sale_transactions
        WHERE sale_date = :dt AND freezer_name = :fname
        ORDER BY id ASC;
        """),
        {"dt": sale_date, "fname": freezer_name}
    ).mappings().all()

    existing_entry = s.execute(
        text("SELECT id FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :cart FOR UPDATE;"),
        {"dt": sale_date, "cart": freezer_name}
    ).fetchone()

    if not txns:
        if existing_entry:
            eid = int(existing_entry[0])
            s.execute(text("DELETE FROM expenses WHERE remarks LIKE :tag;"), {"tag": f"[Auto: Daily Entry #{eid}]%"})
            s.execute(text("DELETE FROM daily_cart_items WHERE daily_entry_id = :eid;"), {"eid": eid})
            has_handover = s.execute(
                text("SELECT 1 FROM public.cash_handover_items WHERE daily_entry_id = :eid LIMIT 1;"),
                {"eid": eid}
            ).fetchone()
            if has_handover:
                s.execute(
                    text("""
                    UPDATE daily_cart_entries
                    SET total_collection = 0, phonepe = 0, cash = 0,
                        cash_leakage_explained = 0, cash_leakage_unexplained = 0,
                        cash_leakage = 0, remarks = '[Freezer Sale Cleared]'
                    WHERE id = :eid;
                    """),
                    {"eid": eid}
                )
            else:
                s.execute(text("DELETE FROM daily_cart_entries WHERE id = :eid;"), {"eid": eid})
        return None

    sum_tot = sum(float(r["total_value"] or 0.0) for r in txns)
    sum_ph = sum(float(r["phonepe"] or 0.0) for r in txns)
    sum_cs = sum(float(r["cash"] or 0.0) for r in txns)
    sum_lk = sum(float(r["leakage"] or 0.0) for r in txns)
    latest_staff = next((str(r["sold_by"]).strip() for r in reversed(txns) if r.get("sold_by")), None)
    reasons_list = [str(r["reason"]).strip() for r in txns if r.get("reason") and str(r["reason"]).strip()]
    combined_reason = " | ".join(reasons_list)
    remarks_text = f"{combined_reason} {web_tag}".strip() if combined_reason else web_tag

    res = s.execute(
        text("""
        INSERT INTO daily_cart_entries (
            entry_date, cart_name, city, staff_name, total_collection, phonepe, cash,
            staff_advance, food_tea_cash, cash_leakage_explained, cash_leakage_unexplained,
            cash_leakage, remarks
        ) VALUES (
            :dt, :cart, :city, :staff, :tot, :ph, :cash,
            0, 0, :leak, 0, :leak, :rem
        )
        ON CONFLICT (entry_date, cart_name) DO UPDATE
        SET staff_name = EXCLUDED.staff_name,
            total_collection = EXCLUDED.total_collection,
            phonepe = EXCLUDED.phonepe,
            cash = EXCLUDED.cash,
            cash_leakage_explained = EXCLUDED.cash_leakage_explained,
            cash_leakage_unexplained = 0,
            cash_leakage = EXCLUDED.cash_leakage,
            remarks = EXCLUDED.remarks
        RETURNING id;
        """),
        {
            "dt": sale_date,
            "cart": freezer_name,
            "city": loc_val,
            "staff": latest_staff,
            "tot": sum_tot,
            "ph": sum_ph,
            "cash": sum_cs,
            "leak": sum_lk,
            "rem": remarks_text,
        }
    )
    daily_id = int(res.scalar())

    s.execute(text("DELETE FROM daily_cart_items WHERE daily_entry_id = :id;"), {"id": daily_id})
    for code in FLAVOR_CODES:
        col_name = FLAVOR_MAP[code]["audit_col"]
        code_qty = sum(max(0, int(r.get(col_name) or 0)) for r in txns)
        s.execute(
            text("""
            INSERT INTO daily_cart_items (daily_entry_id, flavor_code, opening_units, added_units, sold_units, closing_units)
            VALUES (:eid, :code, 0, 0, :sold, 0);
            """),
            {"eid": daily_id, "code": code, "sold": code_qty}
        )

    s.execute(
        text("UPDATE public.freezer_sale_transactions SET daily_entry_id = :eid WHERE sale_date = :dt AND freezer_name = :fname;"),
        {"eid": daily_id, "dt": sale_date, "fname": freezer_name}
    )

    s.execute(text("DELETE FROM expenses WHERE remarks LIKE :tag;"), {"tag": f"[Auto: Daily Entry #{daily_id}]%"})
    if sum_lk > 0.001:
        s.execute(
            text("""
            INSERT INTO expenses (
                expense_date, month, location, expense_type, category, sub_category,
                description, total_amount, attributed_to, vendor_name,
                staff_name, status, recorded_by, remarks
            ) VALUES (
                :ed, :mo, :loc, 'OPEX', 'Leakage Expense', 'Cash Leakage',
                :desc, :amt, :attr, NULL, :staff, 'Not Applicable', 'Freezer Sale Auto', :rem
            );
            """),
            {
                "ed": sale_date,
                "mo": list(calendar.month_name)[sale_date.month],
                "loc": loc_val,
                "desc": f"Freezer Sale Leakage ({freezer_name}): {combined_reason}" if combined_reason else f"Freezer Sale Leakage ({freezer_name})",
                "amt": float(sum_lk),
                "attr": "Central / Freezer",
                "staff": latest_staff,
                "rem": f"[Auto: Daily Entry #{daily_id}] Freezer Leakage",
            }
        )
    return daily_id


def update_freezer_sale_transaction(txn_id, new_sale_date, freezer_name, staff_name, sold_map, total_val, phonepe_val, cash_val, leakage_val, reason_text):
    if db_conn is None:
        return
    clean_reason = str(reason_text or "").strip()
    leakage_val = max(0.0, float(leakage_val or 0.0))
    tot_units = sum(max(0, int(sold_map.get(c, 0))) for c in FLAVOR_CODES)

    with db_conn.session as s:
        old_row = s.execute(
            text("SELECT sale_date, freezer_name, location FROM public.freezer_sale_transactions WHERE id = :tid FOR UPDATE;"),
            {"tid": int(txn_id)}
        ).fetchone()
        if not old_row:
            raise ValueError(f"Freezer sale transaction #{txn_id} was not found.")
        old_date = pd.to_datetime(old_row[0]).date()
        old_freezer = str(old_row[1] or freezer_name)
        old_loc = str(old_row[2] or CITY)

        s.execute(
            text("""
            UPDATE public.freezer_sale_transactions
            SET sale_date = :dt,
                freezer_name = :fname,
                sold_by = :staff,
                ml_units = :ml, mm_units = :mm, ps_units = :ps, mn_units = :mn, kb_units = :kb,
                bm_units = :bm, sg_units = :sg, ch_units = :ch, ra_units = :ra,
                total_units = :tunits,
                total_value = :tval,
                phonepe = :ph,
                cash = :cs,
                leakage = :lk,
                reason = :reason
            WHERE id = :tid;
            """),
            {
                "tid": int(txn_id),
                "dt": new_sale_date,
                "fname": freezer_name,
                "staff": staff_name or None,
                "ml": max(0, int(sold_map.get("ML", 0))),
                "mm": max(0, int(sold_map.get("MM", 0))),
                "ps": max(0, int(sold_map.get("PS", 0))),
                "mn": max(0, int(sold_map.get("MN", 0))),
                "kb": max(0, int(sold_map.get("KB", 0))),
                "bm": max(0, int(sold_map.get("BM", 0))),
                "sg": max(0, int(sold_map.get("SG", 0))),
                "ch": max(0, int(sold_map.get("CH", 0))),
                "ra": max(0, int(sold_map.get("RA", 0))),
                "tunits": tot_units,
                "tval": float(total_val or 0.0),
                "ph": float(phonepe_val or 0.0),
                "cs": float(cash_val or 0.0),
                "lk": leakage_val,
                "reason": clean_reason or None,
            }
        )

        if old_date != new_sale_date or old_freezer != freezer_name:
            reconcile_freezer_daily_entry(s, old_date, old_freezer, old_loc)
        reconcile_freezer_daily_entry(s, new_sale_date, freezer_name, old_loc)
        s.commit()


def delete_freezer_sale_transaction(txn_id):
    if db_conn is None:
        return
    with db_conn.session as s:
        old_row = s.execute(
            text("SELECT sale_date, freezer_name, location FROM public.freezer_sale_transactions WHERE id = :tid FOR UPDATE;"),
            {"tid": int(txn_id)}
        ).fetchone()
        if not old_row:
            return
        old_date = pd.to_datetime(old_row[0]).date()
        old_freezer = str(old_row[1])
        old_loc = str(old_row[2] or CITY)

        s.execute(text("DELETE FROM public.freezer_sale_transactions WHERE id = :tid;"), {"tid": int(txn_id)})
        reconcile_freezer_daily_entry(s, old_date, old_freezer, old_loc)
        s.commit()


@st.dialog("⚠️ Confirm Delete Freezer Sale")
def confirm_delete_freezer_sale_modal(txn_row):
    tid = int(txn_row["id"])
    t_dt = pd.to_datetime(txn_row["sale_date"]).strftime("%d-%b-%Y")
    st.warning(f"Are you sure you want to permanently delete **Freezer Sale #{tid}**?")
    st.markdown(
        f'''
        <div style="background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;padding:10px 12px;margin-bottom:12px;font-size:13px;">
            <div><b>Date:</b> {t_dt} &nbsp;|&nbsp; <b>Freezer:</b> {escape(str(txn_row.get("freezer_name") or "Freezer"))} &nbsp;|&nbsp; <b>Sold By:</b> {escape(str(txn_row.get("sold_by") or "—"))}</div>
            <div><b>Total Units:</b> {int(txn_row.get("total_units") or 0)} pcs &nbsp;|&nbsp; <b>Total Value:</b> ₹{float(txn_row.get("total_value") or 0):,.0f}</div>
            <div><b>PhonePe:</b> ₹{float(txn_row.get("phonepe") or 0):,.0f} &nbsp;|&nbsp; <b>Cash:</b> ₹{float(txn_row.get("cash") or 0):,.0f} &nbsp;|&nbsp; <b>Leakage:</b> ₹{float(txn_row.get("leakage") or 0):,.0f}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Yes, Delete Freezer Sale", type="primary", use_container_width=True, key=f"confirm_del_fzr_txn_{tid}"):
            try:
                delete_freezer_sale_transaction(tid)
                st.session_state.pop("_editing_freezer_txn_id", None)
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete Freezer sale: {e}")
    with c2:
        if st.button("Cancel", use_container_width=True, key=f"cancel_del_fzr_txn_{tid}"):
            st.rerun()


def load_freezer_sale_transactions_df(start_date=None, end_date=None):
    if db_conn is None:
        return pd.DataFrame()
    where_clauses, params = [], {}
    active_loc = get_active_location_filter()
    if active_loc != "ALL":
        where_clauses.append("UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc")
        params["active_loc"] = active_loc
    if start_date:
        where_clauses.append("sale_date >= :sdate")
        params["sdate"] = start_date
    if end_date:
        where_clauses.append("sale_date <= :edate")
        params["edate"] = end_date
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    try:
        return db_conn.query(
            f"""
            SELECT id, sale_date, freezer_name, location, sold_by,
                   ml_units, mm_units, ps_units, mn_units, kb_units,
                   bm_units, sg_units, ch_units, ra_units,
                   total_units, total_value, phonepe, cash, leakage,
                   reason, recorded_by, source_app, created_at
            FROM public.freezer_sale_transactions
            {where_sql}
            ORDER BY sale_date DESC, id DESC;
            """,
            params=params,
            ttl="60s"
        )
    except Exception:
        return pd.DataFrame()

def get_live_cart_sold_map_for_single_cart(cart_name, target_date):
    """Return {flavor_code: live_sold_units} from mobile live_cart_transactions for (cart_name, target_date)."""
    res = {c: 0 for c in FLAVOR_CODES}
    if db_conn is None or not cart_name or not target_date:
        return res
    try:
        df = db_conn.query(
            """
            SELECT
                i.flavor_code,
                COALESCE(SUM(i.quantity), 0) AS qty_sold
            FROM public.live_transaction_items i
            JOIN public.live_cart_transactions t ON i.transaction_id = t.id
            JOIN public.live_cart_shifts s ON t.shift_id = s.id
            WHERE UPPER(TRIM(s.cart_name)) = UPPER(TRIM(:cart))
              AND (t.created_at AT TIME ZONE 'Asia/Kolkata')::date = :dt
            GROUP BY i.flavor_code;
            """,
            params={"cart": str(cart_name).strip(), "dt": target_date},
            ttl="60s",
        )
        for _, r in df.iterrows():
            code = str(r.get("flavor_code") or "").strip().upper()
            if code in res:
                res[code] = int(_num(r.get("qty_sold")))
    except Exception:
        pass
    return res


def get_live_cart_flavour_tables_for_date(target_date, carts_list=None):
    """
    Return per-cart flavour-wise live sales breakdown for target_date:
    Each cart entry contains staff_name, txn_count, rows (Flavour, MRP, Units Sold, Collection),
    total_units, and total_collection.
    """
    carts_to_show = list(carts_list) if carts_list else list(CARTS)
    cart_data_map = {
        c: {
            "cart": c,
            "staff": "—",
            "txns": 0,
            "qty_by_code": {code: 0 for code in FLAVOR_CODES},
            "rev_by_code": {code: 0.0 for code in FLAVOR_CODES},
            "total_units": 0,
            "total_collection": 0.0,
        }
        for c in carts_to_show
    }
    if db_conn is None or not target_date:
        return cart_data_map

    active_loc = get_active_location_filter()
    try:
        shifts_df = db_conn.query(
            """
            SELECT
                s.cart_name,
                MAX(s.staff_name) AS staff_name,
                COUNT(DISTINCT t.id) AS txn_count,
                COALESCE(SUM(t.total_amount), 0) AS shift_total_amt
            FROM public.live_cart_shifts s
            LEFT JOIN public.live_cart_transactions t
                ON t.shift_id = s.id
                AND (t.created_at AT TIME ZONE 'Asia/Kolkata')::date = :dt
            WHERE (
                (s.created_at AT TIME ZONE 'Asia/Kolkata')::date = :dt
                OR EXISTS (
                    SELECT 1 FROM public.live_cart_transactions tx
                    WHERE tx.shift_id = s.id
                      AND (tx.created_at AT TIME ZONE 'Asia/Kolkata')::date = :dt
                )
            )
              AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc)
            GROUP BY s.cart_name
            ORDER BY s.cart_name ASC;
            """,
            params={"dt": target_date, "active_loc": active_loc},
            ttl="60s",
        )
        for _, srow in shifts_df.iterrows():
            cname = str(srow.get("cart_name") or "").strip()
            if not cname:
                continue
            if cname not in cart_data_map:
                cart_data_map[cname] = {
                    "cart": cname,
                    "staff": "—",
                    "txns": 0,
                    "qty_by_code": {code: 0 for code in FLAVOR_CODES},
                    "rev_by_code": {code: 0.0 for code in FLAVOR_CODES},
                    "total_units": 0,
                    "total_collection": 0.0,
                }
            if pd.notna(srow.get("staff_name")) and str(srow.get("staff_name")).strip():
                cart_data_map[cname]["staff"] = str(srow.get("staff_name")).strip()
            cart_data_map[cname]["txns"] = int(_num(srow.get("txn_count")))

        items_df = db_conn.query(
            """
            SELECT
                s.cart_name,
                i.flavor_code,
                COALESCE(SUM(i.quantity), 0) AS qty_sold,
                COALESCE(SUM(i.subtotal), 0) AS rev_amt
            FROM public.live_transaction_items i
            JOIN public.live_cart_transactions t ON i.transaction_id = t.id
            JOIN public.live_cart_shifts s ON t.shift_id = s.id
            WHERE (t.created_at AT TIME ZONE 'Asia/Kolkata')::date = :dt
              AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc)
            GROUP BY s.cart_name, i.flavor_code;
            """,
            params={"dt": target_date, "active_loc": active_loc},
            ttl="60s",
        )
        for _, irow in items_df.iterrows():
            cname = str(irow.get("cart_name") or "").strip()
            code = str(irow.get("flavor_code") or "").strip().upper()
            if not cname or code not in FLAVOR_CODES:
                continue
            if cname not in cart_data_map:
                cart_data_map[cname] = {
                    "cart": cname,
                    "staff": "—",
                    "txns": 0,
                    "qty_by_code": {c: 0 for c in FLAVOR_CODES},
                    "rev_by_code": {c: 0.0 for c in FLAVOR_CODES},
                    "total_units": 0,
                    "total_collection": 0.0,
                }
            qty = int(_num(irow.get("qty_sold")))
            rev = float(_num(irow.get("rev_amt")))
            if rev <= 0 and qty > 0:
                rev = qty * float(FLAVOR_MAP[code]["mrp"])
            cart_data_map[cname]["qty_by_code"][code] += qty
            cart_data_map[cname]["rev_by_code"][code] += rev

        for cname, cdict in cart_data_map.items():
            cdict["total_units"] = sum(cdict["qty_by_code"].values())
            cdict["total_collection"] = sum(cdict["rev_by_code"].values())
    except Exception:
        pass

    return cart_data_map


def _set_live_flavour_date_state(state_key, target_dt):
    """Callback to update date_input session_state key before widget instantiation."""
    st.session_state[state_key] = target_dt


def render_live_cart_flavour_tables_section(key_prefix="live_flv"):
    """Render date-filtered Live Cart Transactions by Flavour with a separate table for each cart."""
    st.markdown("#### 📱 Live Cart Transactions")
    st.caption("Date-wise live POS sales by cart & flavour")

    dt_key = f"{key_prefix}_selected_date"
    if dt_key not in st.session_state:
        st.session_state[dt_key] = date.today()

    fc1, fc2, fc3, fc4, fc5 = st.columns([1.3, 0.9, 0.9, 0.9, 1.0], gap="small", vertical_alignment="bottom")
    with fc2:
        st.button(
            "📅 Today",
            use_container_width=True,
            key=f"{key_prefix}_btn_today",
            on_click=_set_live_flavour_date_state,
            args=(dt_key, date.today()),
        )
    with fc3:
        st.button(
            "⏪ Yesterday",
            use_container_width=True,
            key=f"{key_prefix}_btn_yest",
            on_click=_set_live_flavour_date_state,
            args=(dt_key, date.today() - timedelta(days=1)),
        )
    with fc4:
        st.button(
            "⏪ Today - 2",
            use_container_width=True,
            key=f"{key_prefix}_btn_t2",
            on_click=_set_live_flavour_date_state,
            args=(dt_key, date.today() - timedelta(days=2)),
        )
    with fc5:
        if st.button("🔄 Refresh", type="primary", use_container_width=True, key=f"{key_prefix}_btn_refresh"):
            st.cache_data.clear()
            st.rerun()
    with fc1:
        sel_live_dt = st.date_input(
            "Select Date",
            key=dt_key,
            max_value=date.today(),
            format="DD-MM-YYYY",
        )

    cart_tables_map = get_live_cart_flavour_tables_for_date(sel_live_dt, CARTS)
    cart_names_list = list(cart_tables_map.keys())

    overall_units = sum(int(cart_tables_map[c]["total_units"]) for c in cart_names_list)
    overall_collection = sum(float(cart_tables_map[c]["total_collection"]) for c in cart_names_list)

    st.markdown(
        f"""
        <div style='background:linear-gradient(90deg, #EFF6FF 0%, #F8FAFC 100%);
                    border:1.5px solid #93C5FD;border-radius:10px;padding:10px 16px;
                    margin:8px 0 14px 0;display:flex;justify-content:space-between;align-items:center;'>
            <div style='font-weight:900;color:#1E2252;font-size:14px;'>
                📅 Live Cart Sales Summary — {sel_live_dt.strftime('%d-%b-%Y')}
            </div>
            <div style='display:flex;gap:22px;align-items:center;'>
                <span style='font-size:13.5px;font-weight:900;color:#C43D17;'>
                    🍦 Overall Units Sold: {overall_units:,} pcs
                </span>
                <span style='font-size:14.5px;font-weight:900;color:#047857;background:#ECFDF5;border:1px solid #6EE7B7;padding:4px 12px;border-radius:8px;'>
                    💰 Overall Total Collection: ₹{overall_collection:,.0f}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Render each cart in a separate table (up to 3 per row for clean side-by-side comparison)
    for row_start in range(0, len(cart_names_list), 3):
        chunk = cart_names_list[row_start:row_start + 3]
        cols = st.columns(len(chunk), gap="medium")
        for idx_c, cname in enumerate(chunk):
            cdata = cart_tables_map[cname]
            staff_lbl = cdata.get("staff") or "—"
            tot_u = int(cdata.get("total_units") or 0)
            tot_col = float(cdata.get("total_collection") or 0.0)

            body_rows_html = []
            for code in FLAVOR_CODES:
                f_info = FLAVOR_MAP[code]
                q_u = int(cdata["qty_by_code"].get(code, 0))
                r_amt = float(cdata["rev_by_code"].get(code, 0.0))
                qty_color = "#C43D17" if q_u > 0 else "#64748B"
                amt_color = "#047857" if r_amt > 0 else "#64748B"
                body_rows_html.append(
                    f"""<tr>
                        <td style='text-align:left;font-weight:800;color:#1E2252;padding:6px 8px;border-bottom:1px solid #E2E8F0;'>{escape(f_info['name'])}</td>
                        <td style='text-align:center;color:#2563EB;font-weight:700;padding:6px 6px;border-bottom:1px solid #E2E8F0;'>₹{float(f_info['mrp']):.0f}</td>
                        <td style='text-align:center;font-weight:900;color:{qty_color};padding:6px 6px;border-bottom:1px solid #E2E8F0;'>{q_u}</td>
                        <td style='text-align:right;font-weight:900;color:{amt_color};padding:6px 8px;border-bottom:1px solid #E2E8F0;'>₹{r_amt:,.0f}</td>
                    </tr>"""
                )

            with cols[idx_c]:
                st.markdown(
                    f"""
                    <div style='background:#FFFFFF;border:1.5px solid #CBD5E1;border-radius:11px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.04);margin-bottom:14px;'>
                        <div style='background:linear-gradient(90deg, #DBEAFE 0%, #BFDBFE 100%);color:#111111;border-bottom:1.5px solid #93C5FD;padding:9px 12px;display:flex;justify-content:space-between;align-items:center;'>
                            <span style='font-weight:900;font-size:13.5px;'>🛒 {escape(cname)}</span>
                            <span style='font-size:11px;font-weight:700;background:rgba(255,255,255,0.18);padding:2px 8px;border-radius:999px;'>
                                Staff: {escape(staff_lbl)}
                            </span>
                        </div>
                        <table style='width:100%;border-collapse:collapse;font-size:12px;'>
                            <thead>
                                <tr style='background:#DBEAFE;color:#1E2252;'>
                                    <th style='text-align:left;padding:7px 8px;font-weight:900;'>Flavour</th>
                                    <th style='text-align:center;padding:7px 6px;font-weight:900;'>MRP</th>
                                    <th style='text-align:center;padding:7px 6px;font-weight:900;'>Units Sold</th>
                                    <th style='text-align:right;padding:7px 8px;font-weight:900;'>Collection</th>
                                </tr>
                            </thead>
                            <tbody>
                                {''.join(body_rows_html)}
                            </tbody>
                            <tfoot>
                                <tr style='background:#EFF6FF;border-top:2px solid #93C5FD;'>
                                    <td colspan='2' style='text-align:left;padding:8px 8px;font-weight:900;color:#1E2252;font-size:12.5px;'>FLAVOUR TOTALS</td>
                                    <td style='text-align:center;padding:8px 6px;font-weight:900;color:#C43D17;font-size:13px;'>{tot_u:,} pcs</td>
                                    <td style='text-align:right;padding:8px 8px;font-weight:900;color:#047857;font-size:13.5px;'>₹{tot_col:,.0f}</td>
                                </tr>
                            </tfoot>
                        </table>
                        <div style='background:#ECFDF5;border-top:1.5px solid #6EE7B7;padding:8px 12px;display:flex;justify-content:space-between;align-items:center;'>
                            <span style='font-size:11.5px;font-weight:900;color:#047857;text-transform:uppercase;'>Total Collection</span>
                            <span style='font-size:15px;font-weight:900;color:#047857;'>₹{tot_col:,.0f}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def delete_stock_received_entry(receipt_id):
    """
    Delete a previously entered Stock Received delivery entry and clean up related tables:
    1. Deletes flavour rows from public.stock_received_items (WHERE received_id = :id)
    2. Cleans up any auto-tagged expense/payment records referencing this receipt if present
    3. Deletes the parent receipt record from public.stock_received (WHERE id = :id)
    """
    if db_conn is None or not receipt_id:
        return
    rid = int(receipt_id)
    with db_conn.session as s:
        s.execute(
            text("DELETE FROM public.stock_received_items WHERE received_id = :rid;"),
            {"rid": rid},
        )
        # Clean up any expense rows explicitly tagged to this Stock Received receipt
        tag_like_1 = f"%[Stock Received #{rid}]%"
        tag_like_2 = f"%[Auto: Stock Received #{rid}]%"
        exp_rows = s.execute(
            text("""
                SELECT id FROM public.expenses
                WHERE remarks ILIKE :t1 OR remarks ILIKE :t2;
            """),
            {"t1": tag_like_1, "t2": tag_like_2},
        ).fetchall()
        for erow in exp_rows:
            eid = int(erow[0])
            pay_rows = s.execute(
                text("SELECT id FROM public.expense_payments WHERE expense_id = :eid;"),
                {"eid": eid},
            ).fetchall()
            for prow in pay_rows:
                pid = int(prow[0])
                try:
                    s.execute(text("DELETE FROM public.expense_payment_receipts WHERE payment_id = :pid;"), {"pid": pid})
                except Exception:
                    pass
            s.execute(text("DELETE FROM public.expense_payments WHERE expense_id = :eid;"), {"eid": eid})
            s.execute(text("DELETE FROM public.expenses WHERE id = :eid;"), {"eid": eid})

        s.execute(
            text("DELETE FROM public.stock_received WHERE id = :rid;"),
            {"rid": rid},
        )
        s.commit()


@st.dialog("🗑️ Confirm Delete Stock Received Entry", width="small")
def confirm_delete_stock_received_modal(receipt_row):
    rid = int(receipt_row["id"])
    rdt = pd.to_datetime(receipt_row["received_date"]).strftime("%d-%b-%Y") if receipt_row.get("received_date") else "—"
    rloc = str(receipt_row.get("location") or CITY)
    raw_items = receipt_row.get("items") if isinstance(receipt_row.get("items"), list) else []
    tot_rec_u = sum(int(itm.get("rec") or 0) for itm in raw_items if isinstance(itm, dict))
    pay_amt = float(_num(receipt_row.get("payment_amount")))

    st.markdown(
        f"""
        <div style='background:#FFF3F0;border:1.5px solid #F3C3B6;border-radius:10px;padding:12px 14px;margin-bottom:12px;'>
            <div style='font-weight:900;color:#C43D17;font-size:14px;margin-bottom:4px;'>
                Permanently delete Stock Receipt #{rid}?
            </div>
            <div style='font-size:12px;color:#1E2252;line-height:1.5;'>
                <b>Received Date:</b> {rdt} &nbsp;|&nbsp; <b>Location:</b> {escape(rloc)}<br/>
                <b>Total Received Units:</b> {tot_rec_u:,} pcs &nbsp;|&nbsp; <b>Payment Amount:</b> ₹{pay_amt:,.2f}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("This will remove the receipt from `stock_received`, delete all its flavour rows from `stock_received_items`, and recalculate Freezer Stock & Freezer Analysis.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🗑️ Yes, Delete Receipt", type="primary", use_container_width=True, key=f"confirm_del_sr_yes_{rid}"):
            try:
                delete_stock_received_entry(rid)
                st.session_state.pop("db_stock_select", None)
                st.cache_data.clear()
                st.session_state["_sr_deleted_msg"] = f"Stock Receipt #{rid} ({tot_rec_u} units on {rdt}) was deleted and Freezer stock was updated."
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete Stock Received entry: {e}")
    with c2:
        if st.button("Cancel", use_container_width=True, key=f"confirm_del_sr_no_{rid}"):
            st.rerun()


def get_db_cart_to_freezer_map(active_loc=None, after_date=None):
    """Return flavour-wise units moved from Cart back to Freezer ('Frm Cart')."""
    res_map = {c: 0 for c in FLAVOR_CODES}
    if db_conn is None:
        return res_map
    loc_val = active_loc if active_loc is not None else get_active_location_filter()
    where_parts = ["(:loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc)"]
    params = {"loc": loc_val}
    if after_date is not None:
        where_parts.append("entry_date > :adate")
        params["adate"] = after_date
    where_sql = " AND ".join(where_parts)
    try:
        df = db_conn.query(
            f"""
            SELECT
                COALESCE(SUM(ml_units), 0) AS ml_units, COALESCE(SUM(mm_units), 0) AS mm_units,
                COALESCE(SUM(ps_units), 0) AS ps_units, COALESCE(SUM(mn_units), 0) AS mn_units,
                COALESCE(SUM(kb_units), 0) AS kb_units, COALESCE(SUM(bm_units), 0) AS bm_units,
                COALESCE(SUM(sg_units), 0) AS sg_units, COALESCE(SUM(ch_units), 0) AS ch_units,
                COALESCE(SUM(ra_units), 0) AS ra_units
            FROM public.cart_to_freezer_logs
            WHERE {where_sql};
            """,
            params=params,
            ttl="60s",
        )
        if not df.empty:
            for code in FLAVOR_CODES:
                res_map[code] = int(_num(df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0)))
    except Exception:
        pass
    return res_map


def get_db_freezer_stock():
    if db_conn is None: return pd.DataFrame(columns=["code", "Units in freezer"])
    try:
        active_loc = get_active_location_filter()
        rec_df = db_conn.query("SELECT ri.flavor_code, SUM(ri.received_units) AS total_recv FROM stock_received_items ri JOIN stock_received r ON r.id = ri.received_id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :active_loc) GROUP BY ri.flavor_code;", params={"active_loc": active_loc}, ttl="60s")
        rec_map = dict(zip(rec_df["flavor_code"], rec_df["total_recv"])) if not rec_df.empty else {}

        frm_cart_map = get_db_cart_to_freezer_map(active_loc=active_loc, after_date=None)

        added_df = db_conn.query("SELECT i.flavor_code, SUM(i.added_units) AS total_added FROM daily_cart_items i JOIN daily_cart_entries e ON e.id = i.daily_entry_id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :active_loc) GROUP BY i.flavor_code;", params={"active_loc": active_loc}, ttl="60s")
        added_map = dict(zip(added_df["flavor_code"], added_df["total_added"])) if not added_df.empty else {}

        fzr_df = db_conn.query(f"SELECT i.flavor_code, COALESCE(SUM(i.sold_units), 0) AS total_fzr_sold FROM daily_cart_items i JOIN daily_cart_entries e ON e.id = i.daily_entry_id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :active_loc) AND {is_freezer_cart_name_sql('e.cart_name')} GROUP BY i.flavor_code;", params={"active_loc": active_loc}, ttl="60s")
        fzr_map = dict(zip(fzr_df["flavor_code"], fzr_df["total_fzr_sold"])) if not fzr_df.empty else {}

        rem_map = get_db_stock_removed_map()
        
        rows = []
        for code in FLAVOR_CODES:
            calc_stock = (
                int(rec_map.get(code, 0))
                + int(frm_cart_map.get(code, 0))
                - int(added_map.get(code, 0))
                - int(fzr_map.get(code, 0))
                - int(rem_map.get(code, 0))
            )
            rows.append({"code": code, "Units in freezer": calc_stock})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame(columns=["code", "Units in freezer"])

def get_physical_current_stock_map(as_of_date=None):
    if db_conn is None:
        return {}
    try:
        active_loc = get_active_location_filter()
        locs_to_calc = load_configured_locations_list(include_inactive=False) if active_loc == "ALL" else [active_loc]
        combined_stock = {code: 0 for code in FLAVOR_CODES}

        for loc_code in locs_to_calc:
            audit_df = db_conn.query(
                "SELECT * FROM stock_audits_wide WHERE UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc ORDER BY audit_date DESC, audit_id DESC LIMIT 1;",
                params={"loc": loc_code},
                ttl="60s"
            )
            if audit_df.empty:
                rec_df = db_conn.query(
                    "SELECT ri.flavor_code, COALESCE(SUM(ri.received_units), 0) AS recv FROM stock_received_items ri JOIN stock_received r ON r.id = ri.received_id WHERE UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :loc GROUP BY ri.flavor_code;",
                    params={"loc": loc_code}, ttl="60s"
                )
                rec_map = dict(zip(rec_df["flavor_code"], rec_df["recv"])) if not rec_df.empty else {}
                frm_cart_map = get_db_cart_to_freezer_map(active_loc=loc_code, after_date=None)
                added_df = db_conn.query(
                    "SELECT i.flavor_code, COALESCE(SUM(i.added_units), 0) AS added FROM daily_cart_items i JOIN daily_cart_entries e ON e.id = i.daily_entry_id WHERE UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc GROUP BY i.flavor_code;",
                    params={"loc": loc_code}, ttl="60s"
                )
                added_map = dict(zip(added_df["flavor_code"], added_df["added"])) if not added_df.empty else {}
                fzr_df = db_conn.query(
                    f"SELECT i.flavor_code, COALESCE(SUM(i.sold_units), 0) AS fzr_sold FROM daily_cart_items i JOIN daily_cart_entries e ON e.id = i.daily_entry_id WHERE UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc AND {is_freezer_cart_name_sql('e.cart_name')} GROUP BY i.flavor_code;",
                    params={"loc": loc_code}, ttl="60s"
                )
                fzr_map = dict(zip(fzr_df["flavor_code"], fzr_df["fzr_sold"])) if not fzr_df.empty else {}
                rem_df = db_conn.query(
                    "SELECT COALESCE(SUM(ml_units),0) AS ml_units, COALESCE(SUM(mm_units),0) AS mm_units, COALESCE(SUM(ps_units),0) AS ps_units, COALESCE(SUM(mn_units),0) AS mn_units, COALESCE(SUM(kb_units),0) AS kb_units, COALESCE(SUM(bm_units),0) AS bm_units, COALESCE(SUM(sg_units),0) AS sg_units, COALESCE(SUM(ch_units),0) AS ch_units, COALESCE(SUM(ra_units),0) AS ra_units FROM stock_removed WHERE UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc;",
                    params={"loc": loc_code}, ttl="60s"
                )
                rem_map = {c: int(rem_df.iloc[0].get(FLAVOR_MAP[c]["audit_col"], 0)) for c in FLAVOR_CODES} if not rem_df.empty else {}
                for code in FLAVOR_CODES:
                    combined_stock[code] += (
                        int(rec_map.get(code, 0))
                        + int(frm_cart_map.get(code, 0))
                        - int(added_map.get(code, 0))
                        - int(fzr_map.get(code, 0))
                        - int(rem_map.get(code, 0))
                    )
                continue

            audit_row = audit_df.iloc[0]
            audit_date = pd.to_datetime(audit_row["audit_date"]).date()
            audit_next_date = audit_date + timedelta(days=1)
            audit_map = {code: int(audit_row.get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES}

            rec_df = db_conn.query("""
                SELECT ri.flavor_code, COALESCE(SUM(ri.received_units), 0) AS recv 
                FROM stock_received_items ri 
                JOIN stock_received r ON ri.received_id = r.id 
                WHERE r.received_date >= :adate
                  AND UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :loc
                GROUP BY ri.flavor_code;
            """, params={"adate": audit_date, "loc": loc_code}, ttl="60s")
            rec_map = dict(zip(rec_df["flavor_code"], rec_df["recv"])) if not rec_df.empty else {}

            frm_cart_map = get_db_cart_to_freezer_map(active_loc=loc_code, after_date=audit_date)

            added_df = db_conn.query("""
                SELECT i.flavor_code, COALESCE(SUM(i.added_units), 0) AS added 
                FROM daily_cart_items i 
                JOIN daily_cart_entries e ON i.daily_entry_id = e.id 
                WHERE e.entry_date >= :anext
                  AND UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc
                GROUP BY i.flavor_code;
            """, params={"anext": audit_next_date, "loc": loc_code}, ttl="60s")
            added_map = dict(zip(added_df["flavor_code"], added_df["added"])) if not added_df.empty else {}

            fzr_df = db_conn.query(f"""
                SELECT i.flavor_code, COALESCE(SUM(i.sold_units), 0) AS fzr_sold
                FROM daily_cart_items i
                JOIN daily_cart_entries e ON i.daily_entry_id = e.id
                WHERE e.entry_date >= :anext
                  AND UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc
                  AND {is_freezer_cart_name_sql('e.cart_name')}
                GROUP BY i.flavor_code;
            """, params={"anext": audit_next_date, "loc": loc_code}, ttl="60s")
            fzr_map = dict(zip(fzr_df["flavor_code"], fzr_df["fzr_sold"])) if not fzr_df.empty else {}

            rem_df = db_conn.query("""
                SELECT 
                    COALESCE(SUM(ml_units), 0) AS ml_units, COALESCE(SUM(mm_units), 0) AS mm_units, 
                    COALESCE(SUM(ps_units), 0) AS ps_units, COALESCE(SUM(mn_units), 0) AS mn_units, 
                    COALESCE(SUM(kb_units), 0) AS kb_units, COALESCE(SUM(bm_units), 0) AS bm_units, 
                    COALESCE(SUM(sg_units), 0) AS sg_units, COALESCE(SUM(ch_units), 0) AS ch_units, 
                    COALESCE(SUM(ra_units), 0) AS ra_units 
                FROM stock_removed 
                WHERE removal_date >= :adate
                  AND UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc;
            """, params={"adate": audit_date, "loc": loc_code}, ttl="60s")
            rem_map = {code: int(rem_df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0)) for code in FLAVOR_CODES} if not rem_df.empty else {code: 0 for code in FLAVOR_CODES}

            for code in FLAVOR_CODES:
                combined_stock[code] += (
                    audit_map.get(code, 0)
                    + int(rec_map.get(code, 0))
                    + int(frm_cart_map.get(code, 0))
                    - int(added_map.get(code, 0))
                    - int(fzr_map.get(code, 0))
                    - int(rem_map.get(code, 0))
                )
        return combined_stock
    except Exception:
        return {}

def load_full_staff_df():
    if db_conn is None: return pd.DataFrame()
    query = """
    SELECT s.id, s.name, s.full_name, s.status, s.phone_number, s.role, s.gender,
           s.emergency_contact_name, s.emergency_contact_phone, s.date_of_birth,
           s.pan_number, s.aadhaar_number, s.current_address, s.permanent_address,
           s.date_of_joining, s.date_of_leaving, s.notes,
           c.monthly_fixed_salary, c.commission_threshold_daily, c.commission_percentage,
           c.allowance_weekday, c.allowance_sunday, c.food_tea_allowance_mode,
           c.monthly_food_tea_allowance, c.monthly_fuel_allowance
    FROM staff s
    LEFT JOIN LATERAL (
        SELECT *
        FROM staff_compensation_plans
        WHERE staff_id = s.id
          AND effective_from <= CURRENT_DATE
          AND (effective_to IS NULL OR effective_to >= CURRENT_DATE)
        ORDER BY effective_from DESC, id DESC
        LIMIT 1
    ) c ON true
    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc)
    ORDER BY s.status ASC, s.name ASC;
    """
    try: return db_conn.query(query, params={"active_loc": get_active_location_filter()}, ttl="60s")
    except Exception: return pd.DataFrame()

def load_staff_comp_plan_as_of(staff_id, as_of_date):
    """Return the compensation plan actually effective for a staff member on a given date."""
    if db_conn is None:
        return None
    try:
        df = db_conn.query(
            """
            SELECT id, staff_id, effective_from, effective_to, monthly_fixed_salary,
                   commission_threshold_daily, commission_percentage,
                   allowance_weekday, allowance_sunday, food_tea_allowance_mode,
                   monthly_food_tea_allowance, monthly_fuel_allowance, created_at
            FROM staff_compensation_plans
            WHERE staff_id = :sid
              AND effective_from <= :as_of
              AND (effective_to IS NULL OR effective_to >= :as_of)
            ORDER BY effective_from DESC, id DESC
            LIMIT 1;
            """,
            params={"sid": int(staff_id), "as_of": as_of_date},
            ttl="60s"
        )
        return None if df.empty else df.iloc[0]
    except Exception:
        return None

def load_staff_compensation_history(staff_id):
    if db_conn is None: return pd.DataFrame()
    try: return db_conn.query("SELECT id, staff_id, effective_from, effective_to, monthly_fixed_salary, commission_threshold_daily, commission_percentage, allowance_weekday, allowance_sunday, food_tea_allowance_mode, monthly_food_tea_allowance, monthly_fuel_allowance, created_at FROM staff_compensation_plans WHERE staff_id = :sid ORDER BY effective_from DESC, id DESC;", params={"sid": staff_id}, ttl="60s")
    except Exception: return pd.DataFrame()

def load_staff_attendance_df(start_date=None, end_date=None):
    if db_conn is None: return pd.DataFrame()
    where_clauses, params = [], {}
    active_loc = get_active_location_filter()
    if active_loc != "ALL":
        where_clauses.append("UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc")
        params["active_loc"] = active_loc
    if start_date: where_clauses.append("a.attendance_date >= :sdate"); params["sdate"] = start_date
    if end_date: where_clauses.append("a.attendance_date <= :edate"); params["edate"] = end_date
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    try: return db_conn.query(f"SELECT a.id, a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type, a.reason, a.recorded_by, a.created_at FROM staff_attendance a JOIN staff s ON a.staff_id = s.id {where_sql} ORDER BY a.attendance_date DESC, a.id DESC;", params=params, ttl="60s")
    except Exception: return pd.DataFrame()

def calculate_incurred_labour_for_range(start_date, end_date, include_cash_leakage=False, limit_to_employment=True, allowed_carts=None):
    if db_conn is None: return 0.0, 0.0, 0.0, {}
    staff_df = load_full_staff_df()
    if staff_df.empty: return 0.0, 0.0, 0.0, {}

    active_loc = get_active_location_filter()
    entries_df = db_conn.query("SELECT entry_date, cart_name, staff_name, total_collection FROM daily_cart_entries WHERE entry_date >= :sdate AND entry_date <= :edate AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc) AND LOWER(TRIM(COALESCE(cart_name, ''))) NOT LIKE '%test%' AND staff_name IS NOT NULL AND staff_name != '' AND staff_name != 'Select Staff';", params={"sdate": start_date, "edate": end_date, "active_loc": active_loc}, ttl="60s")
    att_df = db_conn.query("SELECT a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type FROM staff_attendance a JOIN staff s ON a.staff_id = s.id WHERE a.attendance_date >= :sdate AND a.attendance_date <= :edate AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc);", params={"sdate": start_date, "edate": end_date, "active_loc": active_loc}, ttl="60s")
    pay_df = db_conn.query("""
        SELECT p.amount_paid, p.payment_date, e.staff_name
        FROM expense_payments p
        JOIN expenses e ON p.expense_id = e.id
        WHERE e.category = 'Labour Charges'
          AND p.payment_date >= :sdate
          AND p.payment_date <= :edate
          AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.location, 'HOSUR'))) = :active_loc)
          AND (
              LOWER(TRIM(COALESCE(e.sub_category, ''))) <> 'salary'
              OR LOWER(TRIM(COALESCE(e.month, ''))) = LOWER(:salary_month)
          );
    """, params={"sdate": start_date, "edate": end_date, "salary_month": start_date.strftime('%B'), "active_loc": active_loc}, ttl="60s")

    exp_ledger_df = db_conn.query("""
        SELECT expense_date, staff_name, sub_category, total_amount, month
        FROM expenses
        WHERE category = 'Labour Charges'
          AND status = 'Paid'
          AND expense_date >= :sdate
          AND expense_date <= :edate
          AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
          AND (
              LOWER(TRIM(COALESCE(sub_category, ''))) <> 'salary'
              OR LOWER(TRIM(COALESCE(month, ''))) = LOWER(:salary_month)
          );
    """, params={"sdate": start_date, "edate": end_date, "salary_month": start_date.strftime('%B'), "active_loc": active_loc}, ttl="60s")

    leakage_df = pd.DataFrame()
    if include_cash_leakage:
        leakage_df = db_conn.query("""
            SELECT expense_date, staff_name, total_amount
            FROM expenses
            WHERE LOWER(TRIM(COALESCE(sub_category, ''))) = 'cash leakage'
              AND category = 'Leakage Expense'
              AND expense_date >= :sdate AND expense_date <= :edate
              AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
              AND NULLIF(TRIM(staff_name), '') IS NOT NULL;
        """, params={"sdate": start_date, "edate": end_date, "active_loc": active_loc}, ttl="60s")

    def month_days(d):
        return 30

    def prorate_monthly(monthly_amount, eligible_dates):
        amount = float(_num(monthly_amount))
        return sum(amount / month_days(d) for d in eligible_dates)

    def food_allowance_for_date(mode, monthly_amount, weekday_amount, sunday_amount, d):
        if str(mode).strip().lower() == "daily":
            return float(sunday_amount if d.weekday() == 6 else weekday_amount)
        return float(monthly_amount) / month_days(d)

    def food_allowance_for_dates(mode, monthly_amount, weekday_amount, sunday_amount, eligible_dates):
        return sum(food_allowance_for_date(mode, monthly_amount, weekday_amount, sunday_amount, d) for d in eligible_dates)

    def attach_staff_leakage(staff_name, ledger=None, emp_start=None, emp_end=None):
        if leakage_df.empty:
            return 0.0
        staff_leakage = leakage_df[leakage_df["staff_name"].astype(str).str.strip() == staff_name]
        by_date = {}
        for _, entry in staff_leakage.iterrows():
            day = pd.to_datetime(entry["expense_date"]).date()
            if emp_start is not None and day < emp_start:
                continue
            if emp_end is not None and day > emp_end:
                continue
            by_date[day] = by_date.get(day, 0.0) + float(_num(entry["total_amount"]))
        if ledger is not None:
            for day, amount in by_date.items():
                existing = next((row for row in ledger if row["date"] == day), None)
                if existing is not None:
                    existing["leakage"] = amount
                else:
                    ledger.append({"date": day, "type": "Cash Leakage", "cart": "—",
                                   "collection": 0.0, "fixed_salary": 0.0, "commission": 0.0,
                                   "allowance": 0.0, "advance_taken": 0.0, "food_taken": 0.0,
                                   "leakage": amount})
            ledger.sort(key=lambda row: row["date"])
        return sum(by_date.values())

    all_comp_plans_df = pd.DataFrame()
    try:
        all_comp_plans_df = db_conn.query(
            """
            SELECT id, staff_id, effective_from, effective_to, monthly_fixed_salary,
                   commission_threshold_daily, commission_percentage,
                   allowance_weekday, allowance_sunday, food_tea_allowance_mode,
                   monthly_food_tea_allowance, monthly_fuel_allowance, created_at
            FROM staff_compensation_plans
            ORDER BY staff_id ASC, effective_from DESC, id DESC;
            """,
            ttl="60s",
        )
    except Exception:
        all_comp_plans_df = pd.DataFrame()

    comp_plans_by_staff = {}
    if not all_comp_plans_df.empty:
        for _, _cp in all_comp_plans_df.iterrows():
            _sid = int(_cp["staff_id"])
            _ef = pd.to_datetime(_cp["effective_from"]).date() if pd.notna(_cp.get("effective_from")) else date.min
            _et = pd.to_datetime(_cp["effective_to"]).date() if pd.notna(_cp.get("effective_to")) else None
            comp_plans_by_staff.setdefault(_sid, []).append((_ef, _et, _cp))

    def _get_cached_comp_plan(sid, as_of_dt):
        for _ef, _et, _cp in comp_plans_by_staff.get(int(sid), []):
            if _ef <= as_of_dt and (_et is None or _et >= as_of_dt):
                return _cp
        return None

    total_labour_incurred, total_labour_paid, breakdown_by_staff = 0.0, 0.0, {}

    for _, s_row in staff_df.iterrows():
        st_name = str(s_row["name"]).strip()
        staff_role = str(s_row.get("role") or "Cart Operator").strip()
        role_lower = staff_role.lower()
        doj = s_row.get("date_of_joining")
        leaving = s_row.get("date_of_leaving")

        # Always clamp the active employment window to [date_of_joining, date_of_leaving]
        # so nothing beyond Last Working Day (or before joining) is ever counted in pay calculations.
        employment_start, employment_end = start_date, end_date
        if pd.notna(doj) and str(doj).strip():
            try:
                employment_start = max(start_date, pd.to_datetime(doj).date())
            except Exception:
                pass
        if pd.notna(leaving) and str(leaving).strip():
            try:
                employment_end = min(end_date, pd.to_datetime(leaving).date())
            except Exception:
                pass
        if employment_start > employment_end:
            continue

        # Always use the compensation plan effective for the payroll period rather than
        # merely the newest plan row. This is important when a future revision exists.
        plan_row = _get_cached_comp_plan(int(s_row["id"]), employment_end)
        plan_source = plan_row if plan_row is not None else s_row

        monthly_sal = float(_num(plan_source.get("monthly_fixed_salary")) or 18000.0)
        standard_daily_rate = monthly_sal / 30.0
        comm_thresh = float(_num(plan_source.get("commission_threshold_daily")) or 3000.0)
        comm_pct = float(_num(plan_source.get("commission_percentage")) or 15.0)
        allow_wd = float(_num(plan_source.get("allowance_weekday")))
        allow_sun = float(_num(plan_source.get("allowance_sunday")))
        food_mode = str(plan_source.get("food_tea_allowance_mode") or "monthly").strip().lower()
        if food_mode not in ("daily", "monthly"):
            food_mode = "monthly"
        monthly_food = float(_num(plan_source.get("monthly_food_tea_allowance")))
        monthly_fuel = float(_num(plan_source.get("monthly_fuel_allowance")))

        st_shifts = entries_df[entries_df["staff_name"] == st_name].copy() if not entries_df.empty else pd.DataFrame()
        if not st_shifts.empty:
            sh_dates = pd.to_datetime(st_shifts["entry_date"]).dt.date
            st_shifts = st_shifts[(sh_dates >= employment_start) & (sh_dates <= employment_end)]

        st_leaves = att_df[att_df["staff_name"] == st_name].copy() if not att_df.empty else pd.DataFrame()
        if not st_leaves.empty:
            lv_dates = pd.to_datetime(st_leaves["attendance_date"]).dt.date
            st_leaves = st_leaves[(lv_dates >= employment_start) & (lv_dates <= employment_end)]

        if allowed_carts is not None and role_lower == "cart operator":
            _allowed_upper = {str(c).strip().upper() for c in allowed_carts if str(c).strip()}
            _had_any_shift = not st_shifts.empty
            if not st_shifts.empty:
                st_shifts = st_shifts[st_shifts["cart_name"].fillna("").astype(str).str.strip().str.upper().isin(_allowed_upper)].copy()
            if _had_any_shift and st_shifts.empty:
                st_leaves = st_leaves.iloc[0:0].copy()

        st_pay = pay_df[pay_df["staff_name"] == st_name].copy() if not pay_df.empty else pd.DataFrame()
        if not st_pay.empty and "payment_date" in st_pay.columns:
            py_dates = pd.to_datetime(st_pay["payment_date"]).dt.date
            st_pay = st_pay[(py_dates >= employment_start) & (py_dates <= employment_end)]

        # Non-cart roles are salaried on calendar days. Ops Coordinator has a
        # true monthly pro-rata: the payable period always starts no earlier
        # than Date of Joining and each day uses that calendar month's divisor.
        if role_lower != "cart operator":
            period_start = employment_start
            period_end = min(employment_end, date.today())
            if pd.notna(doj) and str(doj).strip():
                period_start = max(period_start, pd.to_datetime(doj).date())
            if pd.notna(leaving) and str(leaving).strip():
                period_end = min(period_end, pd.to_datetime(leaving).date())

            if period_start > period_end:
                continue

            unpaid_leave_dates, paid_leave_dates = set(), set()
            if not st_leaves.empty:
                for _, l_row in st_leaves.iterrows():
                    l_dt = pd.to_datetime(l_row["attendance_date"]).date()
                    if not (period_start <= l_dt <= period_end):
                        continue
                    l_type = str(l_row.get("leave_type") or "Unpaid").strip().lower()
                    if l_type == "paid":
                        paid_leave_dates.add(l_dt)
                    else:
                        unpaid_leave_dates.add(l_dt)

            period_dates = [period_start + timedelta(days=i) for i in range((period_end - period_start).days + 1)]
            payable_dates = [d for d in period_dates if d not in unpaid_leave_dates]
            worked_dates = [d for d in payable_dates if d not in paid_leave_dates]
            payable_days = len(payable_dates)
            worked_days = len(worked_dates)
            paid_leave_cnt = len([d for d in paid_leave_dates if d in payable_dates])
            unpaid_leave_cnt = len([d for d in unpaid_leave_dates if period_start <= d <= period_end])

            staff_salary = payable_days * standard_daily_rate
            display_daily_rate = standard_daily_rate

            if food_mode == "monthly":
                # Monthly Food Allowance is paid centrally and is not part of an individual payslip.
                food_entitled = 0.0
                # Fuel remains an individual earning for the Ops Coordinator and is
                # pro-rated for actual worked days even when Food/Tea is on the monthly model.
                fuel_entitled = prorate_monthly(monthly_fuel, worked_dates) if role_lower == "ops coordinator" else 0.0
            else:
                food_entitled = food_allowance_for_dates(food_mode, monthly_food, allow_wd, allow_sun, worked_dates)
                fuel_entitled = prorate_monthly(monthly_fuel, worked_dates)
            allowance_total = food_entitled + fuel_entitled
            staff_paid = float(st_pay["amount_paid"].sum()) if not st_pay.empty else 0.0

            detailed_ledger = []
            if role_lower != "ops coordinator":
                for d in period_dates:
                    if d in unpaid_leave_dates:
                        row_type, day_salary, day_allow = "Unpaid Leave", 0.0, 0.0
                    elif d in paid_leave_dates:
                        row_type = "Paid Leave"
                        day_salary = standard_daily_rate
                        day_allow = 0.0
                    else:
                        row_type = "Daily Salary"
                        day_salary = standard_daily_rate
                        day_allow = (
                            food_allowance_for_date(food_mode, monthly_food, allow_wd, allow_sun, d)
                            + (monthly_fuel / month_days(d))
                        ) if food_mode == "daily" else 0.0
                    detailed_ledger.append({
                        "date": d, "type": row_type, "cart": "—",
                        "collection": 0.0, "fixed_salary": day_salary,
                        "commission": 0.0, "allowance": day_allow,
                        "advance_taken": 0.0, "food_taken": 0.0
                    })
                leakage_amount = attach_staff_leakage(st_name, detailed_ledger, employment_start, employment_end)
            else:
                leakage_amount = attach_staff_leakage(st_name, None, employment_start, employment_end)

            staff_paid += leakage_amount
            staff_incurred = staff_salary + food_entitled + fuel_entitled
            staff_due = staff_incurred - staff_paid
            total_labour_incurred += staff_incurred
            total_labour_paid += staff_paid

            breakdown_by_staff[st_name] = {
                "monthly_fixed_salary": monthly_sal,
                "daily_rate": display_daily_rate,
                "days_worked": worked_days,
                "paid_leaves": paid_leave_cnt,
                "unpaid_leaves": unpaid_leave_cnt,
                "payable_days": payable_days,
                "salary": staff_salary,
                "commissions": 0.0,
                "food_tea_allowance_mode": food_mode,
                "allowance_weekday": allow_wd,
                "allowance_sunday": allow_sun,
                "monthly_food_tea_allowance": monthly_food,
                "monthly_fuel_allowance": monthly_fuel,
                "food_tea_allowance": food_entitled,
                "fuel_allowance": fuel_entitled,
                "allowances": allowance_total,
                "incurred": staff_incurred,
                "paid": staff_paid,
                "due": staff_due,
                "detailed_ledger": detailed_ledger,
                "doj": doj,
                "role": staff_role,
                "period_start": period_start,
                "period_end": period_end
            }
            continue

        st_exp = exp_ledger_df[exp_ledger_df["staff_name"] == st_name].copy() if not exp_ledger_df.empty else pd.DataFrame()
        if not st_exp.empty:
            ex_dates = pd.to_datetime(st_exp["expense_date"]).dt.date
            st_exp = st_exp[(ex_dates >= employment_start) & (ex_dates <= employment_end)]
        shift_sal, shift_comm, days_worked, detailed_ledger = 0.0, 0.0, 0, []

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

        all_dates = {
            d for d in set(leave_map.keys()).union(set(shift_map.keys())).union(set(exp_map.keys()))
            if employment_start <= d <= employment_end
        }
        paid_leaves_cnt = 0
        worked_dates = set()

        for d in sorted(all_dates):
            is_leave = d in leave_map
            leave_type = leave_map.get(d)
            day_adv = exp_map.get(d, {}).get("advance", 0.0)
            day_food = exp_map.get(d, {}).get("food", 0.0)
            exp_attached = False

            if is_leave:
                if leave_type == "Paid":
                    paid_leaves_cnt += 1
                    shift_sal += standard_daily_rate
                    detailed_ledger.append({
                        "date": d, "type": "Paid Leave", "cart": "—",
                        "collection": 0.0, "fixed_salary": standard_daily_rate,
                        "commission": 0.0, "allowance": 0.0,
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
                worked_dates.add(d)
                shift_sal += standard_daily_rate
                day_allow_rate = (
                    food_allowance_for_date(food_mode, monthly_food, allow_wd, allow_sun, d)
                    if food_mode == "daily" else 0.0
                )

                for idx, cart_shift in enumerate(shift_map[d]):
                    s_col = cart_shift["collection"]
                    day_comm = max(0.0, s_col - comm_thresh) * (comm_pct / 100.0)
                    shift_comm += day_comm
                    if idx == 0:
                        detailed_ledger.append({
                            "date": d, "type": "Worked Day", "cart": cart_shift["cart"],
                            "collection": s_col, "fixed_salary": standard_daily_rate,
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
        unpaid_leaves_cnt = sum(1 for row in detailed_ledger if row.get("type") == "Unpaid Leave")
        if food_mode == "monthly":
            # Monthly Food Allowance is paid centrally, outside the individual payslip.
            food_entitled = 0.0
        else:
            food_entitled = food_allowance_for_dates(food_mode, monthly_food, allow_wd, allow_sun, worked_dates)
        # Monthly Fuel Allowance is not applicable to Cart Operators.
        fuel_entitled = 0.0
        allowance_total = food_entitled
        staff_incurred = shift_sal + shift_comm + food_entitled
        staff_paid = (float(st_pay["amount_paid"].sum()) if not st_pay.empty else 0.0) + attach_staff_leakage(st_name, detailed_ledger, employment_start, employment_end)
        staff_due = staff_incurred - staff_paid
        total_labour_incurred += staff_incurred
        total_labour_paid += staff_paid

        breakdown_by_staff[st_name] = {
            "monthly_fixed_salary": monthly_sal,
            "daily_rate": standard_daily_rate,
            "days_worked": days_worked,
            "paid_leaves": paid_leaves_cnt,
            "unpaid_leaves": unpaid_leaves_cnt,
            "salary": shift_sal,
            "commissions": shift_comm,
            "food_tea_allowance_mode": food_mode,
            "allowance_weekday": allow_wd,
            "allowance_sunday": allow_sun,
            "monthly_food_tea_allowance": monthly_food,
            "monthly_fuel_allowance": monthly_fuel,
            "food_tea_allowance": food_entitled,
            "fuel_allowance": fuel_entitled,
            "allowances": allowance_total,
            "incurred": staff_incurred,
            "paid": staff_paid,
            "due": staff_due,
            "detailed_ledger": detailed_ledger,
            "doj": doj,
            "role": staff_role,
            "period_start": employment_start,
            "period_end": employment_end
        }

    return total_labour_incurred, total_labour_paid, total_labour_incurred - total_labour_paid, breakdown_by_staff


def compute_period_financials(start_date, end_date, avg_divisor_days=None, daily_df_in=None, exp_df_in=None):
    """
    Single source of truth for period financial calculations across:
    - Home Landing Page (Top KPI Strip & Bottom Finance Performance Card)
    - Dashboard Main Financials Overview
    - Dashboard -> Financials Sub-Page (KPIs, OPEX Deep-Dive, P&L, Cost Distribution)
    - Dashboard -> Month-Wise Performance Comparison
    """
    d_df = daily_df_in if daily_df_in is not None else load_db_daily_df()
    if d_df is not None and not d_df.empty and "Cart" in d_df.columns:
        d_df = d_df[~d_df["Cart"].astype(str).str.lower().str.contains("test", na=False)].copy()
    else:
        d_df = pd.DataFrame()

    if exp_df_in is not None:
        e_df = exp_df_in.copy()
    else:
        try:
            e_df = pd.DataFrame(load_db_expenses_list())
        except Exception:
            e_df = pd.DataFrame()

    if not d_df.empty and "Date" in d_df.columns:
        range_df = d_df[(d_df["Date"].dt.date >= start_date) & (d_df["Date"].dt.date <= end_date)].copy()
    else:
        range_df = pd.DataFrame()

    if not e_df.empty and "Date" in e_df.columns and e_df["Date"].notna().any():
        range_exp = e_df[(e_df["Date"].dt.date >= start_date) & (e_df["Date"].dt.date <= end_date)].copy()
    else:
        range_exp = pd.DataFrame()

    total_rev = float(range_df["Total_Collection"].sum()) if not range_df.empty else 0.0
    total_units = int(round(range_df["Sold_Total"].sum())) if not range_df.empty else 0

    try:
        flavor_range_df = load_db_flavor_sales(start_date=start_date, end_date=end_date)
    except Exception:
        flavor_range_df = pd.DataFrame()
    exact_cogs_sold = (
        float(flavor_range_df["COGS (₹)"].sum())
        if not flavor_range_df.empty and "COGS (₹)" in flavor_range_df.columns
        else 0.0
    )

    if not range_exp.empty:
        expense_types = range_exp["Expense_Type"].fillna("").astype(str).str.strip().str.upper()
        expense_categories = range_exp["Category"].fillna("").astype(str).str.strip().str.casefold()
        staff_blank_mask = (
            range_exp["Staff_Name"].isna()
            | range_exp["Staff_Name"].astype(str).str.strip().isin(["", "None", "nan", "null", "Select Staff"])
        )
        capex_total = float(range_exp.loc[expense_types == "CAPEX", "Amount"].sum())
        unassigned_labour_df = range_exp[
            (expense_types == "OPEX") & (expense_categories == "labour charges") & staff_blank_mask
        ].copy()
        unassigned_labour_total = float(unassigned_labour_df["Amount"].sum()) if not unassigned_labour_df.empty else 0.0
        non_labour_opex_df = range_exp[
            (expense_types == "OPEX") & (~expense_categories.isin(["labour charges", "cost of goods"]))
        ].copy()
        other_opex_total = float(non_labour_opex_df["Amount"].sum()) if not non_labour_opex_df.empty else 0.0
    else:
        capex_total = 0.0
        unassigned_labour_df = pd.DataFrame()
        unassigned_labour_total = 0.0
        non_labour_opex_df = pd.DataFrame()
        other_opex_total = 0.0

    try:
        _, _, _, staff_pay_breakdown = calculate_incurred_labour_for_range(
            start_date, end_date, limit_to_employment=True
        )
    except Exception:
        staff_pay_breakdown = {}

    staff_salary_total = sum(float(staff.get("incurred", 0.0)) for staff in staff_pay_breakdown.values())
    tot_labour_incurred = staff_salary_total + unassigned_labour_total
    total_incurred_opex = tot_labour_incurred + other_opex_total

    gross_profit = total_rev - exact_cogs_sold
    cogs_margin = (exact_cogs_sold / total_rev * 100.0) if total_rev > 0 else 0.0
    gross_margin = (gross_profit / total_rev * 100.0) if total_rev > 0 else 0.0
    net_profit = gross_profit - total_incurred_opex
    net_margin = (net_profit / total_rev * 100.0) if total_rev > 0 else 0.0
    opex_margin = (total_incurred_opex / total_rev * 100.0) if total_rev > 0 else 0.0

    if avg_divisor_days is None or int(avg_divisor_days) <= 0:
        today_ref = date.today()
        if start_date.day == 1 and start_date.year == today_ref.year and start_date.month == today_ref.month and end_date >= today_ref:
            avg_divisor_days = max(1, (today_ref - start_date).days)
        else:
            avg_divisor_days = max(1, (end_date - start_date).days + 1)
    else:
        avg_divisor_days = max(1, int(avg_divisor_days))

    avg_rev_per_day = (total_rev / float(avg_divisor_days)) if avg_divisor_days > 0 else 0.0
    avg_units_per_day = int(round(total_units / float(avg_divisor_days))) if avg_divisor_days > 0 else 0

    return {
        "range_df": range_df,
        "range_exp": range_exp,
        "total_rev": total_rev,
        "total_units": total_units,
        "exact_cogs_sold": exact_cogs_sold,
        "capex_total": capex_total,
        "staff_pay_breakdown": staff_pay_breakdown,
        "unassigned_labour_df": unassigned_labour_df,
        "non_labour_opex_df": non_labour_opex_df,
        "tot_labour_incurred": tot_labour_incurred,
        "other_opex_total": other_opex_total,
        "total_incurred_opex": total_incurred_opex,
        "gross_profit": gross_profit,
        "cogs_margin": cogs_margin,
        "gross_margin": gross_margin,
        "net_profit": net_profit,
        "net_margin": net_margin,
        "opex_margin": opex_margin,
        "avg_divisor_days": avg_divisor_days,
        "avg_rev_per_day": avg_rev_per_day,
        "avg_units_per_day": avg_units_per_day,
    }


def compute_what_if_financials(start_date, end_date, enabled_carts, all_carts, avg_divisor_days=None, daily_df_in=None, exp_df_in=None):
    """Recalculate P&L and OPEX for a subset of enabled carts, excluding disabled-cart staff & expenses."""
    d_df = daily_df_in if daily_df_in is not None else load_db_daily_df()
    if d_df is not None and not d_df.empty and "Cart" in d_df.columns:
        d_df = d_df[~d_df["Cart"].astype(str).str.lower().str.contains("test", na=False)].copy()
    else:
        d_df = pd.DataFrame()

    if exp_df_in is not None:
        e_df = exp_df_in.copy()
    else:
        try:
            e_df = pd.DataFrame(load_db_expenses_list())
        except Exception:
            e_df = pd.DataFrame()

    if not d_df.empty and "Date" in d_df.columns:
        full_range_df = d_df[(d_df["Date"].dt.date >= start_date) & (d_df["Date"].dt.date <= end_date)].copy()
    else:
        full_range_df = pd.DataFrame()

    if not e_df.empty and "Date" in e_df.columns and e_df["Date"].notna().any():
        range_exp = e_df[(e_df["Date"].dt.date >= start_date) & (e_df["Date"].dt.date <= end_date)].copy()
    else:
        range_exp = pd.DataFrame()

    enabled_upper = {str(c).strip().upper() for c in (enabled_carts or []) if str(c).strip()}
    all_upper = {str(c).strip().upper() for c in (all_carts or []) if str(c).strip()}
    disabled_upper = all_upper - enabled_upper

    if not full_range_df.empty:
        cart_upper_series = full_range_df["Cart"].fillna("").astype(str).str.strip().str.upper()
        range_df = full_range_df[cart_upper_series.isin(enabled_upper)].copy()
    else:
        range_df = pd.DataFrame()

    # Identify Cart Operators who worked ONLY on disabled carts in this range
    disabled_only_staff_lower = set()
    if not full_range_df.empty and "Staff" in full_range_df.columns and disabled_upper:
        staff_carts_map = {}
        for _, _r in full_range_df.iterrows():
            _sn = str(_r.get("Staff") or "").strip().lower()
            _cn = str(_r.get("Cart") or "").strip().upper()
            if _sn and _sn not in ("none", "nan", "select staff"):
                staff_carts_map.setdefault(_sn, set()).add(_cn)
        for _sn, _cset in staff_carts_map.items():
            if _cset and _cset.isdisjoint(enabled_upper):
                disabled_only_staff_lower.add(_sn)

    total_rev = float(range_df["Total_Collection"].sum()) if not range_df.empty else 0.0
    total_units = int(round(range_df["Sold_Total"].sum())) if not range_df.empty else 0

    try:
        flavor_range_df = load_db_flavor_sales(start_date=start_date, end_date=end_date, allowed_carts=list(enabled_upper))
    except Exception:
        flavor_range_df = pd.DataFrame()
    exact_cogs_sold = (
        float(flavor_range_df["COGS (₹)"].sum())
        if not flavor_range_df.empty and "COGS (₹)" in flavor_range_df.columns
        else 0.0
    )

    def _is_disabled_cart_expense(row):
        if not disabled_upper:
            return False
        attr = str(row.get("Attributed_To") or "").strip().upper()
        if attr and attr in disabled_upper:
            return True
        st_n = str(row.get("Staff_Name") or "").strip().lower()
        if st_n and st_n in disabled_only_staff_lower:
            return True
        if not attr:
            desc_comb = (str(row.get("Description") or "") + " " + str(row.get("Remarks") or "")).upper()
            for dc in disabled_upper:
                if dc and dc in desc_comb:
                    return True
        return False

    if not range_exp.empty:
        keep_mask = ~range_exp.apply(_is_disabled_cart_expense, axis=1)
        filtered_exp = range_exp[keep_mask].copy()
    else:
        filtered_exp = pd.DataFrame()

    try:
        _, _, _, staff_pay_breakdown = calculate_incurred_labour_for_range(
            start_date, end_date, limit_to_employment=True, allowed_carts=list(enabled_upper)
        )
    except Exception:
        staff_pay_breakdown = {}

    cart_staff_names_lower = set()
    cart_specific_labour = 0.0
    common_labour = 0.0
    for _sn, _sv in staff_pay_breakdown.items():
        _role_l = str(_sv.get("role") or "Cart Operator").strip().lower()
        _inc_v = float(_sv.get("incurred", 0.0))
        if _role_l == "cart operator":
            cart_specific_labour += _inc_v
            cart_staff_names_lower.add(str(_sn).strip().lower())
        else:
            common_labour += _inc_v

    def _is_enabled_cart_expense(row):
        if not enabled_upper:
            return False
        attr = str(row.get("Attributed_To") or "").strip().upper()
        if attr and attr in enabled_upper:
            return True
        st_n = str(row.get("Staff_Name") or "").strip().lower()
        if st_n and st_n in cart_staff_names_lower:
            return True
        if not attr:
            desc_comb = (str(row.get("Description") or "") + " " + str(row.get("Remarks") or "")).upper()
            for ec in enabled_upper:
                if ec and ec in desc_comb:
                    return True
        return False

    cart_specific_other_opex = 0.0
    common_other_opex = 0.0
    unassigned_labour_total = 0.0
    other_opex_total = 0.0

    if not filtered_exp.empty:
        expense_types = filtered_exp["Expense_Type"].fillna("").astype(str).str.strip().str.upper()
        expense_categories = filtered_exp["Category"].fillna("").astype(str).str.strip().str.casefold()
        staff_blank_mask = (
            filtered_exp["Staff_Name"].isna()
            | filtered_exp["Staff_Name"].astype(str).str.strip().isin(["", "None", "nan", "null", "Select Staff"])
        )
        unassigned_labour_df = filtered_exp[
            (expense_types == "OPEX") & (expense_categories == "labour charges") & staff_blank_mask
        ].copy()
        non_labour_opex_df = filtered_exp[
            (expense_types == "OPEX") & (~expense_categories.isin(["labour charges", "cost of goods"]))
        ].copy()

        for _sub_df, _is_ul in ((unassigned_labour_df, True), (non_labour_opex_df, False)):
            if not _sub_df.empty:
                for _, _erow in _sub_df.iterrows():
                    _amt = float(_erow.get("Amount") or 0.0)
                    if _is_ul:
                        unassigned_labour_total += _amt
                    else:
                        other_opex_total += _amt
                    if _is_enabled_cart_expense(_erow):
                        cart_specific_other_opex += _amt
                    else:
                        common_other_opex += _amt

    staff_salary_total = cart_specific_labour + common_labour
    tot_labour_incurred = staff_salary_total + unassigned_labour_total
    total_incurred_opex = tot_labour_incurred + other_opex_total
    opex_cart_specific = cart_specific_labour + cart_specific_other_opex
    opex_common = common_labour + common_other_opex

    gross_profit = total_rev - exact_cogs_sold
    cogs_margin = (exact_cogs_sold / total_rev * 100.0) if total_rev > 0 else 0.0
    gross_margin = (gross_profit / total_rev * 100.0) if total_rev > 0 else 0.0
    net_profit = gross_profit - total_incurred_opex
    net_margin = (net_profit / total_rev * 100.0) if total_rev > 0 else 0.0
    opex_margin = (total_incurred_opex / total_rev * 100.0) if total_rev > 0 else 0.0
    opex_common_pct = (opex_common / total_rev * 100.0) if total_rev > 0 else 0.0
    opex_cart_pct = (opex_cart_specific / total_rev * 100.0) if total_rev > 0 else 0.0

    rev_to_cart_opex = (total_rev / opex_cart_specific) if opex_cart_specific > 0 else 0.0
    gm_to_cart_opex = (gross_profit / opex_cart_specific) if opex_cart_specific > 0 else 0.0
    nm_to_cart_opex = (net_profit / opex_cart_specific) if opex_cart_specific > 0 else 0.0

    if avg_divisor_days is None or int(avg_divisor_days) <= 0:
        today_ref = date.today()
        if start_date.day == 1 and start_date.year == today_ref.year and start_date.month == today_ref.month and end_date >= today_ref:
            avg_divisor_days = max(1, (today_ref - start_date).days)
        else:
            avg_divisor_days = max(1, (end_date - start_date).days + 1)
    else:
        avg_divisor_days = max(1, int(avg_divisor_days))

    avg_rev_per_day = (total_rev / float(avg_divisor_days)) if avg_divisor_days > 0 else 0.0
    avg_units_per_day = (total_units / float(avg_divisor_days)) if avg_divisor_days > 0 else 0.0

    return {
        "total_rev": total_rev,
        "total_units": total_units,
        "exact_cogs_sold": exact_cogs_sold,
        "tot_labour_incurred": tot_labour_incurred,
        "other_opex_total": other_opex_total,
        "total_incurred_opex": total_incurred_opex,
        "opex_common": opex_common,
        "opex_common_pct": opex_common_pct,
        "opex_cart_specific": opex_cart_specific,
        "opex_cart_pct": opex_cart_pct,
        "rev_to_cart_opex": rev_to_cart_opex,
        "gm_to_cart_opex": gm_to_cart_opex,
        "nm_to_cart_opex": nm_to_cart_opex,
        "gross_profit": gross_profit,
        "cogs_margin": cogs_margin,
        "gross_margin": gross_margin,
        "net_profit": net_profit,
        "net_margin": net_margin,
        "opex_margin": opex_margin,
        "avg_divisor_days": avg_divisor_days,
        "avg_rev_per_day": avg_rev_per_day,
        "avg_units_per_day": avg_units_per_day,
    }

def generate_payslip_pdf(staff_name, start_date, end_date, data_dict):
    if not REPORTLAB_AVAILABLE: return None
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story, styles = [], getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#2563EB'), alignment=1)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#0F172A'), alignment=1)

    logo_path = "assets/logo.png"
    if os.path.exists(logo_path):
        try:
            img = RLImage(logo_path, width=50, height=50)
            header_table = Table([[img, Paragraph("<b>Kulfi Factory - Hosur Franchise</b><br/>Staff Salary Payslip", title_style)]], colWidths=[60, 470])
        except Exception:
            header_table = Table([[Paragraph("<b>Kulfi Factory</b>", title_style), Paragraph("<b>Kulfi Factory - Hosur Franchise</b><br/>Staff Salary Payslip", title_style)]], colWidths=[80, 450])
    else:
        header_table = Table([[Paragraph("<b>Kulfi Factory</b>", title_style), Paragraph("<b>Kulfi Factory - Hosur Franchise</b><br/>Staff Salary Payslip", title_style)]], colWidths=[80, 450])

    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'CENTER')]))
    header_table.hAlign = 'LEFT'
    story.append(header_table); story.append(Spacer(1, 10))

    doj_val = data_dict.get('doj')
    doj_str = pd.to_datetime(doj_val).strftime('%d-%b-%y') if pd.notna(doj_val) and str(doj_val).strip() else "N/A"

    dol_val = data_dict.get('dol')
    dol_date = None
    if pd.notna(dol_val) and str(dol_val).strip():
        try:
            dol_date = pd.to_datetime(dol_val).date()
        except Exception:
            dol_date = None
    show_last_working_day = dol_date is not None and start_date <= dol_date <= end_date
    dol_str = dol_date.strftime('%d-%b-%y') if show_last_working_day else None

    month_str = start_date.strftime('%B %Y')
    role = str(data_dict.get('role') or 'Cart Operator')
    is_ops_coordinator = role.strip().lower() == 'ops coordinator'
    is_cart_operator = role.strip().lower() == 'cart operator'
    payable_days = int(data_dict.get('payable_days', data_dict.get('days_worked', 0) + data_dict.get('paid_leaves', 0)))

    pdf_header = f"<b>Staff Member:</b> {staff_name} &nbsp;|&nbsp; <b>Role:</b> {role} &nbsp;|&nbsp; <b>Date of Joining:</b> {doj_str}"
    if show_last_working_day:
        pdf_header += f" &nbsp;|&nbsp; <b>Last Working Day:</b> {dol_str}"
    pdf_header += f" &nbsp;|&nbsp; <b>Payslip for the month:</b> {month_str}"
    story.append(Paragraph(pdf_header, sub_style))
    story.append(Spacer(1, 12))

    unpaid_leaves = int(data_dict.get('unpaid_leaves', 0))
    if is_ops_coordinator:
        pro_rata_basis = f"{data_dict['days_worked']} Days Worked + {data_dict['paid_leaves']} Paid Leaves, {unpaid_leaves} Unpaid Leaves"
        days_label = ["Total Days Worked", pro_rata_basis, f"{payable_days} payable days"]
    else:
        pro_rata_basis = f"({data_dict['days_worked']} + {data_dict['paid_leaves']}) days @ Rs. {data_dict.get('daily_rate', 600):.2f}/day"
        days_label = ["Total Days Worked", f"{data_dict['days_worked']} Days Worked + {data_dict['paid_leaves']} Paid Leaves, {unpaid_leaves} Unpaid Leaves", f"{data_dict['days_worked'] + data_dict['paid_leaves']} days"]

    food_mode = str(data_dict.get("food_tea_allowance_mode") or "monthly").strip().lower()
    if food_mode == "daily":
        food_component = "Food & Tea Allowance (Daily Plan)"
        food_basis = f"Weekday Rs. {data_dict.get('allowance_weekday', 0):,.2f}/day | Sunday Rs. {data_dict.get('allowance_sunday', 0):,.2f}/day; based on days worked"
    else:
        food_component = "Food & Tea Allowance (Monthly Plan)"
        food_basis = f"Plan Rs. {data_dict.get('monthly_food_tea_allowance', 0):,.2f}/month; pro-rata for days worked"

    adjustment_amount = float(_num(data_dict.get("adjustment_amount", 0.0)))
    adjustment_reason = str(data_dict.get("adjustment_reason") or "").strip()
    final_adjusted = float(_num(data_dict.get("final_payable_adjusted", data_dict.get("due", 0.0))))

    summary_data = [
        ["Salary Component", "Basis / Calculation Details", "Amount (Rs.)"],
        ["Monthly Fixed Salary", "Standard Monthly Base Plan", f"Rs. {data_dict['monthly_fixed_salary']:,.2f}"],
        days_label,
        ["Pro-rata Fixed Salary", pro_rata_basis, f"Rs. {data_dict['salary']:,.2f}"],
    ]
    if not is_ops_coordinator:
        summary_data.append(["Sales Commissions", "Commission on qualifying daily collections", f"Rs. {data_dict['commissions']:,.2f}"])
    # Daily Food/Tea remains part of the payslip presentation. Monthly Food/Tea is
    # tracked separately under Staff & Payroll -> Monthly Food Allowance.
    if food_mode == "daily":
        summary_data.append([food_component, food_basis, f"Rs. {data_dict.get('food_tea_allowance', 0):,.2f}"])
    if food_mode == "monthly" and is_ops_coordinator:
        gross_basis = "Pro-rata fixed salary + pro-rata Fuel allowance"
    elif food_mode == "monthly":
        gross_basis = "Pro-rata fixed salary + commission (where applicable)"
    elif is_cart_operator:
        gross_basis = "Pro-rata fixed salary + commission + daily Food/Tea allowance"
    else:
        gross_basis = "Pro-rata fixed salary + commission (where applicable) + daily Food/Tea + Fuel"

    if (is_ops_coordinator or food_mode == "daily") and not is_cart_operator:
        summary_data.append([
            "Monthly Fuel Allowance",
            f"Plan Rs. {data_dict.get('monthly_fuel_allowance', 0):,.2f}/month; pro-rata for days worked",
            f"Rs. {data_dict.get('fuel_allowance', 0):,.2f}"
        ])

    summary_data.extend([
        ["Gross Payable Earnings", gross_basis, f"Rs. {data_dict['incurred']:,.2f}"],
        ["Already Paid / Disbursed", ("Advances paid already, unexplained leakages & penalties" if is_cart_operator else "Advances paid already & penalties"), f"-Rs. {data_dict['paid']:,.2f}"],
        ["Calculated Final Payable", "Calculated amount before manual adjustment", f"Rs. {data_dict['due']:,.2f}"],
        ["Manual Adjustment", adjustment_reason if adjustment_reason else "No adjustment entered", f"Rs. {adjustment_amount:+,.2f}" if abs(adjustment_amount) > 0.0001 else "Rs. 0.00"],
        ["Final Payable (Adjusted)", "Calculated final payable amount post adjustments", f"Rs. {final_adjusted:,.2f}"]
    ])

    t_summary = Table(summary_data, colWidths=[150, 250, 100])
    t_summary.hAlign = 'LEFT'
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E2252')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 9.5),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')), ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')), ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,1), (-1,-2), 'Helvetica'), ('FONTSIZE', (0,1), (-1,-1), 9), ('TOPPADDING', (0,1), (-1,-1), 4), ('BOTTOMPADDING', (0,1), (-1,-1), 4)
    ]))
    story.append(t_summary); story.append(Spacer(1, 15))

    if not is_ops_coordinator:
        ledger_title = "Detailed Commission & Allowance Entitlement Ledger" if food_mode == "daily" else "Detailed Commission & Salary Ledger"
        story.append(Paragraph(f"<b>{ledger_title}</b>", ParagraphStyle('SubHeader', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor('#2563EB'), alignment=0)))
        story.append(Spacer(1, 4))

        line_t = Table([['']], colWidths=[525])
        line_t.setStyle(TableStyle([('LINEABOVE', (0,0), (-1,-1), 0.75, colors.HexColor('#2563EB'))]))
        line_t.hAlign = 'LEFT'
        story.append(line_t)
        story.append(Spacer(1, 6))

        if food_mode == "daily":
            ledger_rows = [["Date", "Type", "Cart", "Sales", "Salary", "Comm.", "Allow.", "Adv. Taken", "Allow. Taken", "Leakage"]]
            for item in data_dict.get("detailed_ledger", []):
                ledger_rows.append([
                    item["date"].strftime("%d-%b-%y"), item["type"], item["cart"],
                    f"{item['collection']:,.0f}" if item['collection'] > 0 else "—",
                    f"{item['fixed_salary']:,.0f}",
                    f"{item['commission']:,.0f}" if item['commission'] > 0 else "—",
                    f"{item['allowance']:,.0f}" if item['allowance'] > 0 else "—",
                    f"{item['advance_taken']:,.0f}" if item.get('advance_taken', 0) > 0 else "—",
                    f"{item['food_taken']:,.0f}" if item.get('food_taken', 0) > 0 else "—",
                    f"{item['leakage']:,.0f}" if item.get('leakage', 0) > 0 else "—"
                ])
            if len(ledger_rows) == 1:
                ledger_rows.append(["No records", "—", "—", "—", "—", "—", "—", "—", "—", "—"])
            ledger_widths = [52, 60, 82, 42, 42, 42, 42, 50, 50, 50]
        else:
            ledger_rows = [["Date", "Type", "Cart", "Sales", "Salary", "Comm.", "Adv. Taken", "Leakage"]]
            for item in data_dict.get("detailed_ledger", []):
                ledger_rows.append([
                    item["date"].strftime("%d-%b-%y"), item["type"], item["cart"],
                    f"{item['collection']:,.0f}" if item['collection'] > 0 else "—",
                    f"{item['fixed_salary']:,.0f}",
                    f"{item['commission']:,.0f}" if item['commission'] > 0 else "—",
                    f"{item['advance_taken']:,.0f}" if item.get('advance_taken', 0) > 0 else "—",
                    f"{item['leakage']:,.0f}" if item.get('leakage', 0) > 0 else "—"
                ])
            if len(ledger_rows) == 1:
                ledger_rows.append(["No records", "—", "—", "—", "—", "—", "—", "—"])
            ledger_widths = [58, 72, 100, 55, 55, 55, 65, 65]

        t_ledger = Table(ledger_rows, colWidths=ledger_widths)
        t_ledger.hAlign = 'LEFT'
        t_ledger.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#047857')), ('TEXTCOLOR', (0,0), (-1,0), colors.white), ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,0), 8.5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#6EE7B7')), ('ALIGN', (3,0), (-1,-1), 'RIGHT'), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 8), ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3)
        ]))
        story.append(t_ledger); story.append(Spacer(1, 15))

    story.append(Paragraph("<i>This is a computer-generated payslip for Kulfi Factory - Hosur Franchise.</i>", ParagraphStyle('Footer', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.gray, alignment=1)))
    doc.build(story); buffer.seek(0); return buffer.getvalue()

def generate_stock_received_report_pdf(monthly_sections, overall_units, overall_cost, location_label="All Locations"):
    if not REPORTLAB_AVAILABLE:
        return None
    from reportlab.lib.pagesizes import landscape
    from reportlab.platypus import KeepTogether

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=28,
        leftMargin=28,
        topMargin=26,
        bottomMargin=26,
    )
    story, styles = [], getSampleStyleSheet()

    title_style = ParagraphStyle(
        "SRMatrixTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=colors.HexColor("#1E2252"),
        alignment=0,
        spaceAfter=2,
    )
    sub_style = ParagraphStyle(
        "SRMatrixSub",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        textColor=colors.HexColor("#475569"),
        alignment=0,
        spaceAfter=8,
    )
    month_hdr_style = ParagraphStyle(
        "SRMonthHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        textColor=colors.HexColor("#1E2252"),
        alignment=0,
        spaceBefore=4,
        spaceAfter=5,
    )

    story.append(Paragraph(f"<b>Kulfi Factory — Stock Received Report ({escape(str(location_label))})</b>", title_style))
    story.append(Paragraph(f"Generated on {date.today().strftime('%d-%b-%Y')}", sub_style))

    usable_width = 736.0

    # Top Overall Summary Box
    overall_box = Table(
        [
            ["OVERALL UNITS RECEIVED (SO FAR)", "OVERALL COST (SO FAR)"],
            [f"{int(overall_units):,} units", f"Rs. {float(overall_cost):,.0f}"],
        ],
        colWidths=[usable_width / 2.0, usable_width / 2.0],
    )
    overall_box.hAlign = "LEFT"
    overall_box.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#1E2252")),
            ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#047857")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9.5),
            ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#EFF6FF")),
            ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#ECFDF5")),
            ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#1E2252")),
            ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#047857")),
            ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 1), (-1, 1), 12),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ])
    )
    story.append(overall_box)
    story.append(Spacer(1, 14))

    for sec in monthly_sections:
        m_name = sec["month_name"]
        matrix_cols = sec["matrix_cols"]
        pdf_rows = sec["pdf_rows"]
        m_units = int(sec["month_total_units"])
        m_cost = float(sec["month_total_cost"])

        date_cols = matrix_cols[1:]
        n_dates = max(1, len(date_cols))

        # Dynamically scale Flavour column, date column width, font size, and padding
        # so ALL dates for the month always fit in ONE single table without wrapping.
        if n_dates <= 8:
            flavour_col_w = 115.0
            date_col_w = min(82.0, (usable_width - flavour_col_w) / n_dates)
            hdr_font, body_font, tot_font, h_pad = 9.0, 8.5, 9.0, 5
        elif n_dates <= 11:
            flavour_col_w = 102.0
            date_col_w = (usable_width - flavour_col_w) / n_dates
            hdr_font, body_font, tot_font, h_pad = 8.0, 8.0, 8.2, 4
        elif n_dates <= 14:
            flavour_col_w = 92.0
            date_col_w = (usable_width - flavour_col_w) / n_dates
            hdr_font, body_font, tot_font, h_pad = 7.2, 7.2, 7.5, 3
        else:
            flavour_col_w = 84.0
            date_col_w = (usable_width - flavour_col_w) / n_dates
            hdr_font, body_font, tot_font, h_pad = 6.5, 6.5, 6.8, 2

        col_widths = [flavour_col_w] + [date_col_w] * len(date_cols)
        actual_table_width = sum(col_widths)

        # Ensure the summary boxes below are wide enough for their text while matching
        # the month table's width (minimum 300pt if there is only 1 date column).
        if actual_table_width < 300.0 and len(date_cols) > 0:
            extra_per_col = (300.0 - flavour_col_w) / len(date_cols)
            col_widths = [flavour_col_w] + [max(date_col_w, extra_per_col)] * len(date_cols)
            actual_table_width = sum(col_widths)

        tbl_data = [matrix_cols]
        for r in pdf_rows:
            tbl_data.append([str(r.get(col, "")) for col in matrix_cols])

        t = Table(tbl_data, colWidths=col_widths, repeatRows=1)
        t.hAlign = "LEFT"
        t.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E2252")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), hdr_font),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -3), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -3), body_font),
                ("TEXTCOLOR", (0, 1), (-1, -3), colors.HexColor("#0F172A")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -3), [colors.white, colors.HexColor("#F8FAFC")]),
                # Total Units row (-2)
                ("BACKGROUND", (0, -2), (-1, -2), colors.HexColor("#EFF6FF")),
                ("FONTNAME", (0, -2), (-1, -2), "Helvetica-Bold"),
                ("FONTSIZE", (0, -2), (-1, -2), tot_font),
                ("TEXTCOLOR", (0, -2), (-1, -2), colors.HexColor("#1E2252")),
                ("LINEABOVE", (0, -2), (-1, -2), 1.1, colors.HexColor("#B47A2B")),
                # Total Cost (Rs.) row (-1)
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#ECFDF5")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), tot_font),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.HexColor("#047857")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), h_pad),
                ("RIGHTPADDING", (0, 0), (-1, -1), h_pad),
            ])
        )

        # Summary box below the month table: exact same total width as the month table above
        half_w = actual_table_width / 2.0
        lbl_font = 8.0 if actual_table_width < 420.0 else 8.5
        val_font = 10.0 if actual_table_width < 420.0 else 10.5

        month_summary_box = Table(
            [
                [f"{m_name.upper()} — OVERALL UNITS", f"{m_name.upper()} — OVERALL COST (RS.)"],
                [f"{m_units:,} units", f"Rs. {m_cost:,.0f}"],
            ],
            colWidths=[half_w, half_w],
        )
        month_summary_box.hAlign = "LEFT"
        month_summary_box.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), colors.HexColor("#EFF6FF")),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#ECFDF5")),
                ("TEXTCOLOR", (0, 0), (0, 0), colors.HexColor("#1E2252")),
                ("TEXTCOLOR", (1, 0), (1, 0), colors.HexColor("#047857")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), lbl_font),
                ("BACKGROUND", (0, 1), (0, 1), colors.HexColor("#F8FAFC")),
                ("BACKGROUND", (1, 1), (1, 1), colors.HexColor("#ECFDF5")),
                ("TEXTCOLOR", (0, 1), (0, 1), colors.HexColor("#1E2252")),
                ("TEXTCOLOR", (1, 1), (1, 1), colors.HexColor("#047857")),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), val_font),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#CBD5E1")),
                ("TOPPADDING", (0, 0), (-1, -1), 4.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ])
        )

        month_flowables = [
            Paragraph(f"<b>{escape(m_name)}</b>", month_hdr_style),
            t,
            Spacer(1, 5),
            month_summary_box,
            Spacer(1, 14),
        ]

        # KeepTogether ensures a month table + its summary boxes never split across pages
        story.append(KeepTogether(month_flowables))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


# ----------------------------------------------------------------------
# LOGO HELPER & AUTHENTICATION
# ----------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _load_compressed_logo_b64():
    logo_candidates = ["assets/logo.png", "logo.png"]
    for p in logo_candidates:
        if os.path.exists(p):
            try:
                with open(p, "rb") as lf:
                    return base64.b64encode(lf.read()).decode("ascii")
            except Exception:
                pass
    return None

def get_top_left_square_logo_html(size_px=36):
    """Render the login window logo (assets/logo.png) in a compressed square frame for the top-left corner."""
    b64 = _load_compressed_logo_b64()
    if b64:
        return (
            f'<div class="kulfi-cmd-logo-sq" style="width:{size_px}px;height:{size_px}px;" title="Kulfi Factory">'
            f'<img src="data:image/png;base64,{b64}" alt="Kulfi Factory Logo" />'
            f'</div>'
        )
    return f'<div class="kulfi-cmd-crest" style="width:{size_px}px;height:{size_px}px;">🍦</div>'

def check_login():
    if st.session_state.get("authenticated", False): return True
    _, col_form, _ = st.columns([1, 1.25, 1])
    with col_form:
        with st.container(border=True):
            logo_b64 = _load_compressed_logo_b64()
            if logo_b64:
                st.markdown(
                    f"""
                    <div style="display:flex;flex-direction:column;align-items:center;padding:8px 0 4px 0;">
                        <div style="width:84px;height:84px;border-radius:18px;border:1.5px solid #CBD5E1;background:#FFFFFF;
                                    box-shadow:0 6px 18px rgba(30,34,82,0.12);padding:4px;display:flex;align-items:center;justify-content:center;overflow:hidden;">
                            <img src="data:image/png;base64,{logo_b64}" style="width:100%;height:100%;object-fit:cover;border-radius:14px;" />
                        </div>
                        <div style="font-size:19px;font-weight:800;color:#1E2252;margin-top:10px;">Kulfi Ops Admin Portal</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                try: st.image("assets/logo.png", width=180)
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
                    st.session_state["authenticated"] = True; st.session_state["user_role"] = "admin"; st.session_state["assigned_location"] = "ALL"; st.rerun()
                elif entry_pass and hmac.compare_digest(user_clean, entry_user) and hmac.compare_digest(pass_clean, entry_pass):
                    st.session_state["authenticated"] = True; st.session_state["user_role"] = "entry"; st.session_state["assigned_location"] = str(st.secrets.get("entry_location", "HOSUR")).strip().upper(); st.session_state["current_location"] = st.session_state["assigned_location"]; st.rerun()
                elif db_conn is not None:
                    try:
                        auth_df = db_conn.query("SELECT is_valid, assigned_location FROM public.verify_app_login(:r, :p, NULL);", params={"r": user_clean, "p": pass_clean}, ttl="0s")
                        if not auth_df.empty and bool(auth_df.iloc[0]["is_valid"]):
                            assigned_loc = str(auth_df.iloc[0]["assigned_location"] or "HOSUR").strip().upper()
                            st.session_state["authenticated"] = True
                            st.session_state["user_role"] = "admin" if user_clean == "admin" else "entry"
                            st.session_state["assigned_location"] = assigned_loc
                            st.session_state["current_location"] = "All Locations (Aggregated)" if (user_clean == "admin" and assigned_loc == "ALL") else assigned_loc
                            st.rerun()
                        else:
                            st.error("Incorrect username or password — try again.")
                    except Exception:
                        st.error("Incorrect username or password — try again.")
                else: st.error("Incorrect username or password — try again.")
    return False

if not check_login(): st.stop()

# ----------------------------------------------------------------------
# NAVIGATION & ROLE CONFIG — DEPOSITO WHITE HEADER BAR WITH TOP-LEFT SQUARE LOGO
# ----------------------------------------------------------------------
user_role = st.session_state.get("user_role", "admin")
_top_left_logo_html = get_top_left_square_logo_html(36)

if user_role == "entry":
    st.session_state["current_location"] = st.session_state.get("assigned_location", "HOSUR")
    CITY = get_default_write_city()
    CARTS = get_carts_for_active_location(include_freezer=False)
    ATTRIBUTED_OPTIONS = ["Central / Freezer"] + CARTS
    page = "Daily Entry"
    with st.container(border=True):
        top_nav_c1, top_nav_c2 = st.columns([5.8, 1.2], gap="small", vertical_alignment="center")
        with top_nav_c1:
            st.markdown(
                f'<div class="kulfi-cmd-left kulfi-top-cmd-bar-scope">'
                f'{_top_left_logo_html}'
                f'<div class="kulfi-cmd-text">'
                f'<div class="kulfi-cmd-title">Kulfi Ops — Daily Entry ({CITY})</div>'
                f'<div class="kulfi-cmd-sub"><span class="kulfi-top-pill">📍 {CITY}</span><span>{date.today().strftime("%d %b %Y")}</span></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        with top_nav_c2:
            if st.button("🚪 Log out", type="secondary", use_container_width=True, key="entry_top_logout_btn"):
                st.session_state["authenticated"] = False
                st.session_state["user_role"] = None
                st.rerun()
else:
    if "_pending_page_nav" in st.session_state:
        st.session_state["page_nav"] = st.session_state.pop("_pending_page_nav")
    if "_pending_loc_change" in st.session_state:
        _new_loc = st.session_state.pop("_pending_loc_change")
        st.session_state["current_location"] = _new_loc
        st.session_state.pop("entry_cart_shared", None)

    configured_locs = load_configured_locations_list(include_inactive=False)
    loc_options = ["All Locations (Aggregated)"] + configured_locs
    default_loc = st.session_state.get("current_location", "HOSUR")
    if default_loc not in loc_options:
        default_loc = "HOSUR" if "HOSUR" in loc_options else loc_options[0]
    st.session_state["current_location"] = default_loc

    nav_options = [
        "Home",
        "Dashboard",
        "Daily Entry",
        "Bulk Orders & Quotes",
        "Live Cart Tracking",
        "Cash Custody",
        "Purchase Orders",
        "Freezer Stock",
        "Freezer Analysis",
        "Stock Removed",
        "Expenses",
        "Staff & Payroll",
        "Payslip Generator",
        "Locations & Logins",
    ]

    if st.session_state.get("page_nav") not in nav_options:
        st.session_state["page_nav"] = "Home"
    page = st.session_state["page_nav"]
    page_header_title = "Financials" if page == "Dashboard" else page

    CITY = get_default_write_city()
    CARTS = get_carts_for_active_location(include_freezer=False)
    ATTRIBUTED_OPTIONS = ["Central / Freezer"] + CARTS
    loc_badge = "All Locations" if get_active_location_filter() == "ALL" else get_active_location_filter()

    # --- DEPOSITO WHITE TOP COMMAND BAR (WRAPPED INSIDE BORDERED CONTAINER, NO SWITCH) ---
    with st.container(border=True):
        cmd_c0, cmd_c1, cmd_c2, cmd_c4, cmd_c5 = st.columns(
            [3.2, 0.85, 0.90, 1.20, 0.85],
            gap="small",
            vertical_alignment="center",
        )
        with cmd_c0:
            st.markdown(
                f'<div class="kulfi-cmd-left kulfi-top-cmd-bar-scope">'
                f'{_top_left_logo_html}'
                f'<div class="kulfi-cmd-text">'
                f'<div class="kulfi-cmd-title-row"><span class="kulfi-cmd-title">Kulfi Ops — {escape(page_header_title)}</span></div>'
                f'<div class="kulfi-cmd-sub">'
                f'<span class="kulfi-top-pill">📍 {escape(loc_badge)}</span>'
                f'<span>{date.today().strftime("%d %b %Y")}</span>'
                f'</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        with cmd_c1:
            if st.button(
                "🏠 Home",
                type="primary" if page == "Home" else "secondary",
                use_container_width=True,
                key="top_cmd_home_btn",
            ):
                st.session_state["page_nav"] = "Home"
                st.session_state["dash_sub_page"] = None
                st.rerun()
        with cmd_c2:
            if st.button(
                "🛒 Entry",
                type="primary" if page == "Daily Entry" else "secondary",
                use_container_width=True,
                key="top_cmd_entry_btn",
            ):
                st.session_state["page_nav"] = "Daily Entry"
                st.session_state["daily_entry_mode"] = "sales"
                st.rerun()
        with cmd_c4:
            _loc_pop_nonce = int(st.session_state.get("_loc_pop_nonce", 0))
            def _render_loc_popover_items(nonce_val):
                for _lidx, _loc_opt in enumerate(loc_options):
                    _is_cur_loc = (st.session_state.get("current_location") == _loc_opt)
                    if st.button(
                        f"📍 {_loc_opt}",
                        key=f"top_pop_loc_{nonce_val}_{_lidx}",
                        type="primary" if _is_cur_loc else "secondary",
                        use_container_width=True,
                    ):
                        st.session_state["_loc_pop_nonce"] = nonce_val + 1
                        st.session_state["_pending_loc_change"] = _loc_opt
                        st.rerun()

            if _loc_pop_nonce % 2 == 0:
                with st.container():
                    with st.popover(f"📍 {loc_badge}", use_container_width=True):
                        _render_loc_popover_items(_loc_pop_nonce)
            else:
                with st.popover(f"📍 {loc_badge} ", use_container_width=True):
                    _render_loc_popover_items(_loc_pop_nonce)
        with cmd_c5:
            if st.button("🚪 Log out", type="secondary", use_container_width=True, key="top_cmd_logout_btn"):
                st.session_state["authenticated"] = False
                st.session_state["user_role"] = None
                st.rerun()

# ======================================================================
# PAGE ROUTING
# ======================================================================

if user_role == "admin":
    left_nav_col, main_page_col = st.columns([0.96, 4.04], gap="medium")
    with left_nav_col:
        with st.container(border=True):
            _dock_menu_items = [
                ("Home", "🏠  Home", {}),
                ("Dashboard", "📊  Financials", {"dash_sub_page": None}),
                ("Daily Entry", "🛒  Daily Entry", {"daily_entry_mode": "sales"}),
                ("Live Cart Tracking", "📡  Live POS", {}),
                ("Bulk Orders & Quotes", "📦  Bulk Orders", {}),
                ("Freezer Analysis", "📈  Freezer Analysis", {}),
                ("Freezer Stock", "❄️  Stock Received", {"db_stock_mode": "New entry"}),
                ("Stock Removed", "🗑️  Stock Removed", {"rem_screen_mode": "New Entry"}),
                ("Purchase Orders", "🧾  Purchase Orders", {}),
                ("Expenses", "💳  Expenses", {}),
                ("Cash Custody", "💰  Cash Custody", {}),
                ("Staff & Payroll", "👥  Staff & Payroll", {}),
                ("Payslip Generator", "📄  Payslips", {}),
                ("Locations & Logins", "🌐  Locations & Logins", {}),
            ]

            for _m_idx, (_target_p, _m_lbl, _m_state) in enumerate(_dock_menu_items):
                _is_active_dock = (page == _target_p)
                if st.button(
                    _m_lbl,
                    key=f"deposito_dock_btn_grid_{_m_idx}",
                    type="primary" if _is_active_dock else "secondary",
                    use_container_width=True,
                ):
                    for _k, _v in _m_state.items():
                        st.session_state[_k] = _v
                    st.session_state["page_nav"] = _target_p
                    st.rerun()

    _page_body_container = main_page_col
else:
    _page_body_container = st.container()

with _page_body_container:

    if page == "Home" and user_role == "admin":
        # ------------------------------------------------------------------
        # LIVE OPERATIONAL METRICS FOR THE DEPOSITO-STYLE STACKED LANDING PAGE
        # ------------------------------------------------------------------
        today_home = date.today()
        yesterday_home = today_home - timedelta(days=1)
        mtd_start = today_home.replace(day=1)

        REAL_CARTS_HOME = [c for c in CARTS if "test" not in str(c).strip().lower()]
        if not REAL_CARTS_HOME:
            REAL_CARTS_HOME = [c for c in CARTS]

        try:
            home_daily_df = load_db_daily_df()
            if not home_daily_df.empty and "Cart" in home_daily_df.columns:
                home_daily_df = home_daily_df[~home_daily_df["Cart"].astype(str).str.lower().str.contains("test", na=False)].copy()
        except Exception:
            home_daily_df = pd.DataFrame()

        try:
            home_exp_list = load_db_expenses_list()
            home_exp_df = pd.DataFrame(home_exp_list)
        except Exception:
            home_exp_df = pd.DataFrame()

        if not home_daily_df.empty:
            mtd_df = home_daily_df[(home_daily_df["Date"].dt.date >= mtd_start) & (home_daily_df["Date"].dt.date <= today_home)]
            if mtd_df.empty:
                period_start_home = today_home - timedelta(days=29)
                period_df_home = home_daily_df[(home_daily_df["Date"].dt.date >= period_start_home) & (home_daily_df["Date"].dt.date <= today_home)]
                period_badge_lbl = "Last 30 Days"
                period_short_lbl = "30d"
                avg_divisor_home = max(1, (today_home - period_start_home).days + 1)
            else:
                period_start_home = mtd_start
                period_df_home = mtd_df
                period_badge_lbl = f"{today_home.strftime('%b %Y')} (MTD)"
                period_short_lbl = "MTD"
                avg_divisor_home = max(1, (today_home - mtd_start).days)
        else:
            period_start_home = mtd_start
            period_df_home = pd.DataFrame()
            period_badge_lbl = f"{today_home.strftime('%b %Y')} (MTD)"
            period_short_lbl = "MTD"
            avg_divisor_home = max(1, (today_home - mtd_start).days)

        home_fin = compute_period_financials(
            start_date=period_start_home,
            end_date=today_home,
            avg_divisor_days=avg_divisor_home,
            daily_df_in=home_daily_df,
            exp_df_in=home_exp_df,
        )
        period_rev_home = home_fin["total_rev"]
        period_units_home = home_fin["total_units"]
        avg_daily_rev_home = home_fin["avg_rev_per_day"]
        avg_daily_units_home = home_fin["avg_units_per_day"]

        yest_df_home = home_daily_df[home_daily_df["Date"].dt.date == yesterday_home] if not home_daily_df.empty else pd.DataFrame()
        yest_rev_home = float(yest_df_home["Total_Collection"].sum()) if not yest_df_home.empty else 0.0
        yest_units_home = int(round(yest_df_home["Sold_Total"].sum())) if not yest_df_home.empty else 0
        yest_vs_avg_pct = ((yest_rev_home - avg_daily_rev_home) / avg_daily_rev_home * 100.0) if avg_daily_rev_home > 0 else 0.0

        # Freezer stock & 14-day sales velocity
        try:
            freezer_stock_map = get_physical_current_stock_map()
        except Exception:
            freezer_stock_map = {c: 0 for c in FLAVOR_CODES}
        try:
            vel_df = load_db_flavor_sales(start_date=today_home - timedelta(days=13), end_date=today_home)
            vel_map = dict(zip(vel_df["code"], vel_df["Units sold"])) if not vel_df.empty else {}
        except Exception:
            vel_map = {}

        low_stock_flavors_cnt = 0
        tot_freezer_units_home = 0
        for _c in FLAVOR_CODES:
            _f_qty = int(freezer_stock_map.get(_c, 0))
            tot_freezer_units_home += _f_qty
            _daily_rate = float(vel_map.get(_c, 0)) / 14.0
            if _f_qty <= 0 or (_daily_rate > 0 and _f_qty <= (_daily_rate * 3.0)) or (_daily_rate == 0 and _f_qty < 25):
                low_stock_flavors_cnt += 1

        # Cart-wise current stock (excluding test carts)
        tot_cart_units_home = 0
        if db_conn is not None:
            try:
                latest_c_df = db_conn.query(
                    """
                    WITH latest_ce AS (
                        SELECT DISTINCT ON (cart_name) id, cart_name
                        FROM daily_cart_entries
                        WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                        ORDER BY cart_name, entry_date DESC, id DESC
                    )
                    SELECT e.cart_name, i.flavor_code, COALESCE(i.closing_units, 0) AS closing_units
                    FROM latest_ce e
                    JOIN daily_cart_items i ON i.daily_entry_id = e.id;
                    """,
                    params={"active_loc": get_active_location_filter()},
                    ttl="60s",
                )
                for _, _cr in latest_c_df.iterrows():
                    _cn = str(_cr.get("cart_name") or "").strip()
                    if "test" in _cn.lower() or "freezer" in _cn.lower():
                        continue
                    _fc = str(_cr.get("flavor_code") or "").strip()
                    _cu = max(0, int(round(_num(_cr.get("closing_units")))))
                    if _fc in FLAVOR_CODES:
                        tot_cart_units_home += _cu
            except Exception:
                pass

        # Exact COGS, Gross Profit, OPEX & Net Profit for the Period (via canonical compute_period_financials)
        exact_cogs_home = home_fin["exact_cogs_sold"]
        total_opex_home = home_fin["total_incurred_opex"]
        gross_profit_home = home_fin["gross_profit"]
        net_profit_home = home_fin["net_profit"]
        net_margin_pct_home = home_fin["net_margin"]


        # 1. TOP 5 WHITE KPI CARDS STRIP (Full comma-separated numbers, short labels)
        net_margin_color = "#059669" if net_profit_home >= 0 else "#DC2626"
        net_profit_abs_str = f"-₹{abs(net_profit_home):,.0f}" if net_profit_home < 0 else f"₹{net_profit_home:,.0f}"
        yest_pct_badge = f"({yest_vs_avg_pct:+.0f}%)"

        st.markdown(
            f"""
            <div class="deposito-kpi-strip">
                <div class="dep-kpi-card">
                    <div style="font-size:10px;font-weight:700;color:#64748B;text-align:center;">Time Period</div>
                    <div class="dep-time-pill">• {escape(period_badge_lbl)}</div>
                </div>
                <div class="dep-kpi-card" style="text-align:center;">
                    <div class="dep-kpi-num"><span style="color:#059669;font-size:0.86rem;">{yest_pct_badge}</span> ₹{yest_rev_home:,.0f}</div>
                    <div class="dep-kpi-lbl">Yesterday ({yest_units_home:,} pcs)</div>
                </div>
                <div class="dep-kpi-card">
                    <div class="dep-kpi-dual">
                        <div style="text-align:center;">
                            <div class="dep-kpi-num" style="color:{'#DC2626' if low_stock_flavors_cnt > 0 else '#059669'};">{tot_freezer_units_home:,}</div>
                            <div class="dep-kpi-lbl">Freezer ({low_stock_flavors_cnt} Low)</div>
                        </div>
                        <div style="text-align:center;">
                            <div class="dep-kpi-num" style="color:#1E2252;">{period_units_home:,}</div>
                            <div class="dep-kpi-lbl">Units Sold</div>
                        </div>
                    </div>
                </div>
                <div class="dep-kpi-card">
                    <div class="dep-kpi-dual">
                        <div style="text-align:center;">
                            <div class="dep-kpi-num" style="color:#1E2252;">₹{avg_daily_rev_home:,.0f}</div>
                            <div class="dep-kpi-lbl">Avg Sale / Day</div>
                        </div>
                        <div style="text-align:center;">
                            <div class="dep-kpi-num" style="color:#059669;">₹{period_rev_home:,.0f}</div>
                            <div class="dep-kpi-lbl">Total Sales</div>
                        </div>
                    </div>
                </div>
                <div class="dep-kpi-card" style="text-align:center;">
                    <div class="dep-kpi-num" style="color:{net_margin_color};font-size:0.98rem;">{net_profit_abs_str} <span style="font-size:0.84rem;">({net_margin_pct_home:.1f}%)</span></div>
                    <div class="dep-kpi-lbl">Net Margin</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style=" + chr(39) + "height: 6px;" + chr(39) + "></div>", unsafe_allow_html=True)

        # 2. MIDDLE ROW: EMERALD CAPACITY CARD + LAST 7 DAY SALES MATRIX
        mid_left_col, mid_right_col = st.columns([1.02, 2.53], gap="small")

        with mid_left_col:
            FREEZER_CAP_UNITS = 4000
            NUM_ACTIVE_CARTS = max(1, len(REAL_CARTS_HOME))
            CART_CAP_UNITS = 400 * NUM_ACTIVE_CARTS
            fzr_util_pct = max(0.0, (float(tot_freezer_units_home) / float(FREEZER_CAP_UNITS)) * 100.0)
            cart_util_pct = max(0.0, (float(tot_cart_units_home) / float(CART_CAP_UNITS)) * 100.0)

            fzr_arc_pct = min(100.0, max(2.0 if tot_freezer_units_home > 0 else 0.0, fzr_util_pct))
            outer_circum = 276.5
            outer_offset = outer_circum * (1.0 - (fzr_arc_pct / 100.0))

            st.markdown(
                f"""
                <div class="dep-emerald-card">
                    <div class="dep-emerald-hdr">Capacity Utilization</div>
                    <div class="dep-emerald-float-strip">
                        <div class="dep-emerald-float-dot" style="background:#FEF3C7;color:#D97706;">❄️</div>
                        <div class="dep-emerald-float-dot" style="background:#DBEAFE;color:#2563EB;">🛒</div>
                        <div class="dep-emerald-float-dot" style="background:#ECFDF5;color:#059669;">📦</div>
                    </div>
                    <div style="display:flex;justify-content:center;align-items:center;margin:2px 0;">
                        <svg width="136" height="136" viewBox="0 0 108 108">
                            <circle cx="54" cy="54" r="44" fill="none" stroke="rgba(255,255,255,0.22)" stroke-width="7.5" />
                            <circle cx="54" cy="54" r="44" fill="none" stroke="#F59E0B" stroke-width="7.5"
                                    stroke-linecap="round"
                                    stroke-dasharray="{outer_circum:.1f}"
                                    stroke-dashoffset="{outer_offset:.1f}"
                                    transform="rotate(-90 54 54)" />
                            <text x="54" y="54" text-anchor="middle" dominant-baseline="middle" fill="#FFFFFF" font-size="22" font-weight="900" font-family="Plus Jakarta Sans, sans-serif">{fzr_util_pct:.0f}%</text>
                            <text x="54" y="72" text-anchor="middle" fill="#D1FAE5" font-size="8.5" font-weight="700" font-family="Plus Jakarta Sans, sans-serif">Freezer Used</text>
                        </svg>
                    </div>
                    <div class="dep-emerald-footer">
                        <div>
                            <div class="dep-emerald-ft-lbl">Freezer ({fzr_util_pct:.1f}%)</div>
                            <div class="dep-emerald-ft-val">{tot_freezer_units_home:,} / {FREEZER_CAP_UNITS:,}</div>
                        </div>
                        <div>
                            <div class="dep-emerald-ft-lbl">Carts ({cart_util_pct:.1f}%)</div>
                            <div class="dep-emerald-ft-val">{tot_cart_units_home:,} / {CART_CAP_UNITS:,}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with mid_right_col:
            # LAST 7 DAY SALES MATRIX (7 Days, Full Comma Numbers, Uniform Lighter Cart Color, Border on Latest Day Column)
            last_7_dates = [yesterday_home - timedelta(days=i) for i in range(6, -1, -1)]
            if not home_daily_df.empty:
                df_non_test = home_daily_df.copy()
                df_non_test["SaleDate"] = pd.to_datetime(df_non_test["Date"]).dt.date
            else:
                df_non_test = pd.DataFrame()

            def _fmt_full_inr(val):
                v = float(val or 0.0)
                if v <= 0:
                    return "—"
                return f"₹{v:,.0f}"

            day_overall_rev = {d: 0.0 for d in last_7_dates}
            day_overall_phonepe = {d: 0.0 for d in last_7_dates}
            day_overall_cash = {d: 0.0 for d in last_7_dates}
            cart_day_rev = {c: {d: 0.0 for d in last_7_dates} for c in REAL_CARTS_HOME}

            if not df_non_test.empty:
                sub_7d = df_non_test[df_non_test["SaleDate"].isin(last_7_dates)]
                for _, _sr in sub_7d.iterrows():
                    _sd = _sr["SaleDate"]
                    _cname = str(_sr.get("Cart") or "").strip()
                    if "test" in _cname.lower():
                        continue
                    _rev = float(_sr.get("Total_Collection") or 0.0)
                    _ph = float(_sr.get("PhonePe") or 0.0)
                    _cs = float(_sr.get("Cash") or 0.0)
                    day_overall_rev[_sd] = day_overall_rev.get(_sd, 0.0) + _rev
                    day_overall_phonepe[_sd] = day_overall_phonepe.get(_sd, 0.0) + _ph
                    day_overall_cash[_sd] = day_overall_cash.get(_sd, 0.0) + _cs
                    if _cname in cart_day_rev:
                        cart_day_rev[_cname][_sd] += _rev

            tot_7d_sum = sum(day_overall_rev.values())
            tot_7d_ph = sum(day_overall_phonepe.values())
            tot_7d_cs = sum(day_overall_cash.values())

            # Build Left Label Column
            lbl_cells_html = [
                '<div class="dep-sales7-lbl-cell" style="color:#64748B;font-size:9.5px;">DATE</div>',
                f'<div class="dep-sales7-lbl-cell" style="color:#065F46;font-weight:900;">🔥 Total (₹{tot_7d_sum:,.0f})</div>',
            ]
            for _cname in REAL_CARTS_HOME:
                _c_7d_sum = sum(cart_day_rev.get(_cname, {}).values())
                _short_c = _cname.replace("HOSUR ", "").replace("UTTARAHALLI ", "UTT ")
                lbl_cells_html.append(
                    f'<div class="dep-sales7-lbl-cell">🛒 {escape(_short_c)} (₹{_c_7d_sum:,.0f})</div>'
                )
            lbl_cells_html.append(f'<div class="dep-sales7-lbl-cell" style="color:#4C1D95;">📱 PhonePe (₹{tot_7d_ph:,.0f})</div>')
            lbl_cells_html.append(f'<div class="dep-sales7-lbl-cell" style="color:#1E3A8A;">💵 Cash (₹{tot_7d_cs:,.0f})</div>')

            grid_cols_html = [f'<div class="dep-sales7-col">{"".join(lbl_cells_html)}</div>']

            # Build 7 Day Columns (with latest day column highlighted by a continuous border)
            for _d_idx, _d in enumerate(last_7_dates):
                _is_latest_col = (_d_idx == len(last_7_dates) - 1)
                _col_cls = "dep-sales7-col latest-day-col" if _is_latest_col else "dep-sales7-col"
                _col_cells = [
                    f'<div class="dep-sales7-hdr-cell">{_d.strftime("%d %b")}</div>',
                    f'<div class="dep-sales7-tile total-row">{_fmt_full_inr(day_overall_rev[_d])}</div>',
                ]
                for _cname in REAL_CARTS_HOME:
                    _cv = cart_day_rev.get(_cname, {}).get(_d, 0.0)
                    _c_cls = "cart-zero" if _cv <= 0 else "cart-row"
                    _col_cells.append(f'<div class="dep-sales7-tile {_c_cls}">{_fmt_full_inr(_cv)}</div>')
                _col_cells.append(f'<div class="dep-sales7-tile phonepe-row">{_fmt_full_inr(day_overall_phonepe[_d])}</div>')
                _col_cells.append(f'<div class="dep-sales7-tile cash-row">{_fmt_full_inr(day_overall_cash[_d])}</div>')
                grid_cols_html.append(f'<div class="{_col_cls}">{"".join(_col_cells)}</div>')

            st.markdown(
                f"""
                <div class="dep-matrix-card">
                    <div>
                        <div class="dep-matrix-top">
                            <span class="dep-date-badge">📅 {last_7_dates[0].strftime('%d %b')} – {last_7_dates[-1].strftime('%d %b %Y')}</span>
                            <span style="font-size:12px;font-weight:800;color:#1E2252;">Last 7 day sales</span>
                        </div>
                        <div class="dep-sales7-grid">
                            {"".join(grid_cols_html)}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style=" + chr(39) + "height: 6px;" + chr(39) + "></div>", unsafe_allow_html=True)

        # 3. BOTTOM ROW: FINANCE PERFORMANCE CARD | MONTH-WISE SALE COMPARISON | TOP CARTS
        bot_c1, bot_c2, bot_c3 = st.columns([1.15, 1.30, 1.10], gap="small")

        with bot_c1:
            # CRISP FINANCE PERFORMANCE CARD (Zero Sub-Text, with % up to 1 decimal in brackets for COGS, Gr Profit & Net Profit)
            cogs_pct_home = (exact_cogs_home / period_rev_home * 100.0) if period_rev_home > 0 else 0.0
            gp_pct_home = (gross_profit_home / period_rev_home * 100.0) if period_rev_home > 0 else 0.0
            gp_str = f"-₹{abs(gross_profit_home):,.0f}" if gross_profit_home < 0 else f"₹{gross_profit_home:,.0f}"
            np_str = f"-₹{abs(net_profit_home):,.0f}" if net_profit_home < 0 else f"₹{net_profit_home:,.0f}"
            np_col = "#065F46" if net_profit_home >= 0 else "#991B1B"

            st.markdown(
                f"""
                <div class="dep-bottom-card">
                    <div>
                        <div class="dep-bottom-hdr">Finance Performance ({escape(period_short_lbl)})</div>
                        <div class="dep-fin-grid">
                            <div class="dep-fin-item">
                                <span class="dep-fin-lbl">Revenue</span>
                                <span class="dep-fin-val" style="color:#1E2252;">₹{period_rev_home:,.0f}</span>
                            </div>
                            <div class="dep-fin-item">
                                <span class="dep-fin-lbl">Total Units</span>
                                <span class="dep-fin-val" style="color:#1E2252;">{period_units_home:,}</span>
                            </div>
                            <div class="dep-fin-item">
                                <span class="dep-fin-lbl">Avg Rev / Day</span>
                                <span class="dep-fin-val" style="color:#2563EB;">₹{avg_daily_rev_home:,.0f}</span>
                            </div>
                            <div class="dep-fin-item">
                                <span class="dep-fin-lbl">Avg Units / Day</span>
                                <span class="dep-fin-val" style="color:#2563EB;">{avg_daily_units_home:,}</span>
                            </div>
                            <div class="dep-fin-item" style="border-left-color:#F59E0B;">
                                <span class="dep-fin-lbl">COGS</span>
                                <span class="dep-fin-val" style="color:#B45309;">₹{exact_cogs_home:,.0f} ({cogs_pct_home:.1f}%)</span>
                            </div>
                            <div class="dep-fin-item" style="border-left-color:#059669;">
                                <span class="dep-fin-lbl">Gr Profit</span>
                                <span class="dep-fin-val" style="color:#059669;">{gp_str} ({gp_pct_home:.1f}%)</span>
                            </div>
                        </div>
                        <div class="dep-fin-net-bar">
                            <span style="font-size:10.5px;font-weight:800;color:#065F46;">Net Profit</span>
                            <span style="font-size:12px;font-weight:900;color:{np_col};">{np_str} ({net_margin_pct_home:.1f}%)</span>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with bot_c2:
            # MONTH-WISE SALE COMPARISON CARD (Full-Data Completed Calendar Months)
            full_months_home = []
            if not home_daily_df.empty:
                m_work = home_daily_df.copy()
                m_work["EntryDate"] = pd.to_datetime(m_work["Date"]).dt.date
                m_work["YM"] = pd.to_datetime(m_work["Date"]).dt.to_period("M")
                cur_ym = pd.Period(today_home, freq="M")
                for _ym in sorted(m_work["YM"].unique()):
                    if _ym >= cur_ym:
                        continue
                    _yr, _mo = int(_ym.year), int(_ym.month)
                    _days_in_mo = calendar.monthrange(_yr, _mo)[1]
                    _mo_start = date(_yr, _mo, 1)
                    _mo_end = date(_yr, _mo, _days_in_mo)
                    _sub_m = m_work[(m_work["EntryDate"] >= _mo_start) & (m_work["EntryDate"] <= _mo_end)]
                    if _sub_m.empty:
                        continue
                    if _sub_m["EntryDate"].min() == _mo_start and _sub_m["EntryDate"].max() == _mo_end and _sub_m["EntryDate"].nunique() >= _days_in_mo:
                        _m_rev = float(_sub_m["Total_Collection"].sum())
                        _m_units = int(round(_sub_m["Sold_Total"].sum()))
                        _m_avg = _m_rev / float(_days_in_mo)
                        full_months_home.append((_mo_start.strftime("%b %Y"), _m_rev, _m_avg, _m_units))

            if full_months_home:
                max_m_rev = max(1.0, max(x[1] for x in full_months_home))
                m_rows_html = []
                for _mlbl, _mrev, _mavg, _munits in reversed(full_months_home[-4:]):
                    _mw = min(100, max(15, int(round((_mrev / max_m_rev) * 100.0))))
                    m_rows_html.append(
                        f'<div style="margin-bottom:6px;">'
                        f'<div style="display:flex;justify-content:space-between;font-size:10px;font-weight:800;color:#1E2252;margin-bottom:2px;">'
                        f'<span>{escape(_mlbl)}</span>'
                        f'<span>₹{_mrev:,.0f} &nbsp;•&nbsp; <span style="color:#059669;">Avg ₹{_mavg:,.0f}/d</span> &nbsp;•&nbsp; {_munits:,} pcs</span>'
                        f'</div>'
                        f'<div style="width:100%;background:#EDE9FE;height:7px;border-radius:999px;overflow:hidden;">'
                        f'<div style="width:{_mw}%;background:linear-gradient(90deg, #7C3AED 0%, #4F46E5 100%);height:7px;border-radius:999px;"></div>'
                        f'</div>'
                        f'</div>'
                    )
                month_card_body = "".join(m_rows_html)
            else:
                month_card_body = '<div style="font-size:11px;color:#64748B;font-weight:600;padding:18px 4px;text-align:center;">No completed full-data months yet.</div>'

            st.markdown(
                f"""
                <div class="dep-bottom-card">
                    <div>
                        <div class="dep-bottom-hdr">Month-Wise Sale Comparison</div>
                        <div style="padding:2px 2px 0 2px;">
                            {month_card_body}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with bot_c3:
            # Horizontal Sky-Blue Bar Chart for Carts (Excluding Test Carts, Full Comma Numbers)
            cart_rev_rows = []
            if not period_df_home.empty:
                c_grp = period_df_home.groupby("Cart", as_index=False).agg({"Total_Collection": "sum", "Sold_Total": "sum"}).sort_values("Total_Collection", ascending=False)
                for _, _r in c_grp.iterrows():
                    _cn_str = str(_r["Cart"]).strip()
                    if "test" in _cn_str.lower():
                        continue
                    cart_rev_rows.append((_cn_str, float(_r["Total_Collection"]), int(round(_r["Sold_Total"]))))
            if not cart_rev_rows:
                for _cn in REAL_CARTS_HOME[:4]:
                    cart_rev_rows.append((_cn, 0.0, 0))

            max_c_rev = max(1.0, max((r[1] for r in cart_rev_rows), default=1.0))
            h_bars_html = []
            for _cname, _crev, _cunits in cart_rev_rows[:4]:
                _w_pct = min(100, max(12, int(round((_crev / max_c_rev) * 100.0)))) if _crev > 0 else 12
                _short_c = _cname.replace("HOSUR ", "").replace("UTTARAHALLI ", "UTT ")
                h_bars_html.append(
                    f'<div style="margin-bottom:6px;">'
                    f'<div style="display:flex;justify-content:space-between;font-size:10px;font-weight:700;color:#334155;margin-bottom:2px;">'
                    f'<span>{escape(_short_c)}</span>'
                    f'<span style="color:#1E2252;font-weight:800;">₹{_crev:,.0f} ({_cunits:,})</span>'
                    f'</div>'
                    f'<div style="width:100%;background:#EFF6FF;height:6px;border-radius:999px;overflow:hidden;">'
                    f'<div style="width:{_w_pct}%;background:linear-gradient(90deg, #60A5FA 0%, #3B82F6 100%);height:6px;border-radius:999px;"></div>'
                    f'</div>'
                    f'</div>'
                )

            st.markdown(
                f"""
                <div class="dep-bottom-card">
                    <div>
                        <div class="dep-bottom-hdr">Top Carts ({escape(period_short_lbl)})</div>
                        <div style="padding:2px 2px 0 2px;">
                            {"".join(h_bars_html)}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # 4. QUICK OPERATIONS LAUNCHPAD STRIP BELOW VISUAL CARDS
        with st.container(border=True):
            st.markdown('<span class="kulfi-clickable-card-grid"></span>', unsafe_allow_html=True)
            st.markdown('<div class="launchpad-section-hdr">⚡ Quick Entry</div>', unsafe_allow_html=True)
            qa_cols = st.columns(6, gap="small")
            _quick_ops = [
                ("Daily Entry", "🧾", "Sales Entry", {"daily_entry_mode": "sales"}),
                ("Daily Entry", "📦", "Restock Carts", {"daily_entry_mode": "restock"}),
                ("Daily Entry", "➕", "Extra Stock", {"daily_entry_mode": "extra"}),
                ("Daily Entry", "🔄", "Remove Stock", {"daily_entry_mode": "remove_cart_stock"}),
                ("Daily Entry", "📋", "View Stock", {"daily_entry_mode": "view_stock"}),
                ("Daily Entry", "❄️", "Freezer Sale", {"daily_entry_mode": "freezer_sales", "fzr_entry_sub_mode": "new"}),
            ]
            for _qi, (_qpage, _qico, _qlbl, _qstate) in enumerate(_quick_ops):
                with qa_cols[_qi]:
                    if st.button(f"{_qico} **{_qlbl}**", key=f"home_qa_btn_{_qi}", use_container_width=True):
                        for _k, _v in _qstate.items():
                            st.session_state[_k] = _v
                        st.session_state["page_nav"] = _qpage
                        st.rerun()

    if page == "Locations & Logins" and user_role == "admin":
        st.subheader("🌐 Locations, Carts / Freezers & Logins Setup")
        pass

        if db_conn is None:
            st.error("Database connection is unavailable.")
            st.stop()

        cfg_tab1, cfg_tab2, cfg_tab3 = st.tabs([
            "🏙️ Cities / Locations",
            "🛒 Carts & Freezers",
            "🔐 Logins & Passwords"
        ])

        # ------------------------------------------------------------------
        # TAB 1: CITIES / LOCATIONS
        # ------------------------------------------------------------------
        with cfg_tab1:
            c_left, c_right = st.columns([1.15, 1.35], gap="large")
            with c_left:
                st.markdown("#### ➕ Add New City / Location")
                with st.form("add_operating_location_form"):
                    new_loc_code = st.text_input("Location Code (Uppercase) *", placeholder="e.g. BENGALURU")
                    new_loc_name = st.text_input("Display Name *", placeholder="e.g. Bengaluru")
                    new_loc_prefix = st.text_input("Cart Name Prefix (Optional)", placeholder="e.g. BLR (defaults to Location Code)")
                    auto_seed_assets = st.checkbox("Auto-create 3 Carts + Freezer for this city", value=True)
                    submit_new_loc = st.form_submit_button("💾 Save City / Location", type="primary", use_container_width=True)

                if submit_new_loc:
                    code_clean = re.sub(r"[^A-Z0-9_ -]", "", str(new_loc_code or "").strip().upper())
                    name_clean = str(new_loc_name or "").strip() or code_clean.title()
                    prefix_clean = str(new_loc_prefix or "").strip().upper() or code_clean
                    if not code_clean:
                        st.error("Please enter a valid Location Code.")
                    else:
                        try:
                            with db_conn.session as s:
                                s.execute(
                                    text("""
                                        INSERT INTO public.operating_locations (location_code, display_name, is_active)
                                        VALUES (:code, :name, true)
                                        ON CONFLICT (location_code) DO UPDATE
                                        SET display_name = EXCLUDED.display_name, is_active = true;
                                    """),
                                    {"code": code_clean, "name": name_clean}
                                )
                                if auto_seed_assets:
                                    for idx in (1, 2, 3):
                                        c_name = f"{prefix_clean} CART 0{idx}"
                                        s.execute(
                                            text("""
                                                INSERT INTO public.location_assets (location_code, asset_name, asset_type, is_active, sort_order)
                                                VALUES (:loc, :aname, 'CART', true, :ord)
                                                ON CONFLICT (asset_name) DO NOTHING;
                                            """),
                                            {"loc": code_clean, "aname": c_name, "ord": idx}
                                        )
                                    f_name = "Freezer" if code_clean == "HOSUR" else f"{prefix_clean} FREEZER"
                                    s.execute(
                                        text("""
                                            INSERT INTO public.location_assets (location_code, asset_name, asset_type, is_active, sort_order)
                                            VALUES (:loc, :aname, 'FREEZER', true, 99)
                                            ON CONFLICT (asset_name) DO NOTHING;
                                        """),
                                        {"loc": code_clean, "aname": f_name}
                                    )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"Location '{code_clean}' saved successfully!")
                        except Exception as e:
                            st.error(f"Could not save location: {e}")

            with c_right:
                st.markdown("#### 📋 Configured Cities / Locations")
                try:
                    locs_df = db_conn.query(
                        """
                        SELECT l.location_code, l.display_name, l.is_active,
                               COUNT(a.id) FILTER (WHERE a.asset_type = 'CART' AND a.is_active = true) AS active_carts,
                               COUNT(a.id) FILTER (WHERE a.asset_type = 'FREEZER' AND a.is_active = true) AS active_freezers
                        FROM public.operating_locations l
                        LEFT JOIN public.location_assets a ON a.location_code = l.location_code
                        GROUP BY l.location_code, l.display_name, l.is_active
                        ORDER BY l.location_code ASC;
                        """,
                        ttl="60s"
                    )
                except Exception as e:
                    locs_df = pd.DataFrame()
                    st.error(f"Could not query operating_locations: {e}")

                if locs_df.empty:
                    st.info("No locations found. Run the SQL migration script first.")
                else:
                    for _, lrow in locs_df.iterrows():
                        lcode = str(lrow["location_code"])
                        is_act = bool(lrow["is_active"])
                        with st.container(border=True):
                            lc1, lc2, lc3 = st.columns([2.2, 1.3, 1.1])
                            with lc1:
                                st.markdown(f"**{lcode}** — {lrow['display_name']}")
                                st.caption(f"Active Carts: {int(lrow['active_carts'] or 0)} | Freezers: {int(lrow['active_freezers'] or 0)}")
                            with lc2:
                                st.markdown("🟢 **Active**" if is_act else "⚪ **Inactive**")
                            with lc3:
                                btn_label = "Deactivate" if is_act else "Activate"
                                if st.button(btn_label, key=f"toggle_loc_{lcode}", use_container_width=True):
                                    with db_conn.session as s:
                                        s.execute(
                                            text("UPDATE public.operating_locations SET is_active = :st WHERE location_code = :c;"),
                                            {"st": not is_act, "c": lcode}
                                        )
                                        s.commit()
                                    st.cache_data.clear()
                                    st.rerun()

        # ------------------------------------------------------------------
        # TAB 2: CARTS & FREEZERS
        # ------------------------------------------------------------------
        with cfg_tab2:
            all_locs_for_assets = load_configured_locations_list(include_inactive=True)
            a_left, a_right = st.columns([1.15, 1.45], gap="large")

            with a_left:
                st.markdown("#### ➕ Add Cart or Freezer")
                with st.form("add_location_asset_form"):
                    asset_loc = st.selectbox("Location / City *", all_locs_for_assets)
                    asset_type = st.selectbox("Type *", ["CART", "FREEZER"])
                    asset_name = st.text_input("Cart / Freezer Name *", placeholder="e.g. BLR CART 01 or BLR FREEZER")
                    asset_order = st.number_input("Display Sort Order", min_value=1, max_value=999, value=10, step=1)
                    submit_asset = st.form_submit_button("💾 Save Cart / Freezer", type="primary", use_container_width=True)

                if submit_asset:
                    aname_clean = str(asset_name or "").strip()
                    if not aname_clean:
                        st.error("Cart / Freezer Name is required.")
                    else:
                        try:
                            with db_conn.session as s:
                                s.execute(
                                    text("""
                                        INSERT INTO public.location_assets (location_code, asset_name, asset_type, is_active, sort_order)
                                        VALUES (:loc, :name, :atype, true, :ord)
                                        ON CONFLICT (asset_name) DO UPDATE
                                        SET location_code = EXCLUDED.location_code,
                                            asset_type = EXCLUDED.asset_type,
                                            sort_order = EXCLUDED.sort_order,
                                            is_active = true;
                                    """),
                                    {"loc": asset_loc, "name": aname_clean, "atype": asset_type, "ord": int(asset_order)}
                                )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"{asset_type} '{aname_clean}' saved under {asset_loc}!")
                        except Exception as e:
                            st.error(f"Could not save cart/freezer: {e}")

            with a_right:
                st.markdown("#### 📋 Configured Carts & Freezers")
                filter_asset_loc = st.selectbox("Filter by Location", ["All"] + all_locs_for_assets, key="filter_asset_loc_sel")
                try:
                    if filter_asset_loc == "All":
                        assets_df = db_conn.query(
                            "SELECT id, location_code, asset_name, asset_type, is_active, sort_order FROM public.location_assets ORDER BY location_code ASC, sort_order ASC, asset_name ASC;",
                            ttl="60s"
                        )
                    else:
                        assets_df = db_conn.query(
                            "SELECT id, location_code, asset_name, asset_type, is_active, sort_order FROM public.location_assets WHERE location_code = :loc ORDER BY sort_order ASC, asset_name ASC;",
                            params={"loc": filter_asset_loc},
                            ttl="60s"
                        )
                except Exception as e:
                    assets_df = pd.DataFrame()
                    st.error(f"Could not load location_assets: {e}")

                if assets_df.empty:
                    st.info("No carts or freezers configured yet.")
                else:
                    for _, arow in assets_df.iterrows():
                        aid = int(arow["id"])
                        a_act = bool(arow["is_active"])
                        with st.container(border=True):
                            ac1, ac2, ac3 = st.columns([2.3, 1.1, 1.1])
                            with ac1:
                                icon = "🛒" if str(arow["asset_type"]) == "CART" else "❄️"
                                st.markdown(f"{icon} **{arow['asset_name']}**")
                                st.caption(f"City: **{arow['location_code']}** | Type: {arow['asset_type']} | Order: {arow['sort_order']}")
                            with ac2:
                                st.markdown("🟢 Active" if a_act else "⚪ Inactive")
                            with ac3:
                                if st.button("Deactivate" if a_act else "Activate", key=f"toggle_asset_{aid}", use_container_width=True):
                                    with db_conn.session as s:
                                        s.execute(
                                            text("UPDATE public.location_assets SET is_active = :st WHERE id = :id;"),
                                            {"st": not a_act, "id": aid}
                                        )
                                        s.commit()
                                    st.cache_data.clear()
                                    st.rerun()

        # ------------------------------------------------------------------
        # TAB 3: LOGINS & PASSWORDS
        # ------------------------------------------------------------------
        with cfg_tab3:
            all_locs_for_login = load_configured_locations_list(include_inactive=True)
            l_left, l_right = st.columns([1.15, 1.45], gap="large")

            with l_left:
                st.markdown("#### 🔐 Create / Reset Role Password")
                with st.form("upsert_login_credential_form"):
                    cred_role = st.selectbox("Role *", ["ops_coordinator", "cart_staff", "admin"])
                    loc_choices = ["ALL"] + all_locs_for_login if cred_role == "admin" else all_locs_for_login + ["ALL"]
                    cred_loc = st.selectbox("Assigned Location *", loc_choices)
                    cred_pass = st.text_input("New Password / Passcode *", type="password", placeholder="Enter new password")
                    cred_active = st.checkbox("Login is Active", value=True)
                    submit_cred = st.form_submit_button("💾 Set / Update Password", type="primary", use_container_width=True)

                if submit_cred:
                    if not cred_pass or len(cred_pass.strip()) < 3:
                        st.error("Password must be at least 3 characters.")
                    else:
                        try:
                            with db_conn.session as s:
                                s.execute(
                                    text("SELECT public.upsert_app_login_credential(:r, :l, :p, :a);"),
                                    {"r": cred_role, "l": cred_loc, "p": cred_pass.strip(), "a": bool(cred_active)}
                                )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"Password updated for role '{cred_role}' at location '{cred_loc}'!")
                        except Exception as e:
                            st.error(f"Could not update credential: {e}")

            with l_right:
                st.markdown("#### 📋 Configured Role Logins")
                try:
                    creds_df = db_conn.query("SELECT * FROM public.list_app_login_credentials();", ttl="60s")
                except Exception as e:
                    creds_df = pd.DataFrame()
                    st.error(f"Could not load credentials list: {e}")

                if creds_df.empty:
                    st.info("No login credentials found.")
                else:
                    disp_creds = creds_df.copy()
                    disp_creds["Role"] = disp_creds["login_role"]
                    disp_creds["Location"] = disp_creds["location"]
                    disp_creds["Status"] = disp_creds["is_active"].apply(lambda v: "🟢 Active" if bool(v) else "⚪ Disabled")
                    disp_creds["Last Updated"] = pd.to_datetime(disp_creds["updated_at"]).dt.strftime("%d-%b-%Y %I:%M %p")
                    st.dataframe(
                        disp_creds[["Location", "Role", "Status", "Last Updated"]],
                        hide_index=True,
                        use_container_width=True
                    )

    elif page == "Daily Entry":
        st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
        # Split Entry flow: default directly to Sales Entry with all 7 mode buttons in one compact top row.
        valid_entry_modes = ("sales", "restock", "extra", "remove_cart_stock", "view_stock", "freezer_sales", "live_flavour_view", "staging_sales", "staging_restock")
        if st.session_state.get("daily_entry_mode") not in valid_entry_modes:
            st.session_state["daily_entry_mode"] = "sales"
        if "entry_cart_shared" not in st.session_state or st.session_state["entry_cart_shared"] not in CARTS:
            st.session_state["entry_cart_shared"] = CARTS[0]

        entry_mode = st.session_state["daily_entry_mode"]
        today_val = date.today()
        yesterday_sale_date = today_val - timedelta(days=1)

        def _entry_date_display(value):
            return value.strftime("%d-%b-%Y")

        pending_sales_cnt = 0
        pending_restock_cnt = 0
        if db_conn is not None:
            try:
                _stg_cnt_df = db_conn.query(
                    """
                    SELECT entry_type, COUNT(*) AS cnt
                    FROM cart_entry_staging
                    WHERE status = 'Pending'
                      AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                    GROUP BY entry_type;
                    """,
                    params={"active_loc": get_active_location_filter()},
                    ttl="15s",
                )
                for _, _sr in _stg_cnt_df.iterrows():
                    if str(_sr["entry_type"]).upper() == "SALES":
                        pending_sales_cnt = int(_sr["cnt"] or 0)
                    elif str(_sr["entry_type"]).upper() == "RESTOCK":
                        pending_restock_cnt = int(_sr["cnt"] or 0)
            except Exception:
                pass

        def _handle_de_mode_click(_de_code):
            if _de_code == "sales":
                st.session_state.pop("_last_mismatch_modal_target", None)
            elif _de_code == "extra":
                for _cart in CARTS:
                    for _code in FLAVOR_CODES:
                        st.session_state[f"extra_stock_{_cart}_{_code}"] = "0"
            elif _de_code == "remove_cart_stock":
                for _cart in CARTS:
                    for _code in FLAVOR_CODES:
                        st.session_state[f"rm_cart_stock_{_cart}_{_code}"] = "0"
            elif _de_code == "freezer_sales":
                st.session_state["fzr_sale_form_nonce"] = int(st.session_state.get("fzr_sale_form_nonce", 0)) + 1
                st.session_state["fzr_entry_sub_mode"] = "new"
                st.session_state.pop("_editing_freezer_txn_id", None)
            st.session_state["daily_entry_mode"] = _de_code
            st.rerun()

        _de_row1_buttons = [
            ("staging_sales", f"✅ Approve Sales ({pending_sales_cnt})" if pending_sales_cnt > 0 else "✅ Approve Sales"),
            ("staging_restock", f"📥 Approve Restock ({pending_restock_cnt})" if pending_restock_cnt > 0 else "📥 Approve Restock"),
            ("sales", "🧾 Sales Entry"),
            ("restock", "📦 Restock"),
            ("extra", "➕ Extra Stock"),
        ]
        _de_row2_buttons = [
            ("remove_cart_stock", "🔄 Remove Stock"),
            ("freezer_sales", "❄️ Freezer Sale"),
            ("view_stock", "📋 View Stock"),
            ("live_flavour_view", "📱 Live POS"),
        ]

        with st.container(border=True):
            _de_r1_cols = st.columns(len(_de_row1_buttons), gap="small")
            for _de_i, (_de_code, _de_lbl) in enumerate(_de_row1_buttons):
                with _de_r1_cols[_de_i]:
                    if st.button(
                        _de_lbl,
                        key=f"de_top_mode_{_de_code}",
                        type="primary" if entry_mode == _de_code else "secondary",
                        use_container_width=True,
                    ):
                        _handle_de_mode_click(_de_code)

            _de_r2_cols = st.columns(len(_de_row2_buttons), gap="small")
            for _de_i, (_de_code, _de_lbl) in enumerate(_de_row2_buttons):
                with _de_r2_cols[_de_i]:
                    if st.button(
                        _de_lbl,
                        key=f"de_top_mode_{_de_code}",
                        type="primary" if entry_mode == _de_code else "secondary",
                        use_container_width=True,
                    ):
                        _handle_de_mode_click(_de_code)

        if True:
            # --------------------------------------------------------------
            # SALES ENTRY (CARTS) — Compact 80% Single-Page Layout
            # --------------------------------------------------------------
            if entry_mode == "sales":
                top_c1, top_c2, top_c3 = st.columns([1.4, 1.1, 1.4], gap="small", vertical_alignment="bottom")
                with top_c1:
                    cart_name = st.selectbox("Assigned Cart", CARTS, key="entry_cart_shared")

                try:
                    all_entries = list_daily_entries_with_prefill()
                    cart_entries = [e for e in all_entries if e["cart"] == cart_name]
                except Exception as e:
                    cart_entries = []
                    st.warning(f"Could not load entries from database ({e}).")

                if cart_entries:
                    if user_role == "entry":
                        cart_entries = [e for e in cart_entries if e["date"].date() == yesterday_sale_date]
                    else:
                        cart_entries = [e for e in cart_entries if e["date"].date() <= yesterday_sale_date]

                if not cart_entries:
                    st.info(f"No sales entries found for {cart_name}.")
                else:
                    labels = [_entry_date_display(e["date"].date()) for e in cart_entries]
                    yesterday_label = _entry_date_display(yesterday_sale_date)
                    default_date_index = labels.index(yesterday_label) if yesterday_label in labels else 0
                    current_sel_label = st.session_state.get(f"date_sel_{cart_name}", labels[default_date_index])
                    if current_sel_label not in labels:
                        current_sel_label = labels[default_date_index]

                    loaded = cart_entries[labels.index(current_sel_label)] if user_role != "entry" else cart_entries[0]
                    entry_id = loaded["db_id"]
                    entry_date = loaded["date"].date()
                    data_key_suffix = f"_{entry_id}"
                    opening_map = {code: int(loaded["by_code"][code]["opening"]) for code in FLAVOR_CODES}

                    prev_closings, _, prev_sale_date = get_latest_cart_closing_state_with_date(cart_name, entry_date)
                    sales_opening_mismatch = (
                        prev_sale_date is not None
                        and any(int(opening_map.get(code, 0)) != int(prev_closings.get(code, 0)) for code in FLAVOR_CODES)
                    )

                    with top_c2:
                        if user_role == "entry" or sales_opening_mismatch:
                            sel_date_label = _entry_date_display(entry_date)
                            st.text_input(
                                "Sale Date",
                                value=sel_date_label,
                                disabled=True,
                                key=f"fixed_sale_date_{cart_name}_{entry_date.strftime('%Y%m%d')}",
                            )
                        else:
                            sel_date_label = st.selectbox(
                                "Sale Date",
                                labels,
                                index=labels.index(current_sel_label),
                                key=f"date_sel_{cart_name}",
                            )

                    staff_options = load_active_staff_list()
                    default_staff_name = loaded.get("staff_name", "")
                    if default_staff_name and default_staff_name not in staff_options:
                        staff_options.append(default_staff_name)
                    with top_c3:
                        staff_name = st.selectbox(
                            "Cart Staff Assigned",
                            staff_options,
                            index=staff_options.index(default_staff_name) if default_staff_name in staff_options else 0,
                            key=f"daily_staff{data_key_suffix}",
                            disabled=sales_opening_mismatch,
                        )

                    if sales_opening_mismatch:
                        mismatch_msg = "Error:: Opening units mismatch with previous closing units - please fix this to proceed"
                        mismatch_target = f"{cart_name}_{entry_date.strftime('%Y%m%d')}"
                        if st.session_state.get("_last_mismatch_modal_target") != mismatch_target:
                            st.session_state["_last_mismatch_modal_target"] = mismatch_target
                            show_opening_mismatch_modal(mismatch_msg)
                        st.error(mismatch_msg)
                    else:
                        st.session_state.pop("_last_mismatch_modal_target", None)

                    added_map, closing_map, sold_map, amount_map = {}, {}, {}, {}

                    st.markdown(
                        f"<div class='header-box-sales'><span>🧾 Sales &amp; Closing Entry — {_entry_date_display(entry_date)}</span><span><b>{cart_name}</b></span></div>",
                        unsafe_allow_html=True,
                    )
                    with st.container(border=True):
                        live_sold_map = get_live_cart_sold_map_for_single_cart(cart_name, entry_date)
                        sales_col_w = [1.85, 0.85, 0.95, 0.95, 0.85, 0.85, 1.05]

                        hc1, hc2, hc3, hc4, hc5, hc6, hc7 = st.columns(sales_col_w, gap="small", vertical_alignment="center")
                        hc1.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour (MRP)</div>", unsafe_allow_html=True)
                        hc2.markdown("<div class='entry-grid-header'>Open</div>", unsafe_allow_html=True)
                        hc3.markdown("<div class='entry-grid-header'>+ Add ✏️</div>", unsafe_allow_html=True)
                        hc4.markdown("<div class='entry-grid-header'>Close ✏️</div>", unsafe_allow_html=True)
                        hc5.markdown("<div class='entry-grid-header'>Sold</div>", unsafe_allow_html=True)
                        hc6.markdown("<div class='entry-grid-header' style='background:#DBEAFE;color:#111111;border:1px solid #60A5FA;' title='Units recorded in Live Cart POS on this date'>Live Sold</div>", unsafe_allow_html=True)
                        hc7.markdown("<div class='entry-grid-header' style='text-align:right;'>Sale (₹)</div>", unsafe_allow_html=True)

                        for code in FLAVOR_CODES:
                            f_info = FLAVOR_MAP[code]
                            k_add, k_cls = f"add_{entry_id}_{code}", f"cls_{entry_id}_{code}"
                            if k_add not in st.session_state:
                                st.session_state[k_add] = loaded["by_code"][code]["added"]
                            if k_cls not in st.session_state:
                                st.session_state[k_cls] = loaded["by_code"][code]["closing"]

                            cur_open = opening_map[code]
                            rc1, rc2, rc3, rc4, rc5, rc6, rc7 = st.columns(sales_col_w, gap="small", vertical_alignment="center")
                            with rc1:
                                st.markdown(
                                    f"<div class='entry-grid-cell-flavour'><span>{f_info['name']}</span><span style='color:#2563EB;font-size:10.5px;'>₹{f_info['mrp']:.0f}</span></div>",
                                    unsafe_allow_html=True,
                                )
                            with rc2:
                                st.markdown(f"<div class='entry-grid-cell'>{cur_open}</div>", unsafe_allow_html=True)
                            with rc3:
                                cur_add = _int_num(
                                    st.number_input(
                                        f"Add {f_info['name']}",
                                        min_value=0,
                                        step=1,
                                        format="%d",
                                        key=k_add,
                                        label_visibility="collapsed",
                                        disabled=sales_opening_mismatch,
                                    )
                                )
                            with rc4:
                                cur_cls = _int_num(
                                    st.number_input(
                                        f"Close {f_info['name']}",
                                        min_value=0,
                                        step=1,
                                        format="%d",
                                        key=k_cls,
                                        label_visibility="collapsed",
                                        disabled=sales_opening_mismatch,
                                    )
                                )
                            cur_sold = cur_open + cur_add - cur_cls
                            live_sold_u = int(live_sold_map.get(code, 0))
                            cur_amt = max(0, cur_sold) * float(f_info["mrp"])
                            added_map[code], closing_map[code], sold_map[code], amount_map[code] = cur_add, cur_cls, cur_sold, cur_amt
                            with rc5:
                                st.markdown(f"<div class='entry-grid-cell-sold'>{cur_sold}</div>", unsafe_allow_html=True)
                            with rc6:
                                st.markdown(f"<div class='entry-grid-cell-livesold' title='Live POS sold count for {f_info['name']}'>{live_sold_u}</div>", unsafe_allow_html=True)
                            with rc7:
                                st.markdown(f"<div class='entry-grid-cell-amount'>₹{cur_amt:,.0f}</div>", unsafe_allow_html=True)

                        tot_open = sum(opening_map.values())
                        tot_add = sum(added_map.values())
                        tot_close = sum(closing_map.values())
                        tot_sold = sum(sold_map.values())
                        tot_live_sold = sum(live_sold_map.values())
                        calculated_mrp_total = float(sum(amount_map.values()))

                        tc1, tc2, tc3, tc4, tc5, tc6, tc7 = st.columns(sales_col_w, gap="small", vertical_alignment="center")
                        tc1.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                        tc2.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_open}</div>", unsafe_allow_html=True)
                        tc3.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_add}</div>", unsafe_allow_html=True)
                        tc4.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_close}</div>", unsafe_allow_html=True)
                        tc5.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#C43D17;'>{tot_sold}</div>", unsafe_allow_html=True)
                        tc6.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#1B5E91;'>{tot_live_sold}</div>", unsafe_allow_html=True)
                        tc7.markdown(f"<div class='entry-grid-total-row' style='text-align:right;color:#047857;'>₹{calculated_mrp_total:,.0f}</div>", unsafe_allow_html=True)

                        k_tot = f"daily_total{data_key_suffix}"
                        k_prev_calc = f"daily_prev_calc{data_key_suffix}"

                        if k_tot not in st.session_state:
                            st.session_state[k_tot] = (
                                f"{loaded['total']:.2f}"
                                if (loaded["total"] > 0 and not loaded.get("is_prefill"))
                                else f"{calculated_mrp_total:.2f}"
                            )
                            st.session_state[k_prev_calc] = calculated_mrp_total
                        elif st.session_state.get(k_prev_calc) != calculated_mrp_total:
                            st.session_state[k_tot] = f"{calculated_mrp_total:.2f}"
                            st.session_state[k_prev_calc] = calculated_mrp_total

                        if f"daily_phonepe{data_key_suffix}" not in st.session_state:
                            st.session_state[f"daily_phonepe{data_key_suffix}"] = f"{loaded['phonepe']:.2f}"
                        if f"daily_adv{data_key_suffix}" not in st.session_state:
                            st.session_state[f"daily_adv{data_key_suffix}"] = f"{loaded.get('staff_advance', 0.0):.2f}"
                        if f"daily_food{data_key_suffix}" not in st.session_state:
                            st.session_state[f"daily_food{data_key_suffix}"] = f"{loaded.get('food_tea_cash', 0.0):.2f}"
                        if f"daily_cash{data_key_suffix}" not in st.session_state:
                            st.session_state[f"daily_cash{data_key_suffix}"] = f"{loaded['cash']:.2f}"
                        if f"daily_leak_explained{data_key_suffix}" not in st.session_state:
                            st.session_state[f"daily_leak_explained{data_key_suffix}"] = f"{loaded.get('cash_leakage_explained', 0.0):.2f}"

                        _clean_loaded_rem = re.sub(
                            r"\[(?:mobile\s*app|web\s*app)\]",
                            "",
                            str(loaded.get("remarks") or ""),
                            flags=re.IGNORECASE,
                        ).strip()
                        _default_web_rem = f"{_clean_loaded_rem} [web app]".strip()
                        _rem_state_key = f"daily_remarks{data_key_suffix}"
                        if _rem_state_key not in st.session_state:
                            st.session_state[_rem_state_key] = _default_web_rem
                        elif "[mobile app]" in str(st.session_state.get(_rem_state_key, "")).lower() or not str(st.session_state.get(_rem_state_key, "")).strip():
                            _cur_r = re.sub(r"\[(?:mobile\s*app|web\s*app)\]", "", str(st.session_state.get(_rem_state_key, "")), flags=re.IGNORECASE).strip()
                            st.session_state[_rem_state_key] = f"{_cur_r} [web app]".strip()

                        # Compact 2-row financial & remarks bar (no scrolling required)
                        pay_r1_c1, pay_r1_c2, pay_r1_c3, pay_r1_c4 = st.columns(4, gap="small")
                        with pay_r1_c1:
                            total_collection_val = _num(st.text_input("Total collection (₹)", key=k_tot, disabled=sales_opening_mismatch))
                        with pay_r1_c2:
                            phonepe_val = _num(st.text_input("PhonePe / UPI (₹)", key=f"daily_phonepe{data_key_suffix}", disabled=sales_opening_mismatch))
                        with pay_r1_c3:
                            cash_val = _num(st.text_input("Cash Collected (₹)", key=f"daily_cash{data_key_suffix}", disabled=sales_opening_mismatch))
                        with pay_r1_c4:
                            staff_advance_val = _num(st.text_input("Advance to staff (₹)", key=f"daily_adv{data_key_suffix}", disabled=sales_opening_mismatch))

                        pay_r2_c1, pay_r2_c2, pay_r2_c3, pay_r2_c4 = st.columns(4, gap="small")
                        with pay_r2_c1:
                            food_tea_val = _num(st.text_input("Cash Food / Tea (₹)", key=f"daily_food{data_key_suffix}", disabled=sales_opening_mismatch))

                        leakage_before_explanation = total_collection_val - phonepe_val - staff_advance_val - food_tea_val - cash_val
                        available_cash_leakage = max(0.0, leakage_before_explanation)

                        with pay_r2_c2:
                            cash_leakage_explained = max(
                                0.0,
                                _num(st.text_input(
                                    "Leakage Explained (₹)",
                                    key=f"daily_leak_explained{data_key_suffix}",
                                    placeholder="0.00",
                                    disabled=sales_opening_mismatch,
                                )),
                            )
                        cash_leakage_unexplained = max(0.0, available_cash_leakage - cash_leakage_explained)
                        with pay_r2_c3:
                            _unexp_key_prefix = "daily_leak_unexp_alert" if cash_leakage_unexplained > 0.001 else "daily_leak_unexp_ro"
                            _unexp_w_key = f"{_unexp_key_prefix}{data_key_suffix}"
                            st.session_state[_unexp_w_key] = f"₹{cash_leakage_unexplained:,.2f}"
                            st.text_input(
                                "Leakage Unexplained (₹)",
                                key=_unexp_w_key,
                                disabled=True,
                            )
                        with pay_r2_c4:
                            remarks = st.text_input(
                                "Remarks",
                                value=_default_web_rem,
                                key=_rem_state_key,
                                placeholder="Remarks (mandatory if leakage)...",
                                disabled=sales_opening_mismatch,
                            )

                        explained_exceeds_available = cash_leakage_explained > available_cash_leakage + 0.001
                        has_leakage = cash_leakage_explained > 0.001 or cash_leakage_unexplained > 0.001
                        if explained_exceeds_available:
                            st.error(f"Cash Leakage (Explained) cannot exceed the current leakage amount of ₹{available_cash_leakage:,.2f}.")
                        elif has_leakage:
                            st.markdown(
                                "<p style='color:#C41C1C; font-weight:bold; font-size:11px; margin: 1px 0 !important;'>"
                                "⚠️ Remarks are mandatory when explained or unexplained cash leakage is present."
                                "</p>",
                                unsafe_allow_html=True,
                            )

                        manual_remarks = re.sub(
                            r"\[(?:web\s*app|mobile\s*app)\]",
                            "",
                            str(remarks or ""),
                            flags=re.IGNORECASE,
                        ).strip()

                    if any(s < 0 for s in sold_map.values()):
                        st.error(f"Sales negative for at least one flavour on {_entry_date_display(entry_date)} - check closing count.")

                    if st.button("💾 Submit Sales Entry", type="primary", use_container_width=False, key=f"submit_sales_{entry_id}", disabled=sales_opening_mismatch):
                        if any(s < 0 for s in sold_map.values()):
                            st.error("Sales works out negative for at least one flavour - fix closing count before saving.")
                        elif explained_exceeds_available:
                            st.error("Reduce Cash Leakage (Explained) so it does not exceed the current leakage amount.")
                        elif has_leakage and not manual_remarks:
                            st.error("Remarks/reason is mandatory when explained or unexplained cash leakage is present.")
                        else:
                            try:
                                selected_staff = "" if staff_name == "Select Staff" else staff_name
                                sync_daily_entry(
                                    entry_date,
                                    cart_name,
                                    added_map,
                                    closing_map,
                                    opening_map,
                                    sold_map,
                                    total_collection_val,
                                    phonepe_val,
                                    cash_val,
                                    remarks,
                                    selected_staff,
                                    staff_advance_val,
                                    food_tea_val,
                                    cash_leakage_explained=cash_leakage_explained,
                                    cash_leakage_unexplained=cash_leakage_unexplained,
                                )
                                if entry_date == yesterday_sale_date:
                                    sync_today_opening_after_sales_update(today_val, cart_name, closing_map)
                                st.cache_data.clear()
                                show_success_modal(
                                    f"Sales entry saved successfully for {cart_name}. Total sold: {tot_sold} units."
                                )
                            except Exception as e:
                                st.error(f"Could not save Sales Entry - {e}")

            # --------------------------------------------------------------
            # SALES ENTRY (FREEZER) — Compact 80% Single-Page Layout
            # --------------------------------------------------------------
            # --------------------------------------------------------------
            # ADMIN STAGING REVIEW: SALES ENTRIES
            # --------------------------------------------------------------
            elif entry_mode == "staging_sales":
                st.markdown(
                    "<div class='header-box-sales' style='margin-bottom:14px;'><span>✅ Approve Sales — Cart Staff Submissions</span><span><b>Admin Approval</b></span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

                sf1, sf2, sf3 = st.columns([1.2, 1.2, 2.0], gap="small", vertical_alignment="bottom")
                with sf1:
                    stg_sales_status = st.selectbox(
                        "Status Filter",
                        ["Pending", "Final", "All"],
                        index=0,
                        key="stg_sales_status_filter",
                    )
                with sf2:
                    if st.button("🔄 Refresh Staging", key="stg_sales_refresh_btn", use_container_width=True):
                        st.cache_data.clear()
                        st.rerun()

                try:
                    stg_sales_df = db_conn.query(
                        """
                        SELECT *
                        FROM cart_entry_staging
                        WHERE entry_type = 'SALES'
                          AND (:st = 'All' OR status = :st)
                          AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                        ORDER BY
                            CASE WHEN status = 'Pending' THEN 0 ELSE 1 END,
                            entry_date DESC,
                            submitted_at DESC;
                        """,
                        params={"st": stg_sales_status, "active_loc": get_active_location_filter()},
                        ttl="10s",
                    )
                except Exception as e:
                    stg_sales_df = pd.DataFrame()
                    st.error(f"Could not load staging sales entries (ensure SQL migration is applied): {e}")

                if stg_sales_df.empty:
                    st.info(f"No {stg_sales_status.lower() if stg_sales_status != 'All' else ''} staging sales entries found.")
                else:
                    for _, srow in stg_sales_df.iterrows():
                        sid = int(srow["id"])
                        s_date = pd.to_datetime(srow["entry_date"]).date()
                        s_cart = str(srow["cart_name"])
                        s_staff = str(srow.get("staff_name") or "")
                        s_status = str(srow.get("status") or "Pending")
                        is_final = s_status == "Final"
                        s_sub_by = str(srow.get("submitted_by") or "Cart Staff")
                        s_sub_at = pd.to_datetime(srow["submitted_at"]).strftime("%d-%b %H:%M") if pd.notna(srow.get("submitted_at")) else "—"
                        s_app_by = str(srow.get("approved_by") or "Admin")
                        s_app_at = pd.to_datetime(srow["approved_at"]).strftime("%d-%b %H:%M") if pd.notna(srow.get("approved_at")) else "—"

                        raw_items = srow.get("flavor_items") or {}
                        if isinstance(raw_items, str):
                            try:
                                raw_items = json.loads(raw_items)
                            except Exception:
                                raw_items = {}

                        badge_html = (
                            "<span style='background:#DCFCE7;color:#166534;border:1px solid #86EFAC;padding:2px 9px;border-radius:999px;font-weight:800;font-size:12px;'>🔒 Final</span>"
                            if is_final
                            else "<span style='background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;padding:2px 9px;border-radius:999px;font-weight:800;font-size:12px;'>⏳ Pending</span>"
                        )

                        with st.container(border=True):
                            st.markdown(
                                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;'>"
                                f"<div><b style='font-size:15px;color:#1E2252;'>{escape(s_cart)}</b> &nbsp;|&nbsp; <span style='color:#475569;font-weight:700;'>{_entry_date_display(s_date)}</span> &nbsp;|&nbsp; Staff: <b>{escape(s_staff or '—')}</b></div>"
                                f"<div>{badge_html}</div>"
                                f"</div>"
                                f"<div style='font-size:11.5px;color:#64748B;margin-bottom:8px;'>Submitted by <b>{escape(s_sub_by)}</b> at {s_sub_at}"
                                + (f" &nbsp;•&nbsp; Approved by <b>{escape(s_app_by)}</b> at {s_app_at}" if is_final else "")
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                            # Flavour Table: Open | +Add | Close (Editable) | Sold | Sale (₹)
                            stg_col_w = [1.9, 0.85, 0.85, 1.0, 0.85, 1.1]
                            sh1, sh2, sh3, sh4, sh5, sh6 = st.columns(stg_col_w, gap="small", vertical_alignment="center")
                            sh1.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour (MRP)</div>", unsafe_allow_html=True)
                            sh2.markdown("<div class='entry-grid-header'>Open</div>", unsafe_allow_html=True)
                            sh3.markdown("<div class='entry-grid-header'>+ Add</div>", unsafe_allow_html=True)
                            sh4.markdown("<div class='entry-grid-header'>Close" + ("" if is_final else " ✏️") + "</div>", unsafe_allow_html=True)
                            sh5.markdown("<div class='entry-grid-header'>Sold</div>", unsafe_allow_html=True)
                            sh6.markdown("<div class='entry-grid-header' style='text-align:right;'>Sale (₹)</div>", unsafe_allow_html=True)

                            open_map, add_map, close_map, sold_map, amount_map = {}, {}, {}, {}, {}
                            for code in FLAVOR_CODES:
                                f_info = FLAVOR_MAP[code]
                                it = raw_items.get(code, {}) if isinstance(raw_items, dict) else {}
                                op = int(_num(it.get("opening", 0)))
                                ad = int(_num(it.get("added", 0)))
                                orig_cl = int(_num(it.get("closing", op + ad)))

                                k_cls = f"stg_s_cls_{sid}_{code}"
                                if k_cls not in st.session_state:
                                    st.session_state[k_cls] = orig_cl

                                rc1, rc2, rc3, rc4, rc5, rc6 = st.columns(stg_col_w, gap="small", vertical_alignment="center")
                                with rc1:
                                    st.markdown(
                                        f"<div class='entry-grid-cell-flavour'><span>{escape(f_info['name'])}</span><span style='color:#2563EB;font-size:10.5px;'>₹{f_info['mrp']:.0f}</span></div>",
                                        unsafe_allow_html=True,
                                    )
                                with rc2:
                                    st.markdown(f"<div class='entry-grid-cell'>{op}</div>", unsafe_allow_html=True)
                                with rc3:
                                    st.markdown(f"<div class='entry-grid-cell'>{ad}</div>", unsafe_allow_html=True)
                                with rc4:
                                    if is_final:
                                        cur_cl = orig_cl
                                        st.markdown(f"<div class='entry-grid-cell'>{cur_cl}</div>", unsafe_allow_html=True)
                                    else:
                                        cur_cl = _int_num(
                                            st.number_input(
                                                f"Close {sid} {code}",
                                                min_value=0,
                                                step=1,
                                                format="%d",
                                                key=k_cls,
                                                label_visibility="collapsed",
                                            )
                                        )
                                cur_sd = op + ad - cur_cl
                                cur_amt = max(0, cur_sd) * float(f_info["mrp"])
                                open_map[code] = op
                                add_map[code] = ad
                                close_map[code] = cur_cl
                                sold_map[code] = cur_sd
                                amount_map[code] = cur_amt

                                with rc5:
                                    sold_style = "color:#DC2626;background:#FEF2F2;border-color:#FCA5A5;" if cur_sd < 0 else ""
                                    st.markdown(f"<div class='entry-grid-cell-sold' style='{sold_style}'>{cur_sd}</div>", unsafe_allow_html=True)
                                with rc6:
                                    st.markdown(f"<div class='entry-grid-cell-amount'>₹{cur_amt:,.0f}</div>", unsafe_allow_html=True)

                            tot_open = sum(open_map.values())
                            tot_add = sum(add_map.values())
                            tot_close = sum(close_map.values())
                            tot_sold = sum(sold_map.values())
                            calc_mrp_total = float(sum(amount_map.values()))

                            tc1, tc2, tc3, tc4, tc5, tc6 = st.columns(stg_col_w, gap="small", vertical_alignment="center")
                            tc1.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                            tc2.markdown(f"<div class='entry-grid-total-row'>{tot_open}</div>", unsafe_allow_html=True)
                            tc3.markdown(f"<div class='entry-grid-total-row'>{tot_add}</div>", unsafe_allow_html=True)
                            tc4.markdown(f"<div class='entry-grid-total-row'>{tot_close}</div>", unsafe_allow_html=True)
                            tc5.markdown(f"<div class='entry-grid-total-row' style='color:#C43D17;'>{tot_sold} pcs</div>", unsafe_allow_html=True)
                            tc6.markdown(f"<div class='entry-grid-total-row' style='text-align:right;color:#047857;'>₹{calc_mrp_total:,.0f}</div>", unsafe_allow_html=True)

                            # Live Financial Fields (All Editable for Admin when Pending, Auto-Recalculated on Close Change)
                            init_tot = float(_num(srow.get("total_collection", calc_mrp_total)))
                            init_ph = float(_num(srow.get("phonepe", 0)))
                            init_adv = float(_num(srow.get("staff_advance", 0)))
                            init_food = float(_num(srow.get("food_tea_cash", 0)))
                            init_l_expl = float(_num(srow.get("cash_leakage_explained", 0)))
                            init_l_unexpl = float(_num(srow.get("cash_leakage_unexplained", 0)))
                            init_l_tot = float(_num(srow.get("cash_leakage", init_l_expl + init_l_unexpl)))
                            if init_l_expl == 0 and init_l_unexpl == 0 and init_l_tot > 0:
                                init_l_unexpl = init_l_tot
                            init_cash = float(_num(srow.get("cash", max(0.0, init_tot - init_ph - init_adv - init_food - init_l_expl - init_l_unexpl))))

                            k_tot = f"stg_s_tot_{sid}"
                            k_prev_calc = f"stg_s_prev_calc_{sid}"
                            k_ph = f"stg_s_ph_{sid}"
                            k_cs = f"stg_s_cs_{sid}"
                            k_adv = f"stg_s_adv_{sid}"
                            k_lexp = f"stg_s_lexp_{sid}"
                            k_lunexp = f"stg_s_lunexp_{sid}"
                            k_sig = f"stg_s_sig_{sid}"

                            if k_tot not in st.session_state:
                                st.session_state[k_tot] = f"{(init_tot if init_tot > 0 else calc_mrp_total):.2f}"
                                st.session_state[k_prev_calc] = calc_mrp_total
                            elif not is_final and st.session_state.get(k_prev_calc) != calc_mrp_total:
                                st.session_state[k_tot] = f"{calc_mrp_total:.2f}"
                                st.session_state[k_prev_calc] = calc_mrp_total

                            if k_ph not in st.session_state:
                                st.session_state[k_ph] = f"{init_ph:.2f}"
                            if k_cs not in st.session_state:
                                st.session_state[k_cs] = f"{init_cash:.2f}"
                            if k_adv not in st.session_state:
                                st.session_state[k_adv] = f"{init_adv:.2f}"
                            if k_lexp not in st.session_state:
                                st.session_state[k_lexp] = f"{init_l_expl:.2f}"
                            if k_lunexp not in st.session_state:
                                st.session_state[k_lunexp] = f"{init_l_unexpl:.2f}"

                            # Compact Summary Strip
                            st.markdown(
                                f"<div style='display:flex;justify-content:space-between;align-items:center;background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;padding:6px 12px;margin:8px 0 6px 0;font-size:12.5px;'>"
                                f"<span>🍦 <b>Total Units Sold:</b> <span style='color:#C43D17;font-weight:900;'>{tot_sold} pcs</span></span>"
                                f"<span>💰 <b>Calculated Sale Value:</b> <span style='color:#047857;font-weight:900;'>₹{calc_mrp_total:,.0f}</span></span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                            fr1_c1, fr1_c2, fr1_c3 = st.columns(3, gap="small")
                            with fr1_c1:
                                ed_tot = max(0.0, _num(st.text_input("Total Collection (₹)", key=k_tot, disabled=is_final)))
                            with fr1_c2:
                                ed_ph = max(0.0, _num(st.text_input("PhonePe (₹)", key=k_ph, disabled=is_final)))
                            with fr1_c3:
                                ed_cash = max(0.0, _num(st.text_input("Cash (₹)", key=k_cs, disabled=is_final)))

                            fr2_c1, fr2_c2, fr2_c3 = st.columns(3, gap="small")
                            with fr2_c1:
                                ed_adv = max(0.0, _num(st.text_input("Advance (₹)", key=k_adv, disabled=is_final)))
                            with fr2_c2:
                                ed_lexp = max(0.0, _num(st.text_input("Leakage (Expl) (₹)", key=k_lexp, disabled=is_final)))

                            # Auto-recalculate Leakage (Unexpl) whenever Close/Total/PhonePe/Cash/Advance/Leakage(Expl) changes,
                            # while still allowing Admin to manually edit Leakage (Unexpl) directly.
                            curr_sig = f"{ed_tot:.2f}|{ed_ph:.2f}|{ed_cash:.2f}|{ed_adv:.2f}|{ed_lexp:.2f}"
                            auto_unexpl = max(0.0, ed_tot - ed_ph - ed_cash - ed_adv - init_food - ed_lexp)
                            if not is_final:
                                if k_sig not in st.session_state:
                                    st.session_state[k_sig] = curr_sig
                                elif st.session_state.get(k_sig) != curr_sig:
                                    st.session_state[k_lunexp] = f"{auto_unexpl:.2f}"
                                    st.session_state[k_sig] = curr_sig

                            with fr2_c3:
                                ed_lunexp = max(0.0, _num(st.text_input("Leakage (Unexpl) (₹)", key=k_lunexp, disabled=is_final)))

                            rem_str = str(srow.get("remarks") or "")
                            ed_c1, ed_c2 = st.columns([1.2, 2.5], gap="small")
                            with ed_c1:
                                staff_opts = load_active_staff_list()
                                if s_staff and s_staff not in staff_opts:
                                    staff_opts.append(s_staff)
                                chosen_staff = st.selectbox(
                                    "Staff",
                                    staff_opts,
                                    index=staff_opts.index(s_staff) if s_staff in staff_opts else 0,
                                    key=f"stg_sales_staff_{sid}",
                                    disabled=is_final,
                                )
                            with ed_c2:
                                chosen_rem = st.text_input(
                                    "Admin Remarks (why changes were made)",
                                    value=rem_str,
                                    placeholder="Add reason for any edits or approval notes...",
                                    key=f"stg_sales_rem_{sid}",
                                    disabled=is_final,
                                )

                            if any(sd < 0 for sd in sold_map.values()):
                                st.error("Close cannot exceed Open + Add for any flavour (Sold is negative).")

                            if not is_final:
                                if st.button(
                                    "✅ Approve & Post to Actuals",
                                    type="primary",
                                    key=f"approve_stg_sales_{sid}",
                                ):
                                    if any(sd < 0 for sd in sold_map.values()):
                                        st.error("Fix negative Sold units before approving.")
                                    else:
                                        try:
                                            final_staff = "" if chosen_staff == "Select Staff" else chosen_staff
                                            final_leak_tot = ed_lexp + ed_lunexp
                                            sync_daily_entry(
                                                s_date,
                                                s_cart,
                                                add_map,
                                                close_map,
                                                open_map,
                                                sold_map,
                                                ed_tot,
                                                ed_ph,
                                                ed_cash,
                                                chosen_rem,
                                                final_staff,
                                                ed_adv,
                                                init_food,
                                                cash_leakage_explained=ed_lexp,
                                                cash_leakage_unexplained=ed_lunexp,
                                            )
                                            if s_date == yesterday_sale_date:
                                                sync_today_opening_after_sales_update(today_val, s_cart, close_map)

                                            updated_flavor_items = {
                                                code: {
                                                    "opening": int(open_map[code]),
                                                    "added": int(add_map[code]),
                                                    "closing": int(close_map[code]),
                                                    "sold": int(sold_map[code]),
                                                }
                                                for code in FLAVOR_CODES
                                            }
                                            with db_conn.session as s:
                                                posted_row = s.execute(
                                                    text("SELECT id FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :ct;"),
                                                    {"dt": s_date, "ct": s_cart},
                                                ).fetchone()
                                                posted_id = int(posted_row[0]) if posted_row else None
                                                s.execute(
                                                    text("""
                                                        UPDATE cart_entry_staging
                                                        SET status = 'Final',
                                                            staff_name = :stf,
                                                            flavor_items = CAST(:fitems AS jsonb),
                                                            total_collection = :tot,
                                                            phonepe = :ph,
                                                            cash = :cs,
                                                            staff_advance = :adv,
                                                            cash_leakage_explained = :lexp,
                                                            cash_leakage_unexplained = :lunexp,
                                                            cash_leakage = :ltot,
                                                            remarks = :rem,
                                                            approved_by = 'Admin',
                                                            approved_at = NOW(),
                                                            posted_daily_entry_id = :pid,
                                                            updated_at = NOW()
                                                        WHERE id = :sid;
                                                    """),
                                                    {
                                                        "stf": final_staff,
                                                        "fitems": json.dumps(updated_flavor_items),
                                                        "tot": float(ed_tot),
                                                        "ph": float(ed_ph),
                                                        "cs": float(ed_cash),
                                                        "adv": float(ed_adv),
                                                        "lexp": float(ed_lexp),
                                                        "lunexp": float(ed_lunexp),
                                                        "ltot": float(final_leak_tot),
                                                        "rem": chosen_rem,
                                                        "pid": posted_id,
                                                        "sid": sid,
                                                    },
                                                )
                                                s.commit()
                                            st.cache_data.clear()
                                            show_success_modal(f"Staging Sales #{sid} ({s_cart}, {_entry_date_display(s_date)}) approved, posted to actuals, and marked Final!")
                                        except Exception as e:
                                            st.error(f"Could not approve staging sales entry: {e}")

            # --------------------------------------------------------------
            # ADMIN STAGING REVIEW: RESTOCK ENTRIES
            # --------------------------------------------------------------
            elif entry_mode == "staging_restock":
                st.markdown(
                    "<div class='header-box-restock' style='margin-bottom:14px;'><span>📥 Approve Restock — Cart Staff Submissions</span><span><b>Admin Approval</b></span></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                rf1, rf2, rf3 = st.columns([1.2, 1.2, 2.0], gap="small", vertical_alignment="bottom")
                with rf1:
                    stg_restock_status = st.selectbox(
                        "Status Filter",
                        ["Pending", "Final", "All"],
                        index=0,
                        key="stg_restock_status_filter",
                    )
                with rf2:
                    if st.button("🔄 Refresh Staging", key="stg_restock_refresh_btn", use_container_width=True):
                        st.cache_data.clear()
                        st.rerun()

                try:
                    stg_restock_df = db_conn.query(
                        """
                        SELECT *
                        FROM cart_entry_staging
                        WHERE entry_type = 'RESTOCK'
                          AND (:st = 'All' OR status = :st)
                          AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                        ORDER BY
                            CASE WHEN status = 'Pending' THEN 0 ELSE 1 END,
                            entry_date DESC,
                            submitted_at DESC;
                        """,
                        params={"st": stg_restock_status, "active_loc": get_active_location_filter()},
                        ttl="10s",
                    )
                except Exception as e:
                    stg_restock_df = pd.DataFrame()
                    st.error(f"Could not load staging restock entries (ensure SQL migration is applied): {e}")

                if stg_restock_df.empty:
                    st.info(f"No {stg_restock_status.lower() if stg_restock_status != 'All' else ''} staging restock entries found.")
                else:
                    for _, rrow in stg_restock_df.iterrows():
                        rid = int(rrow["id"])
                        r_date = pd.to_datetime(rrow["entry_date"]).date()
                        r_cart = str(rrow["cart_name"])
                        r_staff = str(rrow.get("staff_name") or "")
                        r_status = str(rrow.get("status") or "Pending")
                        is_final = r_status == "Final"
                        r_sub_by = str(rrow.get("submitted_by") or "Cart Staff")
                        r_sub_at = pd.to_datetime(rrow["submitted_at"]).strftime("%d-%b %H:%M") if pd.notna(rrow.get("submitted_at")) else "—"
                        r_app_by = str(rrow.get("approved_by") or "Admin")
                        r_app_at = pd.to_datetime(rrow["approved_at"]).strftime("%d-%b %H:%M") if pd.notna(rrow.get("approved_at")) else "—"

                        raw_items = rrow.get("flavor_items") or {}
                        if isinstance(raw_items, str):
                            try:
                                raw_items = json.loads(raw_items)
                            except Exception:
                                raw_items = {}

                        badge_html = (
                            "<span style='background:#DCFCE7;color:#166534;border:1px solid #86EFAC;padding:2px 9px;border-radius:999px;font-weight:800;font-size:12px;'>🔒 Final</span>"
                            if is_final
                            else "<span style='background:#FEF3C7;color:#92400E;border:1px solid #FCD34D;padding:2px 9px;border-radius:999px;font-weight:800;font-size:12px;'>⏳ Pending</span>"
                        )

                        with st.container(border=True):
                            st.markdown(
                                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;'>"
                                f"<div><b style='font-size:15px;color:#14532D;'>{r_cart}</b> &nbsp;|&nbsp; <span style='color:#6B5138;font-weight:700;'>{_entry_date_display(r_date)}</span> &nbsp;|&nbsp; Staff: <b>{r_staff or '—'}</b></div>"
                                f"<div>{badge_html}</div>"
                                f"</div>"
                                f"<div style='font-size:11.5px;color:#78716C;margin-bottom:8px;'>Submitted by <b>{r_sub_by}</b> at {r_sub_at}"
                                + (f" &nbsp;•&nbsp; Approved by <b>{r_app_by}</b> at {r_app_at}" if is_final else "")
                                + "</div>",
                                unsafe_allow_html=True,
                            )

                            r_rows = []
                            r_open_map, r_add_map = {}, {}
                            for code in FLAVOR_CODES:
                                f_info = FLAVOR_MAP[code]
                                it = raw_items.get(code, {}) if isinstance(raw_items, dict) else {}
                                op = int(_num(it.get("opening", 0)))
                                ad = int(_num(it.get("restock", it.get("added", 0))))
                                r_open_map[code] = op
                                r_add_map[code] = ad
                                r_rows.append({
                                    "Flavour": f_info["name"],
                                    "Opening": op,
                                    "+ Restock": ad,
                                    "Total Opening": op + ad,
                                })
                            st.dataframe(pd.DataFrame(r_rows), hide_index=True, use_container_width=True)
                            tot_rstk = sum(r_add_map.values())
                            st.caption(f"Total Restock Added: **+{tot_rstk} pcs** | Total Opening After Restock: **{sum(r_open_map.values()) + tot_rstk} pcs**")

                            if not is_final:
                                staff_opts = load_active_staff_list()
                                if r_staff and r_staff not in staff_opts:
                                    staff_opts.append(r_staff)
                                chosen_r_staff = st.selectbox(
                                    "Staff",
                                    staff_opts,
                                    index=staff_opts.index(r_staff) if r_staff in staff_opts else 0,
                                    key=f"stg_restock_staff_{rid}",
                                )
                                if st.button(
                                    "✅ Approve & Post to Actuals",
                                    type="primary",
                                    key=f"approve_stg_restock_{rid}",
                                ):
                                    try:
                                        final_staff = "" if chosen_r_staff == "Select Staff" else chosen_r_staff
                                        sync_today_restock_entry(r_date, r_cart, final_staff, r_open_map, r_add_map)
                                        with db_conn.session as s:
                                            posted_row = s.execute(
                                                text("SELECT id FROM daily_cart_entries WHERE entry_date = :dt AND cart_name = :ct;"),
                                                {"dt": r_date, "ct": r_cart},
                                            ).fetchone()
                                            posted_id = int(posted_row[0]) if posted_row else None
                                            s.execute(
                                                text("""
                                                    UPDATE cart_entry_staging
                                                    SET status = 'Final',
                                                        staff_name = :stf,
                                                        approved_by = 'Admin',
                                                        approved_at = NOW(),
                                                        posted_daily_entry_id = :pid,
                                                        updated_at = NOW()
                                                    WHERE id = :rid;
                                                """),
                                                {"stf": final_staff, "pid": posted_id, "rid": rid},
                                            )
                                            s.commit()
                                        st.cache_data.clear()
                                        show_success_modal(f"Staging Restock #{rid} ({r_cart}, {_entry_date_display(r_date)}) approved, posted to actuals, and marked Final!")
                                    except Exception as e:
                                        st.error(f"Could not approve staging restock entry: {e}")


            elif entry_mode == "freezer_sales":
                if "fzr_entry_sub_mode" not in st.session_state:
                    st.session_state["fzr_entry_sub_mode"] = "new"

                fzr_sub_mode = st.session_state["fzr_entry_sub_mode"]
                editing_txn_id = st.session_state.get("_editing_freezer_txn_id")

                freezer_asset_name = get_freezer_asset_name_for_location(CITY)
                staff_options = load_active_staff_list()

                # MODE A: LIST OF PREVIOUS FREEZER SALE TRANSACTIONS
                if fzr_sub_mode == "list":
                    hdr_c1, hdr_c2, hdr_c3 = st.columns([1.9, 1.2, 1.2], gap="small", vertical_alignment="bottom")
                    with hdr_c1:
                        st.text_input("Freezer Asset", value=freezer_asset_name, disabled=True, key="fzr_list_asset_ro")
                    with hdr_c2:
                        if st.button(
                            "➕ New Freezer Sale",
                            key="btn_fzr_mode_new",
                            type="primary" if fzr_sub_mode == "new" else "secondary",
                            use_container_width=True
                        ):
                            st.session_state["fzr_entry_sub_mode"] = "new"
                            st.session_state.pop("_editing_freezer_txn_id", None)
                            st.session_state["fzr_sale_form_nonce"] = int(st.session_state.get("fzr_sale_form_nonce", 0)) + 1
                            st.rerun()
                    with hdr_c3:
                        if st.button(
                            "✏️ Past Entries",
                            key="btn_fzr_mode_list",
                            type="primary",
                            use_container_width=True
                        ):
                            st.session_state["fzr_entry_sub_mode"] = "list"
                            st.session_state.pop("_editing_freezer_txn_id", None)
                            st.rerun()
                    prev_txns_df = load_freezer_sale_transactions_df()
                    if prev_txns_df.empty:
                        st.info("No previous Freezer sale transactions found.")
                    else:
                        col_w = [0.65, 0.85, 0.80, 0.98, 0.98, 0.65, 0.80, 0.80, 0.80, 0.80, 1.40, 1.05, 0.55, 0.55]
                        hdrs = [
                            ("Txn #", "Transaction ID"),
                            ("Date", "Sale Date"),
                            ("Time", "Submitted Time"),
                            ("Freezer", "Freezer Name"),
                            ("Sold By", "Staff Member"),
                            ("Units", "Total Units Sold"),
                            ("Value", "Total Sale Value"),
                            ("PhonePe", "PhonePe Collected"),
                            ("Cash", "Cash Collected"),
                            ("Leakage", "Leakage Amount"),
                            ("Flavours", "Flavour Breakdown"),
                            ("Reason", "Reason / Remarks"),
                            ("Edit", "Edit Transaction"),
                            ("Del", "Delete Transaction"),
                        ]
                        h_cols = st.columns(col_w, gap="small")
                        for hc, (h_txt, h_tip) in zip(h_cols, hdrs):
                            align = "justify-content:flex-end;" if h_txt in ("Value", "PhonePe", "Cash", "Leakage") else ("justify-content:center;" if h_txt in ("Txn #", "Date", "Time", "Units", "Edit", "Del") else "")
                            hc.markdown(f"<div class='ledger-tbl-header' style='{align}' title='{escape(h_tip)}'>{h_txt}</div>", unsafe_allow_html=True)

                        for _, tr in prev_txns_df.head(100).iterrows():
                            tid = int(tr["id"])
                            dt_s = pd.to_datetime(tr["sale_date"]).strftime("%d-%b-%y")
                            tm_s = pd.to_datetime(tr["created_at"]).strftime("%I:%M %p") if pd.notna(tr.get("created_at")) else "—"
                            fn_s = str(tr.get("freezer_name") or freezer_asset_name)
                            sb_s = str(tr.get("sold_by") or "—")
                            un_v = int(tr.get("total_units") or 0)
                            vl_v = float(tr.get("total_value") or 0.0)
                            ph_v = float(tr.get("phonepe") or 0.0)
                            cs_v = float(tr.get("cash") or 0.0)
                            lk_v = float(tr.get("leakage") or 0.0)
                            flv_str = " • ".join([
                                f"{code}:{int(tr.get(FLAVOR_MAP[code]['audit_col'], 0))}"
                                for code in FLAVOR_CODES
                                if int(tr.get(FLAVOR_MAP[code]["audit_col"], 0)) > 0
                            ]) or "—"
                            rsn_s = str(tr.get("reason") or "—")

                            rc = st.columns(col_w, gap="small")
                            rc[0].markdown(f"<div class='ledger-cell' style='justify-content:center;'>#{tid}</div>", unsafe_allow_html=True)
                            rc[1].markdown(f"<div class='ledger-cell' style='justify-content:center;'>{dt_s}</div>", unsafe_allow_html=True)
                            rc[2].markdown(f"<div class='ledger-cell' style='justify-content:center;'>{tm_s}</div>", unsafe_allow_html=True)
                            rc[3].markdown(f"<div class='ledger-cell' title='{escape(fn_s)}'>{escape(fn_s)}</div>", unsafe_allow_html=True)
                            rc[4].markdown(f"<div class='ledger-cell' title='{escape(sb_s)}'>{escape(sb_s)}</div>", unsafe_allow_html=True)
                            rc[5].markdown(f"<div class='ledger-cell' style='justify-content:center;font-weight:900;'>{un_v}</div>", unsafe_allow_html=True)
                            rc[6].markdown(f"<div class='ledger-amt-paid'>₹{vl_v:,.0f}</div>", unsafe_allow_html=True)
                            rc[7].markdown(f"<div class='ledger-amt-total'>₹{ph_v:,.0f}</div>", unsafe_allow_html=True)
                            rc[8].markdown(f"<div class='ledger-amt-total'>₹{cs_v:,.0f}</div>", unsafe_allow_html=True)
                            lk_cls = "ledger-amt-due" if lk_v > 0.009 else "ledger-cell"
                            rc[9].markdown(f"<div class='{lk_cls}' style='justify-content:flex-end;'>₹{lk_v:,.0f}</div>", unsafe_allow_html=True)
                            rc[10].markdown(f"<div class='ledger-cell-desc' title='{escape(flv_str)}'><span>{escape(flv_str)}</span></div>", unsafe_allow_html=True)
                            rc[11].markdown(f"<div class='ledger-cell-desc' title='{escape(rsn_s)}'><span>{escape(rsn_s)}</span></div>", unsafe_allow_html=True)

                            if rc[12].button("✏️", key=f"row_edit_fzr_txn_{tid}", help="Edit Freezer Sale", use_container_width=True):
                                st.session_state["_editing_freezer_txn_id"] = tid
                                st.session_state["fzr_entry_sub_mode"] = "edit"
                                st.session_state["fzr_sale_form_nonce"] = int(st.session_state.get("fzr_sale_form_nonce", 0)) + 1
                                st.rerun()
                            if rc[13].button("❌", key=f"row_del_fzr_txn_{tid}", help="Delete Freezer Sale", use_container_width=True):
                                confirm_delete_freezer_sale_modal(tr.to_dict())

                # MODE B & C: NEW FREEZER SALE ENTRY OR EDIT EXISTING ENTRY
                else:
                    editing_row = None
                    if fzr_sub_mode == "edit" and editing_txn_id is not None:
                        all_txns_df = load_freezer_sale_transactions_df()
                        match_df = all_txns_df[all_txns_df["id"] == int(editing_txn_id)] if not all_txns_df.empty else pd.DataFrame()
                        if match_df.empty:
                            st.session_state["fzr_entry_sub_mode"] = "list"
                            st.session_state.pop("_editing_freezer_txn_id", None)
                            st.rerun()
                        else:
                            editing_row = match_df.iloc[0].to_dict()
                            freezer_asset_name = str(editing_row.get("freezer_name") or freezer_asset_name)

                    if editing_row:
                        eb1, eb2 = st.columns([3.8, 1.2], gap="small", vertical_alignment="center")
                        with eb1:
                            st.info(
                                f"✏️ **Editing Freezer Sale #{int(editing_row['id'])}** "
                                f"({pd.to_datetime(editing_row['sale_date']).strftime('%d-%b-%Y')} • {freezer_asset_name})"
                            )
                        with eb2:
                            if st.button("⬅ Cancel Edit", key="cancel_fzr_txn_edit_btn", use_container_width=True):
                                st.session_state["fzr_entry_sub_mode"] = "list"
                                st.session_state.pop("_editing_freezer_txn_id", None)
                                st.rerun()

                    form_nonce = int(st.session_state.get("fzr_sale_form_nonce", 0))
                    mode_tag = f"edit_{int(editing_row['id'])}_{form_nonce}" if editing_row else f"new_{form_nonce}"
                    default_sale_dt = pd.to_datetime(editing_row["sale_date"]).date() if editing_row else today_val

                    fs_top1, fs_top2, fs_top3, fs_top4 = st.columns([1.15, 1.45, 1.05, 1.0], gap="small", vertical_alignment="bottom")
                    with fs_top1:
                        fzr_sale_date = st.date_input(
                            "Sale Date",
                            value=default_sale_dt,
                            max_value=today_val,
                            format="DD-MM-YYYY",
                            key=f"fzr_sale_date_picker_{mode_tag}"
                        )
                    date_key_str = f"{fzr_sale_date.strftime('%Y%m%d')}_{mode_tag}"

                    default_staff = str(editing_row.get("sold_by") or "") if editing_row else ""
                    if default_staff and default_staff not in staff_options:
                        staff_options.append(default_staff)

                    with fs_top2:
                        fzr_staff_key = f"fzr_sale_staff_{freezer_asset_name}_{date_key_str}"
                        if fzr_staff_key not in st.session_state:
                            if editing_row and default_staff in staff_options:
                                st.session_state[fzr_staff_key] = default_staff
                            else:
                                st.session_state[fzr_staff_key] = staff_options[1] if len(staff_options) > 1 else "Select Staff"
                        fzr_sold_by = st.selectbox(
                            "Sold By (Staff)",
                            staff_options,
                            index=staff_options.index(st.session_state[fzr_staff_key]) if st.session_state[fzr_staff_key] in staff_options else 0,
                            key=fzr_staff_key
                        )
                    with fs_top3:
                        if st.button(
                            "➕ New Freezer Sale",
                            key="btn_fzr_mode_new",
                            type="primary" if fzr_sub_mode == "new" else "secondary",
                            use_container_width=True
                        ):
                            st.session_state["fzr_entry_sub_mode"] = "new"
                            st.session_state.pop("_editing_freezer_txn_id", None)
                            st.session_state["fzr_sale_form_nonce"] = int(st.session_state.get("fzr_sale_form_nonce", 0)) + 1
                            st.rerun()
                    with fs_top4:
                        if st.button(
                            f"✏️ Editing #{editing_txn_id}" if (fzr_sub_mode == "edit" and editing_txn_id) else "✏️ Past Entries",
                            key="btn_fzr_mode_list",
                            type="primary" if fzr_sub_mode in ("list", "edit") else "secondary",
                            use_container_width=True
                        ):
                            st.session_state["fzr_entry_sub_mode"] = "list"
                            st.session_state.pop("_editing_freezer_txn_id", None)
                            st.rerun()

                    curr_fzr_stock_map = get_physical_current_stock_map()
                    fzr_sold_map = {}
                    fzr_val_map = {}

                    header_label = (
                        f"✏️ Edit Freezer Sale #{int(editing_row['id'])} — {_entry_date_display(fzr_sale_date)}"
                        if editing_row
                        else f"❄️ New Direct Freezer Sale — {_entry_date_display(fzr_sale_date)}"
                    )
                    st.markdown(
                        f"<div class='header-box-sales'><span>{header_label}</span><span><b>{escape(freezer_asset_name)}</b></span></div>",
                        unsafe_allow_html=True,
                    )
                    with st.container(border=True):
                        fzr_col_w = [1.9, 0.95, 0.85, 1.05, 1.1]
                        fhc1, fhc2, fhc3, fhc4, fhc5 = st.columns(fzr_col_w, gap="small", vertical_alignment="center")
                        fhc1.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour</div>", unsafe_allow_html=True)
                        fhc2.markdown("<div class='entry-grid-header'>Current Stock</div>", unsafe_allow_html=True)
                        fhc3.markdown("<div class='entry-grid-header'>MRP</div>", unsafe_allow_html=True)
                        fhc4.markdown("<div class='entry-grid-header'>Sold Units ✏️</div>", unsafe_allow_html=True)
                        fhc5.markdown("<div class='entry-grid-header' style='text-align:right;'>Value (₹)</div>", unsafe_allow_html=True)

                        for code in FLAVOR_CODES:
                            f_info = FLAVOR_MAP[code]
                            orig_edit_qty = int(editing_row.get(f_info["audit_col"], 0)) if editing_row else 0
                            curr_stock_val = int(curr_fzr_stock_map.get(code, 0)) + orig_edit_qty
                            mrp_val = float(f_info["mrp"])
                            k_sold = f"fzr_sold_{freezer_asset_name}_{date_key_str}_{code}"
                            if k_sold not in st.session_state:
                                st.session_state[k_sold] = str(orig_edit_qty)
                            elif not isinstance(st.session_state[k_sold], str):
                                st.session_state[k_sold] = str(max(0, _int_num(st.session_state[k_sold])))

                            r1, r2, r3, r4, r5 = st.columns(fzr_col_w, gap="small", vertical_alignment="center")
                            with r1:
                                st.markdown(f"<div class='entry-grid-cell-flavour'><span>{f_info['name']}</span></div>", unsafe_allow_html=True)
                            with r2:
                                st.markdown(f"<div class='entry-grid-cell'>{curr_stock_val}</div>", unsafe_allow_html=True)
                            with r3:
                                st.markdown(f"<div class='entry-grid-cell'>₹{mrp_val:.0f}</div>", unsafe_allow_html=True)
                            with r4:
                                qty_sold = max(
                                    0,
                                    _int_num(
                                        st.text_input(
                                            f"Freezer Sold {f_info['name']}",
                                            key=k_sold,
                                            label_visibility="collapsed"
                                        )
                                    ),
                                )
                            line_val = max(0, qty_sold) * mrp_val
                            fzr_sold_map[code] = max(0, qty_sold)
                            fzr_val_map[code] = line_val
                            with r5:
                                st.markdown(f"<div class='entry-grid-cell-amount'>₹{line_val:,.0f}</div>", unsafe_allow_html=True)

                        tot_fzr_stock = sum(
                            int(curr_fzr_stock_map.get(c, 0)) + (int(editing_row.get(FLAVOR_MAP[c]["audit_col"], 0)) if editing_row else 0)
                            for c in FLAVOR_CODES
                        )
                        tot_fzr_sold = sum(fzr_sold_map.values())
                        tot_fzr_value = float(sum(fzr_val_map.values()))

                        ft1, ft2, ft3, ft4, ft5 = st.columns(fzr_col_w, gap="small", vertical_alignment="center")
                        ft1.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                        ft2.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_fzr_stock}</div>", unsafe_allow_html=True)
                        ft3.markdown("<div class='entry-grid-total-row' style='text-align:center;'>—</div>", unsafe_allow_html=True)
                        ft4.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#C43D17;'>{tot_fzr_sold}</div>", unsafe_allow_html=True)
                        ft5.markdown(f"<div class='entry-grid-total-row' style='text-align:right;color:#047857;'>₹{tot_fzr_value:,.0f}</div>", unsafe_allow_html=True)

                        k_f_ph = f"fzr_ph_{freezer_asset_name}_{date_key_str}"
                        k_f_cs = f"fzr_cs_{freezer_asset_name}_{date_key_str}"
                        k_f_lk = f"fzr_lk_{freezer_asset_name}_{date_key_str}"
                        k_f_sig = f"fzr_sig_{freezer_asset_name}_{date_key_str}"
                        k_f_rsn = f"fzr_rsn_{freezer_asset_name}_{date_key_str}"

                        if k_f_ph not in st.session_state:
                            st.session_state[k_f_ph] = f"{float(editing_row.get('phonepe') or 0.0):.2f}" if editing_row else "0.00"
                        if k_f_cs not in st.session_state:
                            st.session_state[k_f_cs] = f"{float(editing_row.get('cash') or 0.0):.2f}" if editing_row else "0.00"
                        if k_f_rsn not in st.session_state:
                            st.session_state[k_f_rsn] = str(editing_row.get("reason") or "") if editing_row else ""

                        fc1, fc2, fc3, fc4 = st.columns([0.95, 0.95, 1.05, 1.55], gap="small")
                        with fc1:
                            fzr_phonepe_val = max(0.0, _num(st.text_input("PhonePe / UPI (₹)", key=k_f_ph)))
                        with fc2:
                            fzr_cash_val = max(0.0, _num(st.text_input("Cash Collected (₹)", key=k_f_cs)))

                        auto_leakage = max(0.0, tot_fzr_value - fzr_phonepe_val - fzr_cash_val)
                        curr_sig = f"{tot_fzr_value:.2f}_{fzr_phonepe_val:.2f}_{fzr_cash_val:.2f}"
                        if st.session_state.get(k_f_sig) != curr_sig:
                            if editing_row and st.session_state.get(k_f_sig) is None:
                                st.session_state[k_f_lk] = f"{float(editing_row.get('leakage') or auto_leakage):.2f}"
                            else:
                                st.session_state[k_f_lk] = f"{auto_leakage:.2f}"
                            st.session_state[k_f_sig] = curr_sig

                        with fc3:
                            fzr_leakage_val = max(0.0, _num(st.text_input("Leakage (₹) (Auto/Edit)", key=k_f_lk)))
                        with fc4:
                            fzr_reason = st.text_input(
                                "Reason / Remarks" + (" *" if fzr_leakage_val > 0.001 else ""),
                                key=k_f_rsn,
                                placeholder="Mandatory when leakage > 0..."
                            )

                        if fzr_leakage_val > 0.001:
                            st.markdown(
                                "<p style='color:#C41C1C; font-weight:bold; font-size:11px; margin: 1px 0 !important;'>"
                                "⚠️ Reason for leakage is mandatory when leakage is greater than zero."
                                "</p>",
                                unsafe_allow_html=True,
                            )

                    submit_label = "💾 Update Freezer Sale Entry" if editing_row else "💾 Submit Freezer Sale"
                    if st.button(submit_label, type="primary", use_container_width=False, key=f"submit_fzr_sale_{date_key_str}"):
                        if tot_fzr_sold <= 0:
                            st.error("Please enter Sold Units greater than 0 for at least one flavour.")
                        elif fzr_sold_by == "Select Staff" or not str(fzr_sold_by).strip():
                            st.error("Please select the staff member in 'Sold By'.")
                        elif fzr_leakage_val > 0.001 and not str(fzr_reason or "").strip():
                            st.error("Reason / Remarks is mandatory while Leakage is positive.")
                        else:
                            try:
                                if editing_row:
                                    update_freezer_sale_transaction(
                                        int(editing_row["id"]),
                                        fzr_sale_date,
                                        freezer_asset_name,
                                        fzr_sold_by,
                                        fzr_sold_map,
                                        tot_fzr_value,
                                        fzr_phonepe_val,
                                        fzr_cash_val,
                                        fzr_leakage_val,
                                        fzr_reason
                                    )
                                    st.session_state["fzr_entry_sub_mode"] = "list"
                                    st.session_state.pop("_editing_freezer_txn_id", None)
                                    st.session_state["fzr_sale_form_nonce"] = form_nonce + 1
                                    st.cache_data.clear()
                                    show_success_modal(
                                        f"Freezer Sale #{int(editing_row['id'])} updated! Total: {tot_fzr_sold} units (₹{tot_fzr_value:,.0f})."
                                    )
                                else:
                                    sync_freezer_sale_entry(
                                        fzr_sale_date,
                                        freezer_asset_name,
                                        fzr_sold_by,
                                        fzr_sold_map,
                                        tot_fzr_value,
                                        fzr_phonepe_val,
                                        fzr_cash_val,
                                        fzr_leakage_val,
                                        fzr_reason
                                    )
                                    st.session_state["fzr_sale_form_nonce"] = form_nonce + 1
                                    st.cache_data.clear()
                                    show_success_modal(
                                        f"Freezer sale transaction saved for {freezer_asset_name} on {_entry_date_display(fzr_sale_date)}! Added +{tot_fzr_sold} units (₹{tot_fzr_value:,.0f})."
                                    )
                            except Exception as e:
                                st.error(f"Could not save Freezer sale: {e}")

            # --------------------------------------------------------------
            # RESTOCK ENTRY — Compact 80% Single-Page Layout & Matched Columns
            # --------------------------------------------------------------
            elif entry_mode == "restock":
                rc_top1, rc_top2, rc_top3 = st.columns([1.4, 1.1, 1.4], gap="small", vertical_alignment="bottom")
                with rc_top1:
                    cart_name = st.selectbox("Assigned Cart", CARTS, key="entry_cart_shared")
                with rc_top2:
                    st.text_input(
                        "Restock Date",
                        value=_entry_date_display(today_val),
                        disabled=True,
                        key=f"restock_date_{cart_name}",
                    )

                today_stock_state, today_staff = get_today_cart_stock_state(cart_name, today_val)
                staff_options = load_active_staff_list()
                if today_staff and today_staff not in staff_options:
                    staff_options.append(today_staff)
                restock_staff_key = f"restock_staff_{cart_name}_{today_val.strftime('%Y%m%d')}"
                if restock_staff_key not in st.session_state:
                    st.session_state[restock_staff_key] = today_staff if today_staff in staff_options else "Select Staff"
                with rc_top3:
                    staff_name = st.selectbox(
                        "Cart Staff Assigned",
                        staff_options,
                        index=staff_options.index(st.session_state[restock_staff_key]) if st.session_state[restock_staff_key] in staff_options else 0,
                        key=restock_staff_key,
                    )
                restock_map = {}
                restock_after_map = {}

                st.markdown(
                    f"<div class='header-box-restock'><span>📦 Restock Entry — {_entry_date_display(today_val)}</span><span><b>{cart_name}</b></span></div>",
                    unsafe_allow_html=True,
                )
                with st.container(border=True):
                    restock_col_w = [1.9, 1.0, 1.05, 1.05]
                    rh1, rh2, rh3, rh4 = st.columns(restock_col_w, gap="small", vertical_alignment="center")
                    rh1.markdown("<div class='entry-grid-header' style='background:#D1FAE5;color:#111111;border:1px solid #4ADE80;text-align:left;'>Flavour</div>", unsafe_allow_html=True)
                    rh2.markdown("<div class='entry-grid-header' style='background:#D1FAE5;color:#111111;border:1px solid #4ADE80;'>Opening</div>", unsafe_allow_html=True)
                    rh3.markdown("<div class='entry-grid-header' style='background:#D1FAE5;color:#111111;border:1px solid #4ADE80;'>+ Restock ✏️</div>", unsafe_allow_html=True)
                    rh4.markdown("<div class='entry-grid-header' style='background:#D1FAE5;color:#111111;border:1px solid #4ADE80;'>Total Opening</div>", unsafe_allow_html=True)

                    for code in FLAVOR_CODES:
                        f_info = FLAVOR_MAP[code]
                        opening = int(today_stock_state[code]["opening"])
                        existing_added = int(today_stock_state[code]["added"])
                        key = f"restock_entry_{cart_name}_{code}"
                        if key not in st.session_state:
                            st.session_state[key] = str(existing_added)
                        elif not isinstance(st.session_state[key], str):
                            st.session_state[key] = str(max(0, _int_num(st.session_state[key])))

                        c1, c2, c3, c4 = st.columns(restock_col_w, gap="small", vertical_alignment="center")
                        with c1:
                            st.markdown(f"<div class='entry-grid-cell-flavour'><span>{f_info['name']}</span></div>", unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"<div class='entry-grid-cell'>{opening}</div>", unsafe_allow_html=True)
                        with c3:
                            qty = max(
                                0,
                                _int_num(
                                    st.text_input(
                                        f"Restock {f_info['name']}",
                                        key=key,
                                        label_visibility="collapsed",
                                    )
                                ),
                            )
                        restock_map[code] = qty
                        restock_after_map[code] = opening + qty
                        with c4:
                            st.markdown(f"<div class='entry-grid-cell-amount' style='justify-content:center;'>{opening + qty} pcs</div>", unsafe_allow_html=True)

                    total_opening_base = sum(int(today_stock_state[code]["opening"]) for code in FLAVOR_CODES)
                    total_restock = sum(restock_map.values())
                    total_opening_after = sum(restock_after_map.values())

                    tf1, tf2, tf3, tf4 = st.columns(restock_col_w, gap="small", vertical_alignment="center")
                    tf1.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                    tf2.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{total_opening_base}</div>", unsafe_allow_html=True)
                    tf3.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#047857;'>+{total_restock} pcs</div>", unsafe_allow_html=True)
                    tf4.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#047857;'>{total_opening_after} pcs</div>", unsafe_allow_html=True)

                if st.button("📦 Submit Restock", type="primary", use_container_width=False, key=f"submit_restock_{cart_name}"):
                    try:
                        selected_staff = "" if staff_name == "Select Staff" else staff_name
                        opening_map = {code: int(today_stock_state[code]["opening"]) for code in FLAVOR_CODES}
                        sync_today_restock_entry(today_val, cart_name, selected_staff, opening_map, restock_map)
                        st.cache_data.clear()
                        show_success_modal(
                            f"Restock saved successfully for {cart_name}. Total stock added: {total_restock} units."
                        )
                    except Exception as e:
                        st.error(f"Could not save Restock Entry - {e}")

            # --------------------------------------------------------------
            # EXTRA STOCK — Compact 80% Single-Page Layout
            # --------------------------------------------------------------
            elif entry_mode == "extra":
                ec_top1, ec_top2, ec_top3 = st.columns([1.4, 1.1, 1.4], gap="small", vertical_alignment="bottom")
                with ec_top1:
                    cart_name = st.selectbox("Assigned Cart", CARTS, key="entry_cart_shared")
                with ec_top2:
                    st.text_input(
                        "Extra Stock Date",
                        value=_entry_date_display(today_val),
                        disabled=True,
                        key=f"extra_date_{cart_name}",
                    )

                today_stock_state, today_staff = get_today_cart_stock_state(cart_name, today_val)
                with ec_top3:
                    st.text_input(
                        "Cart Staff Assigned",
                        value=today_staff or "—",
                        disabled=True,
                        key=f"extra_staff_disp_{cart_name}",
                    )
                extra_map = {}

                st.markdown(
                    f"<div class='header-box-restock'><span>➕ Extra Stock Entry — {_entry_date_display(today_val)}</span><span><b>{cart_name}</b></span></div>",
                    unsafe_allow_html=True,
                )
                with st.container(border=True):
                    extra_col_w = [1.9, 0.95, 0.95, 1.05, 1.05]
                    eh1, eh2, eh3, eh4, eh5 = st.columns(extra_col_w, gap="small", vertical_alignment="center")
                    eh1.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour</div>", unsafe_allow_html=True)
                    eh2.markdown("<div class='entry-grid-header'>Current</div>", unsafe_allow_html=True)
                    eh3.markdown("<div class='entry-grid-header'>Added Today</div>", unsafe_allow_html=True)
                    eh4.markdown("<div class='entry-grid-header'>+ Extra ✏️</div>", unsafe_allow_html=True)
                    eh5.markdown("<div class='entry-grid-header'>After Extra</div>", unsafe_allow_html=True)

                    for code in FLAVOR_CODES:
                        f_info = FLAVOR_MAP[code]
                        current_added = int(today_stock_state[code]["added"])
                        current_stock = int(today_stock_state[code]["closing"])
                        key = f"extra_stock_{cart_name}_{code}"
                        if key not in st.session_state:
                            st.session_state[key] = "0"
                        elif not isinstance(st.session_state[key], str):
                            st.session_state[key] = str(max(0, _int_num(st.session_state[key])))

                        c1, c2, c3, c4, c5 = st.columns(extra_col_w, gap="small", vertical_alignment="center")
                        with c1:
                            st.markdown(f"<div class='entry-grid-cell-flavour'><span>{f_info['name']}</span></div>", unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"<div class='entry-grid-cell'>{current_stock}</div>", unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"<div class='entry-grid-cell'>{current_added}</div>", unsafe_allow_html=True)
                        with c4:
                            qty = max(
                                0,
                                _int_num(
                                    st.text_input(
                                        f"Extra {f_info['name']}",
                                        key=key,
                                        label_visibility="collapsed",
                                    )
                                ),
                            )
                        extra_map[code] = qty
                        with c5:
                            st.markdown(f"<div class='entry-grid-cell-amount' style='justify-content:center;'>{current_stock + qty} pcs</div>", unsafe_allow_html=True)

                    tot_curr_stock = sum(int(today_stock_state[code]["closing"]) for code in FLAVOR_CODES)
                    tot_added_today = sum(int(today_stock_state[code]["added"]) for code in FLAVOR_CODES)
                    total_extra = sum(extra_map.values())
                    total_after_extra = tot_curr_stock + total_extra

                    ef1, ef2, ef3, ef4, ef5 = st.columns(extra_col_w, gap="small", vertical_alignment="center")
                    ef1.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                    ef2.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_curr_stock}</div>", unsafe_allow_html=True)
                    ef3.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_added_today}</div>", unsafe_allow_html=True)
                    ef4.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#C43D17;'>+{total_extra} pcs</div>", unsafe_allow_html=True)
                    ef5.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#047857;'>{total_after_extra} pcs</div>", unsafe_allow_html=True)

                if st.button("➕ Submit Extra Stock", type="primary", use_container_width=False, key=f"submit_extra_{cart_name}"):
                    if total_extra <= 0:
                        st.warning("Enter at least one extra stock quantity before submitting.")
                    else:
                        try:
                            add_today_extra_stock_entry(today_val, cart_name, extra_map, today_staff)
                            for code in FLAVOR_CODES:
                                st.session_state[f"extra_stock_{cart_name}_{code}"] = "0"
                            st.cache_data.clear()
                            show_success_modal(
                                f"{total_extra} total extra stock units added successfully for {cart_name}."
                            )
                        except Exception as e:
                            st.error(f"Could not add Extra Stock - {e}")

                with st.expander(f"📋 Extra Stock Audit Log — {cart_name}", expanded=False):
                    try:
                        extra_log_df = db_conn.query(
                            """
                            SELECT id, entry_date, cart_name, location, staff_name,
                                   ml_units, mm_units, ps_units, mn_units, kb_units,
                                   bm_units, sg_units, ch_units, ra_units,
                                   total_extra_units, recorded_by, source_app, created_at
                            FROM public.cart_extra_stock_logs
                            WHERE cart_name = :cart
                            ORDER BY entry_date DESC, id DESC
                            LIMIT 25;
                            """,
                            params={"cart": cart_name},
                            ttl="60s"
                        )
                        if extra_log_df.empty:
                            st.caption(f"No extra stock audit logs recorded for {cart_name} yet.")
                        else:
                            disp_extra_logs = []
                            for _, lr in extra_log_df.iterrows():
                                row_d = {
                                    "Log #": f"#{int(lr['id'])}",
                                    "Date": pd.to_datetime(lr["entry_date"]).strftime("%d-%b-%y"),
                                    "Time": pd.to_datetime(lr["created_at"]).strftime("%I:%M %p") if pd.notna(lr.get("created_at")) else "—",
                                    "Cart": lr["cart_name"],
                                    "Staff": lr.get("staff_name") or "—",
                                    "Total Extra": int(lr.get("total_extra_units") or 0),
                                }
                                for c_code in FLAVOR_CODES:
                                    row_d[c_code] = int(lr.get(FLAVOR_MAP[c_code]["audit_col"], 0))
                                row_d["By"] = f"{lr.get('recorded_by') or '—'} ({lr.get('source_app') or 'app'})"
                                disp_extra_logs.append(row_d)
                            st.dataframe(pd.DataFrame(disp_extra_logs), hide_index=True, use_container_width=True)
                    except Exception as e:
                        st.caption(f"Extra stock audit log unavailable: {e}")

            # --------------------------------------------------------------
            # VIEW CART STOCK (Read-Only: Today, Today-1, Today-2)
            # --------------------------------------------------------------
            elif entry_mode == "view_stock":
                allowed_stock_dates = [
                    today_val,
                    today_val - timedelta(days=1),
                    today_val - timedelta(days=2),
                ]
                date_label_map = {_entry_date_display(d): d for d in allowed_stock_dates}
                date_labels_list = list(date_label_map.keys())

                vc1, vc2, vc3 = st.columns([1.4, 1.1, 1.4], gap="small", vertical_alignment="bottom")
                with vc1:
                    cart_name = st.selectbox("Cart Name", CARTS, key="entry_cart_shared")
                with vc2:
                    sel_view_date_label = st.selectbox(
                        "Date",
                        date_labels_list,
                        index=0,
                        key="view_cart_stock_date_sel",
                    )
                    selected_stock_date = date_label_map[sel_view_date_label]

                stock_rows, readonly_staff_name = get_cart_stock_view_data(cart_name, selected_stock_date)

                with vc3:
                    st.text_input(
                        "Staff Name",
                        value=readonly_staff_name,
                        disabled=True,
                        key=f"view_stock_staff_ro_{cart_name}_{selected_stock_date.strftime('%Y%m%d')}",
                    )

                st.markdown(
                    f"<div class='header-box-restock'><span>📋 Cart Stock Summary — {sel_view_date_label}</span>"
                    f"<span><b>{escape(cart_name)}</b> &nbsp;|&nbsp; Staff: <b>{escape(readonly_staff_name)}</b></span></div>",
                    unsafe_allow_html=True,
                )

                with st.container(border=True):
                    view_col_w = [2.0, 1.0, 1.0, 1.0]
                    vh1, vh2, vh3, vh4 = st.columns(view_col_w, gap="small", vertical_alignment="center")
                    vh1.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour</div>", unsafe_allow_html=True)
                    vh2.markdown("<div class='entry-grid-header'>Opening</div>", unsafe_allow_html=True)
                    vh3.markdown("<div class='entry-grid-header'>Restock</div>", unsafe_allow_html=True)
                    vh4.markdown("<div class='entry-grid-header'>Sold Units</div>", unsafe_allow_html=True)

                    tot_open_v, tot_restock_v, tot_extra_v, tot_sold_v = 0, 0, 0, 0

                    for r in stock_rows:
                        op_val = int(r["opening"])
                        rs_val = int(r["restock"])
                        ex_val = int(r.get("extra", 0))
                        sd_val = int(r["sold"])

                        tot_open_v += op_val
                        tot_restock_v += rs_val
                        tot_extra_v += ex_val
                        tot_sold_v += sd_val

                        rs_disp = f"{rs_val} ({ex_val})" if ex_val > 0 else f"{rs_val}"

                        r1, r2, r3, r4 = st.columns(view_col_w, gap="small", vertical_alignment="center")
                        r1.markdown(f"<div class='entry-grid-cell-flavour'><span>{escape(r['flavour'])}</span></div>", unsafe_allow_html=True)
                        r2.markdown(f"<div class='entry-grid-cell'>{op_val}</div>", unsafe_allow_html=True)
                        r3.markdown(f"<div class='entry-grid-cell'>{rs_disp}</div>", unsafe_allow_html=True)
                        r4.markdown(f"<div class='entry-grid-cell-sold'>{sd_val}</div>", unsafe_allow_html=True)

                    tot_rs_disp = f"{tot_restock_v} ({tot_extra_v})" if tot_extra_v > 0 else f"{tot_restock_v}"

                    vt1, vt2, vt3, vt4 = st.columns(view_col_w, gap="small", vertical_alignment="center")
                    vt1.markdown("<div class='entry-grid-total-row' style='text-align:left;font-weight:900;'><b>TOTAL</b></div>", unsafe_allow_html=True)
                    vt2.markdown(f"<div class='entry-grid-total-row' style='text-align:center;font-weight:900;'><b>{tot_open_v}</b></div>", unsafe_allow_html=True)
                    vt3.markdown(f"<div class='entry-grid-total-row' style='text-align:center;font-weight:900;'><b>{tot_rs_disp}</b></div>", unsafe_allow_html=True)
                    vt4.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#C43D17;font-weight:900;'><b>{tot_sold_v}</b></div>", unsafe_allow_html=True)

            # --------------------------------------------------------------
            # REMOVE CART STOCK (Move Cart Stock Back to Freezer)
            # --------------------------------------------------------------
            elif entry_mode == "remove_cart_stock":
                if st.session_state.get("_rm_cart_success_msg"):
                    st.success(st.session_state.pop("_rm_cart_success_msg"))

                rc1, rc2, rc3, rc4 = st.columns([1.4, 1.0, 1.0, 0.85], gap="small", vertical_alignment="bottom")
                with rc1:
                    cart_name = st.selectbox("Select Cart", CARTS, key="entry_cart_shared")
                with rc2:
                    st.text_input(
                        "Transfer Date",
                        value=_entry_date_display(today_val),
                        disabled=True,
                        key=f"rm_cart_date_disp_{cart_name}",
                    )

                today_stock_state, today_staff = get_today_cart_stock_state(cart_name, today_val)
                with rc3:
                    st.text_input(
                        "Staff Name",
                        value=today_staff or "—",
                        disabled=True,
                        key=f"rm_cart_staff_disp_{cart_name}",
                    )
                with rc4:
                    if st.button("↻ Refresh", use_container_width=True, key=f"refresh_rm_cart_{cart_name}"):
                        st.cache_data.clear()
                        st.rerun()

                tot_in_cart_now = sum(max(0, int(today_stock_state[c]["closing"])) for c in FLAVOR_CODES)

                top_bar1, top_bar2, top_bar3 = st.columns([2.4, 1.0, 0.9], gap="small", vertical_alignment="center")
                with top_bar1:
                    st.markdown(
                        f"<div class='header-box-restock' style='margin-bottom:0;'>"
                        f"<span>🛒 Current Stock in <b>{escape(cart_name)}</b>: <b>{tot_in_cart_now} pcs</b></span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with top_bar2:
                    if st.button("🧹 Empty Cart (Fill All)", type="primary", use_container_width=True, key=f"btn_empty_cart_{cart_name}"):
                        for code in FLAVOR_CODES:
                            st.session_state[f"rm_cart_stock_{cart_name}_{code}"] = str(max(0, int(today_stock_state[code]["closing"])))
                        st.rerun()
                with top_bar3:
                    if st.button("↺ Clear Inputs", use_container_width=True, key=f"btn_clear_rm_cart_{cart_name}"):
                        for code in FLAVOR_CODES:
                            st.session_state[f"rm_cart_stock_{cart_name}_{code}"] = "0"
                        st.rerun()

                return_map = {}
                with st.container(border=True):
                    rm_col_w = [1.9, 0.95, 0.95, 1.05, 1.05]
                    rh1, rh2, rh3, rh4, rh5 = st.columns(rm_col_w, gap="small", vertical_alignment="center")
                    rh1.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour</div>", unsafe_allow_html=True)
                    rh2.markdown("<div class='entry-grid-header'>Opening</div>", unsafe_allow_html=True)
                    rh3.markdown("<div class='entry-grid-header'>In Cart Now</div>", unsafe_allow_html=True)
                    rh4.markdown("<div class='entry-grid-header' style='background:#D1FAE5;color:#111111;border:1px solid #4ADE80;'>Move to Fzr ✏️</div>", unsafe_allow_html=True)
                    rh5.markdown("<div class='entry-grid-header'>Rem. in Cart</div>", unsafe_allow_html=True)

                    for code in FLAVOR_CODES:
                        f_info = FLAVOR_MAP[code]
                        open_u = max(0, int(today_stock_state[code]["opening"]))
                        in_cart_u = max(0, int(today_stock_state[code]["closing"]))
                        r_key = f"rm_cart_stock_{cart_name}_{code}"
                        if r_key not in st.session_state:
                            st.session_state[r_key] = "0"
                        else:
                            st.session_state[r_key] = str(min(in_cart_u, max(0, _int_num(st.session_state[r_key]))))

                        c1, c2, c3, c4, c5 = st.columns(rm_col_w, gap="small", vertical_alignment="center")
                        with c1:
                            st.markdown(f"<div class='entry-grid-cell-flavour'><span>{escape(f_info['name'])}</span><span style='color:#2563EB;font-size:10px;'>₹{int(f_info['mrp'])}</span></div>", unsafe_allow_html=True)
                        with c2:
                            st.markdown(f"<div class='entry-grid-cell'>{open_u}</div>", unsafe_allow_html=True)
                        with c3:
                            st.markdown(f"<div class='entry-grid-cell' style='font-weight:900;color:#047857;'>{in_cart_u}</div>", unsafe_allow_html=True)
                        with c4:
                            raw_move_qty = max(
                                0,
                                _int_num(
                                    st.text_input(
                                        f"Move {f_info['name']} to Freezer",
                                        key=r_key,
                                        label_visibility="collapsed",
                                    )
                                ),
                            )
                            move_qty = min(max(0, in_cart_u), raw_move_qty)
                        return_map[code] = move_qty
                        rem_in_cart = max(0, in_cart_u - move_qty)
                        with c5:
                            st.markdown(f"<div class='entry-grid-cell-amount' style='justify-content:center;'>{rem_in_cart} pcs</div>", unsafe_allow_html=True)

                    tot_open_c = sum(max(0, int(today_stock_state[c]["opening"])) for c in FLAVOR_CODES)
                    tot_move_c = sum(return_map.values())
                    tot_rem_c = max(0, tot_in_cart_now - tot_move_c)

                    rf1, rf2, rf3, rf4, rf5 = st.columns(rm_col_w, gap="small", vertical_alignment="center")
                    rf1.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                    rf2.markdown(f"<div class='entry-grid-total-row' style='text-align:center;'>{tot_open_c}</div>", unsafe_allow_html=True)
                    rf3.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#047857;'>{tot_in_cart_now}</div>", unsafe_allow_html=True)
                    rf4.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#0F766E;'>{tot_move_c} pcs</div>", unsafe_allow_html=True)
                    rf5.markdown(f"<div class='entry-grid-total-row' style='text-align:center;color:#1E2252;'>{tot_rem_c} pcs</div>", unsafe_allow_html=True)

                if st.button("❄️ Move back to Freezer", type="primary", use_container_width=False, key=f"submit_rm_cart_{cart_name}"):
                    if tot_move_c <= 0:
                        st.warning("Please enter at least 1 unit to move back to the Freezer (or click 'Empty Cart').")
                    else:
                        confirm_move_cart_to_freezer_modal(today_val, cart_name, return_map, today_staff)

                with st.expander(f"📋 Recent Cart-to-Freezer Transfers — {cart_name}", expanded=False):
                    try:
                        ctf_df = db_conn.query(
                            """
                            SELECT id, entry_date, cart_name, location, staff_name,
                                   ml_units, mm_units, ps_units, mn_units, kb_units,
                                   bm_units, sg_units, ch_units, ra_units,
                                   total_returned_units, recorded_by, source_app, created_at
                            FROM public.cart_to_freezer_logs
                            WHERE cart_name = :cart
                            ORDER BY entry_date DESC, id DESC
                            LIMIT 25;
                            """,
                            params={"cart": cart_name},
                            ttl="60s",
                        )
                        if ctf_df.empty:
                            st.caption(f"No stock transfers from {cart_name} to Freezer recorded yet.")
                        else:
                            disp_ctf = []
                            for _, lr in ctf_df.iterrows():
                                row_d = {
                                    "Log #": f"#{int(lr['id'])}",
                                    "Date": pd.to_datetime(lr["entry_date"]).strftime("%d-%b-%y"),
                                    "Time": pd.to_datetime(lr["created_at"]).strftime("%I:%M %p") if pd.notna(lr.get("created_at")) else "—",
                                    "Cart": lr["cart_name"],
                                    "Staff": lr.get("staff_name") or "—",
                                    "Moved to Fzr": int(lr.get("total_returned_units") or sum(int(lr.get(FLAVOR_MAP[c]["audit_col"], 0)) for c in FLAVOR_CODES)),
                                }
                                for c_code in FLAVOR_CODES:
                                    row_d[c_code] = int(lr.get(FLAVOR_MAP[c_code]["audit_col"], 0))
                                row_d["By"] = f"{lr.get('recorded_by') or '—'} ({lr.get('source_app') or 'app'})"
                                disp_ctf.append(row_d)
                            st.dataframe(pd.DataFrame(disp_ctf), hide_index=True, use_container_width=True)
                    except Exception as e:
                        st.caption(f"Remove Cart Stock history log unavailable (run SQL migration if needed): {e}")

            elif entry_mode == "live_flavour_view":
                render_live_cart_flavour_tables_section(key_prefix="entry_live_flv")

    elif page == "Bulk Orders & Quotes" and user_role == "admin":
        st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
        st.subheader("📦 Bulk Orders — Estimates, Discount Planner & Invoices")

        # Popularity weights for smart party mix distribution
        BULK_POPULARITY_WEIGHTS = {
            "ML": 1.6, "MM": 1.4, "PS": 1.4, "MN": 1.4,
            "KB": 1.2, "SG": 1.0, "CH": 1.0, "RA": 0.8, "BM": 0.5
        }

        def distribute_bulk_pieces(total_pcs, checked_codes, mode="even"):
            """Distribute total_pcs across checked_codes rounded to the nearest 10 units per flavour."""
            res = {c: 0 for c in FLAVOR_CODES}
            active = [c for c in FLAVOR_CODES if c in checked_codes]
            total_pcs = max(0, int(total_pcs or 0))
            if not active or total_pcs <= 0:
                return res
            total_tens = max(1, int(round(total_pcs / 10.0)))
            if mode == "weighted":
                weights = [BULK_POPULARITY_WEIGHTS.get(c, 1.0) for c in active]
                w_sum = sum(weights)
                raw_tens = [(total_tens * w / w_sum) for w in weights]
                floors = [int(x) for x in raw_tens]
                rem = total_tens - sum(floors)
                fracs = sorted(range(len(active)), key=lambda i: (raw_tens[i] - floors[i], weights[i]), reverse=True)
                for idx in fracs[:rem]:
                    floors[idx] += 1
                for c, val in zip(active, floors):
                    res[c] = val * 10
            else:
                base_tens = total_tens // len(active)
                rem_tens = total_tens % len(active)
                for i, c in enumerate(active):
                    res[c] = (base_tens + (1 if i < rem_tens else 0)) * 10
            return res

        def distribute_bulk_budget(budget_inr, discount_pct, checked_codes, mode="even"):
            """Given a customer budget in INR and discount %, compute optimal flavour counts in multiples of 10 whose discounted net total fits the budget."""
            res = {c: 0 for c in FLAVOR_CODES}
            active = [c for c in FLAVOR_CODES if c in checked_codes]
            budget_inr = max(0.0, float(budget_inr or 0.0))
            disc = min(95.0, max(0.0, float(discount_pct or 0.0)))
            if not active or budget_inr <= 0:
                return res
            disc_factor = 1.0 - (disc / 100.0)
            gross_target = budget_inr / disc_factor if disc_factor > 0 else budget_inr
            if mode == "weighted":
                weights = [BULK_POPULARITY_WEIGHTS.get(c, 1.0) for c in active]
            else:
                weights = [1.0 for _ in active]
            weighted_mrp_unit = sum(weights[i] * float(FLAVOR_MAP[active[i]]["mrp"]) for i in range(len(active)))
            if weighted_mrp_unit <= 0:
                return res
            scale = gross_target / weighted_mrp_unit
            for i, c in enumerate(active):
                res[c] = max(0, int(round((scale * weights[i]) / 10.0)) * 10)
            # Fine-tune in steps of 10 pieces of the lowest-MRP active flavour so net amount is as close as possible to budget_inr
            cheapest_c = min(active, key=lambda c: float(FLAVOR_MAP[c]["mrp"]))
            cheapest_ten_net = float(FLAVOR_MAP[cheapest_c]["mrp"]) * 10.0 * disc_factor
            if cheapest_ten_net > 0:
                curr_gross = sum(res[c] * float(FLAVOR_MAP[c]["mrp"]) for c in active)
                curr_net = curr_gross * disc_factor
                diff = budget_inr - curr_net
                adj_tens = int(round(diff / cheapest_ten_net))
                if adj_tens != 0:
                    res[cheapest_c] = max(0, res[cheapest_c] + (adj_tens * 10))
            return res

        def generate_bulk_quote_pdf_bytes(q_data):
            """Generate a clean, customer-ready PDF for a Bulk Order Estimate or Invoice using ReportLab."""
            if not REPORTLAB_AVAILABLE:
                return None
            buf = io.BytesIO()
            doc = SimpleDocTemplate(
                buf,
                pagesize=letter,
                leftMargin=36,
                rightMargin=36,
                topMargin=32,
                bottomMargin=32,
            )
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "BulkTitle",
                parent=styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=18,
                leading=22,
                textColor=colors.HexColor("#1E2252"),
                spaceAfter=2,
            )
            sub_style = ParagraphStyle(
                "BulkSub",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=13,
                textColor=colors.HexColor("#475569"),
            )
            sec_hdr = ParagraphStyle(
                "BulkSecHdr",
                parent=styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=14,
                textColor=colors.HexColor("#1E2252"),
                spaceBefore=10,
                spaceAfter=6,
            )
            normal_sm = ParagraphStyle(
                "BulkNormSm",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=9.5,
                leading=13,
                textColor=colors.HexColor("#0F172A"),
            )

            story = []
            doc_type_str = str(q_data.get("doc_type", "ESTIMATE")).upper()
            badge_title = "BULK ORDER TAX INVOICE / BILL" if doc_type_str == "INVOICE" else "BULK ORDER ESTIMATE / QUOTATION"
            loc_str = str(q_data.get("location") or CITY).upper()

            header_left = [
                Paragraph(f"<b>KULFI FACTORY — {escape(loc_str)} FRANCHISE</b>", title_style),
                Paragraph("Artisanal Stick &amp; Matka Kulfis • Party, Catering &amp; Bulk Orders", sub_style),
                Paragraph(f"<b>{badge_title}</b>", ParagraphStyle("BadgeP", parent=sub_style, fontName="Helvetica-Bold", fontSize=11, textColor=colors.HexColor("#C43D17"), spaceBefore=4)),
            ]
            if os.path.exists("assets/logo.png"):
                try:
                    rl_logo = RLImage("assets/logo.png", width=62, height=62)
                    hdr_tbl = Table([[rl_logo, header_left]], colWidths=[74, 466])
                    hdr_tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
                    story.append(hdr_tbl)
                except Exception:
                    for p in header_left:
                        story.append(p)
            else:
                for p in header_left:
                    story.append(p)

            story.append(Spacer(1, 10))

            q_num = escape(str(q_data.get("quote_number") or "—"))
            q_dt = escape(str(q_data.get("quote_date") or "—"))
            ev_dt = escape(str(q_data.get("event_date") or "—"))
            cust_name = escape(str(q_data.get("customer_name") or "Valued Customer"))
            cust_phone = escape(str(q_data.get("customer_phone") or "—"))
            cust_addr = escape(str(q_data.get("customer_address") or "—"))
            status_txt = escape(str(q_data.get("status") or doc_type_str.title()))

            meta_data = [
                [
                    Paragraph(f"<b>Customer:</b> {cust_name}", normal_sm),
                    Paragraph(f"<b>{doc_type_str.title()} No:</b> {q_num}", normal_sm),
                ],
                [
                    Paragraph(f"<b>Phone:</b> {cust_phone}", normal_sm),
                    Paragraph(f"<b>Date:</b> {q_dt}", normal_sm),
                ],
                [
                    Paragraph(f"<b>Venue / Address:</b> {cust_addr}", normal_sm),
                    Paragraph(f"<b>Event / Delivery Date:</b> {ev_dt} &nbsp; (<b>{status_txt}</b>)", normal_sm),
                ],
            ]
            meta_tbl = Table(meta_data, colWidths=[280, 260])
            meta_tbl.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            story.append(meta_tbl)
            story.append(Paragraph("Itemized Flavour Breakdown", sec_hdr))

            disc_pct = float(q_data.get("discount_pct") or 0.0)
            tbl_rows = [["#", "Flavour", "Code", "MRP / Pc (Rs.)", "Net Rate (Rs.)", "Qty (Pcs)", "Gross (Rs.)", "Net Amount (Rs.)"]]
            idx_counter = 1
            qty_map = q_data.get("qty_map", {})
            for code in FLAVOR_CODES:
                qty = int(qty_map.get(code, 0) or 0)
                if qty <= 0:
                    continue
                f_info = FLAVOR_MAP[code]
                mrp = float(f_info["mrp"])
                net_rate = mrp * (1.0 - disc_pct / 100.0)
                gross_line = qty * mrp
                net_line = qty * net_rate
                tbl_rows.append([
                    str(idx_counter),
                    f_info["name"],
                    code,
                    f"{mrp:,.2f}",
                    f"{net_rate:,.2f}",
                    f"{qty:,}",
                    f"{gross_line:,.2f}",
                    f"{net_line:,.2f}",
                ])
                idx_counter += 1

            if len(tbl_rows) == 1:
                tbl_rows.append(["—", "No flavours selected", "—", "0.00", "0.00", "0", "0.00", "0.00"])

            tot_units = int(q_data.get("total_units") or 0)
            gross_amt = float(q_data.get("gross_mrp_amount") or 0.0)
            disc_amt = float(q_data.get("discount_amount") or 0.0)
            final_amt = float(q_data.get("final_amount") or 0.0)
            adv_paid = float(q_data.get("advance_paid") or 0.0)
            bal_due = max(0.0, final_amt - adv_paid)

            tbl_rows.append(["", "TOTAL PIECES & AMOUNT", "", "", "", f"{tot_units:,} pcs", f"Rs. {gross_amt:,.2f}", f"Rs. {final_amt:,.2f}"])

            item_tbl = Table(tbl_rows, colWidths=[26, 134, 42, 68, 68, 58, 70, 74])
            item_tbl.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E2252")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 0), (2, -1), "CENTER"),
                    ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#FFFFFF")]),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFF6FF")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ])
            )
            story.append(item_tbl)
            story.append(Spacer(1, 10))

            sum_rows = [
                ["Gross Amount (At MRP):", f"Rs. {gross_amt:,.2f}"],
                [f"Special Bulk Discount ({disc_pct:.1f}%):", f"- Rs. {disc_amt:,.2f}"],
                [f"Net Payable ({doc_type_str.title()} Total):", f"Rs. {final_amt:,.2f}"],
            ]
            if doc_type_str == "INVOICE" or adv_paid > 0:
                sum_rows.append(["Advance / Amount Paid:", f"Rs. {adv_paid:,.2f}"])
                sum_rows.append(["Balance Due:", f"Rs. {bal_due:,.2f}"])

            sum_tbl = Table(sum_rows, colWidths=[390, 150])
            sum_tbl.setStyle(
                TableStyle([
                    ("ALIGN", (0, 0), (0, -1), "RIGHT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1E2252")),
                    ("BACKGROUND", (0, 2), (-1, 2), colors.HexColor("#ECFDF5")),
                    ("TEXTCOLOR", (0, 2), (-1, 2), colors.HexColor("#047857")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ])
            )
            story.append(sum_tbl)

            notes_str = str(q_data.get("notes") or "").strip()
            if notes_str:
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"<b>Notes / Terms:</b> {escape(notes_str)}", normal_sm))

            story.append(Spacer(1, 14))
            story.append(
                Paragraph(
                    "Thank you for choosing Kulfi Factory! For bulk party &amp; catering inquiries, please contact Kulfi Factory Operations.",
                    ParagraphStyle("FooterNote", parent=sub_style, alignment=1, fontSize=8.5),
                )
            )
            doc.build(story)
            return buf.getvalue()

        def build_bulk_whatsapp_text(q_data):
            doc_type_str = str(q_data.get("doc_type", "ESTIMATE")).upper()
            hdr = "🧾 *KULFI FACTORY — BULK ORDER INVOICE*" if doc_type_str == "INVOICE" else "🍦 *KULFI FACTORY — BULK ORDER ESTIMATE*"
            lines = [
                hdr,
                f"*{doc_type_str.title()} No:* {q_data.get('quote_number') or '—'}",
                f"*Customer:* {q_data.get('customer_name') or 'Valued Customer'}",
                f"*Event / Delivery Date:* {q_data.get('event_date') or q_data.get('quote_date') or '—'}",
                "--------------------------------",
                "*Flavour Breakdown:*",
            ]
            qty_map = q_data.get("qty_map", {})
            disc_pct = float(q_data.get("discount_pct") or 0.0)
            for code in FLAVOR_CODES:
                q = int(qty_map.get(code, 0) or 0)
                if q > 0:
                    f_info = FLAVOR_MAP[code]
                    mrp = float(f_info["mrp"])
                    lines.append(f"• {f_info['name']}: *{q} pcs* (MRP ₹{mrp:.0f} → ₹{q * mrp:,.0f})")
            lines.extend([
                "--------------------------------",
                f"*Total Quantity:* {int(q_data.get('total_units') or 0)} pieces",
                f"*Gross Value (MRP):* ₹{float(q_data.get('gross_mrp_amount') or 0):,.2f}",
                f"*Special Bulk Discount ({disc_pct:.1f}%):* -₹{float(q_data.get('discount_amount') or 0):,.2f}",
                f"*Net Payable Amount:* *₹{float(q_data.get('final_amount') or 0):,.2f}*",
            ])
            adv = float(q_data.get("advance_paid") or 0.0)
            if doc_type_str == "INVOICE" or adv > 0:
                bal = max(0.0, float(q_data.get("final_amount") or 0.0) - adv)
                lines.append(f"*Advance Paid:* ₹{adv:,.2f}")
                lines.append(f"*Balance Due:* *₹{bal:,.2f}*")
            if str(q_data.get("notes") or "").strip():
                lines.append(f"*Notes:* {str(q_data.get('notes')).strip()}")
            return "\n".join(lines)

        # Initialize session state defaults for the Bulk Order Estimator
        if "bulk_checked_flavors" not in st.session_state:
            st.session_state["bulk_checked_flavors"] = list(FLAVOR_CODES)
        if "bulk_planning_mode" not in st.session_state:
            st.session_state["bulk_planning_mode"] = "By Total Pieces (e.g. 200 / 400 pcs)"
        if "bulk_dist_style" not in st.session_state:
            st.session_state["bulk_dist_style"] = "Popular Party Mix (Weighted)"
        if "bulk_target_pieces" not in st.session_state:
            st.session_state["bulk_target_pieces"] = 200
        if "bulk_target_budget" not in st.session_state:
            st.session_state["bulk_target_budget"] = 10000.0
        if "bulk_discount_pct" not in st.session_state:
            st.session_state["bulk_discount_pct"] = 10.0
        if "bulk_doc_type" not in st.session_state:
            st.session_state["bulk_doc_type"] = "ESTIMATE"
        if "bulk_editing_id" not in st.session_state:
            st.session_state["bulk_editing_id"] = None

        # Seed initial quantities if not present
        if not any(f"bulk_qty_{c}" in st.session_state for c in FLAVOR_CODES):
            init_dist = distribute_bulk_pieces(200, FLAVOR_CODES, mode="weighted")
            for c in FLAVOR_CODES:
                st.session_state[f"bulk_qty_{c}"] = int(init_dist.get(c, 0))

        def _trigger_bulk_redistribution():
            checked = [c for c in FLAVOR_CODES if st.session_state.get(f"bulk_chk_{c}", True)]
            st.session_state["bulk_checked_flavors"] = checked
            dist_mode = "weighted" if "Popular" in str(st.session_state.get("bulk_dist_style", "")) else "even"
            if "Budget" in str(st.session_state.get("bulk_planning_mode", "")):
                new_map = distribute_bulk_budget(
                    st.session_state.get("bulk_target_budget", 10000.0),
                    st.session_state.get("bulk_discount_pct", 10.0),
                    checked,
                    mode=dist_mode,
                )
            else:
                new_map = distribute_bulk_pieces(
                    st.session_state.get("bulk_target_pieces", 200),
                    checked,
                    mode=dist_mode,
                )
            for c in FLAVOR_CODES:
                st.session_state[f"bulk_qty_{c}"] = int(new_map.get(c, 0))

        bulk_tab1, bulk_tab2 = st.tabs([
            "🧮 Estimate & Invoice Builder",
            "🗂️ Saved Estimates & Invoices History",
        ])

        with bulk_tab1:
            if st.session_state.get("_bulk_save_banner"):
                st.success(st.session_state.pop("_bulk_save_banner"))

            editing_id = st.session_state.get("bulk_editing_id")
            if editing_id:
                eb1, eb2 = st.columns([4, 1])
                with eb1:
                    st.info(f"✏️ Currently editing saved record **#{editing_id}** ({st.session_state.get('bulk_quote_no', '')}). You can modify quantities, discount, or switch Document Type to **INVOICE** to finalize delivery.")
                with eb2:
                    if st.button("➕ Start Fresh Quote", use_container_width=True, key="btn_reset_bulk_quote"):
                        st.session_state["bulk_editing_id"] = None
                        st.session_state["bulk_doc_type"] = "ESTIMATE"
                        st.session_state["bulk_quote_no"] = f"EST-{date.today().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M')}"
                        st.session_state["bulk_cust_name"] = ""
                        st.session_state["bulk_cust_phone"] = ""
                        st.session_state["bulk_cust_addr"] = ""
                        st.session_state["bulk_advance_paid"] = 0.0
                        st.session_state["bulk_notes"] = ""
                        st.rerun()

            # STEP 1: Planning Mode & Smart Parameters
            with st.container(border=True):
                st.markdown("#### 1. Order Planning Mode & Smart Distribution")
                pm1, pm2, pm3, pm4 = st.columns([1.45, 1.35, 1.1, 1.1])
                with pm1:
                    planning_mode = st.radio(
                        "How is the customer asking for the quote?",
                        ["By Total Pieces (e.g. 200 / 400 pcs)", "By Customer Budget (e.g. ₹10,000 INR)"],
                        key="bulk_planning_mode",
                        on_change=_trigger_bulk_redistribution,
                    )
                with pm2:
                    dist_style = st.selectbox(
                        "Auto-Distribution Style",
                        ["Popular Party Mix (Weighted)", "Even Split Across Selected Flavours"],
                        key="bulk_dist_style",
                        on_change=_trigger_bulk_redistribution,
                    )
                with pm3:
                    if "Pieces" in planning_mode:
                        target_pieces = st.number_input(
                            "Target Total Pieces",
                            min_value=10,
                            max_value=50000,
                            step=10,
                            key="bulk_target_pieces",
                            on_change=_trigger_bulk_redistribution,
                        )
                    else:
                        target_budget = st.number_input(
                            "Customer Budget (₹ INR)",
                            min_value=500.0,
                            max_value=5000000.0,
                            step=500.0,
                            format="%.0f",
                            key="bulk_target_budget",
                            on_change=_trigger_bulk_redistribution,
                        )
                with pm4:
                    discount_pct = st.number_input(
                        "Discount (%)",
                        min_value=0.0,
                        max_value=80.0,
                        step=1.0,
                        format="%.1f",
                        key="bulk_discount_pct",
                        on_change=_trigger_bulk_redistribution if "Budget" in planning_mode else None,
                    )

                # Quick Preset Callbacks (mutate session_state safely before widget instantiation)
                def _apply_bulk_preset_pieces(pcs_val):
                    st.session_state["bulk_target_pieces"] = int(pcs_val)
                    _trigger_bulk_redistribution()

                def _apply_bulk_preset_budget(bdg_val):
                    st.session_state["bulk_target_budget"] = float(bdg_val)
                    _trigger_bulk_redistribution()

                def _zero_all_bulk_counts():
                    for c in FLAVOR_CODES:
                        st.session_state[f"bulk_qty_{c}"] = 0

                def _apply_bulk_discount_tier(disc_val, sim_quantities):
                    st.session_state["bulk_discount_pct"] = float(disc_val)
                    for c in FLAVOR_CODES:
                        st.session_state[f"bulk_qty_{c}"] = int(sim_quantities.get(c, 0))

                def _select_bulk_flavour_preset(mode_key):
                    for c in FLAVOR_CODES:
                        if mode_key == "ALL":
                            st.session_state[f"bulk_chk_{c}"] = True
                        elif mode_key == "NO_BM":
                            st.session_state[f"bulk_chk_{c}"] = (c != "BM")
                        elif mode_key == "TOP5":
                            st.session_state[f"bulk_chk_{c}"] = (c in {"ML", "MM", "PS", "MN", "KB"})
                    _trigger_bulk_redistribution()

                # Quick Preset Buttons for Pieces or Budget
                qp_cols = st.columns([1, 1, 1, 1, 1.3, 1.3])
                if "Pieces" in planning_mode:
                    for idx_p, preset_pcs in enumerate([100, 200, 300, 400]):
                        with qp_cols[idx_p]:
                            st.button(
                                f"⚡ {preset_pcs} Pieces",
                                use_container_width=True,
                                key=f"preset_pcs_{preset_pcs}",
                                on_click=_apply_bulk_preset_pieces,
                                args=(preset_pcs,),
                            )
                else:
                    for idx_b, preset_b in enumerate([5000, 10000, 15000, 25000]):
                        with qp_cols[idx_b]:
                            st.button(
                                f"⚡ ₹{preset_b:,} Budget",
                                use_container_width=True,
                                key=f"preset_bdg_{preset_b}",
                                on_click=_apply_bulk_preset_budget,
                                args=(preset_b,),
                            )
                with qp_cols[4]:
                    st.button(
                        "🔄 Re-Distribute Counts",
                        type="primary",
                        use_container_width=True,
                        key="btn_manual_redist",
                        on_click=_trigger_bulk_redistribution,
                    )
                with qp_cols[5]:
                    st.button(
                        "🧹 Zero All Counts",
                        use_container_width=True,
                        key="btn_zero_bulk_counts",
                        on_click=_zero_all_bulk_counts,
                    )

                # If in Budget mode, show an interactive Discount Tier Comparison Matrix (0%, 5%, 10%, 15%, 20% off)
                if "Budget" in planning_mode:
                    st.markdown("##### 💡 Instant Budget Offer Options — What Can We Offer for ₹{:,.0f}?".format(float(st.session_state.get("bulk_target_budget", 10000.0))))
                    checked_now = [c for c in FLAVOR_CODES if st.session_state.get(f"bulk_chk_{c}", True)]
                    dist_mode_now = "weighted" if "Popular" in str(st.session_state.get("bulk_dist_style", "")) else "even"
                    tier_pcts = [0.0, 5.0, 10.0, 15.0, 20.0]
                    tier_cols = st.columns(len(tier_pcts), gap="small")
                    for t_idx, t_disc in enumerate(tier_pcts):
                        sim_map = distribute_bulk_budget(st.session_state.get("bulk_target_budget", 10000.0), t_disc, checked_now, mode=dist_mode_now)
                        sim_pcs = sum(sim_map.values())
                        sim_gross = sum(sim_map[c] * float(FLAVOR_MAP[c]["mrp"]) for c in FLAVOR_CODES)
                        sim_cost = sum(sim_map[c] * float(FLAVOR_MAP[c]["cost_price"]) for c in FLAVOR_CODES)
                        sim_net = sim_gross * (1.0 - t_disc / 100.0)
                        sim_profit = sim_net - sim_cost
                        is_active_tier = abs(float(st.session_state.get("bulk_discount_pct", 0.0)) - t_disc) < 0.05
                        border_col = "#4F46E5" if is_active_tier else "#CBD5E1"
                        bg_col = "#EFF6FF" if is_active_tier else "#F8FAFC"
                        with tier_cols[t_idx]:
                            st.markdown(
                                f"""
                                <div style='background:{bg_col};border:1.8px solid {border_col};border-radius:10px;padding:8px 10px;text-align:center;margin-bottom:4px;'>
                                    <div style='font-size:11px;font-weight:900;color:#1E2252;'>{t_disc:.0f}% DISCOUNT</div>
                                    <div style='font-size:18px;font-weight:900;color:#047857;margin:2px 0;'>{sim_pcs:,} pcs</div>
                                    <div style='font-size:11px;font-weight:800;color:#1E2252;'>Net: ₹{sim_net:,.0f}</div>
                                    <div style='font-size:10px;color:#475569;'>MRP Worth: ₹{sim_gross:,.0f}</div>
                                    <div style='font-size:10px;font-weight:800;color:{"#137333" if sim_profit >= 0 else "#C43D17"};'>Profit: ₹{sim_profit:,.0f}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                            st.button(
                                f"Apply {t_disc:.0f}% Offer",
                                key=f"apply_tier_{int(t_disc)}",
                                use_container_width=True,
                                on_click=_apply_bulk_discount_tier,
                                args=(float(t_disc), dict(sim_map)),
                            )

            # STEP 2: Interactive Flavour Checkboxes & Editable Quantities Table
            with st.container(border=True):
                st_hdr1, st_hdr2, st_hdr3, st_hdr4 = st.columns([2.0, 1.1, 1.25, 1.1], gap="small", vertical_alignment="center")
                with st_hdr1:
                    st.markdown("#### 2. Flavour Selection & Quantity Distribution")
                with st_hdr2:
                    st.button(
                        "✅ Select All Flavours",
                        use_container_width=True,
                        key="bulk_sel_all_flv",
                        on_click=_select_bulk_flavour_preset,
                        args=("ALL",),
                    )
                with st_hdr3:
                    st.button(
                        "🍦 Stick Kulfis Only",
                        use_container_width=True,
                        key="bulk_sel_no_bm",
                        on_click=_select_bulk_flavour_preset,
                        args=("NO_BM",),
                    )
                with st_hdr4:
                    st.button(
                        "⭐ Top 5 Bestsellers",
                        use_container_width=True,
                        key="bulk_sel_top5",
                        on_click=_select_bulk_flavour_preset,
                        args=("TOP5",),
                    )

                bh1, bh2, bh3, bh4, bh5, bh6, bh7, bh8 = st.columns([0.55, 1.75, 0.85, 0.85, 1.15, 1.05, 1.05, 1.1], gap="small")
                bh1.markdown("<div class='entry-grid-header'>Incl.</div>", unsafe_allow_html=True)
                bh2.markdown("<div class='entry-grid-header' style='text-align:left;'>Flavour</div>", unsafe_allow_html=True)
                bh3.markdown("<div class='entry-grid-header'>Cost (CP)</div>", unsafe_allow_html=True)
                bh4.markdown("<div class='entry-grid-header'>MRP</div>", unsafe_allow_html=True)
                bh5.markdown("<div class='entry-grid-header' style='background:#D1FAE5;color:#111111;border:1px solid #4ADE80;'>Qty (Pcs) ✏️</div>", unsafe_allow_html=True)
                bh6.markdown("<div class='entry-grid-header'>Total CP</div>", unsafe_allow_html=True)
                bh7.markdown("<div class='entry-grid-header'>Gross MRP</div>", unsafe_allow_html=True)
                bh8.markdown("<div class='entry-grid-header' style='text-align:right;background:#BFDBFE;color:#111111;border:1px solid #93C5FD;'>After Disc.</div>", unsafe_allow_html=True)

                curr_disc_pct = float(st.session_state.get("bulk_discount_pct", 0.0) or 0.0)
                disc_mult = 1.0 - (curr_disc_pct / 100.0)

                qty_map_current = {}
                tot_units_b = 0
                tot_cost_b = 0.0
                tot_gross_mrp_b = 0.0
                tot_net_b = 0.0

                for code in FLAVOR_CODES:
                    f_info = FLAVOR_MAP[code]
                    chk_key = f"bulk_chk_{code}"
                    qty_key = f"bulk_qty_{code}"
                    if chk_key not in st.session_state:
                        st.session_state[chk_key] = True
                    if qty_key not in st.session_state:
                        st.session_state[qty_key] = 0

                    r_c1, r_c2, r_c3, r_c4, r_c5, r_c6, r_c7, r_c8 = st.columns([0.55, 1.75, 0.85, 0.85, 1.15, 1.05, 1.05, 1.1], gap="small")
                    with r_c1:
                        is_checked = st.checkbox(
                            f"Include {f_info['name']}",
                            key=chk_key,
                            label_visibility="collapsed",
                            on_change=_trigger_bulk_redistribution,
                        )
                    with r_c2:
                        opacity_style = "opacity:1;" if is_checked else "opacity:0.45;"
                        st.markdown(
                            f"<div class='entry-grid-cell-flavour' style='{opacity_style}'><span>{escape(f_info['name'])}</span><span style='color:#2563EB;font-size:10.5px;'>{code}</span></div>",
                            unsafe_allow_html=True,
                        )
                    with r_c3:
                        st.markdown(f"<div class='entry-grid-cell'>₹{float(f_info['cost_price']):.1f}</div>", unsafe_allow_html=True)
                    with r_c4:
                        st.markdown(f"<div class='entry-grid-cell' style='color:#1E2252;'>₹{float(f_info['mrp']):.0f}</div>", unsafe_allow_html=True)
                    with r_c5:
                        q_val = int(
                            st.number_input(
                                f"Bulk Qty {f_info['name']}",
                                min_value=0,
                                max_value=50000,
                                step=5,
                                format="%d",
                                key=qty_key,
                                label_visibility="collapsed",
                            )
                        )
                    qty_map_current[code] = q_val
                    line_cp = q_val * float(f_info["cost_price"])
                    line_mrp = q_val * float(f_info["mrp"])
                    line_net = line_mrp * disc_mult

                    tot_units_b += q_val
                    tot_cost_b += line_cp
                    tot_gross_mrp_b += line_mrp
                    tot_net_b += line_net

                    with r_c6:
                        st.markdown(f"<div class='entry-grid-cell'>₹{line_cp:,.0f}</div>", unsafe_allow_html=True)
                    with r_c7:
                        st.markdown(f"<div class='entry-grid-cell'>₹{line_mrp:,.0f}</div>", unsafe_allow_html=True)
                    with r_c8:
                        st.markdown(f"<div class='entry-grid-cell-amount'>₹{line_net:,.0f}</div>", unsafe_allow_html=True)

                tot_disc_amt_b = max(0.0, tot_gross_mrp_b - tot_net_b)
                tot_profit_b = tot_net_b - tot_cost_b
                margin_pct_b = (tot_profit_b / tot_net_b * 100.0) if tot_net_b > 0 else 0.0
                eff_rate_pc = (tot_net_b / tot_units_b) if tot_units_b > 0 else 0.0
                cp_rate_pc = (tot_cost_b / tot_units_b) if tot_units_b > 0 else 0.0

                tf1, tf2, tf3, tf4, tf5, tf6, tf7, tf8 = st.columns([0.55, 1.75, 0.85, 0.85, 1.15, 1.05, 1.05, 1.1], gap="small")
                tf1.markdown("<div class='entry-grid-total-row'>✓</div>", unsafe_allow_html=True)
                tf2.markdown("<div class='entry-grid-total-row' style='text-align:left;'>TOTAL</div>", unsafe_allow_html=True)
                tf3.markdown(f"<div class='entry-grid-total-row'>₹{cp_rate_pc:.1f}/pc</div>", unsafe_allow_html=True)
                tf4.markdown("<div class='entry-grid-total-row'>—</div>", unsafe_allow_html=True)
                tf5.markdown(f"<div class='entry-grid-total-row' style='color:#047857;'>{tot_units_b:,} pcs</div>", unsafe_allow_html=True)
                tf6.markdown(f"<div class='entry-grid-total-row'>₹{tot_cost_b:,.0f}</div>", unsafe_allow_html=True)
                tf7.markdown(f"<div class='entry-grid-total-row'>₹{tot_gross_mrp_b:,.0f}</div>", unsafe_allow_html=True)
                tf8.markdown(f"<div class='entry-grid-total-row' style='text-align:right;color:#C43D17;'>₹{tot_net_b:,.0f}</div>", unsafe_allow_html=True)

            # Live Cost, Discount & Margin Summary Cards
            profit_color = "#047857" if tot_profit_b >= 0 else "#C43D17"
            st.markdown(
                f"""
                <div class='bulk-kpi-strip'>
                    <div class='bulk-kpi-card'>
                        <div class='bulk-kpi-label'>Total Pieces</div>
                        <div class='bulk-kpi-val' style='color:#047857;'>{tot_units_b:,} pcs</div>
                        <div class='bulk-kpi-sub'>{sum(1 for q in qty_map_current.values() if q > 0)} active flavours</div>
                    </div>
                    <div class='bulk-kpi-card'>
                        <div class='bulk-kpi-label'>Gross MRP Value</div>
                        <div class='bulk-kpi-val'>₹{tot_gross_mrp_b:,.2f}</div>
                        <div class='bulk-kpi-sub'>Avg MRP: ₹{(tot_gross_mrp_b / tot_units_b if tot_units_b else 0):.1f}/pc</div>
                    </div>
                    <div class='bulk-kpi-card' style='background:#EFF6FF;border-color:#D97706;'>
                        <div class='bulk-kpi-label'>Discount ({curr_disc_pct:.1f}%)</div>
                        <div class='bulk-kpi-val' style='color:#B45309;'>- ₹{tot_disc_amt_b:,.2f}</div>
                        <div class='bulk-kpi-sub'>Customer savings</div>
                    </div>
                    <div class='bulk-kpi-card' style='background:#ECFDF5;border-color:#047857;'>
                        <div class='bulk-kpi-label'>Revised Quote / Net</div>
                        <div class='bulk-kpi-val' style='color:#047857;'>₹{tot_net_b:,.2f}</div>
                        <div class='bulk-kpi-sub'>Eff. Rate: ₹{eff_rate_pc:.1f}/pc</div>
                    </div>
                    <div class='bulk-kpi-card'>
                        <div class='bulk-kpi-label'>Our Cost (CP)</div>
                        <div class='bulk-kpi-val' style='color:#1E2252;'>₹{tot_cost_b:,.2f}</div>
                        <div class='bulk-kpi-sub'>Avg CP: ₹{cp_rate_pc:.1f}/pc</div>
                    </div>
                    <div class='bulk-kpi-card'>
                        <div class='bulk-kpi-label'>Est. Gross Profit</div>
                        <div class='bulk-kpi-val' style='color:{profit_color};'>₹{tot_profit_b:,.2f}</div>
                        <div class='bulk-kpi-sub' style='color:{profit_color};'>Margin: {margin_pct_b:.1f}%</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # STEP 3: Customer Details, Document Type (Estimate vs Invoice), Save, PDF & WhatsApp
            with st.container(border=True):
                st.markdown("#### 3. Customer Details, Save to Database & Share (Estimate / Invoice PDF & WhatsApp)")
                if "bulk_quote_no" not in st.session_state or not st.session_state["bulk_quote_no"]:
                    prefix_q = "INV" if st.session_state.get("bulk_doc_type") == "INVOICE" else "EST"
                    st.session_state["bulk_quote_no"] = f"{prefix_q}-{date.today().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M')}"

                cd1, cd2, cd3, cd4 = st.columns([1.1, 1.2, 1.1, 1.1])
                with cd1:
                    doc_type_sel = st.selectbox(
                        "Document Type",
                        ["ESTIMATE", "INVOICE"],
                        key="bulk_doc_type",
                    )
                with cd2:
                    quote_no_inp = st.text_input("Estimate / Invoice No.", key="bulk_quote_no")
                with cd3:
                    quote_dt_inp = st.date_input("Document Date", value=st.session_state.get("bulk_quote_dt", date.today()), format="DD-MM-YYYY", key="bulk_quote_dt")
                with cd4:
                    event_dt_inp = st.date_input("Event / Delivery Date", value=st.session_state.get("bulk_event_dt", date.today() + timedelta(days=1)), format="DD-MM-YYYY", key="bulk_event_dt")

                cd5, cd6, cd7, cd8 = st.columns([1.4, 1.1, 1.1, 1.1])
                with cd5:
                    cust_name_inp = st.text_input("Customer / Organization Name *", placeholder="e.g. Rajesh Sharma / Wedding Catering", key="bulk_cust_name")
                with cd6:
                    cust_phone_inp = st.text_input("Customer WhatsApp / Phone", placeholder="10-digit mobile number", key="bulk_cust_phone")
                with cd7:
                    status_opts = ["Estimate Sent", "Draft", "Confirmed", "Invoiced / Delivered", "Cancelled"]
                    default_st_idx = 3 if doc_type_sel == "INVOICE" else 0
                    order_status_inp = st.selectbox("Order Status", status_opts, index=default_st_idx, key="bulk_status_sel")
                with cd8:
                    advance_paid_inp = st.number_input("Advance / Paid Amount (₹)", min_value=0.0, max_value=5000000.0, step=100.0, format="%.0f", key="bulk_advance_paid")

                cd9, cd10 = st.columns([1.5, 1.5])
                with cd9:
                    cust_addr_inp = st.text_input("Event Venue / Delivery Address", placeholder="Optional venue or address", key="bulk_cust_addr")
                with cd10:
                    notes_inp = st.text_input("Notes / Special Instructions", placeholder="e.g. Dry ice box required, delivery by 6:30 PM", key="bulk_notes")

                balance_due_calc = max(0.0, tot_net_b - float(advance_paid_inp or 0.0))

                current_q_payload = {
                    "doc_type": doc_type_sel,
                    "quote_number": quote_no_inp.strip() or f"{doc_type_sel[:3]}-{date.today().strftime('%Y%m%d')}",
                    "quote_date": quote_dt_inp.strftime("%d-%b-%Y"),
                    "event_date": event_dt_inp.strftime("%d-%b-%Y"),
                    "location": CITY,
                    "customer_name": cust_name_inp.strip() or "Valued Customer",
                    "customer_phone": cust_phone_inp.strip(),
                    "customer_address": cust_addr_inp.strip(),
                    "qty_map": qty_map_current,
                    "total_units": tot_units_b,
                    "gross_mrp_amount": tot_gross_mrp_b,
                    "total_cost_amount": tot_cost_b,
                    "discount_pct": curr_disc_pct,
                    "discount_amount": tot_disc_amt_b,
                    "final_amount": tot_net_b,
                    "advance_paid": float(advance_paid_inp or 0.0),
                    "balance_due": balance_due_calc,
                    "status": order_status_inp,
                    "notes": notes_inp.strip(),
                }

                act1, act2, act3, act4 = st.columns([1.3, 1.3, 1.2, 1.2])
                with act1:
                    save_btn_lbl = f"💾 Update {doc_type_sel.title()} #{editing_id}" if editing_id else f"💾 Save {doc_type_sel.title()} to Database"
                    if st.button(save_btn_lbl, type="primary", use_container_width=True, key="btn_save_bulk_quote"):
                        if tot_units_b <= 0:
                            st.error("Please allocate at least 1 kulfi unit before saving.")
                        elif not cust_name_inp.strip():
                            st.error("Please enter the Customer / Organization Name.")
                        else:
                            try:
                                checked_str = ",".join([c for c in FLAVOR_CODES if st.session_state.get(f"bulk_chk_{c}", True)])
                                p_mode_db = "BUDGET" if "Budget" in planning_mode else "PIECES"
                                with db_conn.session as s:
                                    if editing_id:
                                        s.execute(
                                            text("""
                                                UPDATE public.bulk_order_quotes
                                                SET doc_type = :dtype,
                                                    quote_number = :qno,
                                                    quote_date = :qdt,
                                                    event_date = :edt,
                                                    location = :loc,
                                                    customer_name = :cname,
                                                    customer_phone = :cphone,
                                                    customer_address = :caddr,
                                                    planning_mode = :pmode,
                                                    target_pieces = :tpcs,
                                                    target_budget = :tbdg,
                                                    selected_flavors = :sflav,
                                                    ml_units = :ml, mm_units = :mm, ps_units = :ps, mn_units = :mn,
                                                    kb_units = :kb, bm_units = :bm, sg_units = :sg, ch_units = :ch, ra_units = :ra,
                                                    total_units = :totu,
                                                    gross_mrp_amount = :gmrp,
                                                    total_cost_amount = :tcost,
                                                    discount_pct = :dpct,
                                                    discount_amount = :damt,
                                                    final_amount = :famt,
                                                    advance_paid = :adv,
                                                    balance_due = :bal,
                                                    status = :st,
                                                    notes = :notes,
                                                    updated_at = NOW()
                                                WHERE id = :id;
                                            """),
                                            {
                                                "id": int(editing_id),
                                                "dtype": doc_type_sel,
                                                "qno": current_q_payload["quote_number"],
                                                "qdt": quote_dt_inp,
                                                "edt": event_dt_inp,
                                                "loc": CITY,
                                                "cname": cust_name_inp.strip(),
                                                "cphone": cust_phone_inp.strip() or None,
                                                "caddr": cust_addr_inp.strip() or None,
                                                "pmode": p_mode_db,
                                                "tpcs": int(st.session_state.get("bulk_target_pieces", tot_units_b)),
                                                "tbdg": float(st.session_state.get("bulk_target_budget", tot_net_b)),
                                                "sflav": checked_str,
                                                "ml": int(qty_map_current.get("ML", 0)),
                                                "mm": int(qty_map_current.get("MM", 0)),
                                                "ps": int(qty_map_current.get("PS", 0)),
                                                "mn": int(qty_map_current.get("MN", 0)),
                                                "kb": int(qty_map_current.get("KB", 0)),
                                                "bm": int(qty_map_current.get("BM", 0)),
                                                "sg": int(qty_map_current.get("SG", 0)),
                                                "ch": int(qty_map_current.get("CH", 0)),
                                                "ra": int(qty_map_current.get("RA", 0)),
                                                "totu": int(tot_units_b),
                                                "gmrp": float(tot_gross_mrp_b),
                                                "tcost": float(tot_cost_b),
                                                "dpct": float(curr_disc_pct),
                                                "damt": float(tot_disc_amt_b),
                                                "famt": float(tot_net_b),
                                                "adv": float(advance_paid_inp or 0.0),
                                                "bal": float(balance_due_calc),
                                                "st": order_status_inp,
                                                "notes": notes_inp.strip() or None,
                                            },
                                        )
                                        saved_id = int(editing_id)
                                    else:
                                        ins_q = s.execute(
                                            text("""
                                                INSERT INTO public.bulk_order_quotes (
                                                    doc_type, quote_number, quote_date, event_date, location,
                                                    customer_name, customer_phone, customer_address,
                                                    planning_mode, target_pieces, target_budget, selected_flavors,
                                                    ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                                                    total_units, gross_mrp_amount, total_cost_amount,
                                                    discount_pct, discount_amount, final_amount, advance_paid, balance_due,
                                                    status, notes, created_by, source_app
                                                ) VALUES (
                                                    :dtype, :qno, :qdt, :edt, :loc,
                                                    :cname, :cphone, :caddr,
                                                    :pmode, :tpcs, :tbdg, :sflav,
                                                    :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra,
                                                    :totu, :gmrp, :tcost,
                                                    :dpct, :damt, :famt, :adv, :bal,
                                                    :st, :notes, 'Admin', 'web app'
                                                ) RETURNING id;
                                            """),
                                            {
                                                "dtype": doc_type_sel,
                                                "qno": current_q_payload["quote_number"],
                                                "qdt": quote_dt_inp,
                                                "edt": event_dt_inp,
                                                "loc": CITY,
                                                "cname": cust_name_inp.strip(),
                                                "cphone": cust_phone_inp.strip() or None,
                                                "caddr": cust_addr_inp.strip() or None,
                                                "pmode": p_mode_db,
                                                "tpcs": int(st.session_state.get("bulk_target_pieces", tot_units_b)),
                                                "tbdg": float(st.session_state.get("bulk_target_budget", tot_net_b)),
                                                "sflav": checked_str,
                                                "ml": int(qty_map_current.get("ML", 0)),
                                                "mm": int(qty_map_current.get("MM", 0)),
                                                "ps": int(qty_map_current.get("PS", 0)),
                                                "mn": int(qty_map_current.get("MN", 0)),
                                                "kb": int(qty_map_current.get("KB", 0)),
                                                "bm": int(qty_map_current.get("BM", 0)),
                                                "sg": int(qty_map_current.get("SG", 0)),
                                                "ch": int(qty_map_current.get("CH", 0)),
                                                "ra": int(qty_map_current.get("RA", 0)),
                                                "totu": int(tot_units_b),
                                                "gmrp": float(tot_gross_mrp_b),
                                                "tcost": float(tot_cost_b),
                                                "dpct": float(curr_disc_pct),
                                                "damt": float(tot_disc_amt_b),
                                                "famt": float(tot_net_b),
                                                "adv": float(advance_paid_inp or 0.0),
                                                "bal": float(balance_due_calc),
                                                "st": order_status_inp,
                                                "notes": notes_inp.strip() or None,
                                            },
                                        )
                                        saved_id = int(ins_q.scalar())
                                    s.commit()
                                st.session_state["bulk_editing_id"] = saved_id
                                st.cache_data.clear()
                                st.session_state["_bulk_save_banner"] = f"{doc_type_sel.title()} #{saved_id} ({current_q_payload['quote_number']}) saved to database!"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Could not save {doc_type_sel.lower()} to database (ensure SQL migration has been run): {e}")

                with act2:
                    pdf_bytes = generate_bulk_quote_pdf_bytes(current_q_payload)
                    if pdf_bytes:
                        clean_fn = re.sub(r"[^A-Za-z0-9_-]", "_", f"{doc_type_sel}_{current_q_payload['quote_number']}_{cust_name_inp.strip() or 'Customer'}") + ".pdf"
                        st.download_button(
                            label=f"📄 Download {doc_type_sel.title()} PDF",
                            data=pdf_bytes,
                            file_name=clean_fn,
                            mime="application/pdf",
                            use_container_width=True,
                            key="dl_bulk_pdf_builder",
                        )
                    else:
                        st.button("📄 PDF Unavailable (ReportLab missing)", disabled=True, use_container_width=True)

                with act3:
                    wa_text = build_bulk_whatsapp_text(current_q_payload)
                    clean_phone = re.sub(r"[^0-9]", "", str(cust_phone_inp or ""))
                    if len(clean_phone) == 10:
                        clean_phone = "91" + clean_phone
                    wa_url = f"https://wa.me/{clean_phone}?text={quote(wa_text)}" if clean_phone else f"https://wa.me/?text={quote(wa_text)}"
                    st.link_button(f"📲 Send {doc_type_sel.title()} on WhatsApp", wa_url, use_container_width=True)

                with act4:
                    if doc_type_sel == "ESTIMATE":
                        if st.button("🧾 Convert to Invoice Mode", use_container_width=True, key="btn_switch_to_inv"):
                            st.session_state["bulk_doc_type"] = "INVOICE"
                            old_qno = str(st.session_state.get("bulk_quote_no", ""))
                            st.session_state["bulk_quote_no"] = old_qno.replace("EST-", "INV-") if old_qno.startswith("EST-") else f"INV-{date.today().strftime('%Y%m%d')}-{datetime.now().strftime('%H%M')}"
                            st.session_state["bulk_status_sel"] = "Invoiced / Delivered"
                            st.rerun()
                    else:
                        if st.button("📝 Switch to Estimate Mode", use_container_width=True, key="btn_switch_to_est"):
                            st.session_state["bulk_doc_type"] = "ESTIMATE"
                            st.rerun()

        with bulk_tab2:
            st.markdown("#### 🗂️ Saved Bulk Order Estimates & Invoices")
            pass

            hf1, hf2, hf3 = st.columns([1.2, 1.2, 1.2])
            with hf1:
                hist_type_filter = st.selectbox("Filter by Document Type", ["All", "ESTIMATE", "INVOICE"], key="bulk_hist_type_f")
            with hf2:
                hist_status_filter = st.selectbox("Filter by Status", ["All", "Estimate Sent", "Draft", "Confirmed", "Invoiced / Delivered", "Cancelled"], key="bulk_hist_status_f")
            with hf3:
                if st.button("↻ Refresh History", use_container_width=True, key="btn_refresh_bulk_hist"):
                    st.cache_data.clear()
                    st.rerun()

            try:
                b_where = ["(:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)"]
                b_params = {"active_loc": get_active_location_filter()}
                if hist_type_filter != "All":
                    b_where.append("UPPER(TRIM(doc_type)) = :dtype")
                    b_params["dtype"] = hist_type_filter
                if hist_status_filter != "All":
                    b_where.append("status = :st")
                    b_params["st"] = hist_status_filter
                b_where_sql = " AND ".join(b_where)

                quotes_df = db_conn.query(
                    f"""
                    SELECT *
                    FROM public.bulk_order_quotes
                    WHERE {b_where_sql}
                    ORDER BY quote_date DESC, id DESC
                    LIMIT 100;
                    """,
                    params=b_params,
                    ttl="60s",
                )
            except Exception as e:
                quotes_df = pd.DataFrame()
                st.info(f"Bulk orders table not initialized yet or empty. Run `bulk_orders_and_cart_return_migration.sql` in Supabase. ({e})")

            if quotes_df.empty:
                st.caption("No saved bulk order estimates or invoices found matching the selected filters.")
            else:
                for _, qrow in quotes_df.iterrows():
                    qid = int(qrow["id"])
                    q_dtype = str(qrow.get("doc_type") or "ESTIMATE").upper()
                    q_no = str(qrow.get("quote_number") or f"#{qid}")
                    q_cname = str(qrow.get("customer_name") or "Customer")
                    q_cphone = str(qrow.get("customer_phone") or "")
                    q_dt_str = pd.to_datetime(qrow["quote_date"]).strftime("%d-%b-%Y") if pd.notna(qrow.get("quote_date")) else "—"
                    ev_dt_str = pd.to_datetime(qrow["event_date"]).strftime("%d-%b-%Y") if pd.notna(qrow.get("event_date")) else "—"
                    q_tot_u = int(qrow.get("total_units") or 0)
                    q_gmrp = float(qrow.get("gross_mrp_amount") or 0.0)
                    q_tcost = float(qrow.get("total_cost_amount") or 0.0)
                    q_dpct = float(qrow.get("discount_pct") or 0.0)
                    q_damt = float(qrow.get("discount_amount") or 0.0)
                    q_famt = float(qrow.get("final_amount") or 0.0)
                    q_adv = float(qrow.get("advance_paid") or 0.0)
                    q_bal = float(qrow.get("balance_due") or max(0.0, q_famt - q_adv))
                    q_stat = str(qrow.get("status") or "—")
                    q_profit = q_famt - q_tcost

                    row_qty_map = {c: int(qrow.get(FLAVOR_MAP[c]["audit_col"], 0) or 0) for c in FLAVOR_CODES}
                    flv_chips = " • ".join([f"{c}: {row_qty_map[c]}" for c in FLAVOR_CODES if row_qty_map[c] > 0])

                    badge_bg = "#ECFDF5" if q_dtype == "INVOICE" else "#EFF6FF"
                    badge_fg = "#047857" if q_dtype == "INVOICE" else "#B45309"

                    with st.container(border=True):
                        hc1, hc2, hc3 = st.columns([2.4, 1.8, 2.2])
                        with hc1:
                            st.markdown(
                                f"<span style='background:{badge_bg};color:{badge_fg};padding:2px 8px;border-radius:999px;font-size:10.5px;font-weight:900;'>{q_dtype}</span> "
                                f"&nbsp;<b style='font-size:15px;color:#1E2252;'>{escape(q_cname)}</b> &nbsp;<span style='color:#2563EB;font-size:12px;'>({escape(q_no)})</span>",
                                unsafe_allow_html=True,
                            )
                            st.caption(f"📅 Quote Date: **{q_dt_str}** | 🎉 Event/Delivery: **{ev_dt_str}** | 📞 {q_cphone or '—'} | Status: **{q_stat}**")
                            st.markdown(f"<div style='font-size:12px;color:#047857;font-weight:700;'>🍦 {flv_chips or '—'}</div>", unsafe_allow_html=True)
                        with hc2:
                            st.markdown(
                                f"""
                                <div style='background:#F8FAFC;border:1px solid #CBD5E1;border-radius:8px;padding:6px 10px;font-size:12px;'>
                                    <div><b>Total Qty:</b> {q_tot_u:,} pcs &nbsp;|&nbsp; <b>Gross MRP:</b> ₹{q_gmrp:,.0f}</div>
                                    <div><b>Discount ({q_dpct:.1f}%):</b> -₹{q_damt:,.0f} &nbsp;|&nbsp; <b style='color:#047857;'>Net: ₹{q_famt:,.0f}</b></div>
                                    <div style='color:#475569;font-size:11px;'>CP: ₹{q_tcost:,.0f} • Profit: <b style='color:{"#047857" if q_profit>=0 else "#C43D17"};'>₹{q_profit:,.0f}</b> • Bal Due: <b>₹{q_bal:,.0f}</b></div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with hc3:
                            b_col1, b_col2, b_col3, b_col4 = st.columns(4, gap="small")
                            with b_col1:
                                if st.button("✏️ Edit", key=f"edit_bq_{qid}", use_container_width=True):
                                    st.session_state["bulk_editing_id"] = qid
                                    st.session_state["bulk_doc_type"] = q_dtype
                                    st.session_state["bulk_quote_no"] = q_no
                                    st.session_state["bulk_cust_name"] = q_cname
                                    st.session_state["bulk_cust_phone"] = q_cphone
                                    st.session_state["bulk_cust_addr"] = str(qrow.get("customer_address") or "")
                                    st.session_state["bulk_discount_pct"] = float(q_dpct)
                                    st.session_state["bulk_advance_paid"] = float(q_adv)
                                    st.session_state["bulk_notes"] = str(qrow.get("notes") or "")
                                    for c in FLAVOR_CODES:
                                        q_v = int(row_qty_map.get(c, 0))
                                        st.session_state[f"bulk_qty_{c}"] = q_v
                                        st.session_state[f"bulk_chk_{c}"] = (q_v > 0)
                                    st.rerun()
                            with b_col2:
                                if st.button("🧾 To Inv", key=f"conv_bq_{qid}", use_container_width=True, help="Load into builder as an Invoice to edit delivered quantities"):
                                    st.session_state["bulk_editing_id"] = qid
                                    st.session_state["bulk_doc_type"] = "INVOICE"
                                    st.session_state["bulk_quote_no"] = q_no.replace("EST-", "INV-") if q_no.startswith("EST-") else f"INV-{q_no}"
                                    st.session_state["bulk_cust_name"] = q_cname
                                    st.session_state["bulk_cust_phone"] = q_cphone
                                    st.session_state["bulk_cust_addr"] = str(qrow.get("customer_address") or "")
                                    st.session_state["bulk_discount_pct"] = float(q_dpct)
                                    st.session_state["bulk_advance_paid"] = float(q_adv)
                                    st.session_state["bulk_status_sel"] = "Invoiced / Delivered"
                                    st.session_state["bulk_notes"] = str(qrow.get("notes") or "")
                                    for c in FLAVOR_CODES:
                                        q_v = int(row_qty_map.get(c, 0))
                                        st.session_state[f"bulk_qty_{c}"] = q_v
                                        st.session_state[f"bulk_chk_{c}"] = (q_v > 0)
                                    st.rerun()
                            with b_col3:
                                row_pdf_payload = {
                                    "doc_type": q_dtype,
                                    "quote_number": q_no,
                                    "quote_date": q_dt_str,
                                    "event_date": ev_dt_str,
                                    "location": str(qrow.get("location") or CITY),
                                    "customer_name": q_cname,
                                    "customer_phone": q_cphone,
                                    "customer_address": str(qrow.get("customer_address") or ""),
                                    "qty_map": row_qty_map,
                                    "total_units": q_tot_u,
                                    "gross_mrp_amount": q_gmrp,
                                    "total_cost_amount": q_tcost,
                                    "discount_pct": q_dpct,
                                    "discount_amount": q_damt,
                                    "final_amount": q_famt,
                                    "advance_paid": q_adv,
                                    "balance_due": q_bal,
                                    "status": q_stat,
                                    "notes": str(qrow.get("notes") or ""),
                                }
                                row_pdf_bytes = generate_bulk_quote_pdf_bytes(row_pdf_payload)
                                if row_pdf_bytes:
                                    st.download_button(
                                        "📄 PDF",
                                        data=row_pdf_bytes,
                                        file_name=f"{q_dtype}_{q_no}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_bq_pdf_{qid}",
                                        use_container_width=True,
                                    )
                            with b_col4:
                                if st.button("🗑️ Del", key=f"del_bq_{qid}", use_container_width=True):
                                    with db_conn.session as s:
                                        s.execute(text("DELETE FROM public.bulk_order_quotes WHERE id = :id;"), {"id": qid})
                                        s.commit()
                                    if st.session_state.get("bulk_editing_id") == qid:
                                        st.session_state["bulk_editing_id"] = None
                                    st.cache_data.clear()
                                    st.rerun()

    elif page == "Payslip Generator" and user_role == "admin":
        p_h_col1, p_h_col2 = st.columns([1, 6])
        with p_h_col1:
            if os.path.exists("assets/logo.png"): st.image("assets/logo.png", width=90)
        with p_h_col2:
            st.subheader("Staff Payslip Generator & Detailed Ledger")
            pass

        staff_df = load_full_staff_df()
        if staff_df.empty: st.info("No staff records found in the database.")
        else:
            pc1, pc2 = st.columns([1.4, 1])
            with pc1:
                sel_staff_payslip = st.selectbox("Select Staff Member", staff_df["name"].tolist(), key="payslip_staff_sel")
            with pc2:
                payslip_filter_mode = st.radio(
                    "Filter By",
                    ["Month", "Custom Date Range"],
                    horizontal=True,
                    key="payslip_filter_mode"
                )

            today_payslip = date.today()
            if payslip_filter_mode == "Month":
                pdc1, pdc2 = st.columns(2)
                payslip_month_names = list(calendar.month_name)[1:]
                with pdc1:
                    payslip_month_name = st.selectbox(
                        "Month",
                        payslip_month_names,
                        index=today_payslip.month - 1,
                        key="payslip_month"
                    )
                    payslip_month_num = payslip_month_names.index(payslip_month_name) + 1
                with pdc2:
                    payslip_year = st.number_input(
                        "Year",
                        min_value=2024,
                        max_value=2035,
                        value=today_payslip.year,
                        step=1,
                        key="payslip_year"
                    )
                payslip_start = date(int(payslip_year), int(payslip_month_num), 1)
                payslip_end = date(
                    int(payslip_year),
                    int(payslip_month_num),
                    calendar.monthrange(int(payslip_year), int(payslip_month_num))[1]
                )
            else:
                pdc1, pdc2 = st.columns(2)
                with pdc1:
                    payslip_start = st.date_input(
                        "Start Date",
                        value=today_payslip.replace(day=1),
                        key="payslip_start_dt",
                        format="DD-MM-YYYY"
                    )
                with pdc2:
                    payslip_end = st.date_input(
                        "End Date",
                        value=today_payslip,
                        key="payslip_end_dt",
                        format="DD-MM-YYYY"
                    )

            if payslip_start > payslip_end: st.error("Start date must be before or equal to end date.")
            else:
                _, _, _, breakdown_dict = calculate_incurred_labour_for_range(payslip_start, payslip_end, include_cash_leakage=True)
                selected_staff_row = staff_df[staff_df["name"] == sel_staff_payslip].iloc[0]
                selected_role = str(selected_staff_row.get("role") or "Cart Operator")
                staff_data = breakdown_dict.get(sel_staff_payslip, {
                    "monthly_fixed_salary": 18000.0, "days_worked": 0, "paid_leaves": 0, "unpaid_leaves": 0, "payable_days": 0, "salary": 0.0,
                    "commissions": 0.0, "food_tea_allowance_mode": "monthly", "allowance_weekday": 0.0, "allowance_sunday": 0.0,
                    "monthly_food_tea_allowance": 0.0, "monthly_fuel_allowance": 0.0,
                    "food_tea_allowance": 0.0, "fuel_allowance": 0.0, "allowances": 0.0,
                    "incurred": 0.0, "paid": 0.0, "due": 0.0, "detailed_ledger": [],
                    "doj": selected_staff_row.get("date_of_joining"), "role": selected_role
                })

                role = str(staff_data.get("role") or selected_role)
                is_ops_coordinator = role.strip().lower() == "ops coordinator"
                is_cart_operator = role.strip().lower() == "cart operator"
                doj_val = staff_data.get('doj')
                doj_str = pd.to_datetime(doj_val).strftime('%d-%b-%y') if pd.notna(doj_val) and str(doj_val).strip() else "N/A"

                # Show Last Working Day on the payslip only when it falls within
                # the selected payslip period.
                dol_val = selected_staff_row.get("date_of_leaving")
                dol_date = None
                if pd.notna(dol_val) and str(dol_val).strip():
                    try:
                        dol_date = pd.to_datetime(dol_val).date()
                    except Exception:
                        dol_date = None
                show_last_working_day = dol_date is not None and payslip_start <= dol_date <= payslip_end
                dol_str = dol_date.strftime('%d-%b-%y') if show_last_working_day else None

                month_str = payslip_start.strftime('%B %Y') if payslip_filter_mode == "Month" else f"{payslip_start.strftime('%d-%b-%y')} to {payslip_end.strftime('%d-%b-%y')}"
                payable_days = int(staff_data.get("payable_days", staff_data.get("days_worked", 0) + staff_data.get("paid_leaves", 0)))

                adjustment_key = f"{int(selected_staff_row['id'])}_{payslip_start.strftime('%Y%m%d')}_{payslip_end.strftime('%Y%m%d')}"
                adj_c1, adj_c2 = st.columns([1, 2])
                with adj_c1:
                    adjustment_amount = st.number_input(
                        "Manual Adjustment (₹)",
                        value=0.0,
                        step=100.0,
                        format="%.2f",
                        key=f"payslip_adjustment_{adjustment_key}",
                        help="Use a positive amount to add to payable or a negative amount to reduce it."
                    )
                adjustment_reason = ""
                with adj_c2:
                    if abs(float(adjustment_amount)) > 0.0001:
                        adjustment_reason = st.text_input(
                            "Adjustment Reason / Remarks *",
                            key=f"payslip_adjustment_reason_{adjustment_key}",
                            placeholder="Explain the reason for this manual adjustment"
                        )
                    else:
                        st.text_input(
                            "Adjustment Reason / Remarks",
                            value="",
                            disabled=True,
                            key=f"payslip_adjustment_reason_disabled_{adjustment_key}",
                            placeholder="Enabled when an adjustment amount is entered"
                        )

                has_adjustment = abs(float(adjustment_amount)) > 0.0001
                final_payable_adjusted = float(staff_data.get("due", 0.0)) + float(adjustment_amount)
                staff_data = dict(staff_data)
                # Preserve Last Working Day for the PDF header as well.
                staff_data["dol"] = dol_val
                staff_data["adjustment_amount"] = float(adjustment_amount)
                staff_data["adjustment_reason"] = adjustment_reason.strip()
                staff_data["final_payable_adjusted"] = final_payable_adjusted

                if has_adjustment and not adjustment_reason.strip():
                    st.warning("Adjustment Reason / Remarks is mandatory when a manual adjustment is entered.")

                st.markdown("---")
                st.markdown(f"#### Salary Statement Summary — {sel_staff_payslip}")
                period_label = "Payslip Month" if payslip_filter_mode == "Month" else "Payslip Period"
                employment_header = f"**Role:** {role} &nbsp;|&nbsp; **Date of Joining:** {doj_str}"
                if show_last_working_day:
                    employment_header += f" &nbsp;|&nbsp; **Last Working Day:** {dol_str}"
                employment_header += f" &nbsp;|&nbsp; **{period_label}:** {month_str}"
                st.markdown(employment_header)

                unpaid_leaves = int(staff_data.get("unpaid_leaves", 0))
                if is_ops_coordinator:
                    day_row = ["Total Days Worked", f"{staff_data['days_worked']} Days Worked + {staff_data['paid_leaves']} Paid Leaves, {unpaid_leaves} Unpaid Leaves", f"{payable_days} payable days"]
                    salary_basis = f"Monthly salary pro-rata for {payable_days} payable calendar days"
                else:
                    day_row = ["Total Days Worked", f"{staff_data['days_worked']} Days Worked + {staff_data['paid_leaves']} Paid Leaves, {unpaid_leaves} Unpaid Leaves", f"{staff_data['days_worked'] + staff_data['paid_leaves']} days"]
                    salary_basis = f"({staff_data['days_worked']} + {staff_data['paid_leaves']}) days @ ₹{staff_data.get('daily_rate', 600):.2f}/day"

                food_mode = str(staff_data.get("food_tea_allowance_mode") or "monthly").strip().lower()
                if food_mode == "daily":
                    food_component = "Food & Tea Allowance (Daily Plan)"
                    food_basis = f"Weekday ₹{staff_data.get('allowance_weekday', 0):,.2f}/day | Sunday ₹{staff_data.get('allowance_sunday', 0):,.2f}/day; based on days worked"
                else:
                    food_component = "Food & Tea Allowance (Monthly Plan)"
                    food_basis = f"Plan ₹{staff_data.get('monthly_food_tea_allowance', 0):,.2f}/month; pro-rata for days worked"

                summary_table_data = [
                    ["Salary Component", "Basis / Calculation Details", "Amount (₹)"],
                    ["Monthly Fixed Salary", "Standard Monthly Base Plan", f"₹{staff_data['monthly_fixed_salary']:,.2f}"],
                    day_row,
                    ["Pro-rata Fixed Salary", salary_basis, f"₹{staff_data['salary']:,.2f}"],
                ]
                if not is_ops_coordinator:
                    summary_table_data.append(["Sales Commissions", "Commission on qualifying daily collections", f"₹{staff_data['commissions']:,.2f}"])
                # Daily Food/Tea remains visible in the payslip. Monthly Food/Tea is
                # monitored separately under Staff & Payroll -> Monthly Food Allowance.
                if food_mode == "daily":
                    summary_table_data.append([food_component, food_basis, f"₹{staff_data.get('food_tea_allowance', 0):,.2f}"])
                if food_mode == "monthly" and is_ops_coordinator:
                    gross_basis = "Pro-rata fixed salary + pro-rata Fuel allowance"
                elif food_mode == "monthly":
                    gross_basis = "Pro-rata fixed salary + commission (where applicable)"
                elif is_cart_operator:
                    gross_basis = "Pro-rata fixed salary + commission + daily Food/Tea allowance"
                else:
                    gross_basis = "Pro-rata fixed salary + commission (where applicable) + daily Food/Tea + Fuel"

                if (is_ops_coordinator or food_mode == "daily") and not is_cart_operator:
                    summary_table_data.append([
                        "Monthly Fuel Allowance",
                        f"Plan ₹{staff_data.get('monthly_fuel_allowance', 0):,.2f}/month; pro-rata for days worked",
                        f"₹{staff_data.get('fuel_allowance', 0):,.2f}"
                    ])

                summary_table_data.extend([
                    ["Gross Payable Earnings", gross_basis, f"₹{staff_data['incurred']:,.2f}"],
                    ["Already Paid / Disbursed", ("Advances paid already, unexplained leakages & penalties" if is_cart_operator else "Advances paid already & penalties"), f"-₹{staff_data['paid']:,.2f}"],
                    ["Calculated Final Payable", "Calculated amount before manual adjustment", f"₹{staff_data['due']:,.2f}"],
                    ["Manual Adjustment", adjustment_reason.strip() if adjustment_reason.strip() else "No adjustment entered", f"₹{float(adjustment_amount):+,.2f}" if abs(float(adjustment_amount)) > 0.0001 else "₹0.00"],
                    ["Final Payable (Adjusted)", "Calculated final payable amount post adjustments", f"₹{final_payable_adjusted:,.2f}"]
                ])

                summary_df = pd.DataFrame(summary_table_data[1:], columns=summary_table_data[0])

                def style_bold_rows(row):
                    if row["Salary Component"] in ["Gross Payable Earnings", "Calculated Final Payable", "Final Payable (Adjusted)"]:
                        return ["font-weight: bold;"] * len(row)
                    return [""] * len(row)

                summary_table_height = 38 + (len(summary_df) * 36)
                st.dataframe(
                    summary_df.style.apply(style_bold_rows, axis=1),
                    hide_index=True,
                    width="stretch",
                    height=summary_table_height
                )

                if not is_ops_coordinator:
                    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                    ledger_heading = "Detailed Commission & Allowance Entitlement Ledger" if food_mode == "daily" else "Detailed Commission & Salary Ledger"
                    st.markdown(f"#### {ledger_heading}")
                    pass

                    ledger_list = staff_data.get("detailed_ledger", [])
                    if ledger_list:
                        ledger_df = pd.DataFrame(ledger_list)
                        ledger_df["Date"] = pd.to_datetime(ledger_df["date"]).dt.strftime("%d-%b-%y")
                        ledger_df["Type"] = ledger_df["type"]
                        ledger_df["Cart"] = ledger_df["cart"]
                        ledger_df["Collection (₹)"] = ledger_df["collection"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                        ledger_df["Salary (₹)"] = ledger_df["fixed_salary"].apply(lambda v: f"₹{v:,.2f}")
                        ledger_df["Commission (₹)"] = ledger_df["commission"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                        ledger_df["Advance Taken (₹)"] = ledger_df["advance_taken"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                        ledger_df["Leakage"] = ledger_df["leakage"].fillna(0).apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—") if "leakage" in ledger_df else "—"

                        if food_mode == "daily":
                            ledger_df["Allowance (₹)"] = ledger_df["allowance"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                            ledger_df["Allow. Taken (₹)"] = ledger_df["food_taken"].apply(lambda v: f"₹{v:,.2f}" if v > 0 else "—")
                            display_cols = ["Date", "Type", "Cart", "Collection (₹)", "Salary (₹)", "Commission (₹)", "Allowance (₹)", "Advance Taken (₹)", "Allow. Taken (₹)", "Leakage"]
                        else:
                            display_cols = ["Date", "Type", "Cart", "Collection (₹)", "Salary (₹)", "Commission (₹)", "Advance Taken (₹)", "Leakage"]

                        st.dataframe(
                            ledger_df[display_cols],
                            hide_index=True,
                            use_container_width=True,
                            column_config={col: st.column_config.TextColumn(width="small") for col in display_cols}
                        )
                    else:
                        st.info("No active days or leave records found within the selected date range.")

                st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

                if REPORTLAB_AVAILABLE:
                    pdf_bytes = None
                    if (not has_adjustment) or adjustment_reason.strip():
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
        st.subheader("Live Cart Operations & Flavour Sales")
        st.caption("Live cart shifts & flavour-wise POS sales")

        render_live_cart_flavour_tables_section(key_prefix="admin_live_trk")

        active_loc_live = get_active_location_filter()

        st.markdown("---")
        st.markdown("#### 🛒 Today's Cart Shifts")

        active_shifts_df = db_conn.query("""
            SELECT
                s.id,
                s.cart_name,
                s.staff_name,
                s.started_at,
                s.closed_at,
                s.status,

                COALESCE(SUM(t.total_amount), 0) AS gross_sales,
                COALESCE(SUM(t.cash_amount), 0) AS total_cash,
                COALESCE(SUM(t.phonepe_amount), 0) AS total_phonepe,
                COUNT(t.id) AS transaction_count

            FROM live_cart_shifts s

            LEFT JOIN live_cart_transactions t
                ON s.id = t.shift_id
                AND t.created_at >= CURRENT_DATE

            WHERE s.shift_date = CURRENT_DATE
              AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc)

            GROUP BY
                s.id,
                s.cart_name,
                s.staff_name,
                s.started_at,
                s.closed_at,
                s.status

            ORDER BY s.started_at DESC;
        """, params={"active_loc": active_loc_live}, ttl="60s")

        summary_df = db_conn.query("""
            SELECT
                COALESCE(SUM(t.total_amount), 0) AS total_sales,
                COALESCE(SUM(t.cash_amount), 0) AS total_cash,
                COALESCE(SUM(t.phonepe_amount), 0) AS total_phonepe,
                COUNT(t.id) AS transaction_count
            FROM live_cart_transactions t
            JOIN live_cart_shifts s ON t.shift_id = s.id
            WHERE t.created_at >= CURRENT_DATE
              AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc);
        """, params={"active_loc": active_loc_live}, ttl="60s")

        active_count_df = db_conn.query("""
            SELECT COUNT(*) AS active_carts
            FROM live_cart_shifts s
            WHERE s.shift_date = CURRENT_DATE
              AND s.status = 'Open'
              AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(s.location, 'HOSUR'))) = :active_loc);
        """, params={"active_loc": active_loc_live}, ttl="60s")

        total_sales = 0.0
        total_cash = 0.0
        total_phonepe = 0.0
        transaction_count = 0
        active_carts = 0

        if not summary_df.empty:
            total_sales = float(summary_df.iloc[0]["total_sales"] or 0)
            total_cash = float(summary_df.iloc[0]["total_cash"] or 0)
            total_phonepe = float(summary_df.iloc[0]["total_phonepe"] or 0)
            transaction_count = int(summary_df.iloc[0]["transaction_count"] or 0)

        if not active_count_df.empty:
            active_carts = int(active_count_df.iloc[0]["active_carts"] or 0)

        # ------------------------------------------------------------------
        # LIVE SUMMARY CARDS
        # ------------------------------------------------------------------
        m1, m2, m3, m4, m5 = st.columns(5)

        m1.metric(
            "Live Sales Today",
            f"₹{total_sales:,.2f}"
        )

        m2.metric(
            "Cash",
            f"₹{total_cash:,.2f}"
        )

        m3.metric(
            "PhonePe",
            f"₹{total_phonepe:,.2f}"
        )

        m4.metric(
            "Transactions",
            transaction_count
        )

        m5.metric(
            "Active Carts",
            active_carts
        )

        st.markdown("---")

        # ------------------------------------------------------------------
        # SHIFT DETAILS
        # ------------------------------------------------------------------
        if active_shifts_df.empty:
            st.info("No cart shifts recorded today yet.")
        else:

            for _, shift in active_shifts_df.iterrows():

                # Mobile App.js uses:
                #   Open   = active
                #   Closed = closed
                is_open = str(shift["status"]).strip().lower() == "open"

                status_color = "🟢" if is_open else "🔴"

                status_text = "OPEN" if is_open else "CLOSED"

                started_at = shift["started_at"]

                if pd.notna(started_at):
                    try:
                        started_display = pd.to_datetime(
                            started_at
                        ).strftime("%I:%M %p")
                    except Exception:
                        started_display = str(started_at)
                else:
                    started_display = "—"

                with st.container(border=True):

                    st.markdown(
                        f"#### {status_color} "
                        f"{shift['cart_name']} "
                        f"&nbsp;|&nbsp; Staff: {shift['staff_name']} "
                        f"&nbsp;|&nbsp; Status: {status_text}"
                    )

                    st.caption(
                        f"Shift started: {started_display}"
                    )

                    c1, c2, c3, c4 = st.columns(4)

                    c1.metric(
                        "Gross Live Sales",
                        f"₹{float(shift['gross_sales'] or 0):,.2f}"
                    )

                    c2.metric(
                        "Total PhonePe",
                        f"₹{float(shift['total_phonepe'] or 0):,.2f}"
                    )

                    c3.metric(
                        "Total Cash",
                        f"₹{float(shift['total_cash'] or 0):,.2f}"
                    )

                    c4.metric(
                        "Transactions Today",
                        int(shift["transaction_count"] or 0)
                    )

                    # ------------------------------------------------------
                    # FLAVOUR BREAKDOWN
                    #
                    # Same underlying tables as App.js:
                    # live_transaction_items
                    #   -> live_cart_transactions
                    #   -> flavors
                    # ------------------------------------------------------
                    items_df = db_conn.query("""
                        SELECT
                            f.name AS flavor_name,
                            SUM(i.quantity) AS qty_sold,
                            SUM(i.subtotal) AS rev

                        FROM live_transaction_items i

                        JOIN live_cart_transactions t
                            ON i.transaction_id = t.id

                        JOIN flavors f
                            ON i.flavor_code = f.code

                        WHERE t.shift_id = :sid
                          AND t.created_at >= CURRENT_DATE

                        GROUP BY f.name

                        ORDER BY qty_sold DESC;
                    """,
                    params={
                        "sid": int(shift["id"])
                    },
                    ttl="60s")

                    if not items_df.empty:

                        with st.expander(
                            "View Flavour Breakdown"
                        ):

                            display_items_df = items_df.rename(
                                columns={
                                    "flavor_name": "Flavour",
                                    "qty_sold": "Units Sold",
                                    "rev": "Revenue (₹)"
                                }
                            ).copy()

                            display_items_df["Revenue (₹)"] = (
                                display_items_df["Revenue (₹)"]
                                .astype(float)
                                .map(lambda x: f"₹{x:,.2f}")
                            )

                            st.dataframe(
                                display_items_df,
                                hide_index=True,
                                use_container_width=True
                            )


    # ======================================================================
    # PAGE: CASH CUSTODY (Admin View)
    # ======================================================================
    elif page == "Cash Custody" and user_role == "admin":
        if db_conn is None:
            st.error("Database connection is unavailable.")
            st.stop()

        active_loc = get_active_location_filter()
        write_loc = get_default_write_city()

        # Scoped Deposito styling for Cash Custody (no unisolated :has() rules)
        st.markdown(
            """
            <style>
            .cc-card {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
                padding: 16px 18px;
                box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
                margin-bottom: 12px;
            }
            .cc-card-selected {
                background: #F8FAFC;
                border: 1.5px solid #2563EB;
                border-radius: 14px;
                padding: 16px 18px;
                box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
                margin-bottom: 12px;
            }
            .cc-eyebrow {
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: #64748B;
                margin-bottom: 6px;
            }
            .cc-big-num {
                font-size: 26px;
                font-weight: 800;
                color: #1E2252;
                line-height: 1.15;
            }
            .cc-kpi-row {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 10px;
                margin-top: 10px;
            }
            .cc-kpi-tile {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                padding: 10px 12px;
            }
            .cc-kpi-tile.amber { background: #FFFBEB; border-color: #FDE68A; }
            .cc-kpi-tile.blue { background: #EFF6FF; border-color: #BFDBFE; }
            .cc-kpi-tile.green { background: #ECFDF5; border-color: #A7F3D0; }
            .cc-kpi-tile.red { background: #FEF2F2; border-color: #FECACA; }
            .cc-kpi-lbl {
                font-size: 10.5px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: #64748B;
                margin-bottom: 3px;
            }
            .cc-kpi-val {
                font-size: 16px;
                font-weight: 800;
                color: #0F172A;
            }
            .cc-kpi-sub {
                font-size: 11px;
                color: #64748B;
                margin-top: 2px;
            }
            .cc-table-wrap {
                background: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
                margin-bottom: 12px;
            }
            .cc-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 13px;
            }
            .cc-table th {
                background: #F8FAFC;
                color: #475569;
                font-size: 11px;
                font-weight: 800;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                padding: 10px 14px;
                border-bottom: 1px solid #E2E8F0;
                text-align: left;
            }
            .cc-table th.num, .cc-table td.num { text-align: right; }
            .cc-table td {
                padding: 9px 14px;
                border-bottom: 1px solid #F1F5F9;
                color: #1E293B;
                font-weight: 500;
            }
            .cc-table tr.cc-total-row td {
                background: #F8FAFC;
                font-weight: 800;
                color: #1E2252;
                border-top: 1.5px solid #CBD5E1;
                border-bottom: none;
            }
            .cc-table th.cc-col-gross {
                background: #EFF6FF;
                color: #1E40AF;
                border-left: 1px solid #DBEAFE;
            }
            .cc-table td.cc-col-gross {
                background: #F8FBFF;
                color: #1E3A8A;
                font-weight: 600;
                border-left: 1px solid #E2E8F0;
            }
            .cc-table tr.cc-total-row td.cc-col-gross {
                background: #EFF6FF;
                color: #1E3A8A;
            }
            .cc-table th.cc-col-spent {
                background: #FEF2F2;
                color: #B91C1C;
                border-left: 1px solid #FECACA;
            }
            .cc-table td.cc-col-spent {
                background: #FFF7F7;
                color: #C43D17;
                font-weight: 700;
                border-left: 1px solid #FEE2E2;
            }
            .cc-table td.cc-col-spent-zero {
                background: #FFFBFB;
                color: #94A3B8;
                font-weight: 600;
                border-left: 1px solid #FEE2E2;
            }
            .cc-table tr.cc-total-row td.cc-col-spent {
                background: #FEE2E2;
                color: #B91C1C;
            }
            .cc-table th.cc-col-net {
                background: #D1FAE5;
                color: #065F46;
                border-left: 2px solid #6EE7B7;
            }
            .cc-table td.cc-col-net {
                background: #ECFDF5;
                color: #047857;
                font-weight: 800;
                border-left: 2px solid #6EE7B7;
            }
            .cc-table tr.cc-total-row td.cc-col-net {
                background: #D1FAE5;
                color: #065F46;
                font-size: 14px;
                font-weight: 900;
                border-left: 2px solid #34D399;
            }
            .cc-banner-net {
                background: linear-gradient(90deg, #EFF6FF 0%, #F8FAFC 100%);
                border: 1px solid #BFDBFE;
                border-left: 4px solid #2563EB;
                border-radius: 10px;
                padding: 10px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            }
            .cc-sec-hdr {
                font-size: 16px;
                font-weight: 800;
                color: #1E2252;
                margin: 14px 0 6px 0;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .cc-pill {
                display: inline-block;
                border-radius: 999px;
                padding: 2px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            .cc-pill.amber { background: #FFFBEB; color: #B45309; border: 1px solid #FDE68A; }
            .cc-pill.blue { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
            .cc-pill.green { background: #ECFDF5; color: #047857; border: 1px solid #A7F3D0; }
            .cc-pill.red { background: #FEF2F2; color: #B91C1C; border: 1px solid #FECACA; }
            .cc-note-box {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 12px;
                color: #475569;
                margin-top: 8px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # ------------------------------------------------------------------
        # 1. DATA QUERIES (Exact Mobile App.js Parity, Location-Filtered)
        # ------------------------------------------------------------------
        try:
            custody_rows_df = db_conn.query(
                """
                SELECT
                    daily_entry_id,
                    entry_date,
                    cart_name,
                    city,
                    cash_amount,
                    current_holder,
                    batch_id,
                    collection_date,
                    expected_amount,
                    actual_collected_amount,
                    batch_status
                FROM public.v_cash_custody_status
                WHERE current_holder IN ('OPS_COORDINATOR', 'YOGESH')
                  AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                ORDER BY entry_date DESC, cart_name ASC;
                """,
                params={"active_loc": active_loc},
                ttl="60s",
            )

            summary_df = db_conn.query(
                """
                SELECT
                    current_holder,
                    COUNT(*) AS daily_entry_count,
                    COALESCE(SUM(cash_amount), 0) AS total_cash
                FROM public.v_cash_custody_status
                WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                GROUP BY current_holder;
                """,
                params={"active_loc": active_loc},
                ttl="60s",
            )

            spends_df = db_conn.query(
                """
                SELECT
                    id,
                    spend_date,
                    amount,
                    COALESCE(allocated_amount, 0) AS allocated_amount,
                    notes,
                    batch_id,
                    location,
                    COALESCE(spent_by, 'OPS_COORDINATOR') AS spent_by,
                    created_at,
                    updated_at
                FROM public.cash_ops_spend_entries
                WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
                ORDER BY spend_date DESC, id DESC
                LIMIT 100;
                """,
                params={"active_loc": active_loc},
                ttl="60s",
            )

            tagged_exp_df = db_conn.query(
                """
                SELECT id, category, sub_category, total_amount, remarks
                FROM public.expenses
                WHERE remarks ILIKE '%[Ops Cash Spend #%'
                   OR remarks ILIKE '%[Admin 1 Cash Spend #%'
                ORDER BY id DESC;
                """,
                ttl="60s",
            )

            recent_batches_df = db_conn.query(
                """
                SELECT
                    id,
                    collection_date,
                    expected_amount,
                    actual_collected_amount,
                    status,
                    handed_over_date,
                    handed_over_to,
                    notes,
                    COALESCE(cash_spent_amount, 0) AS cash_spent_amount,
                    cash_spent_notes,
                    COALESCE(admin1_spent_amount, 0) AS admin1_spent_amount,
                    admin1_spent_notes
                FROM public.cash_handover_batches
                WHERE status = 'HANDED_TO_SRILALITHA'
                  AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
                ORDER BY handed_over_date DESC NULLS LAST, id DESC
                LIMIT 10;
                """,
                params={"active_loc": active_loc},
                ttl="60s",
            )
        except Exception as e:
            st.error(f"Could not load Cash Custody data: {e}")
            st.stop()

        # Summary totals by holder
        summary_by_holder = {"OPS_COORDINATOR": 0.0, "YOGESH": 0.0, "SRILALITHA": 0.0}
        if not summary_df.empty:
            for _, r in summary_df.iterrows():
                h = str(r["current_holder"] or "").strip().upper()
                if h in summary_by_holder:
                    summary_by_holder[h] = float(r["total_cash"] or 0.0)
        total_with_srilalitha = summary_by_holder["SRILALITHA"]

        # Tagged expenses map: spend_id -> {id, category, sub_category, total_amount}
        tagged_expense_map = {}
        if not tagged_exp_df.empty:
            _tag_re = re.compile(r"\[(?:Ops|Admin 1) Cash Spend #(\d+)\]", re.IGNORECASE)
            for _, r in tagged_exp_df.iterrows():
                m = _tag_re.search(str(r.get("remarks") or ""))
                if m:
                    sid_key = int(m.group(1))
                    if sid_key not in tagged_expense_map:
                        tagged_expense_map[sid_key] = {
                            "id": int(r["id"]),
                            "category": r.get("category") or "",
                            "sub_category": r.get("sub_category") or "",
                            "total_amount": float(r.get("total_amount") or 0.0),
                        }

        # Normalize spend entries
        all_spends = []
        spend_list = []              # OPS_COORDINATOR, batch_id IS NULL, remaining > 0.001
        admin1_remaining_spends = [] # ADMIN_1, remaining > 0.001
        if not spends_df.empty:
            for _, r in spends_df.iterrows():
                amt = float(r.get("amount") or 0.0)
                alloc = float(r.get("allocated_amount") or 0.0)
                rem = max(0.0, round(amt - alloc, 2))
                sb = str(r.get("spent_by") or "OPS_COORDINATOR").strip().upper()
                bid = None if pd.isna(r.get("batch_id")) else int(r.get("batch_id"))
                item = {
                    "id": int(r["id"]),
                    "spend_date": r.get("spend_date"),
                    "amount": amt,
                    "allocated_amount": alloc,
                    "remaining_amount": rem,
                    "notes": str(r.get("notes") or "").strip(),
                    "batch_id": bid,
                    "location": str(r.get("location") or write_loc),
                    "spent_by": sb,
                }
                all_spends.append(item)
                if sb == "OPS_COORDINATOR" and bid is None and rem > 0.001:
                    spend_list.append(item)
                elif sb == "ADMIN_1" and rem > 0.001:
                    admin1_remaining_spends.append(item)

        # Fetch batch metadata for all batch_ids present in custody_rows_df
        batch_ids_in_custody = []
        if not custody_rows_df.empty:
            batch_ids_in_custody = sorted({
                int(x) for x in custody_rows_df["batch_id"].dropna().tolist()
            })

        batch_meta_map = {}
        if batch_ids_in_custody:
            try:
                placeholders = ", ".join(str(int(b)) for b in batch_ids_in_custody)
                b_meta_df = db_conn.query(
                    f"""
                    SELECT
                        id,
                        collection_date,
                        expected_amount,
                        actual_collected_amount,
                        status,
                        handed_over_date,
                        handed_over_to,
                        notes,
                        COALESCE(cash_spent_amount, 0) AS cash_spent_amount,
                        cash_spent_notes,
                        COALESCE(admin1_spent_amount, 0) AS admin1_spent_amount,
                        admin1_spent_notes
                    FROM public.cash_handover_batches
                    WHERE id IN ({placeholders});
                    """,
                    ttl="60s",
                )
                for _, br in b_meta_df.iterrows():
                    batch_meta_map[int(br["id"])] = br.to_dict()
            except Exception as e:
                st.warning(f"Could not load batch metadata: {e}")

        # Attach sorted salesDates to recent confirmed batches
        recent_batches = []
        if not recent_batches_df.empty:
            rec_ids = [int(x) for x in recent_batches_df["id"].tolist()]
            rec_dates_map = {}
            if rec_ids:
                try:
                    rec_ph = ", ".join(str(int(b)) for b in rec_ids)
                    rec_items_df = db_conn.query(
                        f"""
                        SELECT batch_id, entry_date, cash_amount
                        FROM public.v_cash_custody_status
                        WHERE batch_id IN ({rec_ph});
                        """,
                        ttl="60s",
                    )
                    for _, rr in rec_items_df.iterrows():
                        rbid = int(rr["batch_id"])
                        dt_s = pd.to_datetime(rr["entry_date"]).strftime("%Y-%m-%d")
                        rec_dates_map.setdefault(rbid, set()).add(dt_s)
                except Exception:
                    pass
            for _, rb in recent_batches_df.iterrows():
                d = rb.to_dict()
                d["salesDates"] = sorted(rec_dates_map.get(int(d["id"]), set()))
                recent_batches.append(d)

        # ------------------------------------------------------------------
        # 2. GROUPING & TWO-PASS SPEND APPORTIONMENT (Exact App.js Logic)
        # ------------------------------------------------------------------
        grouped = {}
        if not custody_rows_df.empty:
            for _, row in custody_rows_df.iterrows():
                bid = None if pd.isna(row.get("batch_id")) else int(row.get("batch_id"))
                dt_iso = pd.to_datetime(row["entry_date"]).strftime("%Y-%m-%d")
                gkey = f"batch:{bid}" if bid is not None else f"date:{dt_iso}"
                holder = str(row.get("current_holder") or "OPS_COORDINATOR").strip().upper()
                amt = float(row.get("cash_amount") or 0.0)
                cart_nm = str(row.get("cart_name") or "").strip()
                de_id = int(row["daily_entry_id"]) if pd.notna(row.get("daily_entry_id")) else None

                if gkey not in grouped:
                    bm = batch_meta_map.get(bid, {}) if bid is not None else {}
                    grouped[gkey] = {
                        "key": gkey,
                        "batchId": bid,
                        "salesDates": set(),
                        "salesDate": dt_iso,
                        "currentHolder": holder,
                        "batchStatus": str(bm.get("status") or row.get("batch_status") or "").strip().upper(),
                        "collectionDate": bm.get("collection_date") if bm else row.get("collection_date"),
                        "cashCollected": 0.0,
                        "expectedAmount": (
                            float(bm["expected_amount"])
                            if bm and pd.notna(bm.get("expected_amount"))
                            else (float(row["expected_amount"]) if pd.notna(row.get("expected_amount")) else None)
                        ),
                        "actualCollectedAmount": (
                            float(bm["actual_collected_amount"])
                            if bm and pd.notna(bm.get("actual_collected_amount"))
                            else (float(row["actual_collected_amount"]) if pd.notna(row.get("actual_collected_amount")) else None)
                        ),
                        "handedOverTo": str(bm.get("handed_over_to") or "").strip().upper() if bm else "",
                        "handedOverDate": bm.get("handed_over_date") if bm else None,
                        "cashSpent": float(bm.get("cash_spent_amount") or 0.0) if bm else 0.0,
                        "cashSpentNotes": str(bm.get("cash_spent_notes") or "").strip() if bm else "",
                        "admin1Spent": float(bm.get("admin1_spent_amount") or 0.0) if bm else 0.0,
                        "admin1SpentNotes": str(bm.get("admin1_spent_notes") or "").strip() if bm else "",
                        "batchNotes": str(bm.get("notes") or "").strip() if bm else "",
                        "carts": [],
                        "dailyEntryIds": [],
                    }
                g = grouped[gkey]
                g["salesDates"].add(dt_iso)
                g["cashCollected"] = round(g["cashCollected"] + amt, 2)
                if cart_nm and cart_nm not in g["carts"]:
                    g["carts"].append(cart_nm)
                if de_id is not None:
                    g["dailyEntryIds"].append(de_id)

        all_groups = []
        for g in grouped.values():
            s_sorted = sorted(g["salesDates"])
            g["salesDates"] = s_sorted
            g["salesDate"] = s_sorted[0] if s_sorted else g["salesDate"]
            g["cartCount"] = len(g["carts"])
            base_exp = g["expectedAmount"] if g["expectedAmount"] is not None else g["cashCollected"]
            g["netCash"] = max(0.0, round(base_exp - g["cashSpent"] - g["admin1Spent"], 2))
            all_groups.append(g)

        # Split into 3 buckets matching App.js
        pending_ops_rows = sorted(
            [g for g in all_groups if g["batchId"] is None and g["currentHolder"] == "OPS_COORDINATOR"],
            key=lambda x: x["salesDate"],
            reverse=True,
        )
        with_yogesh_all = [g for g in all_groups if g["batchId"] is not None and g["currentHolder"] == "YOGESH"]

        # Apply 2-pass Ops spend apportionment to unbatched OPS_COORDINATOR rows
        if pending_ops_rows and spend_list:
            ops_alloc_map = _cc_apportion_spends_to_sales_dates(
                pending_ops_rows,
                spend_list,
                date_getter=lambda r: r["salesDate"],
                gross_getter=lambda r: r["cashCollected"],
            )
            for idx, r in enumerate(pending_ops_rows):
                ap = ops_alloc_map.get(idx, {"spent": 0.0, "notes": []})
                r["expectedAmount"] = r["cashCollected"]
                r["cashSpent"] = ap["spent"]
                r["netCash"] = max(0.0, round(r["cashCollected"] - ap["spent"], 2))
                r["cashSpentNotes"] = " • ".join(ap["notes"])
        else:
            for r in pending_ops_rows:
                r["expectedAmount"] = r["cashCollected"]
                r["netCash"] = max(0.0, round(r["cashCollected"] - r["cashSpent"], 2))

        # Apply 2-pass Admin 1 remaining spend apportionment to WITH_YOGESH batches
        if with_yogesh_all and admin1_remaining_spends:
            adm1_alloc_map = _cc_apportion_spends_to_sales_dates(
                with_yogesh_all,
                admin1_remaining_spends,
                date_getter=lambda r: (r["salesDates"][-1] if r["salesDates"] else (r["salesDate"] or r["collectionDate"])),
                gross_getter=lambda r: (
                    r["actualCollectedAmount"]
                    if r["actualCollectedAmount"] is not None
                    else max(0.0, (r["expectedAmount"] if r["expectedAmount"] is not None else r["cashCollected"]) - r["cashSpent"] - r["admin1Spent"])
                ),
            )
            for idx, r in enumerate(with_yogesh_all):
                ap = adm1_alloc_map.get(idx, {"spent": 0.0, "notes": []})
                extra_adm1 = ap["spent"]
                if extra_adm1 > 0.001:
                    r["admin1Spent"] = round(r["admin1Spent"] + extra_adm1, 2)
                    if ap["notes"]:
                        extra_note_str = " • ".join(ap["notes"])
                        r["admin1SpentNotes"] = (
                            f"{r['admin1SpentNotes']} • {extra_note_str}" if r["admin1SpentNotes"] else extra_note_str
                        )
                    base_after_ops = max(0.0, round((r["expectedAmount"] if r["expectedAmount"] is not None else r["cashCollected"]) - r["cashSpent"], 2))
                    r["netCash"] = max(0.0, round(base_after_ops - r["admin1Spent"], 2))
                    if r["actualCollectedAmount"] is not None:
                        r["actualCollectedAmount"] = max(0.0, round(r["actualCollectedAmount"] - extra_adm1, 2))

        # Stage 1 (Ops Marked -> Collect into Admin 1 / Yogesh)
        marked_rows = sorted(
            [g for g in with_yogesh_all if g["handedOverTo"] != "YOGESH_CONFIRMED"],
            key=lambda x: (x["salesDate"], x["batchId"] or 0),
            reverse=True,
        )
        # Stage 2 (With Admin 1 / Yogesh -> Handover to Admin 2 / Srilalitha)
        with_yogesh_confirmed_rows = sorted(
            [g for g in with_yogesh_all if g["handedOverTo"] == "YOGESH_CONFIRMED"],
            key=lambda x: (x["salesDate"], x["batchId"] or 0),
            reverse=True,
        )

        # Totals matching App.js
        ops_gross = round(sum(r["cashCollected"] for r in pending_ops_rows), 2)
        ops_spent = round(sum(s["remaining_amount"] for s in spend_list), 2)
        ops_net = round(ops_gross - ops_spent, 2)

        stage1_total_net = round(
            sum(max(0.0, (r["expectedAmount"] if r["expectedAmount"] is not None else r["cashCollected"]) - r["cashSpent"]) for r in marked_rows),
            2,
        )
        total_with_yogesh_confirmed = round(
            sum((r["actualCollectedAmount"] if r["actualCollectedAmount"] is not None else r["netCash"]) for r in with_yogesh_confirmed_rows),
            2,
        )
        avail_with_yogesh_total = round(
            sum((r["actualCollectedAmount"] if r["actualCollectedAmount"] is not None else r["netCash"]) for r in with_yogesh_all),
            2,
        )

        # Determine currently selected Stage 1 rows (from session_state checkboxes)
        selected_stage1_rows = [
            r for r in marked_rows if st.session_state.get(f"cc_s1_chk_{r['batchId']}", False)
        ]

        # ------------------------------------------------------------------
        # 3. TOP HEADER BAR & MODAL TRIGGERS
        # ------------------------------------------------------------------
        loc_badge_txt = "All Locations" if active_loc == "ALL" else active_loc
        hdr_c1, hdr_c2, hdr_c3, hdr_c4 = st.columns([2.4, 1.0, 1.45, 1.55], vertical_alignment="center")
        with hdr_c1:
            st.markdown(
                f"""
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                    <span style="font-size:22px;font-weight:800;color:#1E2252;">💰 Cash Custody & Handover</span>
                    <span class="cc-pill blue">{escape(loc_badge_txt)}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with hdr_c2:
            if st.button("🔄 Refresh", key="cc_refresh_btn", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with hdr_c3:
            if st.button(f"🧾 Cash Spends ({len(all_spends)})", key="cc_open_spends_modal", use_container_width=True):
                _cc_show_spends_modal(all_spends, tagged_expense_map)
        with hdr_c4:
            if st.button(f"📚 Recent Confirmed ({len(recent_batches)})", key="cc_open_recent_modal", use_container_width=True):
                _cc_show_recent_collections_modal(recent_batches)

        # ------------------------------------------------------------------
        # 4. SUMMARY CARDS ROW (Shared Ops Wallet / Selected Summary + Pipeline)
        # ------------------------------------------------------------------
        sum_left, sum_right = st.columns([1.0, 1.15], gap="medium")

        with sum_left:
            if selected_stage1_rows:
                sel_gross = round(sum((r["expectedAmount"] if r["expectedAmount"] is not None else r["cashCollected"]) for r in selected_stage1_rows), 2)
                sel_spent = round(sum(r["cashSpent"] for r in selected_stage1_rows), 2)
                sel_net = max(0.0, round(sel_gross - sel_spent, 2))
                st.markdown(
                    f"""
                    <div class="cc-card-selected">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div class="cc-eyebrow" style="color:#1D4ED8;">SELECTED HANDOVER SUMMARY ({len(selected_stage1_rows)})</div>
                            <span class="cc-pill blue">Stage 1 Selection</span>
                        </div>
                        <div class="cc-big-num" style="color:#1D4ED8;">{_cc_fmt_inr(sel_net)}</div>
                        <div style="font-size:12px;color:#475569;margin-top:2px;">Net cash expected from selected Ops handover batch(es)</div>
                        <div class="cc-kpi-row">
                            <div class="cc-kpi-tile">
                                <div class="cc-kpi-lbl">Selected Gross</div>
                                <div class="cc-kpi-val">{_cc_fmt_inr(sel_gross)}</div>
                            </div>
                            <div class="cc-kpi-tile red">
                                <div class="cc-kpi-lbl" style="color:#B91C1C;">Ops Spent</div>
                                <div class="cc-kpi-val" style="color:#C43D17;">-{_cc_fmt_inr(sel_spent)}</div>
                            </div>
                            <div class="cc-kpi-tile blue">
                                <div class="cc-kpi-lbl" style="color:#1D4ED8;">Net to Collect</div>
                                <div class="cc-kpi-val" style="color:#1E40AF;">{_cc_fmt_inr(sel_net)}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="cc-card">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <div class="cc-eyebrow">SHARED OPS CASH WALLET</div>
                            <span class="cc-pill amber">{len(pending_ops_rows)} unhanded day(s)</span>
                        </div>
                        <div class="cc-big-num">{_cc_fmt_inr(ops_net)}</div>
                        <div style="font-size:12px;color:#64748B;margin-top:2px;">Net cash currently held by Ops Coordinator</div>
                        <div class="cc-kpi-row">
                            <div class="cc-kpi-tile">
                                <div class="cc-kpi-lbl">Gross Sales Cash</div>
                                <div class="cc-kpi-val">{_cc_fmt_inr(ops_gross)}</div>
                            </div>
                            <div class="cc-kpi-tile red">
                                <div class="cc-kpi-lbl" style="color:#B91C1C;">Less Ops Spent</div>
                                <div class="cc-kpi-val" style="color:#C43D17;">-{_cc_fmt_inr(ops_spent)}</div>
                            </div>
                            <div class="cc-kpi-tile green">
                                <div class="cc-kpi-lbl" style="color:#047857;">Net With Ops</div>
                                <div class="cc-kpi-val" style="color:#059669;">{_cc_fmt_inr(ops_net)}</div>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        with sum_right:
            st.markdown(
                f"""
                <div class="cc-card">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div class="cc-eyebrow">TWO-STAGE ADMIN CUSTODY PIPELINE</div>
                        <span class="cc-pill green">Live Custody</span>
                    </div>
                    <div class="cc-big-num" style="color:#059669;">{_cc_fmt_inr(total_with_srilalitha)}</div>
                    <div style="font-size:12px;color:#64748B;margin-top:2px;">Cumulative confirmed cash with Admin 2 (Srilalitha)</div>
                    <div class="cc-kpi-row">
                        <div class="cc-kpi-tile amber">
                            <div class="cc-kpi-lbl" style="color:#B45309;">Stage 1 • Ops Marked</div>
                            <div class="cc-kpi-val" style="color:#B45309;">{_cc_fmt_inr(stage1_total_net)}</div>
                            <div class="cc-kpi-sub">{len(marked_rows)} batch(es) to collect</div>
                        </div>
                        <div class="cc-kpi-tile blue">
                            <div class="cc-kpi-lbl" style="color:#1D4ED8;">Admin 1 • Yogesh</div>
                            <div class="cc-kpi-val" style="color:#1E40AF;">{_cc_fmt_inr(total_with_yogesh_confirmed)}</div>
                            <div class="cc-kpi-sub">{len(with_yogesh_confirmed_rows)} batch(es) in hand</div>
                        </div>
                        <div class="cc-kpi-tile green">
                            <div class="cc-kpi-lbl" style="color:#047857;">Admin 2 • Srilalitha</div>
                            <div class="cc-kpi-val" style="color:#059669;">{_cc_fmt_inr(total_with_srilalitha)}</div>
                            <div class="cc-kpi-sub">Confirmed total</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ------------------------------------------------------------------
        # 5. CASH STILL WITH OPS — SALES-DATE BREAKDOWN TABLE
        # ------------------------------------------------------------------
        st.markdown('<div class="cc-sec-hdr">📅 Cash Still With Ops — Sales-Date Breakdown</div>', unsafe_allow_html=True)
        if pending_ops_rows:
            rows_html = []
            for r in pending_ops_rows:
                carts_txt = ", ".join(r["carts"]) if r["carts"] else f"{r['cartCount']} cart(s)"
                has_spend = float(r["cashSpent"] or 0.0) > 0.001
                sp_cls = "num cc-col-spent" if has_spend else "num cc-col-spent-zero"
                sp_disp = _cc_fmt_inr(r["cashSpent"]) if has_spend else "-"
                rows_html.append(
                    f"<tr>"
                    f"<td><strong>{_cc_fmt_date(r['salesDate'])}</strong></td>"
                    f"<td>{escape(carts_txt)}</td>"
                    f"<td class='num cc-col-gross'>{_cc_fmt_inr(r['cashCollected'])}</td>"
                    f"<td class='{sp_cls}'>{sp_disp}</td>"
                    f"<td class='num cc-col-net'>{_cc_fmt_inr(r['netCash'])}</td>"
                    f"</tr>"
                )
            tot_spent_table = round(sum(r["cashSpent"] for r in pending_ops_rows), 2)
            tot_net_table = round(sum(r["netCash"] for r in pending_ops_rows), 2)
            tot_spent_disp = _cc_fmt_inr(tot_spent_table) if tot_spent_table > 0.001 else "-"
            rows_html.append(
                f"<tr class='cc-total-row'>"
                f"<td colspan='2'>TOTAL ({len(pending_ops_rows)} date(s))</td>"
                f"<td class='num cc-col-gross'>{_cc_fmt_inr(ops_gross)}</td>"
                f"<td class='num cc-col-spent'>{tot_spent_disp}</td>"
                f"<td class='num cc-col-net'>{_cc_fmt_inr(tot_net_table)}</td>"
                f"</tr>"
            )
            st.markdown(
                f"""
                <div class="cc-table-wrap">
                    <table class="cc-table">
                        <thead>
                            <tr>
                                <th>Sales Date</th>
                                <th>Carts</th>
                                <th class="num cc-col-gross">Gross</th>
                                <th class="num cc-col-spent">Spent</th>
                                <th class="num cc-col-net">Net</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(rows_html)}
                        </tbody>
                    </table>
                </div>
                <div class="cc-banner-net">
                    <div>
                        <span style="font-size:12px;font-weight:800;color:#1E40AF;text-transform:uppercase;letter-spacing:0.04em;">Net Cash Still With Ops</span>
                        <span style="font-size:12px;color:#475569;margin-left:8px;">(Gross {_cc_fmt_inr(ops_gross)} − Unhanded Ops Spends {_cc_fmt_inr(ops_spent)})</span>
                    </div>
                    <div style="font-size:18px;font-weight:800;color:#1E2252;">{_cc_fmt_inr(ops_net)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No unhanded sales cash is currently sitting with Ops Coordinator.")

        # ------------------------------------------------------------------
        # 6. ADD ADMIN 1 (YOGESH) CASH SPENT
        # ------------------------------------------------------------------
        st.markdown('<div class="cc-sec-hdr">💸 Add Admin 1 (Yogesh) Cash Spent</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.caption(
                f"Available cash with Admin 1 (Yogesh): **{_cc_fmt_inr(avail_with_yogesh_total)}** • "
                f"Location: **{write_loc}** • Automatically allocates against Admin 1 batches."
            )
            with st.form("cc_admin1_spend_form", clear_on_submit=True):
                sp_c1, sp_c2, sp_c3 = st.columns([1.1, 1.1, 2.2])
                with sp_c1:
                    adm1_dt = st.date_input("Expense Date", value=date.today(), key="cc_adm1_dt")
                with sp_c2:
                    adm1_amt = st.number_input("Cash Spent (₹)", min_value=0.0, step=10.0, format="%.2f", key="cc_adm1_amt")
                with sp_c3:
                    adm1_notes = st.text_input(
                        "Reason / Details (Required)",
                        placeholder="e.g., Fuel, dry ice, cart repair, packing supplies...",
                        key="cc_adm1_notes",
                    )
                submit_adm1 = st.form_submit_button("💾 Record Admin 1 Cash Spend", type="primary")
                if submit_adm1:
                    if float(adm1_amt or 0.0) <= 0.0:
                        st.error("Please enter a valid cash spend amount greater than ₹0.")
                    elif not str(adm1_notes or "").strip():
                        st.error("Please enter reason / details for this cash spend.")
                    elif float(adm1_amt) > avail_with_yogesh_total + 0.001:
                        st.error(
                            f"Spend amount ({_cc_fmt_inr(adm1_amt)}) exceeds available cash with Admin 1 ({_cc_fmt_inr(avail_with_yogesh_total)})."
                        )
                    else:
                        try:
                            alloc_warn = None
                            with db_conn.session as s:
                                s.execute(
                                    text(
                                        """
                                        INSERT INTO public.cash_ops_spend_entries
                                            (spend_date, amount, notes, location, spent_by)
                                        VALUES
                                            (:dt, :amt, :notes, :loc, 'ADMIN_1');
                                        """
                                    ),
                                    {
                                        "dt": adm1_dt,
                                        "amt": float(adm1_amt),
                                        "notes": str(adm1_notes).strip(),
                                        "loc": write_loc,
                                    },
                                )
                                try:
                                    with s.begin_nested():
                                        s.execute(
                                            text("SELECT public.allocate_admin1_cash_spends(:loc);"),
                                            {"loc": write_loc},
                                        )
                                except Exception as alloc_err:
                                    alloc_warn = str(alloc_err)
                                s.commit()
                            st.cache_data.clear()
                            if alloc_warn:
                                st.warning(f"Spend saved, but auto-allocation RPC returned a warning: {alloc_warn}")
                            else:
                                st.success(f"Recorded Admin 1 cash spend of {_cc_fmt_inr(adm1_amt)}.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to record Admin 1 cash spend: {e}")

        # ------------------------------------------------------------------
        # 7. STAGE 1: COLLECT FROM OPS -> ADMIN 1 (YOGESH)
        # ------------------------------------------------------------------
        s1_hdr_l, s1_hdr_r1, s1_hdr_r2 = st.columns([3.2, 0.85, 0.85], vertical_alignment="center")
        with s1_hdr_l:
            st.markdown(
                f'<div class="cc-sec-hdr">📥 Stage 1: Collect from Ops → Admin 1 (Yogesh) '
                f'<span class="cc-pill amber">{len(marked_rows)} pending</span></div>',
                unsafe_allow_html=True,
            )

        def _cc_set_all_s1(val, bids):
            for _b in bids:
                st.session_state[f"cc_s1_chk_{_b}"] = val

        s1_bids = [r["batchId"] for r in marked_rows]
        if marked_rows:
            with s1_hdr_r1:
                st.button("Select All", key="cc_s1_sel_all", on_click=_cc_set_all_s1, args=(True, s1_bids), use_container_width=True)
            with s1_hdr_r2:
                st.button("Clear", key="cc_s1_clr_all", on_click=_cc_set_all_s1, args=(False, s1_bids), use_container_width=True)

        if not marked_rows:
            st.info("No Ops-marked handovers are currently waiting for Admin 1 (Yogesh) collection.")
        else:
            s1_selected_payloads = []
            for r in marked_rows:
                bid = int(r["batchId"])
                gross_val = float(r["expectedAmount"] if r["expectedAmount"] is not None else r["cashCollected"])
                spent_val = float(r["cashSpent"] or 0.0)
                exp_net = max(0.0, round(gross_val - spent_val, 2))
                s_dates = r["salesDates"]
                dates_str = (
                    _cc_fmt_date(s_dates[0])
                    if len(s_dates) == 1
                    else f"{_cc_fmt_date(s_dates[0])} → {_cc_fmt_date(s_dates[-1])} ({len(s_dates)} days)"
                )
                carts_str = ", ".join(r["carts"]) if r["carts"] else f"{r['cartCount']} cart(s)"

                with st.container(border=True):
                    top_l, top_r = st.columns([3.2, 1.0], vertical_alignment="center")
                    with top_l:
                        is_sel = st.checkbox(
                            f"Batch #{bid}  •  Sales: {dates_str}  •  {carts_str}",
                            key=f"cc_s1_chk_{bid}",
                        )
                    with top_r:
                        st.markdown(
                            "<div style='text-align:right;'><span class='cc-pill amber'>Ops Marked</span></div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f"""
                        <div class="cc-kpi-row" style="margin-top:4px;margin-bottom:8px;">
                            <div class="cc-kpi-tile">
                                <div class="cc-kpi-lbl">Gross Sales Cash</div>
                                <div class="cc-kpi-val">{_cc_fmt_inr(gross_val)}</div>
                            </div>
                            <div class="cc-kpi-tile red">
                                <div class="cc-kpi-lbl" style="color:#B91C1C;">Ops Spent Deducted</div>
                                <div class="cc-kpi-val" style="color:#C43D17;">-{_cc_fmt_inr(spent_val)}</div>
                            </div>
                            <div class="cc-kpi-tile blue">
                                <div class="cc-kpi-lbl" style="color:#1D4ED8;">Expected Net</div>
                                <div class="cc-kpi-val" style="color:#1E2252;">{_cc_fmt_inr(exp_net)}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    notes_parts = []
                    if r["cashSpentNotes"]:
                        notes_parts.append(f"<b>Ops Spend Breakdown:</b> {escape(r['cashSpentNotes'])}")
                    if r["batchNotes"]:
                        notes_parts.append(f"<b>Ops Handover Notes:</b> {escape(r['batchNotes'])}")
                    if notes_parts:
                        st.markdown(f"<div class='cc-note-box'>{'<br>'.join(notes_parts)}</div>", unsafe_allow_html=True)

                    in_c1, in_c2 = st.columns([1.15, 2.2])
                    with in_c1:
                        actual_val = st.number_input(
                            "Actual Cash Received (₹)",
                            min_value=0.0,
                            value=float(exp_net),
                            step=10.0,
                            format="%.2f",
                            key=f"cc_s1_act_{bid}",
                        )
                    diff = round(float(actual_val) - exp_net, 2)
                    diff_needed = abs(diff) > 0.001
                    with in_c2:
                        note_lbl = "Collection Notes (Required — cash difference detected)" if diff_needed else "Collection Notes (Optional)"
                        coll_note = st.text_input(
                            note_lbl,
                            placeholder="Explain shortage/excess or add collection note...",
                            key=f"cc_s1_note_{bid}",
                        )

                    if abs(diff) <= 0.001:
                        st.markdown("<span class='cc-pill green'>✓ Exact Match</span>", unsafe_allow_html=True)
                    elif diff < 0:
                        st.markdown(f"<span class='cc-pill red'>⚠ Short by {_cc_fmt_inr(abs(diff))} — note required</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<span class='cc-pill blue'>＋ Excess by {_cc_fmt_inr(diff)} — note required</span>", unsafe_allow_html=True)

                    if is_sel:
                        s1_selected_payloads.append({
                            "batch_id": bid,
                            "expected_net": exp_net,
                            "actual_collected_amount": round(float(actual_val), 2),
                            "notes": str(coll_note or "").strip(),
                            "diff_needed": diff_needed,
                        })

            s1_sel_tot = round(sum(p["actual_collected_amount"] for p in s1_selected_payloads), 2)
            if st.button(
                f"✓ Confirm Collected by Admin 1 (Yogesh) — {len(s1_selected_payloads)} batch(es) • {_cc_fmt_inr(s1_sel_tot)}",
                key="cc_s1_confirm_btn",
                type="primary",
                disabled=(len(s1_selected_payloads) == 0),
                use_container_width=True,
            ):
                missing_note_bids = [p["batch_id"] for p in s1_selected_payloads if p["diff_needed"] and not p["notes"]]
                if missing_note_bids:
                    st.error(
                        f"Please enter collection notes for Batch #{', #'.join(str(x) for x in missing_note_bids)} because the actual cash differs from the expected net."
                    )
                else:
                    confirmations = [
                        {
                            "batch_id": int(p["batch_id"]),
                            "actual_collected_amount": float(p["actual_collected_amount"]),
                            "notes": p["notes"] or None,
                        }
                        for p in s1_selected_payloads
                    ]
                    try:
                        with db_conn.session as s:
                            s.execute(
                                text("SELECT public.confirm_ops_cash_dates(CAST(:payload AS jsonb));"),
                                {"payload": json.dumps(confirmations)},
                            )
                            s.commit()
                        for p in s1_selected_payloads:
                            st.session_state.pop(f"cc_s1_chk_{p['batch_id']}", None)
                            st.session_state.pop(f"cc_s1_act_{p['batch_id']}", None)
                            st.session_state.pop(f"cc_s1_note_{p['batch_id']}", None)
                        st.cache_data.clear()
                        st.success(f"Confirmed collection of {len(confirmations)} batch(es) ({_cc_fmt_inr(s1_sel_tot)}) into Admin 1 (Yogesh) custody.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not confirm Stage 1 collection: {e}")

        # ------------------------------------------------------------------
        # 8. STAGE 2: ADMIN 1 (YOGESH) -> HANDOVER TO ADMIN 2 (SRILALITHA)
        # ------------------------------------------------------------------
        s2_hdr_l, s2_hdr_r1, s2_hdr_r2 = st.columns([3.2, 0.85, 0.85], vertical_alignment="center")
        with s2_hdr_l:
            st.markdown(
                f'<div class="cc-sec-hdr">🤝 Stage 2: Admin 1 (Yogesh) → Handover to Admin 2 (Srilalitha) '
                f'<span class="cc-pill blue">{len(with_yogesh_confirmed_rows)} ready</span></div>',
                unsafe_allow_html=True,
            )

        def _cc_set_all_s2(val, bids):
            for _b in bids:
                st.session_state[f"cc_s2_chk_{_b}"] = val

        s2_bids = [r["batchId"] for r in with_yogesh_confirmed_rows]
        if with_yogesh_confirmed_rows:
            with s2_hdr_r1:
                st.button("Select All", key="cc_s2_sel_all", on_click=_cc_set_all_s2, args=(True, s2_bids), use_container_width=True)
            with s2_hdr_r2:
                st.button("Clear", key="cc_s2_clr_all", on_click=_cc_set_all_s2, args=(False, s2_bids), use_container_width=True)

        if not with_yogesh_confirmed_rows:
            st.info("No Admin 1 (Yogesh) confirmed batches are waiting for handover to Admin 2 (Srilalitha).")
        else:
            s2_selected_rows = []
            for r in with_yogesh_confirmed_rows:
                bid = int(r["batchId"])
                gross_val = float(r["expectedAmount"] if r["expectedAmount"] is not None else r["cashCollected"])
                ops_sp = float(r["cashSpent"] or 0.0)
                adm1_sp = float(r["admin1Spent"] or 0.0)
                net_handover = float(r["actualCollectedAmount"] if r["actualCollectedAmount"] is not None else r["netCash"])
                s_dates = r["salesDates"]
                dates_str = (
                    _cc_fmt_date(s_dates[0])
                    if len(s_dates) == 1
                    else f"{_cc_fmt_date(s_dates[0])} → {_cc_fmt_date(s_dates[-1])} ({len(s_dates)} days)"
                )
                carts_str = ", ".join(r["carts"]) if r["carts"] else f"{r['cartCount']} cart(s)"

                with st.container(border=True):
                    top_l, top_r = st.columns([3.2, 1.0], vertical_alignment="center")
                    with top_l:
                        is_s2_sel = st.checkbox(
                            f"Batch #{bid}  •  Sales: {dates_str}  •  {carts_str}",
                            key=f"cc_s2_chk_{bid}",
                        )
                    with top_r:
                        st.markdown(
                            "<div style='text-align:right;'><span class='cc-pill blue'>With Yogesh</span></div>",
                            unsafe_allow_html=True,
                        )

                    st.markdown(
                        f"""
                        <div class="cc-kpi-row" style="margin-top:4px;">
                            <div class="cc-kpi-tile">
                                <div class="cc-kpi-lbl">Gross / After Ops Spent</div>
                                <div class="cc-kpi-val">{_cc_fmt_inr(max(0.0, gross_val - ops_sp))}</div>
                                <div class="cc-kpi-sub">Gross {_cc_fmt_inr(gross_val)} • Ops Spent {_cc_fmt_inr(ops_sp)}</div>
                            </div>
                            <div class="cc-kpi-tile red">
                                <div class="cc-kpi-lbl" style="color:#B91C1C;">Admin 1 Spent</div>
                                <div class="cc-kpi-val" style="color:#C43D17;">-{_cc_fmt_inr(adm1_sp)}</div>
                                <div class="cc-kpi-sub">Deducted from Admin 1</div>
                            </div>
                            <div class="cc-kpi-tile green">
                                <div class="cc-kpi-lbl" style="color:#047857;">Net to Handover</div>
                                <div class="cc-kpi-val" style="color:#059669;">{_cc_fmt_inr(net_handover)}</div>
                                <div class="cc-kpi-sub">To Admin 2 (Srilalitha)</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    notes_parts = []
                    if r["admin1SpentNotes"]:
                        notes_parts.append(f"<b>Admin 1 Spent:</b> {escape(r['admin1SpentNotes'])}")
                    if r["cashSpentNotes"]:
                        notes_parts.append(f"<b>Ops Spent:</b> {escape(r['cashSpentNotes'])}")
                    if r["batchNotes"]:
                        notes_parts.append(f"<b>Batch Notes:</b> {escape(r['batchNotes'])}")
                    if notes_parts:
                        st.markdown(f"<div class='cc-note-box'>{'<br>'.join(notes_parts)}</div>", unsafe_allow_html=True)

                    if is_s2_sel:
                        s2_selected_rows.append(r)

            s2_handover_note = st.text_input(
                "Handover Notes to Admin 2 (Srilalitha) (Optional)",
                placeholder="e.g., Handed over cash in person / deposited...",
                key="cc_s2_handover_note",
            )
            s2_sel_tot = round(
                sum((r["actualCollectedAmount"] if r["actualCollectedAmount"] is not None else r["netCash"]) for r in s2_selected_rows),
                2,
            )
            if st.button(
                f"🤝 Confirm Handover to Admin 2 (Srilalitha) — {len(s2_selected_rows)} batch(es) • {_cc_fmt_inr(s2_sel_tot)}",
                key="cc_s2_confirm_btn",
                type="primary",
                disabled=(len(s2_selected_rows) == 0),
                use_container_width=True,
            ):
                sel_batch_ids = [int(r["batchId"]) for r in s2_selected_rows]
                note_clean = str(s2_handover_note or "").strip() or None
                try:
                    with db_conn.session as s:
                        rpc_ok = False
                        try:
                            with s.begin_nested():
                                s.execute(
                                    text("SELECT public.handover_yogesh_batches_to_srilalitha(:batch_ids, :notes);"),
                                    {"batch_ids": sel_batch_ids, "notes": note_clean},
                                )
                                rpc_ok = True
                        except Exception:
                            rpc_ok = False

                        if not rpc_ok:
                            # Exact App.js fallback UPDATE
                            for r in s2_selected_rows:
                                bid = int(r["batchId"])
                                prev_n = str(r.get("batchNotes") or "").strip()
                                if note_clean:
                                    combined_n = f"{prev_n} | Handover to Srilalitha: {note_clean}" if prev_n else f"Handover to Srilalitha: {note_clean}"
                                else:
                                    combined_n = prev_n or None
                                s.execute(
                                    text(
                                        """
                                        UPDATE public.cash_handover_batches
                                        SET status = 'HANDED_TO_SRILALITHA',
                                            handed_over_date = CURRENT_DATE,
                                            handed_over_to = 'Srilalitha',
                                            notes = :combined
                                        WHERE id = :bid
                                          AND status = 'WITH_YOGESH';
                                        """
                                    ),
                                    {"combined": combined_n, "bid": bid},
                                )
                        s.commit()

                    for bid in sel_batch_ids:
                        st.session_state.pop(f"cc_s2_chk_{bid}", None)
                    st.session_state.pop("cc_s2_handover_note", None)
                    st.cache_data.clear()
                    st.success(f"Confirmed handover of {len(sel_batch_ids)} batch(es) ({_cc_fmt_inr(s2_sel_tot)}) to Admin 2 (Srilalitha).")
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not complete Stage 2 handover: {e}")

        # ------------------------------------------------------------------
        # 9. SALES CASH STILL WITH OPS — PER-DATE SUMMARY CARDS
        # ------------------------------------------------------------------
        if pending_ops_rows:
            st.markdown(
                f'<div class="cc-sec-hdr">🧾 Sales Cash Still With Ops (Per-Date Details) '
                f'<span class="cc-pill amber">{len(pending_ops_rows)} date(s)</span></div>',
                unsafe_allow_html=True,
            )
            for r in pending_ops_rows:
                carts_str = ", ".join(r["carts"]) if r["carts"] else f"{r['cartCount']} cart(s)"
                note_block = (
                    f"<div class='cc-note-box'><b>Apportioned Ops Spends:</b> {escape(r['cashSpentNotes'])}</div>"
                    if r["cashSpentNotes"]
                    else ""
                )
                st.markdown(
                    f"""
                    <div class="cc-card" style="padding:12px 16px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                            <div>
                                <span style="font-size:15px;font-weight:800;color:#1E2252;">{_cc_fmt_date(r['salesDate'])}</span>
                                <span style="font-size:12px;color:#64748B;margin-left:8px;">{escape(carts_str)}</span>
                            </div>
                            <span class="cc-pill amber">With Ops Coordinator</span>
                        </div>
                        <div class="cc-kpi-row" style="margin-top:8px;">
                            <div class="cc-kpi-tile">
                                <div class="cc-kpi-lbl">Gross Cash</div>
                                <div class="cc-kpi-val">{_cc_fmt_inr(r['cashCollected'])}</div>
                            </div>
                            <div class="cc-kpi-tile red">
                                <div class="cc-kpi-lbl" style="color:#B91C1C;">Apportioned Spent</div>
                                <div class="cc-kpi-val" style="color:#C43D17;">-{_cc_fmt_inr(r['cashSpent'])}</div>
                            </div>
                            <div class="cc-kpi-tile green">
                                <div class="cc-kpi-lbl" style="color:#047857;">Net Cash</div>
                                <div class="cc-kpi-val" style="color:#059669;">{_cc_fmt_inr(r['netCash'])}</div>
                            </div>
                        </div>
                        {note_block}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    elif page == "Purchase Orders" and user_role == "admin":
        st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
        st.subheader("Purchase Order Estimator & Order Management")
        pass

        # Apply pending PO mode before the radio widget is instantiated.
        if "_pending_po_screen_mode" in st.session_state:
            st.session_state["po_screen_mode"] = st.session_state.pop("_pending_po_screen_mode")

        po_mode = st.radio("Mode", ["Create New Order", "Edit / Track Existing Orders"], horizontal=True, key="po_screen_mode")

        if st.session_state.get("po_success_message"):
            st.success(st.session_state.pop("po_success_message"))

        if po_mode == "Create New Order":
            pass

            c1, c2, c3, c4, c5 = st.columns([1.0, 1.0, 0.95, 1.0, 0.9], gap="small")
            with c1: order_date = st.date_input("Order Date", value=date.today(), key="new_po_order_date", format="DD-MM-YYYY")
            with c2: expected_date = st.date_input("Expected Delivery Date", value=date.today() + timedelta(days=2), key="new_po_exp_date", format="DD-MM-YYYY")
            with c3: location = st.text_input("Delivery Location", value=CITY, key="new_po_loc")
            with c4: order_status = st.selectbox("Order Status", PO_STATUSES, index=PO_STATUSES.index("Placed"), key="new_po_status")
            with c5: discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, format="%.2f", key="new_po_discount")

            grid_rows = []
            prefill_qty = st.session_state.get("po_prefill_quantities", {}) if st.session_state.get("po_prefill_active", False) else {}
            for code in FLAVOR_CODES:
                f_info = FLAVOR_MAP[code]
                grid_rows.append({"Flavour": f_info["name"], "Code": code, "Unit Cost (₹)": float(f_info["cost_price"]), "Order Quantity": int(prefill_qty.get(code, 0))})

            po_editor_df = st.data_editor(pd.DataFrame(grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Order Quantity": st.column_config.NumberColumn(min_value=0, step=10, format="%d")}, hide_index=True, use_container_width=True, row_height=28, key="new_po_editor")

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

            if st.session_state.get("po_prefill_active", False):
                st.markdown("#### WhatsApp Order Message")
                whatsapp_number = st.text_input("WhatsApp Number", placeholder="e.g. 9876543210 or +91 9876543210", key="po_whatsapp_number")
                whatsapp_rows = [(str(row["Flavour"]), int(row["Order Quantity"])) for _, row in po_editor_df.iterrows() if int(row["Order Quantity"]) > 0]
                order_date_text = order_date.strftime("%d-%b-%Y") if hasattr(order_date, "strftime") else str(order_date)
                # Build a boxed table. WhatsApp renders code blocks in monospace,
                # so the borders and Qty column remain visually aligned.
                flavour_width = max(12, max((len(flavour) for flavour, _ in whatsapp_rows), default=0))
                qty_width = max(3, len(str(total_units)))
                border = f"┌{'─' * (flavour_width + 2)}┬{'─' * (qty_width + 2)}┐"
                divider = f"├{'─' * (flavour_width + 2)}┼{'─' * (qty_width + 2)}┤"
                bottom = f"└{'─' * (flavour_width + 2)}┴{'─' * (qty_width + 2)}┘"
                wa_lines = [f"{str(location or CITY).strip().upper()}:: KULFI ORDER - {order_date_text}", "", border,
                            f"│ {'Flavour':<{flavour_width}} │ {'Qty':>{qty_width}} │", divider]
                for flavour, qty in whatsapp_rows:
                    wa_lines.append(f"│ {flavour:<{flavour_width}} │ {qty:>{qty_width}} │")
                wa_lines.extend([divider,
                                 f"│ {'Overall Units':<{flavour_width}} │ {total_units:>{qty_width}} │",
                                 bottom])
                whatsapp_message = "```\n" + "\n".join(wa_lines) + "\n```"
                if total_units > 0:
                    wa_digits = re.sub(r"\D", "", whatsapp_number or "")
                    if len(wa_digits) == 10: wa_digits = "91" + wa_digits
                    st.text(whatsapp_message)
                    if len(wa_digits) >= 10:
                        st.link_button("📲 Send Order to WhatsApp", f"https://wa.me/{wa_digits}?text={quote(whatsapp_message)}", use_container_width=True)
                        pass
                        if st.button("✅ WhatsApp sent — Continue", use_container_width=True, key="wa_sent_continue"):
                            st.session_state["wa_confirmation_payload"] = {"order_date": order_date, "expected_date": expected_date, "location": location, "discount_pct": float(discount_pct), "notes": po_notes.strip(), "total_units": total_units, "final_amount": final_amount, "items": [(str(row["Code"]), int(row["Order Quantity"])) for _, row in po_editor_df.iterrows() if int(row["Order Quantity"]) > 0]}
                            show_whatsapp_order_confirmation()
                    else:
                        st.caption("Enter a valid WhatsApp number to enable the WhatsApp button.")
                else:
                    st.info("There are no suggested/entered quantities to send. Please enter at least one quantity.")
            else:
                if st.button("🚀 Submit Purchase Order", type="primary", use_container_width=False, key="submit_new_po_btn"):
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
                            st.cache_data.clear()
                            show_success_modal(f"Purchase Order #{new_poid} created successfully! Total: {total_units} units | Final Amount: ₹{final_amount:,.2f} ({discount_pct:.1f}% off).")
                        except Exception as e: st.error(f"Could not save purchase order to database: {e}")


        elif po_mode == "Edit / Track Existing Orders":
            po_query_df = db_conn.query("SELECT p.id, p.order_date, p.expected_date, p.location, p.order_status, p.notes, json_agg(json_build_object('code', pi.flavor_code, 'qty', pi.ordered_units)) AS items FROM purchase_orders p LEFT JOIN purchase_order_items pi ON p.id = pi.order_id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(p.location, 'HOSUR'))) = :active_loc) GROUP BY p.id ORDER BY p.order_date DESC, p.id DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if po_query_df.empty: st.info("No purchase orders found in the database.")
            else:
                po_records = po_query_df.to_dict("records")
                po_labels = [f"PO #{r['id']} — {pd.to_datetime(r['order_date']).strftime('%d-%b-%y')} ({r['location']}) — Status: {r['order_status']}" for r in po_records]
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
                with c1: e_order_date = st.date_input("Order Date", value=pd.to_datetime(loaded_po["order_date"]).date() if loaded_po.get("order_date") else date.today(), key=f"edit_po_od_{loaded_po_id}", format="DD-MM-YYYY")
                with c2: e_expected_date = st.date_input("Expected Delivery Date", value=pd.to_datetime(loaded_po["expected_date"]).date() if loaded_po.get("expected_date") else date.today() + timedelta(days=2), key=f"edit_po_ed_{loaded_po_id}", format="DD-MM-YYYY")
                with c3: e_location = st.text_input("Delivery Location", value=str(loaded_po.get("location", CITY)), key=f"edit_po_loc_{loaded_po_id}")

                c4, c5 = st.columns(2)
                with c4: e_status = st.selectbox("Order Status", PO_STATUSES, index=PO_STATUSES.index(loaded_po.get("order_status", "Placed")) if loaded_po.get("order_status", "Placed") in PO_STATUSES else 0, key=f"edit_po_stat_{loaded_po_id}")
                with c5: e_discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=default_disc, step=0.5, format="%.2f", key=f"edit_po_disc_{loaded_po_id}")

                items_by_code = {itm["code"]: itm.get("qty", 0) for itm in loaded_po.get("items", []) if isinstance(itm, dict) and "code" in itm} if loaded_po.get("items") and isinstance(loaded_po["items"], list) else {}
                edit_grid_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Order Quantity": int(items_by_code.get(code) or 0)} for code in FLAVOR_CODES]

                pass
                po_edit_editor_df = st.data_editor(pd.DataFrame(edit_grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Order Quantity": st.column_config.NumberColumn(min_value=0, step=10, format="%d")}, hide_index=True, use_container_width=True, row_height=28, key=f"edit_po_editor_{loaded_po_id}")

                e_total_units = int(po_edit_editor_df["Order Quantity"].sum())
                e_gross_cost = float(sum(po_edit_editor_df["Order Quantity"] * po_edit_editor_df["Unit Cost (₹)"]))
                e_discount_amount = e_gross_cost * (e_discount_pct / 100.0)
                e_final_amount = e_gross_cost - e_discount_amount

                st.markdown("#### Updated Order Summary")
                em1, em2, em3, em4 = st.columns(4)
                em1.metric("Total Ordered Units", f"{e_total_units} units"); em2.metric("Gross Cost", f"₹{e_gross_cost:,.2f}"); em3.metric(f"Discount ({e_discount_pct:.1f}%)", f"-₹{e_discount_amount:,.2f}"); em4.metric("Final Amount to Pay", f"₹{e_final_amount:,.2f}")
                e_notes = st.text_input("Order Notes", value=clean_notes, key=f"edit_po_notes_{loaded_po_id}")

                if st.button("💾 Update Purchase Order", type="primary", use_container_width=False, key="submit_upd_po_btn"):
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
                            st.cache_data.clear()
                            show_success_modal(f"Purchase Order #{loaded_po_id} updated successfully! Final Amount: ₹{e_final_amount:,.2f}.")
                        except Exception as e: st.error(f"Could not update purchase order: {e}")

    elif page == "Freezer Stock" and user_role == "admin":
        st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
        st.subheader("Freezer Stock Management")

        freezer_tab_choice = st.radio("Section", ["Stock Received (Inward)", "Stock Audit (Physical Count)"], horizontal=True)

        if freezer_tab_choice == "Stock Received (Inward)":
            stock_mode = st.radio(
                "Mode",
                ["New entry", "Edit past entry", "📊 Stock Received Report"],
                horizontal=True,
                key="db_stock_mode",
            )

            past_receipts_df = db_conn.query(
                """
                SELECT r.id, r.received_date, r.location, r.purchase_order_id,
                       r.payment_amount, r.payment_status, r.payment_date,
                       r.payment_details, r.damaged_returned_on, r.notes,
                       json_agg(json_build_object('code', i.flavor_code, 'rec', i.received_units, 'dam', i.damaged_units, 'cost', i.unit_cost_price)) AS items
                FROM stock_received r
                LEFT JOIN stock_received_items i ON r.id = i.received_id
                WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :active_loc)
                GROUP BY r.id
                ORDER BY r.received_date DESC, r.id DESC;
                """,
                params={"active_loc": get_active_location_filter()},
                ttl="60s",
            )
            past_receipts = past_receipts_df.to_dict("records") if not past_receipts_df.empty else []

            if stock_mode in ("New entry", "Edit past entry"):
                stock_loaded, loaded_id = None, None
                if stock_mode == "Edit past entry":
                    if not past_receipts: st.info("No past delivery receipts found in database.")
                    else:
                        labels = [f"Receipt #{r['id']} — {pd.to_datetime(r['received_date']).strftime('%d-%b-%y')} ({r['location']})" for r in past_receipts]
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

                pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders WHERE order_status != 'Completed' AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc) ORDER BY order_date DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
                po_options = ["None (Ad-hoc delivery)"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d-%b')})" for _, r in pos_df.iterrows()]

                default_po_idx = 0
                poid_raw = stock_loaded.get("purchase_order_id") if stock_loaded else None
                if poid_raw is not None and pd.notna(poid_raw) and str(poid_raw).strip() != "":
                    try:
                        poid_int = int(float(poid_raw))
                        for idx, opt in enumerate(po_options):
                            if opt.startswith(f"PO #{poid_int} "): default_po_idx = idx; break
                    except Exception: default_po_idx = 0

                c1, c2, c3, c4 = st.columns(4)
                with c1: received_date = st.date_input("Received date", value=pd.to_datetime(stock_loaded["received_date"]).date() if (stock_loaded and stock_loaded.get("received_date")) else date.today(), key=f"rec_date{sk}", format="DD-MM-YYYY")
                with c2: location = st.text_input("Location", value=str(stock_loaded["location"]) if (stock_loaded and stock_loaded.get("location")) else CITY, key=f"rec_loc{sk}")
                with c3: selected_po = st.selectbox("Link to Purchase Order (Optional)", po_options, index=default_po_idx, key=f"rec_po{sk}")
                with c4: rec_discount_pct = st.number_input("Overall Discount (%)", min_value=0.0, max_value=100.0, value=default_rec_disc, step=0.5, format="%.2f", key=f"rec_disc{sk}")

                items_map = {itm["code"]: itm for itm in stock_loaded["items"] if isinstance(itm, dict) and "code" in itm} if stock_loaded and stock_loaded.get("items") and isinstance(stock_loaded["items"], list) else {}
                grid_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost Price (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Received": int(items_map[code]["rec"]) if (code in items_map and items_map[code].get("rec") is not None) else 0, "Damaged": int(items_map[code]["dam"]) if (code in items_map and items_map[code].get("dam") is not None) else 0} for code in FLAVOR_CODES]

                pass
                stock_edited = st.data_editor(pd.DataFrame(grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost Price (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Received": st.column_config.NumberColumn(min_value=0, step=1, format="%d"), "Damaged": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, row_height=28, key=f"db_stock_editor{sk}")

                tot_received, tot_damaged = int(stock_edited["Received"].sum()), int(stock_edited["Damaged"].sum())
                gross_cost_val = float(sum(stock_edited["Received"] * stock_edited["Unit Cost Price (₹)"]))
                rec_discount_amount = gross_cost_val * (rec_discount_pct / 100.0)
                net_cost_val = gross_cost_val - rec_discount_amount

                s_col1, s_col2, s_col3, s_col4 = st.columns(4, gap="small")
                s_col1.metric("Total Received", f"{tot_received} units"); s_col2.metric("Total Damaged", f"{tot_damaged} units"); s_col3.metric("Gross Cost", f"₹{gross_cost_val:,.2f}"); s_col4.metric(f"Net Cost ({rec_discount_pct:.1f}% off)", f"₹{net_cost_val:,.2f}")

                c5, c6, c7, c8 = st.columns(4, gap="small")
                with c5: payment_amount = st.number_input("Payment amount (₹)", min_value=0.0, value=float(stock_loaded["payment_amount"]) if (stock_loaded and stock_loaded.get("payment_amount") is not None) else float(net_cost_val), step=10.0, key=f"db_rec_pay{sk}")
                with c6: payment_status = st.selectbox("Payment status", PAYMENT_STATUSES, index=PAYMENT_STATUSES.index(stock_loaded["payment_status"]) if (stock_loaded and stock_loaded.get("payment_status") in PAYMENT_STATUSES) else 0, key=f"db_rec_status{sk}")
                with c7: payment_details = st.text_input("Payment details (optional)", value=str(stock_loaded["payment_details"]) if (stock_loaded and stock_loaded.get("payment_details")) else "", key=f"db_rec_pdet{sk}")
                with c8: notes = st.text_input("Notes (optional)", value=clean_rec_notes, key=f"db_rec_notes{sk}")

                chk_c1, chk_c2 = st.columns(2, gap="small")
                with chk_c1:
                    has_payment_date = st.checkbox("Add payment date", value=bool(stock_loaded and stock_loaded.get("payment_date")), key=f"db_rec_has_pdate{sk}")
                    payment_date = st.date_input("Payment date", value=pd.to_datetime(stock_loaded["payment_date"]).date() if (stock_loaded and stock_loaded.get("payment_date")) else date.today(), key=f"db_rec_pdate{sk}", format="DD-MM-YYYY") if has_payment_date else None
                with chk_c2:
                    has_dam_ret = st.checkbox("Damaged items were returned", value=bool(stock_loaded and stock_loaded.get("damaged_returned_on")), key=f"db_rec_has_dam{sk}")
                    damaged_returned_on = st.date_input("Damaged returned date", value=pd.to_datetime(stock_loaded["damaged_returned_on"]).date() if (stock_loaded and stock_loaded.get("damaged_returned_on")) else date.today(), key=f"db_rec_damdate{sk}", format="DD-MM-YYYY") if has_dam_ret else None

                if st.session_state.get("_sr_deleted_msg"):
                    st.success(st.session_state.pop("_sr_deleted_msg"))

                if loaded_id:
                    sr_btn_c1, sr_btn_c2, _ = st.columns([1.3, 1.3, 2.4], gap="small")
                    with sr_btn_c1:
                        save_sr_clicked = st.button("💾 Update delivery entry", type="primary", use_container_width=False, key=f"btn_upd_sr_{loaded_id}")
                    with sr_btn_c2:
                        if st.button("🗑️ Delete delivery entry", use_container_width=False, key=f"btn_del_sr_{loaded_id}"):
                            confirm_delete_stock_received_modal(stock_loaded)
                else:
                    save_sr_clicked = st.button("💾 Save stock received", type="primary", use_container_width=False, key="btn_save_new_sr")

                if save_sr_clicked:
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
                            st.cache_data.clear()
                            show_success_modal(f"Stock delivery #{rec_id} saved successfully! Logged {tot_received} units (Net Cost: ₹{net_cost_val:,.2f}).")
                        except Exception as e: st.error(f"Could not save to database: {e}")
            else:
                if not past_receipts:
                    st.info("No stock received records found.")
                else:
                    chronological_receipts = list(reversed(past_receipts))

                    receipts_by_month = {}
                    for r in chronological_receipts:
                        dt = pd.to_datetime(r["received_date"]).date() if r.get("received_date") else date.today()
                        month_key = dt.strftime("%B %Y")
                        if month_key not in receipts_by_month:
                            receipts_by_month[month_key] = []
                        receipts_by_month[month_key].append((dt, r))

                    sorted_months = sorted(receipts_by_month.keys(), key=lambda m: datetime.strptime(m, "%B %Y"))
                    loc_label = "All Locations" if get_active_location_filter() == "ALL" else get_active_location_filter()

                    monthly_sections = []
                    overall_units_all_months = 0
                    overall_cost_all_months = 0.0

                    for m_name in sorted_months:
                        m_receipts = receipts_by_month[m_name]
                        date_label_counts = {}
                        receipt_columns = []
                        month_total_units = 0
                        month_total_cost = 0.0

                        for dt, r in m_receipts:
                            base_dt = dt.strftime("%d-%b-%y")
                            date_label_counts[base_dt] = date_label_counts.get(base_dt, 0) + 1
                            col_label = base_dt if date_label_counts[base_dt] == 1 else f"{base_dt} ({date_label_counts[base_dt]})"

                            raw_items = r.get("items") if isinstance(r.get("items"), list) else []
                            qty_by_code = {}
                            gross_cost = 0.0
                            tot_units = 0
                            for itm in raw_items:
                                if not isinstance(itm, dict) or not itm.get("code"):
                                    continue
                                c = str(itm["code"]).strip()
                                rec_u = int(itm.get("rec") or 0)
                                unit_cp = float(
                                    itm.get("cost")
                                    if itm.get("cost") is not None
                                    else FLAVOR_MAP.get(c, {}).get("cost_price", 0.0)
                                )
                                qty_by_code[c] = qty_by_code.get(c, 0) + rec_u
                                tot_units += rec_u
                                gross_cost += rec_u * unit_cp

                            month_total_units += tot_units
                            month_total_cost += gross_cost

                            receipt_columns.append({
                                "col_label": col_label,
                                "qty_by_code": qty_by_code,
                                "total_units": tot_units,
                                "gross_cost": gross_cost,
                            })

                        overall_units_all_months += month_total_units
                        overall_cost_all_months += month_total_cost

                        matrix_cols = ["Flavour"] + [rc["col_label"] for rc in receipt_columns]
                        matrix_rows = []
                        for code in FLAVOR_CODES:
                            row_dict = {"Flavour": FLAVOR_MAP[code]["name"]}
                            for rc in receipt_columns:
                                qty = int(rc["qty_by_code"].get(code, 0))
                                row_dict[rc["col_label"]] = f"{qty:,}" if qty > 0 else "0"
                            matrix_rows.append(row_dict)

                        tot_units_row = {"Flavour": "Total Units"}
                        tot_cost_row_ui = {"Flavour": "Total Cost (Rs.)"}
                        tot_cost_row_pdf = {"Flavour": "Total Cost (Rs.)"}
                        for rc in receipt_columns:
                            tot_units_row[rc["col_label"]] = f"{int(rc['total_units']):,}"
                            tot_cost_row_ui[rc["col_label"]] = f"₹{rc['gross_cost']:,.0f}"
                            tot_cost_row_pdf[rc["col_label"]] = f"{rc['gross_cost']:,.0f}"

                        ui_rows = matrix_rows + [tot_units_row, tot_cost_row_ui]
                        pdf_rows = matrix_rows + [tot_units_row, tot_cost_row_pdf]

                        monthly_sections.append({
                            "month_name": m_name,
                            "matrix_cols": matrix_cols,
                            "ui_rows": ui_rows,
                            "pdf_rows": pdf_rows,
                            "month_total_units": month_total_units,
                            "month_total_cost": month_total_cost,
                        })

                    # 1. Top Overall Units & Overall Cost (So Far) + PDF Download Button
                    top_k1, top_k2, top_k3 = st.columns([1.8, 1.8, 1.4], gap="small", vertical_alignment="center")
                    with top_k1:
                        st.metric("📦 Overall Units Received (So Far)", f"{overall_units_all_months:,} units")
                    with top_k2:
                        st.metric("💰 Overall Gross Cost (So Far)", f"₹{overall_cost_all_months:,.0f}")
                    with top_k3:
                        if REPORTLAB_AVAILABLE:
                            pdf_bytes = generate_stock_received_report_pdf(
                                monthly_sections,
                                overall_units_all_months,
                                overall_cost_all_months,
                                location_label=loc_label,
                            )
                            if pdf_bytes:
                                st.download_button(
                                    label="📥 Download PDF Report",
                                    data=pdf_bytes,
                                    file_name=f"Stock_Received_Report_{loc_label.replace(' ', '_')}_{date.today().strftime('%Y%m%d')}.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    use_container_width=True,
                                )
                        else:
                            st.warning("Install `reportlab` for PDF export.")

                    st.markdown("---")

                    # 2. Render each month's table + 2 summary boxes below each month's table
                    for sec in monthly_sections:
                        m_name = sec["month_name"]
                        matrix_cols = sec["matrix_cols"]
                        ui_rows = sec["ui_rows"]
                        m_units = sec["month_total_units"]
                        m_cost = sec["month_total_cost"]

                        st.markdown(f"#### 📅 {m_name}")

                        th_cells = "".join(
                            f"<th style='text-align:{'left' if i == 0 else 'center'};'>{escape(col)}</th>"
                            for i, col in enumerate(matrix_cols)
                        )
                        body_trs = []
                        for r in ui_rows:
                            is_units_tot = r["Flavour"] == "Total Units"
                            is_cost_tot = r["Flavour"] == "Total Cost (Rs.)"
                            tr_class = "sr-total-units" if is_units_tot else ("sr-total-cost" if is_cost_tot else "")
                            tds = []
                            for c_idx, col in enumerate(matrix_cols):
                                val = str(r.get(col, ""))
                                align = "left" if c_idx == 0 else "center"
                                tds.append(f"<td style='text-align:{align};'>{escape(val)}</td>")
                            body_trs.append(f"<tr class='{tr_class}'>{''.join(tds)}</tr>")

                        st.html(
                            f"""
                            <style>
                            .sr-matrix-wrap {{
                                width: 100%;
                                overflow-x: auto;
                                margin-top: 4px;
                                margin-bottom: 10px;
                                border: 1.5px solid #BFDBFE;
                                border-radius: 8px;
                                background: #FFFFFF;
                                box-shadow: 0 2px 5px rgba(0,0,0,0.04);
                            }}
                            table.sr-matrix-tbl {{
                                width: 100%;
                                border-collapse: collapse;
                                font-family: 'Manrope', sans-serif;
                                font-size: 13px;
                            }}
                            .sr-matrix-tbl th, .sr-matrix-tbl td {{
                                border: 1px solid #E2E8F0;
                                padding: 7px 10px;
                                white-space: nowrap;
                            }}
                            .sr-matrix-tbl thead th {{
                                background: #BFDBFE;
                                color: #111111;
                                font-weight: 800;
                                font-size: 13px;
                            }}
                            .sr-matrix-tbl tbody td:first-child {{
                                font-weight: 700;
                                color: #1E2252;
                                background: #F8FAFC;
                            }}
                            .sr-matrix-tbl tbody tr:nth-child(even):not(.sr-total-units):not(.sr-total-cost) td:not(:first-child) {{
                                background: #F8FAFC;
                            }}
                            .sr-matrix-tbl tr.sr-total-units td {{
                                background: #EFF6FF !important;
                                color: #1E2252 !important;
                                font-weight: 900 !important;
                                border-top: 2px solid #B47A2B !important;
                            }}
                            .sr-matrix-tbl tr.sr-total-cost td {{
                                background: #ECFDF5 !important;
                                color: #047857 !important;
                                font-weight: 900 !important;
                                border-top: 1.5px solid #6EE7B7 !important;
                            }}
                            .sr-month-boxes {{
                                display: grid;
                                grid-template-columns: 1fr 1fr;
                                gap: 12px;
                                margin-bottom: 22px;
                                font-family: 'Manrope', sans-serif;
                            }}
                            .sr-month-box-units {{
                                background: #EFF6FF;
                                border: 1.5px solid #93C5FD;
                                border-radius: 8px;
                                padding: 10px 14px;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                            }}
                            .sr-month-box-cost {{
                                background: #ECFDF5;
                                border: 1.5px solid #6EE7B7;
                                border-radius: 8px;
                                padding: 10px 14px;
                                display: flex;
                                justify-content: space-between;
                                align-items: center;
                            }}
                            .sr-box-lbl {{
                                font-size: 12px;
                                font-weight: 800;
                                color: #475569;
                                text-transform: uppercase;
                                letter-spacing: 0.02em;
                            }}
                            .sr-box-val-u {{
                                font-size: 16px;
                                font-weight: 900;
                                color: #1E2252;
                            }}
                            .sr-box-val-c {{
                                font-size: 16px;
                                font-weight: 900;
                                color: #047857;
                            }}
                            </style>
                            <div class="sr-matrix-wrap">
                                <table class="sr-matrix-tbl">
                                   <thead><tr>{th_cells}</tr></thead>
                                   <tbody>{''.join(body_trs)}</tbody>
                                </table>
                            </div>
                            <div class="sr-month-boxes">
                                <div class="sr-month-box-units">
                                    <span class="sr-box-lbl">📦 {escape(m_name)} — Overall Units</span>
                                    <span class="sr-box-val-u">{m_units:,} units</span>
                                </div>
                                <div class="sr-month-box-cost">
                                    <span class="sr-box-lbl" style="color:#047857;">💰 {escape(m_name)} — Overall Cost</span>
                                    <span class="sr-box-val-c">₹{m_cost:,.0f}</span>
                                </div>
                            </div>
                            """
                        )

        elif freezer_tab_choice == "Stock Audit (Physical Count)":
            pass

            if st.session_state.get("stock_audit_mode") == "View Last Audit":
                st.session_state["stock_audit_mode"] = "View / Edit Past Audit"
            audit_mode = st.radio(
                "Audit Action",
                ["Log New Audit", "View / Edit Past Audit"],
                horizontal=True,
                key="stock_audit_mode"
            )

            def audit_calc_col(code):
                return f"{str(code).lower()}_calc_units"

            def audit_variance_col(code):
                return f"{str(code).lower()}_variance_units"

            def audit_snapshot_available(audit_row):
                return any(
                    pd.notna(audit_row.get(audit_calc_col(code)))
                    for code in FLAVOR_CODES
                )

            def saved_audit_snapshot_map(audit_row):
                return {
                    code: int(_num(audit_row.get(audit_calc_col(code), 0)))
                    for code in FLAVOR_CODES
                }

            def display_saved_audit_snapshot(audit_row, key_prefix="saved_audit"):
                has_snapshot = audit_snapshot_available(audit_row)
                physical_map = {
                    code: int(_num(audit_row.get(FLAVOR_MAP[code]["audit_col"], 0)))
                    for code in FLAVOR_CODES
                }

                if not has_snapshot:
                    st.warning(
                        "Calculated stock and variance were not stored for this older audit. "
                        "New audits will preserve the exact calculated-stock snapshot used at submission."
                    )
                    physical_df = pd.DataFrame([
                        {
                            "Flavour": FLAVOR_MAP[code]["name"],
                            "Physical Count": physical_map[code],
                        }
                        for code in FLAVOR_CODES
                    ])
                    st.dataframe(physical_df, hide_index=True, use_container_width=True)
                    return

                calc_map = saved_audit_snapshot_map(audit_row)
                variance_map = {
                    code: int(_num(audit_row.get(audit_variance_col(code), physical_map[code] - calc_map[code])))
                    for code in FLAVOR_CODES
                }

                snapshot_df = pd.DataFrame([
                    {
                        "Flavour": FLAVOR_MAP[code]["name"],
                        "Calculated Stock": calc_map[code],
                        "Physical Count": physical_map[code],
                        "Variance": variance_map[code],
                    }
                    for code in FLAVOR_CODES
                ])

                total_calc = int(_num(audit_row.get("total_calc_units")))
                if pd.isna(audit_row.get("total_calc_units")):
                    total_calc = int(sum(calc_map.values()))

                total_physical = int(sum(physical_map.values()))
                total_variance = int(_num(audit_row.get("total_variance_units")))
                if pd.isna(audit_row.get("total_variance_units")):
                    total_variance = total_physical - total_calc

                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("Saved Calculated Stock", f"{total_calc:,}")
                tc2.metric("Physical Count", f"{total_physical:,}")
                tc3.metric("Saved Variance", f"{total_variance:+,}")

                def _variance_style(value):
                    try:
                        return "color: #19692C; font-weight: 800;" if int(value) == 0 else "color: #C43D17; font-weight: 800;"
                    except Exception:
                        return ""

                st.dataframe(
                    snapshot_df.style.map(_variance_style, subset=["Variance"]),
                    hide_index=True,
                    use_container_width=True,
                )

            def get_system_stock_as_of(target_date):
                """
                Reconstruct system stock for a past audit by reversing movements from today's
                system stock back to that audit date.

                Historical system stock =
                    today's system stock
                    + cart additions from (audit date + 1) through today
                    + stock removals from (audit date + 1) through today
                    - stock received from audit date through today

                This keeps the historical view aligned to the same movement logic used by the
                current freezer stock calculation.
                """
                stock_map = {code: 0 for code in FLAVOR_CODES}
                if db_conn is None:
                    return stock_map

                try:
                    current_df = get_db_freezer_stock()
                    current_map = (
                        dict(zip(current_df["code"], current_df["Units in freezer"]))
                        if not current_df.empty else {}
                    )

                    movement_start = target_date + timedelta(days=1)
                    received_start = target_date

                    added_after_df = db_conn.query(
                        """
                        SELECT i.flavor_code, COALESCE(SUM(i.added_units), 0) AS total_added
                        FROM daily_cart_items i
                        JOIN daily_cart_entries e ON i.daily_entry_id = e.id
                        WHERE e.entry_date >= :start_dt
                          AND e.entry_date <= CURRENT_DATE
                        GROUP BY i.flavor_code;
                        """,
                        params={"start_dt": movement_start},
                        ttl="60s"
                    )
                    added_after = (
                        dict(zip(added_after_df["flavor_code"], added_after_df["total_added"]))
                        if not added_after_df.empty else {}
                    )

                    received_after_df = db_conn.query(
                        """
                        SELECT ri.flavor_code, COALESCE(SUM(ri.received_units), 0) AS total_received
                        FROM stock_received_items ri
                        JOIN stock_received r ON ri.received_id = r.id
                        WHERE r.received_date >= :start_dt
                          AND r.received_date <= CURRENT_DATE
                        GROUP BY ri.flavor_code;
                        """,
                        params={"start_dt": received_start},
                        ttl="60s"
                    )
                    received_after = (
                        dict(zip(received_after_df["flavor_code"], received_after_df["total_received"]))
                        if not received_after_df.empty else {}
                    )

                    removed_after_df = db_conn.query(
                        """
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
                        FROM stock_removed
                        WHERE removal_date >= :start_dt
                          AND removal_date <= CURRENT_DATE;
                        """,
                        params={"start_dt": movement_start},
                        ttl="60s"
                    )
                    removed_after = (
                        {
                            code: int(_num(removed_after_df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0)))
                            for code in FLAVOR_CODES
                        }
                        if not removed_after_df.empty
                        else {code: 0 for code in FLAVOR_CODES}
                    )

                    frm_cart_after = get_db_cart_to_freezer_map(active_loc=get_active_location_filter(), after_date=target_date)

                    for code in FLAVOR_CODES:
                        stock_map[code] = (
                            int(_num(current_map.get(code, 0)))
                            + int(_num(added_after.get(code, 0)))
                            + int(_num(removed_after.get(code, 0)))
                            - int(_num(received_after.get(code, 0)))
                            - int(_num(frm_cart_after.get(code, 0)))
                        )

                except Exception:
                    pass

                return stock_map

            def show_audit_totals(audit_df):
                total_system = int(pd.to_numeric(audit_df["Current System Stock"], errors="coerce").fillna(0).sum())
                total_physical = int(pd.to_numeric(audit_df["Physical Counted Units"], errors="coerce").fillna(0).sum())
                total_variance = total_physical - total_system
                tc1, tc2, tc3 = st.columns(3)
                tc1.metric("Total Current System Stock", f"{total_system:,}")
                tc2.metric("Total Physical Counted Units", f"{total_physical:,}")
                tc3.metric("Total Variance", f"{total_variance:+,}")
                return total_system, total_physical

            if audit_mode == "Log New Audit":
                aud_c1, aud_c2, aud_c3, aud_c4 = st.columns(4)
                with aud_c1:
                    audit_date = st.date_input("Audit date", value=date.today(), key="audit_dt_entry", format="DD-MM-YYYY")
                with aud_c2:
                    audit_time = st.time_input(
                        "Audit time",
                        value=datetime.now().time().replace(second=0, microsecond=0),
                        key="audit_time_entry",
                    )
                with aud_c3:
                    audit_location = st.text_input("Freezer / Location", value=CITY, key="audit_loc_entry")
                with aud_c4:
                    audited_by = st.text_input("Audited by", value="Admin", key="audit_by_entry")

                # Use the same last-physical-audit movement logic as Freezer Analysis.
                # For the very first audit (no prior physical audit), fall back to the
                # all-movements freezer calculation.
                sys_stock_map = get_physical_current_stock_map()
                if not sys_stock_map:
                    freezer_curr_df = get_db_freezer_stock()
                    sys_stock_map = (
                        dict(zip(freezer_curr_df["code"], freezer_curr_df["Units in freezer"]))
                        if not freezer_curr_df.empty else {}
                    )

                audit_grid = [
                    {
                        "Flavour": FLAVOR_MAP[code]["name"],
                        "Code": code,
                        "Current System Stock": int(sys_stock_map.get(code, 0)),
                        "Physical Counted Units": int(sys_stock_map.get(code, 0))
                    }
                    for code in FLAVOR_CODES
                ]
                audit_edited = st.data_editor(
                    pd.DataFrame(audit_grid),
                    column_config={
                        "Flavour": st.column_config.TextColumn(disabled=True),
                        "Code": st.column_config.TextColumn(disabled=True),
                        "Current System Stock": st.column_config.NumberColumn(disabled=True, format="%d"),
                        "Physical Counted Units": st.column_config.NumberColumn(min_value=0, step=1, format="%d")
                    },
                    hide_index=True,
                    use_container_width=True,
                    row_height=28,
                    key="audit_editor_grid"
                )
                show_audit_totals(audit_edited)
                audit_remarks = st.text_input("Audit remarks / observation notes", key="audit_remarks_input")

                if st.button("💾 Save Stock Audit", type="primary", use_container_width=False, key="submit_new_stock_audit"):
                    try:
                        phys_by_code = {row["Code"]: int(row["Physical Counted Units"]) for _, row in audit_edited.iterrows()}
                        calc_by_code = {row["Code"]: int(row["Current System Stock"]) for _, row in audit_edited.iterrows()}
                        variance_by_code = {
                            code: int(phys_by_code.get(code, 0)) - int(calc_by_code.get(code, 0))
                            for code in FLAVOR_CODES
                        }
                        total_calc_units = int(sum(calc_by_code.values()))
                        total_variance_units = int(sum(variance_by_code.values()))

                        with db_conn.session as s:
                            res = s.execute(
                                text("""
                                    INSERT INTO stock_audits_wide
                                    (
                                        audit_date, audit_time, location, audited_by, remarks,
                                        ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                                        ml_calc_units, mm_calc_units, ps_calc_units, mn_calc_units, kb_calc_units,
                                        bm_calc_units, sg_calc_units, ch_calc_units, ra_calc_units,
                                        ml_variance_units, mm_variance_units, ps_variance_units, mn_variance_units, kb_variance_units,
                                        bm_variance_units, sg_variance_units, ch_variance_units, ra_variance_units,
                                        total_calc_units, total_variance_units
                                    )
                                    VALUES
                                    (
                                        :adt, :atm, :loc, :by, :rem,
                                        :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra,
                                        :ml_calc, :mm_calc, :ps_calc, :mn_calc, :kb_calc,
                                        :bm_calc, :sg_calc, :ch_calc, :ra_calc,
                                        :ml_var, :mm_var, :ps_var, :mn_var, :kb_var,
                                        :bm_var, :sg_var, :ch_var, :ra_var,
                                        :total_calc, :total_var
                                    )
                                    RETURNING audit_id;
                                """),
                                {
                                    "adt": audit_date, "atm": audit_time, "loc": audit_location, "by": audited_by, "rem": audit_remarks,
                                    "ml": phys_by_code.get("ML", 0), "mm": phys_by_code.get("MM", 0),
                                    "ps": phys_by_code.get("PS", 0), "mn": phys_by_code.get("MN", 0),
                                    "kb": phys_by_code.get("KB", 0), "bm": phys_by_code.get("BM", 0),
                                    "sg": phys_by_code.get("SG", 0), "ch": phys_by_code.get("CH", 0),
                                    "ra": phys_by_code.get("RA", 0),
                                    "ml_calc": calc_by_code.get("ML", 0), "mm_calc": calc_by_code.get("MM", 0),
                                    "ps_calc": calc_by_code.get("PS", 0), "mn_calc": calc_by_code.get("MN", 0),
                                    "kb_calc": calc_by_code.get("KB", 0), "bm_calc": calc_by_code.get("BM", 0),
                                    "sg_calc": calc_by_code.get("SG", 0), "ch_calc": calc_by_code.get("CH", 0),
                                    "ra_calc": calc_by_code.get("RA", 0),
                                    "ml_var": variance_by_code.get("ML", 0), "mm_var": variance_by_code.get("MM", 0),
                                    "ps_var": variance_by_code.get("PS", 0), "mn_var": variance_by_code.get("MN", 0),
                                    "kb_var": variance_by_code.get("KB", 0), "bm_var": variance_by_code.get("BM", 0),
                                    "sg_var": variance_by_code.get("SG", 0), "ch_var": variance_by_code.get("CH", 0),
                                    "ra_var": variance_by_code.get("RA", 0),
                                    "total_calc": total_calc_units,
                                    "total_var": total_variance_units,
                                }
                            )
                            aid = res.scalar()
                            s.commit()
                        st.cache_data.clear()
                        show_success_modal(f"Stock Audit #{aid} logged successfully!")
                    except Exception as e:
                        st.error(f"Could not save audit to database: {e}")

            else:
                try:
                    audit_history_df = db_conn.query(
                        """
                        SELECT audit_id, audit_date, audit_time, location, audited_by, remarks,
                               ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units,
                               ml_calc_units, mm_calc_units, ps_calc_units, mn_calc_units, kb_calc_units,
                               bm_calc_units, sg_calc_units, ch_calc_units, ra_calc_units,
                               ml_variance_units, mm_variance_units, ps_variance_units, mn_variance_units, kb_variance_units,
                               bm_variance_units, sg_variance_units, ch_variance_units, ra_variance_units,
                               total_calc_units, total_variance_units
                        FROM stock_audits_wide
                        WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
                        ORDER BY audit_date DESC, audit_id DESC;
                        """,
                        params={"active_loc": get_active_location_filter()},
                        ttl="60s"
                    )
                except Exception as e:
                    audit_history_df = pd.DataFrame()
                    st.error(f"Could not load audit history: {e}")

                if audit_history_df.empty:
                    st.info("No past stock audits found.")
                else:
                    audit_history_df = audit_history_df.copy()
                    audit_history_df["audit_date_dt"] = pd.to_datetime(audit_history_df["audit_date"]).dt.date
                    audit_history_df["selector"] = audit_history_df.apply(
                        lambda r: (
                            f"Audit #{int(r['audit_id'])} — {r['audit_date_dt'].strftime('%d-%b-%Y')}"
                            f"{(' ' + str(r.get('audit_time'))[:5]) if pd.notna(r.get('audit_time')) and str(r.get('audit_time')).strip() else ''}"
                            f" — {str(r.get('audited_by') or 'N/A')}"
                        ),
                        axis=1
                    )

                    selected_audit_label = st.selectbox(
                        "Select Past Audit",
                        audit_history_df["selector"].tolist(),
                        key="past_audit_selector"
                    )
                    loaded_audit = audit_history_df[audit_history_df["selector"] == selected_audit_label].iloc[0]
                    loaded_audit_id = int(loaded_audit["audit_id"])
                    loaded_audit_date = loaded_audit["audit_date_dt"]

                    loaded_audit_time_raw = loaded_audit.get("audit_time")
                    if pd.notna(loaded_audit_time_raw) and str(loaded_audit_time_raw).strip():
                        try:
                            loaded_audit_time = datetime.strptime(str(loaded_audit_time_raw).split(".")[0], "%H:%M:%S").time()
                        except Exception:
                            loaded_audit_time = datetime.now().time().replace(second=0, microsecond=0)
                    else:
                        loaded_audit_time = datetime.now().time().replace(second=0, microsecond=0)

                    eac1, eac2, eac3, eac4 = st.columns(4)
                    with eac1:
                        edit_audit_date = st.date_input(
                            "Audit date",
                            value=loaded_audit_date,
                            key=f"edit_audit_date_{loaded_audit_id}",
                            format="DD-MM-YYYY"
                        )
                    with eac2:
                        edit_audit_time = st.time_input(
                            "Audit time",
                            value=loaded_audit_time,
                            key=f"edit_audit_time_{loaded_audit_id}",
                        )
                    with eac3:
                        edit_audit_location = st.text_input(
                            "Freezer / Location",
                            value=str(loaded_audit.get("location") or CITY),
                            key=f"edit_audit_loc_{loaded_audit_id}"
                        )
                    with eac4:
                        edit_audited_by = st.text_input(
                            "Audited by",
                            value=str(loaded_audit.get("audited_by") or "Admin"),
                            key=f"edit_audit_by_{loaded_audit_id}"
                        )

                    if audit_snapshot_available(loaded_audit):
                        historical_system_map = saved_audit_snapshot_map(loaded_audit)
                        pass
                    else:
                        historical_system_map = get_system_stock_as_of(edit_audit_date)
                        pass

                    edit_audit_grid = []
                    for code in FLAVOR_CODES:
                        audit_col = FLAVOR_MAP[code]["audit_col"]
                        edit_audit_grid.append({
                            "Flavour": FLAVOR_MAP[code]["name"],
                            "Code": code,
                            "Current System Stock": int(historical_system_map.get(code, 0)),
                            "Physical Counted Units": int(_num(loaded_audit.get(audit_col, 0)))
                        })

                    edited_past_audit = st.data_editor(
                        pd.DataFrame(edit_audit_grid),
                        column_config={
                            "Flavour": st.column_config.TextColumn(disabled=True),
                            "Code": st.column_config.TextColumn(disabled=True),
                            "Current System Stock": st.column_config.NumberColumn(disabled=True, format="%d"),
                            "Physical Counted Units": st.column_config.NumberColumn(min_value=0, step=1, format="%d")
                        },
                        hide_index=True,
                        use_container_width=True,
                        row_height=28,
                        key=f"past_audit_editor_{loaded_audit_id}"
                    )
                    show_audit_totals(edited_past_audit)

                    edit_audit_remarks = st.text_input(
                        "Audit remarks / observation notes",
                        value=str(loaded_audit.get("remarks") or ""),
                        key=f"edit_audit_remarks_{loaded_audit_id}"
                    )

                    ab1, ab2, _ab_sp = st.columns([1.2, 1.0, 2.0], gap="small")
                    with ab2:
                        if st.button("🗑️ Delete Stock Audit", type="secondary", use_container_width=True, key=f"delete_audit_btn_{loaded_audit_id}"):
                            confirm_delete_stock_audit_modal(loaded_audit)
                    with ab1:
                        _do_update_audit = st.button("💾 Update Stock Audit", type="primary", use_container_width=True, key=f"update_audit_{loaded_audit_id}")
                    if _do_update_audit:
                        try:
                            edited_phys_by_code = {
                                row["Code"]: int(row["Physical Counted Units"])
                                for _, row in edited_past_audit.iterrows()
                            }
                            edited_calc_by_code = {
                                row["Code"]: int(row["Current System Stock"])
                                for _, row in edited_past_audit.iterrows()
                            }
                            edited_variance_by_code = {
                                code: int(edited_phys_by_code.get(code, 0)) - int(edited_calc_by_code.get(code, 0))
                                for code in FLAVOR_CODES
                            }
                            edited_total_calc = int(sum(edited_calc_by_code.values()))
                            edited_total_variance = int(sum(edited_variance_by_code.values()))

                            with db_conn.session as s:
                                s.execute(
                                    text("""
                                        UPDATE stock_audits_wide
                                        SET audit_date = :adt,
                                            audit_time = :atm,
                                            location = :loc,
                                            audited_by = :by,
                                            remarks = :rem,
                                            ml_units = :ml,
                                            mm_units = :mm,
                                            ps_units = :ps,
                                            mn_units = :mn,
                                            kb_units = :kb,
                                            bm_units = :bm,
                                            sg_units = :sg,
                                            ch_units = :ch,
                                            ra_units = :ra,
                                            ml_calc_units = :ml_calc,
                                            mm_calc_units = :mm_calc,
                                            ps_calc_units = :ps_calc,
                                            mn_calc_units = :mn_calc,
                                            kb_calc_units = :kb_calc,
                                            bm_calc_units = :bm_calc,
                                            sg_calc_units = :sg_calc,
                                            ch_calc_units = :ch_calc,
                                            ra_calc_units = :ra_calc,
                                            ml_variance_units = :ml_var,
                                            mm_variance_units = :mm_var,
                                            ps_variance_units = :ps_var,
                                            mn_variance_units = :mn_var,
                                            kb_variance_units = :kb_var,
                                            bm_variance_units = :bm_var,
                                            sg_variance_units = :sg_var,
                                            ch_variance_units = :ch_var,
                                            ra_variance_units = :ra_var,
                                            total_calc_units = :total_calc,
                                            total_variance_units = :total_var
                                        WHERE audit_id = :aid;
                                    """),
                                    {
                                        "aid": loaded_audit_id,
                                        "adt": edit_audit_date,
                                        "atm": edit_audit_time,
                                        "loc": edit_audit_location,
                                        "by": edit_audited_by,
                                        "rem": edit_audit_remarks,
                                        "ml": edited_phys_by_code.get("ML", 0),
                                        "mm": edited_phys_by_code.get("MM", 0),
                                        "ps": edited_phys_by_code.get("PS", 0),
                                        "mn": edited_phys_by_code.get("MN", 0),
                                        "kb": edited_phys_by_code.get("KB", 0),
                                        "bm": edited_phys_by_code.get("BM", 0),
                                        "sg": edited_phys_by_code.get("SG", 0),
                                        "ch": edited_phys_by_code.get("CH", 0),
                                        "ra": edited_phys_by_code.get("RA", 0),
                                        "ml_calc": edited_calc_by_code.get("ML", 0),
                                        "mm_calc": edited_calc_by_code.get("MM", 0),
                                        "ps_calc": edited_calc_by_code.get("PS", 0),
                                        "mn_calc": edited_calc_by_code.get("MN", 0),
                                        "kb_calc": edited_calc_by_code.get("KB", 0),
                                        "bm_calc": edited_calc_by_code.get("BM", 0),
                                        "sg_calc": edited_calc_by_code.get("SG", 0),
                                        "ch_calc": edited_calc_by_code.get("CH", 0),
                                        "ra_calc": edited_calc_by_code.get("RA", 0),
                                        "ml_var": edited_variance_by_code.get("ML", 0),
                                        "mm_var": edited_variance_by_code.get("MM", 0),
                                        "ps_var": edited_variance_by_code.get("PS", 0),
                                        "mn_var": edited_variance_by_code.get("MN", 0),
                                        "kb_var": edited_variance_by_code.get("KB", 0),
                                        "bm_var": edited_variance_by_code.get("BM", 0),
                                        "sg_var": edited_variance_by_code.get("SG", 0),
                                        "ch_var": edited_variance_by_code.get("CH", 0),
                                        "ra_var": edited_variance_by_code.get("RA", 0),
                                        "total_calc": edited_total_calc,
                                        "total_var": edited_total_variance,
                                    }
                                )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"Stock Audit #{loaded_audit_id} updated successfully!")
                        except Exception as e:
                            st.error(f"Could not update stock audit: {e}")

    elif page == "Freezer Analysis" and user_role == "admin":
        st.subheader("Freezer Stock Analysis & Reorder Planner")
    
        ac1, ac2, ac3 = st.columns(3)
        with ac1: lookback_days = st.number_input("Sales Velocity Window (days)", min_value=3, max_value=90, value=14, step=1)
        with ac2: buffer_days = st.number_input("Safety Buffer Threshold (days)", min_value=0, max_value=14, value=3, step=1)
        with ac3: cover_days = st.number_input("Reorder Coverage Target (days)", min_value=1, max_value=30, value=7, step=1)

        try:
            today_fa = date.today()
            cutoff_fa = today_fa - timedelta(days=int(lookback_days) - 1)
            flavor_sales_df = load_db_flavor_sales(start_date=cutoff_fa, end_date=today_fa)
            sales_pace_map = dict(zip(flavor_sales_df["code"], flavor_sales_df["Units sold"])) if not flavor_sales_df.empty else {}

            active_loc_fa = get_active_location_filter()
            locs_for_fa = load_configured_locations_list(include_inactive=False) if active_loc_fa == "ALL" else [active_loc_fa]

            audit_map = {code: 0 for code in FLAVOR_CODES}
            rec_since_map = {code: 0 for code in FLAVOR_CODES}
            frm_cart_since_map = {code: 0 for code in FLAVOR_CODES}
            added_since_map = {code: 0 for code in FLAVOR_CODES}
            fzr_sale_since_map = {code: 0 for code in FLAVOR_CODES}
            rem_since_map = {code: 0 for code in FLAVOR_CODES}
            audit_date_labels = []

            for loc_c in locs_for_fa:
                loc_audit_df = db_conn.query(
                    "SELECT * FROM stock_audits_wide WHERE UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc ORDER BY audit_date DESC, audit_id DESC LIMIT 1;",
                    params={"loc": loc_c}, ttl="60s"
                )
                if not loc_audit_df.empty:
                    arow = loc_audit_df.iloc[0]
                    adt = pd.to_datetime(arow["audit_date"]).date()
                    anext = adt + timedelta(days=1)
                    audit_date_labels.append(f"{loc_c}: {adt.strftime('%d-%b-%y')}" if active_loc_fa == "ALL" else adt.strftime("%d-%b-%y"))
                    for code in FLAVOR_CODES:
                        audit_map[code] += int(arow.get(FLAVOR_MAP[code]["audit_col"], 0))

                    r_df = db_conn.query(
                        "SELECT ri.flavor_code, COALESCE(SUM(ri.received_units), 0) AS recv FROM stock_received_items ri JOIN stock_received r ON ri.received_id = r.id WHERE r.received_date >= :adate AND UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :loc GROUP BY ri.flavor_code;",
                        params={"adate": adt, "loc": loc_c}, ttl="60s"
                    )
                    for _, rr in r_df.iterrows():
                        c = str(rr["flavor_code"]).strip()
                        if c in rec_since_map:
                            rec_since_map[c] += int(rr["recv"] or 0)

                    fc_map_loc = get_db_cart_to_freezer_map(active_loc=loc_c, after_date=adt)
                    for code in FLAVOR_CODES:
                        frm_cart_since_map[code] += int(fc_map_loc.get(code, 0))

                    a_df = db_conn.query(
                        "SELECT i.flavor_code, COALESCE(SUM(i.added_units), 0) AS added FROM daily_cart_items i JOIN daily_cart_entries e ON i.daily_entry_id = e.id WHERE e.entry_date >= :anext AND UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc GROUP BY i.flavor_code;",
                        params={"anext": anext, "loc": loc_c}, ttl="60s"
                    )
                    for _, ar in a_df.iterrows():
                        c = str(ar["flavor_code"]).strip()
                        if c in added_since_map:
                            added_since_map[c] += int(ar["added"] or 0)

                    fz_df = db_conn.query(
                        f"SELECT i.flavor_code, COALESCE(SUM(i.sold_units), 0) AS fzr_sold FROM daily_cart_items i JOIN daily_cart_entries e ON i.daily_entry_id = e.id WHERE e.entry_date >= :anext AND UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc AND {is_freezer_cart_name_sql('e.cart_name')} GROUP BY i.flavor_code;",
                        params={"anext": anext, "loc": loc_c}, ttl="60s"
                    )
                    for _, fr in fz_df.iterrows():
                        c = str(fr["flavor_code"]).strip()
                        if c in fzr_sale_since_map:
                            fzr_sale_since_map[c] += int(fr["fzr_sold"] or 0)

                    rm_df = db_conn.query(
                        "SELECT COALESCE(SUM(ml_units),0) AS ml_units, COALESCE(SUM(mm_units),0) AS mm_units, COALESCE(SUM(ps_units),0) AS ps_units, COALESCE(SUM(mn_units),0) AS mn_units, COALESCE(SUM(kb_units),0) AS kb_units, COALESCE(SUM(bm_units),0) AS bm_units, COALESCE(SUM(sg_units),0) AS sg_units, COALESCE(SUM(ch_units),0) AS ch_units, COALESCE(SUM(ra_units),0) AS ra_units FROM stock_removed WHERE removal_date >= :adate AND UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc;",
                        params={"adate": adt, "loc": loc_c}, ttl="60s"
                    )
                    if not rm_df.empty:
                        for code in FLAVOR_CODES:
                            rem_since_map[code] += int(rm_df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0))
                else:
                    r_df = db_conn.query(
                        "SELECT ri.flavor_code, COALESCE(SUM(ri.received_units), 0) AS recv FROM stock_received_items ri JOIN stock_received r ON ri.received_id = r.id WHERE UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :loc GROUP BY ri.flavor_code;",
                        params={"loc": loc_c}, ttl="60s"
                    )
                    for _, rr in r_df.iterrows():
                        c = str(rr["flavor_code"]).strip()
                        if c in rec_since_map:
                            rec_since_map[c] += int(rr["recv"] or 0)

                    fc_map_loc = get_db_cart_to_freezer_map(active_loc=loc_c, after_date=None)
                    for code in FLAVOR_CODES:
                        frm_cart_since_map[code] += int(fc_map_loc.get(code, 0))

                    a_df = db_conn.query(
                        "SELECT i.flavor_code, COALESCE(SUM(i.added_units), 0) AS added FROM daily_cart_items i JOIN daily_cart_entries e ON i.daily_entry_id = e.id WHERE UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc GROUP BY i.flavor_code;",
                        params={"loc": loc_c}, ttl="60s"
                    )
                    for _, ar in a_df.iterrows():
                        c = str(ar["flavor_code"]).strip()
                        if c in added_since_map:
                            added_since_map[c] += int(ar["added"] or 0)

                    fz_df = db_conn.query(
                        f"SELECT i.flavor_code, COALESCE(SUM(i.sold_units), 0) AS fzr_sold FROM daily_cart_items i JOIN daily_cart_entries e ON i.daily_entry_id = e.id WHERE UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :loc AND {is_freezer_cart_name_sql('e.cart_name')} GROUP BY i.flavor_code;",
                        params={"loc": loc_c}, ttl="60s"
                    )
                    for _, fr in fz_df.iterrows():
                        c = str(fr["flavor_code"]).strip()
                        if c in fzr_sale_since_map:
                            fzr_sale_since_map[c] += int(fr["fzr_sold"] or 0)

                    rm_df = db_conn.query(
                        "SELECT COALESCE(SUM(ml_units),0) AS ml_units, COALESCE(SUM(mm_units),0) AS mm_units, COALESCE(SUM(ps_units),0) AS ps_units, COALESCE(SUM(mn_units),0) AS mn_units, COALESCE(SUM(kb_units),0) AS kb_units, COALESCE(SUM(bm_units),0) AS bm_units, COALESCE(SUM(sg_units),0) AS sg_units, COALESCE(SUM(ch_units),0) AS ch_units, COALESCE(SUM(ra_units),0) AS ra_units FROM stock_removed WHERE UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :loc;",
                        params={"loc": loc_c}, ttl="60s"
                    )
                    if not rm_df.empty:
                        for code in FLAVOR_CODES:
                            rem_since_map[code] += int(rm_df.iloc[0].get(FLAVOR_MAP[code]["audit_col"], 0))

            audit_date_str = " | ".join(audit_date_labels) if audit_date_labels else "No audits logged"
        except Exception as e:
            st.error(f"Could not load analysis transactions from database: {e}")
            sales_pace_map, audit_map, rec_since_map, frm_cart_since_map, added_since_map, fzr_sale_since_map, rem_since_map, audit_date_str = {}, {}, {}, {}, {}, {}, {}, "N/A"

        # --- TABLE 1: Physical-Base Current Stock Position ---
        st.markdown("---")
        st.markdown(f"### 1. Current Stock Position &nbsp; *(Per Last Audit Date: {audit_date_str})*")

        phys_base_rows = []
        tot_base_b, tot_rec_b, tot_frm_cart_b, tot_added_b, tot_fzr_b, tot_rem_b, tot_curr_b = 0, 0, 0, 0, 0, 0, 0
        tot_stock_value_cp = 0.0
        tot_stock_value_mrp = 0.0
        phys_curr_map = get_physical_current_stock_map()

        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            base_audit = audit_map.get(code, 0)
            rec_onward = int(rec_since_map.get(code, 0))
            frm_cart_onward = int(frm_cart_since_map.get(code, 0))
            added_onward = int(added_since_map.get(code, 0))
            fzr_sale_onward = int(fzr_sale_since_map.get(code, 0))
            removed_onward = int(rem_since_map.get(code, 0))
        
            current_physical_base_stock = base_audit + rec_onward + frm_cart_onward - added_onward - fzr_sale_onward - removed_onward
        
            tot_base_b += base_audit
            tot_rec_b += rec_onward
            tot_frm_cart_b += frm_cart_onward
            tot_added_b += added_onward
            tot_fzr_b += fzr_sale_onward
            tot_rem_b += removed_onward
            tot_curr_b += current_physical_base_stock
            stock_value_cp = float(current_physical_base_stock) * float(f_info["cost_price"])
            stock_value_mrp = float(current_physical_base_stock) * float(f_info["mrp"])
            stock_value_display = int(stock_value_cp + 0.5) if stock_value_cp >= 0 else int(stock_value_cp - 0.5)
            tot_stock_value_cp += stock_value_cp
            tot_stock_value_mrp += stock_value_mrp

            phys_base_rows.append({
                "Flavour": f_info["name"],
                "Audit": base_audit,
                "Recv": rec_onward,
                "Frm Cart": frm_cart_onward,
                "To Cart": added_onward,
                "FZR Sale": fzr_sale_onward,
                "Rem": removed_onward,
                "Current": current_physical_base_stock,
                "Value": stock_value_display
            })

        tot_stock_value_display = int(sum(int(r["Value"]) for r in phys_base_rows))
        tot_stock_value_mrp_display = int(tot_stock_value_mrp + 0.5) if tot_stock_value_mrp >= 0 else int(tot_stock_value_mrp - 0.5)

        # Render Boxed HTML Table with the 4 distinct grouped borders (without Value column):
        # [Audit], [Recv | Frm Cart], [To Cart | FZR Sale | Rem], [Current]
        fa_body_trs = []
        for r in phys_base_rows:
            fa_body_trs.append(
                f"""<tr>
                    <td style='text-align:left;font-weight:800;color:#1E2252;'>{escape(r['Flavour'])}</td>
                    <td class='fa-box-audit-td'>{r['Audit']:,}</td>
                    <td class='fa-box-in-left-td'>{r['Recv']:,}</td>
                    <td class='fa-box-in-right-td'>{r['Frm Cart']:,}</td>
                    <td class='fa-box-out-left-td'>{r['To Cart']:,}</td>
                    <td class='fa-box-out-mid-td'>{r['FZR Sale']:,}</td>
                    <td class='fa-box-out-right-td'>{r['Rem']:,}</td>
                    <td class='fa-box-cur-only-td'>{r['Current']:,}</td>
                </tr>"""
            )
        fa_body_trs.append(
            f"""<tr class='fa-total-row'>
                <td style='text-align:left;font-weight:900;color:#1E2252;'>🔥 OVERALL TOTAL</td>
                <td class='fa-box-audit-tot'>{tot_base_b:,}</td>
                <td class='fa-box-in-left-tot'>{tot_rec_b:,}</td>
                <td class='fa-box-in-right-tot'>{tot_frm_cart_b:,}</td>
                <td class='fa-box-out-left-tot'>{tot_added_b:,}</td>
                <td class='fa-box-out-mid-tot'>{tot_fzr_b:,}</td>
                <td class='fa-box-out-right-tot'>{tot_rem_b:,}</td>
                <td class='fa-box-cur-only-tot'>{tot_curr_b:,}</td>
            </tr>"""
        )
        st.markdown(
            f"""
            <div class='fa-boxed-table-wrap'>
                <table class='fa-boxed-table' style='table-layout:fixed;'>
                    <thead>
                        <tr>
                            <th style='text-align:left;width:22%;'>Flavour</th>
                            <th class='fa-box-audit-th' style='width:11%;'>Audit</th>
                            <th class='fa-box-in-left-th' style='width:11%;'>Recv</th>
                            <th class='fa-box-in-right-th' style='width:11%;'>-Cart</th>
                            <th class='fa-box-out-left-th' style='width:11%;'>+Cart</th>
                            <th class='fa-box-out-mid-th' style='width:11%;'>FZR Sale</th>
                            <th class='fa-box-out-right-th' style='width:11%;'>Rem</th>
                            <th class='fa-box-cur-only-th' style='width:12%;'>Current</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(fa_body_trs)}
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Supplier amount still outstanding for stock receipts explicitly marked Pending,
        # together with the units covered by those pending receipts.
        pending_stock_payment = 0.0
        pending_stock_units = 0
        try:
            pending_payment_df = db_conn.query(
                """
                SELECT
                    COALESCE((
                        SELECT SUM(r.payment_amount)
                        FROM stock_received r
                        WHERE LOWER(TRIM(COALESCE(r.payment_status, ''))) = 'pending'
                          AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :active_loc)
                    ), 0) AS pending_amount,
                    COALESCE((
                        SELECT SUM(i.received_units)
                        FROM stock_received_items i
                        JOIN stock_received r ON r.id = i.received_id
                        WHERE LOWER(TRIM(COALESCE(r.payment_status, ''))) = 'pending'
                          AND (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :active_loc)
                    ), 0) AS pending_units;
                """,
                params={"active_loc": get_active_location_filter()},
                ttl="60s"
            )
            if not pending_payment_df.empty:
                pending_stock_payment = float(_num(pending_payment_df.iloc[0].get("pending_amount")))
                pending_stock_units = int(round(_num(pending_payment_df.iloc[0].get("pending_units"))))
        except Exception:
            pending_stock_payment = 0.0
            pending_stock_units = 0

        # Current cart stock = latest recorded closing position for each sales cart.
        current_cart_stock = 0
        current_cart_stock_value = 0.0
        current_cart_stock_value_mrp = 0.0
        cart_stock_breakdown = {cart: {"units": 0, "value": 0.0} for cart in CARTS}
        try:
            cart_stock_df = db_conn.query(
                """
                WITH latest_cart_entries AS (
                    SELECT DISTINCT ON (cart_name) id, cart_name, entry_date
                    FROM daily_cart_entries
                    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(city, 'HOSUR'))) = :active_loc)
                    ORDER BY cart_name, entry_date DESC, id DESC
                )
                SELECT e.cart_name, i.flavor_code, COALESCE(i.closing_units, 0) AS closing_units
                FROM latest_cart_entries e
                JOIN daily_cart_items i ON i.daily_entry_id = e.id;
                """,
                params={"active_loc": get_active_location_filter()},
                ttl="60s"
            )
            if not cart_stock_df.empty:
                for _, r in cart_stock_df.iterrows():
                    cart_name = str(r.get("cart_name") or "").strip()
                    code = str(r.get("flavor_code") or "").strip()
                    units = int(round(_num(r.get("closing_units"))))
                    value = units * float(FLAVOR_MAP[code]["cost_price"]) if code in FLAVOR_MAP else 0.0
                    value_mrp = units * float(FLAVOR_MAP[code]["mrp"]) if code in FLAVOR_MAP else 0.0
                    current_cart_stock += units
                    current_cart_stock_value += value
                    current_cart_stock_value_mrp += value_mrp
                    if cart_name in cart_stock_breakdown:
                        cart_stock_breakdown[cart_name]["units"] += units
                        cart_stock_breakdown[cart_name]["value"] += value
        except Exception:
            current_cart_stock = 0
            current_cart_stock_value = 0.0
            current_cart_stock_value_mrp = 0.0
            cart_stock_breakdown = {cart: {"units": 0, "value": 0.0} for cart in CARTS}

        # Round each displayed cart total first and then add those displayed values for
        # the overall cart value, so the TOTAL always equals the visible cart rows.
        for cart in CARTS:
            raw_cart_value = float(cart_stock_breakdown.get(cart, {}).get("value", 0.0))
            cart_stock_breakdown[cart]["display_value"] = (
                int(raw_cart_value + 0.5) if raw_cart_value >= 0 else int(raw_cart_value - 0.5)
            )
        current_cart_stock_value_display = int(
            sum(cart_stock_breakdown[cart]["display_value"] for cart in CARTS)
        )
        current_cart_stock_value_mrp_display = (
            int(current_cart_stock_value_mrp + 0.5)
            if current_cart_stock_value_mrp >= 0
            else int(current_cart_stock_value_mrp - 0.5)
        )

        pv1, pv2, pv3 = st.columns(3)
        pv1.metric("Current Total Stock", f"{tot_curr_b:,.0f} units")
        pv2.metric("Current Stock Value (CP)", f"₹{tot_stock_value_display:,}")
        pv3.metric("Current Stock Value (MRP)", f"₹{tot_stock_value_mrp_display:,}")
        if pending_stock_payment > 0:
            st.markdown(
                "Includes pending payment of "
                f"<span style='color:#C43D17;font-weight:900;'>₹{pending_stock_payment:,.2f}</span> "
                "against "
                f"<span style='color:#C43D17;font-weight:900;'>{pending_stock_units:,}</span> "
                "units",
                unsafe_allow_html=True
            )
        cv1, cv2, cv3 = st.columns(3)
        cv1.metric("Current Cart Stock", f"{current_cart_stock:,.0f} units")
        cv2.metric("Cart Stock Value (CP)", f"₹{current_cart_stock_value_display:,}")
        cv3.metric("Cart Stock Value (MRP)", f"₹{current_cart_stock_value_mrp_display:,}")

        # Compact cart-wise split. Keep the total row visible even though the two summary
        # metrics above also show the overall cart position.
        cart_rows_html = []
        for cart in CARTS:
            cart_data = cart_stock_breakdown.get(cart, {"units": 0, "value": 0.0})
            cart_rows_html.append(
                f"""<div style='display:grid;grid-template-columns:1.7fr 0.8fr 1fr;align-items:center;
                        padding:7px 10px;border-top:1px solid #E2E8F0;font-size:12px;'>
                        <div style='font-weight:800;color:#1E2252;'>{escape(cart)}</div>
                        <div style='text-align:right;font-weight:800;color:#047857;'>{cart_data['units']:,} units</div>
                        <div style='text-align:right;font-weight:800;color:#1E2252;'>₹{cart_data['display_value']:,}</div>
                    </div>"""
            )
        cart_rows_html.append(
            f"""<div style='display:grid;grid-template-columns:1.7fr 0.8fr 1fr;align-items:center;
                    padding:8px 10px;border-top:2px solid #93C5FD;background:#EFF6FF;font-size:12px;'>
                    <div style='font-weight:900;color:#1E2252;'>TOTAL</div>
                    <div style='text-align:right;font-weight:900;color:#047857;'>{current_cart_stock:,} units</div>
                    <div style='text-align:right;font-weight:900;color:#1E2252;'>₹{current_cart_stock_value_display:,}</div>
                </div>"""
        )
        st.markdown(
            f"""
            <div style='margin-top:8px;border:1px solid #CBD5E1;border-radius:9px;overflow:hidden;
                        background:#F8FAFC;box-shadow:0 1px 2px rgba(0,0,0,0.03);'>
                <div style='display:grid;grid-template-columns:1.7fr 0.8fr 1fr;align-items:center;
                            padding:7px 10px;background:#DBEAFE;font-size:11px;color:#1E2252;'>
                    <div style='font-weight:900;'>Cart-wise Stock</div>
                    <div style='text-align:right;font-weight:900;'>Units</div>
                    <div style='text-align:right;font-weight:900;'>Value</div>
                </div>
                {''.join(cart_rows_html)}
            </div>
            """,
            unsafe_allow_html=True
        )

        # --- SECTION 2: Suggested Orders & Inventory Runway (Based on Physical-Base Stock) ---
        st.markdown("---")
        st.markdown("### 2. Suggested Orders & Inventory Runway")
        reorder_rows, trigger_dates, tot_calc_active, tot_rate, tot_suggested_units, tot_order_cost = [], [], 0, 0.0, 0, 0.0

        for code in FLAVOR_CODES:
            f_info = FLAVOR_MAP[code]
            avail_stock = phys_curr_map.get(code, 0)
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
            reorder_rows.append({"Flavour": f_info["name"], "Stock Available": avail_stock, "Daily Pace": f"{rate:.1f} /d", "Runway": f"{int(round(days_left))} days" if days_left is not None else "—", "Target Buffer": target_req, "Suggested Order": int(suggested_qty), "Urgency": status, "Rationale": reason})

        r_m1, r_m2, r_m3, r_m4 = st.columns(4)
        overall_order_date = min(trigger_dates) if trigger_dates else None
        r_m1.metric("Stock Available", f"{tot_calc_active} units"); r_m2.metric("Daily Velocity", f"{tot_rate:.1f} units/day"); r_m3.metric("Total Order Quantity", f"{tot_suggested_units} pcs"); r_m4.metric("Estimated PO Cost", f"₹{tot_order_cost:,.2f}")

        if overall_order_date is not None:
            if overall_order_date <= today_fa: st.error(f"🚨 **Action Required:** At least one flavor has breached the safety buffer. Place replenishment order today!")
            else: st.info(f"📅 **Next Order Milestone:** Estimated order placement on **{overall_order_date.strftime('%d-%b-%y')}** ({(overall_order_date - today_fa).days} days remaining).")

        reorder_df = pd.DataFrame(reorder_rows)
        reorder_df = pd.concat([reorder_df, pd.DataFrame([{"Flavour": "🔥 OVERALL TOTAL", "Stock Available": tot_calc_active, "Daily Pace": f"{tot_rate:.1f} /d", "Runway": f"{(tot_calc_active / tot_rate):.0f} days" if tot_rate > 0 else "—", "Target Buffer": int(round(tot_rate * (buffer_days + cover_days))), "Suggested Order": tot_suggested_units, "Urgency": "🔴 Order Now" if overall_order_date and overall_order_date <= today_fa else "🟢 Stable", "Rationale": f"Est Cost: ₹{tot_order_cost:,.0f}"}])], ignore_index=True)
        st.dataframe(reorder_df, hide_index=True, use_container_width=True)

        if st.button("📝 Create Order", type="primary", use_container_width=False, key="fa_create_order"):
            st.session_state["po_prefill_quantities"] = {code: int(reorder_rows[i]["Suggested Order"]) for i, code in enumerate(FLAVOR_CODES)}
            st.session_state["po_prefill_active"] = True
            st.session_state["new_po_order_date"] = date.today()
            st.session_state["new_po_exp_date"] = date.today() + timedelta(days=2)
            st.session_state["new_po_loc"] = CITY
            st.session_state["new_po_status"] = "Draft"
            st.session_state["new_po_discount"] = 2.0
            st.session_state["new_po_notes"] = ""
            st.session_state.pop("new_po_editor", None)
            st.session_state["_pending_page_nav"] = "Purchase Orders"
            st.session_state["_pending_po_screen_mode"] = "Create New Order"
            st.rerun()

        st.markdown("---"); st.markdown("### 3. Detailed Stock Movement Logs")
        m_tab1, m_tab2, m_tab3, m_tab4, m_tab5, m_tab6, m_tab7 = st.tabs(["📋 Purchase Orders", "📦 Received Deliveries", "🔍 Physical Stock Audits", "🗑️ Stock Removed", "➕ Cart Extra Stock", "🔄 Remove Cart Stock", "❄️ Freezer Sales"])

        with m_tab1:
            po_query_df = db_conn.query("SELECT p.id AS \"PO #\", p.order_date AS \"Order Date\", p.expected_date AS \"Expected Date\", p.location AS \"Location\", p.order_status AS \"Status\", json_agg(json_build_object('code', pi.flavor_code, 'qty', pi.ordered_units)) AS items FROM purchase_orders p LEFT JOIN purchase_order_items pi ON p.id = pi.order_id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(p.location, 'HOSUR'))) = :active_loc) GROUP BY p.id ORDER BY p.order_date DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if not po_query_df.empty:
                po_display = []
                for _, r in po_query_df.iterrows():
                    items_dict = {itm['code']: itm['qty'] for itm in r['items']} if r['items'] else {}
                    row_data = {"PO #": f"PO #{r['PO #']}", "Order Date": pd.to_datetime(r['Order Date']).strftime("%d-%b-%y"), "Expected": pd.to_datetime(r['Expected Date']).strftime("%d-%b-%y") if pd.notna(r['Expected Date']) else "—", "Location": r['Location'], "Status": r['Status'], "Total Qty": sum(int(q or 0) for q in items_dict.values())}
                    for code in FLAVOR_CODES: row_data[code] = items_dict.get(code, 0)
                    po_display.append(row_data)
                st.dataframe(pd.DataFrame(po_display), hide_index=True, use_container_width=True)
            else: st.caption("No purchase orders found in database.")

        with m_tab2:
            rec_query_df = db_conn.query("SELECT r.id AS \"Receipt #\", r.received_date AS \"Received Date\", r.location AS \"Location\", r.purchase_order_id AS \"PO Ref\", r.payment_status AS \"Payment\", json_agg(json_build_object('code', ri.flavor_code, 'rec', ri.received_units)) AS items FROM stock_received r LEFT JOIN stock_received_items ri ON r.id = ri.received_id WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(r.location, 'HOSUR'))) = :active_loc) GROUP BY r.id ORDER BY r.received_date DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if not rec_query_df.empty:
                rec_display = []
                for _, r in rec_query_df.iterrows():
                    items_dict = {itm['code']: itm['rec'] for itm in r['items']} if r['items'] else {}
                    row_data = {"Receipt #": f"#{r['Receipt #']}", "Received Date": pd.to_datetime(r['Received Date']).strftime("%d-%b-%y"), "Location": r['Location'], "Linked PO": f"PO #{r['PO Ref']}" if pd.notna(r['PO Ref']) else "Ad-hoc", "Payment Status": r['Payment'], "Total Received": sum(int(q or 0) for q in items_dict.values())}
                    for code in FLAVOR_CODES: row_data[code] = items_dict.get(code, 0)
                    rec_display.append(row_data)
                st.dataframe(pd.DataFrame(rec_display), hide_index=True, use_container_width=True)
            else: st.caption("No stock receipts recorded in database.")

        with m_tab3:
            audit_query_df = db_conn.query("SELECT audit_id AS \"Audit #\", audit_date AS \"Audit Date\", audit_time AS \"Audit Time\", location AS \"Location\", audited_by AS \"Auditor\", total_physical_units AS \"Total Count\", remarks AS \"Remarks\", ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units FROM stock_audits_wide WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc) ORDER BY audit_date DESC, audit_id DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if not audit_query_df.empty:
                aud_display = []
                for _, r in audit_query_df.iterrows():
                    row_data = {"Audit #": f"#{r['Audit #']}", "Audit Date": pd.to_datetime(r['Audit Date']).strftime("%d-%b-%Y"), "Audit Time": (str(r['Audit Time'])[:5] if pd.notna(r.get('Audit Time')) else ""), "Location": r['Location'], "Audited By": r['Auditor'], "Total Count": r['Total Count'], "Remarks": r['Remarks']}
                    for code in FLAVOR_CODES: row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                    aud_display.append(row_data)
                st.dataframe(pd.DataFrame(aud_display), hide_index=True, use_container_width=True)
            else: st.caption("No physical stock audits recorded in database.")

        with m_tab4:
            rem_query_df = db_conn.query("SELECT id AS \"ID\", removal_date AS \"Date\", location AS \"Location\", ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, total_units AS \"Total Units\", cost_price_of_removed_items AS \"Cost (₹)\", reason_for_removal AS \"Reason\", removed_by AS \"Removed By\", verified_by AS \"Verified By\" FROM stock_removed WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc) ORDER BY removal_date DESC, id DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if not rem_query_df.empty:
                rem_display = []
                for _, r in rem_query_df.iterrows():
                    row_data = {"ID": f"#{r['ID']}", "Date": pd.to_datetime(r['Date']).strftime("%d-%b-%y"), "Location": r['Location'], "Total Units": int(r['Total Units']) if pd.notna(r['Total Units']) else sum(int(r.get(FLAVOR_MAP[code]['audit_col'], 0)) for c in FLAVOR_CODES), "Cost (₹)": float(r['Cost (₹)']), "Reason": r['Reason'], "Removed By": r['Removed By'] if pd.notna(r['Removed By']) else "", "Verified By": r['Verified By']}
                    for code in FLAVOR_CODES: row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                    rem_display.append(row_data)
                st.dataframe(pd.DataFrame(rem_display), hide_index=True, use_container_width=True)
            else: st.caption("No stock removals recorded in database.")

        with m_tab5:
            try:
                extra_all_df = db_conn.query(
                    """
                    SELECT id, entry_date, cart_name, location, staff_name,
                           ml_units, mm_units, ps_units, mn_units, kb_units,
                           bm_units, sg_units, ch_units, ra_units,
                           total_extra_units, recorded_by, source_app, created_at
                    FROM public.cart_extra_stock_logs
                    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
                    ORDER BY entry_date DESC, id DESC;
                    """,
                    params={"active_loc": get_active_location_filter()},
                    ttl="60s"
                )
                if not extra_all_df.empty:
                    ext_display = []
                    for _, r in extra_all_df.iterrows():
                        row_data = {
                            "Log #": f"#{int(r['id'])}",
                            "Date": pd.to_datetime(r["entry_date"]).strftime("%d-%b-%y"),
                            "Time": pd.to_datetime(r["created_at"]).strftime("%I:%M %p") if pd.notna(r.get("created_at")) else "—",
                            "Cart": r["cart_name"],
                            "Location": r.get("location") or CITY,
                            "Staff": r.get("staff_name") or "—",
                            "Total Extra": int(r.get("total_extra_units") or 0),
                        }
                        for code in FLAVOR_CODES:
                            row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                        row_data["Recorded By"] = f"{r.get('recorded_by') or '—'} ({r.get('source_app') or 'app'})"
                        ext_display.append(row_data)
                    st.dataframe(pd.DataFrame(ext_display), hide_index=True, use_container_width=True)
                else:
                    st.caption("No cart extra stock logs recorded in database yet.")
            except Exception as e:
                st.caption(f"Could not load cart_extra_stock_logs: {e}")

        with m_tab6:
            try:
                ctf_all_df = db_conn.query(
                    """
                    SELECT id, entry_date, cart_name, location, staff_name,
                           ml_units, mm_units, ps_units, mn_units, kb_units,
                           bm_units, sg_units, ch_units, ra_units,
                           total_returned_units, recorded_by, source_app, created_at
                    FROM public.cart_to_freezer_logs
                    WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc)
                    ORDER BY entry_date DESC, id DESC;
                    """,
                    params={"active_loc": get_active_location_filter()},
                    ttl="60s",
                )
                if not ctf_all_df.empty:
                    ctf_display = []
                    for _, r in ctf_all_df.iterrows():
                        row_data = {
                            "Log #": f"#{int(r['id'])}",
                            "Date": pd.to_datetime(r["entry_date"]).strftime("%d-%b-%y"),
                            "Time": pd.to_datetime(r["created_at"]).strftime("%I:%M %p") if pd.notna(r.get("created_at")) else "—",
                            "Cart": r["cart_name"],
                            "Location": r.get("location") or CITY,
                            "Staff": r.get("staff_name") or "—",
                            "Frm Cart Units": int(r.get("total_returned_units") or sum(int(r.get(FLAVOR_MAP[c]["audit_col"], 0)) for c in FLAVOR_CODES)),
                        }
                        for code in FLAVOR_CODES:
                            row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                        row_data["Recorded By"] = f"{r.get('recorded_by') or '—'} ({r.get('source_app') or 'app'})"
                        ctf_display.append(row_data)
                    st.dataframe(pd.DataFrame(ctf_display), hide_index=True, use_container_width=True)
                else:
                    st.caption("No Remove Cart Stock (Cart-to-Freezer) logs recorded yet.")
            except Exception as e:
                st.caption(f"Could not load cart_to_freezer_logs: {e}")

        with m_tab7:
            ft_c1, ft_c2, ft_c3 = st.columns([1.2, 1.4, 1.4])
            with ft_c1:
                fa_fzr_mode = st.radio("Filter Mode", ["Month", "Custom Date Range"], horizontal=True, key="fa_fzr_txn_filter_mode")
            today_ft = date.today()
            if fa_fzr_mode == "Month":
                month_names_ft = list(calendar.month_name)[1:]
                with ft_c2:
                    sel_m_name = st.selectbox("Month", month_names_ft, index=today_ft.month - 1, key="fa_fzr_txn_month")
                    sel_m_num = month_names_ft.index(sel_m_name) + 1
                with ft_c3:
                    sel_y_num = st.number_input("Year", min_value=2024, max_value=2035, value=today_ft.year, step=1, key="fa_fzr_txn_year")
                ft_start = date(int(sel_y_num), int(sel_m_num), 1)
                ft_end = date(int(sel_y_num), int(sel_m_num), calendar.monthrange(int(sel_y_num), int(sel_m_num))[1])
            else:
                with ft_c2:
                    ft_start = st.date_input("From Date", value=today_ft.replace(day=1), format="DD-MM-YYYY", key="fa_fzr_txn_from")
                with ft_c3:
                    ft_end = st.date_input("To Date", value=today_ft, format="DD-MM-YYYY", key="fa_fzr_txn_to")

            fa_fzr_df = load_freezer_sale_transactions_df(start_date=ft_start, end_date=ft_end)
            if fa_fzr_df.empty:
                st.caption("No Freezer sale transactions recorded in the selected date range.")
            else:
                fa_rows = []
                for _, r in fa_fzr_df.iterrows():
                    row_d = {
                        "Txn #": f"#{int(r['id'])}",
                        "Date": pd.to_datetime(r["sale_date"]).strftime("%d-%b-%y"),
                        "Time": pd.to_datetime(r["created_at"]).strftime("%I:%M %p") if pd.notna(r.get("created_at")) else "—",
                        "Freezer": r["freezer_name"],
                        "Sold By": r.get("sold_by") or "—",
                        "Units Sold": int(r.get("total_units") or 0),
                        "Total Value (₹)": f"₹{float(r.get('total_value') or 0):,.0f}",
                        "PhonePe (₹)": f"₹{float(r.get('phonepe') or 0):,.0f}",
                        "Cash (₹)": f"₹{float(r.get('cash') or 0):,.0f}",
                        "Leakage (₹)": f"₹{float(r.get('leakage') or 0):,.0f}",
                    }
                    for code in FLAVOR_CODES:
                        row_d[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                    row_d["Reason"] = r.get("reason") or "—"
                    fa_rows.append(row_d)

                tot_row = {
                    "Txn #": "SUMMARY TOTAL",
                    "Date": f"{len(fa_fzr_df)} txn(s)",
                    "Time": "—",
                    "Freezer": "—",
                    "Sold By": "—",
                    "Units Sold": int(fa_fzr_df["total_units"].sum()),
                    "Total Value (₹)": f"₹{float(fa_fzr_df['total_value'].sum()):,.0f}",
                    "PhonePe (₹)": f"₹{float(fa_fzr_df['phonepe'].sum()):,.0f}",
                    "Cash (₹)": f"₹{float(fa_fzr_df['cash'].sum()):,.0f}",
                    "Leakage (₹)": f"₹{float(fa_fzr_df['leakage'].sum()):,.0f}",
                }
                for code in FLAVOR_CODES:
                    tot_row[code] = int(fa_fzr_df[FLAVOR_MAP[code]["audit_col"]].sum())
                tot_row["Reason"] = "—"
                fa_rows.append(tot_row)

                fa_disp_df = pd.DataFrame(fa_rows)
                st.dataframe(
                    fa_disp_df.style.apply(
                        lambda r: ["background-color:#EFF6FF;font-weight:900;color:#1E2252;" if r.get("Txn #") == "SUMMARY TOTAL" else "" for _ in r],
                        axis=1
                    ),
                    hide_index=True,
                    use_container_width=True
                )

    elif page == "Stock Removed" and user_role == "admin":
        st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
        st.subheader("Stock Removed / Wastage Log")
        pass

        rem_mode = st.radio("Mode", ["New Entry", "View Entries", "Edit Past Entry"], horizontal=True, key="rem_screen_mode")

        if rem_mode == "New Entry":
            pass
            c1, c2, c3, c4, c5 = st.columns([0.95, 0.85, 0.95, 0.85, 1.5], gap="small")
            with c1: removal_date = st.date_input("Removal Date", value=date.today(), key="new_rem_date", format="DD-MM-YYYY")
            with c2: location = st.text_input("Location", value=CITY, key="new_rem_loc")
            with c3: removed_by = st.text_input("Removed By", placeholder="e.g. Staff / Cart Boy", key="new_rem_rby")
            with c4: verified_by = st.text_input("Verified By", value="Admin", key="new_rem_vby")
            with c5: reason_for_removal = st.text_input("Reason for Removal *", key="new_rem_reason", placeholder="e.g. Broken packaging, expired batch...")

            rem_grid_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Units Removed": 0} for code in FLAVOR_CODES]

            rem_editor_df = st.data_editor(pd.DataFrame(rem_grid_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Units Removed": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, row_height=28, key="new_rem_editor")

            tot_rem_units = int(rem_editor_df["Units Removed"].sum())
            tot_rem_cost = float(sum(rem_editor_df["Units Removed"] * rem_editor_df["Unit Cost (₹)"]))

            m1, m2, m3 = st.columns(3, gap="small")
            m1.metric("Total Units Removed", f"{tot_rem_units} units"); m2.metric("Total Cost Value", f"₹{tot_rem_cost:,.2f}"); m3.metric("Date of Removal", removal_date.strftime("%d-%b-%y"))

            if st.button("🗑️ Save Stock Removal", type="primary", use_container_width=False, key="submit_new_stock_removal"):
                if tot_rem_units <= 0: st.error("Please enter at least one quantity greater than 0 before saving.")
                elif not reason_for_removal.strip(): st.error("Reason for removal is mandatory. Please provide a brief explanation.")
                else:
                    try:
                        units_map = dict(zip(rem_editor_df["Code"], rem_editor_df["Units Removed"]))
                        with db_conn.session as s:
                            res = s.execute(text("INSERT INTO stock_removed (removal_date, location, ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, cost_price_of_removed_items, reason_for_removal, removed_by, verified_by) VALUES (:rd, :loc, :ml, :mm, :ps, :mn, :kb, :bm, :sg, :ch, :ra, :cost, :reason, :rby, :vby) RETURNING id;"), {"rd": removal_date, "loc": location, "ml": int(units_map.get("ML", 0)), "mm": int(units_map.get("MM", 0)), "ps": int(units_map.get("PS", 0)), "mn": int(units_map.get("MN", 0)), "kb": int(units_map.get("KB", 0)), "bm": int(units_map.get("BM", 0)), "sg": int(units_map.get("SG", 0)), "ch": int(units_map.get("CH", 0)), "ra": int(units_map.get("RA", 0)), "cost": tot_rem_cost, "reason": reason_for_removal.strip(), "rby": removed_by.strip(), "vby": verified_by.strip()})
                            new_rem_id = res.scalar()
                            rem_tag = f"[Auto: Stock Removal #{new_rem_id}]"
                            rem_month = list(calendar.month_name)[removal_date.month]
                            s.execute(
                                text("DELETE FROM expenses WHERE remarks LIKE :tag;"),
                                {"tag": f"{rem_tag}%"}
                            )
                            if float(tot_rem_cost) > 0:
                                s.execute(
                                    text("""
                                    INSERT INTO expenses (
                                        expense_date, month, location, expense_type, category, sub_category,
                                        description, total_amount, attributed_to, status, recorded_by, remarks
                                    ) VALUES (
                                        :ed, :month, :loc, 'OPEX', 'Miscellaneous Expense', 'Gift Goodwill',
                                        :desc, :amt, 'Central / Freezer', 'Not Applicable', :recby, :rem
                                    );
                                    """),
                                    {
                                        "ed": removal_date,
                                        "month": rem_month,
                                        "loc": str(location or CITY).strip().upper(),
                                        "desc": reason_for_removal.strip(),
                                        "amt": float(tot_rem_cost),
                                        "recby": verified_by.strip() or "Stock Removed Auto",
                                        "rem": rem_tag,
                                    }
                                )
                            s.commit()
                        st.cache_data.clear()
                        show_success_modal(f"Stock Removal #{new_rem_id} recorded successfully! Logged {tot_rem_units} units (₹{tot_rem_cost:,.2f}).")
                    except Exception as e: st.error(f"Could not save stock removal to database: {e}")

        elif rem_mode == "View Entries":
            rem_query_df = db_conn.query("SELECT id AS \"ID\", removal_date AS \"Date\", location AS \"Location\", ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, total_units AS \"Total Units\", cost_price_of_removed_items AS \"Cost (₹)\", reason_for_removal AS \"Reason\", removed_by AS \"Removed By\", verified_by AS \"Verified By\" FROM stock_removed WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc) ORDER BY removal_date DESC, id DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if rem_query_df.empty: st.info("No stock removal logs found in the database.")
            else:
                total_logs = len(rem_query_df)
                total_removed_units = int(rem_query_df["Total Units"].sum()) if "Total Units" in rem_query_df.columns else 0
                total_removed_cost = float(rem_query_df["Cost (₹)"].sum())

                k1, k2, k3 = st.columns(3)
                k1.metric("Total Removal Events", f"{total_logs}"); k2.metric("Total Units Removed", f"{total_removed_units} pcs"); k3.metric("Total Value of Removed Stock", f"₹{total_removed_cost:,.2f}")

                display_rem_list = []
                for _, r in rem_query_df.iterrows():
                    row_data = {"ID": f"#{r['ID']}", "Date": pd.to_datetime(r['Date']).strftime("%d-%b-%y"), "Location": r['Location'], "Total Units": int(r['Total Units']) if pd.notna(r['Total Units']) else sum(int(r.get(FLAVOR_MAP[code]['audit_col'], 0)) for c in FLAVOR_CODES), "Cost (₹)": float(r['Cost (₹)']), "Reason": r['Reason'], "Removed By": r['Removed By'] if pd.notna(r['Removed By']) else "", "Verified By": r['Verified By']}
                    for code in FLAVOR_CODES: row_data[code] = int(r.get(FLAVOR_MAP[code]["audit_col"], 0))
                    display_rem_list.append(row_data)

                st.dataframe(pd.DataFrame(display_rem_list), hide_index=True, use_container_width=True, column_config={"Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f")})

        elif rem_mode == "Edit Past Entry":
            rem_query_df = db_conn.query("SELECT id, removal_date, location, ml_units, mm_units, ps_units, mn_units, kb_units, bm_units, sg_units, ch_units, ra_units, cost_price_of_removed_items, reason_for_removal, removed_by, verified_by FROM stock_removed WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(location, 'HOSUR'))) = :active_loc) ORDER BY removal_date DESC, id DESC;", params={"active_loc": get_active_location_filter()}, ttl="60s")
            if rem_query_df.empty: st.info("No past stock removals found in database.")
            else:
                rem_records = rem_query_df.to_dict("records")
                rem_labels = [f"Removal #{r['id']} — {pd.to_datetime(r['removal_date']).strftime('%d-%b-%y')} ({r['location']}) — {str(r['reason_for_removal'])[:25]} (₹{float(r['cost_price_of_removed_items']):,.0f})" for r in rem_records]
                sel_rem_label = st.selectbox("Select removal entry to edit", rem_labels, key="edit_rem_select")
                loaded_rem = rem_records[rem_labels.index(sel_rem_label)]
                loaded_rem_id = loaded_rem["id"]

                c1, c2, c3, c4 = st.columns(4)
                with c1: e_rem_date = st.date_input("Removal Date", value=pd.to_datetime(loaded_rem["removal_date"]).date() if loaded_rem.get("removal_date") else date.today(), key=f"edit_rem_date_{loaded_rem_id}", format="DD-MM-YYYY")
                with c2: e_rem_loc = st.text_input("Location", value=str(loaded_rem.get("location", CITY)), key=f"edit_rem_loc_{loaded_rem_id}")
                with c3: e_rem_rby = st.text_input("Removed By", value=str(loaded_rem.get("removed_by") or ""), key=f"edit_rem_rby_{loaded_rem_id}")
                with c4: e_rem_vby = st.text_input("Verified By", value=str(loaded_rem.get("verified_by", "Admin")), key=f"edit_rem_vby_{loaded_rem_id}")

                e_rem_reason = st.text_input("Reason for Removal", value=str(loaded_rem.get("reason_for_removal") or ""), key=f"edit_rem_reason_{loaded_rem_id}")
                edit_rem_rows = [{"Flavour": FLAVOR_MAP[code]["name"], "Code": code, "Unit Cost (₹)": float(FLAVOR_MAP[code]["cost_price"]), "Units Removed": int(loaded_rem.get(FLAVOR_MAP[code]["audit_col"], 0))} for code in FLAVOR_CODES]

                pass
                rem_edit_editor_df = st.data_editor(pd.DataFrame(edit_rem_rows), column_config={"Flavour": st.column_config.TextColumn(disabled=True), "Code": st.column_config.TextColumn(disabled=True), "Unit Cost (₹)": st.column_config.NumberColumn(format="₹%,.2f", disabled=True), "Units Removed": st.column_config.NumberColumn(min_value=0, step=1, format="%d")}, hide_index=True, use_container_width=True, row_height=28, key=f"edit_rem_editor_{loaded_rem_id}")

                e_tot_rem_units = int(rem_edit_editor_df["Units Removed"].sum())
                e_tot_rem_cost = float(sum(rem_edit_editor_df["Units Removed"] * rem_edit_editor_df["Unit Cost (₹)"]))

                st.markdown("#### Updated Summary")
                em1, em2, em3 = st.columns(3)
                em1.metric("Total Units Removed", f"{e_tot_rem_units} units"); em2.metric("Total Cost Value", f"₹{e_tot_rem_cost:,.2f}"); em3.metric("Date", e_rem_date.strftime("%d-%b-%y"))

                if st.button("💾 Update Stock Removal", type="primary", use_container_width=False, key="submit_upd_stock_removal"):
                    if e_tot_rem_units <= 0: st.error("Please enter at least one quantity greater than 0.")
                    elif not e_rem_reason.strip(): st.error("Reason for removal cannot be empty.")
                    else:
                        try:
                            e_units_map = dict(zip(rem_edit_editor_df["Code"], rem_edit_editor_df["Units Removed"]))
                            with db_conn.session as s:
                                s.execute(text("UPDATE stock_removed SET removal_date = :rd, location = :loc, ml_units = :ml, mm_units = :mm, ps_units = :ps, mn_units = :mn, kb_units = :kb, bm_units = :bm, sg_units = :sg, ch_units = :ch, ra_units = :ra, cost_price_of_removed_items = :cost, reason_for_removal = :reason, removed_by = :rby, verified_by = :vby, updated_at = NOW() WHERE id = :id;"), {"rd": e_rem_date, "loc": e_rem_loc, "ml": int(e_units_map.get("ML", 0)), "mm": int(e_units_map.get("MM", 0)), "ps": int(e_units_map.get("PS", 0)), "mn": int(e_units_map.get("MN", 0)), "kb": int(e_units_map.get("KB", 0)), "bm": int(e_units_map.get("BM", 0)), "sg": int(e_units_map.get("SG", 0)), "ch": int(e_units_map.get("CH", 0)), "ra": int(e_units_map.get("RA", 0)), "cost": e_tot_rem_cost, "reason": e_rem_reason.strip(), "rby": e_rem_rby.strip(), "vby": e_rem_vby.strip(), "id": loaded_rem_id})
                                rem_tag = f"[Auto: Stock Removal #{loaded_rem_id}]"
                                rem_month = list(calendar.month_name)[e_rem_date.month]
                                existing_exp = s.execute(
                                    text("SELECT id FROM expenses WHERE remarks LIKE :tag ORDER BY id DESC LIMIT 1;"),
                                    {"tag": f"{rem_tag}%"}
                                ).fetchone()
                                if existing_exp:
                                    s.execute(
                                        text("""
                                        UPDATE expenses
                                        SET expense_date = :ed,
                                            month = :month,
                                            expense_type = 'OPEX',
                                            category = 'Miscellaneous Expense',
                                            sub_category = 'Gift Goodwill',
                                            description = :desc,
                                            total_amount = :amt,
                                            attributed_to = 'Central / Freezer',
                                            status = 'Not Applicable',
                                            recorded_by = :recby,
                                            remarks = :rem,
                                            updated_at = NOW()
                                        WHERE id = :eid;
                                        """),
                                        {
                                            "ed": e_rem_date,
                                            "month": rem_month,
                                            "desc": e_rem_reason.strip(),
                                            "amt": float(e_tot_rem_cost),
                                            "recby": e_rem_vby.strip() or "Stock Removed Auto",
                                            "rem": rem_tag,
                                            "eid": int(existing_exp[0]),
                                        }
                                    )
                                elif float(e_tot_rem_cost) > 0:
                                    s.execute(
                                        text("""
                                        INSERT INTO expenses (
                                            expense_date, month, expense_type, category, sub_category,
                                            description, total_amount, attributed_to, status, recorded_by, remarks
                                        ) VALUES (
                                            :ed, :month, 'OPEX', 'Miscellaneous Expense', 'Gift Goodwill',
                                            :desc, :amt, 'Central / Freezer', 'Not Applicable', :recby, :rem
                                        );
                                        """),
                                        {
                                            "ed": e_rem_date,
                                            "month": rem_month,
                                            "desc": e_rem_reason.strip(),
                                            "amt": float(e_tot_rem_cost),
                                            "recby": e_rem_vby.strip() or "Stock Removed Auto",
                                            "rem": rem_tag,
                                        }
                                    )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"Stock Removal #{loaded_rem_id} updated successfully! Final Value: ₹{e_tot_rem_cost:,.2f}.")
                        except Exception as e: st.error(f"Could not update stock removal entry: {e}")

    elif page == "Expenses" and user_role == "admin":
        st.subheader("Expenses & Payments Management")
        pass

        if "_pending_exp_nav_sec" in st.session_state:
            st.session_state["exp_nav_sec"] = st.session_state.pop("_pending_exp_nav_sec")
        if "_pending_e_sub_mode_rad" in st.session_state:
            st.session_state["e_sub_mode_rad"] = st.session_state.pop("_pending_e_sub_mode_rad")
        if "_pending_p_sub_mode_rad" in st.session_state:
            st.session_state["p_sub_mode_rad"] = st.session_state.pop("_pending_p_sub_mode_rad")

        if st.session_state.get("e_sub_mode_rad") not in (None, "View Expenses", "Add New Expense"):
            st.session_state["e_sub_mode_rad"] = "View Expenses"
        if st.session_state.get("p_sub_mode_rad") not in (None, "View Payments", "Record New Payment"):
            st.session_state["p_sub_mode_rad"] = "View Payments"

        def _clean_str(val, fallback="—"):
            if val is None or pd.isna(val):
                return fallback
            s = str(val).strip()
            if not s or s.lower() in ("nan", "none", "null"):
                return fallback
            return s

        def _status_pill_html(status_val):
            s = _clean_str(status_val, "Pending")
            sl = s.lower()
            if sl == "paid":
                cls, label = "status-paid", "Paid"
            elif "partial" in sl:
                cls, label = "status-partial", "Partial"
            elif sl == "pending":
                cls, label = "status-pending", "Pending"
            elif "not applicable" in sl:
                cls, label = "status-other", "N/A"
            elif "cancel" in sl:
                cls, label = "status-other", "Cancelled"
            else:
                cls, label = "status-other", s[:10]
            return f"<span class='status-pill {cls}' title='{escape(s)}'>{escape(label)}</span>"

        def _populate_expense_clone_state(src_exp):
            pos_df_cl = db_conn.query("SELECT id, order_date, location FROM purchase_orders ORDER BY order_date DESC;", ttl="60s") if db_conn else pd.DataFrame()
            po_opts_cl = ["None"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d-%b')})" for _, r in pos_df_cl.iterrows()] if not pos_df_cl.empty else ["None"]
            staff_opts_cl = load_active_staff_list()
            st.session_state["add_e_type"] = src_exp["expense_type"] if src_exp.get("expense_type") in EXPENSE_TYPES else EXPENSE_TYPES[0]
            st.session_state["add_e_cat"] = src_exp["category"] if src_exp.get("category") in EXPENSE_CATEGORIES else EXPENSE_CATEGORIES[0]
            st.session_state["add_e_subcat"] = _clean_str(src_exp.get("sub_category"), "")
            st.session_state["add_e_date"] = date.today()
            st.session_state[f"add_e_month_{date.today().strftime('%Y%m')}"] = list(calendar.month_name)[date.today().month]
            st.session_state["add_e_amt"] = float(src_exp.get("total_amount") or 0.0)
            st.session_state["add_e_attr"] = src_exp["attributed_to"] if src_exp.get("attributed_to") in ATTRIBUTED_OPTIONS else ATTRIBUTED_OPTIONS[0]
            st.session_state["add_e_vendor"] = _clean_str(src_exp.get("vendor_name"), "")
            src_staff = _clean_str(src_exp.get("staff_name"), "Select Staff")
            st.session_state["add_e_staff"] = src_staff if src_staff in staff_opts_cl else "Select Staff"
            if pd.notna(src_exp.get("purchase_order_id")):
                matched_po = next((o for o in po_opts_cl if o.startswith(f"PO #{int(src_exp['purchase_order_id'])} ")), "None")
                st.session_state["add_e_po"] = matched_po
            else:
                st.session_state["add_e_po"] = "None"
            st.session_state["add_e_stat"] = "Pending"
            st.session_state["add_e_desc"] = _clean_str(src_exp.get("description"), "")
            st.session_state["add_e_remarks"] = _clean_str(src_exp.get("remarks"), "")

        def _populate_expense_from_ops_spend(spend_row):
            spend_id = int(spend_row["id"])
            spend_dt = pd.to_datetime(spend_row["spend_date"]).date() if pd.notna(spend_row.get("spend_date")) else date.today()
            spend_amt = float(_num(spend_row.get("amount")))
            spend_notes = _clean_str(spend_row.get("notes"), "")
            spent_by_role = str(spend_row.get("spent_by") or "OPS_COORDINATOR").strip().upper()
            tag_prefix = "Admin 1 Cash Spend" if spent_by_role == "ADMIN_1" else "Ops Cash Spend"
            tag = f"[{tag_prefix} #{spend_id}]"
            remarks_tagged = spend_notes if tag in spend_notes else f"{spend_notes} {tag}".strip()

            st.session_state["add_e_type"] = "OPEX"
            st.session_state["add_e_cat"] = EXPENSE_CATEGORIES[0]
            st.session_state["add_e_subcat"] = ""
            st.session_state["add_e_date"] = spend_dt
            st.session_state[f"add_e_month_{spend_dt.strftime('%Y%m')}"] = list(calendar.month_name)[spend_dt.month]
            st.session_state["add_e_amt"] = spend_amt
            st.session_state["add_e_attr"] = "Central / Freezer"
            st.session_state["add_e_vendor"] = ""
            st.session_state["add_e_staff"] = "Select Staff"
            st.session_state["add_e_po"] = "None"
            st.session_state["add_e_stat"] = "Paid"
            st.session_state["add_e_desc"] = spend_notes
            st.session_state["add_e_remarks"] = remarks_tagged
            # Pre-enable immediate payment with Cash mode, spend_date and amount
            st.session_state["add_e_direct_pay"] = True
            st.session_state["add_p_date"] = spend_dt
            st.session_state[f"add_p_amt_{spend_amt:.2f}"] = spend_amt
            st.session_state["add_p_mode"] = "Cash"
            st.session_state["add_p_ref"] = f"OPS-CASH-{spend_id}"
            st.session_state["add_p_notes"] = f"Recorded from Ops Cash Spend #{spend_id}: {spend_notes}".strip()
            st.session_state["_loaded_ops_spend_banner"] = {
                "id": spend_id,
                "date": spend_dt.strftime("%d-%b-%Y"),
                "amount": spend_amt,
                "notes": spend_notes,
            }

        exp_nav = st.radio("Section", ["📋 Expenses (Bills / Invoices)", "💳 Payments (Cash Outflows)", "📊 Summary & Date Reports"], horizontal=True, key="exp_nav_sec")

        # ==================================================================
        # SECTION 1: EXPENSES (BILLS / INVOICES)
        # ==================================================================
        if exp_nav == "📋 Expenses (Bills / Invoices)":
            e_sub_mode = st.radio("Action", ["View Expenses", "Add New Expense"], horizontal=True, key="e_sub_mode_rad")
            expenses_summary_df = load_db_expenses_summary_df()

            if e_sub_mode == "Add New Expense":
                st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
                st.session_state.pop("_editing_expense_id", None)
                if "_pending_ops_spend_to_load" in st.session_state:
                    _populate_expense_from_ops_spend(st.session_state.pop("_pending_ops_spend_to_load"))

                pass
                pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders ORDER BY order_date DESC;", ttl="60s") if db_conn else pd.DataFrame()
                po_opts = ["None"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d-%b')})" for _, r in pos_df.iterrows()] if not pos_df.empty else ["None"]
                staff_opts = load_active_staff_list()

                ops_spends_df = load_ops_cash_spend_entries_df()
                with st.expander("🧾 View & Convert Ops Cash Spend Entries into Expense + Immediate Payment", expanded=bool(st.session_state.get("_loaded_ops_spend_banner"))):
                    if ops_spends_df.empty:
                        st.caption("No Ops cash spend entries recorded yet.")
                    else:
                        ops_records = ops_spends_df.to_dict("records")
                        ops_labels = [
                            f"Ops Spend #{int(r['id'])} | {pd.to_datetime(r['spend_date']).strftime('%d-%b-%Y')} | "
                            f"₹{float(r['amount']):,.2f} — {_clean_str(r.get('notes'), 'No notes')[:45]} "
                            f"[{'✓ Expense #' + str(int(r['linked_expense_id'])) if pd.notna(r.get('linked_expense_id')) else 'Pending Expense'}]"
                            for r in ops_records
                        ]
                        oc1, oc2 = st.columns([3.8, 1.2], gap="small", vertical_alignment="bottom")
                        with oc1:
                            sel_ops_spend_label = st.selectbox(
                                "Select an Ops Cash Spend Entry to pre-fill Expense & Immediate Cash Payment",
                                ops_labels,
                                key="ops_spend_prefill_picker",
                            )
                        with oc2:
                            if st.button("🧾 Load Spend", type="primary", use_container_width=True, key="btn_load_ops_spend"):
                                chosen_ops = ops_records[ops_labels.index(sel_ops_spend_label)]
                                _populate_expense_from_ops_spend(chosen_ops)
                                st.toast(f"Pre-filled Expense & Immediate Payment from Ops Spend #{int(chosen_ops['id'])}!", icon="🧾")
                                st.rerun()

                        disp_ops_df = ops_spends_df.copy()
                        disp_ops_df["Spend Date"] = pd.to_datetime(disp_ops_df["spend_date"]).dt.strftime("%d-%b-%Y")
                        disp_ops_df["Amount (₹)"] = disp_ops_df["amount"].astype(float).map(lambda x: f"₹{x:,.2f}")
                        disp_ops_df["Allocated (₹)"] = disp_ops_df["allocated_amount"].astype(float).map(lambda x: f"₹{x:,.2f}")
                        disp_ops_df["Unhanded (₹)"] = disp_ops_df["remaining_amount"].astype(float).map(lambda x: f"₹{x:,.2f}")
                        disp_ops_df["Reason / Notes"] = disp_ops_df["notes"].fillna("—")
                        disp_ops_df["Expense Status"] = disp_ops_df.apply(
                            lambda r: f"✓ Expense #{int(r['linked_expense_id'])} ({r.get('linked_expense_category') or ''})"
                            if pd.notna(r.get("linked_expense_id"))
                            else "Pending Expense Entry",
                            axis=1,
                        )
                        st.dataframe(
                            disp_ops_df[["id", "Spend Date", "Amount (₹)", "Reason / Notes", "Allocated (₹)", "Unhanded (₹)", "Expense Status"]].rename(columns={"id": "Spend ID"}),
                            hide_index=True,
                            use_container_width=True,
                        )

                loaded_ops_banner = st.session_state.get("_loaded_ops_spend_banner")
                if loaded_ops_banner:
                    st.info(
                        f"🧾 **Pre-filled from Ops Cash Spend #{loaded_ops_banner['id']}** "
                        f"({loaded_ops_banner['date']} • ₹{loaded_ops_banner['amount']:,.2f} • *{loaded_ops_banner['notes']}*). "
                        "Choose **Category**, **Sub-Category**, **Vendor / Staff**, and any other fields below, then click **💾 Save Expense Entry**."
                    )

                with st.container(border=True):
                    cl_c1, cl_c2 = st.columns([3.8, 1.2], gap="small", vertical_alignment="bottom")
                    if not expenses_summary_df.empty:
                        clone_records = expenses_summary_df.to_dict("records")
                        clone_labels = ["— Select an existing expense to clone —"] + [
                            f"#{r['id']} | {pd.to_datetime(r['expense_date']).strftime('%d-%b-%y')} | {r['category']}"
                            f"{(' (' + _clean_str(r.get('sub_category'), '') + ')') if _clean_str(r.get('sub_category'), '') else ''}"
                            f" — {_clean_str(r.get('description') or r.get('vendor_name'), 'No desc')[:38]} (₹{float(r['total_amount']):,.0f})"
                            for r in clone_records
                        ]
                        with cl_c1:
                            sel_clone_label = st.selectbox(
                                "📋 Clone from Existing Expense (Optional)",
                                clone_labels,
                                key="clone_exp_picker",
                                help="Pick any past expense and click 'Load Details' to pre-fill the fields below."
                            )
                        with cl_c2:
                            if st.button("📋 Load Details", use_container_width=True, key="btn_apply_exp_clone", disabled=(sel_clone_label == clone_labels[0])):
                                src_exp = clone_records[clone_labels.index(sel_clone_label) - 1]
                                _populate_expense_clone_state(src_exp)
                                st.toast(f"Cloned details from Expense #{src_exp['id']}!", icon="📋")
                                st.rerun()
                    else:
                        st.caption("No existing expenses available to clone yet.")

                c1, c2, c3, c4, c5 = st.columns([1.05, 1.05, 1.35, 0.95, 1.10], gap="small")
                with c1: e_type = st.selectbox("Expense Type", EXPENSE_TYPES, index=0, key="add_e_type")
                with c2: e_cat = st.selectbox("Category", EXPENSE_CATEGORIES, index=0, key="add_e_cat")
                with c3: e_subcat = st.text_input("Sub-Category (Optional)", placeholder="e.g. Dry Ice, Fuel, Repair", key="add_e_subcat")
                with c4: e_date = st.date_input("Expense Date", value=date.today(), key="add_e_date", format="DD-MM-YYYY")
                with c5:
                    e_month = st.selectbox(
                        "Month",
                        list(calendar.month_name)[1:],
                        index=e_date.month - 1,
                        key=f"add_e_month_{e_date.strftime('%Y%m')}"
                    )

                c5, c6, c7 = st.columns(3)
                with c5: e_amount = st.number_input("Total Amount (₹)", min_value=0.0, step=10.0, format="%.2f", key="add_e_amt")
                with c6: e_attr = st.selectbox("Attributed To", ATTRIBUTED_OPTIONS, index=0, key="add_e_attr")
                with c7: e_vendor = st.text_input("Vendor / Supplier Name", placeholder="e.g. Deep Freeze Services", key="add_e_vendor")

                c8, c9, c10 = st.columns(3)
                with c8: e_staff = st.selectbox("Linked Staff (Optional)", staff_opts, index=0, key="add_e_staff")
                with c9: e_po = st.selectbox("Linked PO (Optional)", po_opts, index=0, key="add_e_po")
                with c10: e_stat = st.selectbox("Initial Status", EXPENSE_STATUSES, index=0, key="add_e_stat")

                desc_c1, desc_c2 = st.columns(2, gap="small")
                with desc_c1: e_desc = st.text_input("Description", placeholder="Brief description of the purchase...", key="add_e_desc")
                with desc_c2: e_remarks = st.text_input("Remarks / Notes (Optional)", key="add_e_remarks")

                st.markdown("---")
                has_direct_pay = st.checkbox("Record immediate payment now", value=False, key="add_e_direct_pay")
                p_date, p_amt, p_mode, p_ref, p_to, p_notes, p_receipt = None, 0.0, "UPI / Bank Transfer", "", "", "", None
                if has_direct_pay:
                    p1, p2, p3 = st.columns(3)
                    with p1: p_date = st.date_input("Payment Date", value=e_date, key="add_p_date", format="DD-MM-YYYY")
                    with p2: p_amt = st.number_input("Amount Paid (₹)", min_value=0.0, value=float(e_amount), step=10.0, format="%.2f", key=f"add_p_amt_{float(e_amount):.2f}")
                    with p3: p_mode = st.selectbox("Payment Mode", PAYMENT_MODES, index=0, key="add_p_mode")
                    p4, p5 = st.columns(2)
                    with p4: p_ref = st.text_input("Ref / UTR No.", placeholder="e.g. UPI Ref, Txn ID", key="add_p_ref")
                    with p5: p_to = st.text_input("Paid To", value=e_vendor, key=f"add_p_to_{e_vendor}")
                    p_notes = st.text_input("Payment Notes", placeholder="Optional payment note...", key="add_p_notes")
                    p_receipt = st.file_uploader(
                        "Receipt / Bill Image (Optional)",
                        type=["jpg", "jpeg", "png", "webp"],
                        accept_multiple_files=False,
                        key="add_p_receipt"
                    )
                    st.caption("Accepted: JPG, JPEG, PNG, WEBP • maximum 3.5 MB")

                if st.button("💾 Save Expense Entry", type="primary", use_container_width=False, key="submit_save_expense_entry"):
                    if e_amount <= 0: st.error("Please enter an expense amount greater than 0.")
                    else:
                        try:
                            p_po_id = int(e_po.split("#")[1].split(" ")[0]) if "PO #" in e_po else None
                            sel_staff = None if e_staff == "Select Staff" else e_staff
                            computed_status = "Paid" if (has_direct_pay and p_amt >= e_amount) else ("Partially Paid" if (has_direct_pay and p_amt > 0) else e_stat)
                            p_receipt_data = prepare_payment_receipt(p_receipt) if (has_direct_pay and p_amt > 0) else prepare_payment_receipt(None)
                            with db_conn.session as s:
                                res = s.execute(text("INSERT INTO expenses (expense_date, month, expense_type, category, sub_category, description, total_amount, attributed_to, vendor_name, staff_name, purchase_order_id, status, recorded_by, remarks) VALUES (:ed, :month, :et, :cat, :subcat, :desc, :amt, :attr, :vendor, :staff, :poid, :stat, :recby, :rem) RETURNING id;"), {"ed": e_date, "month": e_month, "et": e_type, "cat": e_cat, "subcat": e_subcat.strip(), "desc": e_desc.strip(), "amt": float(e_amount), "attr": e_attr, "vendor": e_vendor.strip(), "staff": sel_staff, "poid": p_po_id, "stat": computed_status, "recby": "Admin", "rem": e_remarks.strip()})
                                new_exp_id = res.scalar()
                                new_payment_id = None
                                if has_direct_pay and p_amt > 0:
                                    pay_res = s.execute(
                                        text("INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes, receipt_file_name, receipt_mime_type, receipt_file_size_bytes, receipt_image_base64, receipt_uploaded_at) VALUES (:eid, :pdate, :pamt, :pmode, :pref, :pto, :pby, :notes, :rname, :rmime, :rsize, :rbase64, :ruploaded) RETURNING id;"),
                                        {
                                            "eid": new_exp_id, "pdate": p_date, "pamt": float(p_amt), "pmode": p_mode,
                                            "pref": p_ref.strip(), "pto": p_to.strip(), "pby": "Admin", "notes": p_notes.strip(),
                                            "rname": p_receipt_data["name"], "rmime": p_receipt_data["mime"],
                                            "rsize": p_receipt_data["size"], "rbase64": p_receipt_data["base64"],
                                            "ruploaded": p_receipt_data["uploaded_at"],
                                        }
                                    )
                                    new_payment_id = pay_res.scalar()

                                if e_subcat.strip().lower() == "salary":
                                    payout_res = s.execute(
                                        text("SELECT id FROM staff_salary_payouts WHERE expense_id = :eid ORDER BY id DESC LIMIT 1;"),
                                        {"eid": new_exp_id}
                                    ).fetchone()
                                    payout_params = {
                                        "eid": new_exp_id,
                                        "staff": sel_staff,
                                        "salary_month": e_month,
                                        "salary_year": e_date.year,
                                        "amount_paid": float(e_amount),
                                        "payment_date": p_date if (has_direct_pay and p_amt > 0) else e_date,
                                        "payment_id": new_payment_id,
                                    }
                                    if payout_res:
                                        s.execute(
                                            text("UPDATE staff_salary_payouts SET payment_id = :payment_id, staff_name = :staff, salary_month = :salary_month, salary_year = :salary_year, amount_paid = :amount_paid, payment_date = :payment_date WHERE id = :id;"),
                                            {**payout_params, "id": payout_res[0]}
                                        )
                                    else:
                                        s.execute(
                                            text("INSERT INTO staff_salary_payouts (payment_id, expense_id, staff_name, salary_month, salary_year, amount_paid, payment_date) VALUES (:payment_id, :eid, :staff, :salary_month, :salary_year, :amount_paid, :payment_date);"),
                                            payout_params
                                        )
                                s.commit()
                            st.session_state.pop("_loaded_ops_spend_banner", None)
                            st.cache_data.clear()
                            show_success_modal(f"Expense #{new_exp_id} of ₹{e_amount:,.2f} recorded successfully!")
                        except Exception as e: st.error(f"Could not save expense: {e}")

            elif e_sub_mode == "View Expenses":
                editing_exp_id = st.session_state.get("_editing_expense_id")

                if editing_exp_id is not None and not expenses_summary_df.empty:
                    match_rows = expenses_summary_df[expenses_summary_df["id"] == int(editing_exp_id)]
                    if match_rows.empty:
                        st.session_state.pop("_editing_expense_id", None)
                        st.rerun()
                    else:
                        loaded_exp = match_rows.iloc[0].to_dict()
                        loaded_exp_id = int(loaded_exp["id"])

                        top_b1, top_b2 = st.columns([1.6, 4.4])
                        with top_b1:
                            if st.button("⬅ Back to Expenses List", key="back_from_edit_exp", type="primary", use_container_width=True):
                                st.session_state.pop("_editing_expense_id", None)
                                st.rerun()
                        with top_b2:
                            st.markdown(f"#### ✏️ Editing Expense #{loaded_exp_id}")

                        pos_df = db_conn.query("SELECT id, order_date, location FROM purchase_orders ORDER BY order_date DESC;", ttl="60s") if db_conn else pd.DataFrame()
                        po_opts = ["None"] + [f"PO #{r['id']} ({pd.to_datetime(r['order_date']).strftime('%d-%b')})" for _, r in pos_df.iterrows()] if not pos_df.empty else ["None"]
                        default_po_idx = next((i for i, o in enumerate(po_opts) if o.startswith(f"PO #{int(loaded_exp['purchase_order_id'])} ")), 0) if loaded_exp.get("purchase_order_id") and pd.notna(loaded_exp["purchase_order_id"]) else 0
                        staff_opts = load_active_staff_list()
                        curr_staff = _clean_str(loaded_exp.get("staff_name"), "Select Staff")
                        if curr_staff not in staff_opts: staff_opts.append(curr_staff)

                        c1, c2, c3, c4, c5 = st.columns([1.05, 1.05, 1.35, 0.95, 1.10], gap="small")
                        with c1: e_edit_type = st.selectbox("Expense Type", EXPENSE_TYPES, index=EXPENSE_TYPES.index(loaded_exp["expense_type"]) if loaded_exp["expense_type"] in EXPENSE_TYPES else 0, key=f"ee_type_{loaded_exp_id}")
                        with c2: e_edit_cat = st.selectbox("Category", EXPENSE_CATEGORIES, index=EXPENSE_CATEGORIES.index(loaded_exp["category"]) if loaded_exp["category"] in EXPENSE_CATEGORIES else 0, key=f"ee_cat_{loaded_exp_id}")
                        with c3: e_edit_subcat = st.text_input("Sub-Category", value=_clean_str(loaded_exp.get("sub_category"), ""), key=f"ee_subcat_{loaded_exp_id}")
                        with c4: e_edit_date = st.date_input("Expense Date", value=pd.to_datetime(loaded_exp["expense_date"]).date(), key=f"ee_date_{loaded_exp_id}", format="DD-MM-YYYY")
                        with c5:
                            db_month = _clean_str(loaded_exp.get("month"), "")
                            month_options = list(calendar.month_name)[1:]
                            default_month_idx = month_options.index(db_month) if db_month in month_options else (e_edit_date.month - 1)
                            e_edit_month = st.selectbox("Month", month_options, index=default_month_idx, key=f"ee_month_{loaded_exp_id}")

                        c5, c6, c7 = st.columns(3)
                        with c5: e_edit_amount = st.number_input("Total Amount (₹)", min_value=0.0, value=float(loaded_exp["total_amount"]), step=10.0, format="%.2f", key=f"ee_amt_{loaded_exp_id}")
                        with c6: e_edit_attr = st.selectbox("Attributed To", ATTRIBUTED_OPTIONS, index=ATTRIBUTED_OPTIONS.index(loaded_exp["attributed_to"]) if loaded_exp["attributed_to"] in ATTRIBUTED_OPTIONS else 0, key=f"ee_attr_{loaded_exp_id}")
                        with c7: e_edit_vendor = st.text_input("Vendor Name", value=_clean_str(loaded_exp.get("vendor_name"), ""), key=f"ee_vendor_{loaded_exp_id}")

                        c8, c9, c10 = st.columns(3)
                        with c8: e_edit_staff = st.selectbox("Linked Staff", staff_opts, index=staff_opts.index(curr_staff), key=f"ee_staff_{loaded_exp_id}")
                        with c9: e_edit_po = st.selectbox("Linked PO", po_opts, index=default_po_idx, key=f"ee_po_{loaded_exp_id}")
                        with c10: e_edit_stat = st.selectbox("Status", EXPENSE_STATUSES, index=EXPENSE_STATUSES.index(loaded_exp.get("status", "Pending")) if loaded_exp.get("status", "Pending") in EXPENSE_STATUSES else 0, key=f"ee_stat_{loaded_exp_id}")

                        st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
                        ed_c1, ed_c2 = st.columns(2, gap="small")
                        with ed_c1: e_edit_desc = st.text_input("Description", value=_clean_str(loaded_exp.get("description"), ""), key=f"ee_desc_{loaded_exp_id}")
                        with ed_c2: e_edit_remarks = st.text_input("Remarks", value=_clean_str(loaded_exp.get("remarks"), ""), key=f"ee_rem_{loaded_exp_id}")

                        btn_c1, btn_c2 = st.columns([3.5, 1.2], gap="small")
                        with btn_c1:
                            if st.button("💾 Update Expense", type="primary", use_container_width=False, key=f"btn_upd_exp_{loaded_exp_id}"):
                                if e_edit_amount <= 0: st.error("Amount must be greater than 0.")
                                else:
                                    try:
                                        p_po_id = int(e_edit_po.split("#")[1].split(" ")[0]) if "PO #" in e_edit_po else None
                                        sel_staff = None if e_edit_staff == "Select Staff" else e_edit_staff
                                        with db_conn.session as s:
                                            s.execute(text("UPDATE expenses SET expense_date = :ed, month = :month, expense_type = :et, category = :cat, sub_category = :subcat, description = :desc, total_amount = :amt, attributed_to = :attr, vendor_name = :vendor, staff_name = :staff, purchase_order_id = :poid, status = :stat, remarks = :rem, updated_at = NOW() WHERE id = :id;"), {"ed": e_edit_date, "month": e_edit_month, "et": e_edit_type, "cat": e_edit_cat, "subcat": e_edit_subcat.strip(), "desc": e_edit_desc.strip(), "amt": float(e_edit_amount), "attr": e_edit_attr, "vendor": e_edit_vendor.strip(), "staff": sel_staff, "poid": p_po_id, "stat": e_edit_stat, "rem": e_edit_remarks.strip(), "id": loaded_exp_id})

                                            if e_edit_subcat.strip().lower() == "salary":
                                                payout_res = s.execute(
                                                    text("SELECT id FROM staff_salary_payouts WHERE expense_id = :eid ORDER BY id DESC LIMIT 1;"),
                                                    {"eid": loaded_exp_id}
                                                ).fetchone()
                                                payout_params = {
                                                    "eid": loaded_exp_id,
                                                    "staff": sel_staff,
                                                    "salary_month": e_edit_month,
                                                    "salary_year": e_edit_date.year,
                                                    "amount_paid": float(e_edit_amount),
                                                    "payment_date": e_edit_date,
                                                }
                                                if payout_res:
                                                    s.execute(
                                                        text("UPDATE staff_salary_payouts SET staff_name = :staff, salary_month = :salary_month, salary_year = :salary_year, amount_paid = :amount_paid, payment_date = :payment_date WHERE id = :id;"),
                                                        {**payout_params, "id": payout_res[0]}
                                                    )
                                                else:
                                                    s.execute(
                                                        text("INSERT INTO staff_salary_payouts (expense_id, staff_name, salary_month, salary_year, amount_paid, payment_date) VALUES (:eid, :staff, :salary_month, :salary_year, :amount_paid, :payment_date);"),
                                                        payout_params
                                                    )
                                            s.commit()
                                        st.session_state.pop("_editing_expense_id", None)
                                        st.cache_data.clear()
                                        show_success_modal(f"Expense #{loaded_exp_id} updated successfully!")
                                    except Exception as e: st.error(f"Could not update expense: {e}")
                        with btn_c2:
                            if st.button("❌ Delete Expense", type="secondary", use_container_width=True, key=f"btn_del_exp_{loaded_exp_id}"):
                                confirm_delete_expense_modal(loaded_exp)

                elif expenses_summary_df.empty:
                    st.info("No expenses found in database.")
                else:
                    ek1, ek2, ek3 = st.columns(3)
                    ek1.metric("Total Expenses Incurred", f"₹{float(expenses_summary_df['total_amount'].sum()):,.2f}")
                    ek2.metric("Total Amount Paid", f"₹{float(expenses_summary_df['total_paid'].sum()):,.2f}")
                    ek3.metric("Outstanding Balance Due", f"₹{float(expenses_summary_df['balance_due'].sum()):,.2f}")

                    filter_source = expenses_summary_df.copy()
                    filter_source["Month"] = filter_source.apply(
                        lambda r: _clean_str(r.get("month"), pd.to_datetime(r["expense_date"]).strftime("%B") if pd.notna(r.get("expense_date")) else ""),
                        axis=1
                    )
                    filter_source["Category"] = filter_source["category"].apply(lambda v: _clean_str(v, ""))
                    filter_source["Sub-Category"] = filter_source["sub_category"].apply(lambda v: _clean_str(v, ""))
                    filter_source["Status"] = filter_source["status"].apply(lambda v: _clean_str(v, ""))
                    filter_source["Staff Name"] = filter_source["staff_name"].apply(lambda v: _clean_str(v, ""))
                    filtered_exp_df = apply_smart_filters(filter_source, ["Month", "Category", "Sub-Category", "Status", "Staff Name"], "expense_filters")

                    pg_c1, pg_c2 = st.columns([3.8, 1.2])
                    with pg_c1:
                        pass
                    with pg_c2:
                        page_size = st.selectbox("Rows per page", [25, 50, 100, 500], index=0, key="exp_view_page_size", label_visibility="collapsed")

                    # ID and Month removed from table columns (Month filter retained above); COPY header with Clone tooltip
                    col_weights = [0.74, 1.38, 1.85, 0.78, 0.78, 0.78, 0.72, 0.70, 0.54, 0.54, 0.54, 0.54]
                    headers = [
                        ("Date", "Expense Date"),
                        ("Category", "Category & Sub-Category"),
                        ("Description", "Description"),
                        ("Total", "Total Amount"),
                        ("Paid", "Amount Paid"),
                        ("Balance", "Balance Due"),
                        ("Status", "Payment Status"),
                        ("Staff", "Linked Staff"),
                        ("PO", "Linked Purchase Order"),
                        ("Edit", "Edit Expense"),
                        ("COPY", "Clone"),
                        ("Del", "Delete Expense"),
                    ]
                    h_cols = st.columns(col_weights, gap="small")
                    for hc, (h_text, h_tip) in zip(h_cols, headers):
                        align = "justify-content:flex-end;" if h_text in ("Total", "Paid", "Balance") else ("justify-content:center;" if h_text in ("Date", "Status", "PO", "Edit", "COPY", "Del") else "")
                        hc.markdown(f"<div class='ledger-tbl-header' style='{align}' title='{escape(h_tip)}'>{h_text}</div>", unsafe_allow_html=True)

                    for _, r in filtered_exp_df.head(int(page_size)).iterrows():
                        eid = int(r["id"])
                        dt_str = pd.to_datetime(r["expense_date"]).strftime("%d-%b-%y")
                        cat_str = _clean_str(r.get("category"), "—")
                        sub_str = _clean_str(r.get("sub_category"), "")
                        etype_str = _clean_str(r.get("expense_type"), "OPEX")
                        desc_str = _clean_str(r.get("description"), "—")
                        tot_v = float(r.get("total_amount") or 0.0)
                        paid_v = float(r.get("total_paid") or 0.0)
                        due_v = float(r.get("balance_due") or 0.0)
                        staff_str = _clean_str(r.get("staff_name"), "—")
                        po_str = f"PO #{int(r['purchase_order_id'])}" if pd.notna(r.get("purchase_order_id")) else "—"

                        rc = st.columns(col_weights, gap="small")
                        rc[0].markdown(f"<div class='ledger-cell' style='justify-content:center;'>{dt_str}</div>", unsafe_allow_html=True)
                        sub_html = f"<span class='ledger-subtext' title='{escape(etype_str + (' • ' + sub_str if sub_str else ''))}'>{escape(etype_str)}{(' • ' + escape(sub_str)) if sub_str else ''}</span>"
                        rc[1].markdown(f"<div class='ledger-cell-desc' title='{escape(cat_str)}'><span>{escape(cat_str)}</span>{sub_html}</div>", unsafe_allow_html=True)
                        rc[2].markdown(f"<div class='ledger-cell-desc' title='{escape(desc_str)}'><span>{escape(desc_str)}</span></div>", unsafe_allow_html=True)
                        rc[3].markdown(f"<div class='ledger-amt-total'>₹{tot_v:,.0f}</div>", unsafe_allow_html=True)
                        rc[4].markdown(f"<div class='ledger-amt-paid'>₹{paid_v:,.0f}</div>", unsafe_allow_html=True)
                        due_cls = "ledger-amt-due" if due_v > 0.009 else "ledger-cell"
                        rc[5].markdown(f"<div class='{due_cls}' style='justify-content:flex-end;'>₹{due_v:,.0f}</div>", unsafe_allow_html=True)
                        rc[6].markdown(f"<div class='ledger-cell' style='justify-content:center;'>{_status_pill_html(r.get('status'))}</div>", unsafe_allow_html=True)
                        rc[7].markdown(f"<div class='ledger-cell' title='{escape(staff_str)}'>{escape(staff_str)}</div>", unsafe_allow_html=True)
                        rc[8].markdown(f"<div class='ledger-cell' style='justify-content:center;'>{escape(po_str)}</div>", unsafe_allow_html=True)

                        if rc[9].button("✏️", key=f"row_edit_exp_{eid}", help="Edit", use_container_width=True):
                            st.session_state["_editing_expense_id"] = eid
                            st.rerun()
                        if rc[10].button("📋", key=f"row_clone_exp_{eid}", help="Clone", use_container_width=True):
                            _populate_expense_clone_state(r.to_dict())
                            st.session_state.pop("_editing_expense_id", None)
                            st.session_state["_pending_e_sub_mode_rad"] = "Add New Expense"
                            st.toast(f"Cloned Expense #{eid} into Add New Expense!", icon="📋")
                            st.rerun()
                        if rc[11].button("❌", key=f"row_del_exp_{eid}", help="Delete", use_container_width=True):
                            confirm_delete_expense_modal(r.to_dict())

        # ==================================================================
        # SECTION 2: PAYMENTS (CASH OUTFLOWS)
        # ==================================================================
        elif exp_nav == "💳 Payments (Cash Outflows)":
            p_sub_mode = st.radio("Action", ["View Payments", "Record New Payment"], horizontal=True, key="p_sub_mode_rad")
            payments_df, expenses_summary_df = load_db_payments_df(), load_db_expenses_summary_df()

            if p_sub_mode == "Record New Payment":
                st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
                st.session_state.pop("_editing_payment_id", None)
                pass
                if expenses_summary_df.empty: st.info("No expenses found to make payment against.")
                else:
                    po_net_map = {}
                    if db_conn is not None:
                        try:
                            po_rec_df = db_conn.query(
                                """
                                SELECT
                                    p.id AS po_id,
                                    p.notes AS po_notes,
                                    COALESCE((
                                        SELECT SUM(sr.payment_amount)
                                        FROM stock_received sr
                                        WHERE sr.purchase_order_id = p.id
                                          AND COALESCE(sr.payment_amount, 0) > 0
                                    ), 0) AS received_payment_amount,
                                    COALESCE((
                                        SELECT SUM(pi.ordered_units * f.cost_price)
                                        FROM purchase_order_items pi
                                        JOIN flavors f ON f.code = pi.flavor_code
                                        WHERE pi.order_id = p.id
                                    ), 0) AS po_gross_amount
                                FROM purchase_orders p;
                                """,
                                ttl="60s"
                            )
                            for _, pr in po_rec_df.iterrows():
                                poid = int(pr["po_id"])
                                rec_pay_amt = float(_num(pr.get("received_payment_amount")))
                                po_gross = float(_num(pr.get("po_gross_amount")))
                                notes_str = str(pr.get("po_notes") or "")
                                final_match = re.search(r"Final:\s*₹?([\d,]+(?:\.\d+)?)", notes_str)
                                disc_match = re.search(r"\[Discount:\s*([\d.]+)%", notes_str)
                                if rec_pay_amt > 0:
                                    po_net_map[poid] = rec_pay_amt
                                elif final_match:
                                    po_net_map[poid] = _num(final_match.group(1))
                                elif disc_match and po_gross > 0:
                                    disc_p = float(disc_match.group(1))
                                    po_net_map[poid] = po_gross * (1.0 - disc_p / 100.0)
                                elif po_gross > 0:
                                    po_net_map[poid] = po_gross
                        except Exception:
                            po_net_map = {}

                    exp_work_df = expenses_summary_df.copy()
                    def _resolve_bill_total(row):
                        exp_tot = float(_num(row.get("total_amount")))
                        poid = row.get("purchase_order_id")
                        if pd.notna(poid) and int(poid) in po_net_map and po_net_map[int(poid)] > 0:
                            return float(po_net_map[int(poid)]) if exp_tot <= 0 else exp_tot
                        return exp_tot

                    exp_work_df["effective_total"] = exp_work_df.apply(_resolve_bill_total, axis=1)
                    exp_work_df["effective_due"] = (exp_work_df["effective_total"] - exp_work_df["total_paid"].astype(float)).clip(lower=0.0)

                    clone_pay_payload = st.session_state.get("_clone_payment_payload")
                    if clone_pay_payload:
                        st.session_state["filter_unpaid_exp"] = False

                    unpaid_filter = st.checkbox("Show only expenses with pending balance", value=True, key="filter_unpaid_exp")
                    filtered_exp = exp_work_df[exp_work_df["effective_due"] > 0.009] if unpaid_filter else exp_work_df
                    if filtered_exp.empty: st.success("🎉 All logged expenses are fully settled!")
                    else:
                        f_records = filtered_exp.to_dict("records")
                        f_labels = [
                            f"Expense #{r['id']}"
                            f"{(' (PO #' + str(int(r['purchase_order_id'])) + ')') if pd.notna(r.get('purchase_order_id')) else ''}"
                            f" — {r['category']} — {_clean_str(r.get('description') or r.get('vendor_name'), 'No desc')}"
                            f" (Total: ₹{float(r['effective_total']):,.2f} | Due: ₹{float(r['effective_due']):,.2f})"
                            for r in f_records
                        ]
                        if clone_pay_payload and "expense_id" in clone_pay_payload:
                            c_eid = int(clone_pay_payload["expense_id"])
                            for idx_f, frec in enumerate(f_records):
                                if int(frec["id"]) == c_eid:
                                    st.session_state["pay_target_select"] = f_labels[idx_f]
                                    break

                        selected_label = st.selectbox("Select Expense to Pay", f_labels, key="pay_target_select")
                        target_exp = f_records[f_labels.index(selected_label)]
                        target_exp_id = int(target_exp["id"])
                        bill_total = float(target_exp["effective_total"])
                        already_paid = float(target_exp["total_paid"])
                        curr_due = round(max(0.0, float(target_exp["effective_due"])), 2)

                        m1, m2, m3 = st.columns(3)
                        m1.metric("Bill Total", f"₹{bill_total:,.2f}")
                        m2.metric("Already Paid", f"₹{already_paid:,.2f}")
                        m3.metric("Outstanding Balance", f"₹{curr_due:,.2f}")

                        amt_widget_key = f"rec_p_amt_{target_exp_id}_{curr_due:.2f}"
                        if clone_pay_payload and int(clone_pay_payload.get("expense_id", -1)) == target_exp_id:
                            st.session_state[amt_widget_key] = float(clone_pay_payload.get("amount_paid") or curr_due)
                            st.session_state[f"rec_p_date_{target_exp_id}"] = date.today()
                            if clone_pay_payload.get("payment_mode") in PAYMENT_MODES:
                                st.session_state[f"rec_p_mode_{target_exp_id}"] = clone_pay_payload["payment_mode"]
                            st.session_state[f"rec_p_ref_{target_exp_id}"] = _clean_str(clone_pay_payload.get("ref_no"), "")
                            st.session_state[f"rec_p_to_{target_exp_id}"] = _clean_str(clone_pay_payload.get("paid_to") or target_exp.get("vendor_name"), "")
                            st.session_state[f"rec_p_notes_{target_exp_id}"] = _clean_str(clone_pay_payload.get("notes"), "")
                            st.session_state.pop("_clone_payment_payload", None)
                        elif amt_widget_key not in st.session_state:
                            st.session_state[amt_widget_key] = curr_due

                        c1, c2, c3 = st.columns(3)
                        with c1: new_p_date = st.date_input("Payment Date", value=date.today(), key=f"rec_p_date_{target_exp_id}", format="DD-MM-YYYY")
                        with c2: new_p_amount = st.number_input("Amount to Pay (₹)", min_value=0.0, step=10.0, format="%.2f", key=amt_widget_key)
                        with c3: new_p_mode = st.selectbox("Payment Mode", PAYMENT_MODES, index=0, key=f"rec_p_mode_{target_exp_id}")

                        c4, c5 = st.columns(2)
                        with c4: new_p_ref = st.text_input("Transaction / UTR Ref No.", placeholder="e.g. UPI Ref, IMPS Txn ID", key=f"rec_p_ref_{target_exp_id}")
                        with c5: new_p_to = st.text_input("Paid To", value=_clean_str(target_exp.get("vendor_name"), ""), key=f"rec_p_to_{target_exp_id}")
                        new_p_notes = st.text_input("Payment Notes / Remarks", placeholder="e.g. Part payment tranche 1...", key=f"rec_p_notes_{target_exp_id}")
                        new_p_receipt = st.file_uploader(
                            "Receipt / Bill Image (Optional)",
                            type=["jpg", "jpeg", "png", "webp"],
                            accept_multiple_files=False,
                            key=f"rec_p_receipt_{target_exp_id}"
                        )
                        st.caption("Accepted: JPG, JPEG, PNG, WEBP • maximum 3.5 MB")

                        if st.button("💳 Disburse Payment", type="primary", use_container_width=False, key=f"btn_disburse_{target_exp_id}"):
                            if new_p_amount <= 0: st.error("Please enter a payment amount greater than 0.")
                            else:
                                try:
                                    new_p_receipt_data = prepare_payment_receipt(new_p_receipt)
                                    with db_conn.session as s:
                                        pay_res = s.execute(
                                            text("INSERT INTO expense_payments (expense_id, payment_date, amount_paid, payment_mode, ref_no, paid_to, paid_by, notes, receipt_file_name, receipt_mime_type, receipt_file_size_bytes, receipt_image_base64, receipt_uploaded_at) VALUES (:eid, :pdate, :pamt, :pmode, :pref, :pto, :pby, :notes, :rname, :rmime, :rsize, :rbase64, :ruploaded) RETURNING id;"),
                                            {
                                                "eid": target_exp_id, "pdate": new_p_date, "pamt": float(new_p_amount),
                                                "pmode": new_p_mode, "pref": new_p_ref.strip(), "pto": new_p_to.strip(),
                                                "pby": "Admin", "notes": new_p_notes.strip(),
                                                "rname": new_p_receipt_data["name"], "rmime": new_p_receipt_data["mime"],
                                                "rsize": new_p_receipt_data["size"], "rbase64": new_p_receipt_data["base64"],
                                                "ruploaded": new_p_receipt_data["uploaded_at"],
                                            }
                                        )
                                        new_payment_id = pay_res.scalar()
                                        new_status = "Paid" if (already_paid + float(new_p_amount)) >= (bill_total - 0.009) else "Partially Paid"
                                        s.execute(text("UPDATE expenses SET status = :stat, updated_at = NOW() WHERE id = :id;"), {"stat": new_status, "id": target_exp_id})

                                        salary_res = s.execute(
                                            text("SELECT sub_category FROM expenses WHERE id = :eid;"),
                                            {"eid": target_exp_id}
                                        ).fetchone()
                                        if salary_res and str(salary_res[0] or "").strip().lower() == "salary":
                                            payout_res = s.execute(
                                                text("SELECT id FROM staff_salary_payouts WHERE expense_id = :eid ORDER BY id DESC LIMIT 1;"),
                                                {"eid": target_exp_id}
                                            ).fetchone()
                                            if payout_res:
                                                s.execute(
                                                    text("UPDATE staff_salary_payouts SET payment_id = :payment_id WHERE id = :id;"),
                                                    {"payment_id": new_payment_id, "id": payout_res[0]}
                                                )
                                            else:
                                                exp_res = s.execute(
                                                    text("SELECT staff_name, month, expense_date, total_amount FROM expenses WHERE id = :eid;"),
                                                    {"eid": target_exp_id}
                                                ).fetchone()
                                                if exp_res:
                                                    s.execute(
                                                        text("INSERT INTO staff_salary_payouts (payment_id, expense_id, staff_name, salary_month, salary_year, amount_paid, payment_date) VALUES (:payment_id, :eid, :staff, :salary_month, :salary_year, :amount_paid, :payment_date);"),
                                                        {
                                                            "payment_id": new_payment_id,
                                                            "eid": target_exp_id,
                                                            "staff": exp_res[0],
                                                            "salary_month": exp_res[1],
                                                            "salary_year": pd.to_datetime(exp_res[2]).year,
                                                            "amount_paid": float(new_p_amount),
                                                            "payment_date": new_p_date,
                                                        }
                                                    )
                                        s.commit()
                                    st.cache_data.clear()
                                    show_success_modal(f"Payment of ₹{new_p_amount:,.2f} recorded successfully for Expense #{target_exp_id}!")
                                except Exception as e: st.error(f"Could not record payment: {e}")

            elif p_sub_mode == "View Payments":
                editing_pay_id = st.session_state.get("_editing_payment_id")

                if editing_pay_id is not None and not payments_df.empty:
                    pmatch = payments_df[payments_df["id"] == int(editing_pay_id)]
                    if pmatch.empty:
                        st.session_state.pop("_editing_payment_id", None)
                        st.rerun()
                    else:
                        loaded_pay = pmatch.iloc[0].to_dict()
                        loaded_pay_id = int(loaded_pay["id"])

                        ptop1, ptop2 = st.columns([1.6, 4.4])
                        with ptop1:
                            if st.button("⬅ Back to Payments List", key="back_from_edit_pay", type="primary", use_container_width=True):
                                st.session_state.pop("_editing_payment_id", None)
                                st.rerun()
                        with ptop2:
                            st.markdown(f"#### ✏️ Editing Payment #{loaded_pay_id} (Expense #{int(loaded_pay['expense_id'])})")

                        c1, c2, c3 = st.columns(3)
                        with c1: ep_date = st.date_input("Payment Date", value=pd.to_datetime(loaded_pay["payment_date"]).date(), key=f"ep_dt_{loaded_pay_id}", format="DD-MM-YYYY")
                        with c2: ep_amt = st.number_input("Amount Paid (₹)", min_value=0.0, value=float(loaded_pay["amount_paid"]), step=10.0, format="%.2f", key=f"ep_amt_{loaded_pay_id}")
                        with c3: ep_mode = st.selectbox("Payment Mode", PAYMENT_MODES, index=PAYMENT_MODES.index(loaded_pay["payment_mode"]) if loaded_pay["payment_mode"] in PAYMENT_MODES else 0, key=f"ep_mode_{loaded_pay_id}")

                        c4, c5 = st.columns(2)
                        with c4: ep_ref = st.text_input("Transaction / UTR Ref No.", value=_clean_str(loaded_pay.get("ref_no"), ""), key=f"ep_ref_{loaded_pay_id}")
                        with c5: ep_to = st.text_input("Paid To", value=_clean_str(loaded_pay.get("paid_to"), ""), key=f"ep_to_{loaded_pay_id}")
                        ep_notes = st.text_input("Payment Notes", value=_clean_str(loaded_pay.get("notes"), ""), key=f"ep_notes_{loaded_pay_id}")

                        p_btn1, p_btn2 = st.columns([3.5, 1.2], gap="small")
                        with p_btn1:
                            if st.button("💾 Update Payment", type="primary", use_container_width=False, key=f"btn_upd_pay_{loaded_pay_id}"):
                                if ep_amt <= 0: st.error("Amount must be greater than 0.")
                                else:
                                    try:
                                        with db_conn.session as s:
                                            s.execute(text("UPDATE expense_payments SET payment_date = :pdate, amount_paid = :pamt, payment_mode = :pmode, ref_no = :pref, paid_to = :pto, notes = :notes WHERE id = :id;"), {"pdate": ep_date, "pamt": float(ep_amt), "pmode": ep_mode, "pref": ep_ref.strip(), "pto": ep_to.strip(), "notes": ep_notes.strip(), "id": loaded_pay_id})

                                            s.execute(
                                                text("""
                                                    UPDATE staff_salary_payouts sp
                                                    SET amount_paid = :pamt, payment_date = :pdate
                                                    WHERE sp.payment_id = :pid
                                                      AND EXISTS (
                                                          SELECT 1 FROM expenses e
                                                          WHERE e.id = sp.expense_id
                                                            AND LOWER(TRIM(COALESCE(e.sub_category, ''))) = 'salary'
                                                      );
                                                """),
                                                {"pamt": float(ep_amt), "pdate": ep_date, "pid": loaded_pay_id}
                                            )
                                            s.commit()
                                        st.session_state.pop("_editing_payment_id", None)
                                        st.cache_data.clear()
                                        show_success_modal(f"Payment #{loaded_pay_id} updated successfully!")
                                    except Exception as e: st.error(f"Could not update payment: {e}")
                        with p_btn2:
                            if st.button("❌ Delete Payment", type="secondary", use_container_width=True, key=f"btn_del_pay_{loaded_pay_id}"):
                                confirm_delete_payment_modal(loaded_pay)

                elif payments_df.empty:
                    st.info("No payment transactions found in database.")
                else:
                    st.metric("Total Payments Disbursed", f"₹{float(payments_df['amount_paid'].sum()):,.2f}")
                    filter_pay_df = payments_df.copy()
                    filter_pay_df["Mode"] = filter_pay_df["payment_mode"].apply(lambda v: _clean_str(v, ""))
                    filter_pay_df["Paid To"] = filter_pay_df["paid_to"].apply(lambda v: _clean_str(v, ""))
                    filtered_pay = apply_smart_filters(filter_pay_df, ["Mode", "Paid To"], "payment_filters")

                    p_pg1, p_pg2 = st.columns([3.8, 1.2])
                    with p_pg1:
                        pass
                    with p_pg2:
                        pay_page_size = st.selectbox("Rows per page", [25, 50, 100, 500], index=0, key="pay_view_page_size", label_visibility="collapsed")

                    # ID and RCPT removed from table list; View Receipt section below removed completely
                    p_weights = [0.80, 1.90, 0.90, 1.15, 1.25, 1.65, 0.54, 0.54, 0.54]
                    p_headers = [
                        ("Date", "Payment Date"),
                        ("Expense Link", "Linked Expense"),
                        ("Amount", "Amount Paid"),
                        ("Mode", "Payment Mode"),
                        ("Paid To", "Payee"),
                        ("Notes", "Payment Notes"),
                        ("Edit", "Edit Payment"),
                        ("COPY", "Clone"),
                        ("Del", "Delete Payment"),
                    ]
                    ph_cols = st.columns(p_weights, gap="small")
                    for phc, (ph_text, ph_tip) in zip(ph_cols, p_headers):
                        align = "justify-content:flex-end;" if ph_text == "Amount" else ("justify-content:center;" if ph_text in ("Date", "Edit", "COPY", "Del") else "")
                        phc.markdown(f"<div class='ledger-tbl-header' style='{align}' title='{escape(ph_tip)}'>{ph_text}</div>", unsafe_allow_html=True)

                    for _, r in filtered_pay.head(int(pay_page_size)).iterrows():
                        pid = int(r["id"])
                        eid = int(r["expense_id"])
                        p_dt = pd.to_datetime(r["payment_date"]).strftime("%d-%b-%y")
                        cat_str = _clean_str(r.get("category"), "Expense")
                        sub_str = _clean_str(r.get("sub_category"), "")
                        exp_tot = float(r.get("expense_total") or 0.0)
                        amt_v = float(r.get("amount_paid") or 0.0)
                        mode_str = _clean_str(r.get("payment_mode"), "—")
                        pto_str = _clean_str(r.get("paid_to"), "—")
                        notes_str = _clean_str(r.get("notes"), "—")

                        prc = st.columns(p_weights, gap="small")
                        prc[0].markdown(f"<div class='ledger-cell' style='justify-content:center;'>{p_dt}</div>", unsafe_allow_html=True)
                        prc[1].markdown(
                            f"<div class='ledger-cell-desc' title='#{eid} — {escape(cat_str)}'><span>#{eid} — {escape(cat_str)}</span>"
                            f"<span class='ledger-subtext'>Bill: ₹{exp_tot:,.0f}{(' • ' + escape(sub_str)) if sub_str else ''}</span></div>",
                            unsafe_allow_html=True
                        )
                        prc[2].markdown(f"<div class='ledger-amt-paid'>₹{amt_v:,.2f}</div>", unsafe_allow_html=True)
                        prc[3].markdown(f"<div class='ledger-cell' title='{escape(mode_str)}'>{escape(mode_str)}</div>", unsafe_allow_html=True)
                        prc[4].markdown(f"<div class='ledger-cell' title='{escape(pto_str)}'>{escape(pto_str)}</div>", unsafe_allow_html=True)
                        prc[5].markdown(f"<div class='ledger-cell-desc' title='{escape(notes_str)}'><span>{escape(notes_str)}</span></div>", unsafe_allow_html=True)

                        if prc[6].button("✏️", key=f"row_edit_pay_{pid}", help="Edit", use_container_width=True):
                            st.session_state["_editing_payment_id"] = pid
                            st.rerun()
                        if prc[7].button("📋", key=f"row_clone_pay_{pid}", help="Clone", use_container_width=True):
                            st.session_state["_clone_payment_payload"] = {
                                "expense_id": eid,
                                "amount_paid": amt_v,
                                "payment_mode": mode_str,
                                "ref_no": _clean_str(r.get("ref_no"), ""),
                                "paid_to": _clean_str(r.get("paid_to"), ""),
                                "notes": _clean_str(r.get("notes"), ""),
                            }
                            st.session_state.pop("_editing_payment_id", None)
                            st.session_state["_pending_p_sub_mode_rad"] = "Record New Payment"
                            st.toast(f"Cloned Payment #{pid} into Record New Payment!", icon="📋")
                            st.rerun()
                        if prc[8].button("❌", key=f"row_del_pay_{pid}", help="Delete", use_container_width=True):
                            confirm_delete_payment_modal(r.to_dict())

        # ==================================================================
        # SECTION 3: SUMMARY & DATE REPORTS
        # ==================================================================
        elif exp_nav == "📊 Summary & Date Reports":
            pass
            expenses_summary_df, payments_df = load_db_expenses_summary_df(), load_db_payments_df()

            if expenses_summary_df.empty and payments_df.empty: st.info("No expense or payment records found in database.")
            else:
                all_dts = []
                if not expenses_summary_df.empty: all_dts += [pd.to_datetime(expenses_summary_df["expense_date"]).min().date(), pd.to_datetime(expenses_summary_df["expense_date"]).max().date()]
                if not payments_df.empty: all_dts += [pd.to_datetime(payments_df["payment_date"]).min().date(), pd.to_datetime(payments_df["payment_date"]).max().date()]
                min_exp_d, max_exp_d = min(all_dts), max(all_dts)

                exp_filter_mode = st.radio(
                    "Filter By",
                    ["Month", "Custom Date Range"],
                    horizontal=True,
                    key="expense_report_filter_mode"
                )

                if exp_filter_mode == "Month":
                    rc1, rc2 = st.columns(2)
                    exp_month_names = list(calendar.month_name)[1:]
                    default_exp_month = max_exp_d.month
                    default_exp_year = max_exp_d.year
                    with rc1:
                        exp_month_name = st.selectbox(
                            "Month",
                            exp_month_names,
                            index=default_exp_month - 1,
                            key="exp_rpt_month"
                        )
                        exp_month_num = exp_month_names.index(exp_month_name) + 1
                    with rc2:
                        exp_year = st.number_input(
                            "Year",
                            min_value=min_exp_d.year,
                            max_value=max(max_exp_d.year, date.today().year),
                            value=default_exp_year,
                            step=1,
                            key="exp_rpt_year"
                        )
                    rpt_start = date(int(exp_year), int(exp_month_num), 1)
                    rpt_end = date(int(exp_year), int(exp_month_num), calendar.monthrange(int(exp_year), int(exp_month_num))[1])
                else:
                    rc1, rc2 = st.columns(2)
                    with rc1:
                        rpt_start = st.date_input(
                            "Start Date",
                            value=max(min_exp_d, max_exp_d - timedelta(days=29)),
                            min_value=min_exp_d,
                            max_value=max_exp_d,
                            key="exp_rpt_start",
                            format="DD-MM-YYYY"
                        )
                    with rc2:
                        rpt_end = st.date_input(
                            "End Date",
                            value=max_exp_d,
                            min_value=min_exp_d,
                            max_value=max_exp_d,
                            key="exp_rpt_end",
                            format="DD-MM-YYYY"
                        )
                if rpt_start > rpt_end:
                    st.error("Start Date must be before or equal to End Date.")
                    rpt_start, rpt_end = rpt_end, rpt_start

                f_exp = expenses_summary_df[(pd.to_datetime(expenses_summary_df["expense_date"]).dt.date >= rpt_start) & (pd.to_datetime(expenses_summary_df["expense_date"]).dt.date <= rpt_end)] if not expenses_summary_df.empty else pd.DataFrame()
                f_pay = payments_df[(pd.to_datetime(payments_df["payment_date"]).dt.date >= rpt_start) & (pd.to_datetime(payments_df["payment_date"]).dt.date <= rpt_end)] if not payments_df.empty else pd.DataFrame()

                m1, m2, m3 = st.columns(3)
                m1.metric("Expenses Incurred (In Range)", f"₹{float(f_exp['total_amount'].sum()) if not f_exp.empty else 0.0:,.2f}")
                m2.metric("Actual Cash Paid Out", f"₹{float(f_pay['amount_paid'].sum()) if not f_pay.empty else 0.0:,.2f}")
                m3.metric("Outstanding Unpaid Dues", f"₹{float(f_exp['balance_due'].sum()) if not f_exp.empty else 0.0:,.2f}")

                st.markdown("---"); ch_col1, ch_col2 = st.columns(2)
                with ch_col1:
                    st.markdown("#### Expenses by Category")
                    if not f_exp.empty: st.altair_chart(alt.Chart(f_exp.groupby("category")["total_amount"].sum().reset_index()).mark_bar(color="#1E2252").encode(x=alt.X("category:N", title="", sort="-y", axis=alt.Axis(labelAngle=-30)), y=alt.Y("total_amount:Q", title="Incurred (₹)"), tooltip=[alt.Tooltip("category", title="Category"), alt.Tooltip("total_amount:Q", title="Amount", format=",.2f")]).properties(height=260), use_container_width=True)
                    else: st.caption("No expenses in this range.")
                with ch_col2:
                    st.markdown("#### Expenses by Cart / Attribution")
                    if not f_exp.empty: st.altair_chart(alt.Chart(f_exp.groupby("attributed_to")["total_amount"].sum().reset_index()).mark_bar(color="#4F46E5").encode(x=alt.X("attributed_to:N", title="", sort="-y", axis=alt.Axis(labelAngle=-20)), y=alt.Y("total_amount:Q", title="Total (₹)"), tooltip=[alt.Tooltip("attributed_to", title="Entity"), alt.Tooltip("total_amount:Q", title="Amount", format=",.2f")]).properties(height=260), use_container_width=True)
                    else: st.caption("No expenses in this range.")

                st.markdown("#### Payments Disbursed by Mode")
                if not f_pay.empty: st.dataframe(f_pay.groupby("payment_mode")["amount_paid"].sum().reset_index().rename(columns={"payment_mode": "Payment Mode", "amount_paid": "Amount Paid (₹)"}), hide_index=True, use_container_width=True, column_config={"Amount Paid (₹)": st.column_config.NumberColumn(format="₹%,.2f")})
                else: st.caption("No payments in this range.")

    # ======================================================================
    # PAGE 7: STAFF & PAYROLL (KYC, Leaves, Plans & Settlement)
    # ======================================================================
    elif page == "Staff & Payroll" and user_role == "admin":
        st.subheader("Staff & Payroll Management")
        pass

        staff_tab_sel = st.radio(
            "Section", 
            ["👥 Staff Directory & KYC", "📅 Attendance & Leave", "⚙️ Compensation Plans", "🍱 Monthly Food Allowance", "💵 Monthly Dues & Settlement"], 
            horizontal=True, 
            key="staff_top_nav"
        )

        staff_df = load_full_staff_df()

        if staff_tab_sel == "👥 Staff Directory & KYC":
            st_mode = st.radio("Mode", ["View All Staff", "Add New Staff", "Edit Staff Profile & KYC"], horizontal=True, key="staff_dir_mode")

            if st_mode == "Add New Staff":
                st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
                pass

                with st.form("new_staff_form"):
                    sc1, sc2, sc3 = st.columns(3)
                    with sc1:
                        new_s_name = st.text_input("Display Name (App) *", placeholder="e.g. Ramesh", key="add_s_name")
                    with sc2:
                        new_s_fullname = st.text_input("Full Legal Name", placeholder="e.g. Ramesh Kumar", key="add_s_fname")
                    with sc3:
                        new_s_phone = st.text_input("Mobile Number", placeholder="e.g. 9876543210", key="add_s_phone")

                    sc_role, sc_gender, sc4, sc5 = st.columns(4)
                    with sc_role:
                        new_s_role = st.selectbox("Role / Designation", ["Cart Operator", "Ops Coordinator", "Manager", "Helper"], key="add_s_role")
                    with sc_gender:
                        new_s_gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="add_s_gender")
                    with sc4:
                        new_s_status = st.selectbox("Status", STAFF_STATUSES, index=0, key="add_s_status")
                    with sc5:
                        new_s_doj = st.date_input("Date of Joining", value=date.today(), key="add_s_doj", format="DD-MM-YYYY")

                    sc6, sc_dol, sc7, sc8 = st.columns(4)
                    with sc6:
                        new_s_dob = st.date_input("Date of Birth", value=date(1995, 1, 1), key="add_s_dob", format="DD-MM-YYYY")
                    with sc_dol:
                        new_s_dol = st.date_input("Last Working Day", value=None, key="add_s_dol", format="DD-MM-YYYY")
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
                        new_s_monthly_food = st.number_input("Monthly Food & Tea Allowance (₹/month)", min_value=0.0, value=0.0, step=100.0, key="add_s_monthly_food")
                    with cp5:
                        new_s_monthly_fuel = st.number_input("Monthly Fuel Allowance (₹/month)", min_value=0.0, value=0.0, step=100.0, key="add_s_monthly_fuel")

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
                                        name, full_name, role, gender, status, phone_number, emergency_contact_name, emergency_contact_phone,
                                        date_of_birth, pan_number, aadhaar_number, current_address,
                                        permanent_address, date_of_joining, date_of_leaving, notes
                                    ) VALUES (
                                        :name, :full_name, :role, :gender, :status, :phone, :emg_n, :emg_p,
                                        :dob, :pan, :aadhaar, :caddr,
                                        :paddr, :doj, :dol, :notes
                                    ) RETURNING id;
                                    """),
                                    {
                                        "name": new_s_name.strip(), "full_name": new_s_fullname.strip(), 
                                        "role": new_s_role, "gender": new_s_gender, "status": new_s_status, 
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
                                        food_tea_allowance_mode, monthly_food_tea_allowance, monthly_fuel_allowance
                                    ) VALUES (
                                        :sid, :efrom, :sal, :thresh, :comm, 'monthly', :mfood, :mfuel
                                    );
                                    """),
                                    {
                                        "sid": new_sid, "efrom": new_s_doj, "sal": float(new_s_salary),
                                        "thresh": float(new_s_thresh), "comm": float(new_s_comm_pct),
                                        "mfood": float(new_s_monthly_food), "mfuel": float(new_s_monthly_fuel)
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
                    disp_staff["Role"] = disp_staff["role"].fillna("Cart Operator")
                    disp_staff["Gender"] = disp_staff["gender"].fillna("—")
                    disp_staff["Daily Fixed Rate"] = disp_staff["monthly_fixed_salary"].apply(lambda v: f"₹600/day (₹{_num(v):,.0f}/mo)")
                    disp_staff["Commission"] = disp_staff.apply(lambda r: f"{_num(r['commission_percentage']):.0f}% > ₹{_num(r['commission_threshold_daily']):,.0f}", axis=1)
                    disp_staff["Joined"] = pd.to_datetime(disp_staff["date_of_joining"]).dt.strftime("%d-%b-%y")

                    summary_cols = ["id", "name", "Role", "Gender", "status", "phone_number", "Joined", "Daily Fixed Rate"]
                    st.dataframe(
                        disp_staff[summary_cols].rename(columns={
                            "id": "ID", "name": "Name", "status": "Status", "phone_number": "Phone"
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
                    k1.write(f"**Role:** {s_row.get('role') or 'Cart Operator'}")
                    k1.write(f"**Gender:** {s_row.get('gender') or '—'}")
                
                    k2.write(f"**Date of Birth:** {pd.to_datetime(s_row['date_of_birth']).strftime('%d-%b-%y') if pd.notna(s_row['date_of_birth']) else '—'}")
                    k2.write(f"**PAN Number:** {s_row['pan_number'] or '—'}")
                
                    k3.write(f"**Emergency Contact:** {s_row['emergency_contact_name'] or '—'} ({s_row['emergency_contact_phone'] or '—'})")
                    k3.write(f"**Last Working Day:** {pd.to_datetime(s_row['date_of_leaving']).strftime('%d-%b-%y') if pd.notna(s_row['date_of_leaving']) else '—'}")

                    st.write(f"**Current Address:** {s_row['current_address'] or '—'}")
                    st.write(f"**Permanent Address:** {s_row['permanent_address'] or '—'}")
                    if s_row.get("notes"):
                        st.caption(f"Remarks: {s_row['notes']}")

            elif st_mode == "Edit Staff Profile & KYC":
                st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
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

                        roles_opts = ["Cart Operator", "Ops Coordinator", "Manager", "Helper"]
                        curr_role = str(s_edit.get("role") or "Cart Operator")
                        if curr_role not in roles_opts: roles_opts.append(curr_role)

                        gender_opts = ["Male", "Female", "Other"]
                        curr_gender = str(s_edit.get("gender") or "Male")
                        if curr_gender not in gender_opts: gender_opts.append(curr_gender)

                        ec_role, ec_gender, ec4, ec5 = st.columns(4)
                        with ec_role:
                            e_role = st.selectbox("Role / Designation", roles_opts, index=roles_opts.index(curr_role), key=f"e_role_{s_id}")
                        with ec_gender:
                            e_gender = st.selectbox("Gender", gender_opts, index=gender_opts.index(curr_gender), key=f"e_gender_{s_id}")
                        with ec4:
                            stat_idx = STAFF_STATUSES.index(s_edit["status"]) if s_edit["status"] in STAFF_STATUSES else 0
                            e_status = st.selectbox("Status", STAFF_STATUSES, index=stat_idx, key=f"e_status_{s_id}")
                        with ec5:
                            doj_val = pd.to_datetime(s_edit["date_of_joining"]).date() if pd.notna(s_edit["date_of_joining"]) else date.today()
                            e_doj = st.date_input("Date of Joining", value=doj_val, key=f"e_doj_{s_id}", format="DD-MM-YYYY")

                        ec6, ec_dol, ec7, ec8 = st.columns(4)
                        with ec6:
                            dob_val = pd.to_datetime(s_edit["date_of_birth"]).date() if pd.notna(s_edit["date_of_birth"]) else date(1995, 1, 1)
                            e_dob = st.date_input("Date of Birth", value=dob_val, key=f"e_dob_{s_id}", format="DD-MM-YYYY")
                        with ec_dol:
                            dol_val = pd.to_datetime(s_edit["date_of_leaving"]).date() if pd.notna(s_edit["date_of_leaving"]) else None
                            e_dol = st.date_input("Last Working Day", value=dol_val, key=f"e_dol_{s_id}", format="DD-MM-YYYY")
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
                                        "name": e_name.strip(), "full_name": e_fullname.strip(), 
                                        "role": e_role, "gender": e_gender, "status": e_status, 
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
                                        SET name = :name, full_name = :full_name, role = :role, gender = :gender, status = :status, phone_number = :phone,
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
            pass

            att_mode = st.radio("Action", ["Record Staff Leave / Absence", "View Attendance & Leaves", "Edit Past Leave Entry"], horizontal=True, key="att_sub_nav")

            if att_mode == "Record Staff Leave / Absence":
                st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
                if staff_df.empty:
                    st.info("No staff registered yet.")
                else:
                    st_names = staff_df["name"].tolist()
                    with st.form("add_leave_form"):
                        ac1, ac2 = st.columns(2)
                        with ac1:
                            att_staff_name = st.selectbox("Staff Member *", st_names, key="leave_sname")
                        with ac2:
                            att_date = st.date_input("Leave Date *", value=date.today(), key="leave_dt", format="DD-MM-YYYY")

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
                            st.cache_data.clear()
                            show_success_modal(f"{att_status} ({att_type}) recorded for {att_staff_name} on {att_date.strftime('%d-%b-%y')}!")
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
                    disp_att["attendance_date"] = pd.to_datetime(disp_att["attendance_date"]).dt.strftime("%d-%b-%y")
                
                    disp_att = disp_att[["id", "staff_name", "attendance_date", "status", "leave_type", "reason", "recorded_by"]].rename(columns={
                        "id": "ID", "staff_name": "Staff Name", "attendance_date": "Date", "status": "Status",
                        "leave_type": "Leave Type", "reason": "Reason", "recorded_by": "Recorded By"
                    })
                    disp_att = apply_smart_filters(disp_att, ["Staff Name", "Status", "Leave Type"], "attendance_filters")
                    st.dataframe(disp_att, hide_index=True, use_container_width=True)

            elif att_mode == "Edit Past Leave Entry":
                st.markdown('<span class="kulfi-entry-80-scope"></span>', unsafe_allow_html=True)
                att_df = load_staff_attendance_df()
                if att_df.empty:
                    st.info("No attendance records to edit.")
                else:
                    att_records = att_df.to_dict("records")
                    att_labels = [
                        f"#{r['id']} — {r['staff_name']} on {pd.to_datetime(r['attendance_date']).strftime('%d-%b-%y')} ({r['status']} - {r['leave_type']})"
                        for r in att_records
                    ]
                    sel_att_label = st.selectbox("Select Leave Entry to Edit", att_labels, key="edit_att_select")
                    loaded_att = att_records[att_labels.index(sel_att_label)]
                    loaded_att_id = loaded_att["id"]

                    c1, c2 = st.columns(2)
                    with c1:
                        e_att_date = st.date_input("Leave Date", value=pd.to_datetime(loaded_att["attendance_date"]).date(), key=f"e_att_dt_{loaded_att_id}", format="DD-MM-YYYY")
                    with c2:
                        e_att_stat = st.selectbox("Status", LEAVE_STATUS_OPTIONS, index=LEAVE_STATUS_OPTIONS.index(loaded_att["status"]) if loaded_att["status"] in LEAVE_STATUS_OPTIONS else 0, key=f"e_att_st_{loaded_att_id}")

                    c3, c4 = st.columns(2)
                    with c3:
                        e_att_type = st.selectbox("Leave Type", LEAVE_TYPE_OPTIONS, index=LEAVE_TYPE_OPTIONS.index(loaded_att["leave_type"]) if loaded_att["leave_type"] in LEAVE_TYPE_OPTIONS else 0, key=f"e_att_tp_{loaded_att_id}")
                    with c4:
                        e_att_reason = st.text_input("Reason", value=str(loaded_att.get("reason") or ""), key=f"e_att_rs_{loaded_att_id}")

                    if st.button("💾 Update Leave Entry", type="primary", use_container_width=False, key="submit_upd_leave_btn"):
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
                            st.cache_data.clear()
                            show_success_modal(f"Attendance record #{loaded_att_id} updated successfully!")
                        except Exception as e:
                            st.error(f"Could not update attendance: {e}")

        elif staff_tab_sel == "⚙️ Compensation Plans":
            pass

            if staff_df.empty:
                st.info("No staff records found in database.")
            else:
                sel_s_plan = st.selectbox("Select Staff Member", staff_df["name"].tolist(), key="staff_comp_sel")
                target_s_row = staff_df[staff_df["name"] == sel_s_plan].iloc[0]
                target_s_id = int(target_s_row["id"])
                hist_df = load_staff_compensation_history(target_s_id)

                # --------------------------------------------------------------
                # HISTORICAL PLANS FIRST
                # --------------------------------------------------------------
                st.markdown("#### Historical Plans")
                active_plan = None
                if not hist_df.empty:
                    hist_work = hist_df.copy()
                    hist_work["effective_from_dt"] = pd.to_datetime(hist_work["effective_from"]).dt.date
                    hist_work["effective_to_dt"] = hist_work["effective_to"].apply(
                        lambda d: pd.to_datetime(d).date() if pd.notna(d) else None
                    )
                    today_dt = date.today()

                    active_mask = hist_work.apply(
                        lambda r: r["effective_from_dt"] <= today_dt and
                                  (r["effective_to_dt"] is None or r["effective_to_dt"] >= today_dt),
                        axis=1
                    )
                    active_rows = hist_work[active_mask].sort_values(["effective_from_dt", "id"], ascending=[False, False])
                    if not active_rows.empty:
                        active_plan = active_rows.iloc[0]

                    def plan_status(row):
                        if row["effective_from_dt"] > today_dt:
                            return "Future"
                        if row["effective_to_dt"] is None or row["effective_to_dt"] >= today_dt:
                            return "Active"
                        return "Historical"

                    hist_work["Status"] = hist_work.apply(plan_status, axis=1)
                    hist_work["From"] = hist_work["effective_from_dt"].apply(lambda d: d.strftime("%d-%b-%y"))
                    hist_work["To"] = hist_work["effective_to_dt"].apply(lambda d: d.strftime("%d-%b-%y") if d else "Open")
                    hist_work["Salary"] = hist_work["monthly_fixed_salary"].apply(lambda v: f"₹{_num(v):,.0f}")
                    hist_work["Threshold"] = hist_work["commission_threshold_daily"].apply(lambda v: f"₹{_num(v):,.0f}")
                    hist_work["Comm %"] = hist_work["commission_percentage"].apply(lambda v: f"{_num(v):.1f}%")
                    hist_work["Allowance Mode"] = hist_work["food_tea_allowance_mode"].fillna("monthly").astype(str).str.title()
                    hist_work["Weekday"] = hist_work["allowance_weekday"].apply(lambda v: f"₹{_num(v):,.0f}")
                    hist_work["Sunday"] = hist_work["allowance_sunday"].apply(lambda v: f"₹{_num(v):,.0f}")
                    hist_work["Food/Mth"] = hist_work["monthly_food_tea_allowance"].apply(lambda v: f"₹{_num(v):,.0f}")
                    hist_work["Fuel/Mth"] = hist_work["monthly_fuel_allowance"].apply(lambda v: f"₹{_num(v):,.0f}")

                    compact_hist = hist_work[[
                        "Status", "From", "To", "Salary", "Threshold", "Comm %", "Allowance Mode",
                        "Weekday", "Sunday", "Food/Mth", "Fuel/Mth"
                    ]]
                    hist_html = compact_hist.to_html(index=False, border=0, classes="comp-history-table", escape=True)
                    st.markdown(
                        """
                        <style>
                        .comp-history-wrap {width:100%; overflow-x:hidden; margin-bottom:0.7rem;}
                        .comp-history-table {width:100%; table-layout:fixed; border-collapse:collapse; font-size:12px;}
                        .comp-history-table th {background:#BFDBFE; color:#111111; font-size:11.5px; font-weight:800; padding:6px 4px; border:1px solid #93C5FD; white-space:normal; line-height:1.2;}
                        .comp-history-table td {font-size:12px; padding:6px 4px; border:1px solid #CBD5E1; text-align:center; white-space:normal; overflow-wrap:anywhere; line-height:1.2;}
                        .comp-history-table tr:nth-child(even) td {background:#F8FAFC;}
                        </style>
                        """,
                        unsafe_allow_html=True
                    )
                    st.markdown(f'<div class="comp-history-wrap">{hist_html}</div>', unsafe_allow_html=True)
                else:
                    st.info("No compensation plans found for this staff member.")

                # --------------------------------------------------------------
                # ACTIVE PLAN + EDIT
                # --------------------------------------------------------------
                st.markdown("---")
                st.markdown(f"#### Active Plan for {sel_s_plan}")

                if active_plan is None:
                    st.warning("No compensation plan is currently effective for this staff member. Add a new plan below.")
                else:
                    active_food_mode = str(active_plan.get("food_tea_allowance_mode") or "monthly").strip().lower()
                    if active_food_mode not in ("daily", "monthly"):
                        active_food_mode = "monthly"

                    m1, m2, m3, m4, m5 = st.columns(5)
                    m1.metric("Monthly Fixed Salary", f"₹{_num(active_plan.get('monthly_fixed_salary')):,.2f}")
                    m2.metric("Commission Threshold", f"₹{_num(active_plan.get('commission_threshold_daily')):,.2f}/day")
                    m3.metric("Commission Rate", f"{_num(active_plan.get('commission_percentage')):.1f}%")
                    if active_food_mode == "daily":
                        m4.metric("Food & Tea (Daily)", f"₹{_num(active_plan.get('allowance_weekday')):,.0f} W | ₹{_num(active_plan.get('allowance_sunday')):,.0f} Sun")
                    else:
                        m4.metric("Food & Tea (Monthly)", f"₹{_num(active_plan.get('monthly_food_tea_allowance')):,.0f}/month")
                    m5.metric("Fuel", f"₹{_num(active_plan.get('monthly_fuel_allowance')):,.0f}/month")

                    with st.expander("✏️ Edit Existing Active Plan", expanded=False):
                        st.caption(
                            f"Active from {active_plan['effective_from_dt'].strftime('%d-%b-%y')}. "
                            "Editing updates this active plan in place; it does not create a new history row."
                        )
                        edit_use_monthly_food = st.checkbox(
                            "Use monthly Food & Tea allowance plan",
                            value=(active_food_mode == "monthly"),
                            key=f"edit_comp_food_monthly_mode_{target_s_id}_{int(active_plan['id'])}",
                            help="Checked = monthly Food & Tea amount pro-rated for days worked. Unchecked = weekday / Sunday daily rates."
                        )
                        edit_food_mode = "monthly" if edit_use_monthly_food else "daily"

                        with st.form(f"edit_active_comp_plan_form_{target_s_id}_{int(active_plan['id'])}"):
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                st.date_input(
                                    "Effective From Date",
                                    value=active_plan["effective_from_dt"],
                                    disabled=True,
                                    format="DD-MM-YYYY",
                                    key=f"edit_plan_eff_from_{target_s_id}_{int(active_plan['id'])}"
                                )
                            with ec2:
                                edit_salary = st.number_input(
                                    "Monthly Fixed Salary (₹)", min_value=0.0,
                                    value=float(_num(active_plan.get("monthly_fixed_salary")) or 18000.0), step=500.0,
                                    key=f"edit_plan_salary_{target_s_id}_{int(active_plan['id'])}"
                                )

                            ec3, ec4 = st.columns(2)
                            with ec3:
                                edit_threshold = st.number_input(
                                    "Daily Sales Threshold (₹)", min_value=0.0,
                                    value=float(_num(active_plan.get("commission_threshold_daily"))), step=100.0,
                                    key=f"edit_plan_threshold_{target_s_id}_{int(active_plan['id'])}"
                                )
                            with ec4:
                                edit_comm_pct = st.number_input(
                                    "Commission Rate (%)", min_value=0.0, max_value=100.0,
                                    value=float(_num(active_plan.get("commission_percentage"))), step=0.5,
                                    key=f"edit_plan_comm_{target_s_id}_{int(active_plan['id'])}"
                                )

                            ec5, ec6, ec7 = st.columns(3)
                            with ec5:
                                edit_allow_wd = st.number_input(
                                    "Food & Tea: Mon to Sat (₹/day)", min_value=0.0,
                                    value=float(_num(active_plan.get("allowance_weekday"))), step=10.0,
                                    disabled=edit_use_monthly_food,
                                    key=f"edit_plan_wd_{target_s_id}_{int(active_plan['id'])}"
                                )
                            with ec6:
                                edit_allow_sun = st.number_input(
                                    "Food & Tea: Sunday (₹/day)", min_value=0.0,
                                    value=float(_num(active_plan.get("allowance_sunday"))), step=10.0,
                                    disabled=edit_use_monthly_food,
                                    key=f"edit_plan_sun_{target_s_id}_{int(active_plan['id'])}"
                                )
                            with ec7:
                                edit_monthly_food = st.number_input(
                                    "Food & Tea (₹/month)", min_value=0.0,
                                    value=float(_num(active_plan.get("monthly_food_tea_allowance"))), step=100.0,
                                    disabled=not edit_use_monthly_food,
                                    key=f"edit_plan_mfood_{target_s_id}_{int(active_plan['id'])}"
                                )

                            edit_monthly_fuel = st.number_input(
                                "Monthly Fuel Allowance (₹/month)", min_value=0.0,
                                value=float(_num(active_plan.get("monthly_fuel_allowance"))), step=100.0,
                                key=f"edit_plan_mfuel_{target_s_id}_{int(active_plan['id'])}"
                            )
                            submit_edit_plan = st.form_submit_button(
                                "💾 Update Active Compensation Plan", type="primary", width="stretch"
                            )

                        if submit_edit_plan:
                            try:
                                with db_conn.session as s:
                                    s.execute(
                                        text("""
                                        UPDATE staff_compensation_plans
                                        SET monthly_fixed_salary = :sal,
                                            commission_threshold_daily = :thresh,
                                            commission_percentage = :comm,
                                            allowance_weekday = :awd,
                                            allowance_sunday = :asun,
                                            food_tea_allowance_mode = :food_mode,
                                            monthly_food_tea_allowance = :mfood,
                                            monthly_fuel_allowance = :mfuel
                                        WHERE id = :pid AND staff_id = :sid;
                                        """),
                                        {
                                            "pid": int(active_plan["id"]), "sid": target_s_id,
                                            "sal": float(edit_salary), "thresh": float(edit_threshold),
                                            "comm": float(edit_comm_pct), "awd": float(edit_allow_wd),
                                            "asun": float(edit_allow_sun), "food_mode": edit_food_mode,
                                            "mfood": float(edit_monthly_food), "mfuel": float(edit_monthly_fuel)
                                        }
                                    )
                                    s.commit()
                                st.cache_data.clear()
                                show_success_modal(f"Active compensation plan updated successfully for {sel_s_plan}!")
                            except Exception as e:
                                st.error(f"Could not update active compensation plan: {e}")

                # --------------------------------------------------------------
                # ADD NEW PLAN BELOW HISTORY / ACTIVE EDIT
                # --------------------------------------------------------------
                st.markdown("---")
                st.markdown("#### Add New Compensation Plan")
                pass

                source_plan = active_plan if active_plan is not None else target_s_row
                source_food_mode = str(source_plan.get("food_tea_allowance_mode") or "monthly").strip().lower()
                if source_food_mode not in ("daily", "monthly"):
                    source_food_mode = "monthly"

                use_monthly_food = st.checkbox(
                    "Use monthly Food & Tea allowance plan",
                    value=(source_food_mode == "monthly"),
                    key=f"new_comp_food_monthly_mode_{target_s_id}",
                    help="Checked = monthly Food & Tea amount pro-rated for days worked. Unchecked = weekday / Sunday daily rates."
                )
                selected_food_mode = "monthly" if use_monthly_food else "daily"

                with st.form(f"new_comp_plan_form_{target_s_id}"):
                    cp1, cp2 = st.columns(2)
                    with cp1:
                        plan_eff_from = st.date_input("Effective From Date", value=date.today(), format="DD-MM-YYYY", key=f"new_plan_eff_{target_s_id}")
                    with cp2:
                        plan_salary = st.number_input(
                            "Monthly Fixed Salary (₹)", min_value=0.0,
                            value=float(_num(source_plan.get("monthly_fixed_salary")) or 18000.0), step=500.0,
                            key=f"new_plan_salary_{target_s_id}"
                        )

                    cp3, cp4 = st.columns(2)
                    with cp3:
                        plan_threshold = st.number_input(
                            "Daily Sales Threshold (₹)", min_value=0.0,
                            value=float(_num(source_plan.get("commission_threshold_daily")) or 3000.0), step=100.0,
                            key=f"new_plan_threshold_{target_s_id}"
                        )
                    with cp4:
                        plan_comm_pct = st.number_input(
                            "Commission Rate (%)", min_value=0.0, max_value=100.0,
                            value=float(_num(source_plan.get("commission_percentage")) or 15.0), step=0.5,
                            key=f"new_plan_comm_{target_s_id}"
                        )

                    cp5, cp6, cp7 = st.columns(3)
                    with cp5:
                        plan_allow_wd = st.number_input(
                            "Food & Tea: Mon to Sat (₹/day)", min_value=0.0,
                            value=float(_num(source_plan.get("allowance_weekday"))), step=10.0,
                            disabled=use_monthly_food, key=f"new_plan_wd_{target_s_id}"
                        )
                    with cp6:
                        plan_allow_sun = st.number_input(
                            "Food & Tea: Sunday (₹/day)", min_value=0.0,
                            value=float(_num(source_plan.get("allowance_sunday"))), step=10.0,
                            disabled=use_monthly_food, key=f"new_plan_sun_{target_s_id}"
                        )
                    with cp7:
                        plan_monthly_food = st.number_input(
                            "Food & Tea (₹/month)", min_value=0.0,
                            value=float(_num(source_plan.get("monthly_food_tea_allowance"))), step=100.0,
                            disabled=not use_monthly_food, key=f"new_plan_mfood_{target_s_id}"
                        )

                    plan_monthly_fuel = st.number_input(
                        "Monthly Fuel Allowance (₹/month)", min_value=0.0,
                        value=float(_num(source_plan.get("monthly_fuel_allowance"))), step=100.0,
                        key=f"new_plan_mfuel_{target_s_id}"
                    )
                    submit_plan = st.form_submit_button("💾 Save & Activate Compensation Plan", type="primary", width="stretch")

                if submit_plan:
                    try:
                        if active_plan is not None and plan_eff_from <= active_plan["effective_from_dt"]:
                            st.error(
                                "The new plan Effective From date must be later than the current active plan's start date. "
                                "Use 'Edit Existing Active Plan' to change the current plan."
                            )
                        else:
                            with db_conn.session as s:
                                if active_plan is not None:
                                    s.execute(
                                        text("""
                                        UPDATE staff_compensation_plans
                                        SET effective_to = :prev_end
                                        WHERE id = :pid AND staff_id = :sid;
                                        """),
                                        {
                                            "prev_end": plan_eff_from - timedelta(days=1),
                                            "pid": int(active_plan["id"]), "sid": target_s_id
                                        }
                                    )
                                s.execute(
                                    text("""
                                    INSERT INTO staff_compensation_plans (
                                        staff_id, effective_from, monthly_fixed_salary,
                                        commission_threshold_daily, commission_percentage,
                                        allowance_weekday, allowance_sunday, food_tea_allowance_mode,
                                        monthly_food_tea_allowance, monthly_fuel_allowance
                                    ) VALUES (
                                        :sid, :efrom, :sal, :thresh, :comm,
                                        :awd, :asun, :food_mode, :mfood, :mfuel
                                    );
                                    """),
                                    {
                                        "sid": target_s_id, "efrom": plan_eff_from, "sal": float(plan_salary),
                                        "thresh": float(plan_threshold), "comm": float(plan_comm_pct),
                                        "awd": float(plan_allow_wd), "asun": float(plan_allow_sun),
                                        "food_mode": selected_food_mode,
                                        "mfood": float(plan_monthly_food), "mfuel": float(plan_monthly_fuel)
                                    }
                                )
                                s.commit()
                            st.cache_data.clear()
                            show_success_modal(f"New compensation plan activated for {sel_s_plan} from {plan_eff_from.strftime('%d-%b-%y')}!")
                    except Exception as e:
                        st.error(f"Could not save compensation plan: {e}")

        elif staff_tab_sel == "🍱 Monthly Food Allowance":
            pass

            mfa_filter_mode = st.radio(
                "Filter By",
                ["Month", "Custom Date Range"],
                horizontal=True,
                key="monthly_food_filter_mode"
            )

            today_mfa = date.today()
            min_mfa_date = date(2026, 9, 1)

            if mfa_filter_mode == "Month":
                mf1, mf2 = st.columns(2)
                all_month_names = list(calendar.month_name)[1:]
                with mf2:
                    mfa_year = st.number_input(
                        "Year",
                        min_value=2026,
                        max_value=2035,
                        value=max(2026, today_mfa.year),
                        step=1,
                        key="monthly_food_year"
                    )
                if int(mfa_year) == 2026:
                    allowed_month_names = all_month_names[8:]
                else:
                    allowed_month_names = all_month_names

                default_mfa_month_name = all_month_names[today_mfa.month - 1]
                default_mfa_index = (
                    allowed_month_names.index(default_mfa_month_name)
                    if default_mfa_month_name in allowed_month_names
                    else 0
                )
                with mf1:
                    mfa_month_name = st.selectbox(
                        "Month",
                        allowed_month_names,
                        index=default_mfa_index,
                        key=f"monthly_food_month_{int(mfa_year)}"
                    )
                    mfa_month_num = all_month_names.index(mfa_month_name) + 1

                mfa_start = date(int(mfa_year), int(mfa_month_num), 1)
                mfa_end = date(
                    int(mfa_year),
                    int(mfa_month_num),
                    calendar.monthrange(int(mfa_year), int(mfa_month_num))[1]
                )
            else:
                mf1, mf2 = st.columns(2)
                default_start_dt = max(min_mfa_date, today_mfa.replace(day=1))
                default_end_dt = max(min_mfa_date, today_mfa)
                with mf1:
                    mfa_start = st.date_input(
                        "Start Date",
                        value=default_start_dt,
                        min_value=min_mfa_date,
                        format="DD-MM-YYYY",
                        key="monthly_food_start"
                    )
                with mf2:
                    mfa_end = st.date_input(
                        "End Date",
                        value=default_end_dt,
                        min_value=min_mfa_date,
                        format="DD-MM-YYYY",
                        key="monthly_food_end"
                    )

            if mfa_start > mfa_end:
                st.error("Start Date must be before or equal to End Date.")
            elif db_conn is None:
                st.error("Database connection is not available.")
            else:
                try:
                    entitlement_end = min(mfa_end, today_mfa)
                    if mfa_end > today_mfa and mfa_start <= today_mfa:
                        st.caption(
                            f"ℹ️ Current month is in progress — entitlement is pro-rated up to today (**{today_mfa.strftime('%d-%b-%Y')}**)."
                        )
                    elif mfa_start > today_mfa:
                        st.caption("ℹ️ Selected period is in the future — entitlement accrued so far is ₹0.00.")

                    total_entitled_allowance = 0.0
                    if not staff_df.empty and mfa_start <= entitlement_end:
                        for _, s_row in staff_df.iterrows():
                            s_status = str(s_row.get("status") or "").strip().lower()
                            if s_status == "on-boarding":
                                continue

                            emp_start = mfa_start
                            emp_end = entitlement_end
                            doj = s_row.get("date_of_joining")
                            dol = s_row.get("date_of_leaving")

                            if pd.notna(doj) and str(doj).strip():
                                emp_start = max(emp_start, pd.to_datetime(doj).date())
                            if pd.notna(dol) and str(dol).strip():
                                emp_end = min(emp_end, pd.to_datetime(dol).date())

                            if emp_start > emp_end:
                                continue

                            plan_row = load_staff_comp_plan_as_of(int(s_row["id"]), emp_end)
                            plan_source = plan_row if plan_row is not None else s_row

                            food_mode = str(plan_source.get("food_tea_allowance_mode") or "monthly").strip().lower()
                            monthly_food_amt = float(_num(plan_source.get("monthly_food_tea_allowance")))

                            if food_mode == "monthly" and monthly_food_amt > 0:
                                cur_d = emp_start
                                while cur_d <= emp_end:
                                    days_in_cur_month = calendar.monthrange(cur_d.year, cur_d.month)[1]
                                    month_last_day = date(cur_d.year, cur_d.month, days_in_cur_month)
                                    seg_end = min(emp_end, month_last_day)
                                    active_days_in_month = (seg_end - cur_d).days + 1
                                    total_entitled_allowance += (monthly_food_amt / float(days_in_cur_month)) * active_days_in_month
                                    cur_d = seg_end + timedelta(days=1)

                    mfa_df = db_conn.query(
                        """
                        SELECT id, expense_date, description, total_amount, status
                        FROM expenses
                        WHERE LOWER(TRIM(COALESCE(sub_category, ''))) = 'monthly food allowance'
                          AND expense_date >= :sdate
                          AND expense_date <= :edate
                        ORDER BY expense_date DESC, id DESC;
                        """,
                        params={"sdate": mfa_start, "edate": mfa_end},
                        ttl="60s"
                    )

                    if not mfa_df.empty:
                        mfa_df = mfa_df.copy()
                        mfa_df["total_amount"] = pd.to_numeric(mfa_df["total_amount"], errors="coerce").fillna(0.0)
                        mfa_df["expense_date"] = pd.to_datetime(mfa_df["expense_date"])
                        total_food_paid = float(mfa_df["total_amount"].sum())
                    else:
                        total_food_paid = 0.0

                    entitled_rounded = int(round(total_entitled_allowance))
                    disbursed_rounded = int(round(total_food_paid))
                    remaining_rounded = entitled_rounded - disbursed_rounded

                    mc1, mc2, mc3 = st.columns(3)
                    mc1.metric("Total Entitled Allowance", f"₹{entitled_rounded:,}")
                    mc2.metric("Total Disbursed So Far", f"₹{disbursed_rounded:,}")
                    mc3.metric(
                        "Remaining to be Disbursed",
                        f"-₹{abs(remaining_rounded):,}" if remaining_rounded < 0 else f"₹{remaining_rounded:,}"
                    )

                    if mfa_df.empty:
                        st.info(f"No Monthly Food Allowance expense records found from {mfa_start.strftime('%d-%b-%y')} to {mfa_end.strftime('%d-%b-%y')}.")
                    else:
                        st.markdown("#### Payment Records")
                        detail_mfa = mfa_df.rename(columns={
                            "expense_date": "Date",
                            "description": "Description",
                            "total_amount": "Amount",
                            "status": "Status"
                        })
                        detail_mfa["Date"] = pd.to_datetime(detail_mfa["Date"]).dt.strftime("%d-%b-%y")
                        detail_cols = ["Date", "Description", "Amount", "Status"]
                        st.dataframe(
                            detail_mfa[detail_cols],
                            hide_index=True,
                            width="stretch",
                            column_config={
                                "Date": st.column_config.TextColumn(width="small"),
                                "Description": st.column_config.TextColumn(width="large"),
                                "Amount": st.column_config.NumberColumn(format="₹%,.2f", width="small"),
                                "Status": st.column_config.TextColumn(width="small")
                            }
                        )
                except Exception as e:
                    st.error(f"Could not load Monthly Food Allowance records: {e}")

        elif staff_tab_sel == "💵 Monthly Dues & Settlement":
            pass

            now = date.today()
            settlement_filter_mode = st.radio(
                "Filter By",
                ["Month", "Custom Date Range"],
                horizontal=True,
                key="monthly_dues_filter_mode"
            )

            if settlement_filter_mode == "Month":
                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    month_names = list(calendar.month_name)[1:]
                    sel_month_name = st.selectbox("Select Settlement Month", month_names, index=now.month - 1, key="pay_calc_month")
                    sel_month_idx = month_names.index(sel_month_name) + 1
                with m_col2:
                    sel_year = st.number_input("Select Year", min_value=2024, max_value=2035, value=now.year, step=1, key="pay_calc_year")
                m_start_dt = date(int(sel_year), int(sel_month_idx), 1)
                m_end_dt = date(int(sel_year), int(sel_month_idx), calendar.monthrange(int(sel_year), int(sel_month_idx))[1])
                settlement_period_label = f"{sel_month_name} {int(sel_year)}"
            else:
                m_col1, m_col2 = st.columns(2)
                with m_col1:
                    m_start_dt = st.date_input(
                        "Start Date",
                        value=now.replace(day=1),
                        format="DD-MM-YYYY",
                        key="pay_calc_start"
                    )
                with m_col2:
                    m_end_dt = st.date_input(
                        "End Date",
                        value=now,
                        format="DD-MM-YYYY",
                        key="pay_calc_end"
                    )
                settlement_period_label = f"{m_start_dt.strftime('%d-%b-%y')} to {m_end_dt.strftime('%d-%b-%y')}"

            if m_start_dt > m_end_dt:
                st.error("Start Date must be before or equal to End Date.")
                m_start_dt, m_end_dt = m_end_dt, m_start_dt

            period_day_count = (m_end_dt - m_start_dt).days + 1
            pass

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
                daily_month_df = db_conn.query(query_month, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="60s")

                query_att_m = """
                SELECT a.staff_id, s.name AS staff_name, a.attendance_date, a.status, a.leave_type, a.reason
                FROM staff_attendance a
                JOIN staff s ON a.staff_id = s.id
                WHERE a.attendance_date >= :sdate AND a.attendance_date <= :edate;
                """
                att_month_df = db_conn.query(query_att_m, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="60s")

                query_labour_payments = """
                SELECT 
                    p.id AS payment_id, p.expense_id, p.payment_date, p.amount_paid, p.payment_mode, p.ref_no, p.paid_to, p.notes,
                    e.category, e.sub_category, e.description, e.staff_name, e.attributed_to
                FROM expense_payments p
                JOIN expenses e ON p.expense_id = e.id
                WHERE e.category = 'Labour Charges' AND e.staff_name IS NOT NULL AND e.staff_name != '' AND p.payment_date >= :sdate AND p.payment_date <= :edate;
                """
                staff_payments_df = db_conn.query(query_labour_payments, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="60s")

                query_exp_ledger = """
                SELECT expense_date, staff_name, sub_category, total_amount 
                FROM expenses 
                WHERE category = 'Labour Charges' AND status = 'Paid' AND expense_date >= :sdate AND expense_date <= :edate;
                """
                exp_ledger_df = db_conn.query(query_exp_ledger, params={"sdate": m_start_dt, "edate": m_end_dt}, ttl="60s")

            if staff_df.empty:
                st.info("No staff records found.")
            else:
                settlement_summary_rows = []
                detailed_staff_logs = {}
                detailed_staff_payments = {}

                for _, s_row in staff_df.iterrows():
                    st_name = str(s_row["name"]).strip()
                    staff_role = str(s_row.get("role") or "Cart Operator").strip()
                    monthly_sal = float(_num(s_row.get("monthly_fixed_salary")) or 18000.0)
                    daily_rate = monthly_sal / 30.0
                    comm_thresh = float(_num(s_row.get("commission_threshold_daily")) or 3000.0)
                    comm_pct = float(_num(s_row.get("commission_percentage")) or 15.0)
                    allow_wd = float(_num(s_row.get("allowance_weekday")))
                    allow_sun = float(_num(s_row.get("allowance_sunday")))
                    food_mode = str(s_row.get("food_tea_allowance_mode") or "monthly").strip().lower()
                    if food_mode not in ("daily", "monthly"):
                        food_mode = "monthly"
                    monthly_food = float(_num(s_row.get("monthly_food_tea_allowance")))
                    monthly_fuel = float(_num(s_row.get("monthly_fuel_allowance")))

                    emp_start_m = m_start_dt
                    emp_end_m = m_end_dt
                    doj_val_m = s_row.get("date_of_joining")
                    dol_val_m = s_row.get("date_of_leaving")
                    if pd.notna(doj_val_m) and str(doj_val_m).strip():
                        try:
                            emp_start_m = max(emp_start_m, pd.to_datetime(doj_val_m).date())
                        except Exception:
                            pass
                    if pd.notna(dol_val_m) and str(dol_val_m).strip():
                        try:
                            emp_end_m = min(emp_end_m, pd.to_datetime(dol_val_m).date())
                        except Exception:
                            pass

                    if emp_start_m > emp_end_m:
                        detailed_staff_logs[st_name] = pd.DataFrame()
                        detailed_staff_payments[st_name] = pd.DataFrame()
                        continue

                    st_shifts = daily_month_df[daily_month_df["staff_name"] == st_name].copy() if not daily_month_df.empty else pd.DataFrame()
                    if not st_shifts.empty:
                        sh_dts_m = pd.to_datetime(st_shifts["entry_date"]).dt.date
                        st_shifts = st_shifts[(sh_dts_m >= emp_start_m) & (sh_dts_m <= emp_end_m)]

                    st_leaves = att_month_df[att_month_df["staff_name"] == st_name].copy() if not att_month_df.empty else pd.DataFrame()
                    if not st_leaves.empty:
                        lv_dts_m = pd.to_datetime(st_leaves["attendance_date"]).dt.date
                        st_leaves = st_leaves[(lv_dts_m >= emp_start_m) & (lv_dts_m <= emp_end_m)]

                    st_payments = staff_payments_df[staff_payments_df["staff_name"] == st_name].copy() if not staff_payments_df.empty else pd.DataFrame()
                    if not st_payments.empty:
                        py_dts_m = pd.to_datetime(st_payments["payment_date"]).dt.date
                        st_payments = st_payments[(py_dts_m >= emp_start_m) & (py_dts_m <= emp_end_m)]

                    st_exp = exp_ledger_df[exp_ledger_df["staff_name"] == st_name].copy() if not exp_ledger_df.empty else pd.DataFrame()
                    if not st_exp.empty:
                        ex_dts_m = pd.to_datetime(st_exp["expense_date"]).dt.date
                        st_exp = st_exp[(ex_dts_m >= emp_start_m) & (ex_dts_m <= emp_end_m)]

                    # Non-cart roles do not depend on cart entries. Ops Coordinator uses
                    # calendar-month pro-rata salary starting from Date of Joining when needed.
                    if staff_role.lower() != "cart operator":
                        unpaid_leave_dates = set()
                        paid_leave_dates = set()
                        if not st_leaves.empty:
                            for _, l_row in st_leaves.iterrows():
                                l_dt = pd.to_datetime(l_row["attendance_date"]).date()
                                l_type = str(l_row.get("leave_type") or "Unpaid").strip().lower()
                                if l_type == "paid":
                                    paid_leave_dates.add(l_dt)
                                else:
                                    unpaid_leave_dates.add(l_dt)

                        role_start = m_start_dt
                        role_end = min(m_end_dt, date.today())
                        doj_val = s_row.get("date_of_joining")
                        dol_val = s_row.get("date_of_leaving")
                        if pd.notna(doj_val) and str(doj_val).strip():
                            role_start = max(role_start, pd.to_datetime(doj_val).date())
                        if pd.notna(dol_val) and str(dol_val).strip():
                            role_end = min(role_end, pd.to_datetime(dol_val).date())

                        if role_start > role_end:
                            detailed_staff_logs[st_name] = pd.DataFrame()
                            detailed_staff_payments[st_name] = st_payments
                            continue

                        period_dates = [role_start + timedelta(days=i) for i in range((role_end - role_start).days + 1)]
                        payable_dates = [d for d in period_dates if d not in unpaid_leave_dates]
                        worked_dates = [d for d in payable_dates if d not in paid_leave_dates]
                        payable_days = len(payable_dates)
                        worked_days = len(worked_dates)
                        paid_leave_cnt = len([d for d in paid_leave_dates if role_start <= d <= role_end])
                        unpaid_leave_cnt = len([d for d in unpaid_leave_dates if role_start <= d <= role_end])

                        salary_by_date = {d: daily_rate for d in period_dates}
                        apportioned_base_salary = sum(salary_by_date[d] for d in payable_dates)
                        salary_daily_rate = (apportioned_base_salary / payable_days) if payable_days > 0 else 0.0
                        if food_mode == "monthly":
                            # Monthly Food Allowance is a central expense, not an individual payroll earning.
                            food_entitled = 0.0
                            # Ops Coordinator Fuel is an individual earning and remains payable
                            # pro-rata for actual worked days under the monthly Food/Tea model.
                            fuel_entitled = (
                                sum(monthly_fuel / 30.0 for d in worked_dates)
                                if staff_role.lower() == "ops coordinator" else 0.0
                            )
                        else:
                            food_entitled = sum((allow_sun if d.weekday() == 6 else allow_wd) for d in worked_dates)
                            fuel_entitled = sum(monthly_fuel / 30.0 for d in worked_dates)
                        total_allow_entitled = food_entitled + fuel_entitled
                        total_payments_disbursed = float(st_payments["amount_paid"].sum()) if not st_payments.empty else 0.0
                        gross_earnings = apportioned_base_salary + total_allow_entitled
                        net_payable_due = gross_earnings - total_payments_disbursed

                        settlement_summary_rows.append({
                            "Staff Name": st_name,
                            "Status": s_row["status"],
                            "Days Worked": f"{worked_days} worked / {payable_days} payable",
                            "Leaves Logged": f"{paid_leave_cnt + unpaid_leave_cnt} ({paid_leave_cnt}P / {unpaid_leave_cnt}U)",
                            "Apportioned Salary (₹)": apportioned_base_salary,
                            "Daily Rate Used (₹)": f"₹{salary_daily_rate:.2f}/day",
                            "Total Sales (₹)": 0.0,
                            "Commission Earned (₹)": 0.0,
                            "Allowances Entitled (₹)": total_allow_entitled,
                            "Gross Payable (₹)": gross_earnings,
                            "Total Paid / Deductions (₹)": total_payments_disbursed,
                            "Net Amount Due (₹)": net_payable_due
                        })

                        staff_shift_records = []
                        for d in period_dates:
                            if d in unpaid_leave_dates:
                                row_type, day_salary, day_allow = "Unpaid Leave", 0.0, 0.0
                            elif d in paid_leave_dates:
                                row_type, day_salary, day_allow = "Paid Leave", salary_by_date.get(d, 0.0), 0.0
                            else:
                                row_type = "Daily Salary"
                                day_salary = salary_by_date.get(d, 0.0)
                                if food_mode == "daily":
                                    day_food_allow = allow_sun if d.weekday() == 6 else allow_wd
                                    day_allow = day_food_allow + (monthly_fuel / 30.0)
                                else:
                                    day_allow = 0.0
                            staff_shift_records.append({
                                "Date": d.strftime("%d-%b-%y"), "Day": d.strftime("%A"),
                                "Staff Name": st_name, "Cart Operated": "—",
                                "Shift Status": row_type, "Daily Sales (₹)": 0.0,
                                "Salary Apportioned (₹)": day_salary, "Commission (₹)": 0.0,
                                "Allowance Entitled (₹)": day_allow, "Advance Taken (₹)": 0.0,
                                "Allow. Taken (₹)": 0.0, "Total Entitled (₹)": day_salary + day_allow
                            })
                        detailed_staff_logs[st_name] = pd.DataFrame(staff_shift_records)
                        detailed_staff_payments[st_name] = st_payments
                        continue

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
                    worked_dates = set()
                    staff_shift_records = []

                    if not st_shifts.empty:
                        st_shifts["entry_date"] = pd.to_datetime(st_shifts["entry_date"])
                        st_shifts = st_shifts.sort_values(by="entry_date")

                        for _, shift in st_shifts.iterrows():
                            s_dt = shift["entry_date"].date()
                            is_sun = (s_dt.weekday() == 6)
                            first_shift_today = s_dt not in worked_dates
                            if first_shift_today:
                                worked_dates.add(s_dt)
                                if is_sun:
                                    sundays_worked += 1
                                else:
                                    weekdays_worked += 1
                            if first_shift_today:
                                # Cart Operators receive only the daily Food/Tea allowance when on the daily model.
                                # Monthly Food is central and Fuel is not applicable to cart staff.
                                day_allow = (allow_sun if is_sun else allow_wd) if food_mode == "daily" else 0.0
                            else:
                                day_allow = 0.0

                            s_col = float(_num(shift["total_collection"]))
                            day_comm = max(0.0, s_col - comm_thresh) * (comm_pct / 100.0)

                            total_sales_done += s_col
                            total_comm_earned += day_comm
                            total_allow_entitled += day_allow
                        
                            day_adv = exp_map.get(s_dt, {}).get("advance", 0.0)
                            day_food = exp_map.get(s_dt, {}).get("food", 0.0)
                            if s_dt in exp_map: del exp_map[s_dt]

                            staff_shift_records.append({
                                "Date": s_dt.strftime("%d-%b-%y"),
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
                                "Date": l_dt.strftime("%d-%b-%y"),
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
                            "Date": d.strftime("%d-%b-%y"),
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
                    days_worked = len(worked_dates)
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
                        s_ledger_df["dt_sort"] = pd.to_datetime(s_ledger_df["Date"], format="%d-%b-%y")
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
                    pass
                    if target_staff_log.empty:
                        st.info(f"No shifts or leave records logged for {sel_staff_drill} in {settlement_period_label}.")
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
                    pass
                    if target_staff_pay.empty:
                        st.info(f"No disbursements / payments recorded for {sel_staff_drill} in {settlement_period_label}.")
                    else:
                        disp_sp = target_staff_pay.copy()
                        disp_sp["payment_date"] = pd.to_datetime(disp_sp["payment_date"]).dt.strftime("%d-%b-%y")
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
        if "dash_sub_page" not in st.session_state:
            st.session_state["dash_sub_page"] = None

        def _open_dash_sub_page(target_sub):
            st.cache_data.clear()
            st.session_state["dash_sub_page"] = target_sub

        try:
            daily_df = load_db_daily_df()
            exp_list = load_db_expenses_list()
            exp_df = pd.DataFrame(exp_list)
        except Exception as e:
            daily_df, exp_df = pd.DataFrame(), pd.DataFrame()
            st.warning(f"Could not load data from database ({e}).")

        # Shared Date Filter & Financial Overview Calculations (Aligned with Home Landing Page MTD)
        today_cur = date.today()
        month_start_cur = today_cur.replace(day=1)
        default_end_cur = today_cur

        all_dates = [today_cur, month_start_cur]
        if not daily_df.empty:
            all_dates += [daily_df["Date"].min().date(), daily_df["Date"].max().date()]
        if not exp_df.empty and exp_df["Date"].notna().any():
            all_dates += [exp_df["Date"].min().date(), exp_df["Date"].max().date()]
        min_d, max_d = min(all_dates), max(today_cur, max(all_dates))

        if "applied_start" not in st.session_state:
            st.session_state["applied_start"] = month_start_cur
        if "applied_end" not in st.session_state:
            st.session_state["applied_end"] = default_end_cur
        st.session_state["applied_start"] = min(max(st.session_state["applied_start"], min_d), max_d)
        st.session_state["applied_end"] = min(max(st.session_state["applied_end"], min_d), max_d)

        def _render_dash_date_filter_and_compute(key_suffix="main"):
            dashboard_filter_mode = st.radio(
                "Filter By",
                ["Month", "Custom Date Range"],
                horizontal=True,
                key=f"dashboard_report_filter_mode_{key_suffix}",
            )
            with st.form(f"date_range_form_{key_suffix}"):
                if dashboard_filter_mode == "Month":
                    rc1, rc2, rc3 = st.columns([2, 2, 1], gap="small", vertical_alignment="bottom")
                    dash_month_names = list(calendar.month_name)[1:]
                    default_dash_month = st.session_state["applied_start"].month
                    default_dash_year = st.session_state["applied_start"].year
                    with rc1:
                        dash_month_name = st.selectbox(
                            "Month",
                            dash_month_names,
                            index=default_dash_month - 1,
                            key=f"dashboard_report_month_{key_suffix}",
                        )
                        dash_month_num = dash_month_names.index(dash_month_name) + 1
                    with rc2:
                        dash_year = st.number_input(
                            "Year",
                            min_value=min_d.year,
                            max_value=max_d.year,
                            value=default_dash_year,
                            step=1,
                            key=f"dashboard_report_year_{key_suffix}",
                        )
                    pending_start = date(int(dash_year), int(dash_month_num), 1)
                    pending_end = date(int(dash_year), int(dash_month_num), calendar.monthrange(int(dash_year), int(dash_month_num))[1])
                    pending_start = max(pending_start, min_d)
                    pending_end = min(pending_end, max_d)
                else:
                    dash_month_num = st.session_state["applied_start"].month
                    dash_year = st.session_state["applied_start"].year
                    rc1, rc2, rc3 = st.columns([2, 2, 1], gap="small", vertical_alignment="bottom")
                    with rc1:
                        pending_start = st.date_input(
                            "Start Date",
                            value=st.session_state["applied_start"],
                            min_value=min_d,
                            max_value=max_d,
                            format="DD-MM-YYYY",
                            key=f"dashboard_report_start_{key_suffix}",
                        )
                    with rc2:
                        pending_end = st.date_input(
                            "End Date",
                            value=st.session_state["applied_end"],
                            min_value=min_d,
                            max_value=max_d,
                            format="DD-MM-YYYY",
                            key=f"dashboard_report_end_{key_suffix}",
                        )
                with rc3:
                    apply_clicked = st.form_submit_button("Apply", type="primary", use_container_width=True)

            if apply_clicked or dashboard_filter_mode == "Month":
                st.session_state["applied_start"] = pending_start
                st.session_state["applied_end"] = pending_end
            range_start, range_end = st.session_state["applied_start"], st.session_state["applied_end"]

            if range_start > range_end:
                st.error("'From' date is after 'To' date - swap them and click Apply again.")
                range_start, range_end = range_end, range_start

            today_ref = date.today()
            if dashboard_filter_mode == "Month":
                if int(dash_year) == today_ref.year and int(dash_month_num) == today_ref.month:
                    elapsed_days = max(1, (today_ref - date(today_ref.year, today_ref.month, 1)).days)
                    avg_divisor_days = elapsed_days
                else:
                    avg_divisor_days = max(1, calendar.monthrange(int(dash_year), int(dash_month_num))[1])
            else:
                if range_start == today_ref.replace(day=1) and range_end == today_ref:
                    avg_divisor_days = max(1, (today_ref - range_start).days)
                else:
                    avg_divisor_days = max(1, (range_end - range_start).days + 1)

            fin_res = compute_period_financials(
                start_date=range_start,
                end_date=range_end,
                avg_divisor_days=avg_divisor_days,
                daily_df_in=daily_df,
                exp_df_in=exp_df,
            )

            return (
                dashboard_filter_mode, dash_year, dash_month_num,
                range_start, range_end, fin_res["range_df"], fin_res["range_exp"],
                fin_res["total_rev"], fin_res["total_units"], fin_res["exact_cogs_sold"], fin_res["capex_total"],
                fin_res["staff_pay_breakdown"], fin_res["unassigned_labour_df"], fin_res["non_labour_opex_df"],
                fin_res["tot_labour_incurred"], fin_res["other_opex_total"], fin_res["total_incurred_opex"],
                fin_res["gross_profit"], fin_res["cogs_margin"], fin_res["gross_margin"], fin_res["net_profit"], fin_res["net_margin"], fin_res["opex_margin"],
                fin_res["avg_divisor_days"], fin_res["avg_rev_per_day"], fin_res["avg_units_per_day"]
            )

        def _render_7_financial_overview_boxes(total_rev, avg_rev_per_day, total_units, exact_cogs_sold, cogs_margin, gross_profit, gross_margin, total_incurred_opex, opex_margin, net_profit, net_margin):
            st.markdown('<div class="dashboard-kpi-row">', unsafe_allow_html=True)
            mc1, mc2, mc3, mc4, mc5, mc6, mc7 = st.columns(7)
            mc1.metric("Revenue", f"₹{total_rev:,.0f}")
            mc2.metric("Avg Rev / Day", f"₹{avg_rev_per_day:,.0f}")
            mc3.metric("Units Sold", f"{total_units:,}")
            mc4.metric(f"COGS ({cogs_margin:.1f}%)", f"₹{exact_cogs_sold:,.0f}")
            mc5.metric(f"Gr. Profit ({gross_margin:.1f}%)", f"₹{gross_profit:,.0f}")
            mc6.metric(f"OPEX ({opex_margin:.1f}%)", f"₹{total_incurred_opex:,.0f}")
            mc7.metric(f"Net Profit ({net_margin:.1f}%)", f"₹{net_profit:,.0f}")
            st.markdown('</div>', unsafe_allow_html=True)

        active_dash_sub = st.session_state.get("dash_sub_page")
        if active_dash_sub not in ("month_comp", "sales_log", "dow_patterns", "what_if"):
            active_dash_sub = None
            st.session_state["dash_sub_page"] = None

        # ==================================================================
        # DEFAULT MAIN FINANCIALS PAGE:
        # 7 KPI Boxes -> Per-Cart Daily Average -> Daily Revenue Trend -> OPEX Breakdown & Full P&L
        # ==================================================================
        if active_dash_sub is None:
            dash_hdr_c1, dash_hdr_c2, dash_hdr_c3, dash_hdr_c4, dash_hdr_c5 = st.columns(
                [1.55, 1.10, 1.25, 1.10, 1.25],
                gap="small",
                vertical_alignment="center",
            )
            with dash_hdr_c1:
                st.subheader("💰 Financials Overview")
            with dash_hdr_c2:
                st.button(
                    "🔮 What-If Analysis",
                    key="dash_open_page_what_if",
                    type="primary",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("what_if",),
                )
            with dash_hdr_c3:
                st.button(
                    "📅 Month-Wise Performance",
                    key="dash_open_page_month_comp",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("month_comp",),
                )
            with dash_hdr_c4:
                st.button(
                    "📋 Date-wise Sales Log",
                    key="dash_open_page_sales_log",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("sales_log",),
                )
            with dash_hdr_c5:
                st.button(
                    "📆 Day-Wise & Timing Patterns",
                    key="dash_open_page_dow_patterns",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("dow_patterns",),
                )

            if not daily_df.empty or not exp_df.empty:
                (
                    dashboard_filter_mode, dash_year, dash_month_num,
                    range_start, range_end, range_df, range_exp,
                    total_rev, total_units, exact_cogs_sold, capex_total,
                    staff_pay_breakdown, unassigned_labour_df, non_labour_opex_df,
                    tot_labour_incurred, other_opex_total, total_incurred_opex,
                    gross_profit, cogs_margin, gross_margin, net_profit, net_margin, opex_margin,
                    avg_divisor_days, avg_rev_per_day, avg_units_per_day
                ) = _render_dash_date_filter_and_compute(key_suffix="main_overview")

                _render_7_financial_overview_boxes(
                    total_rev, avg_rev_per_day, total_units,
                    exact_cogs_sold, cogs_margin, gross_profit, gross_margin,
                    total_incurred_opex, opex_margin, net_profit, net_margin
                )

                st.markdown("#### Cart Daily Average")
                if not range_df.empty and "Cart" in range_df.columns:
                    _cart_day_df = range_df.copy()
                    _cart_day_df["_d_only"] = pd.to_datetime(_cart_day_df["Date"]).dt.date
                    _cart_day_agg = (
                        _cart_day_df.groupby(["Cart", "_d_only"], as_index=False)
                        .agg(Day_Rev=("Total_Collection", "sum"), Day_Units=("Sold_Total", "sum"))
                    )
                    _cart_nonzero = _cart_day_agg[_cart_day_agg["Day_Rev"] > 0].copy()
                    if not _cart_nonzero.empty:
                        _cart_avg_df = (
                            _cart_nonzero.groupby("Cart", as_index=False)
                            .agg(
                                Active_Days=("_d_only", "nunique"),
                                Total_Rev=("Day_Rev", "sum"),
                                Total_Units=("Day_Units", "sum"),
                            )
                        )
                        _cart_avg_df["Avg Rev / Day (₹)"] = _cart_avg_df["Total_Rev"] / _cart_avg_df["Active_Days"]
                        _cart_avg_df["Avg Units / Day"] = _cart_avg_df["Total_Units"] / _cart_avg_df["Active_Days"]
                        _cart_avg_df = _cart_avg_df.sort_values("Avg Rev / Day (₹)", ascending=False).reset_index(drop=True)
                        _cart_avg_disp = _cart_avg_df[["Cart", "Active_Days", "Avg Rev / Day (₹)", "Avg Units / Day", "Total_Rev", "Total_Units"]].rename(
                            columns={"Active_Days": "Active Days", "Total_Rev": "Total Revenue (₹)", "Total_Units": "Total Units"}
                        )
                        st.dataframe(
                            _cart_avg_disp,
                            hide_index=True,
                            use_container_width=True,
                            height=min(320, 40 + len(_cart_avg_disp) * 36),
                            column_config={
                                "Cart": st.column_config.TextColumn("Cart"),
                                "Active Days": st.column_config.NumberColumn("Active Days", format="%d"),
                                "Avg Rev / Day (₹)": st.column_config.NumberColumn("Avg Rev / Day (₹)", format="₹%,.0f"),
                                "Avg Units / Day": st.column_config.NumberColumn("Avg Units / Day", format="%,.1f"),
                                "Total Revenue (₹)": st.column_config.NumberColumn("Total Revenue (₹)", format="₹%,.0f"),
                                "Total Units": st.column_config.NumberColumn("Total Units", format="%,d"),
                            },
                        )

                st.markdown("#### Daily Revenue Trend")
                if not range_df.empty:
                    line_chart = alt.Chart(range_df.groupby("Date", as_index=False)["Total_Collection"].sum()).mark_line(point=True, color="#4F46E5").encode(
                        x=alt.X("Date:T", title="Date", axis=alt.Axis(format="%d-%b")),
                        y=alt.Y("Total_Collection:Q", title="Revenue (₹)"),
                        tooltip=[alt.Tooltip("Date:T", format="%d-%b-%y", title="Date"), alt.Tooltip("Total_Collection:Q", format=",.2f", title="Revenue (₹)")]
                    ).properties(height=270)
                    st.altair_chart(line_chart, use_container_width=True)
                else:
                    st.caption("No revenue data available for this range to plot.")

                st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
                # ------------------------------------------------------------------
                # INTERACTIVE OPEX BREAKDOWN & INSIGHTS BUTTON + PANEL
                # ------------------------------------------------------------------
                if "show_dash_opex_breakdown" not in st.session_state:
                    st.session_state["show_dash_opex_breakdown"] = False

                def _toggle_dash_opex_breakdown():
                    st.session_state["show_dash_opex_breakdown"] = not bool(st.session_state.get("show_dash_opex_breakdown", False))

                opex_btn_c1, opex_btn_c2 = st.columns([1.5, 2.5], gap="small", vertical_alignment="center")
                with opex_btn_c1:
                    opex_btn_lbl = (
                        "🔼 Hide OPEX Breakdown & Insights"
                        if st.session_state["show_dash_opex_breakdown"]
                        else f"🧾 View OPEX Breakdown & Insights (₹{total_incurred_opex:,.0f} • {opex_margin:.1f}%)"
                    )
                    st.button(
                        opex_btn_lbl,
                        key="btn_toggle_dash_opex_breakdown",
                        type="primary" if not st.session_state["show_dash_opex_breakdown"] else "secondary",
                        use_container_width=True,
                        on_click=_toggle_dash_opex_breakdown,
                    )
                with opex_btn_c2:
                    st.markdown(
                        "<div style='font-size:12px;font-weight:700;color:#475569;'>"
                        "Category & sub-category split, labour & burn rate"
                        "</div>",
                        unsafe_allow_html=True,
                    )

                if st.session_state.get("show_dash_opex_breakdown", False):
                    with st.container(border=True):
                        st.markdown(
                            f"""
                            <div style="background:linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);border:1.5px solid #93C5FD;padding:14px 18px;border-radius:10px;color:#111111;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
                                <div>
                                    <div style="font-size:11px;font-weight:800;color:#111111;letter-spacing:0.6px;text-transform:uppercase;">OPERATING EXPENSE (OPEX) DEEP-DIVE & INSIGHTS</div>
                                    <div style="font-size:18px;font-weight:900;color:#111111;margin-top:2px;">Period: {range_start.strftime('%d %b %Y')} — {range_end.strftime('%d %b %Y')} ({avg_divisor_days} active days)</div>
                                </div>
                                <div style="text-align:right;">
                                    <div style="font-size:11px;color:#111111;font-weight:800;">Total Incurred OPEX</div>
                                    <div style="font-size:22px;font-weight:900;color:#111111;">₹{total_incurred_opex:,.0f} <span style="font-size:13px;color:#1E2252;">({opex_margin:.1f}% of Rev)</span></div>
                                </div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        # Build granular Category & Sub-Category rows
                        opex_detail_rows = []
                        opex_cat_totals = {}

                        # 1. Incurred Staff Labour broken down by Fixed Salary, Commission, Allowances + Staff names
                        tot_fixed_sal_inc = sum(float(v.get("salary", 0.0)) for v in staff_pay_breakdown.values())
                        tot_comm_inc = sum(float(v.get("commissions", v.get("commission", 0.0))) for v in staff_pay_breakdown.values())
                        tot_allow_inc = sum(float(v.get("allowances", v.get("allowance", 0.0))) for v in staff_pay_breakdown.values())

                        if tot_fixed_sal_inc > 0:
                            staff_sal_notes = ", ".join(
                                f"{sn}: ₹{float(sv['salary']):,.0f} ({int(sv.get('payable_days', sv.get('days_worked', 0)))}d)"
                                for sn, sv in sorted(staff_pay_breakdown.items(), key=lambda x: -float(x[1].get("salary", 0)))
                                if float(sv.get("salary", 0)) > 0
                            )
                            opex_detail_rows.append({
                                "Category": "Labour Charges",
                                "Sub-Category": "Pro-Rata Fixed Salaries (Incurred)",
                                "Entries": sum(1 for sv in staff_pay_breakdown.values() if float(sv.get("salary", 0)) > 0),
                                "Amount": tot_fixed_sal_inc,
                                "Details": staff_sal_notes or "Active staff pro-rata salary",
                            })
                        if tot_comm_inc > 0:
                            staff_comm_notes = ", ".join(
                                f"{sn}: ₹{float(sv.get('commissions', sv.get('commission', 0.0))):,.0f}"
                                for sn, sv in sorted(staff_pay_breakdown.items(), key=lambda x: -float(x[1].get("commissions", x[1].get("commission", 0))))
                                if float(sv.get("commissions", sv.get("commission", 0.0))) > 0
                            )
                            opex_detail_rows.append({
                                "Category": "Labour Charges",
                                "Sub-Category": "Sales Incentives & Commissions",
                                "Entries": sum(1 for sv in staff_pay_breakdown.values() if float(sv.get("commissions", sv.get("commission", 0.0))) > 0),
                                "Amount": tot_comm_inc,
                                "Details": staff_comm_notes or "Cart shift target commissions",
                            })
                        if tot_allow_inc > 0:
                            staff_allow_notes = ", ".join(
                                f"{sn}: ₹{float(sv.get('allowances', sv.get('allowance', 0.0))):,.0f}"
                                for sn, sv in sorted(staff_pay_breakdown.items(), key=lambda x: -float(x[1].get("allowances", x[1].get("allowance", 0))))
                                if float(sv.get("allowances", sv.get("allowance", 0.0))) > 0
                            )
                            opex_detail_rows.append({
                                "Category": "Labour Charges",
                                "Sub-Category": "Daily Food, Tea & Fuel Allowances",
                                "Entries": sum(1 for sv in staff_pay_breakdown.values() if float(sv.get("allowances", sv.get("allowance", 0.0))) > 0),
                                "Amount": tot_allow_inc,
                                "Details": staff_allow_notes or "Daily shift food/tea & fuel allowances",
                            })
                        if not unassigned_labour_df.empty:
                            for sub_c, grp_u in unassigned_labour_df.groupby(unassigned_labour_df["Sub_Category"].fillna("Monthly Food / General Labour")):
                                amt_u = float(grp_u["Amount"].sum())
                                if amt_u > 0:
                                    descs = [str(d).strip() for d in grp_u["Description"].dropna().unique().tolist() if str(d).strip()]
                                    opex_detail_rows.append({
                                        "Category": "Labour Charges",
                                        "Sub-Category": str(sub_c or "Monthly Food / General Labour"),
                                        "Entries": int(len(grp_u)),
                                        "Amount": amt_u,
                                        "Details": "; ".join(descs[:3]) if descs else "Unassigned labour expense",
                                    })

                        # 2. Non-Labour OPEX broken down by Category -> Sub-Category
                        if not non_labour_opex_df.empty:
                            nl_clean = non_labour_opex_df.copy()
                            nl_clean["Cat_Clean"] = nl_clean["Category"].fillna("Miscellaneous Expense").astype(str).str.strip()
                            nl_clean["Sub_Clean"] = nl_clean["Sub_Category"].fillna("General").astype(str).str.strip()
                            nl_clean.loc[nl_clean["Sub_Clean"] == "", "Sub_Clean"] = "General"
                            for (cat_n, sub_n), grp_nl in nl_clean.groupby(["Cat_Clean", "Sub_Clean"]):
                                amt_nl = float(grp_nl["Amount"].sum())
                                if amt_nl <= 0:
                                    continue
                                descs = [str(d).strip() for d in grp_nl["Description"].dropna().unique().tolist() if str(d).strip()]
                                attrs = [str(a).strip() for a in grp_nl["Attributed_To"].dropna().unique().tolist() if str(a).strip()]
                                detail_str = "; ".join(descs[:2]) if descs else (", ".join(attrs[:2]) if attrs else "Recorded OPEX")
                                opex_detail_rows.append({
                                    "Category": cat_n,
                                    "Sub-Category": sub_n,
                                    "Entries": int(len(grp_nl)),
                                    "Amount": amt_nl,
                                    "Details": detail_str,
                                })

                        for r_item in opex_detail_rows:
                            c_key = r_item["Category"]
                            opex_cat_totals[c_key] = opex_cat_totals.get(c_key, 0.0) + float(r_item["Amount"])

                        sorted_cats = sorted(opex_cat_totals.items(), key=lambda x: -x[1])
                        top_cat_name = sorted_cats[0][0] if sorted_cats else "None"
                        top_cat_amt = sorted_cats[0][1] if sorted_cats else 0.0
                        top_cat_share = (top_cat_amt / total_incurred_opex * 100.0) if total_incurred_opex > 0 else 0.0

                        labour_share_opex = (tot_labour_incurred / total_incurred_opex * 100.0) if total_incurred_opex > 0 else 0.0
                        other_share_opex = (other_opex_total / total_incurred_opex * 100.0) if total_incurred_opex > 0 else 0.0
                        opex_per_unit = (total_incurred_opex / float(total_units)) if total_units > 0 else 0.0
                        gp_per_unit = (gross_profit / float(total_units)) if total_units > 0 else 0.0
                        daily_opex_burn = (total_incurred_opex / float(avg_divisor_days)) if avg_divisor_days > 0 else 0.0
                        daily_gp_gen = (gross_profit / float(avg_divisor_days)) if avg_divisor_days > 0 else 0.0

                        # Key Executive Insights Strip
                        ins1, ins2, ins3, ins4 = st.columns(4, gap="small")
                        with ins1:
                            st.markdown(
                                f"""
                                <div style="background:#F8FAFC;border:1.5px solid #CBD5E1;border-radius:10px;padding:10px 12px;height:100%;">
                                    <div style="font-size:10.5px;font-weight:800;color:#2563EB;text-transform:uppercase;">🔥 #1 Cost Driver</div>
                                    <div style="font-size:15px;font-weight:900;color:#1E2252;margin-top:2px;">{escape(str(top_cat_name))}</div>
                                    <div style="font-size:14px;font-weight:900;color:#C43D17;margin-top:2px;">₹{top_cat_amt:,.0f} <span style="font-size:11px;color:#475569;">({top_cat_share:.1f}% of OPEX)</span></div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with ins2:
                            st.markdown(
                                f"""
                                <div style="background:#F4F9FD;border:1.5px solid #B5D3EB;border-radius:10px;padding:10px 12px;height:100%;">
                                    <div style="font-size:10.5px;font-weight:800;color:#1B5E91;text-transform:uppercase;">👥 Labour vs Overhead</div>
                                    <div style="font-size:13px;font-weight:900;color:#1B5E91;margin-top:3px;">Labour: ₹{tot_labour_incurred:,.0f} ({labour_share_opex:.1f}%)</div>
                                    <div style="font-size:12.5px;font-weight:800;color:#1E2252;margin-top:2px;">Other OPEX: ₹{other_opex_total:,.0f} ({other_share_opex:.1f}%)</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with ins3:
                            st.markdown(
                                f"""
                                <div style="background:#ECFDF5;border:1.5px solid #6EE7B7;border-radius:10px;padding:10px 12px;height:100%;">
                                    <div style="font-size:10.5px;font-weight:800;color:#047857;text-transform:uppercase;">🍦 OPEX Per Kulfi Sold</div>
                                    <div style="font-size:16px;font-weight:900;color:#047857;margin-top:2px;">₹{opex_per_unit:,.2f} / pc</div>
                                    <div style="font-size:11.5px;font-weight:700;color:#1E2252;margin-top:2px;">vs Gr. Margin ₹{gp_per_unit:,.2f} / pc</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with ins4:
                            st.markdown(
                                f"""
                                <div style="background:#FDF6F6;border:1.5px solid #EAB6B6;border-radius:10px;padding:10px 12px;height:100%;">
                                    <div style="font-size:10.5px;font-weight:800;color:#9E2A2B;text-transform:uppercase;">📆 Daily OPEX Burn Rate</div>
                                    <div style="font-size:16px;font-weight:900;color:#9E2A2B;margin-top:2px;">₹{daily_opex_burn:,.0f} / day</div>
                                    <div style="font-size:11.5px;font-weight:700;color:#1E2252;margin-top:2px;">vs Daily Gr. Profit ₹{daily_gp_gen:,.0f}/d</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

                        if opex_detail_rows:
                            # Category Progress Bars + Granular Category -> Sub-Category Table
                            cat_col_left, sub_col_right = st.columns([1.05, 1.55], gap="medium")
                            with cat_col_left:
                                st.markdown("##### 📊 Category Share of OPEX & Revenue")
                                palette_bars = ["#4F46E5", "#059669", "#2563EB", "#1B5E91", "#6A4C93", "#C43D17", "#047857", "#D97706"]
                                for idx_c, (c_name, c_amt) in enumerate(sorted_cats):
                                    pct_opex = (c_amt / total_incurred_opex * 100.0) if total_incurred_opex > 0 else 0.0
                                    pct_rev = (c_amt / total_rev * 100.0) if total_rev > 0 else 0.0
                                    bar_w = min(100.0, max(3.0, pct_opex))
                                    b_col = palette_bars[idx_c % len(palette_bars)]
                                    st.markdown(
                                        f"""
                                        <div style="background:#FFFFFF;border:1px solid #CBD5E1;border-radius:8px;padding:8px 10px;margin-bottom:7px;">
                                            <div style="display:flex;justify-content:space-between;align-items:center;font-size:12.5px;font-weight:800;color:#0F172A;">
                                                <span>{escape(str(c_name))}</span>
                                                <span style="color:{b_col};font-weight:900;">₹{c_amt:,.0f}</span>
                                            </div>
                                            <div style="display:flex;justify-content:space-between;font-size:11px;color:#475569;margin-top:2px;margin-bottom:4px;">
                                                <span><b>{pct_opex:.1f}%</b> of OPEX</span>
                                                <span><b>{pct_rev:.1f}%</b> of Revenue</span>
                                            </div>
                                            <div style="width:100%;background:#E2E8F0;height:7px;border-radius:4px;overflow:hidden;">
                                                <div style="width:{bar_w:.1f}%;background:{b_col};height:7px;border-radius:4px;"></div>
                                            </div>
                                        </div>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                            with sub_col_right:
                                st.markdown("##### 🧾 Granular Category & Sub-Category OPEX Table")
                                opex_sub_df = pd.DataFrame(opex_detail_rows).sort_values(["Amount"], ascending=False).reset_index(drop=True)
                                opex_sub_df["% of OPEX"] = opex_sub_df["Amount"].apply(
                                    lambda v: f"{(float(v) / total_incurred_opex * 100.0):.1f}%" if total_incurred_opex > 0 else "0.0%"
                                )
                                opex_sub_df["% of Rev"] = opex_sub_df["Amount"].apply(
                                    lambda v: f"{(float(v) / total_rev * 100.0):.1f}%" if total_rev > 0 else "0.0%"
                                )
                                opex_sub_df["Amount (₹)"] = opex_sub_df["Amount"].apply(lambda v: f"₹{float(v):,.0f}")

                                total_row_opex = pd.DataFrame([{
                                    "Category": "TOTAL INCURRED OPEX",
                                    "Sub-Category": f"{len(opex_detail_rows)} Sub-Components",
                                    "Entries": int(opex_sub_df["Entries"].sum()),
                                    "Amount (₹)": f"₹{total_incurred_opex:,.0f}",
                                    "% of OPEX": "100.0%",
                                    "% of Rev": f"{opex_margin:.1f}%",
                                    "Details": f"Net Margin after OPEX: ₹{net_profit:,.0f} ({net_margin:.1f}%)",
                                }])
                                disp_opex_df = pd.concat(
                                    [opex_sub_df[["Category", "Sub-Category", "Entries", "Amount (₹)", "% of OPEX", "% of Rev", "Details"]], total_row_opex],
                                    ignore_index=True,
                                )
                                st.dataframe(
                                    disp_opex_df.style.apply(
                                        lambda r: ["background-color:#EFF6FF;font-weight:900;color:#1E2252;" if r.get("Category") == "TOTAL INCURRED OPEX" else "" for _ in r],
                                        axis=1,
                                    ),
                                    hide_index=True,
                                    use_container_width=True,
                                    height=min(420, 42 + len(disp_opex_df) * 35),
                                )
                        else:
                            st.info("No operating expenses incurred in the selected period.")

                st.markdown("---")
                pl_c1, pl_c2 = st.columns([1.1, 1.2])
                with pl_c1:
                    st.markdown("#### Profit & Loss Statement (P&L)")
                    pnl_df = pd.DataFrame({
                        "Financial Line Item": ["1. Total Revenue in Period", "2. Cost of Goods Sold", "3. Gross Profit (1 - 2)", "4. Labour Charges (OPEX)", "5. Other Operating Costs (OPEX)", "6. Total Operating Costs (4 + 5)", "7. Net Profit (3 - 6)"],
                        "Amount (₹)": [total_rev, -exact_cogs_sold, gross_profit, -tot_labour_incurred, -other_opex_total, -total_incurred_opex, net_profit]
                    })
                    st.dataframe(pnl_df, hide_index=True, use_container_width=True, column_config={"Amount (₹)": st.column_config.NumberColumn(format="₹%,.2f")})

                with pl_c2:
                    st.markdown("#### Cost Distribution: COGS, OPEX & CAPEX")
                    cost_dist_df = pd.DataFrame({"Cost Bucket": ["Cost of Goods Sold", "Operating Expenses (OPEX)", "Capital Expenditure (CAPEX)"], "Amount (₹)": [exact_cogs_sold, total_incurred_opex, capex_total]})
                    cost_chart = alt.Chart(cost_dist_df).mark_bar(width=28).encode(x=alt.X("Cost Bucket:N", title="", sort=None, axis=alt.Axis(labelAngle=-15)), y=alt.Y("Amount (₹):Q", title="Amount (₹)"), color=alt.Color("Cost Bucket:N", scale=alt.Scale(domain=["Cost of Goods Sold", "Operating Expenses (OPEX)", "Capital Expenditure (CAPEX)"], range=["#C43D17", "#2563EB", "#1E2252"]), legend=None), tooltip=[alt.Tooltip("Cost Bucket:N", title="Type"), alt.Tooltip("Amount (₹):Q", format=",.2f", title="Amount")]).properties(height=200)
                    st.altair_chart(cost_chart, use_container_width=True)

                st.markdown("#### Revenue in Range - Breakdown")
                if not range_df.empty:
                    total_phonepe = float(range_df["PhonePe"].sum())
                    gross_cash = max(0.0, float(total_rev - total_phonepe))
            
                    adv_paid = 0.0
                    food_paid = 0.0
                    leakage_recorded = float(range_df["Cash_Leakage"].sum()) if "Cash_Leakage" in range_df.columns else 0.0
            
                    if not range_exp.empty and "Status" in range_exp.columns and "Sub_Category" in range_exp.columns:
                        paid_exp = range_exp[range_exp["Status"].astype(str).str.strip().str.lower() == "paid"]
                        if not paid_exp.empty:
                            adv_mask = paid_exp["Sub_Category"].astype(str).str.contains("Advance", case=False, na=False)
                            food_mask = paid_exp["Sub_Category"].astype(str).str.contains("Food|Tea", case=False, na=False)
                            adv_paid = float(paid_exp[adv_mask]["Amount"].sum())
                            food_paid = float(paid_exp[food_mask]["Amount"].sum())

                    net_cash = max(0.0, float(gross_cash - adv_paid - food_paid - leakage_recorded))

                    pie1_df = pd.DataFrame({"Category": ["Gross Cash", "PhonePe"], "Amount": [gross_cash, total_phonepe]})
                    pie1_df = pie1_df[pie1_df["Amount"] > 0] 
            
                    pie1 = alt.Chart(pie1_df).mark_arc(innerRadius=40).encode(
                        theta=alt.Theta("Amount:Q"),
                        color=alt.Color("Category:N", scale=alt.Scale(domain=["Gross Cash", "PhonePe"], range=["#059669", "#3B82F6"])),
                        tooltip=[alt.Tooltip("Category:N", title="Category"), alt.Tooltip("Amount:Q", format=",.2f", title="Amount (₹)")]
                    ).properties(height=250)

                    pie2_df = pd.DataFrame({
                        "Category": ["PhonePe", "Net Cash (In Hand)", "Staff Advance", "Food / Tea"], 
                        "Amount": [total_phonepe, net_cash, adv_paid, food_paid]
                    })
                    pie2_df = pie2_df[pie2_df["Amount"] > 0] 
            
                    pie2 = alt.Chart(pie2_df).mark_arc(innerRadius=40).encode(
                        theta=alt.Theta("Amount:Q"),
                        color=alt.Color("Category:N", scale=alt.Scale(domain=["PhonePe", "Net Cash (In Hand)", "Staff Advance", "Food / Tea"], range=["#3B82F6", "#059669", "#E9C46A", "#F4A261"])),
                        tooltip=[alt.Tooltip("Category:N", title="Category"), alt.Tooltip("Amount:Q", format=",.2f", title="Amount (₹)")]
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
                    exp_cat_list.append({"Category": "Labour Charges (OPEX)", "Amount": float(tot_labour_incurred)})
                if not non_labour_opex_df.empty:
                    for cat, amt in non_labour_opex_df.groupby("Category")["Amount"].sum().items(): 
                        exp_cat_list.append({"Category": cat, "Amount": max(0.0, float(amt))})

                if exp_cat_list:
                    exp_cat_df = pd.DataFrame(exp_cat_list)
                    exp_cat_df = exp_cat_df[exp_cat_df["Amount"] > 0]
            
                    exp_pie = alt.Chart(exp_cat_df).mark_arc(innerRadius=40).encode(
                        theta=alt.Theta("Amount:Q"),
                        color=alt.Color("Category:N", scale=alt.Scale(scheme="tableau10")),
                        tooltip=[alt.Tooltip("Category:N", title="Category"), alt.Tooltip("Amount:Q", format=",.2f", title="Amount (₹)")]
                    ).properties(height=300)

                    exp_chart_col, exp_table_col = st.columns([1.15, 1])
                    with exp_chart_col:
                        st.altair_chart(exp_pie, use_container_width=True)
                    with exp_table_col:
                        exp_breakdown_table = exp_cat_df.copy()
                        exp_breakdown_table["Amount (₹)"] = exp_breakdown_table["Amount"].astype(float)
                        exp_breakdown_table = exp_breakdown_table[["Category", "Amount (₹)"]]
                        exp_total_row = pd.DataFrame([{
                            "Category": "TOTAL",
                            "Amount (₹)": float(exp_breakdown_table["Amount (₹)"].sum())
                        }])
                        exp_breakdown_table = pd.concat([exp_breakdown_table, exp_total_row], ignore_index=True)
                        st.dataframe(
                            exp_breakdown_table,
                            hide_index=True,
                            use_container_width=True,
                            height=min(340, 38 + (len(exp_breakdown_table) * 36)),
                            column_config={
                                "Category": st.column_config.TextColumn("Expense Component"),
                                "Amount (₹)": st.column_config.NumberColumn("Amount (₹)", format="₹%,.2f"),
                            }
                        )
                else: 
                    st.caption("No operating expenses incurred in this date range.")

                st.markdown("---")
                st.markdown("### 2. Comparative Cart Revenue")
                if not range_df.empty:
                    cart_grp = range_df.groupby("Cart")["Total_Collection"].sum().reset_index().rename(columns={"Total_Collection": "Revenue (₹)"}).sort_values("Revenue (₹)", ascending=False)
            
                    base = alt.Chart(cart_grp).encode(
                        x=alt.X("Cart:N", title="", sort="-y", axis=alt.Axis(labelAngle=0, labelFontSize=13, labelPadding=10))
                    )
            
                    bars = base.mark_bar(color="#4F46E5", cornerRadiusTopLeft=4, cornerRadiusTopRight=4, size=60).encode(
                        y=alt.Y("Revenue (₹):Q", title="Total Revenue (₹)", axis=alt.Axis(grid=True, gridColor="#E2E8F0")),
                        tooltip=["Cart", alt.Tooltip("Revenue (₹):Q", format=",.2f")]
                    )
            
                    text_labels = base.mark_text(align='center', baseline='bottom', dy=-5, color="#1E2252", fontWeight=700, fontSize=14).encode(
                        y=alt.Y("Revenue (₹):Q"),
                        text=alt.Text("Revenue (₹):Q", format=",.0f")
                    )
            
                    st.altair_chart((bars + text_labels).properties(height=300), use_container_width=True)
                else: 
                    st.caption("No cart sales in this date range.")



            else:
                st.info("No sales or expense records logged in database yet.")

        # ==================================================================
        # SEPARATE SUB-PAGES: MONTH-WISE, DATE-WISE SALES LOG & DAY-WISE PATTERNS
        # ==================================================================
        else:
            nav_b1, nav_b2, nav_b3, nav_b4, nav_b5 = st.columns([1.05, 1.15, 1.25, 1.15, 1.25], gap="small")
            with nav_b1:
                st.button(
                    "⬅ Back to Financials",
                    key="dash_sub_back_top",
                    type="primary",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=(None,),
                )
            with nav_b2:
                st.button(
                    "🔮 What-If Analysis",
                    key="dash_sub_switch_what_if",
                    type="primary" if active_dash_sub == "what_if" else "secondary",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("what_if",),
                )
            with nav_b3:
                st.button(
                    "📅 Month-Wise Performance",
                    key="dash_sub_switch_month_comp",
                    type="primary" if active_dash_sub == "month_comp" else "secondary",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("month_comp",),
                )
            with nav_b4:
                st.button(
                    "📋 Date-wise Sales Log",
                    key="dash_sub_switch_sales_log",
                    type="primary" if active_dash_sub == "sales_log" else "secondary",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("sales_log",),
                )
            with nav_b5:
                st.button(
                    "📆 Day-Wise & Timing Patterns",
                    key="dash_sub_switch_dow_patterns",
                    type="primary" if active_dash_sub == "dow_patterns" else "secondary",
                    use_container_width=True,
                    on_click=_open_dash_sub_page,
                    args=("dow_patterns",),
                )
            st.markdown("---")

            # ------------------------------------------------------------------
            # SUB-PAGE 1: DATE-WISE SALES LOG
            # ------------------------------------------------------------------
            if active_dash_sub == "sales_log":
                st.subheader("📋 Date-wise Sales Log")
                (
                    dashboard_filter_mode, dash_year, dash_month_num,
                    range_start, range_end, range_df, range_exp,
                    total_rev, total_units, exact_cogs_sold, capex_total,
                    staff_pay_breakdown, unassigned_labour_df, non_labour_opex_df,
                    tot_labour_incurred, other_opex_total, total_incurred_opex,
                    gross_profit, cogs_margin, gross_margin, net_profit, net_margin, opex_margin,
                    avg_divisor_days, avg_rev_per_day, avg_units_per_day
                ) = _render_dash_date_filter_and_compute(key_suffix="sub_sales_log")
                # Sales report tables show completed cart sales dates (<= yesterday) PLUS any direct Freezer sales in the range (including today).
                latest_completed_sales_date = date.today() - timedelta(days=1)
                if not range_df.empty:
                    is_fzr_mask = range_df["Cart"].astype(str).str.strip().str.upper().str.contains("FREEZER")
                    report_sales_df = range_df[
                        (pd.to_datetime(range_df["Date"]).dt.date <= latest_completed_sales_date) | is_fzr_mask
                    ].copy()
                else:
                    report_sales_df = pd.DataFrame()

                st.markdown("#### Date-Wise Daily Sales Log")
                if not report_sales_df.empty:
                    date_wise_agg = report_sales_df.groupby("Date").agg({
                                    "Sold_Total": "sum",
                                    "Total_Collection": "sum",
                                    "PhonePe": "sum",
                                    "Cash": "sum",
                                    "Staff_Advance": "sum",
                                    "Food_Tea_Cash": "sum",
                                    "Cash_Leakage_Explained": "sum",
                                    "Cash_Leakage_Unexplained": "sum"
                                }).reset_index()

                    date_wise_table = date_wise_agg.rename(columns={
                                    "Sold_Total": "Units Sold",
                                    "Total_Collection": "Revenue (₹)",
                                    "PhonePe": "PhonePe (₹)",
                                    "Cash": "Cash (₹)",
                                    "Staff_Advance": "Staff Advance (₹)",
                                    "Food_Tea_Cash": "Food / Tea (₹)",
                                    "Cash_Leakage_Explained": "Leakage Expl (₹)",
                                    "Cash_Leakage_Unexplained": "Leakage Unexpl (₹)"
                                })
                    date_wise_table["Units Sold"] = date_wise_table["Units Sold"].apply(lambda x: int(round(x)))
                    date_wise_table["Date"] = pd.to_datetime(date_wise_table["Date"]).dt.date

                    date_wise_table = date_wise_table.sort_values("Date", ascending=False).reset_index(drop=True)

                    def _highlight_latest_completed_sales_row(row):
                        if row.get("Date") == latest_completed_sales_date:
                            return [
                                "background-color:#ECFDF5;color:#047857;font-weight:900;"
                                for _ in row
                            ]
                        return ["" for _ in row]

                    date_wise_total = {
                        "Units Sold": int(date_wise_table["Units Sold"].sum()),
                        "Revenue (₹)": float(date_wise_table["Revenue (₹)"].sum()),
                        "PhonePe (₹)": float(date_wise_table["PhonePe (₹)"].sum()),
                        "Cash (₹)": float(date_wise_table["Cash (₹)"].sum()),
                        "Staff Advance (₹)": float(date_wise_table["Staff Advance (₹)"].sum()),
                        "Food / Tea (₹)": float(date_wise_table["Food / Tea (₹)"].sum()),
                        "Leakage Expl (₹)": float(date_wise_table["Leakage Expl (₹)"].sum()),
                        "Leakage Unexpl (₹)": float(date_wise_table["Leakage Unexpl (₹)"].sum()),
                    }

                    def _render_report_total_row(total_values):
                        total_cells = [
                            "TOTAL",
                            f"{int(total_values['Units Sold']):,}",
                            f"₹{float(total_values['Revenue (₹)']):,.0f}",
                            f"₹{float(total_values['PhonePe (₹)']):,.0f}",
                            f"₹{float(total_values['Cash (₹)']):,.0f}",
                            f"₹{float(total_values['Staff Advance (₹)']):,.0f}",
                            f"₹{float(total_values['Food / Tea (₹)']):,.0f}",
                            f"₹{float(total_values['Leakage Expl (₹)']):,.0f}",
                            f"₹{float(total_values['Leakage Unexpl (₹)']):,.0f}",
                        ]
                        alignments = ["left"] + ["right"] * 8
                        cell_html = "".join(
                            f"<div style='padding:9px 6px;text-align:{alignments[i]};"
                            f"font-weight:900;color:#111111;font-size:13.5px;line-height:1.25;"
                            f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{escape(str(value))}</div>"
                            for i, value in enumerate(total_cells)
                        )
                        st.markdown(
                            f"""
                            <div style="
                                display:grid;
                                grid-template-columns:0.72fr 0.62fr 1.02fr 0.92fr 0.82fr 1.08fr 0.92fr 1.18fr 1.28fr;
                                background:#BFDBFE;
                                border:1.5px solid #93C5FD;
                                border-radius:0 0 7px 7px;
                                margin-top:-13px;
                                margin-bottom:8px;
                                font-size:13.5px;
                                align-items:center;">
                                {cell_html}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                    date_wise_styled = (
                        date_wise_table.style
                        .set_properties(
                            subset=["Date", "Units Sold", "Revenue (₹)"],
                            **{
                                "background-color": "#EFF6FF",
                                "color": "#1E2252",
                                "font-weight": "700",
                            }
                        )
                        .apply(_highlight_latest_completed_sales_row, axis=1)
                    )

                    st.dataframe(
                        date_wise_styled,
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "Date": st.column_config.DateColumn(format="DD-MMM-YY", width=72),
                            "Units Sold": st.column_config.NumberColumn(width=62),
                            "Revenue (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=102),
                            "PhonePe (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=92),
                            "Cash (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=82),
                            "Staff Advance (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=108),
                            "Food / Tea (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=92),
                            "Leakage Expl (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=118),
                            "Leakage Unexpl (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=126),
                        },
                        row_height=25
                    )
                    _render_report_total_row(date_wise_total)

                    st.markdown("#### Itemized Daily Cart Sales Log")
                    display_cols = [
                        "Date", "Cart", "Sold_Total", "Total_Collection", "PhonePe", "Cash",
                        "Staff_Advance", "Food_Tea_Cash",
                        "Cash_Leakage_Explained", "Cash_Leakage_Unexplained"
                    ]
                    sales_table = report_sales_df[display_cols].rename(columns={
                                    "Sold_Total": "Units Sold",
                                    "Total_Collection": "Revenue (₹)",
                                    "PhonePe": "PhonePe (₹)",
                                    "Cash": "Cash (₹)",
                                    "Staff_Advance": "Staff Advance (₹)",
                                    "Food_Tea_Cash": "Food / Tea (₹)",
                                    "Cash_Leakage_Explained": "Leakage Expl (₹)",
                                    "Cash_Leakage_Unexplained": "Leakage Unexpl (₹)"
                                })
                    sales_table["Units Sold"] = sales_table["Units Sold"].apply(lambda x: int(round(x)))
                    sales_table["Date"] = pd.to_datetime(sales_table["Date"]).dt.date

                    all_carts_and_freezers = get_carts_for_active_location(include_freezer=True)
                    extra_logged_entities = [c for c in sales_table["Cart"].dropna().unique().tolist() if c not in all_carts_and_freezers]
                    for cart_name in (all_carts_and_freezers + extra_logged_entities):
                        cart_table = sales_table[sales_table["Cart"] == cart_name].copy()
                        if cart_table.empty and "FREEZER" in str(cart_name).upper():
                            continue
                        cart_table = cart_table.sort_values("Date", ascending=False).reset_index(drop=True)
                        cart_units = int(cart_table["Units Sold"].sum()) if not cart_table.empty else 0
                        cart_revenue = float(cart_table["Revenue (₹)"].sum()) if not cart_table.empty else 0.0

                        st.markdown(
                            f"""
                            <div style="
                                margin-top:10px;
                                margin-bottom:6px;
                                padding:9px 12px;
                                border:1px solid #93C5FD;
                                border-radius:8px;
                                background:#EFF6FF;
                                display:flex;
                                justify-content:space-between;
                                align-items:center;">
                                <span style="font-weight:900;color:#1E2252;font-size:14px;">🛒 {escape(cart_name)}</span>
                                <span style="font-weight:900;color:#047857;font-size:14px;">
                                    {cart_units:,} units &nbsp;•&nbsp; ₹{cart_revenue:,.0f}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )

                        if cart_table.empty:
                            st.caption("No sales entries for this cart in the selected period.")
                            continue

                        cart_table = cart_table.drop(columns=["Cart"])

                        cart_total = {
                            "Units Sold": int(cart_table["Units Sold"].sum()),
                            "Revenue (₹)": float(cart_table["Revenue (₹)"].sum()),
                            "PhonePe (₹)": float(cart_table["PhonePe (₹)"].sum()),
                            "Cash (₹)": float(cart_table["Cash (₹)"].sum()),
                            "Staff Advance (₹)": float(cart_table["Staff Advance (₹)"].sum()),
                            "Food / Tea (₹)": float(cart_table["Food / Tea (₹)"].sum()),
                            "Leakage Expl (₹)": float(cart_table["Leakage Expl (₹)"].sum()),
                            "Leakage Unexpl (₹)": float(cart_table["Leakage Unexpl (₹)"].sum()),
                        }

                        cart_table_styled = (
                            cart_table.style
                            .set_properties(
                                subset=["Date", "Units Sold", "Revenue (₹)"],
                                **{
                                    "background-color": "#EFF6FF",
                                    "color": "#1E2252",
                                    "font-weight": "700",
                                }
                            )
                            .apply(_highlight_latest_completed_sales_row, axis=1)
                        )

                        st.dataframe(
                            cart_table_styled,
                            hide_index=True,
                            use_container_width=True,
                            column_config={
                                "Date": st.column_config.DateColumn(format="DD-MMM-YY", width=72),
                                "Units Sold": st.column_config.NumberColumn(width=62),
                                "Revenue (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=104),
                                "PhonePe (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=94),
                                "Cash (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=88),
                                "Staff Advance (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=108),
                                "Food / Tea (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=94),
                                "Leakage Expl (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=116),
                                "Leakage Unexpl (₹)": st.column_config.NumberColumn(format="₹%,.0f", width=124),
                            },
                            row_height=25
                        )
                        _render_report_total_row(cart_total)
                else:
                    st.caption("No sales data recorded in this period.")

                # ------------------------------------------------------------------
                # FREEZER SALE TRANSACTIONS & SUMMARY (Filtered by Dashboard Month / Custom Date Range)
                # ------------------------------------------------------------------
                st.markdown("---")
                with st.expander(f"❄️ View Freezer Sale Transactions & Summary ({range_start.strftime('%d-%b-%y')} – {range_end.strftime('%d-%b-%y')})", expanded=True):
                    fzr_txns_df = load_freezer_sale_transactions_df(start_date=range_start, end_date=range_end)
                    if fzr_txns_df.empty:
                        st.caption("No direct Freezer sale transactions recorded in this period.")
                    else:
                        # 1. Date-wise Summary of Freezer Sales
                        st.markdown("##### 📊 Freezer Sales Summary (By Date)")
                        fzr_date_grp = (
                            fzr_txns_df.groupby(["sale_date", "freezer_name"], as_index=False)
                            .agg(
                                txns_count=("id", "count"),
                                total_units=("total_units", "sum"),
                                total_value=("total_value", "sum"),
                                phonepe=("phonepe", "sum"),
                                cash=("cash", "sum"),
                                leakage=("leakage", "sum"),
                            )
                            .sort_values("sale_date", ascending=False)
                        )
                        sum_rows = []
                        for _, sr in fzr_date_grp.iterrows():
                            sum_rows.append({
                                "Date": pd.to_datetime(sr["sale_date"]).strftime("%d-%b-%y"),
                                "Freezer": sr["freezer_name"],
                                "Txns": int(sr["txns_count"]),
                                "Units Sold": int(sr["total_units"]),
                                "Total Value (₹)": f"₹{float(sr['total_value']):,.0f}",
                                "PhonePe (₹)": f"₹{float(sr['phonepe']):,.0f}",
                                "Cash (₹)": f"₹{float(sr['cash']):,.0f}",
                                "Leakage (₹)": f"₹{float(sr['leakage']):,.0f}",
                            })
                        sum_rows.append({
                            "Date": "SUMMARY TOTAL",
                            "Freezer": "—",
                            "Txns": int(fzr_date_grp["txns_count"].sum()),
                            "Units Sold": int(fzr_date_grp["total_units"].sum()),
                            "Total Value (₹)": f"₹{float(fzr_date_grp['total_value'].sum()):,.0f}",
                            "PhonePe (₹)": f"₹{float(fzr_date_grp['phonepe'].sum()):,.0f}",
                            "Cash (₹)": f"₹{float(fzr_date_grp['cash'].sum()):,.0f}",
                            "Leakage (₹)": f"₹{float(fzr_date_grp['leakage'].sum()):,.0f}",
                        })
                        sum_table_df = pd.DataFrame(sum_rows)
                        st.dataframe(
                            sum_table_df.style.apply(
                                lambda r: ["background-color:#EFF6FF;font-weight:900;color:#1E2252;" if r.get("Date") == "SUMMARY TOTAL" else "" for _ in r],
                                axis=1
                            ),
                            hide_index=True,
                            use_container_width=True
                        )

                        # 2. Individual Freezer Sale Transactions Table
                        st.markdown("##### 🧾 Individual Freezer Sale Transactions")
                        txn_rows = []
                        for _, tr in fzr_txns_df.iterrows():
                            flv_parts = [
                                f"{code}:{int(tr.get(FLAVOR_MAP[code]['audit_col'], 0))}"
                                for code in FLAVOR_CODES
                                if int(tr.get(FLAVOR_MAP[code]["audit_col"], 0)) > 0
                            ]
                            txn_rows.append({
                                "Txn #": f"#{int(tr['id'])}",
                                "Date": pd.to_datetime(tr["sale_date"]).strftime("%d-%b-%y"),
                                "Time": pd.to_datetime(tr["created_at"]).strftime("%I:%M %p") if pd.notna(tr.get("created_at")) else "—",
                                "Freezer": tr["freezer_name"],
                                "Sold By": tr.get("sold_by") or "—",
                                "Units": int(tr.get("total_units") or 0),
                                "Total Value (₹)": f"₹{float(tr.get('total_value') or 0):,.0f}",
                                "PhonePe (₹)": f"₹{float(tr.get('phonepe') or 0):,.0f}",
                                "Cash (₹)": f"₹{float(tr.get('cash') or 0):,.0f}",
                                "Leakage (₹)": f"₹{float(tr.get('leakage') or 0):,.0f}",
                                "Flavours": " • ".join(flv_parts) if flv_parts else "—",
                                "Reason": tr.get("reason") or "—",
                            })
                        txn_rows.append({
                            "Txn #": "SUMMARY TOTAL",
                            "Date": f"{len(fzr_txns_df)} txn(s)",
                            "Time": "—",
                            "Freezer": "—",
                            "Sold By": "—",
                            "Units": int(fzr_txns_df["total_units"].sum()),
                            "Total Value (₹)": f"₹{float(fzr_txns_df['total_value'].sum()):,.0f}",
                            "PhonePe (₹)": f"₹{float(fzr_txns_df['phonepe'].sum()):,.0f}",
                            "Cash (₹)": f"₹{float(fzr_txns_df['cash'].sum()):,.0f}",
                            "Leakage (₹)": f"₹{float(fzr_txns_df['leakage'].sum()):,.0f}",
                            "Flavours": "—",
                            "Reason": "—",
                        })
                        txn_table_df = pd.DataFrame(txn_rows)
                        st.dataframe(
                            txn_table_df.style.apply(
                                lambda r: ["background-color:#EFF6FF;font-weight:900;color:#1E2252;" if r.get("Txn #") == "SUMMARY TOTAL" else "" for _ in r],
                                axis=1
                            ),
                            hide_index=True,
                            use_container_width=True
                        )



                st.markdown("---")
                b_back1, _ = st.columns([1.5, 3.5])
                with b_back1:
                    st.button(
                        "⬅ Back to Financials",
                        key="dash_sub_back_bot_sales",
                        type="primary",
                        use_container_width=True,
                        on_click=_open_dash_sub_page,
                        args=(None,),
                    )

            # ------------------------------------------------------------------
            # SUB-PAGE 2: MONTH-WISE PERFORMANCE COMPARISON
            # ------------------------------------------------------------------
            elif active_dash_sub == "month_comp":
                st.subheader("📅 Month-Wise Performance Comparison (Full-Data Months Only)")
                st.caption("Completed full-data months")
                if not daily_df.empty:
                    m_daily = daily_df.copy()
                    m_daily["EntryDate"] = pd.to_datetime(m_daily["Date"]).dt.date
                    m_daily["YM"] = pd.to_datetime(m_daily["Date"]).dt.to_period("M")

                    today_d = date.today()
                    current_ym = pd.Period(today_d, freq="M")

                    # Pre-fetch monthly COGS from daily_cart_items joined with flavors
                    monthly_cogs_df = db_conn.query(
                        """
                        SELECT
                            DATE_TRUNC('month', e.entry_date)::date AS month_start,
                            COALESCE(SUM(i.sold_units * f.cost_price), 0) AS cogs_amount
                        FROM daily_cart_entries e
                        JOIN daily_cart_items i ON i.daily_entry_id = e.id
                        JOIN flavors f ON f.code = i.flavor_code
                        WHERE (:active_loc = 'ALL' OR UPPER(TRIM(COALESCE(e.city, 'HOSUR'))) = :active_loc)
                        GROUP BY DATE_TRUNC('month', e.entry_date)::date;
                        """,
                        params={"active_loc": get_active_location_filter()},
                        ttl="60s"
                    )
                    cogs_by_month_start = {}
                    if not monthly_cogs_df.empty:
                        for _, cr in monthly_cogs_df.iterrows():
                            m_dt = pd.to_datetime(cr["month_start"]).date()
                            cogs_by_month_start[(m_dt.year, m_dt.month)] = float(cr["cogs_amount"] or 0.0)

                    full_month_rows = []
                    for ym in sorted(m_daily["YM"].unique()):
                        # Never include current ongoing or future months
                        if ym >= current_ym:
                            continue
                        yr, mo = int(ym.year), int(ym.month)
                        days_in_mo = calendar.monthrange(yr, mo)[1]
                        mo_start = date(yr, mo, 1)
                        mo_end = date(yr, mo, days_in_mo)

                        sub_d = m_daily[(m_daily["EntryDate"] >= mo_start) & (m_daily["EntryDate"] <= mo_end)]
                        if sub_d.empty:
                            continue

                        min_logged = sub_d["EntryDate"].min()
                        max_logged = sub_d["EntryDate"].max()
                        distinct_days = sub_d["EntryDate"].nunique()

                        # Strict full-month check: data must start on day 1 and reach the final day of the month (or have all calendar days logged)
                        if not (min_logged == mo_start and max_logged == mo_end and distinct_days >= days_in_mo):
                            continue

                        m_fin = compute_period_financials(
                            start_date=mo_start,
                            end_date=mo_end,
                            avg_divisor_days=days_in_mo,
                            daily_df_in=m_daily,
                            exp_df_in=exp_df,
                        )
                        m_rev = m_fin["total_rev"]
                        m_avg_rev = m_fin["avg_rev_per_day"]
                        m_units = m_fin["total_units"]
                        m_cogs = m_fin["exact_cogs_sold"]
                        m_gp = m_fin["gross_profit"]
                        m_gp_pct = m_fin["gross_margin"]
                        m_opex = m_fin["total_incurred_opex"]
                        m_opex_pct = m_fin["opex_margin"]
                        m_np = m_fin["net_profit"]
                        m_np_pct = m_fin["net_margin"]

                        full_month_rows.append({
                            "Month_Order": mo_start,
                            "Month": mo_start.strftime("%b %Y"),
                            "Revenue_Num": round(m_rev, 2),
                            "Avg_Rev_Day_Num": round(m_avg_rev, 2),
                            "Units_Sold_Num": m_units,
                            "COGS_Num": round(m_cogs, 2),
                            "Gross_Profit_Num": round(m_gp, 2),
                            "Gross_Margin_Pct": round(m_gp_pct, 1),
                            "OPEX_Num": round(m_opex, 2),
                            "OPEX_Pct": round(m_opex_pct, 1),
                            "Net_Profit_Num": round(m_np, 2),
                            "Net_Profit_Pct": round(m_np_pct, 1),
                            "Revenue": f"₹{m_rev:,.0f}",
                            "Avg Rev / Day": f"₹{m_avg_rev:,.0f}",
                            "Units Sold": f"{m_units:,}",
                            "COGS": f"₹{m_cogs:,.0f}",
                            "Gr. Profit": f"₹{m_gp:,.0f} ({m_gp_pct:.1f}%)",
                            "OPEX": f"₹{m_opex:,.0f} ({m_opex_pct:.1f}%)",
                            "Net Profit": f"₹{m_np:,.0f} ({m_np_pct:.1f}%)",
                        })

                    if not full_month_rows:
                        st.info("No completed calendar months with full-month data (from 1st to last day of the month) are available yet.")
                    else:
                        full_m_df = pd.DataFrame(full_month_rows).sort_values("Month_Order")
                        display_m_cols = ["Month", "Revenue", "Avg Rev / Day", "Units Sold", "COGS", "Gr. Profit", "OPEX", "Net Profit"]
                        st.dataframe(full_m_df[display_m_cols], hide_index=True, use_container_width=True)

                        st.markdown("##### 📈 Graphic View — Full-Data Months Comparison")
                        month_sort_order = full_m_df["Month"].tolist()

                        def _build_month_bar_chart(val_col, title_text, bar_color, val_format=",.0f", suffix=""):
                            base_c = alt.Chart(full_m_df).encode(
                                x=alt.X("Month:N", sort=month_sort_order, title="", axis=alt.Axis(labelAngle=0, labelFontWeight="bold"))
                            )
                            bars_c = base_c.mark_bar(color=bar_color, cornerRadiusTopLeft=5, cornerRadiusTopRight=5, size=42).encode(
                                y=alt.Y(f"{val_col}:Q", title=title_text),
                                tooltip=[
                                    alt.Tooltip("Month:N", title="Month"),
                                    alt.Tooltip(f"{val_col}:Q", title=title_text, format=val_format)
                                ]
                            )
                            txt_c = base_c.mark_text(dy=-8, fontWeight="bold", fontSize=11.5, color="#0F172A").encode(
                                y=alt.Y(f"{val_col}:Q"),
                                text=alt.Text(f"{val_col}:Q", format=val_format)
                            )
                            return (bars_c + txt_c).properties(title=title_text, height=235)

                        gc1, gc2 = st.columns(2)
                        with gc1:
                            st.altair_chart(_build_month_bar_chart("Revenue_Num", "Revenue (₹)", "#4F46E5", ",.0f"), use_container_width=True)
                        with gc2:
                            st.altair_chart(_build_month_bar_chart("Avg_Rev_Day_Num", "Average Rev / Day (₹)", "#059669", ",.0f"), use_container_width=True)

                        gc3, gc4 = st.columns(2)
                        with gc3:
                            st.altair_chart(_build_month_bar_chart("Units_Sold_Num", "Units Sold", "#1E2252", ",.0f"), use_container_width=True)
                        with gc4:
                            st.altair_chart(_build_month_bar_chart("Net_Profit_Pct", "Net Profit %", "#047857", ".1f"), use_container_width=True)
                else:
                    st.info("No sales data available for month-wise comparison.")

                st.markdown("---")
                b_back3, _ = st.columns([1.5, 3.5])
                with b_back3:
                    st.button(
                        "⬅ Back to Financials",
                        key="dash_sub_back_bot_mc",
                        type="primary",
                        use_container_width=True,
                        on_click=_open_dash_sub_page,
                        args=(None,),
                    )

            # ------------------------------------------------------------------
            # SUB-PAGE 3: DAY-WISE & TIMING PATTERNS
            # ------------------------------------------------------------------
            elif active_dash_sub == "dow_patterns":
                st.subheader("📆 Day-Wise & Timing Patterns")
                (
                    dashboard_filter_mode, dash_year, dash_month_num,
                    range_start, range_end, range_df, range_exp,
                    total_rev, total_units, exact_cogs_sold, capex_total,
                    staff_pay_breakdown, unassigned_labour_df, non_labour_opex_df,
                    tot_labour_incurred, other_opex_total, total_incurred_opex,
                    gross_profit, cogs_margin, gross_margin, net_profit, net_margin, opex_margin,
                    avg_divisor_days, avg_rev_per_day, avg_units_per_day
                ) = _render_dash_date_filter_and_compute(key_suffix="sub_dow_patterns")
                if not range_df.empty:
                    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
                    dow_df = range_df[~range_df["Cart"].astype(str).str.strip().str.upper().isin(["FREEZER", "HOSUR FREEZER"])].copy()
                    dow_df["Day"] = dow_df["Date"].dt.day_name().str[:3]
            
                    if not dow_df.empty:
                        def show_compact_average_table(pivot):
                            headers = "".join(f"<th>{escape(str(day))}</th>" for day in pivot.columns)
                            rows = []
                            for cart, values in pivot.iterrows():
                                cells = "".join(f"<td>{int(round(value)):,}</td>" for value in values)
                                rows.append(f"<tr><th scope='row'>{escape(str(cart))}</th>{cells}</tr>")
                            st.html(
                                "<style>"
                                ".compact-dow-table{width:100%;table-layout:fixed;border-collapse:separate;border-spacing:0;font-size:clamp(9px,.78vw,11.5px);line-height:1.35;background:#FFFFFF;border:1.5px solid #BFDBFE;border-radius:9px;overflow:hidden;box-shadow:0 3px 10px rgba(228,118,61,0.08)}"
                                ".compact-dow-table th,.compact-dow-table td{padding:6px 5px;border-bottom:1px solid #E2E8F0;border-right:1px solid #F1F5F9;text-align:right;overflow-wrap:anywhere;color:#111111;font-weight:700}"
                                ".compact-dow-table thead th{font-weight:800;background:linear-gradient(180deg,#DBEAFE 0%,#BFDBFE 100%);color:#111111;border-bottom:2px solid #93C5FD;text-align:center}"
                                ".compact-dow-table th:first-child{width:29%;text-align:left;padding-left:8px}"
                                ".compact-dow-table tbody tr:nth-child(even) td,.compact-dow-table tbody tr:nth-child(even) th{background:#F8FAFC}"
                                ".compact-dow-table tbody tr:first-child td,.compact-dow-table tbody tr:first-child th{font-weight:900;background:linear-gradient(90deg,#EFF6FF 0%,#DBEAFE 100%);color:#1E2252;border-bottom:1.5px solid #C89B3C}"
                                "</style>"
                                f"<table class='compact-dow-table'><thead><tr><th scope='col'>Cart</th>{headers}</tr></thead>"
                                f"<tbody>{''.join(rows)}</tbody></table>"
                            )

                        dw1, dw2 = st.columns(2)
                        with dw1: 
                            st.write("**Average Units Sold per Day of Week**")
                            units_df = dow_df[dow_df["Sold_Total"] > 0]
                            if not units_df.empty:
                                units_pivot = units_df.pivot_table(index="Cart", columns="Day", values="Sold_Total", aggfunc="mean", fill_value=0)
                                day_cols = [d for d in day_order if d in units_pivot.columns]
                                units_pivot = units_pivot.reindex(columns=day_cols)
                                overall_units = units_df.groupby("Day")["Sold_Total"].mean().reindex(day_cols)
                                units_pivot.loc["Overall Average (per cart)"] = overall_units
                                units_pivot = units_pivot.reindex(["Overall Average (per cart)"] + [cart for cart in units_pivot.index if cart != "Overall Average (per cart)"])
                                show_compact_average_table(units_pivot)
                            else:
                                st.caption("No units sold in this range.")
                        with dw2: 
                            st.write("**Average Revenue (₹) per Day of Week**")
                            rev_pivot = dow_df.pivot_table(index="Cart", columns="Day", values="Total_Collection", aggfunc="mean", fill_value=0)
                            rev_day_cols = [d for d in day_order if d in rev_pivot.columns]
                            rev_pivot = rev_pivot.reindex(columns=rev_day_cols)
                            overall_rev = dow_df.groupby("Day")["Total_Collection"].mean().reindex(rev_day_cols)
                            rev_pivot.loc["Overall Average (per cart)"] = overall_rev
                            rev_pivot = rev_pivot.reindex(["Overall Average (per cart)"] + [cart for cart in rev_pivot.index if cart != "Overall Average (per cart)"])
                            show_compact_average_table(rev_pivot)

                        max1, max2 = st.columns(2)
                        with max1:
                            st.write("**Maximum Units Sold per Day of Week**")
                            if not dow_df.empty:
                                max_units = dow_df.pivot_table(index="Cart", columns="Day", values="Sold_Total", aggfunc="max", fill_value=0)
                                max_units = max_units.reindex(columns=[d for d in day_order if d in max_units.columns])
                                st.dataframe(max_units.round(0).astype(int), use_container_width=True)
                        with max2:
                            st.write("**Maximum Revenue (₹) per Day of Week**")
                            max_rev = dow_df.pivot_table(index="Cart", columns="Day", values="Total_Collection", aggfunc="max", fill_value=0)
                            max_rev = max_rev.reindex(columns=[d for d in day_order if d in max_rev.columns])
                            st.dataframe(max_rev.round(0).astype(int), use_container_width=True)
                    else: 
                        st.caption("No cart entries found in this range.")


                st.markdown("---")
                b_back4, _ = st.columns([1.5, 3.5])
                with b_back4:
                    st.button(
                        "⬅ Back to Financials",
                        key="dash_sub_back_bot_dow",
                        type="primary",
                        use_container_width=True,
                        on_click=_open_dash_sub_page,
                        args=(None,),
                    )

            # ------------------------------------------------------------------
            # SUB-PAGE 4: WHAT-IF ANALYSIS (CLEAN, NO SUB-TEXT)
            # ------------------------------------------------------------------
            elif active_dash_sub == "what_if":
                st.subheader("🔮 What-If Analysis")

                _wi_today = date.today()
                _wi_default_start = _wi_today.replace(day=1)
                _wi_months = [
                    "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"
                ]

                _wi_f1, _wi_f2, _wi_f3 = st.columns([1.15, 1.35, 1.15], gap="small", vertical_alignment="bottom")
                with _wi_f1:
                    _wi_mode = st.radio(
                        "Period",
                        ["Current / Month", "Date Range"],
                        horizontal=True,
                        key="wi_filter_mode",
                        label_visibility="collapsed",
                    )

                if _wi_mode == "Current / Month":
                    with _wi_f2:
                        _wi_m_name = st.selectbox(
                            "Month",
                            _wi_months,
                            index=_wi_today.month - 1,
                            key="wi_month_sel",
                            label_visibility="collapsed",
                        )
                    with _wi_f3:
                        _wi_years = sorted(list({2024, 2025, 2026, _wi_today.year}), reverse=True)
                        _wi_yr = st.selectbox(
                            "Year",
                            _wi_years,
                            index=_wi_years.index(_wi_today.year),
                            key="wi_year_sel",
                            label_visibility="collapsed",
                        )
                    _wi_m_num = _wi_months.index(_wi_m_name) + 1
                    _wi_last_day = calendar.monthrange(_wi_yr, _wi_m_num)[1]
                    wi_start = date(_wi_yr, _wi_m_num, 1)
                    _wi_full_end = date(_wi_yr, _wi_m_num, _wi_last_day)
                    wi_end = min(_wi_full_end, _wi_today) if (_wi_yr == _wi_today.year and _wi_m_num == _wi_today.month) else _wi_full_end
                    if _wi_yr == _wi_today.year and _wi_m_num == _wi_today.month:
                        wi_divisor = max(1, (_wi_today - wi_start).days)
                    else:
                        wi_divisor = max(1, _wi_last_day)
                else:
                    with _wi_f2:
                        wi_start = st.date_input("From", value=_wi_default_start, key="wi_start_dt")
                    with _wi_f3:
                        wi_end = st.date_input("To", value=_wi_today, key="wi_end_dt")
                    if wi_start > wi_end:
                        wi_start, wi_end = wi_end, wi_start
                    wi_divisor = max(1, (wi_end - wi_start).days + 1)

                # Discover all non-test carts for this location & date range
                _wi_carts_ordered = []
                for _c in CARTS:
                    if "test" not in str(_c).lower() and _c not in _wi_carts_ordered:
                        _wi_carts_ordered.append(_c)
                if daily_df is not None and not daily_df.empty and "Date" in daily_df.columns and "Cart" in daily_df.columns:
                    _wi_r_tmp = daily_df[(daily_df["Date"].dt.date >= wi_start) & (daily_df["Date"].dt.date <= wi_end)]
                    for _c in _wi_r_tmp["Cart"].dropna().astype(str).str.strip().unique().tolist():
                        if _c and "test" not in _c.lower() and _c not in _wi_carts_ordered:
                            _wi_carts_ordered.append(_c)

                with st.container(border=True):
                    _wi_h1, _wi_h2 = st.columns([3.5, 1.0], vertical_alignment="center")
                    with _wi_h1:
                        st.markdown("##### Carts")
                    with _wi_h2:
                        if st.button("Enable All", key="wi_enable_all_btn", use_container_width=True):
                            for _c in _wi_carts_ordered:
                                st.session_state[f"wi_tog_{_c}"] = True
                            st.rerun()

                    _wi_enabled_carts = []
                    _n_cols = min(5, max(1, len(_wi_carts_ordered)))
                    for _row_start in range(0, len(_wi_carts_ordered), _n_cols):
                        _row_slice = _wi_carts_ordered[_row_start:_row_start + _n_cols]
                        _t_cols = st.columns(_n_cols, gap="small")
                        for _ci, _cname in enumerate(_row_slice):
                            with _t_cols[_ci]:
                                _k = f"wi_tog_{_cname}"
                                if _k not in st.session_state:
                                    st.session_state[_k] = True
                                _is_on = st.toggle(_cname, key=_k)
                                if _is_on:
                                    _wi_enabled_carts.append(_cname)

                _wi_res = compute_what_if_financials(
                    wi_start, wi_end, _wi_enabled_carts, _wi_carts_ordered,
                    avg_divisor_days=wi_divisor, daily_df_in=daily_df, exp_df_in=exp_df,
                )
                _act_res = compute_what_if_financials(
                    wi_start, wi_end, _wi_carts_ordered, _wi_carts_ordered,
                    avg_divisor_days=wi_divisor, daily_df_in=daily_df, exp_df_in=exp_df,
                )

                def _wi_card(title, val_str, pct_str="", bg="#FFFFFF", border="#CBD5E1", val_color="#0F172A"):
                    _pct_html = f'<div style="font-size:13px;font-weight:800;color:#475569;margin-top:2px;">{pct_str}</div>' if pct_str else ""
                    return f"""
                    <div style="background:{bg};border:1.5px solid {border};border-radius:12px;padding:14px 16px;height:100%;">
                        <div style="font-size:11.5px;font-weight:800;color:#475569;text-transform:uppercase;letter-spacing:0.4px;">{title}</div>
                        <div style="font-size:24px;font-weight:900;color:{val_color};margin-top:4px;line-height:1.15;">{val_str}</div>
                        {_pct_html}
                    </div>
                    """

                _r1c1, _r1c2, _r1c3, _r1c4 = st.columns(4, gap="small")
                with _r1c1:
                    st.markdown(_wi_card("Revenue", f"₹{_wi_res['total_rev']:,.0f}", bg="#FFF7ED", border="#FDBA74", val_color="#C2410C"), unsafe_allow_html=True)
                with _r1c2:
                    st.markdown(_wi_card("Units Sold", f"{_wi_res['total_units']:,}", bg="#EFF6FF", border="#93C5FD", val_color="#1D4ED8"), unsafe_allow_html=True)
                with _r1c3:
                    st.markdown(_wi_card("Avg Rev / Day", f"₹{_wi_res['avg_rev_per_day']:,.0f}", bg="#F0FDF4", border="#86EFAC", val_color="#15803D"), unsafe_allow_html=True)
                with _r1c4:
                    st.markdown(_wi_card("Avg Units / Day", f"{_wi_res['avg_units_per_day']:,.1f}", bg="#F5F3FF", border="#C4B5FD", val_color="#6D28D9"), unsafe_allow_html=True)

                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

                _r2c1, _r2c2, _r2c3, _r2c4 = st.columns(4, gap="small")
                with _r2c1:
                    st.markdown(_wi_card("COGS", f"₹{_wi_res['exact_cogs_sold']:,.0f}", f"{_wi_res['cogs_margin']:.1f}%", bg="#FEF2F2", border="#FCA5A5", val_color="#B91C1C"), unsafe_allow_html=True)
                with _r2c2:
                    st.markdown(_wi_card("Gross Margin", f"₹{_wi_res['gross_profit']:,.0f}", f"{_wi_res['gross_margin']:.1f}%", bg="#ECFDF5", border="#6EE7B7", val_color="#047857"), unsafe_allow_html=True)
                with _r2c3:
                    st.markdown(_wi_card("OPEX (Total)", f"₹{_wi_res['total_incurred_opex']:,.0f}", f"{_wi_res['opex_margin']:.1f}%", bg="#FEFCE8", border="#FDE047", val_color="#A16207"), unsafe_allow_html=True)
                with _r2c4:
                    _nm_col = "#047857" if _wi_res["net_profit"] >= 0 else "#B91C1C"
                    _nm_bg = "#ECFDF5" if _wi_res["net_profit"] >= 0 else "#FEF2F2"
                    _nm_bd = "#6EE7B7" if _wi_res["net_profit"] >= 0 else "#FCA5A5"
                    st.markdown(_wi_card("Net Margin", f"₹{_wi_res['net_profit']:,.0f}", f"{_wi_res['net_margin']:.1f}%", bg=_nm_bg, border=_nm_bd, val_color=_nm_col), unsafe_allow_html=True)

                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)

                def _ratio_badge(wi_v, act_v):
                    _d = wi_v - act_v
                    if abs(_d) < 0.005:
                        return "<span style='color:#64748B;'>— 0.00x</span>"
                    if _d > 0:
                        return f"<span style='color:#047857;'>▲ +{_d:.2f}x</span>"
                    return f"<span style='color:#B91C1C;'>▼ {_d:.2f}x</span>"

                _r3c1, _r3c2, _r3c3, _r3c4, _r3c5 = st.columns(5, gap="small")
                with _r3c1:
                    st.markdown(_wi_card("OPEX (Common)", f"₹{_wi_res['opex_common']:,.0f}", f"{_wi_res['opex_common_pct']:.1f}%", bg="#F8FAFC", border="#CBD5E1", val_color="#334155"), unsafe_allow_html=True)
                with _r3c2:
                    st.markdown(_wi_card("OPEX (Cart Specific)", f"₹{_wi_res['opex_cart_specific']:,.0f}", f"{_wi_res['opex_cart_pct']:.1f}%", bg="#FFFBEB", border="#FCD34D", val_color="#B45309"), unsafe_allow_html=True)
                with _r3c3:
                    st.markdown(_wi_card("Rev / Cart OPEX", f"{_wi_res['rev_to_cart_opex']:.2f}x", _ratio_badge(_wi_res['rev_to_cart_opex'], _act_res['rev_to_cart_opex']), bg="#F0FDFA", border="#99F6E4", val_color="#0F766E"), unsafe_allow_html=True)
                with _r3c4:
                    st.markdown(_wi_card("Gross Margin / Cart OPEX", f"{_wi_res['gm_to_cart_opex']:.2f}x", _ratio_badge(_wi_res['gm_to_cart_opex'], _act_res['gm_to_cart_opex']), bg="#F0FDF4", border="#86EFAC", val_color="#15803D"), unsafe_allow_html=True)
                with _r3c5:
                    st.markdown(_wi_card("Net Margin / Cart OPEX", f"{_wi_res['nm_to_cart_opex']:.2f}x", _ratio_badge(_wi_res['nm_to_cart_opex'], _act_res['nm_to_cart_opex']), bg="#EFF6FF", border="#93C5FD", val_color="#1D4ED8"), unsafe_allow_html=True)

                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

                def _ratio_diff_txt(wi_v, act_v):
                    _d = wi_v - act_v
                    if abs(_d) < 0.005:
                        return "— 0.00x"
                    return f"▲ +{_d:.2f}x" if _d > 0 else f"▼ {_d:.2f}x"

                _cmp_rows = [
                    ("Revenue", f"₹{_act_res['total_rev']:,.0f}", f"₹{_wi_res['total_rev']:,.0f}", f"₹{_wi_res['total_rev'] - _act_res['total_rev']:+,.0f}"),
                    ("Units Sold", f"{_act_res['total_units']:,}", f"{_wi_res['total_units']:,}", f"{_wi_res['total_units'] - _act_res['total_units']:+,}"),
                    ("Avg Rev / Day", f"₹{_act_res['avg_rev_per_day']:,.0f}", f"₹{_wi_res['avg_rev_per_day']:,.0f}", f"₹{_wi_res['avg_rev_per_day'] - _act_res['avg_rev_per_day']:+,.0f}"),
                    ("Avg Units / Day", f"{_act_res['avg_units_per_day']:,.1f}", f"{_wi_res['avg_units_per_day']:,.1f}", f"{_wi_res['avg_units_per_day'] - _act_res['avg_units_per_day']:+,.1f}"),
                    ("COGS", f"₹{_act_res['exact_cogs_sold']:,.0f} ({_act_res['cogs_margin']:.1f}%)", f"₹{_wi_res['exact_cogs_sold']:,.0f} ({_wi_res['cogs_margin']:.1f}%)", f"₹{_wi_res['exact_cogs_sold'] - _act_res['exact_cogs_sold']:+,.0f}"),
                    ("Gross Margin", f"₹{_act_res['gross_profit']:,.0f} ({_act_res['gross_margin']:.1f}%)", f"₹{_wi_res['gross_profit']:,.0f} ({_wi_res['gross_margin']:.1f}%)", f"₹{_wi_res['gross_profit'] - _act_res['gross_profit']:+,.0f}"),
                    ("OPEX (Common)", f"₹{_act_res['opex_common']:,.0f} ({_act_res['opex_common_pct']:.1f}%)", f"₹{_wi_res['opex_common']:,.0f} ({_wi_res['opex_common_pct']:.1f}%)", f"₹{_wi_res['opex_common'] - _act_res['opex_common']:+,.0f}"),
                    ("OPEX (Cart Specific)", f"₹{_act_res['opex_cart_specific']:,.0f} ({_act_res['opex_cart_pct']:.1f}%)", f"₹{_wi_res['opex_cart_specific']:,.0f} ({_wi_res['opex_cart_pct']:.1f}%)", f"₹{_wi_res['opex_cart_specific'] - _act_res['opex_cart_specific']:+,.0f}"),
                    ("OPEX (Total)", f"₹{_act_res['total_incurred_opex']:,.0f} ({_act_res['opex_margin']:.1f}%)", f"₹{_wi_res['total_incurred_opex']:,.0f} ({_wi_res['opex_margin']:.1f}%)", f"₹{_wi_res['total_incurred_opex'] - _act_res['total_incurred_opex']:+,.0f}"),
                    ("Net Margin", f"₹{_act_res['net_profit']:,.0f} ({_act_res['net_margin']:.1f}%)", f"₹{_wi_res['net_profit']:,.0f} ({_wi_res['net_margin']:.1f}%)", f"₹{_wi_res['net_profit'] - _act_res['net_profit']:+,.0f}"),
                    ("Rev / Cart OPEX", f"{_act_res['rev_to_cart_opex']:.2f}x", f"{_wi_res['rev_to_cart_opex']:.2f}x", _ratio_diff_txt(_wi_res['rev_to_cart_opex'], _act_res['rev_to_cart_opex'])),
                    ("Gross Margin / Cart OPEX", f"{_act_res['gm_to_cart_opex']:.2f}x", f"{_wi_res['gm_to_cart_opex']:.2f}x", _ratio_diff_txt(_wi_res['gm_to_cart_opex'], _act_res['gm_to_cart_opex'])),
                    ("Net Margin / Cart OPEX", f"{_act_res['nm_to_cart_opex']:.2f}x", f"{_wi_res['nm_to_cart_opex']:.2f}x", _ratio_diff_txt(_wi_res['nm_to_cart_opex'], _act_res['nm_to_cart_opex'])),
                ]
                _cmp_df = pd.DataFrame(_cmp_rows, columns=["Metric", "Actual", "What-If", "Difference"])
                st.dataframe(_cmp_df, hide_index=True, use_container_width=True, height=495)