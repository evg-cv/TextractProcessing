import boto3
import time
from Helper import DocProcessor, FileHelper, OutputGenerator
import json
import os

def lambda_handler(event, context):
    print(event)
    bucket_name = 'medical-documents-storage'
    if 'source' in event and event['source'] == 'aws.s3':
        if 'detail' in event:
            if 'requestParameters' in event['detail']:
                key = event['detail']['requestParameters']['key']
                document_name = key
   

    
                # Get document textracted
                dp = DocProcessor(document_name)
                response = dp.run()
                print("Recieved Textract response...")
            
                name, ext = FileHelper.getFileNameAndExtension(document_name)
                opg = OutputGenerator(response, document_name)
                opg.run()
                
                s3 = boto3.resource('s3')
                copy_source = {
                    'Bucket': bucket_name,
                    'Key': document_name
                }
                copy_key = 'processed/{}'.format(document_name.split("/")[-1])
                s3.meta.client.copy(copy_source, bucket_name, copy_key)
                
                client = boto3.client('s3')
                response = client.delete_object(
                    Bucket=bucket_name,
                    Key=document_name,
                )

                return {
                    "body": json.dumps("{} Textracted Successfully.".format(document_name)),
                    "statusCode": 200
                }
                
                
    return {
        "body": json.dumps("No document found."),
        "statusCode": 200
    }