import streamlit as st
import pandas as pd
from PIL import Image
from pathlib import Path
import requests
from io import BytesIO
import time

# ========== CONFIG ==========
st.set_page_config(page_title="Image Review App", layout="centered")
EXCEL_PATH = "failed28.xlsx"  # Input Excel file
OUTPUT_PATH = "updated_results.xlsx"  # Shared output file


# Hide the footer and Streamlit branding
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .css-164nlkn {display: none}  /* For some Streamlit versions */
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# ========== USER INFO ==========
if "user_name" not in st.session_state:
    st.session_state.user_name = ""

st.session_state.user_name = st.text_input("Enter Your Name:", value=st.session_state.user_name)

if not st.session_state.user_name.strip():
    st.warning("Please enter your name to proceed.")
    st.stop()

user_name = st.session_state.user_name.strip()

# ========== SAVE FUNCTION ==========
def save_with_retry(df, filepath, retries=5, delay=1):
    for _ in range(retries):
        try:
            df.to_excel(filepath, index=False)
            return True
        except PermissionError:
            time.sleep(delay)
    return False

# ========== LOAD DATA ==========
@st.cache_data(show_spinner=False)
def load_excel():
    if not Path(EXCEL_PATH).exists():
        return None
    df = pd.read_excel(EXCEL_PATH)
    if "Actual reading" not in df.columns:
        df["Actual reading"] = ""
    if "Actual Unit" not in df.columns:
        df["Actual Unit"] = ""
    if "Reviewed by" not in df.columns:
        df["Reviewed by"] = ""
    return df

# Always load the latest data
df_all = load_excel()
if df_all is None:
    st.error(f"Input file '{EXCEL_PATH}' not found.")
    st.stop()

# Load progress if file exists
if Path(OUTPUT_PATH).exists():
    df_saved = pd.read_excel(OUTPUT_PATH)
    if "actual_image_path" in df_all.columns and "actual_image_path" in df_saved.columns:
        df_all.set_index("actual_image_path", inplace=True)
        df_saved.set_index("actual_image_path", inplace=True)

        for col in ["Actual reading", "Actual Unit", "Reviewed by"]:
            if col in df_saved.columns:
                df_all[col].update(df_saved[col])

        df_all.reset_index(inplace=True)

# ========== TRACK INDEX ==========
if "index" not in st.session_state:
    st.session_state.index = 0

# Filter unreviewed rows
df_filtered = df_all[df_all["Reviewed by"].isna() | (df_all["Reviewed by"].astype(str).str.strip() == "")].reset_index(drop=True)

# ========== UI ==========
st.title(f"Image Annotation Interface - Reviewer: {user_name}")

# Progress Info
st.info(f"Total: {len(df_all)} | Reviewed: {df_all[df_all['Reviewed by'].notna() & (df_all['Reviewed by'].astype(str).str.strip() != '')].shape[0]} | Pending: {len(df_filtered)}")

# ========== ALWAYS VISIBLE DOWNLOAD BUTTON FOR ALLOWED USERS ==========
allowed_users = ["rahul pushp", "kumar abhinav"]
if user_name.strip().lower() in allowed_users and Path(OUTPUT_PATH).exists():
    try:
        with open(OUTPUT_PATH, "rb") as f:
            excel_data = f.read()
        st.download_button(
            label="Download Final Excel File",
            data=excel_data,
            file_name="final_review_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        st.error(f"Could not prepare download: {e}")

# ========== MAIN REVIEW INTERFACE ==========
if len(df_filtered) == 0:
    st.success("All images have already been reviewed.")

    if st.button("Save Final File"):
        if save_with_retry(df_all, OUTPUT_PATH):
            st.success(f"Final file saved as: `{OUTPUT_PATH}`")
        else:
            st.warning("Unable to save. Please ensure the file is not open elsewhere.")

else:
    i = st.session_state.index
    if i < len(df_filtered):
        row = df_filtered.iloc[i]
        real_index = df_all[df_all["actual_image_path"] == row["actual_image_path"]].index[0]

        st.markdown(f"### Image {i+1} of {len(df_filtered)}")

        # ========== IMAGE DISPLAY ==========
        image_path = row["actual_image_path"]
        try:
            if image_path.startswith("http://") or image_path.startswith("https://"):
                response = requests.get(image_path)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
            else:
                img = Image.open(image_path)

            img = img.resize((400, 300))
            st.image(img, caption=row.get("Filename", "Image"))
        except Exception as e:
            st.error(f"Failed to load image: {e}")

        # ========== Predicted vs Actual ==========
        col_r1, col_r2 = st.columns([1, 1])
        with col_r1:
            st.markdown(f"**Predicted Reading:** `{row.get('pred_readings', '')}`")
        with col_r2:
            actual_reading = st.text_input("Actual Reading:", value=row.get("Actual reading", ""))

        col_u1, col_u2 = st.columns([1, 1])
        with col_u1:
            st.markdown(f"**Predicted Unit:** `{row.get('pred_units', '')}`")
        with col_u2:
            actual_unit = st.text_input("Actual Unit:", value=row.get("Actual Unit", ""))

        # ========== ACTION BUTTON ==========
        if st.button("Save & Next"):
            df_all.at[real_index, "Actual reading"] = actual_reading
            df_all.at[real_index, "Actual Unit"] = actual_unit
            df_all.at[real_index, "Reviewed by"] = user_name

            if save_with_retry(df_all, OUTPUT_PATH):
                st.session_state.index += 1
                st.rerun()
            else:
                st.warning("Could not save to Excel. Please close the file and try again.")
    else:
        st.success("You have reviewed all available images.")
