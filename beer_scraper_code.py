import time
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
import bisect
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service


def get_links(url, attrs):
    """Gets all the links to the beer styles depending on the attrs.
    :param url: containing the web page we want to extract the links from.
    :param attrs: containing the attributes for the find method.
    :type url: str
    :type attrs: str
    :return: a list containing all the links.
    :rtype: list
    """
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    mtag = soup.find("div", attrs=attrs)
    link_list = [t['href'] for t in mtag.findAll("a")]
    return link_list


def get_main_styles(url_link):
    """Gets all the names of the main beer styles.
    :param url_link: containing the web page we want to get the names.
    :type url_link: str
    :return: a list containing all the names of the main beer styles.
    :rtype: list
    """
    l = []
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    mtag = soup.find_all("div", attrs={"class": "stylebreak"})
    for style in mtag:
        main_style = style.next.get_text()
        l.append(main_style)
    return l


def get_beer_data1(curr_beer, soup, main_style_list, index):
    """Gets the next information about the beer: Main_Style, Primary_Style, Min_IBU, Max_IBU.
    :param curr_beer: a dictionary storing all the data about a beer.
    :param soup: bs4 object containing the inforamtion we want to extract.
    :param main_style_list: list of main beer styles names.
    :param index: index to know the current beer range to know the correct main style.
    :type curr_beer: dict
    :type soup: bs4 object
    :type main_style_list: list
    :type index: int
    :return: None
    :rtype: None
    """
    style = soup.find("div", attrs={"class": "titleBar"}).get_text().strip()
    curr_beer['Primary_Style'] = style
    IBU = soup.find(lambda tag: tag.name == 'b' and "IBU:" in tag.text).nextSibling
    if '-' in IBU:
        curr_beer['Min_IBU'] = int(IBU.split('-')[0])
        curr_beer['Max_IBU'] = int(IBU.split('-')[1])
    else:
        curr_beer['Min_IBU'] = int(IBU.split('–')[0])
        curr_beer['Max_IBU'] = int(IBU.split('–')[1])

    limits = [4, 9, 13, 22, 26, 34, 48, 63, 69, 81, 89, 101, 108, 119]
    index = bisect.bisect_left(limits, index)
    curr_beer['Main_Style'] = main_style_list[index]


def get_beer_data_helper(category, part1, part2, curr_beer, text):
    """A function helper for the function get_beer_data2. Searches for the right format inside the text var and inserts
     it to the curr beer dict by the category specified.
        :param category: a dictionary storing all the data about a beer.
        :param part1: part one of the search.
        :param part2: part two of the search.
        :param curr_beer: a dictionary storing all the data about a beer.
        :param text: the text we want to extract the variable from.
        :type category: str
        :type part1: str
        :type part2: str
        :type curr_beer: dict
        :type text: str
        :return: None
        :rtype: None
        """
    var = re.search(r'{}(.*){}'.format(part1, part2), text).group(1).strip()
    curr_beer[category] = var


def get_beer_brewery_data(part1, part2, curr_beer, text):
    """ Gets the brewery information of a beer and stores it in the curr_beer dict.
        :param part1: part one of the search.
        :param part2: part two of the search.
        :param curr_beer: a dictionary storing all the data about a beer.
        :param text: the text we want to extract the variable from.
        :type part1: str
        :type part2: str
        :type curr_beer: dict
        :type text: str
        :return: the name of the brewery
        :rtype: str
        """
    brewery = re.search(r'{}(.*){}'.format(part1, part2), text).group(1).strip()
    if 'amp;' in brewery:
        brewery = brewery.replace('amp;', '')
    curr_beer['Brewery'] = brewery
    if '(' in brewery:
        brewery = brewery.replace('(', '\(')
        brewery = brewery.replace(')', '\)')
    brewery = brewery.translate(brewery.maketrans({"+": r"\+",
                                                   "-": r"\-",
                                                   "/": r"\/",
                                                   ".": r"\.",
                                                   "|": r"\|",
                                                   ":": r"\:",
                                                   "&": r"\&",
                                                   "*": r"\*",
                                                   "'": r"\'",
                                                   "?": r"\?",
                                                   "!": r"!"}))
    return brewery


def get_beer_data2(curr_beer, soup):
    """Gets the next information about the beer: Name, Country, ABV, Web_Score, Average_Score,
     Num_of_reviews and Num_of_ratings.
    :param curr_beer: a dictionary storing all the data about a beer.
    :param soup: bs4 object containing the inforamtion we want to extract.
    :type curr_beer: dict
    :type soup: bs4 object
    :return: None
    :rtype: None
    """
    text = soup.find("div", attrs={"class": "titleBar"}).prettify()
    text = text.replace('\n', '')
    text1 = soup.find("dl", attrs={"class": "beerstats"}).get_text()
    text1 = text1.replace('\n', '')
    text2 = soup.find("div", attrs={"style":"clear:both; margin:0; padding:0px 20px; font-size:1.05em;"}).get_text()
    text2 = text2.replace('\n', '').replace('Notes:', '')

    get_beer_data_helper('Name', '<h1>', '<br/>', curr_beer, text)
    brewery = get_beer_brewery_data(';">', '</span>', curr_beer, text)
    get_beer_data_helper('Country', brewery, 'Style', curr_beer, text1)
    get_beer_data_helper('ABV', 'ABV:', 'Score', curr_beer, text1)
    score = re.search(r'Score:(\d?\d?\d?)', text1).group(1).strip()
    curr_beer['Web_Score'] = score
    get_beer_data_helper('Average_Score', 'Avg:', '\|', curr_beer, text1)
    get_beer_data_helper('Num_of_reviews', 'Reviews:', 'Ratings:', curr_beer, text1)
    get_beer_data_helper('Num_of_ratings', 'Ratings:', 'Status:', curr_beer, text1)
    curr_beer['Notes'] = text2


data = []  # a list to store all the different beer information
main_styles = []  # a list to store the names of the main styles
curr_beer = {}  # a dictionary to store the current beer information
url = "https://www.beeradvocate.com/beer/styles/"
linkToStyles = get_links(url, {"id": "ba-content"})
linkToStyles.pop()  # remove the last element - unnecessary
main_styles = get_main_styles(url)

#  selenium library adjustments
PATH = "C:\Program Files (x86)\chromedriver.exe"
options = webdriver.ChromeOptions()
options.add_argument('--headless')
driver = webdriver.Chrome(service=Service(PATH), options=options)
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.5414.120 Safari/537.36'}

#  main loop to go over all the beers and extract the data needed
for curr_style in range(0, len(linkToStyles)):
    url = "https://www.beeradvocate.com" + linkToStyles[curr_style]
    time.sleep(0.5)
    try:
        response = requests.get(url, headers=headers)
    except:
        continue
    soup = BeautifulSoup(response.content, "html.parser")
    get_beer_data1(curr_beer, soup, main_styles, curr_style)

    clickable_next_button = True
    while clickable_next_button:
        temp_beer_links = get_links(url, {"class": "mainContent"})
        beer_links = []
        for beer in temp_beer_links:
            if ('/beer/profile/' in beer) and beer.count('/') == 5:
                beer_links.append(beer)

        for beer in range(0, len(beer_links)):
            curr_beer_url = 'https://www.beeradvocate.com' + beer_links[beer]
            time.sleep(0.5)
            try:
                response = requests.get(curr_beer_url, headers=headers)
            except:
                continue
            soup = BeautifulSoup(response.content, "html.parser")
            get_beer_data2(curr_beer, soup)
            data.append(curr_beer.copy())

        driver.get(url)
        #  if there is a next button click it, otherwise move to the next beer style
        try:
            next_button = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.LINK_TEXT, 'next'))
            )
            driver.execute_script('arguments[0].click()', next_button)
            url = driver.current_url
        except:
            clickable_next_button = False

#  store the data into a data frame and write it into a csv file
df = pd.DataFrame(data)
df.to_csv('beer_data_final.csv')

