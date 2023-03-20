import scrapy
import re
import requests
from io import BytesIO
from PIL import Image
import json
from datetime import datetime
import pandas as pd
from datetime import date

class TagesschauSpider(scrapy.Spider):
    """
    COMMAND TO EXECUTE SITEMAP SPIDER:  scrapy crawl sitemap -a site_url=https://www.tagesschau.de/sitemap/ -O expected_sitemap.json
    """

    # Assigning spider name
    name = "sitemap"
    # Defining the allowed domains
    allowed_domains = ["tagesschau.de"]
    # Initializing the start urls list
    start_urls = []
    # Assigning the domain name
    domain_name = "https://www.tagesschau.de"
    # Initializing a dictionary to store the scraped data
    sitemap_json = {}

    # Initializing the spider class with site_url and category parameters
    def __init__(self, site_url=None, category=None):
        try:
            # Asserting that the site_url parameter is not None
            assert site_url != None, "should be 'site_url is not None"
            # Adding the site_url to the start_urls list
            self.start_urls.append("https://www.tagesschau.de/")
        except AssertionError as e:
            # Printing an error message if the assertion fails
            print(f"Error: {e}")

    # Parsing the response received from the start url
    def parse(self, response):
        # Sending a request to the parse_sitemap method
        yield scrapy.Request(response.url, callback=self.parse_sitemap)

    # Parsing the sitemap page to extract links and their titles
    def parse_sitemap(self, response):
        # Looping through all the anchor tags in the response
        for link in response.css("a"):
            # Extracting the URL and title
            url = link.css("::attr(href)").get()
            title = link.css("a::text").get().replace("\n", "")
            # Checking if the URL is valid and not a duplicate
            if url:
                if url.startswith(("#", "//")) or url in [
                    "https://www.ard.de",
                    "https://www.tagesschau.de",
                    "https://wetter.tagesschau.de/",
                ]:
                    continue
                if url.startswith("/"):
                    url = self.domain_name + url
            # Checking if the URL and title are not None
            if url is not None and title is not None:
                # Storing the URL in the sitemap_json dictionary
                self.sitemap_json["link"] = url
                # Stripping the title of any whitespace
                title = title.strip()

                # Checking if the title is empty and scraping the headline if it is
                if not title:
                    self.sitemap_json["title"] = (
                        link.css(".teaser-xs__headline::text , .teaser__headline::text")
                        .get()
                        .replace("\n", "")
                        .replace(" ", "")
                    )
                # Storing the title in the sitemap_json dictionary
                elif title:
                    self.sitemap_json["title"] = title
                # Sending a request to the parse_articlewise_get_date method
                yield scrapy.Request(url, callback=self.parse_articlewise_get_date)
                # Yielding the sitemap_json dictionary
                yield self.sitemap_json

    # Parsing the individual articles to extract their publication dates
    def parse_articlewise_get_date(self, response):
        # Looping through all the article links in the response
        for article in response.css(".teaser__link"):
            # Extracting the title and link of the article
            title = article.css(".teaser__headline::text").get()

            link = article.css("a::attr(href)").get()
            # Sending a request to the parse_date method along with the title and link as meta data
            yield scrapy.Request(
                link, callback=self.parse_date, meta={"link": link, "title": title}
            )

    # This function parses the date of the article by extracting it from the web page's HTML code.
    def parse_date(self, response):
        # It extracts the article link and title from the response's metadata.
        link = response.meta["link"]
        title = response.meta["title"]
        date = response.css(".metatextline::text").get()
        # It then extracts the date string from the HTML code using a regular expression.
        match = re.search(r"\d{2}\.\d{2}\.\d{4}", date)
        # If a match is found, it converts the date string to a datetime object, and formats it as '%d-%m-%Y'.
        if match:
            date_string = match.group()
            # Convert the date string to a datetime object
            date = datetime.strptime(date_string, "%d.%m.%Y")
            date_only = date.date()
            formatted_date = date_only.strftime("%d-%m-%Y")
        # Finally, it stores the article link, title, and date in a dictionary named 'sitemap_json' and yields it.
        self.sitemap_json["link"] = link
        self.sitemap_json["title"] = title.replace("\n", "").replace('"', "").strip()
        self.sitemap_json["published_at"] = formatted_date

        yield self.sitemap_json
