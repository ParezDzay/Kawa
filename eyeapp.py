import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

# ==============================
# CONFIG
# ==============================
CSV_FILE = "eye_data.csv"   # Local backup copy
SHEET_NAME = "eye_data"     # Google Sheet tab name

# Google Sheets authentication
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

# Open worksheet
sheet = client.open_by_url(
    "https://docs.google.com/spreadsheets/d/1keLx7iBH92_uKxj-Z70iTmAVus7X9jxaFXl_SQ-mZvU/edit"
).worksheet(SHEET_NAME)

# ==============================
# HELPER FUNCTIONS
# ==============================
def load_bookings():
    """Load data from Google Sheets first; fallback to CSV if empty"""
    try:
        records = sheet.get_all_records()
        if records:
            return pd.DataFrame(records)
        else:
            return pd.DataFrame(columns=["Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"])
    except Exception as e:
        st.error(f"❌ Failed to load from Google Sheets: {e}")
        # fallback to CSV
        try:
            return pd.read_csv(CSV_FILE)
        except FileNotFoundError:
            return pd.DataFrame(columns=["Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"])

def add_booking_to_sheet(record: dict):
    """Append a single record to Google Sheet"""
    try:
        sheet.append_row(list(record.values()), value_input_option="RAW")
    except Exception as e:
        st.error(f"❌ Failed to save to Google Sheets: {e}")

# ==============================
# STREAMLIT APP
# ==============================
st.set_page_config(page_title="Global Eye Center - Appointments", layout="wide")

st.title("👁️ Global Eye Center - Operation List")

# Load data
df = load_bookings()

# Sidebar booking form
st.sidebar.header("➕ New Booking")

if "form_inputs" not in st.session_state:
    st.session_state.form_inputs = {
        "patient_name": "",
        "appt_date": date.today(),
        "appt_time": "",
        "payment": ""
    }

patient_name = st.sidebar.text_input("Patient Name", st.session_state.form_inputs["patient_name"])
appt_date = st.sidebar.date_input("Appointment Date", st.session_state.form_inputs["appt_date"])
appt_time = st.sidebar.text_input("Appointment Time (manual)", st.session_state.form_inputs["appt_time"])
payment = st.sidebar.text_input("Payment", st.session_state.form_inputs["payment"])

if st.sidebar.button("💾 Save Appointment"):
    if not patient_name:
        st.sidebar.error("Patient Name is required.")
    elif not appt_time:
        st.sidebar.error("Appointment Time is required.")
    else:
        new_record = {
            "Patient Name": patient_name.strip(),
            "Appointment Date": appt_date.strftime("%Y-%m-%d"),
            "Appointment Time (manual)": appt_time.strip(),
            "Payment": payment.strip()
        }

        # Save directly to Google Sheet
        add_booking_to_sheet(new_record)

        # Update local CSV backup
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        df.to_csv(CSV_FILE, index=False)

        st.sidebar.success("✅ Appointment saved successfully.")

        # Clear form
        st.session_state.form_inputs = {
            "patient_name": "",
            "appt_date": date.today(),
            "appt_time": "",
            "payment": ""
        }
        st.rerun()

# Tabs
tab1, tab2 = st.tabs(["📅 Upcoming", "📦 Archived"])

with tab1:
    if not df.empty:
        upcoming = df[df["Appointment Date"] >= str(date.today())]
        st.subheader("Upcoming Appointments")
        st.dataframe(upcoming, use_container_width=True)
    else:
        st.info("No upcoming appointments found.")

with tab2:
    if not df.empty:
        archived = df[df["Appointment Date"] < str(date.today())]
        st.subheader("Archived Appointments")
        st.dataframe(archived, use_container_width=True)
    else:
        st.info("No archived appointments found.")
