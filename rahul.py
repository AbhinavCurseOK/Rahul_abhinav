import streamlit as st
import pandas as pd
from pathlib import Path
import time

# ========== CONFIG ==========
st.set_page_config(page_title="Image Review App", layout="centered")
EXCEL_PATH = "failed28.xlsx"  # Input Excel file
OUTPUT_PATH = "updated_results.xlsx"  # Shared output file

# ========== USER INFO ==========
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

st.session_state.user_name = st.text_input("👤 Enter Your Name:", value=st.session_state.user_name)

if not st.session_state.user_name.strip():
    st.warning("Please enter your name to proceed.")
    st.stop()

user_name = st.session_state.user_name.strip()
user_output_path = f"updated_results_{user_name.lower()}.xlsx"  # Optional: user-specific file

# ========== LOAD DATA ==========
if "df" not in st.session_state:
    if not Path(EXCEL_PATH).exists():
        st.error(f"Input file '{EXCEL_PATH}' not found.")
        st.stop()

    df = pd.read_excel(EXCEL_PATH)
    if "Actual reading" not in df.columns:
        df["Actual reading"] = ""
    if "Actual Unit" not in df.columns:
        df["Actual Unit"] = ""
    if "Reviewed by" not in df.columns:
        df["Reviewed by"] = ""
    st.session_state.df = df

# ========== FILTER DATA ==========
df_all = st.session_state.df
df_filtered = df_all[df_all["Reviewed by"] == ""].reset_index(drop=True)

# ========== TRACK INDEX ==========
if "index" not in st.session_state:
    st.session_state.index = 0
i = st.session_state.index

# ========== SAVE FUNCTION ==========
def save_with_retry(df, filepath, retries=5, delay=1):
    for _ in range(retries):
        try:
            df.to_excel(filepath, index=False)
            return True
        except PermissionError:
            time.sleep(delay)
    return False

# ========== UI ==========
st.title(f"Image Annotation Interface - Reviewer: {user_name}")

if len(df_filtered) == 0:
    st.success("All images have already been reviewed by someone.")
else:
    if i < len(df_filtered):
        row = df_filtered.iloc[i]
        real_index = df_all[df_all["actual_image_path"] == row["actual_image_path"]].index[0]

        st.markdown(f"### Image {i+1} of {len(df_filtered)}")
        st.image(row["actual_image_path"], caption=row.get("Filename", "Image"), use_container_width=True)

        st.markdown(f"**Predicted Reading:** `{row.get('pred_readings', '')}`")
        st.markdown(f"**Predicted Unit:** `{row.get('pred_units', '')}`")

        actual_reading = st.text_input("Actual Reading:", value=row.get("Actual reading", ""))
        actual_unit = st.text_input("Actual Unit:", value=row.get("Actual Unit", ""))

        col1, col2 = st.columns([1, 1])

        # ========== SAVE & NEXT ==========
        with col1:
            if st.button("Save & Next"):
                st.session_state.df.at[real_index, "Actual reading"] = actual_reading
                st.session_state.df.at[real_index, "Actual Unit"] = actual_unit
                st.session_state.df.at[real_index, "Reviewed by"] = user_name
                st.session_state.index += 1
                st.rerun()

        # ========== SAVE ALL ==========
        with col2:
            if st.button("Save All to Excel"):
                if save_with_retry(st.session_state.df, OUTPUT_PATH):
                    st.success(f"Saved to {OUTPUT_PATH}")
                else:
                    st.warning("File is open or locked. Please close it and try again.")
    else:
        st.success("You have reviewed all available images.")
        if st.button("Save Final File"):
            if save_with_retry(st.session_state.df, OUTPUT_PATH):
                st.success(f"Final file saved as: {OUTPUT_PATH}")
            else:
                st.warning("Unable to save. Please ensure the file is not open elsewhere.")
