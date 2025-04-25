import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
import xlsxwriter

# --- App Config ---
st.set_page_config(page_title="Mixing Ratio Log", layout="centered")
st.title("🧪 Mixing Ratio Worksheet")

# --- Setup Form ---
with st.sidebar:
    st.header("🔧 Setup")
    resin_name = st.text_input("Resin Name", key="resin_name")
    hardener_name = st.text_input("Hardener Name", key="hardener_name")
    hardener_ratio = st.number_input("Hardener Ratio (e.g. 30)", min_value=1.0, step=0.1, key="hardener_ratio")
    tolerance_percent = st.number_input("Tolerance (%)", min_value=0.1, step=0.1, key="tolerance_percent")
    resin_ratio = 100

# --- Initialize Session State for Entry Log ---
if "entries" not in st.session_state:
    st.session_state.entries = []

# --- Data Entry Section ---
if resin_name and hardener_name and hardener_ratio > 0 and tolerance_percent > 0:
    st.subheader("📥 Enter Actual Weights")

    with st.form(key="entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            resin_weight = st.number_input("Resin Weight (g)", min_value=0.0, step=0.1, key="input_resin")
        with col2:
            hardener_weight = st.number_input("Hardener Weight (g)", min_value=0.0, step=0.1, key="input_hardener")
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

# --- Results Table ---
if st.session_state.entries:
    df = pd.DataFrame(st.session_state.entries)
    st.subheader("📋 Mixing Log")
    st.dataframe(df, use_container_width=True)

    # --- Plot Graph ---
    st.subheader("📈 Deviation Chart")
    fig = px.line(df, x="Entry #", y="% Deviation", markers=True, title="Deviation Over Time")
    failed = df[df["Result"].str.contains("FAIL")]
    if not failed.empty:
        fig.add_scatter(
            x=failed["Entry #"], y=failed["% Deviation"],
            mode="markers",
            marker=dict(size=12, color="red", line=dict(color="black", width=2)),
            name="Failed"
        )
    fig.add_hline(y=tolerance_percent, line_dash="dash", line_color="green", annotation_text=f"+{tolerance_percent}%")
    fig.add_hline(y=-tolerance_percent, line_dash="dash", line_color="green", annotation_text=f"-{tolerance_percent}%")
    fig.update_yaxes(range=[-10, 10])
    st.plotly_chart(fig, use_container_width=True)

    # --- Export to Excel ---
    st.subheader("📤 Download Report")
    fig_img = pio.to_image(fig, format="png", width=800, height=400)
    fig_io = io.BytesIO(fig_img)

    excel_output = io.BytesIO()
    workbook = xlsxwriter.Workbook(excel_output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Mixing Report")

    # Header Info
    setup_info = [
        ["Resin Name", resin_name],
        ["Hardener Name", hardener_name],
        ["Mixing Ratio", f"{resin_ratio}:{hardener_ratio}"],
        ["Tolerance (%)", f"±{tolerance_percent}%"]
    ]
    for r, (label, value) in enumerate(setup_info):
        worksheet.write(r, 0, label)
        worksheet.write(r, 1, value)

    # Data Table
    start_row = len(setup_info) + 2
    for c, col_name in enumerate(df.columns):
        worksheet.write(start_row, c, col_name)
    for r_idx, row in enumerate(df.itertuples(index=False), start=start_row + 1):
        for c_idx, value in enumerate(row):
            worksheet.write(r_idx, c_idx, value)

    # Insert Graph Image
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

else:
    st.info("No entries yet. Enter data above and press 'Next ➕'.")

