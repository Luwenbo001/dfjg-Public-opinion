import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional, List, Tuple

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import OpenAI
from datetime import datetime

log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, f"client_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
log_file = open(log_file_path, 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

load_dotenv()

api_key = os.getenv("QWEN_API_KEY")
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "qwen-plus"


def print_to_terminal(message):
    original_stdout = sys.stdout  # 保存当前的标准输出
    sys.stdout = sys.__stdout__    # 恢复原始的标准输出
    print(message)                 # 输出到终端
    sys.stdout = log_file          # 恢复到日志文件输出

class MCPClient:
    def __init__(self):
        """初始化MCP客户端"""
        print("[INFO]正在加载环境变量...")
        self.exit_stack = AsyncExitStack()
        self.openai_api_key = api_key
        self.base_url = base_url
        self.model = model
        print("[INFO]环境变量加载完成")
        if not self.openai_api_key:
            raise ValueError("[ERR]未找到OpenAI API Key，请在.env文件中设置OPENAI_API_KEY")

        print("[INFO]OpenAI API 客户端初始化中...")
        self.client = OpenAI(
            api_key=self.openai_api_key,
            base_url=self.base_url,
        )
        self.sessions: List[ClientSession] = []
        print("[INFO]OpenAI API 客户端初始化完成")

    async def connect_to_server(self, server_configs: List[Tuple[str, str]]):
        """连接到多个SSE MCP服务器并启动对应脚本"""
        print("[INFO]正在连接到MCP服务器...")

        for script_path, port in server_configs:
            if not script_path.endswith(".py"):
                raise ValueError(f"[ERR]不支持的脚本类型: {script_path}，请使用Python脚本")

            print(f"[INFO]启动服务器脚本: {script_path}，端口: {port}")
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path, port,
                stdout=log_file,
                stderr=log_file
            )
            await asyncio.sleep(1)

            url = f"http://localhost:{port}/sse"
            print(f"[INFO]尝试连接到SSE服务器: {url}")
            streams = await self.exit_stack.enter_async_context(sse_client(url=url))
            session = await self.exit_stack.enter_async_context(ClientSession(*streams))
            await session.initialize()
            self.sessions.append(session)
            print(f"[INFO]连接并初始化成功: {script_path}@{port}")

        print("\n已连接到服务器，支持以下工具:")
        for i, session in enumerate(self.sessions):
            response = await session.list_tools()
            tools = [tool.name for tool in response.tools]
            print(f"  来自服务 {i+1} 的工具: {tools}")

    async def process_query(self, query):
        """处理用户输入，调用大模型和工具"""
        messages = [{"role": "system", "content": "你是一个舆情分析助手，当user让你完成今日的舆情分析时，你需要调用start_crawler工具获取微博舆情数据，然后调用wb_analysis_tool工具进行分析，最后输出wb_analysis_tool返回的舆情简报。"},
                    {"role": "user", "content": query}]

        all_tools = []
        tool_session_map = {}

        print("[INFO]正在收集所有工具...")
        for session in self.sessions:
            response = await session.list_tools()
            for tool in response.tools:
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                })
                tool_session_map[tool.name] = session
        print(f"[INFO]工具收集完毕: {[tool['function']['name'] for tool in all_tools]}")

        # 循环处理调用
        while True:
            print("[INFO]正在调用大模型...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=all_tools
            )
            print(f"[INFO]大模型调用完成，响应: {response}")
            content = response.choices[0].message
            messages.append(content.model_dump())
            print(f"[INFO]messages 更新: {messages}")
            print(f"[INFO]大模型返回: {content}")

            if hasattr(content, 'tool_calls') and content.tool_calls:
                tool_call = content.tool_calls[0]
                function_name = tool_call.function.name
                function_args = tool_call.function.arguments
                session = tool_session_map.get(function_name)
                if session is None:
                    raise ValueError(f"[ERR]未找到工具 {function_name} 的会话")

                print(f"[INFO]调用工具: {function_name} 参数: {function_args}")
                result = await session.call_tool(function_name, json.loads(function_args))
                
                # messages.append(content.message.model_dump())
                print(f"[INFO]result: {result}")
                print(f"[INFO]工具 {function_name} 返回结果: {result}")
                if function_name == "wb_analysis_tool":
                    if result:
                        json_str = result.content[0].text
                        data = json.loads(json_str)
                        print_to_terminal(f"简报生成成功: {data.get('summary')}")
                        return
                result_dict = result.content[0].text

                messages.append({
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(result_dict, ensure_ascii=False)
                })
            else:
                print(f"[INFO]大模型未调用任何工具，content: {content}")
                if content:
                    messages.append({
                        "role": "assistant",
                        "content": content
                    })
                    continue
                else:
                    print("[INFO]大模型没有返回内容，结束循环")
                    break

    async def chat_loop(self):
        """交互式聊天循环"""
        print_to_terminal("欢迎使用MCP客户端！输入你的问题，或输入 'quit' 退出。请输入你的问题：")
        while True:
            try:
                query = input().strip()
                if query.lower() == "quit":
                    break
                await self.process_query(query)
            except Exception as e:
                print(f"[ERR]发生异常：{e}")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 3 or len(sys.argv[1:]) % 2 != 0:
        print("请按 server.py 端口号 的格式提供参数，例如: python client_sse.py server1.py 8000 server2.py 8001")
        sys.exit(1)

    script_args = sys.argv[1:]
    server_configs = [(script_args[i], script_args[i + 1]) for i in range(0, len(script_args), 2)]

    client = MCPClient()

    try:
        await client.connect_to_server(server_configs)
        await client.chat_loop()
    finally:
        await client.cleanup()
        print("[INFO]MCP 客户端已关闭")

if __name__ == "__main__":
    asyncio.run(main())

# python client.py crawl_server.py 8000 analysis_server.py 8001
