import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import html2text
from pathlib import Path
import logging
from typing import Optional


class HTMLToMarkdownConverter:
    def __init__(self, url: str, output_dir: str = 'output'):
        self.url = url
        self.output_dir = Path(output_dir)
        self.assets_dir = self.output_dir / 'assets'
        self.setup_logging()

    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def setup_directories(self):
        """创建必要的目录结构"""
        self.output_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)

    def fetch_page(self) -> Optional[BeautifulSoup]:
        """获取并解析网页内容"""
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.RequestException as e:
            self.logger.error(f"Failed to fetch page: {e}")
            return None

    def get_title(self, soup: BeautifulSoup) -> str:
        """提取文章标题"""
        try:
            title = soup.find('h1', {'id': 'title'}).text.strip()
            return title
        except AttributeError:
            self.logger.warning("Title not found, using default")
            return "untitled"

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


    def clean_content(self, article_content):
        """
        清理不需要的内容
        检查第一个div是否是Google通知，如果是则删除
        """
        first_div = article_content.find('div', recursive=False)
        if first_div and first_div.get('align') == 'center':
            # 获取div中的文本内容
            div_text = first_div.get_text(strip=True)
            google_notice = "因收到Google相关通知，网站将会择期关闭"

            if google_notice in div_text:
                first_div.decompose()
                self.logger.info("Removed Google notice div")
            else:
                self.logger.info("First div found but doesn't contain Google notice")
        else:
            self.logger.info("No center-aligned div found at first level")

        return article_content

    def process_content(self, article_content) -> str:
        """处理文章内容，转换为Markdown格式并处理图片"""
        cleaned_content = self.clean_content(article_content)

        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False

        markdown_content = h.handle(str(cleaned_content))

        # 处理图片
        for img in article_content.find_all('img'):
            img_url = urljoin(self.url, img.get('src', ''))
            img_filename = os.path.basename(img_url)

            if self.download_image(img_url, img_filename):
                # 使用相对路径，确保使用正斜杠
                relative_path = f"./assets/{img_filename}"
                markdown_content = markdown_content.replace(
                    img['src'],
                    relative_path.replace('\\', '/')
                )

        return markdown_content

    def save_markdown(self, title: str, content: str):
        """保存Markdown文件"""
        markdown_path = self.output_dir / f"{title}.md"
        try:
            with open(markdown_path, 'w', encoding='utf-8') as md_file:
                md_file.write(content)
            self.logger.info(f"Markdown file saved to {markdown_path}")
        except IOError as e:
            self.logger.error(f"Failed to save markdown file: {e}")

    def convert(self):
        """执行转换流程"""
        self.setup_directories()

        soup = self.fetch_page()
        if not soup:
            return

        title = self.get_title(soup)
        article_content = soup.find('div', {'class': 'book-post'})

        if not article_content:
            self.logger.error("Article content not found")
            return

        markdown_content = self.process_content(article_content)
        self.save_markdown(title, markdown_content)


def main():
    url = input("请输入文章地址：\n")
    converter = HTMLToMarkdownConverter(url)
    converter.convert()


if __name__ == "__main__":
    main()