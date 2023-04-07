import scrapy
from scrapy.utils.response import open_in_browser
import scrapy
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager



class a_spider(scrapy.Spider):
    name = "ws"

    def parse_cookies(self, raw_cookies):
        # parsed cookies
        cookies = {}

        # loop over cookies
        for cookie in raw_cookies.split('; '):
            try:
                # init cookie key
                key = cookie.split('=')[0]

                # init cookie value
                val = cookie.split('=')[1]

                # parse raw cookie string
                cookies[key] = val

            except:
                pass

        return cookies

    def start_requests(self):
        headers = {}
        chrome_options = Options()
        # chrome_options.add_argument("--headless")
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get("https://www.zeit.de/index")
        time.sleep(5)

        try:
            element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                '//*[@id="main"]/div/article/div/section[2]/div[1]/div')))
            banner_button = driver.find_element(By.XPATH, '//*[@id="main"]/div/article/div/section[2]/div[1]/div')
            if element:

                banner_button.click()
                article = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH,
                                                    '/html/body/div[3]')))
                # '//article[@id="js-article"]')))
                if article:
                    data = []
                    for request in driver.requests:
                        if "https://www.zeit.de/index" in str(request.url) and "cookie:" in str(request.headers):
                            # breakpoint()
                            headers |= self.format_headers(str(request.headers))
                            print(headers)
                            print(str(request.headers).split("cookie:"))

                    driver.quit()
        except:
            pass


        self.valid_cookie = headers.get('cookie')
        # del headers['cookie']
        cookie_string = self.valid_cookie
        req = scrapy.Request("https://www.zeit.de/gsitemaps/index.xml", headers=headers,
            cookies=cookie_string, callback=self.parse)
        yield req

    def parse(self, response):
        open_in_browser(response)
        raw_cookies = '; '.join([cookie.decode('utf-8') for cookie in response.headers.getlist('Set-Cookie')])
        print('\n\nSET COOKIE: %s\n\n' % raw_cookies)
        open_in_browser(response)

    def format_headers(self,request_headers, sep=': ', strip_cookie=False, strip_cl=True,
                       strip_headers: list = []) -> dict:
        """
        formates a string of headers to a dictionary containing key-value pairs of request headers
        :param request_headers:
        :param sep:
        :param strip_cookie:
        :param strip_cl:
        :param strip_headers:
        :return: -> dictionary
        """
        headers_dict = dict()
        for keyvalue in request_headers.split('\n'):
            keyvalue = keyvalue.strip()
            if keyvalue and sep in keyvalue:
                value = ''
                key = keyvalue.split(sep)[0]
                if len(keyvalue.split(sep)) == 1:
                    value = ''
                else:
                    value = keyvalue.split(sep)[1]
                if value == '\'\'':
                    value = ''
                if strip_cookie and key.lower() == 'cookie': continue
                if strip_cl and key.lower() == 'content-length': continue
                if key in strip_headers: continue
                headers_dict[key] = value
        breakpoint()
        headers_dict["cookie"] = self.parse_cookies(headers_dict.get("cookie", None))
        return headers_dict
