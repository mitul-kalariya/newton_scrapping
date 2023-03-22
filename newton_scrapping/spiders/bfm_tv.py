import scrapy
import json
import re
from datetime import datetime


class BFMTVNewsSpider(scrapy.Spider):
    name = "bfm_tv"
    start_urls = [
        # "https://www.bfmtv.com/politique/retraites-des-milliers-de-manifestants-dans-tout-le-pays-48-heures-avant-la-greve-du-23-mars_AV-202303210796.html",
        # "https://www.bfmtv.com/politique/elysee/il-n-y-aura-pas-de-reponse-politique-que-va-dire-emmanuel-macron-sur-la-reforme-des-retraites-ce-mercredi_AV-202303210738.html",
        # "https://www.bfmtv.com/police-justice/je-suis-content-l-enfant-blesse-dans-l-accident-avec-pierre-palmade-raconte-son-retour-chez-lui_AN-202303210703.html",
        # "https://www.bfmtv.com/police-justice/paris-une-enquete-ouverte-pour-des-soupcons-de-violences-policieres-en-marge-d-une-manifestation_AN-202303210705.html",
        # "https://www.bfmtv.com/societe/religions/l-arabie-saoudite-annonce-le-debut-du-ramadan-ce-jeudi_AD-202303210660.html",
        # "https://www.bfmtv.com/economie/economie-social/social/reforme-des-retraites-transports-ecoles-eboueurs-a-quoi-s-attendre-pour-la-journee-du-jeudi-23-mars_AV-202303210442.html",
        # "https://www.bfmtv.com/people/je-pense-aux-victimes-muriel-robin-reagit-pour-la-premiere-fois-a-l-affaire-palmade_AV-202303200832.html",
        # "https://www.bfmtv.com/politique/gouvernement/reforme-des-retraites-pourquoi-le-conseil-constitutionnel-pourrait-en-partie-la-censurer_AN-202303220029.html",
        # "https://www.bfmtv.com/politique/il-met-sans-cesse-de-l-huile-sur-le-feu-les-propos-de-macron-sur-la-foule-qui-n-a-pas-de-legitimite-tres-critiques_AV-202303210810.html",
        "https://www.bfmtv.com/politique/elysee/il-n-y-aura-pas-de-reponse-politique-que-va-dire-emmanuel-macron-sur-la-reforme-des-retraites-ce-mercredi_AV-202303210738.html",
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_json = None

    def parse(self, response):
        response_json = self.response_json(response)
        response_data = self.response_data(response)
        data = {
            # "raw_response": {
            #     "content_type": "text/html; charset=utf-8",
            #     "content": response.css("html").get(),
            # },
        }
        # if response_json:
        # data["parsed_json"] = response_json
        if response_data:
            response_data["country"] = ["France"]
            response_data["time_scraped"] = [str(datetime.now())]
            data["parsed_data"] = response_data
        yield data

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
            self.main_json = data
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

    def response_data(self, response):
        response_data = {}
        pattern = r"[\r\n\t\"]+"
        embedded_video_links = []
        text = []

        article_title = response.css("h1.content_title::text").get()
        if article_title:
            response_data["title"] = [re.sub(pattern, "", article_title).strip()]

        article_published = response.css("div#content_scroll_start time::text").get()
        if article_published:
            response_data["published_at"] = [article_published]

        article_description = response.css("div.chapo::text").get()
        if article_description:
            response_data["description"] = [article_description]

        article_text = " ".join(response.css("p::text").getall())
        print("\n\n\n\n ====>", article_text)
        if article_text:
            text.append(re.sub(pattern, "", article_text).strip())

        article_blockquote_text = " ".join(response.css("span::text").getall())
        if article_blockquote_text:
            text.append(re.sub(pattern, "", article_blockquote_text))

        if text:
            response_data["text"] = [" ".join(text)]

        article_author = response.css("span.author_name::text").get()
        if article_author:
            response_data["author"] = [
                {"@type": "Person", "name": re.sub(pattern, "", article_author).strip()}
            ]

        article_publisher = (self.main_json[1]).get("publisher")
        if article_publisher:
            response_data["publisher"] = [article_publisher]

        article_thumbnail = (self.main_json[1]).get("image").get("contentUrl")
        if isinstance(article_thumbnail, list):
            response_data["thumbnail_image"] = article_thumbnail

        thumbnail_video = (self.main_json[1]).get("video").get("embedUrl")
        if thumbnail_video:
            embedded_video_links.append(thumbnail_video)

        video_linkes = self.extract_videos(response.request.url)
        if video_linkes:
            embedded_video_links.append(video_linkes)

        if embedded_video_links:
            response_data["embed_video_link"] = embedded_video_links
        return response_data

    def extract_videos(self, current_url) -> list:
        return 0
