import streamlit as st
import pandas as pd
import os
import gspread
from fpdf import FPDF
import tempfile

def generate_patient_pdf(record):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(0, 10, "Dr Kawa Khalil _Clinic Patient Record Summary", ln=True, align="C")
    pdf.ln(10)
    
    for key, value in record.items():
        pdf.cell(0, 8, f"{key}: {value}", ln=True)
    pdf.ln(20)
    
    # Footer text (multiline)
    footer_lines = [
        "دكتور كاوه خليل _ ڕاوێژکاری نەشتەرگەری تۆڕی چاو",
        "استشاري جراحة العيون والشبكية _ دكتورا (بورد) الماني",
        "ناونيشان/سەنتەرى گڵوباڵ _ العنوان / مركز كلوبال",
        "07507712332 - 07715882299"
    ]
    pdf.set_font("Arial", size=10)
    for line in footer_lines:
        pdf.cell(0, 7, line, ln=True, align="C")
    
    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(temp_file.name)
    return temp_file.name
from google.oauth2.service_account import Credentials

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

# Push to Google Sheet
def push_to_sheet(df):
    try:
        df = df.fillna("").astype(str)  # sanitize
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
        return True
    except Exception as e:
        st.error(f"❌ Google Sheets push failed: {e}")
        return False

# Page config
st.set_page_config(page_title="Clinic Patient Data", layout="wide")
file_path = "eye_data.csv"

# Initialize CSV if missing
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number",
        "Visual_Acuity", "IOP", "Medication", "AC", "Fundus", "U/S",
        "OCT/FFA", "Diagnosis", "Treatment", "Plan"
    ]).to_csv(file_path, index=False)

df = pd.read_csv(file_path)

# Session state
if "selected_waiting_id" not in st.session_state:
    st.session_state.selected_waiting_id = None

# Sidebar
menu = st.sidebar.radio("📁 Menu", ["🌟 New Patient", "📊 View Data"], index=0)

if menu == "🌟 New Patient":
    tabs = st.tabs(["📋 Pre-Visit Entry", "⏳ Waiting List / Doctor update"])

    # --- Pre-Visit Entry ---
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
                va = st.text_input("VA: RA / LA")
                bcva_ra = st.text_input("BCVA: RA")
                bcva_la = st.text_input("BCVA: LA")
                iop = st.text_input("IOP: RA / LA")
                medication = st.text_input("Medication")

            if st.form_submit_button("Submit"):
                visual_acuity = f"RA ({bcva_ra}) ; LA ({bcva_la})"
                new_entry = pd.DataFrame([{
                    "Date": str(date),
                    "Patient_ID": next_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Visual_Acuity": visual_acuity,
                    "IOP": iop,
                    "Medication": medication,
                    "AC": "",
                    "Fundus": "",
                    "U/S": "",
                    "OCT/FFA": "",
                    "Diagnosis": "",
                    "Treatment": "",
                    "Plan": ""
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                try:
                    df.to_csv(file_path, index=False)
                    st.success("✅ Data saved locally.")
                    df = df.fillna("").astype(str)
                    if push_to_sheet(df):
                        st.success("✅ Data saved to Google Sheets.")
                    else:
                        st.warning("⚠️ Google Sheets save failed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")

    # --- Waiting List ---
    with tabs[1]:
        st.title("⏳ Patients Waiting for Doctor Update")
        df = df.fillna("")
        waiting_df = df[(df["Diagnosis"] == "") & (df["Treatment"] == "") & (df["Plan"] == "")]

        if waiting_df.empty:
            st.success("🎉 No patients are currently waiting.")
        else:
            updated_ids = []
            for _, row in waiting_df.iterrows():
                with st.expander(f"🪪 {row['Patient_ID']} — {row['Full_Name']}, Age {row['Age']}"):
                    selected = df[df["Patient_ID"] == row["Patient_ID"]]
                    with st.form(f"form_{row['Patient_ID']}", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            ac = st.text_area("AC", height=100)
                            fundus = st.text_area("Fundus", height=100)
                            us = st.text_input("U/S")
                            oct_ffa = st.text_input("OCT/FFA")
                        with col2:
                            diagnosis = st.text_input("Diagnosis", value=selected["Diagnosis"].values[0])
                            treatment = st.text_input("Treatment")
                            plan = st.text_input("Plan")
                        submitted = st.form_submit_button("Update Record")

                    if submitted:
                        idx = df[df["Patient_ID"] == row["Patient_ID"]].index[0]
                        df.loc[idx, ["AC", "Fundus", "U/S", "OCT/FFA", "Diagnosis", "Treatment", "Plan"]] = [
                            ac.strip(), fundus.strip(), us.strip(), oct_ffa.strip(), diagnosis.strip(), treatment.strip(), plan.strip()
                        ]
                        try:
                            df.to_csv(file_path, index=False)
                            st.success("✅ Updated locally.")
                            df = df.fillna("").astype(str)
                            if push_to_sheet(df):
                                st.success("✅ Updated Google Sheets.")
                            else:
                                st.warning("⚠️ Google Sheets update failed.")
                            patient_record = df.loc[idx].to_dict()
                            pdf_path = generate_patient_pdf(patient_record)
                            with open(pdf_path, "rb") as f:
                                pdf_bytes = f.read()
                                st.download_button(
                                    label=f"🖨️ Download PDF Summary for Patient {row['Patient_ID']}",
                                    data=pdf_bytes,
                                    file_name=f"Patient_{row['Patient_ID']}_summary.pdf",
                                    mime="application/pdf",
                                )
                        except Exception as e:
                            st.error(f"❌ Update failed: {e}")

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
