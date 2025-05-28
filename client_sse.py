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
log_file = open(log_file_path, 'w')
sys.stdout = log_file
sys.stderr = log_file  # 同样重定向stderr

load_dotenv()

api_key = os.getenv("QWEN_API_KEY")
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
model = "qwen-plus"

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

            # 启动服务器脚本
            print(f"[INFO]启动服务器脚本: {script_path}，端口: {port}")
            process = await asyncio.create_subprocess_exec(
                sys.executable, script_path, port,
                stdout=log_file,
                stderr=log_file
            )
            await asyncio.sleep(1)  # 给服务器一些时间启动

            # SSE连接到服务器
            url = f"http://localhost:{port}/sse"
            print(f"[INFO]尝试连接到SSE服务器: {url}")
            streams = await self.exit_stack.enter_async_context(sse_client(url=url))
            session = await self.exit_stack.enter_async_context(ClientSession(*streams))
            await session.initialize()
            self.sessions.append(session)
            print(f"[INFO]连接并初始化成功: {script_path}@{port}")

        # 打印所有工具
        print("\n已连接到服务器，支持以下工具:")
        for i, session in enumerate(self.sessions):
            response = await session.list_tools()
            tools = [tool.name for tool in response.tools]
            print(f"来自服务 {i+1} 的工具: {tools}")

    async def work(self):
        """执行工作"""
        print("[INFO]正在执行工作...")
        all_tools = []
        tool_session_map = {}

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

        print(f"[INFO]所有工具获取完成: {all_tools}")

        function_name = "test_tool"
        function_args = "{}"
        session = tool_session_map.get(function_name)
        if session:
            response = await session.call_tool(
                function_name,
                json.loads(function_args),
            )
            print(f"[INFO]调用结果: {response}")
        else:
            print(f"[ERR]找不到工具 {function_name}")

        print("[INFO]工作完成")

    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 3 or len(sys.argv[1:]) % 2 != 0:
        print("请按 server.py 端口号 的格式提供参数，例如: python client.py server1.py 8000 server2.py 8001")
        sys.exit(1)

    script_args = sys.argv[1:]
    server_configs = [(script_args[i], script_args[i + 1]) for i in range(0, len(script_args), 2)]

    client = MCPClient()

    try:
        await client.connect_to_server(server_configs)
        await client.work()
    except Exception as e:
        print(f"连接到 MCP 服务器失败: {e}")
        sys.exit(1)
    finally:
        await client.cleanup()
        print("[INFO]MCP 客户端已关闭")

if __name__ == "__main__":
    asyncio.run(main())

# python client_sse.py test_server.py 8000