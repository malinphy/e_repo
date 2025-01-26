import pandas as pd
import sagemaker
import boto3
from sagemaker.amazon.amazon_estimator import get_image_uri 
from sagemaker.session import s3_input, Session
import urllib

import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
import os
import boto3

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

bucket_name = "esci-aws"
prefix = "clean_data/df_task_1_test_cleaned.csv"
local_dir = "data"

download_all_files(bucket_name, prefix, local_dir)        