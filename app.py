import os
import boto3
import json
import fitz
# remove
import configparser

from helper import DocProcessor, OutputGenerator
from settings import BUCKET_NAME, JSON_PREFIX, DOWNLOAD_DIR, TEST_PREFIX, DOCUMENT_NAME, CONFIG_FILE_PATH

# ------------------ remove
params = configparser.ConfigParser()
params.read(CONFIG_FILE_PATH)
# -----------------------------


def run(document_name):
    # ---------- remove ---------------
    client = boto3.client('s3', aws_access_key_id=params.get("DEFAULT", "access_key_id"),
                          aws_secret_access_key=params.get("DEFAULT", "secret_access_key"))
    s3 = boto3.resource('s3', aws_access_key_id=params.get("DEFAULT", "access_key_id"),
                        aws_secret_access_key=params.get("DEFAULT", "secret_access_key"))
    # -----------------

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
    client.download_file(BUCKET_NAME, TEST_PREFIX + "/" + document_name, file_path)
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
        dp = DocProcessor(TEST_PREFIX + "/" + document_name)
        response = dp.run()
        # ---------- remove ----------
        json_file_path = "/media/main/Data/Task/TextractProcessing/test_json/" + document_json_name
        file = open(json_file_path, "w")
        file.write(json.dumps(response, indent=4))
        file.close()
        # ---------------------------------------
        s3object = s3.Object(BUCKET_NAME, JSON_PREFIX + "/" + document_json_name)
        s3object.put(
            Body=(bytes(json.dumps(response, indent=4).encode('UTF-8')))
        )

    print("[INFO] Received Textract response...")
    # name, ext = FileHelper.get_file_name_and_extension(document_name)
    opg = OutputGenerator(response, document_name)
    opg.run(frame_path)

    copy_source = {
        'Bucket': BUCKET_NAME,
        'Key': TEST_PREFIX + "/" + document_name
    }
    copy_key = f'test_processed/{document_name.split("/")[-1]}'
    s3.meta.client.copy(copy_source, BUCKET_NAME, copy_key)

    client.delete_object(
        Bucket=BUCKET_NAME,
        Key=TEST_PREFIX + "/" + document_name,
    )

    return {
        "body": json.dumps(f"{document_name} Textracted Successfully."),
        "statusCode": 200
    }


if __name__ == '__main__':
    run(document_name=DOCUMENT_NAME)
