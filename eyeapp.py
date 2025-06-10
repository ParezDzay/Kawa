import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
import base64
import requests
from datetime import datetime
import time

# GitHub push function
def push_to_github(file_path, commit_message):
    try:
        token = st.secrets["github"]["token"]
        username = st.secrets["github"]["username"]
        repo = st.secrets["github"]["repo"]
        branch = st.secrets["github"]["branch"]

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        encoded_content = base64.b64encode(content.encode()).decode()
        filename = os.path.basename(file_path)
        url = f"https://api.github.com/repos/{username}/{repo}/contents/{filename}"

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json"
        }

        response = requests.get(url, headers=headers)
        sha = response.json().get("sha") if response.status_code == 200 else None

        payload = {
            "message": commit_message,
            "content": encoded_content,
            "branch": branch
        }
        if sha:
            payload["sha"] = sha

        res = requests.put(url, headers=headers, json=payload)
        if res.status_code in [200, 201]:
            return True
        else:
            st.error(f"❌ GitHub push failed: {res.status_code} – {res.json().get('message')}")
            return False

    except Exception as e:
        st.error(f"🚨 Error pushing to GitHub: {e}")
        return False

# Set page config
st.set_page_config(page_title="Clinic Patient Data", layout="wide")

# Ensure consistent base directory
BASE_DIR = os.path.dirname(__file__)
file_path = os.path.join(BASE_DIR, "eye_data.csv")

# Ensure file exists
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number", "Address",
        "Medical_Record_Number", "Diagnosis", "Eye_Affected", "Visual_Acuity_Right", "Visual_Acuity_Left",
        "Intraocular_Pressure_Right", "Intraocular_Pressure_Left", "Treatment_Provided",
        "Medication_Prescribed", "Surgery_Scheduled", "Doctor_Name", "Next_Visit_Date", "Remarks"
    ]).to_csv(file_path, index=False)

# Load data
df = pd.read_csv(file_path)
df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('"', '')

# Language dictionary
texts = {
    "English": {
        "new_patient": "🆕 New Patient",
        "view_data": "📊 View Data",
        "patient_data_title": "👁️ Dr. Kawa Khoshnaw Clinic Patient Data",
        "add_patient_title": "➕ New Patient Record",
        "download": "⬇️ Download filtered data as CSV",
        "download_all": "⬇️ Download full dataset as CSV"
    }
}

language = "English"

# Sidebar
menu = st.sidebar.radio(
    "📁 Menu",
    [texts[language]["new_patient"], texts[language]["view_data"]],
    index=0
)

if menu == texts[language]["new_patient"]:
    tab1, tab2 = st.tabs(["📋 Pre-Visit Entry", "🩺 Post-Visit Update"])

    with tab1:
        st.title("📋 Secretary - Pre-Visit Patient Entry")
        with st.form("secretary_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                patient_id = st.text_input("Patient ID")
                full_name = st.text_input("Full Name")
                age = st.number_input("Age", min_value=0, max_value=120)
                gender = st.selectbox("Gender", ["Male", "Female", "Child"])
                phone = st.text_input("Phone Number")
                address = st.text_input("Address")
            with col2:
                mrn = st.text_input("Medical Record Number")
                next_visit = st.date_input("Next Visit Date")
                doctor = st.text_input("Doctor Name")

            submitted = st.form_submit_button("Add Pre-Visit Record")
            if submitted:
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": patient_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Address": address,
                    "Medical_Record_Number": mrn,
                    "Diagnosis": "",
                    "Eye_Affected": "",
                    "Visual_Acuity_Right": "",
                    "Visual_Acuity_Left": "",
                    "Intraocular_Pressure_Right": "",
                    "Intraocular_Pressure_Left": "",
                    "Treatment_Provided": "",
                    "Medication_Prescribed": "",
                    "Surgery_Scheduled": "",
                    "Doctor_Name": doctor,
                    "Next_Visit_Date": next_visit,
                    "Remarks": ""
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                df.to_csv(file_path, index=False)
                push_to_github(file_path, f"Pre-visit patient added on {datetime.now()}")
                st.success("✅ Pre-visit patient entry saved.")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.title("🩺 Doctor - Post-Visit Patient Update")
        editable_df = df.copy()
        patient_ids = editable_df["Patient_ID"].dropna().unique()
        selected_id = st.selectbox("Select Patient ID to Update", patient_ids)
        patient_record = editable_df[editable_df["Patient_ID"] == selected_id].iloc[0]

        with st.form("doctor_form"):
            col1, col2 = st.columns(2)
            with col1:
                diagnosis = st.text_input("Diagnosis", value=patient_record["Diagnosis"])
                eye_affected = st.selectbox("Eye Affected", ["Right", "Left", "Both"], index=0)
                visual_right = st.text_input("Visual Acuity Right", value=patient_record["Visual_Acuity_Right"])
                visual_left = st.text_input("Visual Acuity Left", value=patient_record["Visual_Acuity_Left"])
            with col2:
                pressure_right = st.number_input("IOP Right", value=float(patient_record["Intraocular_Pressure_Right"] or 0))
                pressure_left = st.number_input("IOP Left", value=float(patient_record["Intraocular_Pressure_Left"] or 0))
                treatment = st.text_input("Treatment Provided", value=patient_record["Treatment_Provided"])
                medication = st.text_input("Medication Prescribed", value=patient_record["Medication_Prescribed"])
                surgery = st.text_input("Surgery Scheduled", value=patient_record["Surgery_Scheduled"])
                remarks = st.text_area("Remarks", value=patient_record["Remarks"])

            submitted_doctor = st.form_submit_button("Update Patient Record")
            if submitted_doctor:
                idx = editable_df[editable_df["Patient_ID"] == selected_id].index[0]
                editable_df.at[idx, "Diagnosis"] = diagnosis
                editable_df.at[idx, "Eye_Affected"] = eye_affected
                editable_df.at[idx, "Visual_Acuity_Right"] = visual_right
                editable_df.at[idx, "Visual_Acuity_Left"] = visual_left
                editable_df.at[idx, "Intraocular_Pressure_Right"] = pressure_right
                editable_df.at[idx, "Intraocular_Pressure_Left"] = pressure_left
                editable_df.at[idx, "Treatment_Provided"] = treatment
                editable_df.at[idx, "Medication_Prescribed"] = medication
                editable_df.at[idx, "Surgery_Scheduled"] = surgery
                editable_df.at[idx, "Remarks"] = remarks
                editable_df.to_csv(file_path, index=False)
                push_to_github(file_path, f"Post-visit update for patient {selected_id} on {datetime.now()}")
                st.success("✅ Patient record updated.")
                time.sleep(1)
                st.rerun()

elif menu == texts[language]["view_data"]:
    st.title(texts[language]["patient_data_title"])
    st.markdown("---")
    tab1, tab2, tab3 = st.tabs(["📋 All Data", "🔍 Filtered View", "📥 Download Data"])

    with tab1:
        st.dataframe(df, use_container_width=True)

    with tab2:
        patient_options = df['Full_Name'].dropna().unique()
        diagnosis_options = df['Diagnosis'].dropna().unique()
        col1, col2 = st.columns(2)
        selected_patient = col1.multiselect("Select Patient", patient_options, default=patient_options)
        selected_diagnosis = col2.multiselect("Select Diagnosis", diagnosis_options, default=diagnosis_options)
        filtered_df = df[df['Full_Name'].isin(selected_patient) & df['Diagnosis'].isin(selected_diagnosis)]
        st.dataframe(filtered_df, use_container_width=True)
        st.download_button(
            label=texts[language]["download"],
            data=filtered_df.to_csv(index=False),
            file_name="filtered_eye_patients.csv",
            mime="text/csv"
        )

    with tab3:
        st.download_button(
            label=texts[language]["download_all"],
            data=df.to_csv(index=False),
            file_name="all_eye_patients.csv",
            mime="text/csv"
        )
