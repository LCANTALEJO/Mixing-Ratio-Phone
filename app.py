import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
import xlsxwriter
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Mixing Ratio Worksheet", layout="centered")
st.title("\U0001f9ea Mixing Ratio Worksheet")

# --- Session Reset Flags ---
if "reset_all" not in st.session_state:
    st.session_state.reset_all = False
if "reset_data" not in st.session_state:
    st.session_state.reset_data = False

if st.session_state.reset_data:
    keys_to_keep = {"resin_name", "hardener_name", "hardener_ratio", "tolerance_percent", "entry_count", "reset_all", "reset_data"}
    for k in list(st.session_state.keys()):
        if k not in keys_to_keep:
            del st.session_state[k]
    st.session_state.reset_data = False
    st.rerun()

if st.session_state.reset_all:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# --- Sidebar Setup ---
with st.sidebar:
    st.header("\U0001f527 Setup")
    resin_name = st.text_input("Resin Name", key="resin_name")
    hardener_name = st.text_input("Hardener Name", key="hardener_name")
    hardener_ratio = st.number_input("Hardener Ratio (e.g. 30)", min_value=1.0, step=0.1, key="hardener_ratio")
    tolerance_percent = st.number_input("Tolerance (%)", min_value=0.1, step=0.1, key="tolerance_percent")
    resin_ratio = 100

    st.markdown("---")
    st.button("\U0001f504 Reset All", on_click=lambda: st.session_state.update(reset_all=True))
    st.button("\u267b\ufe0f Reset Data Only", on_click=lambda: st.session_state.update(reset_data=True))

# --- Initialize Entry Log ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# --- Entry Form ---
if all([resin_name, hardener_name, hardener_ratio, tolerance_percent]):
    st.success("\u2705 Setup complete. Enter weights below.")
    with st.form(key="entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            resin_weight = st.number_input("Resin Weight (g)", min_value=0.0, step=0.1, key="input_resin")
        with col2:
            hardener_weight = st.number_input("Hardener Weight (g)", min_value=0.0, step=0.1, key="input_hardener")
        submitted = st.form_submit_button("Next \u2795")

    if submitted and resin_weight > 0 and hardener_weight > 0:
        ideal = (resin_weight / resin_ratio) * hardener_ratio
        tol = ideal * (tolerance_percent / 100)
        min_acc = ideal - tol
        max_acc = ideal + tol
        deviation = ((hardener_weight - ideal) / ideal) * 100
        status = "\u2705 PASS" if min_acc <= hardener_weight <= max_acc else "\u274c FAIL"

        st.session_state.entries.append({
            "Entry #": len(st.session_state.entries) + 1,
            f"{resin_name} (g)": resin_weight,
            f"{hardener_name} (g)": hardener_weight,
            "% Deviation": round(deviation, 2),
            "Result": status
        })

# --- Show Table and Graph ---
if st.session_state.entries:
    df = pd.DataFrame(st.session_state.entries)
    st.subheader("\ud83d\udccb Mixing Log")
    st.dataframe(df, use_container_width=True)

    st.subheader("\ud83d\udcc8 Deviation Chart")
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

    st.subheader("\ud83d\udcc4 Download Reports")
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
            worksheet.write(start_row, c, col_name)
        for r_idx, row in enumerate(df.itertuples(index=False), start=start_row + 1):
            for c_idx, value in enumerate(row):
                worksheet.write(r_idx, c_idx, value)

        worksheet.insert_image(start_row + len(df) + 3, 0, "deviation_chart.png", {
            'image_data': fig_io,
            'x_scale': 0.9,
            'y_scale': 0.9
        })

        workbook.close()
        excel_output.seek(0)

        st.download_button(
            label="\ud83d\udcc5 Download Excel Report",
            data=excel_output,
            file_name="Mixing_Ratio_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        generate_pdf = st.button("\ud83d\udcc4 Generate and Download PDF")

    if generate_pdf:
        pdf = FPDF()
        pdf.add_page()
        pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
        pdf.set_font("DejaVu", size=14)
        pdf.cell(200, 10, txt="\U0001f9ea Mixing Ratio Report", ln=True, align="C")
        pdf.ln(5)

        pdf.set_font("DejaVu", size=12)
        for label, value in setup_info:
            pdf.cell(80, 8, f"{label}:", 0)
            pdf.cell(100, 8, str(value), 0, ln=True)
        pdf.ln(5)

        col_width = 40
        row_height = 8
        for col in df.columns:
            pdf.cell(col_width, row_height, str(col), border=1)
        pdf.ln(row_height)

        for row in df.itertuples(index=False):
            for item in row:
                pdf.cell(col_width, row_height, str(item), border=1)
            pdf.ln(row_height)

        img = Image.open(io.BytesIO(fig_img))
        img_path = "plot_temp.png"
        img.save(img_path)
        pdf.ln(5)
        pdf.image(img_path, x=10, w=190)

        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        st.download_button(
            label="\ud83d\udcc5 Download PDF Report",
            data=pdf_output,
            file_name="Mixing_Ratio_Report.pdf",
            mime="application/pdf"
        )
else:
    st.info("No entries yet. Enter data above and press 'Next \u2795'.")
