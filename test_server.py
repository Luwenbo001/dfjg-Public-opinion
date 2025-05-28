# test_server_sse.py
import asyncio
import os
import sys
from mcp.server import FastMCP
from datetime import datetime

# 允许通过命令行参数设置端口号
if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    port = 8000  # 默认端口

# 创建 FastMCP 实例，指定传输为 SSE
mcp = FastMCP("CrawlerServer", port=port)
log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"test_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

@mcp.tool()
async def test_tool():
    """运行爬虫脚本并记录输出"""

    print(f"[MCP] 日志输出到: {log_file}")

    with open(log_file, 'w', encoding='utf-8') as logfile:
        print("[MCP] 启动爬虫进程...", file=logfile)
        cmd = ["scrapy", "crawl", "search"]
        cwd = os.path.join(os.getcwd(), "weibo-search")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=logfile,
            stderr=logfile
        )
        await process.wait()
        print("[MCP] 子进程完成！", file=logfile)

    return {"status": "爬虫完成", "log_file": log_file}

if __name__ == "__main__":
    # 启动 SSE 服务
    mcp.run(transport="sse")
