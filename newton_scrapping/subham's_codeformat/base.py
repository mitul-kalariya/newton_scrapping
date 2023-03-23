from abc import ABC, abstractmethod

class BaseSpider(ABC):

    # should have below attributes in your Spider class
    # articles=[]
    # type = "sitemap" or "article"

    @abstractmethod
    def parse(response):
        pass

    @abstractmethod
    def parse_sitemap(self, response: str) -> None:
        # parse_sitemap_article will be called from here
        pass
    
    @abstractmethod
    def parse_sitemap_article(self, response: str) -> None:
        pass

    @abstractmethod
    def parse_article(self, response: str) -> list:
        # below functions will be called from here
        # get_raw_response
        # get_parsed_json
        # get_parsed_data
        # should return self.articles
        pass
