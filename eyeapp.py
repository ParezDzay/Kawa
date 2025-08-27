import streamlit as st
import pandas as pd
from datetime import date, timedelta
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
import tempfile

# ---------- PDF Generator ----------
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
COLUMNS = ["Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"]

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

# ---------- Load & Save Functions ----------
def load_bookings():
    """Load all bookings from Google Sheets into a DataFrame"""
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        # Auto-rename old headers if needed
        rename_map = {
            "Appt_Name": "Patient Name",
            "Appt_Date": "Appointment Date",
            "Appt_Time": "Appointment Time (manual)",
            "Appt_Payment": "Payment"
        }
        df.rename(columns=rename_map, inplace=True)

        # Ensure all columns exist
        for col in COLUMNS:
            if col not in df.columns:
                df[col] = ""

        return df[COLUMNS]
    except Exception as e:
        st.error(f"❌ Failed to load from Google Sheets: {e}")
        return pd.DataFrame(columns=COLUMNS)

def push_to_sheet_append(new_row):
    """Append a single row to Google Sheets"""
    try:
        row_df = pd.DataFrame([new_row], columns=COLUMNS)
        sheet.append_rows(row_df.values.tolist(), value_input_option="RAW")
        return True
    except Exception as e:
        st.error(f"❌ Failed to append to Google Sheets: {e}")
        return False

# ---------- Streamlit Page ----------
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
        new_record = {
            "Patient Name": patient_name.strip(),
            "Appointment Date": appt_date.strftime("%Y-%m-%d"),
            "Appointment Time (manual)": appt_time.strip(),
            "Payment": payment.strip()
        }
        success = push_to_sheet_append(new_record)
        if success:
            st.sidebar.success("✅ Appointment saved to Google Sheet.")
            st.experimental_rerun()

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
        st.dataframe(
            archive_disp[["Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"]],
            use_container_width=True
        )
