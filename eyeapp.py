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
file_path = "eye_data.csv"

# Initialize file
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number", "Address",
        "Medical_Record_Number", "Diagnosis", "Eye_Affected", "Visual_Acuity_Right",
        "Visual_Acuity_Left", "Intraocular_Pressure_Right", "Intraocular_Pressure_Left",
        "Treatment_Provided", "Medication_Prescribed", "Surgery_Scheduled",
        "Doctor_Name", "Next_Visit_Date", "Remarks"
    ]).to_csv(file_path, index=False)

# Load data
df = pd.read_csv(file_path)
df.columns = df.columns.str.strip().str.replace('\n', ' ').str.replace('"', '')

# Sidebar Menu
menu = st.sidebar.radio("📁 Menu", ["🆕 New Patient", "📊 View Data"], index=0)

if menu == "🆕 New Patient":
    tab1, tab2 = st.tabs(["📋 Pre-Visit Entry", "🩺 Post-Visit Update (Doctor)"])

    with tab1:
        st.title("📋 Pre-Visit Entry")

        # Generate auto-incremented Patient_ID
        try:
            last_id = df["Patient_ID"].dropna().astype(str).str.extract('(\d+)')[0].astype(int).max()
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
                address = st.text_input("Address")
            with col2:
                mrn = st.text_input("Medical Record Number")
                next_visit = st.date_input("Next Visit Date")
                remarks = st.text_input("Remarks")

            submitted = st.form_submit_button("Submit Pre-Visit Entry")
            if submitted:
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": next_id,
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
                    "Doctor_Name": "",
                    "Next_Visit_Date": next_visit,
                    "Remarks": remarks
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                try:
                    df.to_csv(file_path, index=False)
                    st.success("✅ Pre-visit data saved locally.")
                except Exception as e:
                    st.error(f"❌ Local save failed: {e}")

                if push_to_github(file_path, f"Pre-visit added for Patient {next_id}"):
                    st.success("✅ Pushed to GitHub.")
                else:
                    st.warning("⚠️ GitHub push failed.")
                time.sleep(2)
                st.rerun()

    with tab2:
        st.title("🩺 Post-Visit Update (Doctor)")
        if df.empty or df["Patient_ID"].isna().all():
            st.warning("No patient records available.")
        else:
            existing_ids = df["Patient_ID"].dropna().unique().tolist()
            latest_id = df["Patient_ID"].dropna().iloc[-1]
            selected_id = st.selectbox(
                "Select Patient ID",
                existing_ids,
                index=existing_ids.index(latest_id) if latest_id in existing_ids else 0
            )

            record = df[df["Patient_ID"] == selected_id]
            if record.empty:
                st.error("Patient ID not found.")
            else:
                with st.form("post_visit_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        diagnosis = st.text_input("Diagnosis", value=record["Diagnosis"].values[0])
                        eye_affected = st.selectbox("Eye Affected", ["Right", "Left", "Both"])
                        visual_right = st.text_input("Visual Acuity Right", value=record["Visual_Acuity_Right"].values[0])
                        visual_left = st.text_input("Visual Acuity Left", value=record["Visual_Acuity_Left"].values[0])
                    with col2:
                        pressure_right = st.number_input("IOP Right", value=float(record["Intraocular_Pressure_Right"].fillna(0).values[0]), step=1.0)
                        pressure_left = st.number_input("IOP Left", value=float(record["Intraocular_Pressure_Left"].fillna(0).values[0]), step=1.0)
                        treatment = st.text_input("Treatment Provided", value=record["Treatment_Provided"].values[0])
                        medication = st.text_input("Medication Prescribed", value=record["Medication_Prescribed"].values[0])
                        surgery = st.text_input("Surgery Scheduled", value=record["Surgery_Scheduled"].values[0])
                        doctor = st.text_input("Doctor Name", value=record["Doctor_Name"].values[0])

                    submitted = st.form_submit_button("Update Patient Record")
                    if submitted:
                        idx = df[df["Patient_ID"] == selected_id].index[0]
                        df.loc[idx, [
                            "Diagnosis", "Eye_Affected", "Visual_Acuity_Right", "Visual_Acuity_Left",
                            "Intraocular_Pressure_Right", "Intraocular_Pressure_Left",
                            "Treatment_Provided", "Medication_Prescribed", "Surgery_Scheduled", "Doctor_Name"
                        ]] = [
                            diagnosis, eye_affected, visual_right, visual_left,
                            pressure_right, pressure_left,
                            treatment, medication, surgery, doctor
                        ]

                        try:
                            df.to_csv(file_path, index=False)
                            st.success("✅ Post-visit data saved locally.")
                        except Exception as e:
                            st.error(f"❌ Local save failed: {e}")

                        if push_to_github(file_path, f"Post-visit update for Patient {selected_id}"):
                            st.success("✅ Pushed to GitHub.")
                        else:
                            st.warning("⚠️ GitHub push failed.")
                        time.sleep(2)
                        st.rerun()

elif menu == "📊 View Data":
    st.title("📊 Patient Records")
    tab1, tab2 = st.tabs(["📋 All Records", "📥 Download CSV"])

    with tab1:
        st.dataframe(df, use_container_width=True)

    with tab2:
        st.download_button(
            label="⬇️ Download All Records",
            data=df.to_csv(index=False),
            file_name="all_eye_patients.csv",
            mime="text/csv"
        )
