import os
import re
import ast
import json
import logging
import time
import requests
from io import BytesIO
from PIL import Image
from datetime import datetime,timedelta
from crwzeitnews.constant import TODAYS_DATE,LOGGER
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from crwzeitnews.exceptions import *

language_mapper = {"de": "Germany", "en": "English"}


ERROR_MESSAGES = {
    "InputMissingException": "{} field is required.",
    "InvalidDateException": "Please provide valid date.",
    "InvalidArgumentException": "Please provide a valid arguments.",
}

def create_log_file():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        filename="logs.log",
        filemode="a",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def based_on_scrape_type(
    scrape_type: str, scrape_start_date: datetime, scrape_end_date: datetime, url: str
) -> datetime:
    """
    check scrape type and based on the type pass it to the validated function,
    after validation return required values.

     Args:
         scrape_type: Name of the scrape type
         scrape_start_date (datetime): scrapping start date
         scrape_end_date (datetime): scrapping end date
         url: url to be used

     Returns:
         datetime: if scrape_type is sitemap
         list: if scrape_type is sitemap
    """
    if scrape_type == "sitemap":
        scrape_start_date, scrape_end_date = sitemap_validations(
            scrape_start_date, scrape_end_date, url
        )
        date_range_lst = []
        date_range_lst.extend(iter(date_range(scrape_start_date, scrape_end_date)))
        return date_range_lst

    return validate_arg("MISSING_REQUIRED_FIELD", None, "type")



def date_range(start_date: datetime, end_date: datetime) -> None:
    """
    Return range of all date between given date
    if not end_date then take start_date as end date

    Args:
        start_date (datetime): scrapping start date
        end_date (datetime): scrapping end date
    Returns:
        Value of parameter
    """
    for date in range(int((end_date - start_date).days) + 1):
        yield (start_date + timedelta(date)).strftime("%Y-%m-%d")


def sitemap_validations(
    scrape_start_date: datetime, scrape_end_date: datetime, article_url: str
) -> datetime:
    """
    Validate the sitemap arguments
    Args:
        scrape_start_date (datetime): scrapping start date
        scrape_end_date (datetime): scrapping end date
        article_url (str): article url
    Returns:
        date: return current date if user not passed any date parameter
    """
    if scrape_start_date and scrape_end_date:
        validate_arg(InvalidDateException, not scrape_start_date > scrape_end_date)
        validate_arg(
            InvalidDateException,
            int((scrape_end_date - scrape_start_date).days) <= 30,
        )
    else:
        validate_arg(
            InputMissingException,
            not (scrape_start_date or scrape_end_date),
            "start_date and end_date",
        )
        scrape_start_date = scrape_end_date = datetime.now().date()

    validate_arg(
        InvalidArgumentException, not article_url, "url is not required for sitemap."
    )

    return scrape_start_date, scrape_end_date




def validate_arg(param_name, param_value, custom_msg=None) -> None:
    """
    Validate the param.

    Args:
        param_name: Name of the parameter to be validated
        param_value: Value of the required parameter

    Raises:
        ValueError if not provided
    Returns:
          Value of parameter
    """
    if not param_value:
        raise param_name(ERROR_MESSAGES[param_name.__name__].format(custom_msg))

def export_data_to_json_file(scrape_type: str, file_data: str, file_name: str) -> None:
    """
    Export data to json file
    Args:
        scrape_type: Name of the scrape type
        file_data: file data
        file_name: Name of the file which contain data
    Raises:
        ValueError if not provided
    Returns:
        Values of parameters
    """

    folder_structure = ""
    if scrape_type == "sitemap":
        folder_structure = "Links"
        filename = f'{file_name}-sitemap-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
    elif scrape_type == "article":
        folder_structure = "Article"
        filename = (
            f'{file_name}-articles-{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        )
    if not os.path.exists(folder_structure):
        os.makedirs(folder_structure)
    with open(f"{folder_structure}/{filename}.json", "w", encoding="utf-8") as file:
        json.dump(file_data, file, indent=4)


def remove_empty_elements(parsed_data_dict):
    """
    Recursively remove empty lists, empty dicts, or None elements from a dictionary.
    :param d: Input dictionary.
    :type d: dict
    :return: Dictionary with all empty lists, and empty dictionaries removed.
    :rtype: dict
    """

    def empty(value):
        return value is None or value == {} or value == []

    if not isinstance(parsed_data_dict, (dict, list)):
        data_dict = parsed_data_dict
    elif isinstance(parsed_data_dict, list):
        data_dict = [
            value
            for value in (remove_empty_elements(value) for value in parsed_data_dict)
            if not empty(value)
        ]
    else:
        data_dict = {
            key: value
            for key, value in (
                (key, remove_empty_elements(value))
                for key, value in parsed_data_dict.items()
            )
            if not empty(value)
        }
    return data_dict


def get_raw_response(response):
    raw_resopnse = {
        "content_type": "text/html; charset=utf-8",
        "content": response.css("html").get(),
    }
    return raw_resopnse


def get_parsed_json(response):
    """
    extracts json data from web page and returns a dictionary
    Parameters:
        response(object): web page
    Returns
        parsed_json(dictionary): available json data
    """
    parsed_json = {}
    other_data = []
    ld_json_data = response.css('script[type="application/ld+json"]::text').getall()
    for a_block in ld_json_data:
        data = json.loads(a_block)
        if data.get("@type") == "Article":
            parsed_json["main"] = data
        elif data.get("@type") == "ImageGallery":
            parsed_json["ImageGallery"] = data
        elif data.get("@type") == "VideoObject":
            parsed_json["VideoObject"] = data
        else:
            other_data.append(data)
    
    parsed_json["Other"] = other_data
    misc = get_misc(response)
    if misc:
        parsed_json["misc"] = misc

    return remove_empty_elements(parsed_json)


def get_main(response):
    """
    returns a list of main data available in the article from application/ld+json
    Parameters:
        response:
    Returns:
        main data
    """
    try:
        
        information = {}
        main = response.css('script[type="application/ld+json"]::text').getall()
        for block in main:
            data = json.loads(block)
            if data.get("@type") == "Article":
                information["article"] = data
            elif data.get("@type") == "WebPage":
                information["WebPage"] = data
            elif data.get("@type") == "VideoObject":
                information["VideoObject"] = data
            elif data.get("@type") == "NewsMediaOrganization":
                information["publisher_info"] = data

        return information
    except BaseException as e:
        LOGGER.error(f"{e}")
        print(f"Error while getting main: {e}")


def get_misc(response):
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



def get_parsed_data_dict() -> dict:
    """
    Return base data dictionary

    Args:
    None

    Returns:
        dict: Return base data dictionary
    """
    return {
        "source_country": None,
        "source_language": None,
        "author": [{"@type": None, "name": None, "url": None}],
        "description": None,
        "modified_at": None,
        "published_at": None,
        "publisher": None,
        "text": None,
        "thumbnail_image": None,
        "title": None,
        "images": None,
        "section": None,
        "embed_video_link": None,
    }


# def get_parsed_data(response):
#     """
#     Extracts data from a news article webpage and returns it in a dictionary format.
#     Parameters:
#     response (scrapy.http.Response): A scrapy response object of the news article webpage.
#     Returns:
#     dict: A dictionary containing the extracted data from the webpage, including:
#          - 'publisher': (str) The name of the publisher of the article.
#          - 'article_catagory': The region of the news that the article refers to
#          - 'headline': (str) The headline of the article.
#          - 'authors': (list) The list of authors of the article, if available.
#          - 'published_on': (str) The date and time the article was published.
#          - 'updated_on': (str) The date and time the article was last updated, if available.
#          - 'text': (list) The list of text paragraphs in the article.
#          - 'images': (list) The list of image URLs in the article, if available. (using bs4)
#     """
#     try:
#         main_dict = {}
#         imp_ld_json_data = get_main(response)
#         article_json = imp_ld_json_data.get("article")
#         webpage_json = imp_ld_json_data.get("WebPage")
#         if article_json:
#             main_dict["author"] =  article_json.get("author")
#             main_dict["description"] = article_json.get("description")
#             main_dict["modified_at"] = article_json.get("dateModified")
#             main_dict["published_at"] = article_json.get("datePublished")
#             main_dict["publisher"] = article_json.get("publisher")
#             main_dict["text"] = article_json.get("articleBody")
#             if webpage_json:
#                 main_dict["thumbnail_image"] = extract_thumbnail_image(webpage_json)
#             main_dict["title"] = article_json.get("headline")
#             main_dict["tags"] = article_json.get("keywords")
#             mapper = {"de": "German"}
#             article_lang = response.css("html::attr(lang)").get()
#             main_dict["source_language"] = [mapper.get(article_lang)]
#             main_dict["source_country"] = ["Germany"]
#             main_dict["time_scraped"] = [str(datetime.now())]
#             main_dict = format_dictionary(main_dict)
#         return remove_empty_elements(main_dict)
  
#     except BaseException as e:
#         LOGGER.error(f"{e}")
#         raise exceptions.ArticleScrappingException(f"Error while fetching parsed_data data: {e}")

def get_parsed_data(response: str) -> dict:
    """
     Parsed data response from generated data using given response and selector

    Args:
        response: provided response
        parsed_json_main: A list of dictionary with applications/+ld data

    Returns:
        Dictionary with Parsed json response from generated data
    """
   
    imp_ld_json_data = get_main(response)
    article_json = imp_ld_json_data.get("article")
    webpage_json = imp_ld_json_data.get("WebPage")
    publisher_info_json = imp_ld_json_data.get("publisher_info")
    videoobject_json = imp_ld_json_data.get("VideoObject")
    if article_json:
        parsed_json_main = article_json
    else:
        parsed_json_main = videoobject_json
    parsed_data_dict = get_parsed_data_dict()
    parsed_data_dict |= get_country_details()
    parsed_data_dict |= get_language_details(response)
    parsed_data_dict |= get_author_details(parsed_json_main, response)
    parsed_data_dict |= get_descriptions_date_details(parsed_json_main)
    parsed_data_dict |= get_publisher_details(parsed_json_main)
    parsed_data_dict |= get_text_title_section_tag_details(parsed_json_main, response)
    parsed_data_dict |= get_thumbnail_image_video(response, webpage_json)
    final_dict = format_dictionary(parsed_data_dict)
    return remove_empty_elements(final_dict)


def get_country_details() -> dict:
    """
    Return country related details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: country related details
    """

    return {"source_country": ["Germany"]}


def get_language_details(response: str) -> dict:
    """
    Return language related details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: language related details
    """
    return {
        "source_language": [
            "German"
        ]
    }



def get_author_details(parsed_data: list, response: str) -> dict:
    """
    Return author related details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: author related details
    """
    author_details = []
    parsed_data = format_dictionary(parsed_data)
    if not parsed_data.get("author"):
        return author_details.append(
            {
                "name": response.css('div.column-heading__name > script[itemprop="name"]::text')
                .get()
                .strip()
            }
        )
    author_details.extend(
        {
            "@type": author.get("@type"),
            "name": author.get("name"),
            "url": author.get("url", None),
        }
        for author in parsed_data.get("author")
    )
    print(author_details)
    return {"author": author_details}


def get_descriptions_date_details(parsed_data: list) -> dict:
    """
    Returns description, modified date, published date details
    Args:
        parsed_data: response of application/ld+json data
    Returns:
        dict: description, modified date, published date related details
    """
    if "Article" or "VideoObject" in parsed_data.get("@type"):
        return {
            "description": parsed_data.get("description"),
            "modified_at": parsed_data.get("dateModified"),
            "published_at": parsed_data.get("datePublished"),
        }

    return {
        "description": None,
        "modified_at": None,
        "published_at": None,
    }


def get_publisher_details(parsed_data: list) -> dict:
    """
    Returns publisher details like name, type, id
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: publisher details like name, type, id related details
    """
    publisher_details = []
    if parsed_data.get("publisher"):
        publisher_details.extend(parsed_data.get("publisher"))
    return {"publisher": publisher_details}


def get_text_title_section_tag_details(parsed_data: list, response: str) -> dict:
    """
    Returns text, title, section details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: text, title, section, tag details
    """
    if "Article" or "VideoObject" in parsed_data.get("@type"):
        return {
            "title": parsed_data.get("headline"),
            "text": parsed_data.get("articleBody"),
            "section": parsed_data.get('articleSection'),
            "tags": parsed_data.get("keywords"),
        }
    return {
        "title": response.css("header.article-header > h1::text").getall(),
        "tags": response.css("ul.article-tags__list > li > a::text").getall(),
    }


def get_thumbnail_image_video(response: str, webpage_json: dict) -> dict:
    """
    Returns thumbnail images, images and video details
    Args:
        parsed_data: response of application/ld+json data
        response: provided response
    Returns:
        dict: thumbnail images, images and video details
    """
    video_urls = response.css("video::attr(src)").getall()
    thumbnail_json = webpage_json.get("primaryImageOfPage")
    if thumbnail_json:
        thumbnail_url = [thumbnail_json.get("url")] 
    return {
        "embed_video_link": video_urls,
        "thumbnail_image": thumbnail_url
    }

      
def format_dictionary(raw_dictionary):
    for key, value in raw_dictionary.items():
        if not isinstance(value, list):
            raw_dictionary[key] = [value]
    return raw_dictionary

def extract_thumbnail_image(webpage_json):
    image_object_dict = webpage_json.get("primaryImageOfPage")
    if image_object_dict:
        return image_object_dict.get("url")

