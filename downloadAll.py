import logging
from typing import List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from downloadTheColumn import download_column


class AllArticlesDownloader:
    """
    Downloads all articles from the Learn Python the Hard Way website.
    """

    def __init__(self, start_url: str = "https://learn.lianglianglee.com/%e4%b8%93%e6%a0%8f",
                 base_url: str = "https://learn.lianglianglee.com/"):
        self.base_url = base_url
        self.start_url = start_url
        self.logger = None
        self.setup_logging()

    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler("AllArticles_download.log", encoding='utf-8')
            ]
        )
        self.logger = logging.getLogger(__name__)

    def get_course_list(self) -> List[str]:
        """获取所有课程的URL列表"""
        self.logger.info("Fetching course list...")
        try:
            response = requests.get(self.start_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # 找到课程列表所在的元素
            course_list = soup.find('div', {'class': 'book-menu uncollapsible'})
            if not course_list:
                self.logger.error("Book menu not found")
                return []

            # 找到所有的ul.uncollapsible，选择最后一个
            all_uls = course_list.find_all('ul', {'class': 'uncollapsible'})
            if not all_uls:
                self.logger.error("No uncollapsible lists found")
                return []

            # 使用最后一个ul，因为它包含文章列表
            effective_ul = all_uls[-1]

            # 提取每个课程的URL以及名称
            courses = []
            for course_url in effective_ul.find_all('a', {'class': 'menu-item'}):
                href = course_url.get('href')
                id = course_url.get('id')
                if href:
                    full_url = urljoin(self.base_url, href)
                    first_course_url = self.get_first_article_url(full_url)
                    if id:
                        courses.append([id, first_course_url])
                    else:
                        self.logger.error(f"Invalid href for course with id: {id}")
                else:
                    self.logger.error(f"Invalid id for course with href: {href}")

            if not courses:
                self.logger.error("No courses found")
            else:
                self.logger.info(f"Found {len(courses)} courses")
            return courses

        except Exception as e:
            self.logger.error(f"Error occurred while fetching course list: {e}")
            return []

    def get_first_article_url(self, course_url: str) -> str:
        """获取课程的第一篇文章的URL"""
        self.logger.info(f"Fetching first article URL for course: {course_url}")
        try:
            response = requests.get(course_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            book_post = soup.find('div', {'class': 'book-post'})
            if not book_post:
                self.logger.error("book-post not found")
                return ''

            # 找到所有的div，选择最后一个
            all_divs = book_post.find_all('div')
            if not all_divs:
                self.logger.error("No uncollapsible lists found")
                return ''

            # 使用最后一个ul，因为它包含文章列表
            right_div = all_divs[-1]
            ul = right_div.find('ul')

            articles = []
            for item in ul.find_all('a'):
                href = item.get('href')
                if href and '捐赠' not in href:  # 排除捐赠链接
                    full_url = urljoin(self.base_url, href)
                    articles.append(full_url)

            if not articles:
                self.logger.warning("No articles found in the last uncollapsible list")
            else:
                self.logger.info(f"Found {len(articles)} articles in the column")
            return articles[0]

        except Exception as e:
            self.logger.error(f"Failed to get first article url: {e}")
            return ''


def save_all_articles_url(start_url: str = "https://learn.lianglianglee.com/%e4%b8%93%e6%a0%8f",
                          base_url: str = "https://learn.lianglianglee.com/"):
    """下载所有文章"""
    downloader = AllArticlesDownloader(start_url, base_url)
    course_list = downloader.get_course_list()

    # 检查 course_list 是否为空
    if not course_list:
        print("课程列表为空")
        exit(0)

    # 保存course_list
    with open('course_list.txt.bak', 'w') as f:
        for course in course_list:
            course = list(course)
            f.write(f"{course[0]}****{course[1]}\n")



def download_all_articles():
    # 读取课程列表
    with open('course_list.txt', 'r') as f:
        course_list = [line.strip().split('****') for line in f.readlines()]
        for course in course_list:
            download_column(course[0], course[1])

if __name__ == '__main__':
    download_all_articles()
