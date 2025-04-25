import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
import xlsxwriter
from fpdf import FPDF
from PIL import Image

st.set_page_config(page_title="Mixing Ratio Worksheet", layout="centered")
st.title("🧪 Mixing Ratio Worksheet")

# --- Initialize Data Store ---
if "entries" not in st.session_state:
    st.session_state.entries = []
if "submitted_success" not in st.session_state:
    st.session_state.submitted_success = False

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
    with st.form(key="entry_form"):
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

                st.session_state.submitted_success = True  # 🔥 Flag set
            else:
                st.error("Resin and Hardener weights must be greater than 0.")
        except ValueError:
            st.error("Please enter valid numeric values for Resin and Hardener Weights.")

# --- After form: Safe rerun to reset fields ---
if st.session_state.submitted_success:
    st.session_state.submitted_success = False
    st.experimental_rerun()

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

