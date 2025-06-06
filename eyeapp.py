import streamlit as st
import pandas as pd
import os

# File path
file_path = r"eye_data.csv"

# Ensure file exists with correct columns
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

# Language dictionary for English and Arabic
texts = {
    "English": {
        "fill_data": "Fill Data",
        "view_data": "View Data",
        "patient_data_title": "Dr Kawa Khoshnaw Clinic Patient Data",
        "add_patient_title": "Add New Patient Record",
        "select_patient": "Select Patient",
        "select_diagnosis": "Select Diagnosis",
        "add_patient_button": "Add Patient",
        "success_msg": "New patient record added and saved!",
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
        "download": "Download filtered data as CSV"
    },
    "Arabic": {
        "fill_data": "ملء البيانات",
        "view_data": "عرض البيانات",
        "patient_data_title": "بيانات مرضى عيادة د. كاوا خوشناو",
        "add_patient_title": "إضافة سجل مريض جديد",
        "select_patient": "اختر المريض",
        "select_diagnosis": "اختر التشخيص",
        "add_patient_button": "إضافة المريض",
        "success_msg": "تمت إضافة سجل المريض الجديد وحفظه!",
        "date": "التاريخ",
        "patient_id": "معرّف المريض",
        "full_name": "الاسم الكامل",
        "age": "العمر",
        "gender": "الجنس",
        "phone": "رقم الهاتف",
        "address": "العنوان",
        "mrn": "رقم السجل الطبي",
        "diagnosis": "التشخيص",
        "eye_affected": "العين المتأثرة",
        "visual_right": "حدة البصر اليمنى",
        "visual_left": "حدة البصر اليسرى",
        "pressure_right": "ضغط العين اليمنى",
        "pressure_left": "ضغط العين اليسرى",
        "treatment": "العلاج المقدم",
        "medication": "الأدوية الموصوفة",
        "surgery": "العملية المجدولة",
        "doctor_name": "اسم الطبيب",
        "next_visit": "تاريخ الزيارة القادمة",
        "remarks": "ملاحظات",
        "download": "تحميل البيانات المصفاة بصيغة CSV"
    }
}

# Language selection (no "Navigation" word)
language = st.sidebar.selectbox("Select Language / اختر اللغة", ["English", "Arabic"])

# Sidebar menu, default to "Fill Data"
menu = st.sidebar.radio(
    "",
    [texts[language]["view_data"], texts[language]["fill_data"]],
    index=1
)

if menu == texts[language]["view_data"]:
    st.title(texts[language]["patient_data_title"])

    # Filters
    patient_options = df['Full_Name'].dropna().unique()
    diagnosis_options = df['Diagnosis'].dropna().unique()

    selected_patient = st.sidebar.multiselect(texts[language]["select_patient"], patient_options, default=patient_options)
    selected_diagnosis = st.sidebar.multiselect(texts[language]["select_diagnosis"], diagnosis_options, default=diagnosis_options)

    # Filter data
    filtered_df = df[
        df['Full_Name'].isin(selected_patient) &
        df['Diagnosis'].isin(selected_diagnosis)
    ]

    st.subheader(texts[language]["patient_data_title"])
    st.dataframe(filtered_df)

    st.download_button(
        label=texts[language]["download"],
        data=filtered_df.to_csv(index=False),
        file_name="filtered_eye_patients.csv",
        mime="text/csv"
    )

elif menu == texts[language]["fill_data"]:
    st.title(texts[language]["add_patient_title"])

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
            df.to_csv(file_path, index=False)
            st.success(texts[language]["success_msg"])
