import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, unquote
from pathlib import Path
import logging
import html2text
import time
from typing import Optional, List
from urllib.parse import urljoin


class ColumnDownloader:
    def __init__(self, column_name: str, first_article_url: str, base_url: str = "https://learn.lianglianglee.com/"):
        self.logger = None
        self.column_name = column_name
        self.first_article_url = first_article_url
        self.base_url = base_url
        self.output_dir = Path(column_name)
        self.setup_logging()

    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f"{self.column_name}_download.log", encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def create_directories(self):
        """创建专栏目录和assets子目录"""
        self.output_dir.mkdir(exist_ok=True)
        assets_dir = self.output_dir / 'assets'
        assets_dir.mkdir(exist_ok=True)
        self.logger.info(f"Created directory structure for column: {self.column_name}")


class ArticleProcessor:
    def __init__(self, url: str, output_dir: Path, base_url: str):
        self.url = url
        self.output_dir = output_dir
        self.base_url = base_url
        self.assets_dir = output_dir / 'assets'
        self.logger = logging.getLogger(__name__)

    def fetch_page(self) -> Optional[BeautifulSoup]:
        """获取并解析网页内容"""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch page {self.url}: {e}")
            return None

    def get_title(self, soup: BeautifulSoup) -> str:
        """提取文章标题"""
        try:
            title = soup.find('h1', {'id': 'title'}).text.strip()
            # 移除标题中的非法字符
            title = "".join(c for c in title if c.isalnum() or c.isspace() or c in '-_')
            return title
        except AttributeError:
            self.logger.warning("Title not found, using timestamp")
            return f"article_{int(time.time())}"

    def get_next_page_url(self, soup: BeautifulSoup) -> Optional[str]:
        """获取下一页的URL"""
        next_page_div = soup.find('div', {'id': 'nextPage'})
        if next_page_div and next_page_div.find('a'):
            href = next_page_div.find('a').get('href')
            if href:
                # 解码URL并拼接完整地址
                decoded_href = unquote(href)
                full_url = urljoin(self.base_url, decoded_href)
                self.logger.info(f"Found next page URL: {full_url}")
                return full_url
        self.logger.info("No next page found")
        return None

    def clean_content(self, article_content):
        """清理不需要的内容"""
        first_div = article_content.find('div', recursive=False)
        if first_div and first_div.get('align') == 'center':
            div_text = first_div.get_text(strip=True)
            google_notice = "因收到Google相关通知，网站将会择期关闭"

            if google_notice in div_text:
                first_div.decompose()
                self.logger.info("Removed Google notice div")
            else:
                self.logger.info("First div found but doesn't contain Google notice")
        return article_content

    def download_image(self, img_url: str, filename: str) -> bool:
        """下载图片到assets目录"""
        try:
            img_path = self.assets_dir / filename
            response = requests.get(img_url, timeout=10)
            response.raise_for_status()

            with open(img_path, 'wb') as img_file:
                img_file.write(response.content)
            return True
        except Exception as e:
            self.logger.error(f"Failed to download image {img_url}: {e}")
            return False

    def process_content(self, article_content) -> str:
        """处理文章内容"""
        cleaned_content = self.clean_content(article_content)

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0

        markdown_content = h.handle(str(cleaned_content))

        for img in cleaned_content.find_all('img'):
            img_url = urljoin(self.url, img.get('src', ''))
            img_filename = os.path.basename(img_url)

            if self.download_image(img_url, img_filename):
                relative_path = f"./assets/{img_filename}"
                markdown_content = markdown_content.replace(
                    img['src'],
                    relative_path.replace('\\', '/')
                )

        return markdown_content

    def save_markdown(self, title: str, content: str) -> bool:
        """保存Markdown文件"""
        try:
            file_path = self.output_dir / f"{title}.md"
            with open(file_path, 'w', encoding='utf-8') as md_file:
                md_file.write(content)
            self.logger.info(f"Saved article: {file_path}")
            return True
        except IOError as e:
            self.logger.error(f"Failed to save markdown file: {e}")
            return False

    def process_article(self) -> Optional[str]:
        """处理单篇文章，返回下一页URL"""
        soup = self.fetch_page()
        if not soup:
            return None

        title = self.get_title(soup)
        article_content = soup.find('div', {'class': 'book-post'})

        if not article_content:
            self.logger.error("Article content not found")
            return None

        markdown_content = self.process_content(article_content)
        if self.save_markdown(title, markdown_content):
            return self.get_next_page_url(soup)
        return None


def download_column(column_name: str, first_article_url: str):
    """下载整个专栏的文章"""
    downloader = ColumnDownloader(column_name, first_article_url)
    downloader.create_directories()

    current_url = first_article_url
    processed_urls = set()  # 防止循环引用

    while current_url and current_url not in processed_urls:
        downloader.logger.info(f"Processing article: {current_url}")
        processor = ArticleProcessor(current_url, downloader.output_dir, downloader.base_url)

        processed_urls.add(current_url)
        current_url = processor.process_article()

        if current_url:
            downloader.logger.info("Waiting before processing next article...")
            time.sleep(2)  # 添加延时，避免请求过于频繁

    downloader.logger.info("Column download completed!")


if __name__ == "__main__":
    COLUMN_NAME = input("请输入专栏名称\n")
    FIRST_ARTICLE_URL = input("请输入第一篇文章地址\n")

    download_column(COLUMN_NAME, FIRST_ARTICLE_URL)