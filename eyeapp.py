import streamlit as st  
import pandas as pd
import os
import base64
import requests
from datetime import datetime

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

# Page config
st.set_page_config(page_title="Clinic Patient Data", layout="wide")
file_path = "eye_data.csv"

# Initialize CSV
if not os.path.exists(file_path):
    pd.DataFrame(columns=[
        "Date", "Patient_ID", "Full_Name", "Age", "Gender", "Phone_Number",
        "Diagnosis", "Visual_Acuity", "IOP", "Medication"
    ]).to_csv(file_path, index=False)

df = pd.read_csv(file_path)

# Session state
if "selected_waiting_id" not in st.session_state:
    st.session_state.selected_waiting_id = None
if "print_ready" not in st.session_state:
    st.session_state.print_ready = False

# Sidebar
menu = st.sidebar.radio("📁 Menu", ["🌟 New Patient", "📊 View Data"], index=0)

if menu == "🌟 New Patient":
    tabs = st.tabs(["📋 Pre-Visit Entry", "⏳ Waiting List / Doctor update"])

    # --- Pre-Visit Entry ---
    with tabs[0]:
        st.title("📋 Pre-Visit Entry")

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
            with col2:
                vacol1, vacol2 = st.columns(2)
                with vacol1:
                    va_la = st.text_input("VA: LA")
                with vacol2:
                    va_ra = st.text_input("VA: RA")

                iopcol1, iopcol2 = st.columns(2)
                with iopcol1:
                    iop_la = st.text_input("IOP: LA")
                with iopcol2:
                    iop_ra = st.text_input("IOP: RA")

                medication = st.text_input("Medication")

            if st.form_submit_button("Submit"):
                visual_acuity = f"RA ({va_ra}) ; LA ({va_la})"
                iop = f"RA ({iop_ra}) ; LA ({iop_la})"
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": next_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Diagnosis": "",
                    "Visual_Acuity": visual_acuity,
                    "IOP": iop,
                    "Medication": medication
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                try:
                    df.to_csv(file_path, index=False)
                    st.success("✅ Data saved locally.")
                    if push_to_github(file_path, f"Pre-visit added for Patient {next_id}"):
                        st.success("✅ Pushed to GitHub.")
                    else:
                        st.warning("⚠️ GitHub push failed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")

    # --- Waiting List with Inline Update ---
    with tabs[1]:
        st.title("⏳ Patients Waiting for Doctor Update")
        filtered_df = df.copy()
        filtered_df[["Diagnosis", "Treatment", "Plan"]] = filtered_df[["Diagnosis", "Treatment", "Plan"]].fillna("").astype(str)
        waiting_df = filtered_df[(filtered_df["Diagnosis"] == "") & (filtered_df["Treatment"] == "") & (filtered_df["Plan"] == "")]

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
                            if push_to_github(file_path, f"Post-visit update for Patient {row['Patient_ID']}"):
                                st.success("✅ Pushed to GitHub.")
                            else:
                                st.warning("⚠️ GitHub push failed.")

                            record = df.loc[idx]
                            html = f"""
                            <style>
                                body {{ font-family: Arial, sans-serif; padding: 20px; }}
                                h2 {{ color: #2c3e50; }}
                                table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                                td, th {{ border: 1px solid #ddd; padding: 8px; }}
                                th {{ background-color: #f2f2f2; text-align: left; }}
                            </style>
                            <h2>Patient Record Summary</h2>
                            <h3>Pre-Visit Information</h3>
                            <table>
                                <tr><th>Date</th><td>{record['Date']}</td></tr>
                                <tr><th>Patient ID</th><td>{record['Patient_ID']}</td></tr>
                                <tr><th>Full Name</th><td>{record['Full_Name']}</td></tr>
                                <tr><th>Age</th><td>{record['Age']}</td></tr>
                                <tr><th>Gender</th><td>{record['Gender']}</td></tr>
                                <tr><th>Phone Number</th><td>{record['Phone_Number']}</td></tr>
                                <tr><th>Visual Acuity</th><td>{record['Visual_Acuity']}</td></tr>
                                <tr><th>IOP</th><td>{record['IOP']}</td></tr>
                                <tr><th>Medication</th><td>{record['Medication']}</td></tr>
                            </table>
                            <h3>Doctor's Update</h3>
                            <table>
                                <tr><th>AC</th><td>{record.get('AC', '')}</td></tr>
                                <tr><th>Fundus</th><td>{record.get('Fundus', '')}</td></tr>
                                <tr><th>U/S</th><td>{record.get('U/S', '')}</td></tr>
                                <tr><th>OCT/FFA</th><td>{record.get('OCT/FFA', '')}</td></tr>
                                <tr><th>Diagnosis</th><td>{record.get('Diagnosis', '')}</td></tr>
                                <tr><th>Treatment</th><td>{record.get('Treatment', '')}</td></tr>
                                <tr><th>Plan</th><td>{record.get('Plan', '')}</td></tr>
                            </table>
                            <center><button onclick="window.print()" style="padding:10px 20px; font-size:16px;">🖨️ Print This Page</button></center>
                            """
                            st.components.v1.html(html, height=900)

                            updated_ids.append(row['Patient_ID'])

                        except Exception as e:
                            st.error(f"❌ Update failed: {e}")

            if updated_ids:
                df = df[~df['Patient_ID'].isin(updated_ids)]
                df.to_csv(file_path, index=False)

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
