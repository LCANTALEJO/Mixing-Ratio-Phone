import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.io as pio
import io
import xlsxwriter

st.set_page_config(page_title="Mixing Ratio Worksheet", layout="centered")
st.title("🧪 Mixing Ratio Worksheet")

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
    st.header("🛠️ Setup")
    resin_name = st.text_input("Resin Name", key="resin_name")
    hardener_name = st.text_input("Hardener Name", key="hardener_name")
    hardener_ratio = st.number_input("Hardener Ratio (e.g. 30)", min_value=1.0, step=0.1, key="hardener_ratio")
    tolerance_percent = st.number_input("Tolerance (%)", min_value=0.1, step=0.1, key="tolerance_percent")
    entry_count = st.number_input("Data Points (max 30)", min_value=1, max_value=30, step=1, key="entry_count")
    
    st.markdown("---")
    st.button("🔄 Reset All", on_click=lambda: st.session_state.update(reset_all=True))
    st.button("♻️ Reset Data Only", on_click=lambda: st.session_state.update(reset_data=True))

# --- Main Panel ---
resin_ratio = 100
data = []

if all([resin_name, hardener_name, hardener_ratio, tolerance_percent, entry_count]):
    st.success("✅ Setup complete. Enter weights below.")

    for i in range(int(entry_count)):
        with st.expander(f"📦 Entry #{i+1}", expanded=i == 0):
            resin_weight = st.number_input(f"Resin Weight (g) - Entry {i+1}", min_value=0.0, step=0.1, key=f"resin_{i}")
            hardener_weight = st.number_input(f"Hardener Weight (g) - Entry {i+1}", min_value=0.0, step=0.1, key=f"hardener_{i}")

            if resin_weight > 0 and hardener_weight > 0:
                ideal = (resin_weight / resin_ratio) * hardener_ratio
                tol = ideal * (tolerance_percent / 100)
                min_acc = ideal - tol
                max_acc = ideal + tol
                deviation = ((hardener_weight - ideal) / ideal) * 100
                status = "✅" if min_acc <= hardener_weight <= max_acc else "❌"
            else:
                ideal = min_acc = max_acc = deviation = None
                status = ""

            st.markdown(f"**Ideal:** {ideal:.2f} g" if ideal else "-")
            st.markdown(f"**Acceptable Range:** {min_acc:.2f} g – {max_acc:.2f} g" if min_acc else "-")
            st.markdown(f"**Deviation:** {deviation:+.2f}%" if deviation is not None else "-")
            st.markdown(f"**Result:** {status}")

            data.append({
                "Entry #": i + 1,
                f"{resin_name} (g)": resin_weight,
                f"{hardener_name} (g)": hardener_weight,
                "Ideal Hardener (g)": round(ideal, 2) if ideal else None,
                "Min Acceptable (g)": round(min_acc, 2) if min_acc else None,
                "Max Acceptable (g)": round(max_acc, 2) if max_acc else None,
                "% Deviation": round(deviation, 2) if deviation is not None else None,
                "Result": status
            })

    df = pd.DataFrame(data).dropna()

    if not df.empty:
        st.subheader("📈 Deviation Graph")

        fig = px.line(df, x="Entry #", y="% Deviation", markers=True, title="Deviation of Hardener vs Entry #")
        fig.update_traces(line_color="blue", marker=dict(size=10))

        failed = df[df["Result"] == "❌"]
        if not failed.empty:
            fig.add_scatter(x=failed["Entry #"], y=failed["% Deviation"],
                            mode="markers", marker=dict(size=12, color="red", line=dict(color="black", width=2)),
                            name="Failed Points")

        fig.add_hline(y=tolerance_percent, line_dash="dash", line_color="green", annotation_text=f"+{tolerance_percent}%", annotation_position="top right")
        fig.add_hline(y=-tolerance_percent, line_dash="dash", line_color="green", annotation_text=f"-{tolerance_percent}%", annotation_position="bottom right")

        fig.update_yaxes(range=[-10, 10], title="% Deviation")
        fig.update_layout(margin=dict(l=20, r=20, t=40, b=40))

        st.plotly_chart(fig, use_container_width=True)

        # Convert Plotly to image with kaleido
        img_bytes = pio.to_image(fig, format='png', width=800, height=400)
        img_buffer = io.BytesIO(img_bytes)

        # --- Export to Excel ---
        st.subheader("📤 Export to Excel")

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet("Mixing Report")

        # Setup info
        setup_info = [
            ["Resin Name", resin_name],
            ["Hardener Name", hardener_name],
            ["Mixing Ratio", f"{resin_ratio}:{hardener_ratio}"],
            ["Tolerance (%)", f"±{tolerance_percent}%"],
            ["Number of Entries", entry_count]
        ]
        for row, (label, val) in enumerate(setup_info):
            worksheet.write(row, 0, label)
            worksheet.write(row, 1, val)

        # Write data table
        start_row = len(setup_info) + 2
        for col_idx, col_name in enumerate(df.columns):
            worksheet.write(start_row, col_idx, col_name)

        for row_idx, row in enumerate(df.itertuples(index=False), start=start_row + 1):
            for col_idx, val in enumerate(row):
                worksheet.write(row_idx, col_idx, val)

        # Insert plotly image
        worksheet.insert_image(start_row + len(df) + 3, 0, "chart.png", {
            'image_data': img_buffer,
            'x_scale': 0.9,
            'y_scale': 0.9
        })

        workbook.close()
        output.seek(0)

        st.download_button(
            "📥 Download Excel Report",
            data=output,
            file_name="Mixing_Ratio_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.warning("⚠️ Please complete all setup fields in the sidebar to proceed.")
