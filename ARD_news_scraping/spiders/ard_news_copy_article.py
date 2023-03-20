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
    # name = "ArdNewsArticle"
    start_urls = ['https://www.tagesschau.de/inland/innenpolitik/zeitenwende-sondervermoegen-bundeswehr-101.html']
    today = (date.today()).strftime("%d-%m-%Y")


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

    def parse_by_dates(self, json_file, start_date, end_date, catagory="") -> list:
        start_date = datetime.strptime(start_date, "%d-%m-%Y")
        end_date = datetime.strptime(end_date, "%d-%m-%Y")

        with open(json_file) as f:
            json_data = json.load(f)

        df = pd.DataFrame(json_data).dropna()
        df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
        filtered_df = df.loc[(df["date"] >= start_date) & (df["date"] <= end_date)]

        if catagory:
            new_df = filtered_df[filtered_df["link"].str.contains(catagory)]
            return list(new_df["link"])

        return list(filtered_df["link"])

    def parse(self, response):
        current_url = response.request.url
        response_json = self.response_json(response, current_url)
        response_data = self.response_data(response, current_url)
        yield {
            # 'raw_response': {
            #     "content_type": "text/html; charset=utf-8",
            #     "content": response.css('html').get(),
            # },
            'parsed_json' : response_json,
            "parsed_data": response_data
        }

    def response_data(self, response, current_url) -> dict:
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
            img_dimension = {"width": width, "height": height}
            main_dict["thumbnail_image"] = {
                "@type": "image_media",
                "image_link": thumbnail_image,
                "dimensions": img_dimension,
            }

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

    def response_json(self, response, current_url) -> dict:
        pattern = r"[\r\n\t\"]+"
        main_data = {}
        for data in response:
            main_data["@context"] = "http://schema.org"
            main_data["@type"] = "NewsArticle"
            main_entity_of_page = {}
            main_entity_of_page["@type"] = "WebPage"
            main_entity_of_page[
                "@id"
            ] = "https://www.tagesschau.de/ausland/europa/bachmut-143.html"
            main_data["mainEntityOfPage"] = main_entity_of_page
            main_data["headline"] = (
                data.css("span.seitenkopf__topline::text").get().strip()
            )
            main_data["datePublished"] = (
                data.css("div.metatextline::text").get().strip()
            )
            image = data.css("picture.ts-picture--topbanner .ts-image::attr(src)").get()
            if image:
                image = "https://www.tagesschau.de/" + image
                main_data["image"] = image

            main_data["title1"] = data.css(
                "span.seitenkopf__headline--text::text"
            ).get()
            main_data["title2"] = data.css("h2.meldung__subhead::text").get()
            description = []
            for i in data.css("p.textabsatz::text, p.m-ten > strong::text").getall():
                description.append(i.strip())
            main_data["description"] = description
            main_data["tags"] = data.css("ul.taglist li a::text").getall()

        yield main_data

    def extract_audio_info(self, response) -> list:
        info = []
        for child in response:
            audio = child.css("div.ts-mediaplayer::attr(data-config)").get()
            adict = {}
            if audio:
                audio_link = re.findall(r"http?.*?\.mp3", audio)[0]
                if audio_link:
                    adict["@type"] = "audio_media"
                    adict["link"] = (audio_link,)
                audio_title = child.css("h3.copytext__audio__title::text").get()
                if audio_title:
                    adict["Title"] = audio_title
                audio_info = child.css("div.copytext__audio__metainfo::text").get()
                try:
                    audio_info = audio_info.split(",")
                    audio_author = audio_info[0].strip()
                    if audio_author:
                        adict["Author"] = {
                            "@type": "person",
                            "name": audio_author,
                        }
                    audio_publisher = audio_info[1].strip()
                    if audio_publisher:
                        adict["publisher"] = {
                            "@type": "Organization",
                            "name": audio_publisher,
                        }
                    publish_time = audio_info[2]
                    if publish_time:
                        adict["published_at"] = publish_time
                except:
                    pass
                info.append(adict)
        return info

    def extract_recommendation_data(self, response) -> list:
        info = []
        pattern = r"[\r\n\t\"]+"

        for child in response:
            a_dict = {}
            image = child.css("div.ts-picture__wrapper picture img::attr(src)").get()
            if image:
                a_dict["image"] = "https://www.tagesschau.de/" + image

            type = child.css("span.label.label--small strong::text").get()
            if type:
                a_dict["type_of_artical"] = type

            publish_date = child.css("span.teaser-absatz__date::text").get()
            if publish_date:
                a_dict["publish_date"] = publish_date

            top_line = child.css("span.teaser-absatz__topline::text").get()
            if top_line:
                a_dict["topic"] = top_line

            tagline = child.css("span.teaser-absatz__headline::text").get()
            if tagline:
                clean_tagline = re.sub(pattern, "", tagline).strip()
                a_dict["Tag-line"] = clean_tagline
            else:
                continue

            short_text = child.css("p.teaser-absatz__shorttext::text").get()
            if short_text:
                a_dict["short_descryption"] = short_text

            info.append(a_dict)
        return info

    def extract_info_boxs(self, response) -> list:
        info = []
        for child in response:
            info_headline = child.css(".infobox__headline--textonly::text").get()
            info_text = child.css("p.infobox__text--textonly::text").get()
            info.append(
                dict(
                    {
                        "info_headline": info_headline,
                        "info_text": info_text,
                    }
                )
            )
        return info

    def extract_breadcrumbs(self, response, current_url) -> list:
        breadcrumb_list = response.css("ul.article-breadcrumb li")
        info = []
        index = 1
        info.append(dict({"index": 0, "page": "home", "url": "/"}))
        for i in breadcrumb_list:
            text = i.css("li a::text").get()
            if text:
                text = text.split()
                text = "".join(text)
                if text:
                    info.append(
                        dict(
                            {
                                "index": index,
                                "page": text,
                                "url": i.css("li a::attr(href)").get(),
                            }
                        )
                    )
                    index += 1
        info.append(
            dict(
                {
                    "index": index,
                    "page": breadcrumb_list.css(
                        "li.article-breadcrumb__title span::text"
                    ).get(),
                    "url": current_url,
                }
            )
        )

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
                else:
                    continue
                image = child.css("div.id-card div picture a img::attr(src)").get()
                if image:
                    a_dict["image"] = "https://www.tagesschau.de/" + image
                if child.css("span.id-card__logo svg title::text").get():
                    broadcaster = child.css("span.id-card__logo svg title::text").get()
                    a_dict["broadcaster"] = {
                        "@type": "organization",
                        "name": broadcaster.replace(" Logo", ""),
                    }
                organization = child.css("span.id-card__name::text").get()
                if organization:
                    a_dict["organization"] = organization.strip()
                link = child.css("a.id-card__twitter-id::attr(href)").get()
                if link:
                    a_dict["Link"] = link

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
                    a_dict["video_title"] = video_title

                video_info = child.css("div.copytext__video__metainfo::text").get()
                video_info = video_info.split(",")
                video_author = video_info[0].strip()
                if video_author:
                    a_dict["Author"] = {
                        "@type": "Person",
                        "name": video_author,
                    }
                try:
                    if len(video_info) > 2:
                        video_publisher = video_info[1].strip()

                        a_dict["publisher"] = {
                            "@type": "Organization",
                            "publisher_name": video_publisher,
                        }
                except:
                    pass

                a_dict["published_at"] = video_info[len(video_info) - 1].strip()

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
