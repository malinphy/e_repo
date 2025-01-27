print('start of the script')
import pandas as pd
from utils.prompts import generate_test_prompt
from utils.s3_file import upload_file, download_all_files
import os
from vllm import LLM, SamplingParams
import time

bucket = "esci-aws"
prefix = "clean_data/df_task_1_test_cleaned.csv"
download_dir = "data"

print('DOWNLOAD STARTED....')
download_all_files(bucket_name=bucket, prefix=prefix, local_dir=download_dir)
print('DOWNLOAD COMPLETED....')

df = pd.read_csv(r"data\df_task_1_test_cleaned.csv",nrows=100)
df['text'] = df.apply(generate_test_prompt, axis=1)

model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
llm = LLM(model_name, trust_remote_code = True,max_model_len = 2014)
sampling_params = SamplingParams(temperature = 0.0, max_tokens = 15)


start_time = time.time()
response = llm.generate(df['text'], sampling_params)
end_time = time.time()
print('BATCHED ELAPSED TIME:', end_time-start_time)

df['response'] = response

df.to_csv(r"data\df_task_2_test_cleaned.csv")

file_name = r"data\df_task_2_test_cleaned.csv" 
object_name = "results/df_task_2_test_cleaned.csv"
upload_file(file_name,bucket,object_name)


print('end of the script')