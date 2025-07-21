import streamlit as st
import pandas as pd
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ---------- Password Protection ----------
PASSWORD = "1977"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    pwd = st.text_input("Enter password", type="password")
    login_button = st.button("Login")
    if login_button:
        if pwd == PASSWORD:
            st.session_state.authenticated = True
        else:
            st.error("Incorrect password")
    st.stop()

# ---------- Google Sheets Setup ----------
SHEET_ID = "YOUR_SHEET_ID"  # <-- put your actual Sheet ID here!

@st.cache_resource
def get_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        st.secrets["gcp_service_account"], scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1

sheet = get_sheet()

# Push to Google Sheet
def push_to_sheet(df):
    try:
        sheet.clear()  # Clear old data
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ Google Sheets push failed: {e}")
        return False

# ---------- Page config ----------
st.set_page_config(page_title="Clinic Patient Data", layout="wide")
file_path = "eye_data.csv"

# Initialize CSV if missing
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number",
        "Diagnosis", "Visual_Acuity", "IOP", "Medication"
    ]).to_csv(file_path, index=False)

df = pd.read_csv(file_path)

# Sidebar state
if "selected_waiting_id" not in st.session_state:
    st.session_state.selected_waiting_id = None
if "print_ready" not in st.session_state:
    st.session_state.print_ready = False

# Sidebar Menu
menu = st.sidebar.radio("📁 Menu", ["🌟 New Patient", "📊 View Data"], index=0)

if menu == "🌟 New Patient":
    tabs = st.tabs(["📋 Pre-Visit Entry", "⏳ Waiting List / Doctor update"])

    with tabs[0]:
        st.title("📋 Pre-Visit Entry")
        try:
            last_id = df["Patient_ID"].dropna().astype(str).str.extract('(\\d+)')[0].astype(int).max()
            next_id = f"{last_id + 1:04d}"
        except:
            next_id = "0001"
        st.markdown(f"**Generated Patient ID:** `{next_id}`")

        with st.form("pre_visit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                full_name = st.text_input("Full Name")
                age = st.number_input("Age", min_value=0, max_value=120)
                gender = st.selectbox("Gender", ["Male", "Female", "Child"])
                phone = st.text_input("Phone Number")
            with col2:
                va = st.text_input("Visual Acuity")
                iop = st.text_input("IOP")
                medication = st.text_input("Medication")

            if st.form_submit_button("Submit"):
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": next_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Diagnosis": "",
                    "Visual_Acuity": va,
                    "IOP": iop,
                    "Medication": medication
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                try:
                    df.to_csv(file_path, index=False)
                    st.success("✅ Data saved locally.")
                    if push_to_sheet(df):
                        st.success("✅ Data pushed to Google Sheet.")
                    else:
                        st.warning("⚠️ Google Sheet push failed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")

    with tabs[1]:
        st.title("⏳ Patients Waiting for Doctor Update")
        # (keep your waiting list logic unchanged, just replace the push_to_github with push_to_sheet)
        # Same idea: call push_to_sheet(df) after saving

# --- View Data ---
elif menu == "📊 View Data":
    st.title("📊 Patient Records")
    tab1, tab2 = st.tabs(["📋 All Records", "🗕️ Download CSV"])
    with tab1:
        st.dataframe(df, use_container_width=True)
    with tab2:
        st.download_button(
            label="⬇️ Download All Records",
            data=df.to_csv(index=False),
            file_name="all_eye_patients.csv",
            mime="text/csv"
        )
