import boto3
from botocore.client import Config
import os
import csv
import time
from trp import *
from datetime import datetime


class Input:
    def __init__(self):
        self.bucketName = "medical-documents-storage"
        self.fileName = ""
        self.awsRegion = "us-west-1"
        self.detectText = True
        self.detectForms = True
        self.detectTables = True

        self.documentType = "PDF"


class AwsHelper:
    @staticmethod
    def get_client(name, aws_region):
        config = Config(
            retries=dict(
                max_attempts=30
            )
        )
        return boto3.client(name, region_name=aws_region, config=config)


class FileHelper:
    @staticmethod
    def get_file_name_and_extension(file_path):
        basename = os.path.basename(file_path)
        dn, dext = os.path.splitext(basename)
        return dn, dext[1:]

    @staticmethod
    def get_file_extension(file_name):
        ext = file_name.split(".")[-1]
        return ext

    @staticmethod
    def write_csv(file_name, field_names, csv_data):
        with open(file_name, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=field_names)
            writer.writeheader()

            for item in csv_data:
                i = 0
                row = {}
                for value in item:
                    row[field_names[i]] = value
                    i = i + 1
                writer.writerow(row)

    @staticmethod
    def write_csv_raw(file_name, csv_data):
        with open(file_name, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for item in csv_data:
                writer.writerow(item)

    @staticmethod
    def write_csv_to_s3(header_row, row_data):
        # print(header_row)
        # print(rowData)
        prefix = 'GS Clinical Data Current as of'
        today = datetime.today().strftime('%Y-%m-%d')

        inp = Input()
        bucket_name = inp.bucketName
        s3_client = AwsHelper().get_client('s3', inp.awsRegion)
        res = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        file_name = '{} {}.csv'.format(prefix, today)
        tmp_file_name = '/tmp/{}'.format(file_name)

        if 'Contents' in res:
            keys = res['Contents']
            for key in keys:
                path_arr = key['Key'].split("/")
                path_arr.reverse()
                tmp_file_name = '/tmp/{}'.format(path_arr[0])
                with open(tmp_file_name, 'wb') as f:
                    s3_client.download_fileobj(bucket_name, key['Key'], f)
                    f.close()

                # response = s3_client.delete_object(
                #     Bucket=bucket_name,
                #     Key=key['Key'],
                # )

        else:
            with open(tmp_file_name, 'w') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=header_row)
                writer.writeheader()
                csv_file.close()

        with open(tmp_file_name, 'a') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=header_row)
            for item in [row_data]:
                i = 0
                row = {}
                for value in item:
                    row[header_row[i]] = value
                    i = i + 1
                writer.writerow(row)

            csv_file.close()

        s3 = boto3.resource('s3')
        s3.Object(bucket_name, "{}".format(file_name)).upload_file(tmp_file_name)


class PDFProcessor:
    def __init__(self, input_parameters):
        self.input_parameters = input_parameters

    def _start_job(self):
        # response = None
        client = AwsHelper().get_client('textract', self.input_parameters.awsRegion)
        if not self.input_parameters.detectForms and not self.input_parameters.detectTables:
            response = client.start_document_text_detection(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': self.input_parameters.bucketName,
                        'Name': self.input_parameters.fileName
                    }
                })
        else:
            features = []
            if self.input_parameters.detectTables:
                features.append("TABLES")
            if self.input_parameters.detectForms:
                features.append("FORMS")

            response = client.start_document_analysis(
                DocumentLocation={
                    'S3Object': {
                        'Bucket': self.input_parameters.bucketName,
                        'Name': self.input_parameters.fileName
                    }
                },
                FeatureTypes=features
            )

        return response["JobId"]

    def _is_job_complete(self, job_id):
        time.sleep(5)
        client = AwsHelper().get_client('textract', self.input_parameters.awsRegion)
        if not self.input_parameters.detectForms and not self.input_parameters.detectTables:
            response = client.get_document_text_detection(JobId=job_id)
        else:
            response = client.get_document_analysis(JobId=job_id)
        status = response["JobStatus"]
        print(status)

        while status == "IN_PROGRESS":
            time.sleep(5)
            if not self.input_parameters.detectForms and not self.input_parameters.detectTables:
                response = client.get_document_text_detection(JobId=job_id)
            else:
                response = client.get_document_analysis(JobId=job_id)
            status = response["JobStatus"]
            print(status)

        return status

    def _get_job_results(self, job_id):

        pages = []

        time.sleep(5)

        client = AwsHelper().get_client('textract', self.input_parameters.awsRegion)
        if not self.input_parameters.detectForms and not self.input_parameters.detectTables:
            response = client.get_document_text_detection(JobId=job_id)
        else:
            response = client.get_document_analysis(JobId=job_id)
        pages.append(response)
        print("Result set page received: {}".format(len(pages)))
        next_token = None
        if 'NextToken' in response:
            next_token = response['NextToken']
            # print("Next token: {}".format(nextToken))

        while next_token:
            time.sleep(5)

            if not self.input_parameters.detectForms and not self.input_parameters.detectTables:
                response = client.get_document_text_detection(JobId=job_id, NextToken=next_token)
            else:
                response = client.get_document_analysis(JobId=job_id, NextToken=next_token)

            pages.append(response)
            print("Result set page received: {}".format(len(pages)))
            next_token = None
            if 'NextToken' in response:
                next_token = response['NextToken']
                # print("Next token: {}".format(nextToken))

            # if(len(pages) > 20):
            #    break

        return pages

    def run(self):
        job_id = self._start_job()
        print("Started Asyc Job with Id: {}".format(job_id))
        status = self._is_job_complete(job_id)
        if status == "SUCCEEDED":
            response_pages = self._get_job_results(job_id)
            return response_pages


class DocProcessor:
    def __init__(self, file_name):
        inp = Input()
        self.output = None

        ext = FileHelper.get_file_extension(file_name)
        if ext != 'pdf':
            raise Exception('PDF document is required.')

        inp.fileName = file_name
        self.inputParameters = inp

    def run(self):
        print("Starting Textract..")

        pdf_proc = PDFProcessor(self.inputParameters)
        self.output = pdf_proc.run()

        return self.output


class OutputGenerator:
    def __init__(self, response, document_name):
        self.response = response
        self.forms = True
        self.tables = True

        self.document = Document(self.response)
        self.document_name = document_name

    def _output_form(self, page):
        ref_field_names = {'fileName': 'filename', 'GRI ID:': 'sample_id', 'GRI ID:-Confidence': 'sample_id_confidence',
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

        row_data = []
        json_resp = {}
        for field in page.form.fields:
            if field.key:
                json_key = field.key.text
                json_key1 = '{}-Confidence'.format(field.key.text)
            else:
                json_key = ""
                json_key1 = '-Confidence'
            if field.value:
                json_val = field.value.text
                json_val1 = field.value.confidence
            else:
                json_val = ""
                json_val1 = ""

            if json_key in ref_field_names:
                json_resp[ref_field_names[json_key]] = json_val

            if json_key1 in ref_field_names:
                json_resp[ref_field_names[json_key1]] = json_val1

        for table in page.tables:
            csv_data = []
            for row in table.rows:
                csv_row = []
                for cell in row.cells:
                    csv_row.append(cell.text.strip())
                csv_data.append(csv_row)

            print(csv_data)

            if 'Criteria' in csv_data[0]:
                for i in range(1, len(csv_data)):
                    for j in range(1, len(csv_data[i])):
                        json_key = '{}-{}'.format(csv_data[i][0], csv_data[0][j])
                        json_val = '{}'.format(csv_data[i][j])
                        if json_key in ref_field_names:
                            json_resp[ref_field_names[json_key]] = json_val

            elif 'Other tests done' in csv_data[0]:
                for i in range(1, len(csv_data)):
                    for j in range(0, len(csv_data[i])):
                        if csv_data[i][j] in ref_field_names:
                            json_key = '{}'.format(csv_data[i][j])
                            json_val = ''
                            try:
                                k = j + 1
                                json_val = '{}'.format(csv_data[i][k])
                            except Exception as e:
                                print(e)
                            json_resp[ref_field_names[json_key]] = json_val

            else:
                for i in range(1, len(csv_data)):
                    if csv_data[i]:
                        for j in range(0, len(csv_data[i])):
                            if csv_data[i][j] in ref_field_names:
                                json_key = csv_data[i][j]
                                for k in range(j, len(csv_data[i])):
                                    if csv_data[i][k].strip() == 'SELECTED,':
                                        json_resp[ref_field_names[json_key]] = csv_data[0][k]
                                        break

        json_resp['filename'] = self.document_name.split('/')[-1]
        json_resp['final_path'] = 'https://test-textract-bucket1.s3.ap-south-1.amazonaws.com/processed/{}'.format(
            self.document_name.split('/')[-1])
        # print(jsonResp)

        header_row = ['filename', 'sample_id', 'sample_id_confidence', 'sample_collected_date',
                      'sample_collected_date_confidence', 'year_of_birth', 'year_of_birth_confidence', 'age',
                      'age_confidence', 'sex', 'sex_confidence', 'ethnicity', 'ethnicity_confidence', 'height',
                      'height_confidence', 'weight', 'weight_confidence', 'previously_diagnosed',
                      'previously_diagnosed_confidence', 'previously_hostpitalized',
                      'previously_hostpitalized_confidence', 'pulse_rate', 'pulse_rate_confidence', 'respritory_rate',
                      'respritory_rate_confidence', 'blood_pressure', 'blood_pressure_confidence',
                      'date_of_fever_onset', 'date_of_fever_onset_confidence', 'temperature', 'temperature_confidence',
                      'headache', 'retrorbital_pain', 'runny_nose', 'difficulty_breathing', 'intercostal_pain', 'cough',
                      'loss_of_appetite', 'nausea', 'vomiting', 'abdominal_pain', 'back_pain', 'muscle_ache',
                      'joint_ache', 'bleeding_gums', 'bleeding_nose', 'vomiting_blood', 'blood_in_stool',
                      'blood_in_urine', 'increased_menstrual_flow', 'Inter Menstrual Bleeding', 'flushed_face',
                      'sunken_eyes', 'mucosal_petechiae', 'ecchymoses', 'petechiae', 'rash', 'erythematous_rash',
                      'abdominal_tenderness', 'abdominal_distension', 'ascites', 'hepatomegaly_size',
                      'pleural_effusion', 'platelets_admission', 'platelets_lowest', 'platelets_on_discharge',
                      'Haematocrit_addmission', 'haematocrit_lowest', 'haematocrit_on_discharge',
                      'haemoglobin_admission', 'haemoglobin_lowest', 'haemoglobin_on_discharge', 'leucocytes_admission',
                      'leucocytes_lowest', 'leucocytes_on_discharge', 'neutrophils_admission', 'neutrophils_lowest',
                      'neutrophils_on_discharge', 'lymphocytes_admission', 'lymphocytes_lowest',
                      'lymphocytes_on_discharge', 'eosinophils_admission', 'eosinophils_lowest',
                      'eosinophils_on_discharge', 'albumin_admission', 'albumin_lowest', 'albumin_on_discharge',
                      'ast_admission', 'ast_lowest', 'ast_on_discharge', 'alt_admission', 'alt_lowest',
                      'alt_on_discharge', 'bilirubin_admission', 'bilirubin_lowest', 'bilirubin_on_discharge',
                      'xray_admission', 'xray_lowest', 'xray_on_discharge', 'other_tests_done', 'serum_protein',
                      'serum_calcium', 'total_cholesterol', 'ultrasound_findings', 'presumptive_diagnosis',
                      'presumptive_diagnosis_confidence', 'other_comments', 'final_path']
        for ele in header_row:
            if ele in json_resp:
                row_data.append(json_resp[ele])
            else:
                row_data.append("")

        FileHelper.write_csv_to_s3(header_row, row_data)
        # FileHelper.writeCSV("{}-page-{}-tables.csv".format(self.fileName, p), fieldNames, [rowData])
        # FileHelper.writeCSVRaw("{}-page-{}-tables.csv".format(self.fileName, p), csvData)

    def run(self):
        if not self.document.pages:
            return

        print("Total Pages in Document: {}".format(len(self.document.pages)))

        p = 1
        for page in self.document.pages:
            self._output_form(page)
            p = p + 1


if __name__ == '__main__':
    OutputGenerator(response="", document_name="").run()
