import boto3
import os
import json
import time
import fitz

from helper import DocProcessor, OutputGenerator
from settings import JSON_PREFIX, DOWNLOAD_DIR, BUCKET_NAME, DOCUMENT_PREFIX

start_time = time.time()


def lambda_handler(event, context):
    print(event)

    if 'source' in event and event['source'] == 'aws.events':
        try:
            s3 = boto3.resource('s3')
            client = boto3.client('s3')
            response = client.list_objects_v2(
                Bucket=BUCKET_NAME,
                Delimiter='/',
                Prefix=DOCUMENT_PREFIX
            )
            # print(response)

            if 'Contents' in response:
                keys = response['Contents']
                for key in keys:
                    document_name = key['Key']
                    now_time = time.time() - start_time
                    if document_name.endswith(".pdf") and now_time < 720:
                        # print(document_name)

                        # Get document textracted
                        document_json_name = document_name.replace("pdf", "json")
                        processed_files = []
                        response = client.list_objects(Bucket=BUCKET_NAME, Prefix=JSON_PREFIX)
                        for content in response.get('Contents', []):
                            obj = content.get('Key')
                            if ".json" in obj:
                                processed_files.append(obj.split("/")[1])
                        file_path = os.path.join(DOWNLOAD_DIR, document_name)
                        frame_path = os.path.join(DOWNLOAD_DIR, document_name.replace('.pdf', '.png'))
                        print(f"[INFO] {document_name} downloading...")
                        client.download_file(BUCKET_NAME, DOCUMENT_PREFIX + "/" + document_name, file_path)
                        doc = fitz.open(file_path)
                        first_page = doc[0]
                        image_matrix = fitz.Matrix(fitz.Identity)
                        image_matrix.preScale(2, 2)
                        pix = first_page.getPixmap(alpha=False, matrix=image_matrix)
                        pix.writePNG(frame_path)

                        if document_json_name in processed_files:
                            content_object = s3.Object(BUCKET_NAME, JSON_PREFIX + "/" + document_json_name)
                            file_content = content_object.get()['Body'].read().decode('utf-8')
                            response = json.loads(file_content)
                        else:
                            # Get document textracted
                            dp = DocProcessor(DOCUMENT_PREFIX + "/" + document_name)
                            response = dp.run()
                            s3object = s3.Object(BUCKET_NAME, JSON_PREFIX + "/" + document_json_name)
                            s3object.put(
                                Body=(bytes(json.dumps(response, indent=4).encode('UTF-8')))
                            )

                        print("[INFO] Received Textract response...")
                        opg = OutputGenerator(response, document_name)
                        opg.run(frame_path)

                        copy_source = {
                            'Bucket': BUCKET_NAME,
                            'Key': DOCUMENT_PREFIX + "/" + document_name
                        }
                        copy_key = f'test_processed/{document_name.split("/")[-1]}'
                        s3.meta.client.copy(copy_source, BUCKET_NAME, copy_key)

                        client.delete_object(
                            Bucket=BUCKET_NAME,
                            Key=DOCUMENT_PREFIX + "/" + document_name,
                        )

                return {
                    "body": json.dumps("Documents Textracted Successfully."),
                    "statusCode": 200
                }

        except Exception as e:
            print(e)

    return {
        "body": json.dumps("No document found."),
        "statusCode": 200
    }
