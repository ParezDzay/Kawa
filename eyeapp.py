import gspread
from google.oauth2.service_account import Credentials

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key("1keLx7iBH92_uKxj-Z70iTmAVus7X9jxaFXl_SQ-mZvU").sheet1

# Try appending a test row
sheet.append_row(["Test Name", "2025-08-28", "10:30", "Cash"])
print("Row added successfully!")
