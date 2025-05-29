import os
import sys
import csv
import asyncio
import httpx
import subprocess
from datetime import datetime
from mcp.server import FastMCP
from openai import OpenAI

# 移除代理（可选）
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = os.path.join(LOG_DIR, f"llm_analysis_{timestamp}.log")
log_file = open(log_file_path, 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

# 获取命令行参数
if len(sys.argv) < 2:
    print("用法: python llm_stock_check.py <csv_file_path>")
    sys.exit(1)

csv_file_path = sys.argv[1]
csv_file_path = os.path.normpath(csv_file_path)

if not os.path.exists(csv_file_path):
    print(f"CSV 文件不存在: {csv_file_path}")
    sys.exit(1)

# 自动生成输出路径
output_file_path = csv_file_path.replace('.csv', '_output.csv')

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)
model = "qwq-plus"
company_name = "东方精工"

messages = [
    {'role': 'system', 'content': 'You are a helpful assistant.'},
    {'role': 'user', 'content': f'你需要检测下面这则来自微博的关于{company_name}公司的信息（下文用公司指代），做4个二分类任务。类别共有4类，分别是：\
    1.是否为对公司进行的负面报道、不实报道； \
    2.是否为会上存在的已经或将给公司造成不良影响的传言或信息 \
    3.是否为可能或者已经影响社会公众投资者投资取向，造成公司股价异常波动的信息 \
    4.是否为涉及公司信息披露且可能对公司股票及其衍生品交易价格产生较大影响的事\
    请你按照下面的格式输出结果：\
    1.是否为对公司进行的负面报道、不实报道：是/否 \
    2.是否为会上存在的已经或将给公司造成不良影响的传言或信息：是/否 \
    3.是否为可能或者已经影响社会公众投资者投资取向，造成公司股价异常波动的信息：是/否 \
    4.是否为涉及公司信息披露且可能对公司股票及其衍生品交易价格产生较大影响的事：是/否 '}
]

try:
    with open(csv_file_path, mode='r', encoding='utf-8') as csv_file, \
         open(output_file_path, mode='w', encoding='utf-8', newline='') as output_file:
        
        csv_reader = csv.DictReader(csv_file)
        fieldnames = ['微博正文', '思考过程', '模型回复']
        csv_writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        csv_writer.writeheader()

        for i, row in enumerate(csv_reader):
            if i == 50:
                break

            content = row['微博正文']
            messages.append({'role': 'user', 'content': content})
            reasoning_content = ""
            answer_content = ""
            is_answering = False  # 🔧修复未定义变量

            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                )

                for chunk in completion:
                    if not chunk.choices:
                        print("\nUsage:")
                        print(chunk.usage)
                        continue

                    delta = chunk.choices[0].delta

                    if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        print(delta.reasoning_content, end='', flush=True)
                        reasoning_content += delta.reasoning_content
                    elif hasattr(delta, 'content') and delta.content:
                        if not is_answering:
                            print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                            is_answering = True
                        print(delta.content, end='', flush=True)
                        answer_content += delta.content

                messages.append({"role": "assistant", "content": answer_content})
                csv_writer.writerow({'微博正文': content, '思考过程': reasoning_content, '模型回复': answer_content})
            except Exception as e:
                print(f"处理第 {i + 1} 行时出错: {e}")
except Exception as e:
    print(f"文件操作出错: {e}")
