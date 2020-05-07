import requests
import sys, os
import time
import csv
import re
from bs4 import BeautifulSoup

# proxy was tried. due to (1) free proxy was unreliable and slow,
# (2) we would perform crawling on a server,
# I decide not to use

def dump_html(response, file_name):
    writer = open(file_name, "w", encoding="utf8")
    writer.write(response)
    writer.close()

class ListCrawler():
    def __init__(self, start_url, sleep_time):
        self.start_url = start_url
        self.sleep_time = sleep_time
        self.yelp_start_index = int(start_url[start_url.rindex("=")+1:])

        #info crawled
        self.header = ["yelp start index","place name","link","stars","reviews","price","tags"]

    def _get_total_page(self):
        response = requests.get(self.start_url).text
        '''with open("temp.html",'r',encoding="utf8") as reader:
            response = reader.read()'''

        soup = BeautifulSoup(response, 'html.parser')
        navigation_div = soup.find("div", {"role": "navigation"})
        pagi_div = navigation_div.findChild("div", {"class":re.compile(".*padding-b2*.")})
        total_page = int(pagi_div.text[pagi_div.text.index("of") + 3:])

        return total_page

    def _get_write_type(self, save_to_file):
        if os.path.isfile(save_to_file):
            return "a"
        else:
            return "w"

    def _extract_data(self, response):
        place_names = []
        lnks = []
        soup = BeautifulSoup(response, 'html.parser')
        name_divs = soup.find_all("div", {"class":re.compile(".*businessNameWithNoVerifiedBadge*.")})
        for div in name_divs:
            ahref = div.findChild("a")
            place_names.append(ahref.text)
            lnks.append(f"https://www.yelp.com.sg{ahref['href']}")

        stars = []
        star_divs = soup.find_all("div", {"class": re.compile(".*i-stars*.")})
        for div in star_divs:
            star = float(div["aria-label"][0:div["aria-label"].index("star")])
            stars.append(star)

        reviews = []
        price = []
        tags = []
        rev_spans = soup.find_all("span", {"class": re.compile(".*reviewCount*.")})
        for span in rev_spans:
            reviews.append(int(span.text))

            ancestor = span.parent.parent.parent.parent
            price_tag_div = ancestor.nextSibling
            price_span = price_tag_div.findChild("span", {"class": re.compile(".*priceRange*.")})
            if price_span == None:
                price.append("NA")
            else:
                price.append(span.text)

            tag_lnks = price_tag_div.find_all("a")
            tag = ""
            for ahref in tag_lnks:
                tag += ahref.text + ","
            tags.append(tag[:-1])

        datas = list(zip(place_names, lnks, stars, reviews, price, tags))
        return datas

    def run(self, save_to_file):
        total_page = self._get_total_page()
        write_type = self._get_write_type(save_to_file)

        with open(save_to_file, write_type, encoding="utf8", newline="") as writer:
            csv_writer = csv.writer(writer)
            if write_type == "w":
                csv_writer.writerow(self.header)

            next_url = self.start_url

            for i in range(int(self.yelp_start_index/30), total_page):
                response = requests.get(next_url).text
                '''with open("temp.html", 'r', encoding="utf8") as reader:
                    response = reader.read()'''

                datas = self._extract_data(response)
                yelp_start_index = i*30
                for data_row in datas:
                    data = [yelp_start_index]
                    data.extend(data_row)
                    csv_writer.writerow(data)
                    writer.flush()

                print("\r", end="")
                print("Finish getting page", (i+1), "out of", f"{total_page}.", "Now sleeping...", end="", flush=True)
                time.sleep(self.sleep_time)

                next_url = next_url[0:next_url.rindex("=")+1] + str((i+1) * 30)




start_url = "https://www.yelp.com.sg/search?cflt=restaurants&find_loc=Singapore&start=60"
sleep_time = 5
list_crawler = ListCrawler(start_url, sleep_time)
list_crawler.run("resto_list.csv")
