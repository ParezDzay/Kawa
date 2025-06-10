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
        return res.status_code in [200, 201]
    except Exception as e:
        st.error(f"❌ GitHub push failed: {e}")
        return False

# Set page config
st.set_page_config(page_title="Clinic Patient Data", layout="wide")
BASE_DIR = os.path.dirname(__file__)
file_path = os.path.join(BASE_DIR, "eye_data.csv")

# Initialize file if missing
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number",
        "Eye_Affected", "Visual_Acuity_Right", "Visual_Acuity_Left",
        "Intraocular_Pressure_Right", "Intraocular_Pressure_Left",
        "Diagnosis", "Surgery_Scheduled", "Remarks",
        "Treatment_Provided", "Medication_Prescribed"
    ]).to_csv(file_path, index=False)

# Load data
df = pd.read_csv(file_path)
df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('"', '')

# Sidebar Menu
menu = st.sidebar.radio("📁 Menu", ["🆕 New Patient", "📊 View Data"], index=0)

# New Patient Logic
if menu == "🆕 New Patient":
    tab1, tab2 = st.tabs(["📋 Pre-Visit Entry", "🩺 Post-Visit Update"])

    with tab1:
        st.title("📋 Secretary - Pre-Visit Entry")
        with st.form("pre_visit_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date")
                patient_id = st.text_input("Patient ID")
                full_name = st.text_input("Full Name")
                age = st.number_input("Age", 0, 120)
                gender = st.selectbox("Gender", ["Male", "Female", "Child"])
                phone = st.text_input("Phone Number")
            with col2:
                eye_affected = st.selectbox("Eye Affected", ["Right", "Left", "Both"])
                visual_right = st.text_input("Visual Acuity Right")
                visual_left = st.text_input("Visual Acuity Left")
                pressure_right = st.text_input("IOP Right")
                pressure_left = st.text_input("IOP Left")

            submitted = st.form_submit_button("Submit Pre-Visit Entry")
            if submitted:
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": patient_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Eye_Affected": eye_affected,
                    "Visual_Acuity_Right": visual_right,
                    "Visual_Acuity_Left": visual_left,
                    "Intraocular_Pressure_Right": pressure_right,
                    "Intraocular_Pressure_Left": pressure_left,
                    "Diagnosis": "",
                    "Surgery_Scheduled": "",
                    "Remarks": "",
                    "Treatment_Provided": "",
                    "Medication_Prescribed": ""
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                df.to_csv(file_path, index=False)
                push_to_github(file_path, f"Pre-visit entry for {patient_id} on {datetime.now()}")
                st.success("✅ Pre-visit data saved and pushed.")
                time.sleep(1)
                st.rerun()

    with tab2:
        st.title("🩺 Doctor - Post-Visit Update")
        if df.empty:
            st.warning("No data found.")
        else:
            patient_ids = df["Patient_ID"].dropna().unique()
            selected_id = st.selectbox("Select Patient ID", patient_ids)
            patient_row = df[df["Patient_ID"] == selected_id].iloc[0]

            with st.form("post_visit_form"):
                col1, col2 = st.columns(2)
                with col1:
                    diagnosis = st.text_input("Diagnosis", value=patient_row["Diagnosis"])
                    surgery = st.text_input("Surgery Scheduled", value=patient_row["Surgery_Scheduled"])
                    remarks = st.text_area("Remarks", value=patient_row["Remarks"])
                with col2:
                    treatment = st.text_input("Treatment Provided", value=patient_row["Treatment_Provided"])
                    medication = st.text_input("Medication Prescribed", value=patient_row["Medication_Prescribed"])

                submitted = st.form_submit_button("Submit Post-Visit Update")
                if submitted:
                    idx = df[df["Patient_ID"] == selected_id].index[0]
                    df.at[idx, "Diagnosis"] = diagnosis
                    df.at[idx, "Surgery_Scheduled"] = surgery
                    df.at[idx, "Remarks"] = remarks
                    df.at[idx, "Treatment_Provided"] = treatment
                    df.at[idx, "Medication_Prescribed"] = medication
                    df.to_csv(file_path, index=False)
                    push_to_github(file_path, f"Post-visit update for {selected_id} on {datetime.now()}")
                    st.success("✅ Post-visit data updated and pushed.")
                    time.sleep(1)
                    st.rerun()

# View Data Logic
elif menu == "📊 View Data":
    st.title("📊 Patient Records")
    tab1, tab2, tab3 = st.tabs(["📋 All Data", "🔍 Filter", "📥 Download"])

    with tab1:
        st.dataframe(df, use_container_width=True)

    with tab2:
        patients = df["Full_Name"].dropna().unique()
        diagnoses = df["Diagnosis"].dropna().unique()
        selected_names = st.multiselect("Select Patient(s)", patients, default=patients)
        selected_diagnoses = st.multiselect("Select Diagnosis(es)", diagnoses, default=diagnoses)
        filtered = df[df["Full_Name"].isin(selected_names) & df["Diagnosis"].isin(selected_diagnoses)]
        st.dataframe(filtered, use_container_width=True)

    with tab3:
        st.download_button("⬇️ Download All Data", data=df.to_csv(index=False), file_name="all_eye_patients.csv")
