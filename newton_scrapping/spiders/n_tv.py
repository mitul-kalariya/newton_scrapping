import re
import json
import scrapy
from PIL import Image
from io import BytesIO
from dateutil import parser
from datetime import date
from datetime import datetime
import os


class InvalidDateRange(Exception):
    pass

class NTVNewsSpider(scrapy.Spider):
    # ntvnews spider
    name = "n_tv"
    start_urls = [
        "https://www.n-tv.de/wirtschaft/Paypal-entlaesst-sieben-Prozent-der-Belegschaft-article23883895.html",
        "https://www.n-tv.de/politik/Kampf-um-Bachmut-Prigoschin-bittet-um-Hilfe-article23999504.html",
        "https://www.n-tv.de/politik/USA-wappnen-sich-fuer-moeglichen-Sturm-von-Trump-Anhaengern-article23999741.html",
        "https://www.n-tv.de/politik/Scholz-plaudert-ueber-Telefonate-mit-Putin-article23999612.html",
        "https://www.n-tv.de/wirtschaft/Aktie-von-US-Bank-First-Republic-im-freien-Fall-article23999825.html",
        "https://www.n-tv.de/wirtschaft/Tesla-findet-in-Deutschland-kaum-noch-Mitarbeiter-article23999753.html",
        "https://www.n-tv.de/leute/Helene-Fischer-muss-ihre-Tour-verschieben-article23999382.html",
        "https://www.n-tv.de/leute/tv/Beim-dritten-Katzen-Tattoo-verzweifelt-Jauch-article23998827.html",
        "https://www.n-tv.de/politik/Lindner-stellt-Neubau-fuer-Finanzministerium-infrage-article23999533.html",
        "https://www.n-tv.de/wissen/Maya-Grabstaette-bei-Bauarbeiten-entdeckt-article23999722.html",
        "https://www.n-tv.de/mediathek/videos/politik/Finnische-Regierungschefin-aeussert-sich-zu-Party-Video-article23535688.html",
        "https://www.n-tv.de/mediathek/videos/politik/Heusgen-Russland-ist-jetzt-Discount-Tankstelle-Chinas-article24000082.html",
        "https://www.n-tv.de/mediathek/videos/politik/Zwischenruferin-platzt-in-Putin-Inszenierung-article23998457.html",
        "https://www.n-tv.de/mediathek/videos/politik/Putin-ist-Xis-pubertierender-kleiner-Bruder-article23998352.html",
        "https://www.n-tv.de/mediathek/videos/politik/Russland-baut-wohl-Verteidigungsanlagen-auf-der-Krim-article23995696.html",
        "https://www.n-tv.de/mediathek/videos/politik/Deutschland-und-Japan-ruecken-naeher-zusammen-article23994664.html",
        "https://www.n-tv.de/mediathek/videos/politik/Heusgen-Russland-ist-jetzt-Discount-Tankstelle-Chinas-article24000082.html",
    ]


    def parse(self, response):

        # if self.type == "sitemap":
        #     if self.start_date != None and self.end_date != None:
        #         yield scrapy.Request(response.url, callback=self.parse_sitemap)
        #     else:
        #         yield scrapy.Request(response.url, callback=self.parse_sitemap)

        # if self.type == 'article':
        response_json = self.response_json(response)
        response_data = self.response_data(response)
        data = {
            'raw_response': {
                "content_type": "text/html; charset=utf-8",
                "content": response.css('html').get(),
            },
        }
        if response_data:
            data["parsed_json"] = response_json
        if response_data:
            data["parsed_data"] = response_data

        yield data
           # self.article_json_data.append(data)

    def response_json(self, response) -> dict:

        parsed_json = {}
        main = self.get_main(response)
        if main:
            parsed_json["main"] = main

        misc = self.get_misc(response)
        if misc:
            parsed_json["misc"] = misc

        return parsed_json

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
            self.logger.error(f"{e}")
            print(f"Error while getting misc: {e}")

    def response_data(self,response):
        response_data = {}
        pattern = r"[\r\n\t\"]+"


        article_title = response.css("h2 span.article__headline::text").get()
        if article_title:
            response_data['title'] = [re.sub(pattern,"",article_title).strip()]

        article_author = response.css("span.article__infos span.article__author::text").get()
        if article_author:
            response_data['author'] = [{
                "@type": "Person",
                "name": re.sub(pattern, "",article_author).strip()
            }]

        article_publishdate = response.css("span.article__date::text").get()
        if article_publishdate:
            response_data['published_at'] = [article_publishdate]

        article_description = response.css('p strong::text').get()
        if article_description:
            response_data['description'] = [article_description]

        article_text = " ".join(response.css('p::text').getall())
        if article_text:
            response_data['text'] = [article_text]
        elif response.css('div.article__text::text').get():
            response_data['text'] = [re.sub(pattern, "" ,response.css('div.article__text::text').get()).strip()]

        article_thumbnail = self.extract_thumbnail(response)
        if article_thumbnail:
            response_data['thumbnail_image'] = article_thumbnail

        article_video = response.css('div.vplayer__video div video source::attr(src)').get()
        link = re.findall(r"http?.*?\.mp4", str(article_video))
        if link:
            response_data['embed_video_link'] = link

        article_tags = response.css("section.article__tags ul li a::text").getall()
        if article_tags:
            response_data['tags'] = article_tags

        return response_data

    def extract_thumbnail(self, response):
        video_article = response.css("div.vplayer div.vplayer__video")
        normal_article = response.css("div.article__media figure")
        data = []
        if normal_article:
            for i in normal_article:
                thumbnail_image = i.css("picture img::attr(src)").get()
                if thumbnail_image:
                    data.append(thumbnail_image)
        elif video_article:
            for j in video_article:
                thumbnail_image = j.css("img::attr(src)").get()
                if thumbnail_image:
                    data.append(thumbnail_image)
        return data




