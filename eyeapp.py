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

# Sidebar
menu = st.sidebar.radio("📁 Menu", ["🆕 New Patient", "📊 View Data"], index=0)

# Session state
if "selected_id_from_waiting" not in st.session_state:
    st.session_state.selected_id_from_waiting = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📋 Pre-Visit Entry"

if menu == "🆕 New Patient":
    tabs = st.tabs(["📋 Pre-Visit Entry", "⏳ Waiting List", "🩺 Post-Visit Update"])

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
                visual_acuity = st.text_input("VA: RA ( ) and LA ( )", placeholder="e.g., RA (6/6) and LA (6/9)")
                iop = st.text_input("IOP: RA ( ) and LA ( )", placeholder="e.g., RA (15) and LA (14)")
                medication = st.text_input("Medication")

            if st.form_submit_button("Submit"):
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": next_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Diagnosis": pd.NA,
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
                    st.stop()
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")

    # --- Waiting List ---
    with tabs[1]:
        st.title("⏳ Patients Waiting for Doctor Update")
        df["Diagnosis_cleaned"] = df["Diagnosis"].replace("", pd.NA)
        waiting_df = df[df["Diagnosis_cleaned"].isna()].drop(columns=["Diagnosis_cleaned"])

        if waiting_df.empty:
            st.success("🎉 No patients are currently waiting.")
        else:
            for _, row in waiting_df.iterrows():
                btn = f"🪪 {row['Patient_ID']} — {row['Full_Name']}, Age {row['Age']}"
                if st.button(btn, key=row["Patient_ID"]):
                    st.session_state.selected_id_from_waiting = row["Patient_ID"]
                    st.session_state.active_tab = "🩺 Post-Visit Update"
                    st.experimental_rerun()

    # --- Post-Visit Update ---
    with tabs[2]:
        st.title("🩺 Post-Visit Update")
        if df.empty or df["Patient_ID"].isna().all():
            st.warning("No patient records.")
        else:
            ids = df["Patient_ID"].dropna().unique().tolist()
            default_idx = 0
            if st.session_state.selected_id_from_waiting in ids:
                default_idx = ids.index(st.session_state.selected_id_from_waiting)

            selected_id = st.selectbox("Select Patient ID", ids, index=default_idx)
            st.session_state.selected_id_from_waiting = None
            record = df[df["Patient_ID"] == selected_id]
            if record.empty:
                st.error("Patient not found.")
            else:
                with st.form("post_visit_form", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        diagnosis = st.text_input("Diagnosis", value=record["Diagnosis"].values[0] or "")
                        visual_acuity = st.text_input("VA: RA ( ) and LA ( )", value=record["Visual_Acuity"].values[0])
                    with col2:
                        iop = st.text_input("IOP: RA ( ) and LA ( )", value=record["IOP"].values[0])
                        medication = st.text_input("Medication", value=record["Medication"].values[0])

                    if st.form_submit_button("Update"):
                        idx = df[df["Patient_ID"] == selected_id].index[0]
                        df.loc[idx, ["Diagnosis", "Visual_Acuity", "IOP", "Medication"]] = [
                            diagnosis, visual_acuity, iop, medication
                        ]
                        try:
                            df.to_csv(file_path, index=False)
                            st.success("✅ Updated locally.")
                            if push_to_github(file_path, f"Post-visit update for Patient {selected_id}"):
                                st.success("✅ Pushed to GitHub.")
                            else:
                                st.warning("⚠️ GitHub push failed.")
                            st.stop()
                        except Exception as e:
                            st.error(f"❌ Update failed: {e}")

# --- View Data ---
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
