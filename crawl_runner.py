# weibosearch/crawl_runner.py
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from weibo.spiders.search import SearchSpider  # 替换为你的爬虫类

import logging

logging.basicConfig(
    filename="crawl_output.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
def main():
    logging.info("[INFO] 创建爬虫进程...")
    settings = get_project_settings()
    process = CrawlerProcess(settings)
    process.crawl(SearchSpider)
    logging.info("[INFO] 启动爬虫...")
    process.start()
    logging.info("[INFO] 爬虫结束")

if __name__ == "__main__":
    main()
