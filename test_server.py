# 测试服务器（test_server.py）
from mcp.server import FastMCP

mcp = FastMCP("TestServer")  # 服务名称需唯一

@mcp.tool()
async def test_tool():
    return "Test tool initialized"

# @mcp.on_initialized
# async def on_initialized():
#     print("Test server initialized")

if __name__ == "__main__":
    mcp.run(transport="stdio")