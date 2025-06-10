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
        "add_patient_title": "➕ Add New Patient Record",
        "select_patient": "Select Patient",
        "select_diagnosis": "Select Diagnosis",
        "add_patient_button": "Add Patient",
        "success_msg": "✅ New patient record added and saved!",
        "date": "Date",
        "patient_id": "Patient ID",
        "full_name": "Full Name",
        "age": "Age",
        "gender": "Gender",
        "phone": "Phone Number",
        "address": "Address",
        "mrn": "Medical Record Number",
        "diagnosis": "Diagnosis",
        "eye_affected": "Eye Affected",
        "visual_right": "Visual Acuity Right",
        "visual_left": "Visual Acuity Left",
        "pressure_right": "IOP Right",
        "pressure_left": "IOP Left",
        "treatment": "Treatment Provided",
        "medication": "Medication Prescribed",
        "surgery": "Surgery Scheduled",
        "doctor_name": "Doctor Name",
        "next_visit": "Next Visit Date",
        "remarks": "Remarks",
        "download": "📂 Download filtered data as CSV",
        "download_all": "📂 Download full dataset as CSV"
    }
}

language = "English"

# Sidebar
menu = st.sidebar.radio(
    "📁 Menu",
    [texts[language]["new_patient"], texts[language]["view_data"]],
    index=0
)

if menu == texts[language]["view_data"]:
    st.title(texts[language]["patient_data_title"])
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 All Data", "🔍 Filtered View", "📥 Download Data"])

    with tab1:
        st.subheader("📋 Complete Patient Records")
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("🔍 Filter and Explore Records")
        patient_options = df['Full_Name'].dropna().unique()
        diagnosis_options = df['Diagnosis'].dropna().unique()

        col1, col2 = st.columns(2)
        selected_patient = col1.multiselect(texts[language]["select_patient"], patient_options, default=patient_options)
        selected_diagnosis = col2.multiselect(texts[language]["select_diagnosis"], diagnosis_options, default=diagnosis_options)

        filtered_df = df[
            df['Full_Name'].isin(selected_patient) &
            df['Diagnosis'].isin(selected_diagnosis)
        ]

        st.dataframe(filtered_df, use_container_width=True)

        st.download_button(
            label=texts[language]["download"],
            data=filtered_df.to_csv(index=False),
            file_name="filtered_eye_patients.csv",
            mime="text/csv"
        )

    with tab3:
        st.subheader("📥 Download All Data")
        st.download_button(
            label=texts[language]["download_all"],
            data=df.to_csv(index=False),
            file_name="all_eye_patients.csv",
            mime="text/csv"
        )

    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Diagnosis Distribution")
        if not df.empty and "Diagnosis" in df:
            diag_counts = df['Diagnosis'].value_counts()
            st.bar_chart(diag_counts)

    with col2:
        st.subheader("🧑‍🤝‍🧑 Gender Distribution")
        if not df.empty and "Gender" in df:
            gender_counts = df['Gender'].value_counts()
            fig, ax = plt.subplots()
            ax.pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%', startangle=90)
            ax.axis('equal')
            st.pyplot(fig)

elif menu == texts[language]["new_patient"]:
    st.title(texts[language]["add_patient_title"])
    st.markdown("Please fill out the following patient details:")
    st.markdown("---")

    with st.form("patient_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            date = st.date_input(texts[language]["date"])
            patient_id = st.text_input(texts[language]["patient_id"])
            full_name = st.text_input(texts[language]["full_name"])
            age = st.number_input(texts[language]["age"], min_value=0, max_value=120)
            gender = st.selectbox(texts[language]["gender"], ["Male", "Female", "Child"])
            phone = st.text_input(texts[language]["phone"])
            address = st.text_input(texts[language]["address"])
            mrn = st.text_input(texts[language]["mrn"])
            diagnosis = st.text_input(texts[language]["diagnosis"])
            eye_affected = st.selectbox(texts[language]["eye_affected"], ["Right", "Left", "Both"])
            visual_right = st.text_input(texts[language]["visual_right"])
        with col2:
            visual_left = st.text_input(texts[language]["visual_left"])
            pressure_right = st.number_input(texts[language]["pressure_right"], step=1.0)
            pressure_left = st.number_input(texts[language]["pressure_left"], step=1.0)
            treatment = st.text_input(texts[language]["treatment"])
            medication = st.text_input(texts[language]["medication"])
            surgery = st.text_input(texts[language]["surgery"])
            doctor = st.text_input(texts[language]["doctor_name"])
            next_visit = st.date_input(texts[language]["next_visit"])
            remarks = st.text_input(texts[language]["remarks"])

        submitted = st.form_submit_button(texts[language]["add_patient_button"])

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
                "Diagnosis": diagnosis,
                "Eye_Affected": eye_affected,
                "Visual_Acuity_Right": visual_right,
                "Visual_Acuity_Left": visual_left,
                "Intraocular_Pressure_Right": pressure_right,
                "Intraocular_Pressure_Left": pressure_left,
                "Treatment_Provided": treatment,
                "Medication_Prescribed": medication,
                "Surgery_Scheduled": surgery,
                "Doctor_Name": doctor,
                "Next_Visit_Date": next_visit,
                "Remarks": remarks,
            }])

            df = pd.concat([df, new_entry], ignore_index=True)
            try:
                df.to_csv(file_path, index=False)
                st.info(f"✅ Data saved locally to: {file_path}")
            except Exception as e:
                st.error(f"❌ Failed to save locally: {e}")

            success = push_to_github(file_path, f"Patient data updated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            if success:
                st.success("✅ New patient record added and saved to GitHub!")
            else:
                st.warning("⚠️ Data saved locally, but failed to push to GitHub.")

            time.sleep(2)
            st.rerun()
