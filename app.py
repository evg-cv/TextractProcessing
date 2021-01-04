import boto3
from Helper import DocProcessor, OutputGenerator
import json


def run(document_name):
    bucket_name = 'medical-documents-storage'

    # Get document textracted
    dp = DocProcessor(document_name)
    response = dp.run()
    print("Recieved Textract response...")

    # name, ext = FileHelper.get_file_name_and_extension(document_name)
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
    client.delete_object(
        Bucket=bucket_name,
        Key=document_name,
    )

    return {
        "body": json.dumps("{} Textracted Successfully.".format(document_name)),
        "statusCode": 200
    }


if __name__ == '__main__':
    run(document_name="")
