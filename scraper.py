import requests
import sys, os
import time
import csv
import re
from bs4 import BeautifulSoup
import json

# proxy was tried. due to (1) free proxy was unreliable and slow,
# (2) we would perform crawling on a server,
# I decide not to use

def dump_html(response, file_name):
    writer = open(file_name, "w", encoding="utf8")
    soup = BeautifulSoup(response, 'html.parser')
    writer.write(soup.prettify())
    writer.close()

class Crawler():
    def __init__(self, home_url, sleep_time, start_index):
        self.start_url = f"{home_url}?start={start_index}"
        self.sleep_time = sleep_time
        self.yelp_start_index = start_index

    def _get_write_type(self, save_to_file):
        if os.path.isfile(save_to_file):
            return "a"
        else:
            return "w"

    def _get_total_page(self):
        response = requests.get(self.start_url).text
        '''with open("temp.html",'r',encoding="utf8") as reader:
            response = reader.read()'''

        soup = BeautifulSoup(response, 'html.parser')
        navigation_div = soup.find("div", {"role": "navigation"})
        pagi_div = navigation_div.findChild("div", {"class": re.compile(".*padding-b2.*")})
        total_page = int(pagi_div.text[pagi_div.text.index("of") + 3:])

        return total_page

class ReviewCrawler(Crawler):
    def __init__(self, home_url, sleep_time, start_index):
        super().__init__(home_url, sleep_time, start_index)

        self.header = ["city", "stars", "date", "text"]

    def _extract_data(self, response):
        soup = BeautifulSoup(response, 'html.parser')

        cities = []
        user_info_divs = soup.find_all("div", {"class":re.compile(".*user-passport-info.*")})
        for div in user_info_divs:
            city_span = div.findChild("span", {"class":re.compile(".*text-color--normal.*")})
            city = "" if city_span == None else city_span.text
            cities.append(city)

        stars = []
        star_divs = soup.find_all("div", {"class": re.compile(".*i-stars.*")})
        for div in star_divs[1:21]:
            star = float(div["aria-label"][0:div["aria-label"].index("star")])
            stars.append(star)

        dates = []
        date_spans = soup.find_all("span", {"class":re.compile(".*text-color--mid.*")})
        for date in date_spans:
            dates.append(date.text)

        texts = []
        text_ps = soup.find_all("p", {"class":re.compile(".*comment.*")})
        for p in text_ps:
            texts.append(p.text)

        datas = list(zip(cities, stars, dates, texts))

        #sys.exit()
        return datas

    def run(self, save_to_file):
        item_per_page = 20
        total_page = self._get_total_page()
        write_type = self._get_write_type(save_to_file)

        with open(save_to_file, write_type, encoding="utf8", newline="") as writer:
            csv_writer = csv.writer(writer)
            if write_type == "w":
                csv_writer.writerow(self.header)

            next_url = self.start_url

            for i in range(int(self.yelp_start_index / item_per_page), total_page):
                response = requests.get(next_url).text
                '''with open("temp.html", 'r', encoding="utf8") as reader:
                    response = reader.read()'''

                datas = self._extract_data(response)
                yelp_start_index = i * item_per_page
                for data_row in datas:
                    data = [yelp_start_index]
                    data.extend(data_row)
                    csv_writer.writerow(data)
                    writer.flush()

                print("\r", end="")
                print("Finish getting page", (i + 1), "out of", f"{total_page}.", "Now sleeping...", end="", flush=True)
                time.sleep(self.sleep_time)

                next_url = next_url[0:next_url.rindex("=") + 1] + str((i + 1) * item_per_page)

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
        pagi_div = navigation_div.findChild("div", {"class":re.compile(".*padding-b2.*")})
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
        name_divs = soup.find_all("div", {"class":re.compile(".*businessNameWithNoVerifiedBadge.*")})
        for div in name_divs:
            ahref = div.findChild("a")
            place_names.append(ahref.text)
            lnks.append(f"https://www.yelp.com.sg{ahref['href']}")

        stars = []
        star_divs = soup.find_all("div", {"class": re.compile(".*i-stars.*")})
        for div in star_divs:
            star = float(div["aria-label"][0:div["aria-label"].index("star")])
            stars.append(star)

        reviews = []
        price = []
        tags = []
        rev_spans = soup.find_all("span", {"class": re.compile(".*reviewCount.*")})
        for span in rev_spans:
            reviews.append(int(span.text))

            ancestor = span.parent.parent.parent.parent
            price_tag_div = ancestor.nextSibling
            price_span = price_tag_div.findChild("span", {"class": re.compile(".*priceRange.*")})
            if price_span == None:
                price.append("NA")
            else:
                price.append(price_span.text)

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
                writer.flush()

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

class GeocoordinatesFinder():
    def __init__(self, name_link_pairs, sleep_time):
        self.name_link_pairs = name_link_pairs
        self.header = ["name", "latitude", "longitude"]
        self.home_url = "https://www.yelp.com.sg/map/"
        self.sleep_time = sleep_time

    def _get_write_type(self, save_to_file):
        if os.path.isfile(save_to_file):
            return "a"
        else:
            return "w"

    def run(self, save_to_file):
        write_type = self._get_write_type(save_to_file)

        with open(save_to_file, write_type, encoding="utf8", newline="") as writer:
            cwriter = csv.writer(writer)
            if write_type == "w":
                cwriter.writerow(self.header)
                writer.flush()

            count = 0
            for name,link,start_index in self.name_link_pairs:
                count += 1
                biz_name = link[link.rindex("/")+1:]
                url = self.home_url + biz_name
                response = requests.get(url).text
                '''with open("geoex.html", 'r', encoding="utf8") as reader:
                    response = reader.read()'''
                soup = BeautifulSoup(response, 'html.parser')
                enveloping_text = soup.find(text=re.compile("\"location\": {.*}"))
                enveloping_text = enveloping_text[enveloping_text.index("\"location\": {"):]
                geo_text = enveloping_text[enveloping_text.index("{"):enveloping_text.index("}")+1]
                geo_json = json.loads(geo_text)


                row = [name, geo_json["latitude"], geo_json["longitude"]]
                cwriter.writerow(row)

                writer.flush()

                print("\r", end="")
                print("Processing", count, "out of", len(self.name_link_pairs), end="", flush=True)
                time.sleep(self.sleep_time)

def get_names_and_links_to_crawl(file_name):
    place_names = []
    links = []
    start_indexes = []
    with open(file_name, "r", encoding="utf8") as reader:
        creader = csv.DictReader(reader)
        for row in creader:
            place_names.append(row["place name"])
            links.append(row["link"])
            start_indexes.append(row["yelp_start_index"])

    name_link_pairs = list(zip(place_names, links, start_indexes))
    return name_link_pairs


# If you want to scrape list of places, run the following lines
'''start_url = "https://www.yelp.com.sg/search?cflt=restaurants&find_loc=Singapore&start=150"
sleep_time = 5
list_crawler = ListCrawler(start_url, sleep_time)
list_crawler.run("resto_list.csv")'''

# If you want to scrape geographic coordinates, run the following lines
'''name_link_pairs = get_names_and_links_to_crawl("bottom782.csv")
gfinder = GeocoordinatesFinder(name_link_pairs[81:],15)
gfinder.run("geocoordinates.csv")'''

# If you want to scrape reviews given a list of places, run the following lines
sleep_time = 10
name_link_pairs = get_names_and_links_to_crawl("top97.csv")
count = 0
for name,link,start_index in name_link_pairs:
    count += 1
    print("Processing place no.", count, "Name:", name)
    review_crawler = ReviewCrawler(link, sleep_time, int(start_index))
    file_name = f"{link[link.rindex('/')+1:]}.csv"
    review_crawler.run(f"reviews/{file_name}")
