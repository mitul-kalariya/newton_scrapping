import scrapy
import re
import requests
from io import BytesIO
from PIL import Image
import json
from datetime import datetime
import datetime
import pandas as pd
from datetime import date


class BharatRepublicWorldSpider(scrapy.Spider):
    name = "Bharat_News"
    today = (date.today()).strftime("%d-%m-%Y")
    data = None
    start_urls = [
        "https://www.republicworld.com/entertainment-news/hollywood-news/jr-ntr-meets-michael-b-jordan-after-naatu-naatu-oscar-win-photos-go-viral-articleshow.html"
    ]

    def __init__(
        self,
        article=None,
        site_map=None,
        start_date=None,
        end_date=None,
        category=None,
        type=None,
        url=None,
        subcategory=None,
        **kwargs,
    ):
        """
        Initializes a Scrapy spider to scrape articles from Republic World.

        Args:
            article (str, optional): The URL of a specific article to scrape (default is None).
            site_map (str, optional): The path to a sitemap XML file to scrape (default is None).
            start_date (str, optional): The start date (inclusive) in the format "dd-mm-yyyy" for filtering articles
                by publication date (default is None to include all dates).
            end_date (str, optional): The end date (inclusive) in the format "dd-mm-yyyy" for filtering articles
                by publication date (default is None to include all dates).
            category (str, optional): The category to filter articles by when using a sitemap (default is None to include
                all categories).
            subcategory (str, optional): The subcategory to filter articles by when using a sitemap (default is None to
                include all subcategories).
            **kwargs: Additional keyword arguments to pass to the parent class.
        """
        super().__init__(**kwargs)
        self.start_urls = []

        if type.lower() == "sitemap":
            self.start_urls.append("https://www.republicworld.com/sitemap.xml")
        if type.lower() == "article":
            if url:
                self.start_urls.append(url)
            else:
                raise Exception("Must have a URL to scrap")

    def parse(self, response):
        """
        Parses the given Scrapy response object, extracting the relevant data and returning it as a dictionary.

        Yields:
            dict: A dictionary containing the parsed data from the response, including the row response content type, content,
            response JSON, and response data.
        """
        # if "sitemap.xml" in response.url:
        #     for sitemap in response.xpath(
        #         "//sitemap:loc/text()",
        #         namespaces={"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"},
        #     ):
        #         if sitemap.get().endswith(".xml"):
        #             for link in sitemap.getall():
        #                 yield scrapy.Request(link, callback=self.parse_sitemap)
        #
        # else:
        response_dict = {
            "raw_response": {
                "content_type": "text/html; charset=utf-8",
                "content": response.css("html").get(),
            }
        }

        response_json = self.response_json(response)
        if response_json:
            response_dict["parsed_json"] = response_json

        response_data = self.response_data(response)
        if response_data:
            response_dict["parsed_data"] = response_data

        yield response_dict

    def parse_sitemap(self, response):
        """
        This function is used to parse sitemap by sending a request to the sitemap URL and getting all the links available in the sitemap.

        Args:
            response (scrapy.http.Response object): The response object obtained from the sitemap URL request.

        Returns:
            This function is a generator and yields a scrapy.Request object with a callback to parse_sitemap_link_title function for each link obtained from the sitemap.

        Raises:
            This function doesn't raise any explicit exception.
        """
        namespaces = {"n": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        links = response.xpath("//n:url/n:loc/text()", namespaces=namespaces).getall()
        published_at = response.xpath(
            "//n:url/n:lastmod/text()", namespaces=namespaces
        ).get()
        for link in links:
            yield scrapy.Request(
                link,
                callback=self.parse_sitemap_link_title,
                meta={"link": link, "published_at": published_at},
            )

    def parse_sitemap_link_title(self, response):
        """
        Extracts the link, published date, and title of a news article from the given response.

        Args:
            response (scrapy.http.Response): The response object from the HTTP request.

        Yields:
            dict: A dictionary containing the link, published date, and title of the news article.
        """
        link = response.meta["link"]
        published_at = response.meta["published_at"][0:10]
        title = response.css(".story-title::text").get()
        self.data = {"link": link, "published_at": published_at, "title": title}

        yield self.data

    def parse_by_dates(self, json_file, start_date, end_date, catagory="") -> list:
        """
        Parses the given JSON file to extract links to articles published between the given start and end dates, and
        optionally filtered by the given category.

        Args:
            json_file (str): The path to the JSON file to parse.
            start_date (str): The start date (inclusive) in the format "dd-mm-yyyy".
            end_date (str): The end date (inclusive) in the format "dd-mm-yyyy".
            catagory (str, optional): The category to filter by (default is "" to include all categories).

        Returns:
            list: A list of links to articles that satisfy the specified criteria.
        """
        start_date = datetime.strptime(start_date, "%d-%m-%Y")
        end_date = datetime.strptime(end_date, "%d-%m-%Y")

        with open(json_file) as f:
            json_data = json.load(f)

        df = pd.DataFrame(json_data).dropna()
        df["published_at"] = pd.to_datetime(df["published_at"], format="%Y-%m-%d")
        filtered_df = df.loc[
            (df["published_at"] >= start_date) & (df["published_at"] <= end_date)
        ]

        if catagory:
            new_df = filtered_df[filtered_df["link"].str.contains(catagory)]
            return list(new_df["link"])

        return list(filtered_df["link"])

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

        main = self.get_main(response)
        if main:
            parsing_dict["main"] = main

        misc = self.get_misc(response)
        if misc:
            parsing_dict["misc"] = misc

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

    def response_data(self, response) -> dict:
        """
        Extracts data from a news article webpage and returns it in a dictionary format.

        Parameters:
        response (scrapy.http.Response): A scrapy response object of the news article webpage.

        Returns:
        dict: A dictionary containing the extracted data from the webpage, including:
            - 'breadcrumbs': (list) The list of breadcrumb links to the article, if available.
            - 'published_on': (str) The date and time the article was published.
            - 'last_updated': (str) The date and time the article was last updated, if available.
            - 'headline': (str) The headline of the article.
            - 'description': (str) The description of the article, if available.
            - 'publisher': (str) The name of the publisher of the article.
            - 'authors': (list) The list of authors of the article, if available.
            - 'video': (str) The video URL of the article, if available.
            - 'thumbnail_image': (str) The URL of the thumbnail image of the article, if available.
            - 'subheadings': (list) The list of subheadings in the article, if available.
            - 'text': (list) The list of text paragraphs in the article.
            - 'images': (list) The list of image URLs in the article, if available.
        """
        main_dict = {}

        authors = self.extract_author(response)
        if authors:
            main_dict["authors"] = authors

        published_on = self.extract_publishd_on(response)
        if published_on:
            main_dict["published_at"] = [published_on]

        last_updated = self.extract_lastupdated(response)
        if last_updated:
            main_dict["modified_at"] = [last_updated]

        description = response.css("h2.story-description::text").get()
        if description:
            main_dict["description"] = [description]

        publisher = self.extract_publisher(response)
        if publisher:
            main_dict["publisher"] = publisher

        article_text = response.css("section p::text").getall()
        if article_text:
            main_dict["text"] = [" ".join(article_text)]

        thumbnail = self.extract_thumnail(response)
        if thumbnail:
            main_dict["thumbnail_image"] = thumbnail

        headline = response.css("h1.story-title::text").get()
        if headline:
            main_dict["title"] = [headline]

        article_images = self.extract_all_images(response)
        if article_images:
            main_dict["images"] = article_images

        video = self.extract_video(response)
        if video:
            main_dict["embed_video_link"] = video

        return main_dict

    def extract_breadcrumbs(self, response) -> list:
        """
        Parameters:
        response:
            scrapy.http.Response object of the web page from which to extract the breadcrumb information.

        Returns:
            A list of dictionaries with the breadcrumb information. Each dictionary contains the following keys:
            index: the index of the breadcrumb element in the list.
            page: the text of the breadcrumb element.
            url: the URL of the breadcrumb element (if available).
        """
        breadcrumb_list = response.css("nav#breadcrumb span")
        info = []
        index = 0
        for i in breadcrumb_list:
            temp_dict = {}
            text = i.css("a::text").get()
            if text:
                temp_dict["index"] = index
                temp_dict["page"] = text
                link = i.css("a::attr(href)").get()
                if link:
                    temp_dict["url"] = link
                info.append(temp_dict)
                index += 1
        return info

    def extract_lastupdated(self, response) -> str:
        """
        This function extracts the last updated date and time of an article from a given Scrapy response object.
        It returns a string representation of the date and time in ISO 8601 format.
        If the information is not available in the response, it returns None.

        Args:
            response: A Scrapy response object representing the web page from which to extract the information.
        """
        info = response.css("span.time-elapsed")
        if info:
            return info.css("time::attr(datetime)").get()

    def extract_publishd_on(self, response) -> str:
        info = response.css("div.padbtm10")
        info_eng = response.css("div.padtop20")
        # when in some pages containing english text published date is reflected by this variable info_eng
        if info_eng:
            return info_eng.css("time::attr(datetime)").get()
        elif info_eng:
            return info.css("time::attr(datetime)").get()

    def extract_author(self, response) -> list:
        """
        The extract_author function extracts information about the author(s)
        of an article from the given response object and returns it in the form of a list of dictionaries.

        Parameters:
            response (scrapy.http.Response): The response object containing the HTML of the article page.

        Returns:
            A list of dictionaries, where each dictionary contains information about one author.

        """
        info = response.css("div.author")
        pattern = r"[\r\n\t\"]+"
        data = []
        if info:
            for i in info:
                temp_dict = {}
                temp_dict["@type"] = "Person"
                temp_dict["name"] = re.sub(
                    pattern, "", i.css("div a span::text").get()
                ).strip()
                temp_dict["info"] = i.css("div a::attr(href)").get()
                data.append(temp_dict)
            return data

    def extract_thumnail(self, response) -> list:
        """
        The function extract_thumbnail extracts information about the thumbnail image(s) associated with a webpage,
        including its link, width, and height, and returns the information as a list of dictionaries.

        Returns:
            A list of dictionaries, with each dictionary containing information about an image. If no images are found, an empty list is returned.
        """
        info = response.css("div.gallery-item")
        mod_info = response.css(".storypicture img.width100")
        data = []
        if info:
            for i in info:
                image = i.css("div.gallery-item-img-wrapper img::attr(src)").get()
                if image:
                    data.append(image)
        elif mod_info:
            for i in mod_info:
                image = i.css("img::attr(src)").get()
                if image:
                    data.append(image)
        return data

    def extract_video(self, response) -> list:
        """
        A list of video objects containing information about the videos on the webpage.
        """
        info = response.css("div.videoWrapper")
        data = []
        if info:
            for i in info:
                js = i.css("script").get()
                request_link = re.findall(r"playlist\s*:\s*'(\S+)'", js)[0]
                response = requests.get(request_link)
                link = response.json().get("playlist")[0].get("sources")[1].get("file")
                temp_dict = {"link": link}
                data.append(temp_dict)
        return data

    def extract_publisher(self, response) -> list:
        """
        Extracts publisher information from the given response object and returns it as a dictionary.

        Returns:
        - A dictionary containing information about the publisher. The dictionary has the following keys:
            - "@id": The unique identifier for the publisher.
            - "@type": The type of publisher (in this case, always "NewsMediaOrganization").
            - "name": The name of the publisher.
        """
        logo = response.css('link[rel="icon"]::attr(href)').getall()[2]
        img_response = requests.get(logo)
        width, height = Image.open(BytesIO(img_response.content)).size
        a_dict = {
            "@id": "bharat.republicworld.com",
            "@type": "NewsMediaOrganization",
            "name": "Bharat republic word",
            "logo": {
                "@type": "ImageObject",
                "url": logo,
                "width": {"@type": "Distance", "name": str(width) + " px"},
                "height": {"@type": "Distance", "name": str(height) + " px"},
            },
        }
        return [a_dict]

    def extract_all_images(self, response) -> list:
        """
        Extracts all the images present in the web page.

        Returns:
        list: A list of dictionaries containing information about each image,
        such as image link.
        """
        info = response.css("div.embedpicture")
        data = []
        if info:
            for i in info:
                temp_dict = {}
                image = i.css("div.embedimgblock img::attr(src)").get()
                if image:
                    temp_dict["link"] = image
                data.append(temp_dict)
        return data
