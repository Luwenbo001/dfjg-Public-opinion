import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from typing import Optional, List

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, stdio_client
from openai import OpenAI

sys.stdout.reconfigure(encoding='utf-8')
os.environ['PYTHONIOENCODING'] = 'utf-8'

load_dotenv()

api_key=os.getenv("QWEN_API_KEY")
base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
model="qwen-plus"

class MCPClient:
    def __init__(self):
        """初始化MCP客户端"""
        print("✅正在加载环境变量...")
        self.exit_stack = AsyncExitStack()
        self.openai_api_key = api_key
        self.base_url = base_url
        self.model = model
        print(self.model)
        print("✅环境变量加载完成")
        if not self.openai_api_key:
            raise ValueError("❌未找到OpenAI API Key，请在.env文件中设置OPENAI_API_KEY")

        # self.client = OpenAI(api_key=self.openai_api_key, base_url=self.base_url)
        self.client = OpenAI(
            api_key=os.getenv("QWEN_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        print("✅OpenAI API 客户端初始化中...")
        self.session: Optional[ClientSession] = None
        print("✅OpenAI API 客户端初始化完成")
 

    async def connect_to_server(self, server_script_paths: List[str]):
        """连接到多个MCP服务器"""
        self.sessions = []
        self.stdio_servers = []
        self.write_functions = []
        
        print("✅正在连接到MCP服务器...")

        for script_path in server_script_paths:
            is_python = script_path.endswith('.py')
            is_js = script_path.endswith('.js')
            if not is_python and not is_js:
                raise ValueError(f"❌不支持的脚本类型: {script_path}，请使用Python或JavaScript脚本")

            command = "python" if is_python else "node"
            server_params = StdioServerParameters(
                command=command,
                args=[script_path],
                env=None,
            )

            # 启动 MCP 服务器并建立通信
            print(f"✅正在连接到MCP服务器: {script_path}...")
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            stdio, write = stdio_transport
            self.stdio_servers.append(stdio)
            self.write_functions.append(write)
            print(f"✅成功连接到MCP服务器: {script_path}")

            # 每个服务端创建自己的会话
            print(f"✅正在创建会话:...")
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            print(f"session赋值成功: {session}")
            await session.initialize()
            print(f"✅会话初始化成功: {session}")
            self.sessions.append(session)
            print(f"✅会话创建成功: {session}")

        # 打印所有工具
        print("\n已连接到服务器，支持以下工具:")
        for i, session in enumerate(self.sessions):
            response = await session.list_tools()
            tools = [tool.name for tool in response.tools]
            print(f"  🛠️ 来自服务 {i+1} 的工具: {tools}")
    async def work(self):
        """执行工作"""
        print("✅正在执行工作...")
        # 例如调用工具、处理数据等
        all_tools = []
        tool_session_map = {}
        for session in self.sessions:
            print(f"✅正在获取服务端 {session} 的工具...")
            response = await session.list_tools()
            print(f"✅服务端 {session} 的工具获取完成: {response}")
            print(f"✅获取到的工具: {response.tools}")
            for tool in response.tools:
                print('type(tool.name):', type(tool.name))
                print('type(tool.description):', type(tool.description))
                print('type(tool.inputSchema):', type(tool.inputSchema),tool.inputSchema)
                print('type(tool.inputSchema["properties"]):', type(tool.inputSchema['properties']),tool.inputSchema['properties'])
                all_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    }
                })
                tool_session_map[tool.name] = session  # 记录每个工具属于哪个 session
                print(f"✅工具 {tool.name} 映射到会话 {session}")
        print(f"✅所有工具获取完成: {all_tools}")
        print(f"✅工具与会话映射: {tool_session_map}")

        function_name = "wb_crawl_tool"
        function_args = "{}"
        session = tool_session_map.get(function_name)
        print(f"✅正在调用工具 {function_name}，会话: {session}")
        await session.call_tool(
            function_name,
            json.loads(function_args),
        )
        print("✅工作完成")
    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()

async def main():
    if len(sys.argv) < 2:
        print("请提供至少一个 MCP 服务器脚本路径作为参数")
        sys.exit(1)
    
    print("正在加载环境变量...")
    client = MCPClient()
    print("正在连接到 MCP 服务器...")
    
    try:
        await client.connect_to_server(sys.argv[1:])
        await client.work()
    except Exception as e:
        print(f"连接到 MCP 服务器失败: {e}")
        sys.exit(1)
    finally:
        await client.cleanup()
        print("✅MCP 客户端已关闭")
    

if __name__ == "__main__":
    asyncio.run(main())

# python client.py weather_server.py wb_crawl_server.py wb_analysis_server.py