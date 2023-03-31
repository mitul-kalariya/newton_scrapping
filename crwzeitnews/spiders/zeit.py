import scrapy
import logging
import time
from datetime import datetime
from lxml import etree
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crwzeitnews import exceptions
from scrapy.loader import ItemLoader
from scrapy.selector import Selector
from crwzeitnews.constant import TODAYS_DATE, LOGGER
from abc import ABC, abstractmethod
from crwzeitnews.items import ArticleData
from crwzeitnews.utils import (
    create_log_file,
    validate_sitemap_date_range,
    export_data_to_json_file,
    get_raw_response,
    get_parsed_data,
    get_parsed_json,
    # remove_popup
)
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


class BaseSpider(ABC):
    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        pass

class ZeitSpider(scrapy.Spider,BaseSpider):
    name = "zeit"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, *args, **kwargs):
        """
        A spider to crawl globalnews.ca for news articles. The spider can be initialized with two modes:
        1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca
        and scrape articles within a specified date range.
        2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

        Attributes:
            name (str): The name of the spider.
            type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
            start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
            url (str): The URL of the article to scrape in article mode.
        """
        super(ZeitSpider,self).__init__(*args,**kwargs)

        self.output_callback = kwargs.get('args', {}).get('callback', None)
        self.start_urls = []
        self.articles = []
        self.article_url = url
        self.type = type.lower()
        create_log_file()

        if self.type == "sitemap":
            self.start_urls.append("https://www.zeit.de/gsitemaps/index.xml")
            self.start_date = (
                datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
            )
            self.end_date = (
                datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
            )
            validate_sitemap_date_range(start_date, end_date)

        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                LOGGER.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

    def remove_popup(self, response) -> None:

        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(response.url)
        time.sleep(5)
        try:
            element =  WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    '//*[@id="main"]/div/article/div/section[2]/div[1]/div')))
            banner_button = driver.find_element(By.XPATH, '//*[@id="main"]/div/article/div/section[2]/div[1]/div')
            if element:
                banner_button.click()
                article = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    '//article[@id="js-article"]')))
                if article:
            
                    html_string = driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
                    selector = Selector(text=html_string)
                    self.parse_article(selector)
                    driver.quit()

        except BaseException as e:
            print("/n/n",e)
            driver.quit()

      

    def parse(self,response):

        if self.type == "sitemap":
            if self.start_date and self.end_date:
                LOGGER.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_sitemap)
            else:
                yield scrapy.Request(response.url, callback=self.parse_sitemap)

        elif self.type == "article":
            self.remove_popup(response)
            articledata_loader = ItemLoader(item=ArticleData(), response=response)
            return articledata_loader.item


    def parse_sitemap(self, response: str) -> None:
        pass

    def parse_sitemap_article(self, response: str) -> None:
        pass


    def parse_article(self, response) -> list:
        """
        Parses the article data from the response object and returns it as a dictionary.

        Args:
            response (scrapy.http.Response): The response object containing the article data.

        Returns:
            dict: A dictionary containing the parsed article data, including the raw response,
            parsed JSON, and parsed data, along with additional information such as the country
            and time scraped.
        """
        articledata_loader = ItemLoader(item=ArticleData(), response=response)
        raw_response = get_raw_response(response)
        response_json = get_parsed_json(response)
        response_data = get_parsed_data(response)
        

        articledata_loader.add_value("raw_response", raw_response)
        articledata_loader.add_value(
            "parsed_json",
            response_json,
        )
        articledata_loader.add_value("parsed_data", response_data)

        self.articles.append(dict(articledata_loader.load_item()))



    def closed(self, reason: any) -> None:
        """
        store all scrapped data into json file with given date in filename
        Args:
            response: generated response
        Raises:
            ValueError if not provided
        Returns:
            Values of parameters
        """

        try:
            if self.output_callback is not None:
                self.output_callback(self.articles)
            
            if not self.articles:
                self.log("No articles or sitemap url scrapped.", level=logging.INFO)
            else:
                export_data_to_json_file(self.type, self.articles, self.name)
        except Exception as exception:
            exceptions.ExportOutputFileException(
                f"Error occurred while writing json file{str(exception)} - {reason}"
            )
            self.log(
                f"Error occurred while writing json file{str(exception)} - {reason}",
                level=logging.ERROR,
            )



if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(ZeitSpider)
    process.start()
