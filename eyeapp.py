import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- Google Sheets setup ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)

SPREADSHEET_NAME = "eye_data"   # Your Google Sheet
WORKSHEET_NAME = "Sheet1"       # The tab inside the Google Sheet
CSV_FILE = "eye_data.csv"       # Local backup

def get_sheet():
    return client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)

# --- Load bookings directly from Google Sheets ---
def load_bookings():
    try:
        sheet = get_sheet()
        data = sheet.get_all_records()
        df = pd.DataFrame(data)
        if not df.empty:
            df.to_csv(CSV_FILE, index=False)  # overwrite local CSV cache
        return df
    except Exception as e:
        st.error(f"❌ Failed to load from Google Sheets: {e}")
        # fallback to local CSV
        try:
            return pd.read_csv(CSV_FILE)
        except:
            return pd.DataFrame()

# --- Save bookings to Google Sheets ---
def save_bookings(df):
    try:
        sheet = get_sheet()
        sheet.clear()  # wipe everything
        sheet.update([df.columns.values.tolist()] + df.values.tolist())  # push fresh
        df.to_csv(CSV_FILE, index=False)  # keep local in sync
        return True
    except Exception as e:
        st.error(f"❌ Failed to push to Google Sheets: {e}")
        return False

# --- Append a single new booking row ---
def push_to_sheet_append(new_row: dict):
    try:
        sheet = get_sheet()
        sheet.append_row(list(new_row.values()))
        # reload full sheet so CSV stays in sync
        df = load_bookings()
        return df
    except Exception as e:
        st.error(f"❌ Failed to append to Google Sheets: {e}")
        return None


# --- Streamlit UI ---
st.set_page_config(page_title="Global Eye Center", layout="wide")

st.title("👁 Global Eye Center - Operation List")

# Load existing bookings
df = load_bookings()

tab1, tab2 = st.tabs(["📅 Upcoming Operations", "📂 Archived Operations"])

with tab1:
    st.subheader("Add New Appointment")
    with st.form("booking_form", clear_on_submit=True):
        name = st.text_input("Patient Name")
        doctor = st.text_input("Doctor Name")
        room = st.selectbox("Room", ["Room 1", "Room 2", "Room 3"])
        date = st.date_input("Date")
        time = st.time_input("Time")
        submit = st.form_submit_button("Save Appointment")

        if submit:
            new_row = {
                "Patient": name,
                "Doctor": doctor,
                "Room": room,
                "Date": date.strftime("%Y-%m-%d"),
                "Time": time.strftime("%H:%M"),
                "Created": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            df = push_to_sheet_append(new_row)
            if df is not None:
                st.success("✅ Appointment saved successfully!")

    if not df.empty:
        st.dataframe(df)

with tab2:
    st.subheader("Archived Operations (Past Dates)")
    if not df.empty:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        archived = df[df["Date"] < pd.to_datetime(datetime.today().date())]
        if not archived.empty:
            st.dataframe(archived)
        else:
            st.info("No archived operations yet.")
    else:
        st.info("No data available.")
