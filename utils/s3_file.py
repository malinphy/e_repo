import pandas as pd
import sagemaker
import boto3
from sagemaker.amazon.amazon_estimator import get_image_uri 
from sagemaker.session import s3_input, Session
import urllib
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError
import os
import logging



def download_all_files(bucket_name, prefix="", local_dir="."):
    s3 = boto3.client('s3')
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=prefix)

    if 'Contents' in response:
        for obj in response['Contents']:
            key = obj['Key'] 
            local_file_path = os.path.join(local_dir, os.path.basename(key))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            s3.download_file(bucket_name, key, local_file_path)
            print(f"Downloaded: {key} to {local_file_path}")
    else:
        print("No files found.")



def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """

    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = os.path.basename(file_name)

    # Upload the file
    s3_client = boto3.client('s3')
    try:
        response = s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        logging.error(e)
        return False
    return True

# file_name = r"E:\PERSONAL_PROJ\e_repo\data\df_task_2_test_cleaned.csv" 
# bucket = "esci-aws"
# object_name = "results/df_task_2_test_cleaned.csv"
# upload_file(file_name,bucket,object_name)