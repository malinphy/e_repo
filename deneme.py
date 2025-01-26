print('start of the script')
import pandas as pd
from utils.prompts import generate_test_prompt
import time

df = pd.read_csv(r"E:\PERSONAL_PROJ\e_repo\data\df_task_1_test_cleaned.csv",nrows=10)
df['text'] = df.apply(generate_test_prompt, axis=1)

model_name = "meta-llama/Meta-Llama-3-8B-Instruct"
# llm = LLM(model_name, trust_remote_code = True,max_model_len = 2014)
# sampling_params = SamplingParams(temperature = 0.0, max_tokens = 15)


# start_time = time.time()
# response = llm.generate(df['text'], sampling_params)
# end_time = time.time()
# print('BATCHED ELAPSED TIME:', end_time-start_time)

# df['response'] = response

df.to_csv(r"E:\PERSONAL_PROJ\e_repo\data\df_task_2_test_cleaned.csv")

print('end of the script')