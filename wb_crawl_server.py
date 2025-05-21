import json
import os
import asyncio
import re
import time
from mcp.server import FastMCP
import subprocess
import sys

mcp = FastMCP("CrawlServer")
test_output_file = "test_crawl.txt"

async def read_stream(stream, prefix, log_file):
    """异步读取流并写入日志文件"""
    try:
        while True:
            line = await stream.readline()
            if not line:
                break
            line_str = line.decode('utf-8').rstrip()
            with open(log_file, "a", encoding='utf-8') as f:
                f.write(f"[{prefix}] {line_str}\n")
    except Exception as e:
        with open(log_file, "a", encoding='utf-8') as f:
            f.write(f"[{prefix}] 读取异常: {str(e)}\n")


async def crawl():
    """
    调用本地的爬虫服务获取微博平台当天的企业相关舆情信息
    :return: CSV文件路径或None
    """
    pwd = os.getcwd()
    file_path = pwd + "/weibo-search/weibo/settings.py"
    
    with open(test_output_file, "a", encoding='utf-8') as f:
        f.write(f"当前工作目录：{pwd}\n")
        f.write(f"爬虫配置文件路径：{file_path}\n")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"爬虫配置文件不存在: {file_path}")
    
    # 读取文件内容
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write("文件内容读取成功\n")
    
    # 修正时间计算逻辑
    current_time = time.time()
    yesterday_time = current_time - 86400  # 减去一天的秒数
    new_value = time.strftime("%Y-%m-%d", time.localtime(yesterday_time))
    new_value = f"'{new_value}'"  # 添加引号以匹配文件中的格式
    with open(test_output_file, "a", encoding='utf-8') as f:
        f.write(f"当前日期：{new_value}\n")
    
    # 匹配格式为 "variable = value" 的行
    variable_name1 = "START_DATE"
    variable_name2 = "END_DATE"
    pattern1 = re.compile(
        rf'^(\s*{re.escape(variable_name1)}\s*=\s*)(\S+)(.*)$',
        re.MULTILINE
    )
    pattern2 = re.compile(
        rf'^(\s*{re.escape(variable_name2)}\s*=\s*)(\S+)(.*)$',
        re.MULTILINE
    )

    # 替换变量值
    def replace_value(match):
        return f"{match.group(1)}{new_value}{match.group(3)}"
    
    new_content, count1 = pattern1.subn(replace_value, content)
    new_content, count2 = pattern2.subn(replace_value, new_content)
    
    # 检查是否有修改
    if count1 + count2 <= 1:
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write(f"没有修改变量 {variable_name1} 和 {variable_name2} 的值\n")
        return None
    
    with open(test_output_file, "a", encoding='utf-8') as f:
        f.write(f"修改变量 {variable_name1} 和 {variable_name2} 的值成功\n")
    
    # 写入修改后的内容
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(new_content)
    
    with open(test_output_file, "a", encoding='utf-8') as f:
        f.write(f"文件内容写入成功\n")

    # 异步调用爬虫服务并等待完成
    crawl_dir = os.path.join(pwd, "weibo-search")
    process = None
    result_csv = os.path.join(pwd, "weibo-search/结果文件/东方精工/东方精工.csv")
    
    try:
        # 使用asyncio.subprocess进行异步调用
        cmd = [
            "scrapy", "crawl", "search",
            "-o", result_csv,
            "-t", "csv",
            "-s", "LOG_FILE=scrapy.log"
        ]

        
        # result = subprocess.run(
        #     cmd,
        #     cwd=crawl_dir,
        #     shell=True,
        # )
        # result = subprocess.Popen(
        #     cmd,
        #     cwd=crawl_dir,
        #     shell=True,
        #     # stdout=subprocess.PIPE,
        #     # stderr=subprocess.PIPE,
        # )
    #     with open(test_output_file, "a", encoding='utf-8') as f:
    #         f.write("存在",os.path.exists(result_csv))
    #         f.write(f"准备执行命令: {' '.join(cmd)} 在目录 {crawl_dir}\n")
    #         f.write(f"爬虫进程已启动，PID: {result.pid}\n")
    #         f.write(f"等待爬虫进程完成...\n")
    # # 直接获取返回码和输出
    #     returncode = result.returncode
    #     stdout = result.stdout
    #     stderr = result.stderr
    #     with open(test_output_file, "a", encoding='utf-8') as f:
    #         f.write("result",result)
    #         f.write(f"爬虫返回码: {returncode}\n")
    #         f.write(f"stdout: {stdout}\n")
    #         f.write(f"stderr: {stderr}\n")
        # 创建进程
        # with open(test_output_file, "a", encoding='utf-8') as f:
        #     f.write(f"准备执行命令: {' '.join(cmd)} 在目录 {crawl_dir}\n")
            
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=crawl_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        # time.sleep(10)
        
        # **关键1：启动流读取任务并绑定到异步事件循环**
        stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT", test_output_file))
        stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR", test_output_file))
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write(f"stdout err获取\n")
        # **关键2：阻塞等待子进程完成（必须用await）**
        
        # with open(test_output_file, "a", encoding='utf-8') as f:
        #     f.write(f"爬虫进程已启动，PID: {process.pid}\n")
        #     f.write(f"stdout_task: {stdout_task}\n")
        #     f.write(f"stderr_task: {stderr_task}\n")
        # returncode = await process.wait()
        
        # # **关键3：确保流读取任务完成（避免缓冲区残留）**
        # with open(test_output_file, "a", encoding='utf-8') as f:
        #     f.write(f"爬虫进程已启动，PID: {process.pid}\n")
        # await asyncio.gather(stdout_task, stderr_task)
        try:
            # 3 个任务：读 stdout、读 stderr、等进程退出，一起并行，最迟 60 秒
            await asyncio.wait_for(
                asyncio.gather(
                    stdout_task,
                    stderr_task,
                    process.wait()
                ),
                timeout=20
            )
        except asyncio.TimeoutError:
            # 超时，强杀子进程
            process.kill()
            await process.wait()
            with open(test_output_file, "a", encoding="utf-8") as f:
                f.write("⚠️ 爬虫执行超时，子进程已被强制终止\n")
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write(f"爬虫进程已启动，PID: {process.pid}\n")
            f.write(f"stdout_task: {stdout_task}\n")
            f.write(f"stderr_task: {stderr_task}\n")
        # 等待进程完成
        returncode = await process.wait()
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write(f"爬虫进程完成，返回码: {returncode}\n")
        
        # 确保所有输出都已读取完毕
        
    except Exception as e:
        raise
    #     # 异步读取标准输出和错误输出
    #     stdout_task = asyncio.create_task(read_stream(process.stdout, "STDOUT", test_output_file))
    #     stderr_task = asyncio.create_task(read_stream(process.stderr, "STDERR", test_output_file))
        
    #     # 等待进程完成或超时（设置合理的超时时间，例如3600秒）
    #     try:
    #         await asyncio.wait_for(process.wait(), timeout=60)
    #     except asyncio.TimeoutError:
    #         with open(test_output_file, "a", encoding='utf-8') as f:
    #             f.write("爬虫执行超时，将尝试终止进程\n")
    #         process.terminate()
    #         await asyncio.sleep(1)  # 给进程时间响应终止信号
    #         if process.returncode is None:
    #             with open(test_output_file, "a", encoding='utf-8') as f:
    #                 f.write("进程未响应终止信号，将强制杀死进程\n")
    #             process.kill()
    #         raise
        
    #     # 确保所有输出都已读取完毕
    #     await asyncio.gather(stdout_task, stderr_task)
        
    #     # 检查返回码
    #     with open(test_output_file, "a", encoding='utf-8') as f:
    #         f.write(f"爬虫返回码: {process.returncode}\n")
    #     if process.returncode != 0:
    #         error_msg = f"爬虫执行失败，返回码: {process.returncode}"
    #         with open(test_output_file, "a", encoding='utf-8') as f:
    #             f.write(f"{error_msg}\n")
    #         raise subprocess.CalledProcessError(process.returncode, cmd, stderr=error_msg)
        
    #     with open(test_output_file, "a", encoding='utf-8') as f:
    #         f.write(f"爬虫执行成功，返回码: {process.returncode}\n")
        
    #     # 检查结果文件是否存在
    #     if os.path.exists(result_csv):
    #         with open(test_output_file, "a", encoding='utf-8') as f:
    #             f.write(f"结果文件存在: {result_csv}\n")
    #         return result_csv
    #     else:
    #         with open(test_output_file, "a", encoding='utf-8') as f:
    #             f.write(f"警告: 结果文件不存在: {result_csv}\n")
    #             f.write(f"检查目录内容: {os.listdir(os.path.dirname(result_csv)) if os.path.exists(os.path.dirname(result_csv)) else '结果目录不存在'}\n")
    #         return None
            
    # except asyncio.CancelledError:
    #     # 处理任务取消
    #     with open(test_output_file, "a", encoding='utf-8') as f:
    #         f.write("爬虫任务被取消，尝试终止子进程...\n")
        
    #     if process and process.returncode is None:
    #         # 尝试优雅地终止进程
    #         process.terminate()
    #         try:
    #             # 等待一段时间让进程有机会自行终止
    #             await asyncio.wait_for(process.wait(), timeout=5.0)
    #             with open(test_output_file, "a", encoding='utf-8') as f:
    #                 f.write("子进程已成功终止\n")
    #         except asyncio.TimeoutError:
    #             # 如果超时，强制杀死进程
    #             process.kill()
    #             with open(test_output_file, "a", encoding='utf-8') as f:
    #                 f.write("子进程超时未响应，已强制终止\n")
        
    #     raise
    # except Exception as e:
    #     with open(test_output_file, "a", encoding='utf-8') as f:
    #         f.write(f"爬虫执行失败，错误信息：{str(e)}\n")
        
    #     # 确保在发生错误时也尝试终止进程
    #     if process and process.returncode is None:
    #         process.terminate()
    #     raise
    # finally:
    #     # 清理资源
    #     if process:
    #         # 确保所有流都已关闭
    #         if process.stdout:
    #             process.stdout.close()
    #         if process.stderr:
    #             process.stderr.close()
    
    # # 如果执行到这里，说明没有错误但结果文件不存在
    # return None

@mcp.tool()
async def wb_crawl_tool():
    """
    调用本地的爬虫服务获取微博平台当天的企业相关舆情信息
    :return: CSV文件路径或None
    """
    with open(test_output_file, "a", encoding='utf-8') as f:
        f.write(f"wb_crawl_tool函数内\n")
    result_csv = await crawl()
    
    if result_csv and os.path.exists(result_csv):
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write(f"将返回结果文件: {result_csv}\n")
        return result_csv
    else:
        with open(test_output_file, "a", encoding='utf-8') as f:
            f.write(f"无法返回有效结果文件\n")
        return None

if __name__ == "__main__":
    print("CrawlServer 启动中...")
    
    try:
        mcp.run(transport="stdio")
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在优雅地关闭服务...")
    finally:
        print("CrawlServer 已停止")