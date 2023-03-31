import scrapy
from scrapy.utils.response import open_in_browser


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
        headers = {'sec-ch-ua': '"Not_A Brand";v="99", "Google Chrome";v="109", "Chromium";v="109"',
                   'sec-ch-ua-mobile': '?0', 'sec-ch-ua-platform': '"Linux"', 'upgrade-insecure-requests': '1',
                   'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
                   'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                   'sec-fetch-site': 'same-origin', 'sec-fetch-mode': 'navigate', 'sec-fetch-user': '?1',
                   'sec-fetch-dest': 'document',
                   'referer': 'https://www.zeit.de/zustimmung?url=https%3A%2F%2Fwww.zeit.de%2Fpolitik%2Fausland%2Fkarte-ukraine-krieg-russland-frontverlauf-truppenbewegungen',
                   'accept-encoding': 'gzip, deflate, br', 'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
        }

        cookie_string = 'creid=1761880315003170047; _k5a=61@{"u":[{"uid":"TIq4ITCaXvHrWQ2z","ts":1680260007},1680350007]}; wt_fa=lv~1680260007789|1695812007789#cv~1|1695812007789#fv~1680260007789|1695812007789#; wt_fa_s=start~1|1711796007790#; wteid_981949533494636=4168026000800950088; wtsid_981949533494636=1; _sp_v1_uid=1:432:876f1249-65ad-46fd-b836-33dd5b9fec72; _sp_v1_ss=1:H4sIAAAAAAAAAItWqo5RKimOUbKKRmbkgRgGtbE6MUqpIGZeaU4OkF0CVlBdi1tCKRYAmuD4I1IAAAA%3D; _sp_su=false; _sp_enable_dfp_personalized_ads=true; consentUUID=b18a6fa5-f2b0-43a8-a282-6edf1f0d9949_18; consentDate=2023-03-31T10:53:42.081Z; _sp_v1_data=2:532696:1680260010:0:1:-1:1:0:0:_:-1; _sp_v1_opt=1:login|true:last_id|11:; _sp_v1_csv=; _sp_v1_lt=1:; zonconsent=2023-03-31T10:53:42.454Z; wt_rla=981949533494636%2C2%2C1680260007792'
        req = scrapy.Request(
            "https://www.zeit.de/politik/ausland/2023-03/usa-schweigegeld-anklage-donald-trump-spenden",
            headers=headers, cookies=self.parse_cookies(cookie_string), callback=self.parse)
        yield req

    def parse(self, response):
        open_in_browser(response)
        raw_cookies = '; '.join([cookie.decode('utf-8') for cookie in response.headers.getlist('Set-Cookie')])
        print('\n\nSET COOKIE: %s\n\n' % raw_cookies)
        open_in_browser(response)
