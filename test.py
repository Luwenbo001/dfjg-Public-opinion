import json
import os
import asyncio
import re
import time
from mcp.server import FastMCP
import subprocess
import sys

    # 使用asyncio.subprocess进行异步调用
async def work():
    pwd = os.getcwd()
    crawl_dir = os.path.join(pwd, "weibo-search")
    process = None
    result_csv = os.path.join(pwd, "weibo-search/结果文件/东方精工/东方精工.csv")
    cmd = [
        'scrapy', 'crawl', 'search'
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=crawl_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    
    # 异步读取标准输出和错误输出
    # stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT", test_out))
    # stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR", test_output_file))

    # 等待进程完成或超时（设置合理的超时时间，例如3600秒）
    try:
        await asyncio.wait_for(process.wait(), timeout=60)
    except asyncio.TimeoutError:
        print("爬虫执行超时，将尝试终止进程")
        process.terminate()
        await asyncio.sleep(1)  # 给进程时间响应终止信号
        if process.returncode is None:
            process.kill()
        raise

    # 确保所有输出都已读取完毕

if __name__ == "__main__":
    asyncio.run(work())