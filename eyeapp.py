import streamlit as st
import pandas as pd
import os
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

# ---------- Constants ----------
CSV_FILE = "eye_data.csv"
SHEET_ID = "1keLx7iBH92_uKxj-Z70iTmAVus7X9jxaFXl_SQ-mZvU"
REQUIRED_COLUMNS = [
    "Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"
]

# ---------- Google Sheets Setup ----------
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
    sheet = client.open_by_key(SHEET_ID).sheet1

    # --- Check for duplicate headers ---
    headers = sheet.row_values(1)
    if len(headers) != len(set(headers)):
        st.warning("Duplicate headers detected in Google Sheet, fixing automatically.")
        new_headers = []
        seen = {}
        for h in headers:
            if h in seen:
                seen[h] += 1
                new_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                new_headers.append(h)
        sheet.update("1:1", [new_headers])
    return sheet

sheet = get_sheet()

# ---------- Functions ----------
def load_bookings():
    """Load from Google Sheet directly (sync with local CSV)."""
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
    except Exception as e:
        st.error(f"❌ Could not load from Google Sheets: {e}")
        # fallback to CSV
        if not os.path.exists(CSV_FILE):
            pd.DataFrame(columns=REQUIRED_COLUMNS).to_csv(CSV_FILE, index=False)
        df = pd.read_csv(CSV_FILE)

    # Ensure required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = ""
    return df


def save_booking_to_sheet(new_record):
    """Save only the new booking to Google Sheet and CSV."""
    try:
        sheet.append_row(
            [
                new_record["Patient Name"],
                new_record["Appointment Date"],
                new_record["Appointment Time (manual)"],
                new_record["Payment"],
            ],
            value_input_option="RAW",
        )
    except Exception as e:
        st.error(f"❌ Failed to save to Google Sheets: {e}")

    # Save locally also
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
    else:
        df = pd.DataFrame(columns=REQUIRED_COLUMNS)
    df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)


# ---------- Page Setup ----------
st.set_page_config(page_title="Global Eye Center (Appointments)", layout="wide")
st.title("Global Eye Center (Appointments)")

# ---------- Sidebar Form ----------
st.sidebar.header("Add New Appointment")

if "form_inputs" not in st.session_state:
    st.session_state.form_inputs = {
        "patient_name": "",
        "appt_date": date.today(),
        "appt_time": "",
        "payment": ""
    }

patient_name = st.sidebar.text_input(
    "Patient Name", value=st.session_state.form_inputs["patient_name"]
)
appt_date = st.sidebar.date_input(
    "Appointment Date", value=st.session_state.form_inputs["appt_date"]
)
appt_time = st.sidebar.text_input(
    "Appointment Time (manual)",
    placeholder="HH:MM",
    value=st.session_state.form_inputs["appt_time"],
)
payment = st.sidebar.text_input(
    "Payment",
    placeholder="e.g., Cash / Card / None",
    value=st.session_state.form_inputs["payment"],
)

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
        save_booking_to_sheet(new_record)
        st.sidebar.success("Appointment saved successfully.")

        # Clear form
        st.session_state.form_inputs = {
            "patient_name": "",
            "appt_date": date.today(),
            "appt_time": "",
            "payment": ""
        }

# ---------- Load Bookings ----------
bookings = load_bookings()

# Convert Appointment Date
bookings["Appointment Date"] = pd.to_datetime(
    bookings["Appointment Date"], errors="coerce"
)

yesterday = pd.Timestamp(date.today() - timedelta(days=1))

# ---------- Main Tabs ----------
tabs = st.tabs(["📌 Upcoming Appointments", "📂 Appointment Archive"])

# Upcoming
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
                day_df_display = day_df[
                    ["Patient Name", "Appointment Time (manual)", "Payment"]
                ].reset_index(drop=True)
                day_df_display.index = range(1, len(day_df_display) + 1)
                st.dataframe(day_df_display, use_container_width=True)

# Archive
with tabs[1]:
    archive = bookings[bookings["Appointment Date"] <= yesterday]
    st.subheader("📂 Appointment Archive")

    if archive.empty:
        st.info("No archived appointments.")
    else:
        archive_disp = archive.sort_values(
            "Appointment Date", ascending=False
        ).reset_index(drop=True)
        archive_disp.index += 1
        st.dataframe(
            archive_disp[
                ["Patient Name", "Appointment Date", "Appointment Time (manual)", "Payment"]
