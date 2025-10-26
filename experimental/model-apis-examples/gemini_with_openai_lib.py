import argparse
from enum import StrEnum
import json
import os
from openai import OpenAI
from openai.types.chat.chat_completion import ChatCompletion


def parse_args():
    parser = argparse.ArgumentParser(description='Chat with AI models')
    parser.add_argument('--provider', 
                       choices=['google', 'openrouter'], 
                       default='openrouter',
                       help='AI provider to use')
    parser.add_argument('--model',
                       default='google/gemini-2.5-flash',
                       help='AI model to use')
    return parser.parse_args()


class ProviderEnum(StrEnum):
    google = 'google'
    openrouter = 'openrouter'


args = parse_args()
print(args.provider == ProviderEnum.google.value)
print(ProviderEnum.google.value)
if args.provider == ProviderEnum.google.value:
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
else:
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = "https://openrouter.ai/api/v1"


print(f"Using provider: {args.provider}")
print(f"Using api key: {api_key}")
print(f"Using base url: {base_url}")
print(f"Using model: {args.model}")

client = OpenAI(
#您可以直接在此处设置api_key，您可以在其中读取不同的环境变量。
# api_key=os.getenv("GEMINI_API_KEY"),
# 如果您想让OpenAI直接读取环境变量，您需要在您的环境中设置OPENAI_API_KEY
# 由于 OPENAI_API_KEY 是 OpenAI SDK 读取的环境变量。
# Gemini 基本 URL
＃base_url =“https://generativelanguage.googleapis.com/v1beta/openai/"
    api_key=api_key,
    base_url=base_url
)

response: ChatCompletion = client.chat.completions.create(
    model=args.model,
# 这是控制gemini-2。5-flash推理的唯一方法。
# 此删除参数以调用gemini-2。5闪时消除推理。
    reasoning_effort="low",
    max_completion_tokens=4096,
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a plot summary of a novel on AI causing human extinction"
        }
    ],
＃额外的身体={
# '额外身材': {
＃     “谷歌”： {
#“思考配置”：{
# # 这似乎不起作用，设置 >0 值并不能引发进行推理或思考。
#“思考预算”：1024，
# # 这似乎也不起作用，将其转为False不会产生不包含推理细节
# #（如果 Reasoning_effort 设置为“低”、“中”、“高”其中之一）。
#“include_thoughts”：正确
# }
# }
# }
# }
)
# Pretty print 响应
response_dict = response.model_dump()
print(json.dumps(response_dict, indent=4))
