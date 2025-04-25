import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mixing Ratio Worksheet", layout="wide")
st.title("🧪 Mixing Ratio Worksheet (Complete with Export & Reset)")

# --- INIT SAFE RESET FLAGS ---
if "trigger_master_reset" not in st.session_state:
    st.session_state.trigger_master_reset = False
if "trigger_data_reset" not in st.session_state:
    st.session_state.trigger_data_reset = False

# --- RERUN-SAFE RESET HANDLING ---
if st.session_state.trigger_data_reset:
    keys_to_keep = {
        "resin_name", "hardener_name", "hardener_ratio",
        "tolerance_percent", "entry_count",
        "trigger_data_reset", "trigger_master_reset"
    }
    keys_to_delete = [k for k in st.session_state.keys() if k not in keys_to_keep]
    for k in keys_to_delete:
        del st.session_state[k]
    st.session_state.trigger_data_reset = False
    st.rerun()

if st.session_state.trigger_master_reset:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# --- SIDEBAR SETUP ---
st.sidebar.header("🔧 Setup Information")

# Reset Buttons
st.sidebar.markdown("### 🔁 Reset Options")
st.sidebar.button("🔄 Master Reset (All)", on_click=lambda: st.session_state.update(trigger_master_reset=True))
st.sidebar.button("♻️ Data Reset Only", on_click=lambda: st.session_state.update(trigger_data_reset=True))

# Fixed resin ratio
resin_ratio = 100

# Setup Inputs
resin_name = st.sidebar.text_input("Enter RESIN name:", key="resin_name")
hardener_name = st.sidebar.text_input("Enter HARDENER name:", key="hardener_name")
hardener_ratio = st.sidebar.number_input("Enter HARDENER ratio (e.g., 30):", min_value=1.0, step=0.1, key="hardener_ratio")
tolerance_percent = st.sidebar.number_input("Enter tolerance (%) (e.g., 3):", min_value=0.1, step=0.1, key="tolerance_percent")
entry_count = st.sidebar.number_input("How many data sets? (up to 30)", min_value=1, max_value=30, step=1, key="entry_count")

# --- MAIN LOGIC ---
if resin_name and hardener_name and hardener_ratio > 0 and tolerance_percent > 0 and entry_count > 0:
    st.success("✅ Setup complete! Enter weights below.")

    st.subheader("📥 Actual Weights and Results Table")

    data = []

    # Header Row
    cols = st.columns([1, 1, 1, 1.5, 1.5, 1.5, 1, 1])
    headers = ["Entry", f"{resin_name} (g)", f"{hardener_name} (g)",
               "Ideal Hardener (g)", "Min Accept (g)", "Max Accept (g)",
               "% Deviation", "Result"]
    for col, header in zip(cols, headers):
        col.markdown(f"**{header}**")

    for i in range(int(entry_count)):
        col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 1.5, 1.5, 1.5, 1, 1])

        entry_number = i + 1
        with col1:
            st.markdown(f"{entry_number}")

        with col2:
            resin_weight = st.number_input(f"Resin_{i}", min_value=0.0, step=0.1, key=f"resin_{i}", label_visibility="collapsed")
        with col3:
            hardener_weight = st.number_input(f"Hardener_{i}", min_value=0.0, step=0.1, key=f"hardener_{i}", label_visibility="collapsed")

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

        with col4:
            st.markdown(f"{ideal:.2f}" if ideal else "-")
        with col5:
            st.markdown(f"{min_acc:.2f}" if min_acc else "-")
        with col6:
            st.markdown(f"{max_acc:.2f}" if max_acc else "-")
        with col7:
            st.markdown(f"{deviation:+.2f}%" if deviation is not None else "-")
        with col8:
            st.markdown(status)

        # Save data for graph and export
        data.append({
            "Entry #": entry_number,
            f"{resin_name} (g)": resin_weight,
            f"{hardener_name} (g)": hardener_weight,
            "Ideal Hardener (g)": round(ideal, 2) if ideal else None,
            "Min Acceptable (g)": round(min_acc, 2) if min_acc else None,
            "Max Acceptable (g)": round(max_acc, 2) if max_acc else None,
            "% Deviation": round(deviation, 2) if deviation is not None else None,
            "Result": status
        })

    # --- DEVIATION GRAPH ---
    df = pd.DataFrame(data)
    df = df.dropna()

    if not df.empty:
        st.subheader("📈 Deviation Graph")

        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot all points
        ax.plot(df["Entry #"], df["% Deviation"], marker='o', linestyle='-', label="Deviation (%)")

        # Highlight failed entries
        failed = df[df["Result"] == "❌"]
        if not failed.empty:
            ax.scatter(failed["Entry #"], failed["% Deviation"], color='red', edgecolors='black',
                       s=100, label="Failed Points", zorder=5)

        # Tolerance bands
        ax.axhline(y=tolerance_percent, color='green', linestyle='--', linewidth=1.5, label=f"+{tolerance_percent}% Tolerance")
        ax.axhline(y=-tolerance_percent, color='green', linestyle='--', linewidth=1.5, label=f"-{tolerance_percent}% Tolerance")

        ax.set_xlabel("Entry #")
        ax.set_ylabel("Deviation (%)")
        ax.set_title("Deviation of Hardener Weight vs Entry")
        ax.grid(True)
        ax.legend()

        st.pyplot(fig)

        # --- EXCEL EXPORT ---
        st.subheader("📤 Export to Excel")

        setup_info = {
            "Resin Name": resin_name,
            "Hardener Name": hardener_name,
            "Hardener Ratio": f"{resin_ratio}:{hardener_ratio}",
            "Tolerance (%)": f"±{tolerance_percent}%",
            "Number of Entries": entry_count
        }
        setup_df = pd.DataFrame(setup_info.items(), columns=["Setup", "Value"])

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            setup_df.to_excel(writer, sheet_name="Setup Info", index=False)
            df.to_excel(writer, sheet_name="Deviation Data", index=False)

        output.seek(0)

        st.download_button(
            label="📥 Download Full Report as Excel",
            data=output,
            file_name="Mixing_Ratio_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.warning("⚠️ Please complete all setup fields in the sidebar to proceed.")
