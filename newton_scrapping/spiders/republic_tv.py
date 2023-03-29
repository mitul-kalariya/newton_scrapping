import json
import scrapy
import logging
from dateutil import parser
from datetime import datetime
from newton_scrapping import exceptions
from newton_scrapping.constants import (
        TODAYS_DATE,
        SITEMAP_SCHEMA,
        LOGGER
    )
from newton_scrapping.utils import (
    create_log_file,
    export_data_to_json_file,
    validate_sitemap_date_range,
)


class RepublicTvSpider(scrapy.Spider):
    name = "republic_tv"

    def __init__(self, type=None, start_date=None, url=None, end_date=None, **kwargs):
        """
        Initializes a web scraper object with the given parameters.

        Parameters:
        type (str): The type of scraping to be performed. Either "sitemap" or "article".
        start_date (str): The start date of the time period to be scraped, in the format "YYYY-MM-DD".
        url (str): The URL of the article to be scraped. Required if type is "article".
        end_date (str): The end date of the time period to be scraped, in the format "YYYY-MM-DD".
        **kwargs: Additional keyword arguments to be passed to the superclass constructor.

        Raises:
        ValueError: If the start_date and/or end_date are invalid.
        InvalidDateRange: If the start_date is later than the end_date.
        Exception: If no URL is provided when type is "article".
        """
        super().__init__(**kwargs)
        self.start_urls = []
        self.articles = []
        self.type = type.lower()

        create_log_file()



        self.start_date = (
            datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        )

        self.end_date = (
            datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
        )

        if self.type == "sitemap":
            self.start_urls.append(SITEMAP_SCHEMA)
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

    def parse(self, response):
        """
        Parses the response obtained from a website.

        Yields:
        scrapy.Request: A new request object to be sent to the website.

        Raises:
        BaseException: If an error occurs during parsing.
        """
        LOGGER.info("Parse function called on %s", response.url)
        if self.type == "sitemap":
            if self.start_date and self.end_date:
                LOGGER.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_sitemap_by_dates)
            else:
                LOGGER.info("Parse function called on %s", response.url)
                yield scrapy.Request(response.url, callback=self.parse_sitemap_by_dates)
        elif self.type == "article":
            try:
                LOGGER.debug("Parse function called on %s", response.url)
                response_json = self.response_json(response)
                response_data = utils.response_data(response)
                data = {
                    "raw_response": {
                        "content_type": "text/html; charset=utf-8",
                        "content": response.css("html").get(),
                    },
                }
                if response_json:
                    data["parsed_json"] = response_json
                if response_data:
                    response_data["country"] = ["India"]
                    response_data["time_scraped"] = [str(datetime.now())]
                    data["parsed_data"] = response_data

                self.articles.append(data)

            except BaseException as e:
                print(f"Error: {e}")
                LOGGER.error(f"{e}")

    def parse_sitemap_by_dates(self, response):
        """
        Parses a webpage response object and yields scrapy requests for each sitemap XML link found.

        Yields:
        scrapy.Request: A scrapy request object for each sitemap XML link found in the response.
        """
        LOGGER.info("Parse by date at %s", response.url)
        if "sitemap.xml" in response.url:
            for sitemap in response.xpath(
                "//sitemap:loc/text()",
                namespaces={"sitemap": SITEMAP_SCHEMA},
            ):
                if sitemap.get().endswith(".xml"):
                    for link in sitemap.getall():
                        if self.start_date is None and self.end_date is None:
                            if TODAYS_DATE.replace("-", "") in link:
                                yield scrapy.Request(link, callback=self.parse_sitemap)
                        else:
                            yield scrapy.Request(link, callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        """
        Parses a sitemap and sends requests to scrape each of the links.

        Yields:
        scrapy.Request: A request to scrape each of the links in the sitemap.

        Notes:
        The sitemap must be in the XML format specified by the sitemaps.org protocol.
        The function extracts the links from the sitemap
            and sends a request to scrape each link using the `parse_sitemap_link_title` callback method.
        The function also extracts the publication date of the sitemap, if available, and
            passes it along as a meta parameter in each request.
        """
        namespaces = {"n": SITEMAP_SCHEMA}
        links = response.xpath("//n:url/n:loc/text()", namespaces=namespaces).getall()
        published_at = response.xpath('//*[local-name()="lastmod"]/text()').get()
        published_date = parser.parse(published_at).date() if published_at else None
        for link in links:
            yield scrapy.Request(
                link,
                callback=self.parse_sitemap_link_title,
                meta={"link": link, "published_date": published_date},
            )

    def parse_sitemap_link_title(self, response):
        """
        Parses the link, title, and published date from a sitemap page.

        Notes:
        - Adds the parsed data to the scraper's sitemap_data list.
        - Skips the link if the published date is outside the scraper's specified date range.
        """
        link = response.meta["link"]
        published_date = response.meta["published_date"]
        title = response.css(".story-title::text").get().strip()

        if self.start_date and published_date < self.start_date:
            return
        if self.end_date and published_date > self.end_date:
            return

        data = {"link": link, "title": title}

        self.articles.append(data)

    def response_json(self, response) -> dict:
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
        parsing_dict = {}
        main_data = self.get_main(response)
        if main_data:
            parsing_dict["main"] = main_data

        misc_data = self.get_misc(response)
        if misc_data:
            parsing_dict["misc"] = misc_data

        return parsing_dict

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
            LOGGER.error(f"{e}")
            print(f"Error while getting main: {e}")

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
            LOGGER.error(f"{e}")
            print(f"Error while getting misc: {e}")

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