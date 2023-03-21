import scrapy
import re
import requests
from io import BytesIO
from PIL import Image


class RepublicWorldSpider(scrapy.Spider):
    name = "republicworld"

    def __init__(self, category=None, article_link=None):
        self.start_urls = []
        self.category = category
        self.article_link = article_link
        if self.category == "sitemap":
            self.start_urls.append("https://www.republicworld.com/sitemap.xml")
        if self.article_link:
            self.start_urls.append(self.article_link)

    def parse(self, response):
        # Checking if the response URL is a sitemap
        if "sitemap.xml" in response.url:
            for sitemap in response.xpath(
                "//sitemap:loc/text()",
                namespaces={"sitemap": "http://www.sitemaps.org/schemas/sitemap/0.9"},
            ):
                if sitemap.get().endswith(".xml"):
                    for link in sitemap.getall():
                        yield scrapy.Request(link, callback=self.parse_sitemap)
        else:
            response_data = self.response_data(response)
            yield {"response_data": response_data}

    def parse_sitemap(self, response):
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
        link = response.meta["link"]
        published_at = response.meta["published_at"]
        title = response.css(".story-title::text").get()

        yield {"link": link, "published_at": published_at, "title": title}


class BharatNews(scrapy.Spider):
    name = "BharatNews"
    start_urls = [
        # 'https://bharat.republicworld.com/india-news/accidents-and-disasters/5-people-died-after-fire-broke-out-inside-a-house-in-kanpur-dehat',
        # 'https://bharat.republicworld.com/entertainment-news/bollywood-news/oscars-2023-naatu-naatu-performance-got-standing-ovation-deepika-padukone-speech'
        "https://bharat.republicworld.com/sports-news/cricket-news/sanju-samson-meets-rajinikanth-as-he-shares-an-emotional-post-after-meeting-on-twitter"
    ]

    def __init__(
        self,
        article=None,
        site_map=None,
        start_date=None,
        end_date=None,
        category=None,
        **kwargs
    ):
        super().__init__(**kwargs)

        # if category == "sitemap":

        if site_map and category:
            links = []
            if start_date != None and end_date != None:
                links = self.parse_by_dates(
                    site_map, start_date, start_date, category=category
                )
            if end_date == None and start_date == None:
                links = self.parse_by_dates(
                    site_map, self.today, self.today, category=category
                )
            if end_date == None and start_date != None:
                links = self.parse_by_dates(
                    site_map, start_date, self.today, category=category
                )

            self.start_urls = links
        elif site_map:
            links = []
            if start_date != None and end_date != None:
                links = self.parse_by_dates(site_map, start_date, start_date)
            if end_date == None and start_date == None:
                links = self.parse_by_dates(site_map, self.today, self.today)
            if end_date == None and start_date != None:
                links = self.parse_by_dates(site_map, start_date, self.today)

            self.start_urls = links

        if article:
            self.start_urls.append(article)

    def parse(self, response, **kwargs):
        current_url = response.request.url
        response_data = self.response_data(response)
        response_json = self.response_json(response, current_url)
        yield {
            "row_response": {
                "content_type": "text/html; charset=utf-8",
                "content": response.css("html").get(),
            },
            "response_json": response_json,
            "response_data": response_data,
        }

    def response_json(self, response, current_url) -> dict:
        main_dict = {}
        main_dict["main"] = {
            "@context": "https://bharat.republicworld.com/",
            "@type": "NewsArticle",
            "mainEntityOfPage": {"@type": "WebPage", "@id": current_url},
        }

        headline = response.css("h1.story-title::text").get()
        if headline:
            main_dict["headline"] = headline

        published_on = self.extract_publishd_on(response)
        if published_on:
            main_dict["published_on"] = published_on

        last_updated = self.extract_lastupdated(response)
        if last_updated:
            main_dict["last_updated"] = last_updated

        description = response.css("h2.story-description::text").get()
        if description:
            main_dict["description"] = description

        authors = self.extract_author(response)
        if authors:
            main_dict["authors"] = authors

        video = self.extract_video(response)
        if video:
            main_dict["video"] = video

        thumbnail = self.extract_thumnail(response)
        if thumbnail:
            main_dict["thumbnail_image"] = thumbnail

        return main_dict

    def response_data(self, response) -> dict:
        main_dict = {}

        breadcrumbs = self.extract_breadcrumbs(response)
        if breadcrumbs:
            main_dict["breadcrumbs"] = breadcrumbs

        published_on = self.extract_publishd_on(response)
        if published_on:
            main_dict["published_on"] = published_on

        last_updated = self.extract_lastupdated(response)
        if last_updated:
            main_dict["last_updated"] = last_updated

        headline = response.css("h1.story-title::text").get()
        if headline:
            main_dict["headline"] = headline

        description = response.css("h2.story-description::text").get()
        if description:
            main_dict["description"] = description

        publisher = self.extract_publisher(response)
        if publisher:
            main_dict["publisher"] = publisher

        authors = self.extract_author(response)
        if authors:
            main_dict["authors"] = authors

        video = self.extract_video(response)
        if video:
            main_dict["video"] = video

        thumbnail = self.extract_thumnail(response)
        if thumbnail:
            main_dict["thumbnail_image"] = thumbnail

        subheadings = response.css("strong::text").getall()
        if subheadings:
            main_dict["subheadings"] = subheadings

        article_text = response.css("div.storytext > div > p::text").getall()
        if article_text:
            main_dict["text"] = article_text

        return main_dict

    def extract_breadcrumbs(self, response) -> list:
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
        info = response.css("span.time-elapsed")
        if info:
            return info.css("time::attr(datetime)").get()

    def extract_publishd_on(self, response) -> str:
        info = response.css("div.padbtm10")
        if info:
            return info.css("time::attr(datetime)").get()

    def extract_author(self, response) -> list:
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
        info = response.css("div.gallery-item")
        data = []
        if info:
            for i in info:
                temp_dict = {}
                image = i.css("div.gallery-item-img-wrapper img::attr(src)").get()
                img_response = requests.get(image)
                width, height = Image.open(BytesIO(img_response.content)).size
                if image:
                    temp_dict["@type"] = "ImageObject"
                    temp_dict["link"] = image
                    temp_dict["width"] = {
                        "@type": "Distance",
                        "name": str(width) + " px",
                    }
                    temp_dict["height"] = {
                        "@type": "Distance",
                        "name": str(height) + " px",
                    }

                data.append(temp_dict)
        return data

    def extract_video(self, response) -> list:
        info = response.css("div.videoWrapper")

        data = []
        if info:
            for i in info:
                js = i.css("script").get()
                request_link = re.findall(r"playlist\s*:\s*'(\S+)'", js)[0]
                response = requests.get(request_link)
                link = response.json().get("playlist")[0].get("sources")[1].get("file")
                temp_dict = {"@type": "VideoObject", "link": link}
                data.append(temp_dict)
        return data

    def extract_publisher(self, response) -> list:
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

        return a_dict
