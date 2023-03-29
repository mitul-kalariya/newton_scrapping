from datetime import datetime
import logging

TODAYS_DATE = datetime.today().strftime("%Y-%m-%d")
SITEMAP_SCHEMA = "http://www.sitemaps.org/schemas/sitemap/0.9"
SITEMAP_URL = "https://www.republicworld.com/sitemap.xml"
LOGGER = logging.getLogger()
