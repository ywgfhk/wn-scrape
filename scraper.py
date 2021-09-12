from bs4 import BeautifulSoup as bs
import argparse
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re
import sys

def get_ch_links(driver, TOC_url, ch_link_xpath):
    driver.get(TOC_url)
    link_elements = driver.find_elements(By.XPATH,ch_link_xpath)
    links = []
    for e in link_elements:
        links.append(e.get_attribute('href'))
    return e


def start_driver():
    # start webdriver
    driver = webdriver.Chrome(executable_path="C:\\Users\\test\\AppData\\Local\\Programs\\Python\\Python36\\chromedriver.exe")
    # driver.implicitly_wait(0.5)
    driver.maximize_window()
    return(driver)


def get_body_text(driver, body_xpath):
    print('getting body')
    e = driver.find_element(By.XPATH, body_xpath)
    html = e.get_attribute("outerHTML")  # driver.page_source
    return html


def make_footnote_counter(start=1):
    count = [start - 1] # emulate nonlocal keyword
    def footnote_counter(match):
        count[0] += 1
        return "%d. " % count[0]
    return footnote_counter

def html_str_substitutions_for_footnote_formatting(html):
    # html = re.sub(r'(<li.*?>)(.*?)(</li>)',r'\1<p>FOOTNOTE_PLACEHOLDER\2</p>\3', html, 0, re.DOTALL)
    html = re.sub(r'(role="doc-endnote"><p>)', r'\1FOOTNOTE_PLACEHOLDER', html)  # temp
    html = re.sub(r'(class="footnote-item"><p>)', r'\1FOOTNOTE_PLACEHOLDER', html)  # temp
    html = re.sub('FOOTNOTE_PLACEHOLDER', make_footnote_counter(), html)
    return html

def decrypt(encoded):
    #decrypts crysanthemom garden's text scrambling
    keyMap = dict(zip('jymvfoutlpxiwcbqdgraenkzshCDJGSMXLPABOZRYUHEVKFNQWTI', 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    return ''.join(keyMap.get(c, c) for c in encoded)

def main(first_ch_url, output_filename, body_xpath, chapter_header_xpath = '', next_ch_button_xpath = '', output_type='plaintext'):
    # open output file
    f = open(output_filename, "a", encoding="utf-8")
    # start web crawler
    driver = start_driver()
    driver.get(first_ch_url)

    # press change language to trad chinese
    if first_ch_url.startswith('http://www.jjwxc.net/'):
        try:
            driver.find_element(By.XPATH, "//a [text() = '繁體版' or text() = '繁体版']").click()
        except NoSuchElementException:
            print("No switch to traditional chinese button")

    next_page_exists = True

    while next_page_exists:
        # jjwxc wait until text switches to trad chinese
        # reference: https://www.soudegesu.com/en/post/python/selenium-wait-element/
        if first_ch_url.startswith('http://www.jjwxc.net/'):
            l_change_button_wait = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a [text() = '简体版' or text() = '简体版']")))
        elif first_ch_url.startswith('https://www.wattpad.com/'):
            load_button_xpath = "//a[@class='on-load-more-page load-more-page next-up grey']"
            # load_more_button_wait = WebDriverWait(driver, 5).until(
            #     EC.presence_of_element_located((By.XPATH, load_button_xpath)))
            while len(driver.find_elements(By.XPATH, load_button_xpath)) > 0:
                try:
                    driver.find_element(By.XPATH, load_button_xpath).click()
                except:
                    continue

        if output_type == "plaintext":
            # write chapter title
            f.write('\n')
            if chapter_header_xpath:
                try:
                    f.write(driver.find_element(By.XPATH, chapter_header_xpath).text)
                    f.write('\n\n')
                except NoSuchElementException:
                    print("Header not found")

            #different scraping and formatting scripts for different webpages
            if first_ch_url.startswith('http://www.jjwxc.net/') or first_ch_url.startswith(
                    'https://www.oldtimescc.cc/'):
                html = get_body_text(driver, body_xpath)
                soup = bs(html, "lxml")
                f.write('\n')
                f.write(driver.find_element(By.XPATH, body_xpath).text)
                f.write('\n')
            elif first_ch_url.startswith('https://www.wattpad.com/') or first_ch_url.startswith(
                    'https://www.zhenhunxiaoshuo.com'):
                html = get_body_text(driver, body_xpath)
                soup = bs(html, "lxml")
                all_p = soup.find_all(['p'])
                # change soup to str, replace <br/> with linebreak, remove Wattpad comment button text, revert back to soup
                for p in all_p:
                    p = str(p).replace("<br/>", "\n")
                    p = re.sub(r'<span class="num-comment">.*?</span>', "", p, flags=re.DOTALL)
                    f.write(bs(p, "lxml").getText())
                    f.write('\n')
            elif first_ch_url.startswith('https://chrysanthemumgarden.com/'):
                html = get_body_text(driver, body_xpath)
                html = html_str_substitutions_for_footnote_formatting(html)
                soup = bs(html, "lxml")

                all_p = soup.find_all(['p'])
                for p in all_p:
                    p = str(p)
                    # get translator's notes' id
                    tooltip_targets = re.findall(r'tooltip-target="(.*?)"', p)
                    # translator_notes = []
                    # if tooltip_targets:
                    #     for t in tooltip_targets:
                    #         tooltip_xpath = "//span[@tooltip-target=" + "'" + t + "']"
                    #         text_xpath = "//div[@id='" + t + "']"
                    #         print("find")
                    #         tooltip = driver.find_element(By.XPATH, tooltip_xpath)
                    #         print("click")
                    #         #driver.find_element(By.XPATH, "./ancestor::div[@class='row']").click()
                    #         tooltip.click()
                    #         text = driver.find_element(By.XPATH, text_xpath).text()
                    #         translator_notes.append(text)

                    # clean body (remove hidden garbage text, decrypt jumbled text)
                    p = re.sub(r"<[a-z]*? style=.*?hidden.*?>.*?</[a-z]*?>", "", p,
                               flags=re.DOTALL)
                    encrypted = re.findall(r'<[a-z]*? class="jum">(.*?)</[a-z]*?>', p, flags=re.DOTALL)
                    for e in encrypted:
                        d = decrypt(e)
                        p = re.sub(r'<[a-z]*? class="jum">.*?</[a-z]*?>', d, p, count=1, flags=re.DOTALL)
                    # p = re.sub(r'<span class=tooltip-toggle.*?</span>', make_footnote_counter, p,
                    #            flags=re.DOTALL)  # add footnote number [%d]
                    f.write(bs(p, "lxml").getText())
                    f.write('\n')

                # write translators' note
                # if translator_notes:
                #     f.write("Translator's Note")
                #     note_idx = 1
                #     for note in translator_notes:
                #         f.write(note_idx + ". " + note + "\n")

            else:
                html = get_body_text(driver, body_xpath)
                html = html_str_substitutions_for_footnote_formatting(html)
                soup = bs(html, "lxml")
                all_p = soup.find_all(['p', 'cite'])
                for p in all_p:
                    p = str(p).replace("<br/>", "\n")
                    p = p.replace('</sup>', "]")
                    p = re.sub(r'<sup.*?>', r'[', p)
                    f.write(bs(p, "lxml").getText())
                    f.write('\n\n')

                # write Translator's Notes
            f.write("----------------------------------")
        else:
            f.write(html)

        # Is there a next page?
        try:
            print(next_ch_button_xpath)
            next_page_url = driver.find_element(By.XPATH, next_ch_button_xpath).get_attribute('href')
            print(next_page_url)
            driver.get(next_page_url)
            print("Proceeding to next page")
            # next_page_exists = False #run to test one page only

        except NoSuchElementException:
            print("Element does not exist")
            next_page_exists = False

    f.close()
    driver.quit()

def parse_args():
    example_text = """sample call:
         python scraper.py https://cangji.net/qiangjinjiu/qiangjinjiu-c1/ 将进酒_ch1-160ongoing_Lianyin_plaintext.txt "//div[@class = 'post-entry']" -head "//h1" -b "(//div[@class='post-entry']//a[img])[last()-1]"
         """
    parser = argparse.ArgumentParser()
    parser.add_argument("url",
                        help="Page to start scraping from.  Usually Chapter 1")
    parser.add_argument("output_filename", help="what to call the file")
    parser.add_argument("body_xpath", help="xpath of page content that you want to scrape")
    parser.add_argument("--header", "-head", help="optional chapter header, to be added to the top of each chapter of scraped file")
    parser.add_argument("--button", "-b", help="next button xpath. If excluded, then script only scrapes single page")
    #parser.add_argument("--html", help="use flag to save html rather than plaintext", default=False, action='store_true')
    #parser.add_argument(description='scrape text from Wordpress, Wattpadd etc. into one text file', epilog=example_text)
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    first_ch_url = args.url
    output_filename = args.output_filename
    body_xpath = args.body_xpath
    if args.header:
        chapter_header_xpath = args.header
    else:
        chapter_header_xpath = ''
    if args.button:
        next_ch_button_xpath = args.button
    else:
        next_ch_button_xpath = ''

    main(first_ch_url, output_filename, body_xpath, chapter_header_xpath, next_ch_button_xpath) #leaving plaintext as only option for now

