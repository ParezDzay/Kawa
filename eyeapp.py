import streamlit as st
import pandas as pd
import os
import gspread
from fpdf import FPDF
import tempfile
from google.oauth2.service_account import Credentials

# ----------------- PDF Generation -----------------
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

# ----------------- Google Sheets Setup -----------------
SHEET_ID = "1keLx7iBH92_uKxj-Z70iTmAVus7X9jxaFXl_SQ-mZvU"

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

# ----------------- Push to Google Sheet -----------------
def push_to_sheet_append(df):
    """Sync all past and new appointments to Google Sheet (4 columns only)."""
    try:
        sheet = get_sheet()
        headers = ["Appt_Name","Appt_Date","Appt_Time","Appt_Payment"]
        appt_df = df[headers].dropna(how="all")

        # Clear sheet and write headers
        sheet.clear()
        sheet.append_row(headers)

        # Append all rows one by one
        for _, row in appt_df.iterrows():
            sheet.append_row(row.tolist())

        st.success("✅ All appointments synced to Google Sheet.")

    except Exception as e:
        st.error(f"❌ Failed to sync Google Sheet: {e}")

sheet = get_sheet()

# ----------------- Page Config -----------------
st.set_page_config(page_title="Clinic Patient Data", layout="wide")
file_path = "eye_data.csv"

# ----------------- Load Local CSV -----------------
if os.path.exists(file_path):
    df = pd.read_csv(file_path)
else:
    df = pd.DataFrame(columns=[
        "Date","Patient_ID","Full_Name","Age","Gender","Phone_Number",
        "Visual_Acuity","VAcc","IOP","Medication","AC","Fundus","U/S",
        "OCT/FFA","Diagnosis","Treatment","Plan",
        "Appt_Name","Appt_Date","Appt_Time","Appt_Payment"
    ])

# Ensure all required columns exist
for col in ["VAcc","Appt_Name","Appt_Date","Appt_Time","Appt_Payment"]:
    if col not in df.columns:
        df[col] = ""

# Session state
if "selected_waiting_id" not in st.session_state:
    st.session_state.selected_waiting_id = None

# ----------------- Sidebar Menu -----------------
menu = st.sidebar.radio("📁 Menu", ["📅 Appointments", "🌟 New Patient", "📊 View Data"], index=0)

# ----------------- APPOINTMENTS -----------------
if menu == "📅 Appointments":
    st.title("📅 Appointment Records")
    
    with st.form("appt_form", clear_on_submit=True):
        appt_name = st.text_input("Patient Name")
        appt_date = st.date_input("Appointment Date")
        appt_time = st.text_input("Appointment Time (manual)")
        appt_payment = st.text_input("Payment")
        if st.form_submit_button("Save Appointment"):
            new_appt = pd.DataFrame([{
                "Date": "", "Patient_ID": "", "Full_Name": "", "Age": "", "Gender": "", "Phone_Number": "",
                "Visual_Acuity": "", "VAcc": "", "IOP": "", "Medication": "", "AC": "", "Fundus": "", "U/S": "", "OCT/FFA": "",
                "Diagnosis": "", "Treatment": "", "Plan": "",
                "Appt_Name": appt_name, "Appt_Date": str(appt_date), "Appt_Time": appt_time, "Appt_Payment": appt_payment
            }])
            df = pd.concat([df, new_appt], ignore_index=True)
            try:
                df.to_csv(file_path, index=False)
                st.success("✅ Appointment saved locally.")
                push_to_sheet_append(df)  # Sync all appointments
            except Exception as e:
                st.error(f"❌ Save failed: {e}")

    st.subheader("📋 All Appointments")
    appt_df = df[["Appt_Name","Appt_Date","Appt_Time","Appt_Payment"]].dropna(how="all")
    if not appt_df.empty:
        appt_df_display = appt_df.iloc[::-1].reset_index(drop=True)
        appt_df_display.index = appt_df_display.index + 1
        st.dataframe(appt_df_display, use_container_width=True)
    else:
        st.info("No appointments recorded yet.")

# ----------------- NEW PATIENT -----------------
elif menu == "🌟 New Patient":
    tabs = st.tabs(["📋 Pre-Visit Entry","⏳ Waiting List / Doctor update"])

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
            col1,col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                full_name = st.text_input("Full Name")
                age = st.number_input("Age", min_value=0, max_value=120)
                gender = st.selectbox("Gender", ["Male","Female","Child"])
                phone = st.text_input("Phone Number")
            with col2:
                va = st.text_input("VA: RA / LA")
                vacc = st.text_input("VAcc: RA / LA")
                bcva_ra = st.text_input("BCVA: RA")
                bcva_la = st.text_input("BCVA: LA")
                iop = st.text_input("IOP: RA / LA")
                medication = st.text_input("Medication")

            if st.form_submit_button("Submit"):
                visual_acuity = f"RA ({bcva_ra}) ; LA ({bcva_la})"
                new_entry = pd.DataFrame([{
                    "Date": str(date), "Patient_ID": next_id, "Full_Name": full_name, "Age": age,
                    "Gender": gender, "Phone_Number": phone,
                    "Visual_Acuity": visual_acuity, "VAcc": vacc,
                    "IOP": iop, "Medication": medication,
                    "AC": "", "Fundus": "", "U/S": "", "OCT/FFA": "",
                    "Diagnosis": "", "Treatment": "", "Plan": "",
                    "Appt_Name": "", "Appt_Date": "", "Appt_Time": "", "Appt_Payment": ""
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                try:
                    df.to_csv(file_path, index=False)
                    st.success("✅ Data saved locally.")
                    # No experimental_rerun, form clears automatically
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")

    # --- Waiting List ---
    with tabs[1]:
        st.title("⏳ Patients Waiting for Doctor Update")
        df = df.fillna("")
        waiting_df = df[
            (df["Diagnosis"] == "") &
            (df["Treatment"] == "") &
            (df["Plan"] == "") &
            (df["Appt_Name"] == "")
        ]
        if waiting_df.empty:
            st.success("🎉 No patients are currently waiting.")
        else:
            for idx,row in waiting_df.iterrows():
                with st.expander(f"🪪 {row['Patient_ID']} — {row['Full_Name']}, Age {row['Age']}"):
                    selected = df[df["Patient_ID"]==row["Patient_ID"]]
                    with st.form(f"form_{row['Patient_ID']}_{idx}", clear_on_submit=True):
                        col1,col2 = st.columns(2)
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
                        idx_df = df[df["Patient_ID"]==row["Patient_ID"]].index[0]
                        df.loc[idx_df, ["AC","Fundus","U/S","OCT/FFA","Diagnosis","Treatment","Plan"]] = [
                            ac.strip(), fundus.strip(), us.strip(), oct_ffa.strip(), diagnosis.strip(), treatment.strip(), plan.strip()
                        ]
                        try:
                            df.to_csv(file_path, index=False)
                            st.success("✅ Updated locally.")
                            patient_record = df.loc[idx_df].to_dict()
                            pdf_path = generate_patient_pdf(patient_record)
                            with open(pdf_path,"rb") as f:
                                pdf_bytes = f.read()
                                st.download_button(
                                    label=f"🖨️ Download PDF Summary for Patient {row['Patient_ID']}",
                                    data=pdf_bytes,
                                    file_name=f"Patient_{row['Patient_ID']}_summary.pdf",
                                    mime="application/pdf"
                                )
                        except Exception as e:
                            st.error(f"❌ Update failed: {e}")

# ----------------- VIEW DATA -----------------
elif menu == "📊 View Data":
    st.title("📊 Patient Records")
    tab1,tab2 = st.tabs(["📋 All Records","🗕️ Download CSV"])
    with tab1:
        st.dataframe(df,use_container_width=True)
    with tab2:
        st.download_button(
            label="⬇️ Download All Records",
            data=df.to_csv(index=False),
            file_name="all_eye_patients.csv",
            mime="text/csv"
        )
