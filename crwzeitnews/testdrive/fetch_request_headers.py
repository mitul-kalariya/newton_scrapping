import scrapy
import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_headers(s, sep=': ', strip_cookie=False, strip_cl=True, strip_headers: list = []) -> dict():
    d = dict()
    for kv in s.split('\n'):
        kv = kv.strip()
        if kv and sep in kv:
            v=''
            k = kv.split(sep)[0]
            if len(kv.split(sep)) == 1:
                v = ''
            else:
                v = kv.split(sep)[1]
            if v == '\'\'':
                v =''
            # v = kv.split(sep)[1]
            if strip_cookie and k.lower() == 'cookie': continue
            if strip_cl and k.lower() == 'content-length': continue
            if k in strip_headers: continue
            d[k] = v
    return d
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
                    headers |= get_headers(str(request.headers))
                    print(headers)
                    print(str(request.headers).split("cookie:"))

            driver.quit()
    req = scrapy.Request("https://www.zeit.de/politik/ausland/karte-ukraine-krieg-russland-frontverlauf-truppenbewegungen",)


except:
    pass

