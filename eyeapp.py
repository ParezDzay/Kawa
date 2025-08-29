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
    "Patient Name",
    "Appointment Date",
    "Time",
    "Payment"
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
                new_headers.append(f"{h}_{seen[h]}")  # rename duplicates
            else:
                seen[h] = 0
                new_headers.append(h)
        # Update header row in the sheet
        sheet.update("1:1", [new_headers])

    return sheet

sheet = get_sheet()

# ---------- Functions ----------
def load_bookings():
    """Load data from Google Sheet (syncs with CSV)."""
    try:
        records = sheet.get_all_records()
        df = pd.DataFrame(records)

        # Ensure required columns exist
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""

        # Save a synced local copy
        df.to_csv(CSV_FILE, index=False)
        return df

    except Exception as e:
        st.error(f"⚠️ Failed to load from Google Sheets, using local CSV. Error: {e}")
        if not os.path.exists(CSV_FILE):
            pd.DataFrame(columns=REQUIRED_COLUMNS).to_csv(CSV_FILE, index=False)
        df = pd.read_csv(CSV_FILE)
        for col in REQUIRED_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        return df


def save_bookings(df):
    """Save DataFrame locally and to Google Sheet."""
    df.to_csv(CSV_FILE, index=False)
    try:
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"❌ Failed to save to Google Sheets: {e}")


def push_to_sheet_append(df):
    """Append new rows to Google Sheet (and sync CSV)."""
    try:
        df_to_push = df.fillna("").astype(str)
        existing_records = sheet.get_all_records()
        existing_df = pd.DataFrame(existing_records)

        if not existing_df.empty:
            new_rows = df_to_push.merge(existing_df, how="outer", indicator=True) \
                                 .query('_merge=="left_only"') \
                                 .drop('_merge', axis=1)
        else:
            new_rows = df_to_push

        if not new_rows.empty:
            sheet.append_rows(new_rows.values.tolist(), value_input_option="RAW")

        # Sync CSV
        updated_records = sheet.get_all_records()
        pd.DataFrame(updated_records).to_csv(CSV_FILE, index=False)

        return True

    except Exception as e:
        st.error(f"❌ Failed to push to Google Sheets: {e}")
        return False


# ---------- Page Setup ----------
st.set_page_config(page_title="Global Eye Center (Appointments)", layout="wide")
st.title("Global Eye Center (Appointments)")

# ---------- Sidebar Form ----------
st.sidebar.header("Add New Appointment")

if "form_inputs" not in st.session_state:
    st.session_state.form_inputs = {"patient_name": "", "appt_date": date.today(),
                                    "appt_time": "", "payment": ""}

patient_name = st.sidebar.text_input("Patient Name", value=st.session_state.form_inputs["patient_name"])
appt_date = st.sidebar.date_input("Appointment Date", value=st.session_state.form_inputs["appt_date"])
appt_time = st.sidebar.text_input("Time", placeholder="HH:MM",
                                  value=st.session_state.form_inputs["appt_time"])
payment = st.sidebar.text_input("Payment", placeholder="e.g., Cash / Card / None",
                                value=st.session_state.form_inputs["payment"])

if st.sidebar.button("💾 Save Appointment"):
    if not patient_name:
        st.sidebar.error("Patient Name is required.")
    elif not appt_time:
        st.sidebar.error("Time is required.")
    else:
        df = load_bookings()
        new_record = {
            "Patient Name": patient_name.strip(),
            "Appointment Date": appt_date.strftime("%Y-%m-%d"),
            "Time": appt_time.strip(),
            "Payment": payment.strip()
        }
        df = pd.concat([df, pd.DataFrame([new_record])], ignore_index=True)

        save_bookings(df)
        push_to_sheet_append(df)

        st.sidebar.success("Appointment saved successfully.")

        # Clear form inputs
        st.session_state.form_inputs = {"patient_name": "", "appt_date": date.today(),
                                        "appt_time": "", "payment": ""}

# ---------- Load Bookings ----------
bookings = load_bookings()

# Convert Appointment Date to datetime
bookings["Appointment Date"] = pd.to_datetime(bookings["Appointment Date"], errors="coerce")
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
                day_df_display = day_df[["Patient Name", "Time", "Payment"]].reset_index(drop=True)
                day_df_display.index = range(1, len(day_df_display)+1)
                st.dataframe(day_df_display, use_container_width=True)

# Archive
with tabs[1]:
    archive = bookings[bookings["Appointment Date"] <= yesterday]
    st.subheader("📂 Appointment Archive")

    if archive.empty:
        st.info("No archived appointments.")
    else:
        archive_disp = archive.sort_values("Appointment Date", ascending=False).reset_index(drop=True)
        archive_disp.index += 1
        st.dataframe(
            archive_disp[["Patient Name", "Appointment Date", "Time", "Payment"]],
            use_container_width=True
        )
