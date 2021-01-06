BUCKET_NAME = 'medical-documents-storage'
DOCUMENT_PREFIX = "documents"
REGION = "us-west-1"
DOWNLOAD_DIR = "/tmp"
JSON_PREFIX = "json"
TICK_THRESH = 30
LAMBDA = False
REF_FIELD_NAMES = {'fileName': 'filename', 'GRI ID:': 'sample_id', 'GRI ID:-Confidence': 'sample_id_confidence',
                   'Sample Collection Date:': 'sample_collected_date',
                   'Sample Collection Date:-Confidence': 'sample_collected_date_confidence',
                   'Date of Birth (dd/mm/yy):': 'year_of_birth',
                   'Date of Birth (dd/mm/yy):-Confidence': 'year_of_birth_confidence', 'Age:': 'age',
                   'Age:-Confidence': 'age_confidence', 'Sex:': 'sex', 'Sex:-Confidence': 'sex_confidence',
                   'Ethnicity:': 'ethnicity', 'Ethnicity:-Confidence': 'ethnicity_confidence',
                   'Height:': 'height', 'Height:-Confidence': 'height_confidence', 'Weight:': 'weight',
                   'Weight:-Confidence': 'weight_confidence',
                   'Has the patient been diagnosed with Dengue previously?': 'previously_diagnosed',
                   'Has the patient been diagnosed with '
                   'Dengue previously?-Confidence': 'previously_diagnosed_confidence',
                   'Has the patient been hospitalized '
                   'for previous dengue infections?': 'previously_hostpitalized',
                   'Has the patient been hospitalized '
                   'for previous dengue infections?-Confidence': 'previously_hostpitalized_confidence',
                   'Pulse Rate:': 'pulse_rate', 'Pulse Rate:-Confidence': 'pulse_rate_confidence',
                   'Respiratory Rate:': 'respritory_rate',
                   'Respiratory Rate:-Confidence': 'respritory_rate_confidence', 'Bp S/D': 'blood_pressure',
                   'Bp S/D-Confidence': 'blood_pressure_confidence',
                   'Date of Fever Onset:': 'date_of_fever_onset',
                   'Date of Fever Onset:-Confidence': 'date_of_fever_onset_confidence', 'Temp:': 'temperature',
                   'Temp:-Confidence': 'temperature_confidence', 'Headache': 'headache',
                   'Retrorbital Pain': 'retrorbital_pain', 'Runny nose': 'runny_nose',
                   'Difficulty in breathing': 'difficulty_breathing', 'Intercostal Pain': 'intercostal_pain',
                   'Cough': 'cough', 'Loss of Appetite': 'loss_of_appetite', 'Nausea': 'nausea',
                   'Vomiting': 'vomiting', 'Abdominal Pain': 'abdominal_pain', 'Back Pain': 'back_pain',
                   'Muscle ache': 'muscle_ache', 'Joint ache': 'joint_ache', 'Bleeding gums': 'bleeding_gums',
                   'Bleeding nose': 'bleeding_nose', 'Vomiting Blood': 'vomiting_blood',
                   'Blood in stool': 'blood_in_stool', 'Blood in urine': 'blood_in_urine',
                   'Increased menstrual flow': 'increased_menstrual_flow',
                   'Inter-menstrual bleeding': 'Inter Menstrual Bleeding', 'Flushed Face': 'flushed_face',
                   'Sunken eyes': 'sunken_eyes', 'Mucosal Petechiae': 'mucosal_petechiae',
                   'Ecchymoses': 'ecchymoses', 'Petechiae': 'petechiae', 'Rash': 'rash',
                   'Erythematous Rash': 'erythematous_rash', 'Abdominal Tenderness': 'abdominal_tenderness',
                   'Abdominal Distension': 'abdominal_distension', 'Ascites': 'ascites',
                   'Hepatomegaly (size in cm)': 'hepatomegaly_size', 'Pleural effusion': 'pleural_effusion',
                   'Platelets (x1000)-Upon Admission': 'platelets_admission',
                   'Platelets (x1000)-2nd Recording (highest where applicable)': 'platelets_lowest',
                   'Platelets (x1000)-On Discharge': 'platelets_on_discharge',
                   'Haematocrit (%)-Upon Admission': 'Haematocrit_addmission',
                   'Haematocrit (%)-2nd Recording (highest where applicable)': 'haematocrit_lowest',
                   'Haematocrit (%)-On Discharge': 'haematocrit_on_discharge',
                   'Haemoglobin (g/dl)-Upon Admission': 'haemoglobin_admission',
                   'Haemoglobin (g/dl)-2nd Recording (highest where applicable)': 'haemoglobin_lowest',
                   'Haemoglobin (g/dl)-On Discharge': 'haemoglobin_on_discharge',
                   'Leukocytes (x1000)-Upon Admission': 'leucocytes_admission',
                   'Leukocytes (x1000)-2nd Recording (highest where applicable)': 'leucocytes_lowest',
                   'Leukocytes (x1000)-On Discharge': 'leucocytes_on_discharge',
                   'Neutrophils (%)-Upon Admission': 'neutrophils_admission',
                   'Neutrophils (%)-2nd Recording (highest where applicable)': 'neutrophils_lowest',
                   'Neutrophils (%)-On Discharge': 'neutrophils_on_discharge',
                   'Lymphocytes (%)-Upon Admission': 'lymphocytes_admission',
                   'Lymphocytes (%)-2nd Recording (highest where applicable)': 'lymphocytes_lowest',
                   'Lymphocytes (%)-On Discharge': 'lymphocytes_on_discharge',
                   'Eosinophil (%)-Upon Admission': 'eosinophils_admission',
                   'Eosinophil (%)-2nd Recording (highest where applicable)': 'eosinophils_lowest',
                   'Eosinophil (%)-On Discharge': 'eosinophils_on_discharge',
                   'Albumin (g/dl)-Upon Admission': 'albumin_admission',
                   'Albumin (g/dl)-2nd Recording (highest where applicable)': 'albumin_lowest',
                   'Albumin (g/dl)-On Discharge': 'albumin_on_discharge',
                   'AST (U/L)-Upon Admission': 'ast_admission',
                   'AST (U/L)-2nd Recording (highest where applicable)': 'ast_lowest',
                   'AST (U/L)-On Discharge': 'ast_on_discharge', 'ALT (U/L)-Upon Admission': 'alt_admission',
                   'ALT (U/L)-2nd Recording (highest where applicable)': 'alt_lowest',
                   'ALT (U/L)-On Discharge': 'alt_on_discharge',
                   'Bilirubin (mg/dl)-Upon Admission': 'bilirubin_admission',
                   'Bilirubin (mg/dl)-2nd Recording (highest where applicable)': 'bilirubin_lowest',
                   'Bilirubin (mg/dl)-On Discharge': 'bilirubin_on_discharge',
                   'X-Ray-Upon Admission': 'xray_admission',
                   'X-Ray-2nd Recording (highest where applicable)': 'xray_lowest',
                   'X-Ray-On Discharge': 'xray_on_discharge', 'Other tests done': 'other_tests_done',
                   'Serum Protein': 'serum_protein', 'Serum Calcium': 'serum_calcium',
                   'Total Cholesterol': 'total_cholesterol', 'Ultrasound Findings': 'ultrasound_findings',
                   'Presumptive Diagnosis': 'presumptive_diagnosis',
                   'Presumptive Diagnosis-Confidence': 'presumptive_diagnosis_confidence',
                   'Other comments': 'other_comments'}
DOCUMENT_NAME = ""
TEST_PREFIX = "test"
CONFIG_FILE_PATH = ""
