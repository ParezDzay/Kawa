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

# Sidebar
menu = st.sidebar.radio("\ud83d\udcc1 Menu", ["\ud83c\udd91 New Patient", "\ud83d\udcc8 View Data"], index=0)

if menu == "\ud83c\udd91 New Patient":
    tabs = st.tabs(["\ud83d\udccb Pre-Visit Entry (Secretary)", "\u23f3 Waiting List / Doctor Update"])

    # --- Pre-Visit Entry ---
    with tabs[0]:
        st.title("\ud83d\udccb Pre-Visit Entry (Secretary)")

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
                st.markdown("**VA:**")
                vcol1, vcol2 = st.columns(2)
                with vcol1:
                    va_ra = st.number_input("RA", min_value=0.0, format="%.2f", key="va_ra")
                with vcol2:
                    va_la = st.number_input("LA", min_value=0.0, format="%.2f", key="va_la")

                st.markdown("**IOP:**")
                icol1, icol2 = st.columns(2)
                with icol1:
                    iop_ra = st.number_input("RA ", min_value=0.0, format="%.2f", key="iop_ra")
                with icol2:
                    iop_la = st.number_input("LA ", min_value=0.0, format="%.2f", key="iop_la")

                medication = st.text_input("Medication")

            if st.form_submit_button("Submit"):
                new_entry = pd.DataFrame([{
                    "Date": date,
                    "Patient_ID": next_id,
                    "Full_Name": full_name,
                    "Age": age,
                    "Gender": gender,
                    "Phone_Number": phone,
                    "Diagnosis": "",
                    "Visual_Acuity": f"RA ({va_ra}) ; LA ({va_la})",
                    "IOP": f"RA ({iop_ra}) ; LA ({iop_la})",
                    "Medication": medication
                }])
                df = pd.concat([df, new_entry], ignore_index=True)
                try:
                    df.to_csv(file_path, index=False)
                    st.success("\u2705 Data saved locally.")
                    if push_to_github(file_path, f"Pre-visit added for Patient {next_id}"):
                        st.success("\u2705 Pushed to GitHub.")
                    else:
                        st.warning("\u26a0\ufe0f GitHub push failed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"\u274c Save failed: {e}")

    # --- Waiting List / Doctor Update ---
    with tabs[1]:
        st.title("\u23f3 Patients Waiting / Doctor Update")
        filtered_df = df.copy()
        filtered_df["Diagnosis"] = filtered_df["Diagnosis"].fillna("").astype(str).str.strip()
        waiting_df = filtered_df[filtered_df["Diagnosis"] == ""]

        def extract_val(text, eye):
            try:
                return float(text.split(f"{eye} (")[1].split(")")[0])
            except:
                return 0.0

        if waiting_df.empty:
            st.success("\ud83c\udf89 No patients are currently waiting.")
        else:
            for _, row in waiting_df.iterrows():
                with st.expander(f"\ud83e\uddea {row['Patient_ID']} — {row['Full_Name']}, Age {row['Age']}"):
                    selected = df[df["Patient_ID"] == row["Patient_ID"]]
                    with st.form(f"form_{row['Patient_ID']}", clear_on_submit=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            diagnosis = st.text_input("Diagnosis", value=selected["Diagnosis"].values[0])
                            va_val = selected["Visual_Acuity"].values[0]
                            va_ra_val = extract_val(va_val, "RA")
                            va_la_val = extract_val(va_val, "LA")
                            st.markdown("**VA:**")
                            vcol1, vcol2 = st.columns(2)
                            with vcol1:
                                va_ra = st.number_input("RA", min_value=0.0, format="%.2f", value=va_ra_val, key=f"va_ra_{row['Patient_ID']}")
                            with vcol2:
                                va_la = st.number_input("LA", min_value=0.0, format="%.2f", value=va_la_val, key=f"va_la_{row['Patient_ID']}")
                        with col2:
                            iop_val = selected["IOP"].values[0]
                            iop_ra_val = extract_val(iop_val, "RA")
                            iop_la_val = extract_val(iop_val, "LA")
                            st.markdown("**IOP:**")
                            icol1, icol2 = st.columns(2)
                            with icol1:
                                iop_ra = st.number_input("RA ", min_value=0.0, format="%.2f", value=iop_ra_val, key=f"iop_ra_{row['Patient_ID']}")
                            with icol2:
                                iop_la = st.number_input("LA ", min_value=0.0, format="%.2f", value=iop_la_val, key=f"iop_la_{row['Patient_ID']}")

                            medication = st.text_input("Medication", value=selected["Medication"].values[0])

                        if st.form_submit_button("Update Record"):
                            idx = df[df["Patient_ID"] == row["Patient_ID"]].index[0]
                            df.loc[idx, ["Diagnosis", "Visual_Acuity", "IOP", "Medication"]] = [
                                diagnosis.strip(),
                                f"RA ({va_ra}) ; LA ({va_la})",
                                f"RA ({iop_ra}) ; LA ({iop_la})",
                                medication
                            ]
                            try:
                                df.to_csv(file_path, index=False)
                                st.success("\u2705 Updated locally.")
                                if push_to_github(file_path, f"Post-visit update for Patient {row['Patient_ID']}"):
                                    st.success("\u2705 Pushed to GitHub.")
                                else:
                                    st.warning("\u26a0\ufe0f GitHub push failed.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"\u274c Update failed: {e}")

# --- View Data ---
elif menu == "\ud83d\udcc8 View Data":
    st.title("\ud83d\udcc8 Patient Records")
    tab1, tab2 = st.tabs(["\ud83d\udccb All Records", "\ud83d\udcc5 Download CSV"])
    with tab1:
        st.dataframe(df, use_container_width=True)
    with tab2:
        st.download_button(
            label="\u2b07\ufe0f Download All Records",
            data=df.to_csv(index=False),
            file_name="all_eye_patients.csv",
            mime="text/csv"
        )
