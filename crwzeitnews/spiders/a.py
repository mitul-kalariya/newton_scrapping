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
                   'referer': 'https://www.zeit.de/zustimmung?url=https%3A%2F%2Fwww.zeit.de%2Findex',
                   'accept-encoding': 'gzip, deflate, br', 'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
                   'cookie': 'creid=1761892688200608988; _k5a=61@{"u":[{"uid":"aDvnTTQYuLXfldY7","ts":1680271807},1680361807]}; wt_fa=lv~1680271807791|1695823807791#cv~1|1695823807793#fv~1680271807800|1695823807801#; wt_fa_s=start~1|1711807807802#; _sp_v1_uid=1:384:01848358-9df8-4a28-8eac-ec0ec570d83c; _sp_v1_ss=1:H4sIAAAAAAAAAItWqo5RKimOUbKKRmbkgRgGtbE6MUqpIGZeaU4OkF0CVlBdi1tCKRYAmuD4I1IAAAA%3D; _sp_su=false; wteid_981949533494636=4168027180800266792; wtsid_981949533494636=1; _sp_enable_dfp_personalized_ads=true; consentUUID=67655ceb-2a75-4f5f-aa2b-b81696677577_18; consentDate=2023-03-31T14:10:23.833Z; _sp_v1_data=2:532696:1680271746:0:1:-1:1:0:0:_:-1; _sp_v1_opt=1:login|true:last_id|11:; _sp_v1_csv=; _sp_v1_lt=1:; zonconsent=2023-03-31T14:10:24.018Z; wt_rla=981949533494636%2C2%2C1680271807819'}

        cookie_string = 'creid=1761891441443194415; _k5a=61@{"u":[{"uid":"kXb0YZhbZgmWaE12","ts":1680270618},1680360618]}; wt_fa=lv~1680270618944|1695822618944#cv~1|1695822618945#fv~1680270618946|1695822618946#; wt_fa_s=start~1|1711806618947#; wteid_981949533494636=4168027061900569888; wtsid_981949533494636=1; _sp_v1_uid=1:799:ce56a9e8-0b43-499a-adce-177cefeceb10; _sp_v1_ss=1:H4sIAAAAAAAAAItWqo5RKimOUbKKRmbkgRgGtbE6MUqpIGZeaU4OkF0CVlBdi1tCKRYAmuD4I1IAAAA%3D; _sp_su=false; _sp_enable_dfp_personalized_ads=true; consentUUID=1e7fb635-9b0f-4aae-88b8-f5cfee8d6352_18; consentDate=2023-03-31T13:50:28.061Z; _sp_v1_data=2:532696:1680270437:0:1:-1:1:0:0:_:-1; _sp_v1_opt=1:login|true:last_id|11:; _sp_v1_csv=; _sp_v1_lt=1:; zonconsent=2023-03-31T13:50:28.478Z; wt_rla=981949533494636%2C2%2C1680270618956'
        req = scrapy.Request("https://www.zeit.de/gsitemaps/index.xml", headers=headers,
            cookies=self.parse_cookies(cookie_string), callback=self.parse)
        yield req

    def parse(self, response):
        open_in_browser(response)
        raw_cookies = '; '.join([cookie.decode('utf-8') for cookie in response.headers.getlist('Set-Cookie')])
        print('\n\nSET COOKIE: %s\n\n' % raw_cookies)
        open_in_browser(response)
