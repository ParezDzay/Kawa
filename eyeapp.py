import streamlit as st
import pandas as pd
import os
import gspread
from fpdf import FPDF
import tempfile
from google.oauth2.service_account import Credentials
from datetime import date, timedelta 

def generate_patient_pdf(record):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, "Dr Kawa Khalil_ Clinic Patient Record Summary", ln=True, align="C")
    pdf.ln(10)
    for key, value in record.items():
        pdf.cell(0, 8, f"{key}: {value}", ln=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name

# ---------- Google Sheets Setup ----------
SHEET_ID = "1keLx7iBH92_uKxj-Z70iTmAVus7X9jxaFXl_SQ-mZvU"
@st.cache_resource
def get_sheet():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scope
    )
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).sheet1
sheet = get_sheet()

# ---------- Append-only push to Google Sheets ----------
def push_to_sheet_append(df):
    try:
        df = df.fillna("").astype(str)
        existing_records = sheet.get_all_records()
        existing_df = pd.DataFrame(existing_records)
        if not existing_df.empty:
            new_rows = df.merge(existing_df, how="outer", indicator=True).query('_merge=="left_only"').drop('_merge', axis=1)
        else:
            new_rows = df
        if not new_rows.empty:
            sheet.append_rows(new_rows.values.tolist(), value_input_option="RAW")
        return True
    except Exception as e:
        st.error(f"❌ Google Sheets append failed: {e}")
        return False

# ---------- Page config ----------
st.set_page_config(page_title="Clinic Patient Data", layout="wide")
file_path = "eye_data.csv"

# Initialize CSV if missing
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number",
        "Visual_Acuity", "VAcc", "IOP", "Medication", "AC", "Fundus", "U/S",
        "OCT/FFA", "Diagnosis", "Treatment", "Plan",
        "Appt_Name", "Appt_Date", "Appt_Time", "Appt_Payment"
    ]).to_csv(file_path, index=False)

df = pd.read_csv(file_path)

# ====== Safely add new columns if missing ======
for col in ["VAcc", "Appt_Name", "Appt_Date", "Appt_Time", "Appt_Payment"]:
    if col not in df.columns:
        df[col] = ""

# Session state
if "selected_waiting_id" not in st.session_state:
    st.session_state.selected_waiting_id = None


# ---------- Streamlit Page Setup ----------
st.set_page_config(page_title="Global Eye Center (Appointments)", layout="wide")
st.title("Global Eye Center (Appointments)")

# ---------- Main Tabs ----------
tabs = st.tabs(["📌 Upcoming Appointments", "📂 Appointment Archive"])

# ---------- Sidebar Form ----------
st.sidebar.header("Add New Appointment")
patient_name = st.sidebar.text_input("Patient Name")
appt_date = st.sidebar.date_input("Appointment Date", value=date.today())
appt_time = st.sidebar.text_input("Appointment Time (manual)", placeholder="HH:MM")
payment = st.sidebar.text_input("Payment", placeholder="e.g., Cash / Card / None")

if st.sidebar.button("💾 Save Appointment"):
    if not patient_name:
        st.sidebar.error("Patient Name is required.")
    elif not appt_time:
        st.sidebar.error("Appointment Time is required.")
    else:
        df = load_bookings()
        new_record = {
            "Patient Name": patient_name.strip(),
            "Appointment Date": appt_date.strftime("%Y-%m-%d"),
            "Appointment Time (manual)": appt_time.strip(),
            "Payment": payment.strip()
        }
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
        save_bookings(df)
        st.sidebar.success("Appointment saved successfully.")
        safe_rerun()

# ---------- Load Bookings ----------
bookings = load_bookings()
bookings["Appointment Date"] = pd.to_datetime(bookings["Appointment Date"], errors="coerce")
yesterday = pd.Timestamp(date.today() - timedelta(days=1))

# ---------- Upcoming Tab ----------
with tabs[0]:
    upcoming = bookings[bookings["Appointment Date"] > yesterday]
    st.subheader("📌 Upcoming Appointments")
    if upcoming.empty:
        st.info("No upcoming appointments.")
    else:
        upcoming_disp = upcoming.sort_values("Appointment Date")
        for d in upcoming_disp["Appointment Date"].dt.date.unique():
            day_df = upcoming_disp[upcoming_disp["Appointment Date"].dt.date == d]
            with st.expander(d.strftime("📅 %A, %d %B %Y")):
                day_df_display = day_df[["Patient Name", "Appointment Time (manual)", "Payment"]].reset_index(drop=True)
                day_df_display.index = range(1, len(day_df_display)+1)
                st.dataframe(day_df_display, use_container_width=True)

# ---------- Archive Tab ----------
with tabs[1]:
    archive = bookings[bookings["Appointment Date"] <= yesterday]
    st.subheader("📂 Appointment Archive")
    if archive.empty:
        st.info("No archived appointments.")
    else:
        archive_disp = archive.sort_values("Appointment Date", ascending=False).reset_index(drop=True)
        archive_disp.index += 1
        st.dataframe(archive_disp[["Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"]],
                     use_container_width=True)
