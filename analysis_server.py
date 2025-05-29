import os
import sys
import csv
import asyncio
import httpx
import subprocess
from datetime import datetime
from mcp.server import FastMCP
from openai import OpenAI

# 初始化 MCP server（SSE模式）
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
mcp = FastMCP("AnalysisServer", port=port)

# 设置日志目录
BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = os.path.join(LOG_DIR, f"analysis_{timestamp}.log")
log_file = open(log_file_path, 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

# 移除代理设置
os.environ.pop('http_proxy', None)
os.environ.pop('https_proxy', None)

model = "qwq-plus"  # 替换为实际模型
api_key = os.getenv("QWEN_API_KEY2")
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
company_name = "东方精工"
messages = [{'role': 'system', 'content': '你是一个舆情分析助手'}]

# 异步获取 OpenAI 客户端
# async def get_openai_client():
#     return await asyncio.to_thread(
#         OpenAI,
#         api_key=os.getenv("QWEN_API_KEY2"),
#         base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
#     )

# 分析主函数
def analysis(csv_file_path: str):
    # client = await get_openai_client()
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )
    file_path = os.path.join(BASE_DIR, "llm_stock_check.py")
    
    if not os.path.exists(file_path):
        print(f"[ERR] 分析脚本不存在: {file_path}")
        raise FileNotFoundError(f"分析脚本不存在: {file_path}")

    try:
        # cmd = ['conda', 'run', '-n', 'wb', 'python', file_path, csv_file_path]
        # print(f"[INFO] 执行分析脚本: {' '.join(cmd)}")
        # result = subprocess.run(
        #     cmd,
        #     cwd=os.path.dirname(file_path),
        #     check=True,
        #     text=True,
        #     capture_output=True
        # )

        cmd = ['python', file_path, csv_file_path]
        print(f"[INFO] 执行分析脚本: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(file_path),
            stdout=log_file,
            stderr=log_file,
        )
        print("[INFO] 分析脚本执行成功")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERR] 分析脚本执行失败: {e}")
        print(f"[ERR] 错误输出: {e.stderr}")
        raise

    analysis_file = csv_file_path.replace('.csv', '_output.csv')
    result_text = ""
    try:
        with open(analysis_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                result_text += ",".join(map(str, row)) + "\n"
    except FileNotFoundError:
        print(f"[ERR] 分析结果文件不存在: {analysis_file}")
        raise

    messages.append({
        "role": "user",
        "content": f"我将发送给你一段文字，内容为爬虫收集到的今天的关于{company_name}这家公司的互联网发言和大模型作出的关于这则发言是否对公司产生影响的判断。你需要总结成一篇300字左右的简报。\n{result_text.strip()}"
    })

    reasoning_content = ""
    answer_content = ""
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )

        for chunk in completion:
            if not chunk.choices:
                print(f"[WARN] 空响应 chunk: {chunk}")
                continue
            delta = chunk.choices[0].delta
            if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                reasoning_content += delta.reasoning_content
            elif hasattr(delta, 'content') and delta.content:
                answer_content += delta.content

        print("[INFO] 简报生成成功")
        print("[INFO] 模型思考:", reasoning_content)
        print("[INFO] 模型回复:", answer_content)

    except Exception as e:
        print(f"[ERR] 简报生成失败: {e}")
        raise

    return answer_content.strip()

@mcp.tool()
async def wb_analysis_tool(csv_file_path: str):
    """
    调用大模型分析 CSV 舆情信息，返回简报文本
    :param csv_file_path: CSV 文件路径
    :return: 简报字符串
    """
    try:
        # success = await asyncio.to_thread(run_spider, crawl_dir)
        # result = await analysis(csv_file_path)
        result = await asyncio.to_thread(analysis, csv_file_path)
        return {
            "status": "success",
            "summary": result,
            "log_file": log_file_path,
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "log_file": log_file_path,
        }

if __name__ == "__main__":
    mcp.run(transport="sse")
