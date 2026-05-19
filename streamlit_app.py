import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from PIL import Image
import easyocr
import pytesseract
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from fpdf import FPDF

# ====================== PAGE CONFIG ======================
st.set_page_config(page_title="Lux Online Trading Journal", layout="wide")

# ====================== LOGO & THEME ======================
LOGO_FILE = "logo.png"

dark_mode = st.sidebar.toggle("🌙 Dark Mode (Gold Theme)", value=True)

if dark_mode:
    st.markdown("""
    <style>
        .stApp { background-color: #0E1117; color: #FAFAFA; }
        .stButton>button { background-color: #FFD700; color: #0E1117; font-weight: bold; border-radius: 8px; }
        label, h1, h2, h3 { color: #FFD700 !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# ====================== CENTERED HEADER ======================
col1, col2, col3 = st.columns([1, 3, 1])

with col2:
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=340)
    else:
        st.markdown("<h1 style='text-align: center; color: #FFD700;'>Lux Online</h1>", unsafe_allow_html=True)

    st.markdown("""
        <h2 style='text-align: center; color: #FFD700; margin-top: 8px; margin-bottom: 5px;'>
            Trading Journal
        </h2>
    """, unsafe_allow_html=True)

    st.markdown("""
        <p style='text-align: center; color: #AAAAAA; margin: 0;'>
            Professional Crypto Trading Journal with OCR & Analytics
        </p>
    """, unsafe_allow_html=True)

st.divider()

# ====================== DATA ======================
os.makedirs("screenshots", exist_ok=True)
CSV_FILE = "crypto_trades.csv"

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE)
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce').dt.date
else:
    df = pd.DataFrame(columns=["Date", "Symbol", "Direction", "Entry", "Exit", "Size",
                               "P&L", "P&L%", "Reason", "Screenshot", "Notes", "Source"])

# ====================== SIDEBAR ======================
st.sidebar.title("⚙️ Controls")
starting_capital = st.sidebar.number_input("Starting Capital (USDT)", value=10000.0, min_value=1000.0)

st.sidebar.header("🔍 Filters")
filter_symbol = st.sidebar.text_input("Symbol", "")
filter_direction = st.sidebar.selectbox("Direction", ["All", "Long", "Short"])
col1, col2 = st.sidebar.columns(2)
filter_start = col1.date_input("From", datetime.now().date() - timedelta(days=90))
filter_end = col2.date_input("To", datetime.now().date())

# Apply filters
filtered_df = df.copy()
if filter_symbol:
    filtered_df = filtered_df[filtered_df["Symbol"].str.contains(filter_symbol, case=False)]
if filter_direction != "All":
    filtered_df = filtered_df[filtered_df["Direction"] == filter_direction]
if not filtered_df.empty:
    filtered_df = filtered_df[(filtered_df["Date"] >= filter_start) & (filtered_df["Date"] <= filter_end)]

# ==================== SCREENSHOT + OCR ====================
st.subheader("📸 Screenshot")
c1, c2 = st.columns(2)
with c1:
    camera = st.camera_input("Take photo of chart")
with c2:
    upload = st.file_uploader("Upload screenshot", type=["png", "jpg", "jpeg"])

screenshot_path = None
extracted = ""
file = camera or upload

if file:
    image = Image.open(file)
    screenshot_path = f"screenshots/{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    image.save(screenshot_path)
    st.image(image, use_column_width=True)

    with st.spinner("🔍 Running OCR..."):
        try:
            extracted = pytesseract.image_to_string(image)
        except:
            try:
                reader = easyocr.Reader(['en'])
                result = reader.readtext(screenshot_path)
                extracted = " ".join([det[1] for det in result])
            except:
                extracted = "OCR failed - enter manually"

    st.text_area("Extracted Text (you can edit)", extracted, height=100)

# ==================== TRADE ENTRY FORM ====================
with st.form("trade_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        date = st.date_input("Date", datetime.now().date())
        symbol = st.text_input("Symbol", "SOLUSDT")
        direction = st.selectbox("Direction", ["Long", "Short"])
    with c2:
        entry = st.number_input("Entry Price", value=0.0, format="%.6f")
        exit_p = st.number_input("Exit Price", value=0.0, format="%.6f")
        size = st.number_input("Size (USDT)", value=0.0, format="%.2f")
    
    pnl = st.number_input("P&L (USDT)", value=0.0, format="%.2f")
    pnl_pct = st.number_input("P&L %", value=0.0, format="%.2f")
    reason = st.text_input("Reason / Strategy", value=extracted[:100] if extracted else "")
    notes = st.text_area("Notes / Emotions / Lessons")
    
    if st.form_submit_button("💾 Save Trade"):
        new_row = pd.DataFrame([{
            "Date": date, "Symbol": symbol, "Direction": direction,
            "Entry": entry, "Exit": exit_p, "Size": size,
            "P&L": pnl, "P&L%": pnl_pct, "Reason": reason,
            "Screenshot": screenshot_path or "", "Notes": notes, "Source": "Manual/OCR"
        }])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)
        st.success("✅ Trade Saved Successfully!")
        st.rerun()

# ==================== PERFORMANCE DASHBOARD ====================
st.subheader("📊 Performance Dashboard")
if not filtered_df.empty:
    df_sorted = filtered_df.sort_values("Date").copy()
    df_sorted["Cumulative_PnL"] = df_sorted["P&L"].cumsum()
    df_sorted["Equity"] = starting_capital + df_sorted["Cumulative_PnL"]
    
    total_pnl = df_sorted["P&L"].sum()
    total_trades = len(df_sorted)
    win_rate = (len(df_sorted[df_sorted["P&L"] > 0]) / total_trades * 100) if total_trades > 0 else 0
    
    tab1, tab2, tab3 = st.tabs(["📈 Equity Curve", "📅 Monthly Breakdown", "⚡ Risk Metrics"])
    
    with tab1:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df_sorted["Date"], y=df_sorted["Equity"], 
                                name="Equity Curve", line=dict(color="#FFD700", width=3)))
        fig.add_trace(go.Scatter(x=df_sorted["Date"], 
                                y=df_sorted["Equity"] - df_sorted["Equity"].cummax(), 
                                name="Drawdown", line=dict(color="#FF4C4C", dash="dash")))
        fig.update_layout(height=500, template="plotly_dark" if dark_mode else "plotly_white")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        df_sorted["Month"] = pd.to_datetime(df_sorted["Date"]).dt.to_period('M').astype(str)
        monthly = df_sorted.groupby("Month")["P&L"].sum()
        st.bar_chart(monthly)
    
    with tab3:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total P&L", f"${total_pnl:,.2f}")
        c2.metric("Win Rate", f"{win_rate:.1f}%")
        c3.metric("Total Trades", total_trades)

# ==================== TRADE LIST ====================
st.subheader("📋 Recent Trades")
if not filtered_df.empty:
    st.dataframe(filtered_df, use_container_width=True)
else:
    st.info("No trades recorded yet.")

# ==================== DOWNLOADS ====================
col1, col2 = st.columns(2)
with col1:
    st.download_button("📥 Download CSV", df.to_csv(index=False), "lux_trades.csv", type="primary")

with col2:
    if st.button("📄 Export PDF Report"):
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Lux Online Trading Journal Report", ln=1, align="C")
            pdf.set_font("Arial", "", 12)
            pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1)
            pdf.cell(0, 10, f"Total P&L: ${total_pnl:,.2f} | Win Rate: {win_rate:.1f}%", ln=1)
            pdf.output("lux_report.pdf")
            
            with open("lux_report.pdf", "rb") as f:
                st.download_button("⬇️ Download PDF", f, "lux_trading_report.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF Error: {e}")

st.caption("Made for serious traders")