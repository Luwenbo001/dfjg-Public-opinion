import json
import os
import httpx
import subprocess
from mcp.server import FastMCP

from openai import OpenAI
import csv

import asyncio
mcp = FastMCP("AnalysisServer")
os.environ.pop('http_proxy', None)


os.environ.pop('https_proxy', None)
_openai_client = None  # 延迟初始化
model = "qwq-plus"  # 替换为你要使用的模型名称
# 初始化消息列表，包含系统消息
company_name = "东方精工"  # 替换为你要检测的公司名称

messages = [
    {'role': 'system', 'content': '你是一个舆情分析助手'}
]

# 获取异步 OpenAI 客户端
async def get_openai_client():
    # 使用to_thread将同步初始化放到单独线程中执行
    return await asyncio.to_thread(
        OpenAI,
        api_key=os.getenv("QWEN_API_KEY"),
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

async def analysis(csv_file_path: str):
    """
    根据爬虫采集好的信息通过调用大模型对其舆情分析，分析分为两个部分，第一个部分是逐条分析此条信息，第二个部分是根据上面的结果生成一篇300字左右企业舆情当日简报
    :param csv_file_path: CSV文件路径
    :return: 当日简报，类型为str
    """
    client = await get_openai_client()
    pwd = os.getcwd() 
    file_path = os.path.join(pwd, "weibo-search/analysis/llm_stock_check.py")
    
    # 检查Python文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"分析脚本不存在: {file_path}")
    
    # 调用分析脚本并等待完成
    try:
        # 获取脚本所在目录
        script_dir = os.path.dirname(file_path)
        
        # 构建完整的命令，传递CSV文件路径作为参数
        cmd = [
            'conda', 'run', '-n', 'wb',  # 使用conda环境
            'python', file_path,         # 执行Python脚本
            csv_file_path                # 传递CSV文件路径作为参数
        ]
        
        # 执行命令并等待完成
        result = subprocess.run(
            cmd, 
            cwd=script_dir,              # 设置工作目录为脚本所在目录
            check=True,                  # 命令失败时抛出异常
            text=True,                   # 以文本模式处理输出
            capture_output=True          # 捕获标准输出和错误输出
        )
        
        print("分析脚本执行成功")
    except subprocess.CalledProcessError as e:
        print(f"分析脚本执行失败: {e}")
        print("错误输出:", e.stderr)
        raise

    analysis_file = csv_file_path.replace('.csv', '_output.csv')

    # 读取csv 文件，转化为str
    result = "" 
    delimiter = ","  # 使用制表符作为分隔符
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.reader(file, delimiter=delimiter)
            for row in reader:
                result += delimiter.join(map(str, row)) + '\n'
        return result.strip()  # 去除末尾多余的换行符
    except FileNotFoundError:
        print(f"分析结果文件不存在: {analysis_file}")

    messages.append({"role": "user", "content": "我将发送给你一段文字，内容为爬虫收集到的今天的关于东方精工这家公司的互联网发言和大模型作出的关于这则发言是否对公司产生影响的判断。你需要总结成一篇300字左右的简报。"+result})
    reasoning_content = ""  # 定义完整思考过程
    answer_content = ""     # 定义完整回复
    is_answering = False
    try:
        completion = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            #incremental_output=True
        )

        for chunk in completion:
        # 如果chunk.choices为空，则打印usage
            if not chunk.choices:
                print("\nUsage:")
                print(chunk.usage)
            else:
                delta = chunk.choices[0].delta
                # 打印思考过程
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content != None:
                    # print(delta.reasoning_content, end='', flush=True)
                    reasoning_content += delta.reasoning_content
                else:
                    # 开始回复
                    # if delta.content != "" and is_answering is False:
                    #     print("\n" + "=" * 20 + "完整回复" + "=" * 20 + "\n")
                    #     is_answering = True
                    # 打印回复过程
                    # print(delta.content, end='', flush=True)
                    answer_content += delta.content
    # 将模型回复的content添加到上下文中
    except Exception as e:
        print(f"简报生成失败: {e}")
    print("简报生成成功")
    print("思考过程:", reasoning_content)
    print("模型回复:", answer_content)
    return answer_content.strip()  # 去除末尾多余的换行符

@mcp.tool()
async def wb_analysis_tool(csv_file_path: str):
    """
    根据爬虫采集好的信息通过调用大模型对其舆情分析，分析分为两个部分，第一个部分是逐条分析此条信息，第二个部分是根据上面的结果生成一篇300字左右企业舆情当日简报
    :param csv_file_path: CSV文件路径
    :return: 当日简报，类型为str
    """
    # 调用分析函数
    result = await analysis(csv_file_path)

    # # 返回分析结果
    return result
 
    return "123"  # 测试返回值
if __name__ == "__main__":
    mcp.run(transport="stdio")    