import boto3
from botocore.client import Config
import os
import csv
import time
from trp import *
import json
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
    def getClient(self, name, awsRegion):
        config = Config(
            retries = dict(
                max_attempts = 30
            )
        )
        return boto3.client(name, region_name=awsRegion, config=config)

class FileHelper:
    @staticmethod
    def getFileNameAndExtension(filePath):
        basename = os.path.basename(filePath)
        dn, dext = os.path.splitext(basename)
        return (dn, dext[1:])

    @staticmethod
    def getFileExtension(fileName):
        ext = fileName.split(".")[-1]
        return ext


    @staticmethod
    def writeCSV(fileName, fieldNames, csvData):
        with open(fileName, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldNames)
            writer.writeheader()

            for item in csvData:
                i = 0
                row = {}
                for value in item:
                    row[fieldNames[i]] = value
                    i = i + 1
                writer.writerow(row)

    @staticmethod
    def writeCSVRaw(fileName, csvData):
        with open(fileName, 'w') as csv_file:
            writer = csv.writer(csv_file)
            for item in csvData:
                writer.writerow(item)

    @staticmethod
    def writeCSVToS3(header_row, rowData):
        #print(header_row)
        #print(rowData)
        prefix = 'GS Clinical Data Current as of'
        today = datetime.today().strftime('%Y-%m-%d')

        inp = Input()
        bucket_name = inp.bucketName
        s3Client =  AwsHelper().getClient('s3', inp.awsRegion)
        res = s3Client.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

        fileName = '{} {}.csv'.format(prefix, today)
        tmpFileName = '/tmp/{}'.format(fileName)

        if 'Contents' in res:
            Keys = res['Contents']
            for key in Keys:
                pathArr = key['Key'].split("/")
                pathArr.reverse()
                tmpFileName = '/tmp/{}'.format(pathArr[0])
                with open(tmpFileName, 'wb') as f:
                    s3Client.download_fileobj(bucket_name, key['Key'], f)
                    f.close()
                    
                response = s3Client.delete_object(
                    Bucket=bucket_name,
                    Key=key['Key'],
                )

        else:
            with open(tmpFileName, 'w') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=header_row)
                writer.writeheader()
                csv_file.close()

        with open(tmpFileName, 'a') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=header_row)
            for item in [rowData]:
                i = 0
                row = {}
                for value in item:
                    row[header_row[i]] = value
                    i = i + 1
                writer.writerow(row)

            csv_file.close()

        s3 = boto3.resource('s3')
        s3.Object(bucket_name, "{}".format(fileName)).upload_file(tmpFileName)

class PDFProcessor:
    def __init__(self, inputParameters):
        self.inputParameters = inputParameters

    def _startJob(self):
        response = None
        client = AwsHelper().getClient('textract', self.inputParameters.awsRegion)
        if(not self.inputParameters.detectForms and not self.inputParameters.detectTables):
            response = client.start_document_text_detection(
            DocumentLocation={
                'S3Object': {
                    'Bucket': self.inputParameters.bucketName,
                    'Name': self.inputParameters.fileName
                }
            })
        else:
            features  = []
            if(self.inputParameters.detectTables):
                features.append("TABLES")
            if(self.inputParameters.detectForms):
                features.append("FORMS")

            response = client.start_document_analysis(
            DocumentLocation={
                'S3Object': {
                    'Bucket': self.inputParameters.bucketName,
                    'Name': self.inputParameters.fileName
                }
            },
            FeatureTypes=features
            )

        return response["JobId"]

    def _isJobComplete(self, jobId):
        time.sleep(5)
        client = AwsHelper().getClient('textract', self.inputParameters.awsRegion)
        if(not self.inputParameters.detectForms and not self.inputParameters.detectTables):
            response = client.get_document_text_detection(JobId=jobId)
        else:
            response = client.get_document_analysis(JobId=jobId)
        status = response["JobStatus"]
        print(status)

        while(status == "IN_PROGRESS"):
            time.sleep(5)
            if(not self.inputParameters.detectForms and not self.inputParameters.detectTables):
                response = client.get_document_text_detection(JobId=jobId)
            else:
                response = client.get_document_analysis(JobId=jobId)
            status = response["JobStatus"]
            print(status)

        return status

    def _getJobResults(self, jobId):

        pages = []

        time.sleep(5)

        client = AwsHelper().getClient('textract', self.inputParameters.awsRegion)
        if(not self.inputParameters.detectForms and not self.inputParameters.detectTables):
            response = client.get_document_text_detection(JobId=jobId)
        else:
            response = client.get_document_analysis(JobId=jobId)
        pages.append(response)
        print("Resultset page recieved: {}".format(len(pages)))
        nextToken = None
        if('NextToken' in response):
            nextToken = response['NextToken']
            #print("Next token: {}".format(nextToken))

        while(nextToken):
            time.sleep(5)

            if(not self.inputParameters.detectForms and not self.inputParameters.detectTables):
                response = client.get_document_text_detection(JobId=jobId, NextToken=nextToken)
            else:
                response = client.get_document_analysis(JobId=jobId, NextToken=nextToken)

            pages.append(response)
            print("Resultset page recieved: {}".format(len(pages)))
            nextToken = None
            if('NextToken' in response):
                nextToken = response['NextToken']
                #print("Next token: {}".format(nextToken))

            #if(len(pages) > 20):
            #    break

        return pages

    def run(self):
        jobId = self._startJob()
        print("Started Asyc Job with Id: {}".format(jobId))
        status = self._isJobComplete(jobId)
        if(status == "SUCCEEDED"):
            responsePages = self._getJobResults(jobId)
            return responsePages


class DocProcessor:
    def __init__(self, fileName):
        inp = Input()

        ext = FileHelper.getFileExtension(fileName)
        if ext != 'pdf':
            raise Exception('PDF document is required.')

        inp.fileName = fileName
        self.inputParameters = inp


    def run(self):
        print("Starting Textract..")

        pdfProc = PDFProcessor(self.inputParameters)
        output = pdfProc.run()
        self.output = output

        return self.output


class OutputGenerator:
    def __init__(self, response, document_name):
        self.response = response
        self.forms = True
        self.tables = True

        self.document = Document(self.response)
        self.document_name = document_name

    def _outputForm(self, page, p):
        refFieldNames = {'fileName': 'filename', 'GRI ID:': 'sample_id', 'GRI ID:-Confidence': 'sample_id_confidence', 'Sample Collection Date:': 'sample_collected_date', 'Sample Collection Date:-Confidence': 'sample_collected_date_confidence', 'Date of Birth (dd/mm/yy):': 'year_of_birth', 'Date of Birth (dd/mm/yy):-Confidence': 'year_of_birth_confidence', 'Age:': 'age', 'Age:-Confidence': 'age_confidence', 'Sex:': 'sex', 'Sex:-Confidence': 'sex_confidence', 'Ethnicity:': 'ethnicity', 'Ethnicity:-Confidence': 'ethnicity_confidence', 'Height:': 'height', 'Height:-Confidence': 'height_confidence', 'Weight:': 'weight', 'Weight:-Confidence': 'weight_confidence', 'Has the patient been diagnosed with Dengue previously?': 'previously_diagnosed', 'Has the patient been diagnosed with Dengue previously?-Confidence': 'previously_diagnosed_confidence', 'Has the patient been hospitalized for previous dengue infections?': 'previously_hostpitalized', 'Has the patient been hospitalized for previous dengue infections?-Confidence': 'previously_hostpitalized_confidence', 'Pulse Rate:': 'pulse_rate', 'Pulse Rate:-Confidence': 'pulse_rate_confidence', 'Respiratory Rate:': 'respritory_rate', 'Respiratory Rate:-Confidence': 'respritory_rate_confidence', 'Bp S/D': 'blood_pressure', 'Bp S/D-Confidence': 'blood_pressure_confidence', 'Date of Fever Onset:': 'date_of_fever_onset', 'Date of Fever Onset:-Confidence': 'date_of_fever_onset_confidence', 'Temp:': 'temperature', 'Temp:-Confidence': 'temperature_confidence', 'Headache': 'headache', 'Retrorbital Pain': 'retrorbital_pain', 'Runny nose': 'runny_nose', 'Difficulty in breathing': 'difficulty_breathing', 'Intercostal Pain': 'intercostal_pain', 'Cough': 'cough', 'Loss of Appetite': 'loss_of_appetite', 'Nausea': 'nausea', 'Vomiting': 'vomiting', 'Abdominal Pain': 'abdominal_pain', 'Back Pain': 'back_pain', 'Muscle ache': 'muscle_ache', 'Joint ache': 'joint_ache', 'Bleeding gums': 'bleeding_gums', 'Bleeding nose': 'bleeding_nose', 'Vomiting Blood': 'vomiting_blood', 'Blood in stool': 'blood_in_stool', 'Blood in urine': 'blood_in_urine', 'Increased menstrual flow': 'increased_menstrual_flow', 'Inter-menstrual bleeding': 'Inter Menstrual Bleeding', 'Flushed Face': 'flushed_face', 'Sunken eyes': 'sunken_eyes', 'Mucosal Petechiae': 'mucosal_petechiae', 'Ecchymoses': 'ecchymoses', 'Petechiae': 'petechiae', 'Rash': 'rash', 'Erythematous Rash': 'erythematous_rash', 'Abdominal Tenderness': 'abdominal_tenderness', 'Abdominal Distension': 'abdominal_distension', 'Ascites': 'ascites', 'Hepatomegaly (size in cm)': 'hepatomegaly_size', 'Pleural effusion': 'pleural_effusion', 'Platelets (x1000)-Upon Admission': 'platelets_admission', 'Platelets (x1000)-2nd Recording (highest where applicable)': 'platelets_lowest', 'Platelets (x1000)-On Discharge': 'platelets_on_discharge', 'Haematocrit (%)-Upon Admission': 'Haematocrit_addmission', 'Haematocrit (%)-2nd Recording (highest where applicable)': 'haematocrit_lowest', 'Haematocrit (%)-On Discharge': 'haematocrit_on_discharge', 'Haemoglobin (g/dl)-Upon Admission': 'haemoglobin_admission', 'Haemoglobin (g/dl)-2nd Recording (highest where applicable)': 'haemoglobin_lowest', 'Haemoglobin (g/dl)-On Discharge': 'haemoglobin_on_discharge', 'Leukocytes (x1000)-Upon Admission': 'leucocytes_admission', 'Leukocytes (x1000)-2nd Recording (highest where applicable)': 'leucocytes_lowest', 'Leukocytes (x1000)-On Discharge': 'leucocytes_on_discharge', 'Neutrophils (%)-Upon Admission': 'neutrophils_admission', 'Neutrophils (%)-2nd Recording (highest where applicable)': 'neutrophils_lowest', 'Neutrophils (%)-On Discharge': 'neutrophils_on_discharge', 'Lymphocytes (%)-Upon Admission': 'lymphocytes_admission', 'Lymphocytes (%)-2nd Recording (highest where applicable)': 'lymphocytes_lowest', 'Lymphocytes (%)-On Discharge': 'lymphocytes_on_discharge', 'Eosinophil (%)-Upon Admission': 'eosinophils_admission', 'Eosinophil (%)-2nd Recording (highest where applicable)': 'eosinophils_lowest', 'Eosinophil (%)-On Discharge': 'eosinophils_on_discharge', 'Albumin (g/dl)-Upon Admission': 'albumin_admission', 'Albumin (g/dl)-2nd Recording (highest where applicable)': 'albumin_lowest', 'Albumin (g/dl)-On Discharge': 'albumin_on_discharge', 'AST (U/L)-Upon Admission': 'ast_admission', 'AST (U/L)-2nd Recording (highest where applicable)': 'ast_lowest', 'AST (U/L)-On Discharge': 'ast_on_discharge', 'ALT (U/L)-Upon Admission': 'alt_admission', 'ALT (U/L)-2nd Recording (highest where applicable)': 'alt_lowest', 'ALT (U/L)-On Discharge': 'alt_on_discharge', 'Bilirubin (mg/dl)-Upon Admission': 'bilirubin_admission', 'Bilirubin (mg/dl)-2nd Recording (highest where applicable)': 'bilirubin_lowest', 'Bilirubin (mg/dl)-On Discharge': 'bilirubin_on_discharge', 'X-Ray-Upon Admission': 'xray_admission', 'X-Ray-2nd Recording (highest where applicable)': 'xray_lowest', 'X-Ray-On Discharge': 'xray_on_discharge', 'Other tests done': 'other_tests_done', 'Serum Protein': 'serum_protein', 'Serum Calcium': 'serum_calcium', 'Total Cholesterol': 'total_cholesterol', 'Ultrasound Findings': 'ultrasound_findings', 'Presumptive Diagnosis': 'presumptive_diagnosis', 'Presumptive Diagnosis-Confidence': 'presumptive_diagnosis_confidence', 'Other comments': 'other_comments'}
        
        rowData = []
        fieldNames = []
        jsonResp = {}
        for field in page.form.fields:
            if(field.key):
                jsonKey = field.key.text
                jsonKey1 = '{}-Confidence'.format(field.key.text)
            else:
                jsonKey = ""
                jsonKey1 = '-Confidence'
            if(field.value):
                jsonVal = field.value.text
                jsonVal1 = field.value.confidence
            else:
                jsonVal = ""
                jsonVal1 = ""

            if jsonKey in refFieldNames:
                jsonResp[refFieldNames[jsonKey]] = jsonVal

            if jsonKey1 in refFieldNames:
                jsonResp[refFieldNames[jsonKey1]] = jsonVal1
            
        for table in page.tables:
            csvData = []
            for row in table.rows:
                csvRow  = []
                for cell in row.cells:
                    csvRow.append(cell.text.strip())
                csvData.append(csvRow)

            print(csvData)

            if 'Criteria' in csvData[0]:
                for i in range(1, len(csvData)):
                    for j in range(1, len(csvData[i])):
                        jsonKey = '{}-{}'.format(csvData[i][0], csvData[0][j])
                        jsonVal = '{}'.format(csvData[i][j])
                        if jsonKey in refFieldNames:
                                    jsonResp[refFieldNames[jsonKey]] = jsonVal

            elif 'Other tests done' in csvData[0]:
                for i in range(1, len(csvData)):
                    k = 0
                    for j in range(0, len(csvData[i])):
                        if csvData[i][j] in refFieldNames:
                            jsonKey = '{}'.format(csvData[i][j])
                            jsonVal = ''
                            try:
                                k = j + 1
                                jsonVal = '{}'.format(csvData[i][k])
                            except Exception as e:
                                print(e)
                            jsonResp[refFieldNames[jsonKey]] = jsonVal

            else:
                for i in range(1, len(csvData)):
                    if csvData[i]:
                        for j in range(0, len(csvData[i])):
                            if csvData[i][j] in refFieldNames:
                                jsonKey = csvData[i][j]
                                for k in range(j, len(csvData[i])):
                                    if csvData[i][k].strip() == 'SELECTED,':
                                        jsonVal = csvData[0][k]
                                        jsonResp[refFieldNames[jsonKey]] = csvData[0][k]
                                        break

        jsonResp['filename'] = self.document_name.split('/')[-1]
        jsonResp['final_path'] = 'https://test-textract-bucket1.s3.ap-south-1.amazonaws.com/processed/{}'.format(self.document_name.split('/')[-1])
        #print(jsonResp)
        
        header_row = ['filename', 'sample_id', 'sample_id_confidence', 'sample_collected_date', 'sample_collected_date_confidence', 'year_of_birth', 'year_of_birth_confidence', 'age', 'age_confidence', 'sex', 'sex_confidence', 'ethnicity', 'ethnicity_confidence', 'height', 'height_confidence', 'weight', 'weight_confidence', 'previously_diagnosed', 'previously_diagnosed_confidence', 'previously_hostpitalized', 'previously_hostpitalized_confidence', 'pulse_rate', 'pulse_rate_confidence', 'respritory_rate', 'respritory_rate_confidence', 'blood_pressure', 'blood_pressure_confidence', 'date_of_fever_onset', 'date_of_fever_onset_confidence', 'temperature', 'temperature_confidence', 'headache', 'retrorbital_pain', 'runny_nose', 'difficulty_breathing', 'intercostal_pain', 'cough', 'loss_of_appetite', 'nausea', 'vomiting', 'abdominal_pain', 'back_pain', 'muscle_ache', 'joint_ache', 'bleeding_gums', 'bleeding_nose', 'vomiting_blood', 'blood_in_stool', 'blood_in_urine', 'increased_menstrual_flow', 'Inter Menstrual Bleeding', 'flushed_face', 'sunken_eyes', 'mucosal_petechiae', 'ecchymoses', 'petechiae', 'rash', 'erythematous_rash', 'abdominal_tenderness', 'abdominal_distension', 'ascites', 'hepatomegaly_size', 'pleural_effusion', 'platelets_admission', 'platelets_lowest', 'platelets_on_discharge', 'Haematocrit_addmission', 'haematocrit_lowest', 'haematocrit_on_discharge', 'haemoglobin_admission', 'haemoglobin_lowest', 'haemoglobin_on_discharge', 'leucocytes_admission', 'leucocytes_lowest', 'leucocytes_on_discharge', 'neutrophils_admission', 'neutrophils_lowest', 'neutrophils_on_discharge', 'lymphocytes_admission', 'lymphocytes_lowest', 'lymphocytes_on_discharge', 'eosinophils_admission', 'eosinophils_lowest', 'eosinophils_on_discharge', 'albumin_admission', 'albumin_lowest', 'albumin_on_discharge', 'ast_admission', 'ast_lowest', 'ast_on_discharge', 'alt_admission', 'alt_lowest', 'alt_on_discharge', 'bilirubin_admission', 'bilirubin_lowest', 'bilirubin_on_discharge', 'xray_admission', 'xray_lowest', 'xray_on_discharge', 'other_tests_done', 'serum_protein', 'serum_calcium', 'total_cholesterol', 'ultrasound_findings', 'presumptive_diagnosis', 'presumptive_diagnosis_confidence', 'other_comments', 'final_path']
        for ele in header_row:
            if ele in jsonResp:
                rowData.append(jsonResp[ele])
            else:
                rowData.append("")

        FileHelper.writeCSVToS3(header_row, rowData)
        #FileHelper.writeCSV("{}-page-{}-tables.csv".format(self.fileName, p), fieldNames, [rowData])
        #FileHelper.writeCSVRaw("{}-page-{}-tables.csv".format(self.fileName, p), csvData)

    def run(self):
        if(not self.document.pages):
            return

        print("Total Pages in Document: {}".format(len(self.document.pages)))

        p = 1
        for page in self.document.pages:
            
            self._outputForm(page, p)

            p = p + 1

    
