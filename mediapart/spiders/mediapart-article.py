import re
import json
import scrapy
import requests
from lxml import html
from PIL import Image
from lxml import etree
from io import BytesIO
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


class InvalidDateRange(Exception):
    pass


class GlobalNewSpider(scrapy.Spider):
    name = "mediapart_news"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
            A spider to crawl globalnews.ca for news articles. The spider can be initialized with two modes:
            1. Sitemap mode: In this mode, the spider will crawl the news sitemap of globalnews.ca and scrape articles within a specified date range.
            2. Article mode: In this mode, the spider will scrape a single article from a specified URL.

            Attributes:
                name (str): The name of the spider.
                type (str): The mode of the spider. Possible values are 'sitemap' and 'article'.
                start_date (str): The start date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
                end_date (str): The end date of the date range for sitemap mode. Should be in 'YYYY-MM-DD' format.
                url (str): The URL of the article to scrape in article mode.
        """
        super().__init__(**kwargs)
        self.start_urls = []
        self.sitemap_data = []
        self.article_json_data = []
        self.type = type.lower()
        self.today_date = datetime.today().strftime("%Y-%m-%d")


        if self.type == "article":
            if url:
                self.start_urls.append(url)
            else:
                self.logger.error("Must have a URL to scrap")
                raise Exception("Must have a URL to scrap")

    def parse(self, response):
        """Parses the response object and extracts data based on the type of object.
            Returns:
                generator: A generator that yields scrapy.Request objects to be further parsed by other functions.
        """
        if self.type == "article":
            try:
                self.logger.debug("Parse function called on %s", response.url)
                current_url = response.request.url
                response_data = self.response_data(response)
                response_json = self.response_json(response)
                final_data = {
                    # "raw_response": {
                    #     "content_type": "text/html; charset=utf-8",
                    #     "content": response.css("html").get(),
                    # },
                    "parsed_json": response_json,
                    "parsed_data": response_data,
                }
                self.article_json_data.append(final_data)
            except BaseException as e:
                print(f"Error: {e}")
                self.logger.error(f"{e}")

    def response_json(self, response):
        """
        Extracts relevant information from a news article web page using the given
        Scrapy response object and the URL of the page.

        Args:
        - response: A Scrapy response object representing the web page to extract
          information from.
        - current_url: A string representing the URL of the web page.

        Returns:
        - A dictionary representing the extracted information from the web page.
        """
        try:
            parsed_data = {}
            main = self.get_main(response)
            if main:
                parsed_data["main"] = main

            misc = self.get_misc(response)
            if misc:
                parsed_data["misc"] = misc

            return parsed_data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def response_data(self, response):
        """
        Extracts data from a news article webpage and returns it in a dictionary format.

        Parameters:
        response (scrapy.http.Response): A scrapy response object of the news article webpage.

        Returns:
        dict: A dictionary containing the extracted data from the webpage, including:
             - 'publisher': (str) The name of the publisher of the article.
             - 'article_catagory': The region of the news that the article refers to
             - 'headline': (str) The headline of the article.
             - 'authors': (list) The list of authors of the article, if available.
             - 'published_on': (str) The date and time the article was published.
             - 'updated_on': (str) The date and time the article was last updated, if available.
             - 'text': (list) The list of text paragraphs in the article.
             - 'images': (list) The list of image URLs in the article, if available. (using bs4)

        """
        try:
            main_dict = {}
            pattern = r"[\r\n\t\"]+"
            publisher = self.extract_publisher(response)
            if publisher:
                main_dict["publisher"] = publisher

            headline = response.css("h1.l-article__title::text").getall()
            if headline:
                main_dict["title"] = headline

            authors = self.extract_author(response)
            if authors:
                main_dict["author"] = authors

            published_on = response.css(
                'div.splitter__first p'
            ).getall()
            if published_on:
                main_dict["published_at"] = [re.split("\n",published_on[1])[1].strip()]

            description = response.css("p.news__heading__top__intro::text").get()
            if description:
                main_dict["description"] = [description]

            article_text = response.css("p.dropcap-wrapper::text").getall()
            if article_text:
                main_dict["text"] = [" ".join(article_text).replace("\n", "")]

            

            return main_dict
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def get_main(self, response):
        """
        returns a list of main data available in the article from application/ld+json
        Parameters:
            response:
        Returns:
            main data
        """
        try:
            data = []
            misc = response.css('script[type="application/ld+json"]::text').getall()
            for block in misc:
                data.append(json.loads(block))
            return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def get_misc(self, response):
        """
        returns a list of misc data available in the article from application/json
        Parameters:
            response:
        Returns:
            misc data
        """
        try:
            data = []
            misc = response.css('script[type="application/json"]::text').getall()
            for block in misc:
                data.append(json.loads(block))
            return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def extract_publisher(self, response) -> list:
        """
        Extracts publisher information from the given response object and returns it as a dictionary.

        Returns:
        - A dictionary containing information about the publisher.The dictionary has the following keys:
        ---
        @id: The unique identifier for the publisher.
        @type: The type of publisher (in this case, always "NewsMediaOrganization").
        name: The name of the publisher.
        logo: Logo of the publisher as an image object
        """
        try:
            logo = response.css('head link[rel="icon"]::attr(href)').get()
            img_response = requests.get(logo)
            width, height = Image.open(BytesIO(img_response.content)).size
            a_dict = {
                "@id": "mediapart.fr",
                "@type": "NewsMediaOrganization",
                "name": "Global NEWS",
                "logo": {
                    "@type": "ImageObject",
                    "url": logo,
                    "width": {"@type": "Distance", "name": str(width) + " px"},
                    "height": {"@type": "Distance", "name": str(height) + " px"},
                },
            }
            return [a_dict]
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")

    def extract_author(self, response) -> list:
        """
        The extract_author function extracts information about the author(s)
        of an article from the given response object and returns it in the form of a list of dictionaries.

        Parameters:
            response (scrapy.http.Response): The response object containing the HTML of the article page.

        Returns:
            A list of dictionaries, where each dictionary contains information about one author.

        """
        try:
            info = response.css("div.splitter__first p a")
            pattern = r"[\r\n\t\"]+"
            data = []
            if info:
                for i in info:
                    temp_dict = {}
                    temp_dict["@type"] = "Person"
                    name = i.css("a::text").get()
                    if name:
                        name = re.sub(pattern, "", name).strip()
                        temp_dict["name"] = "".join((name.split("("))[0::-2])
                        url = i.css("a::attr(href)").get()
                        if url:
                            temp_dict["url"] = "https://www.mediapart.fr"+url
                        data.append(temp_dict)
                return data
        except BaseException as e:
            self.logger.error(f"{e}")
            print(f"Error: {e}")


    def closed(self, response):
        """
            Method called when the spider is finished scraping.
            Saves the scraped data to a JSON file with a timestamp
            in the filename.
        """
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
        if self.type == "sitemap":
            file_name = f"{self.name}-{'sitemap'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.sitemap_data, f, indent=4)

        if self.type == "article":
            file_name = f"{self.name}-{'article'}-{timestamp}.json"
            with open(file_name, "w") as f:
                json.dump(self.article_json_data, f, indent=4)




if __name__ == "__main__":
    process = CrawlerProcess(get_project_settings())
    process.crawl(GlobalNewSpider)
    process.start()