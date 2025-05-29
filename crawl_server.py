import os, re, time, subprocess
import sys
import asyncio
from datetime import datetime
from mcp.server import FastMCP

# 参数配置
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
mcp = FastMCP("CrawlerServer", port=port)


BASE_DIR = os.getcwd()
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file_path = os.path.join(LOG_DIR, f"crawl_{timestamp}.log")
log_file = open(log_file_path, 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

result_file_path = os.path.join(BASE_DIR, "weibo-search", "结果文件","东方精工","东方精工.csv")

def update_settings(file_path: str):
    """更新settings.py中的START_DATE和END_DATE"""
    if not os.path.exists(file_path):
        # log.append(f"[ERR] 配置文件不存在: {file_path}")
        print(f"[ERR] 配置文件不存在: {file_path}")
        return False

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    yesterday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    date_str = f"'{yesterday}'"

    pattern = lambda var: re.compile(rf"^\s*{var}\s*=\s*\S+", re.MULTILINE)
    new_content = pattern("START_DATE").sub(f"START_DATE = {date_str}", content)
    new_content = pattern("END_DATE").sub(f"END_DATE = {date_str}", new_content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    # log.append(f"[INFO] 成功更新 START_DATE 和 END_DATE 为 {date_str}")
    print(f"[INFO] 成功更新 START_DATE 和 END_DATE 为 {date_str}")
    return True

def run_spider(crawl_dir: str) -> bool:
    """运行爬虫脚本（同步）"""
    try:
        cmd = ["scrapy", "crawl", "search"]
        # log.append(f" 执行命令: {' '.join(cmd)}")
        print(f"[INFO] 执行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=crawl_dir, stdout=log_file, stderr=log_file, timeout=60)
        # log.append(f"[INFO] 爬虫执行完成，状态码：{result.returncode}")
        print(f"[INFO] 爬虫执行完成，状态码：{result.returncode}")
        return result.returncode == 0
    except Exception as e:
        # log.append(f"[ERR] 执行爬虫失败: {str(e)}")
        print(f"[ERR] 执行爬虫失败: {str(e)}")
        return False

@mcp.tool()
async def start_crawler():
    """
    调用本地的爬虫服务获取微博平台当天的企业相关舆情信息
    :return: dict 包括爬虫状态"status"和结果csv文件路径""result_file_path"
    """
    settings_path = os.path.join(BASE_DIR, "weibo-search", "weibo", "settings.py")
    crawl_dir = os.path.join(BASE_DIR, "weibo-search")

    # 1. 修改设置文件
    success_config = update_settings(settings_path)
    if not success_config:
        print("[ERR]设置文件更新失败")
        return {
            "status": "failed",
        }
    
    # 2. 运行爬虫
    success = await asyncio.to_thread(run_spider, crawl_dir)

    if not success:
        print("[ERR]爬虫执行失败")
        return {
            "status": "failed",
        }
    return {
        "status": "success" if success else "failed",
        "result_file_path": result_file_path,
    }

if __name__ == "__main__":
    mcp.run(transport="sse")
