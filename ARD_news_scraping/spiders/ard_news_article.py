import scrapy
import re
import requests
from io import BytesIO
from PIL import Image
import json
from datetime import datetime
import pandas as pd
from datetime import date


class ArdNewsArticle(scrapy.Spider):
    name = "ArdNewsArticle"
    start_urls = ['https://www.tagesschau.de/inland/innenpolitik/zeitenwende-sondervermoegen-bundeswehr-101.html']



    def parse(self, response):
        current_url = response.request.url
        response_json = self.response_json(response)
        response_data = self.response_data(response)
        yield {
            # 'raw_response': {
            #     "content_type": "text/html; charset=utf-8",
            #     "content": response.css('html').get(),
            # },
            'parsed_json' : response_json,
            "parsed_data": response_data
        }

    def response_data(self, response) -> dict:
        pattern = r"[\r\n\t\"]+"
        main_dict = {}

        # extract author info
        authors = self.extract_author_info(response.css("div.copytext-element-wrapper"))
        if authors:
            main_dict["authors"] = authors

        # extract main headline of article
        title = response.css("span.seitenkopf__headline--text::text").get()
        if title:
            main_dict["HeadLine"] = title

        # extract the tagline above the title
        tag_line = response.css("span.seitenkopf__topline::text").get()
        if tag_line:
            clean_top_line = re.sub(pattern, "", tag_line).strip()
            main_dict["tag_line"] = clean_top_line

        publisher = response.css("div.header__items")
        if publisher:
            main_dict["publisher"] = {
                "@id": "tagesschau.de",
                "@type": "NewsMediaOrganization",
                "name": "tagesschau",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://www.tagesschau.de/res/assets/image/favicon/favicon-96x96.png",
                    "width": {"@type": "Distance", "name": "96 px"},
                    "height": {"@type": "Distance", "name": "96 px"},
                },
            }

        # extract the date published at
        published_at = response.css("div.metatextline::text").get()
        if published_at:
            clean_time = re.sub(pattern, "", published_at).strip()
            main_dict["published_at"] = clean_time

        # extract the description or read text of the article
        text = response.css("p.textabsatz::text").getall()
        text = [re.sub(pattern, "", i) for i in text]
        main_dict["descryption"] = " ".join(list(filter(None, text)))

        # extract all the sub-headlines of the article
        sub_headlines = self.extract_all_title(
            response.css(
                "h2.meldung__subhead, article > div.seitenkopf > div.seitenkopf__data > div.seitenkopf__title > h1.seitenkopf__headline > span.seitenkopf__headline--text"
            )
        )
        if sub_headlines:
            main_dict["sub_headings"] = sub_headlines

        # extract the modular info-boxes that displays with blue background
        info_box = self.extract_info_boxs(response.css(".infobox--textonly"))
        if info_box:
            main_dict["Additional-info"] = info_box

        # extract the thumbnail image
        thumbnail_image = response.css(
            "picture.ts-picture--topbanner .ts-image::attr(src)"
        ).get()
        if thumbnail_image:
            thumbnail_image = "https://www.tagesschau.de/" + thumbnail_image
            img_response = requests.get(thumbnail_image)
            width, height = Image.open(BytesIO(img_response.content)).size


        # extract audio file if any
        audio = self.extract_audio_info(response.css("div.copytext__audio"))
        if audio:
            main_dict["audio"] = audio

        # extract video files if any
        video = self.extract_all_videos(response.css("div.copytext__video"))
        if video:
            main_dict["video"] = video

        # extract tags associated with article
        tags = response.css("ul.taglist li a::text").getall()
        if tags:
            main_dict["tags"] = tags

        # extract recommended article on the current topic of article
        recommendations = self.extract_recommendation_data(
            response.css(".teaser-absatz__link")
        )
        if recommendations:
            main_dict["recommendations"] = recommendations

        return main_dict

    def response_json(self, response) -> dict:
        pattern = r"[\r\n\t\"]+"
        current_url = response.request.url
        parsed_json = {}
        parsed_json["main"] = {
            "@context": "https://globalnews.ca/",
            "@type": "NewsArticle",
            "mainEntityOfPage": {"@type": "WebPage", "@id": current_url},
        }
        main_parsed_dict = parsed_json['main']
        # extract author info
        authors = self.extract_author_info(response.css("div.copytext-element-wrapper"))
        if authors:
            main_parsed_dict["authors"] = authors

        # extract main headline of article
        title = response.css("span.seitenkopf__headline--text::text").get()
        if title:
            main_parsed_dict["headline"] = title


        publisher = response.css("div.header__items")
        if publisher:
            main_parsed_dict["publisher"] = {
                "@id": "tagesschau.de",
                "@type": "NewsMediaOrganization",
                "name": "tagesschau",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://www.tagesschau.de/res/assets/image/favicon/favicon-96x96.png",
                    "width": {"@type": "Distance", "name": "96 px"},
                    "height": {"@type": "Distance", "name": "96 px"},
                },
            }

        # extract the date published at
        published_at = response.css("div.metatextline::text").get()
        if published_at:
            clean_time = re.sub(pattern, "", published_at).strip()
            main_parsed_dict["datePublished"] = clean_time

        # extract the description or read text of the article
        text = response.css("p.textabsatz::text").getall()
        text = [re.sub(pattern, "", i) for i in text]
        main_parsed_dict["descryption"] = " ".join(list(filter(None, text)))



        # extract audio file if any
        audio = self.extract_audio_info(response.css("div.copytext__audio"))
        if audio:
            main_dict["audio"] = audio

        # extract video files if any
        video = self.extract_all_videos(response.css("div.copytext__video"))
        if video:
            main_dict["video"] = video

        # extract tags associated with article
        tags = response.css("ul.taglist li a::text").getall()
        if tags:
            main_dict["tags"] = tags

        # extract recommended article on the current topic of article
        recommendations = self.extract_recommendation_data(
            response.css(".teaser-absatz__link")
        )
        if recommendations:
            main_dict["recommendations"] = recommendations

        return main_dict

        return main_data

    def get_misc(self, response):
        """
        returns a list of misc data available in the article
        Parameters:
            response:
        Returns:
            misc data
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



    def extract_audio_info(self, response) -> list:
        info = []
        for child in response:
            audio = child.css("div.ts-mediaplayer::attr(data-config)").get()
            adict = {}
            if audio:
                audio_link = re.findall(r"http?.*?\.mp3", audio)[0]
                if audio_link:
                    adict["link"] = (audio_link,)
                audio_title = child.css("h3.copytext__audio__title::text").get()
                if audio_title:
                    adict["caption"] = audio_title

                info.append(adict)
        return info




    def extract_author_info(self, response) -> list:
        info = []
        if response:
            for child in response:
                a_dict = {}

                auth_name = child.css("span.id-card__name::text").get()
                if auth_name:
                    a_dict["@type"] = "person"
                    a_dict["name"] = auth_name.strip()
                link = child.css("a.id-card__twitter-id::attr(href)").get()
                if link:
                    a_dict["url"] = link
                info.append(a_dict)

            return info

    def extract_all_title(self, response) -> list:
        titles = []
        for single_title in response:
            title = single_title.css("span::text").get()
            if title in ["", None]:
                title = single_title.css("h2.meldung__subhead::text").get()
            titles.append(title)
        return titles

    def extract_all_videos(self, response) -> list:
        info = []
        for child in response:
            video = child.css("div.ts-mediaplayer::attr(data-config)").get()
            a_dict = {}
            if video:
                video_link = re.findall(r"http?.*?\.mp4", video)[0]
                if video_link:
                    a_dict["@type"] = "video_media"
                    a_dict["link"] = video_link
                else:
                    continue
                video_title = child.css("h3.copytext__video__title::text").get()
                if video_title:
                    a_dict["caption"] = video_title

                info.append(a_dict)
        return info

