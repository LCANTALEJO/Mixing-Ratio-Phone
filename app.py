import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
import xlsxwriter
from fpdf import FPDF
from PIL import Image
import random

st.set_page_config(page_title="Mixing Ratio Worksheet", layout="centered")
st.title("🧪 Mixing Ratio Worksheet")

# --- Initialize Data Store ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# --- Sidebar Setup ---
with st.sidebar:
    st.header("🔧 Setup")
    resin_name = st.text_input("Resin Name")
    hardener_name = st.text_input("Hardener Name")
    hardener_ratio_input = st.text_input("Hardener Ratio (e.g., 30)")
    tolerance_percent_input = st.text_input("Tolerance (%) (e.g., 3)")

    resin_ratio = 100

    st.markdown("---")
    if st.button("🔄 Reset All"):
        st.session_state.entries = []
        st.experimental_rerun()

# --- Validate Setup Before Proceeding ---
setup_complete = False
if resin_name and hardener_name and hardener_ratio_input and tolerance_percent_input:
    try:
        hardener_ratio = float(hardener_ratio_input)
        tolerance_percent = float(tolerance_percent_input)
        setup_complete = True
    except ValueError:
        st.error("Please enter valid numeric values for Hardener Ratio and Tolerance %.")

# --- Entry Form ---
if setup_complete:
    st.success("✅ Setup complete. Enter weights below.")

    form_key = f"entry_form_{random.randint(1, 1000000)}"
    with st.form(key=form_key):
        resin_weight_input = st.text_input("Resin Weight (g)")
        hardener_weight_input = st.text_input("Hardener Weight (g)")
        submitted = st.form_submit_button("Next ➕")

    if submitted:
        try:
            resin_weight = float(resin_weight_input)
            hardener_weight = float(hardener_weight_input)
            if resin_weight > 0 and hardener_weight > 0:
                ideal = (resin_weight / resin_ratio) * hardener_ratio
                tol = ideal * (tolerance_percent / 100)
                min_acc = ideal - tol
                max_acc = ideal + tol
                deviation = ((hardener_weight - ideal) / ideal) * 100
                status = "✅ PASS" if min_acc <= hardener_weight <= max_acc else "❌ FAIL"

                st.session_state.entries.append({
                    "Entry #": len(st.session_state.entries) + 1,
                    f"{resin_name} (g)": resin_weight,
                    f"{hardener_name} (g)": hardener_weight,
                    "% Deviation": round(deviation, 2),
                    "Result": status
                })

                st.success("✅ Entry added!")
            else:
                st.error("Resin and Hardener weights must be greater than 0.")
        except ValueError:
            st.error("Please enter valid numeric values for Resin and Hardener Weights.")

# --- Show Table and Graph ---
if st.session_state.entries:
    df = pd.DataFrame(st.session_state.entries)
    st.subheader("📋 Mixing Log")
    st.dataframe(df, use_container_width=True)

    st.subheader("📈 Deviation Chart")
    fig = px.line(df, x="Entry #", y="% Deviation", markers=True, title="Deviation of Hardener vs Entry #")
    failed = df[df["Result"].str.contains("FAIL")]
    if not failed.empty:
        fig.add_scatter(x=failed["Entry #"], y=failed["% Deviation"],
                        mode="markers",
                        marker=dict(size=12, color="red", line=dict(color="black", width=2)),
                        name="Failed")

    fig.add_hline(y=tolerance_percent, line_dash="dash", line_color="green", annotation_text=f"+{tolerance_percent}%")
    fig.add_hline(y=-tolerance_percent, line_dash="dash", line_color="green", annotation_text=f"-{tolerance_percent}%")
    fig.update_yaxes(range=[-10, 10])
    st.plotly_chart(fig, use_container_width=True)

    # --- Export Buttons Section ---
    fig_img = pio.to_image(fig, format="png", width=800, height=400)
    fig_io = io.BytesIO(fig_img)

    setup_info = [
        ["Resin Name", resin_name],
        ["Hardener Name", hardener_name],
        ["Mixing Ratio", f"{resin_ratio}:{hardener_ratio}"],
        ["Tolerance (%)", f"±{tolerance_percent}%"]
    ]

    st.subheader("📤 Download Reports")
    col1, col2 = st.columns(2)

    with col1:
        excel_output = io.BytesIO()
        workbook = xlsxwriter.Workbook(excel_output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Mixing Report")

        for r, (label, value) in enumerate(setup_info):
            worksheet.write(r, 0, label)
            worksheet.write(r, 1, value)

        start_row = len(setup_info) + 2
        for c, col_name in enumerate(df.columns):
            worksheet.write
