import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
import xlsxwriter
from fpdf import FPDF
from PIL import Image
import time

# --- Page Setup ---
st.set_page_config(page_title="Mixing Ratio Worksheet", layout="centered")

# --- Splash Screen with Loading Animation ---
if "splash_shown" not in st.session_state:
    st.session_state.splash_shown = False

if not st.session_state.splash_shown:
    splash = st.empty()
    splash.image("MR Splash Screen.png", use_container_width=True)

    loading_text = st.empty()
    for i in range(6):  # 6 x 0.5s = 3 seconds
        loading_text.markdown(f"<h4 style='text-align: center;'>Loading{'.' * (i % 4)}</h4>", unsafe_allow_html=True)
        time.sleep(0.5)

    st.session_state.splash_shown = True
    st.rerun()

# --- App Title ---
st.title("🧪 Mixing Ratio Worksheet")

# --- Initialize Entry Log ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# --- Sidebar Setup (no reset buttons anymore) ---
with st.sidebar:
    st.header("🔧 Setup")
    resin_name = st.text_input("Resin Name")
    hardener_name = st.text_input("Hardener Name")
    hardener_ratio = st.number_input("Hardener Ratio (e.g. 30)", min_value=1.0, step=0.1)
    tolerance_percent = st.number_input("Tolerance (%)", min_value=0.1, step=0.1)
    resin_ratio = 100

# --- Entry Form ---
if all([resin_name, hardener_name, hardener_ratio, tolerance_percent]):
    st.success("✅ Setup complete. Enter weights below.")
    with st.form(key="entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            resin_weight = st.number_input("Resin Weight (g)", min_value=0.0, step=0.1)
        with col2:
            hardener_weight = st.number_input("Hardener Weight (g)", min_value=0.0, step=0.1)
        submitted = st.form_submit_button("Next ➕")

    if submitted and resin_weight > 0 and hardener_weight > 0:
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
            label="📥 Download Excel Report",
            data=excel_output,
            file_name="Mixing_Ratio_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with col2:
        if st.button("📄 Generate and Download PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", uni=True)
            pdf.set_font("DejaVu", size=14)
            pdf.cell(200, 10, txt="🧪 Mixing Ratio Report", ln=True, align="C")
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
                label="📥 Download PDF Report",
                data=pdf_output,
                file_name="Mixing_Ratio_Report.pdf",
                mime="application/pdf"
            )
else:
    st.info("No entries yet. Enter data above and press 'Next ➕'.")
