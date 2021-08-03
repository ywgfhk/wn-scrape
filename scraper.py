from bs4 import BeautifulSoup as bs
import requests
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import re

# start webdriver
driver = webdriver.Chrome(executable_path="C:\\Users\\test\\AppData\\Local\\Programs\\Python\\Python36\\chromedriver.exe")
driver.implicitly_wait(0.5)
driver.maximize_window()

# config
output_filename = "将进酒_cn_trad_raw_plaintext.txt"
first_ch_url = "https://www.twfanti.com/JiangJinJiu/read_3_p2.html"
next_ch_button_xpath = "//a[@class='pt-nextchapter']"
output_type = "plaintext"
body_xpath = "//div[@class='size16 color5 pt-read-text']"
chapter_header_xpath = "//h1/a[@title]"


def get_body_text(body_xpath):
    print('getting body')
    e = driver.find_element(By.XPATH, body_xpath)
    html = e.get_attribute("outerHTML")  # driver.page_source
    return html


def make_footnote_counter(start=1):
    count = [start - 1]

    def footnote_counter(match):
        count[0] += 1
        return " [%d] " % count[0]

    return footnote_counter


# open output file
f = open(output_filename, "a", encoding="utf-8")
# start web crawler
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

    html = get_body_text(body_xpath)

    if output_type == "plaintext":
        #write chapter title
        f.write('\n')
        f.write(driver.find_element(By.XPATH, chapter_header_xpath).text)
        f.write('\n\n')

        #write body
        soup = bs(html, "lxml")
        if first_ch_url.startswith('http://www.jjwxc.net/') or first_ch_url.startswith('https://www.oldtimescc.cc/'):
            f.write('\n')
            f.write(driver.find_element(By.XPATH, body_xpath).text)
            f.write('\n')
        elif first_ch_url.startswith('https://www.wattpad.com/') or first_ch_url.startswith('https://www.zhenhunxiaoshuo.com'):
            all_p = soup.find_all(['p'])
            for p in all_p:
                p = str(p).replace("<br/>", "\n")  # change soup to text, replace <br/> with linebreak, revert back to soup
                p = re.sub(r'<span class="num-comment">.*?</span>', "", p, flags=re.DOTALL) #remove Wattpad comment button text
                f.write(bs(p, "lxml").getText())
                f.write('\n')
        elif first_ch_url.startswith('https://chrysanthemumgarden.com/'):
            all_p = soup.find_all(['p'])

            for p in all_p:
                p = str(p)
                print(p)
                # get translator's notes' id
                tooltip_targets = re.findall(r'tooltip-target="(.*?)"', p)
                translator_notes = []
                if tooltip_targets:
                    for t in tooltip_targets:
                        tooltip_xpath = "//span[@tooltip-target="+"'"+t+"']"
                        text_xpath = "//div[@id='" + t + "']"
                        print(tooltip_xpath)
                        tooltip = driver.find_element(By.XPATH, tooltip_xpath)
                        # driver.find_element(By.XPATH, "./ancestor::div[@class='row']").click()
                        # tooltip.click()
                        # text = driver.find_element(By.XPATH, text_xpath).text()
                        # translator_notes.append(text)

                # clean body
                p = re.sub(r"<(span|h3|p) style=.*?hidden.*?>.*?</(span|h3|p)>", "", p, flags=re.DOTALL)  # remove hidden text
                p = re.sub(r"<(span|h3|p) class=.*?jum.*?>.*?</(span|h3|p)>", "", p,
                           flags=re.DOTALL)  # remove jumbled text
                print(p)
                # p = re.sub(r'<span class=tooltip-toggle.*?</span>', make_footnote_counter, p,
                #            flags=re.DOTALL)  # add footnote number [%d]
                f.write(bs(p, "lxml").getText(strip=True))
                f.write('\n')
            #write translators' note

            if translator_notes:
                f.write("Translator's Note")
                note_idx = 1
                for note in translator_notes:
                    f.write(note_idx+". "+note+"\n")

        else:
            all_p = soup.find_all(['p'])
            for p in all_p:
                f.write(p.get_text(strip=True))
                f.write('\n')

        f.write("----------------------------------")
    else:
        f.write(html)

    # Is there a next page?
    try:
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
