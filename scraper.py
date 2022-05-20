import argparse
import re
from copy import deepcopy
import lxml.etree as et
import lxml.html as lh
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
import time


def get_ch_links(driver, TOC_url, ch_link_xpath):
    driver.get(TOC_url)
    link_elements = driver.find_elements(By.XPATH,ch_link_xpath)
    links = []
    for e in link_elements:
        links.append(e.get_attribute('href'))
    return e


def start_driver():
    # start webdriver
    options = webdriver.ChromeOptions()
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36")
    options.add_argument("--no-sandbox")
    options.add_argument("--enable-javascript")
    options.add_argument('-ignore-certificate-errors')
    options.add_argument('-ignore -ssl-errors')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.set_capability("pageLoadStrategy", "eager")
    driver = webdriver.Chrome(executable_path="C:\\Users\\test\\AppData\\Local\\Programs\\Python\\Python36\\chromedriver.exe", options=options)
    driver.maximize_window()
    return driver


def get_body_text(driver, body_xpath):
    print('getting body')
    #WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//iframe")))
    # element = driver.find_element(By.XPATH, "//iframe")
    # driver.switch_to.frame(element)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, body_xpath)))
    e = driver.find_element(By.XPATH, body_xpath)
    html = e.get_attribute("outerHTML")  # driver.page_source
    # driver.switch_to.default_content()
    return html


def make_footnote_counter(start=1):
    count = [start - 1] # emulate nonlocal keyword
    def footnote_counter(match):
        count[0] += 1
        return "%d. " % count[0]
    return footnote_counter


def html_str_substitutions_for_footnote_formatting(html):
    #html = re.sub(r'(<li.*?>)(<span>)(.*?)(</span>)(<div>)(.*?)(</div>)(</li>)', r'\1<p>FOOTNOTE_PLACEHOLDER\6</p>\8', html, 0, re.DOTALL) #knoxt
    html = re.sub(r'(<li.*?>)(.*?)(</li>)',r'\1<p>FOOTNOTE_PLACEHOLDER\2</p>\3', html, 0, re.DOTALL)
    html = re.sub(r'(role="doc-endnote"><p>)', r'\1FOOTNOTE_PLACEHOLDER', html)  # temp
    html = re.sub(r'(class="footnote-item"><p>)', r'\1FOOTNOTE_PLACEHOLDER', html)  # temp
    html = re.sub(r'(<pre class="wp-block-preformatted">)(.*?)(</pre>)',r'\1<p>\2</p>\3', html, 0, re.DOTALL) # inkstainedcharm
    html = re.sub(r'(<pre class="wp-block-verse">)(.*?)(</pre>)', r'\1<p>\2</p>\3', html, 0,
                  re.DOTALL)  # novel98tl
    html = re.sub('FOOTNOTE_PLACEHOLDER', make_footnote_counter(), html)
    return html

def html_str_substitutions_dividers(html):
    html = html.replace('<hr', "<p>---</p><hr")
    return html

def html_str_substitutions_for_removing_wordpress_links(html):
    xpaths = ["//*[contains(@class, 'related') or contains(@class, 'sd-') or contains(@class, 'post-navigation') or contains(@class, 'pp-multiple-authors')]"]
    return remove_from_html_by_xpath(html, xpaths)


def remove_from_html_by_xpath(html, xpaths):
    if not xpaths:
        return html
    tree = lh.fromstring(html)
    for x in xpaths:
        # print(x)
        for bad in tree.xpath(x):
            bad.drop_tree()
    return lh.tostring(tree, encoding="unicode")  #if encoding is anything besides "unicode" a byte object is returned


def move_footnote_to_bottom(html, footnote_xpath):
    tree = et.ElementTree(lh.fromstring(html))
    root = tree.getroot()
    for footnote in tree.xpath(footnote_xpath):
        # need to leave a footnote counter [1] behind, ahead of a tail
        footnote.drop_tree() # drop element from original position but keeps tail
        tailless_copy = et.tostring(deepcopy(footnote), with_tail=False, encoding="unicode") # use tostring's with_tail parameter to remove tail
        footnote_text = bs(tailless_copy, "lxml").getText() # get footnote text, prepend footnote number insertion, move footnote to end of html
        root.append(lh.fromstring('<p>FOOTNOTE_PLACEHOLDER '+footnote_text+'</p>'))
    return lh.tostring(tree, encoding="unicode")


def html_add_brackets_around_superscript(html):
    html = html.replace('</sup>', "]")
    html = re.sub(r'<sup.*?>', r'[', html)
    return html


def decrypt(encoded):
    #decrypts chrysanthemum garden's text scrambling
    keyMap = dict(zip('jymvfoutlpxiwcbqdgraenkzshCDJGSMXLPABOZRYUHEVKFNQWTI', 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ')) #chrysanthemum
    return ''.join(keyMap.get(c, c) for c in encoded)


def enter_pwd(driver, pwd, pwd_field_path, submit_btn_xpath):
    WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, pwd_field_path)))
    pwd_field_element = driver.find_element(By.XPATH, pwd_field_path)
    # enter pwd and press Enter
    pwd_field_element.send_keys(pwd)
    driver.find_element(By.XPATH, submit_btn_xpath).click()

# def url_check(url):
#     return True

def close_chapter(file):
    file.write("----------------------------------")


def main(first_ch_url, output_filename, body_xpath, chapter_header_xpath ='', next_ch_button_xpath ='', title_must_contain ='', tags =['h1', 'h2', 'h3', 'p', 'cite'], remove_xpath ='', footnote_xpath =''):
    # open output file
    f = open(output_filename, "a", encoding="utf-8")
    # start web crawler
    driver = start_driver()
    driver.get(first_ch_url)

    #time.sleep(20)

    # # Enter text in pwd box
    # WebDriverWait(driver, 10).until(
    #     EC.presence_of_element_located((By.XPATH, "//p/a[contains(@href,'') and contains(text(),'here')]")))
    # driver.find_element(By.XPATH, "//p/a[contains(@href,'') and contains(text(),'here')]").click()

    # press change language to trad chinese
    if first_ch_url.startswith('http://www.jjwxc.net/'):
        try:
            driver.find_element(By.XPATH, "//a [text() = '繁體版' or text() = '繁体版']").click()
        except NoSuchElementException:
            print("No switch to traditional chinese button")

    next_page_exists = True

    while next_page_exists:

        #### GENERAL PAGE LOADING STEPS ####

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

        #exclude if header text does not match criteria
        if title_must_contain and not chapter_header_xpath:
            print('In order to user filter by header feature (--filter_header, -f) please supply a header (--header, -head)')
            break
        elif chapter_header_xpath and title_must_contain and (title_must_contain not in driver.find_element(By.XPATH, chapter_header_xpath).text):
            print("Skipping current page: " + driver.find_element(By.XPATH, chapter_header_xpath).text)
            next_page_url = driver.find_element(By.XPATH, next_ch_button_xpath).get_attribute('href')
            print("prodeeding to next page: " + next_page_url)
            driver.get(next_page_url)
            continue


        #### write chapter title ####
        f.write('\n')
        if chapter_header_xpath:
            try:
                header_wait = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, chapter_header_xpath)))
                f.write(driver.find_element(By.XPATH, chapter_header_xpath).text)
                f.write('\n\n')
            except NoSuchElementException:
                print("Header not found")

        #### scraping body ####

        if first_ch_url.startswith('http://www.jjwxc.net/') or first_ch_url.startswith(
                'https://www.oldtimescc.cc/'):
            html = get_body_text(driver, body_xpath)
            soup = bs(html, "lxml")
            f.write('\n')
            f.write(driver.find_element(By.XPATH, body_xpath).text)
            f.write('\n')
        elif first_ch_url.startswith('https://www.babayu.com/'):
            # general pattern: chapters split over multiple pages
            still_on_curr_chapter = True
            while still_on_curr_chapter:
                #write segment of chapter
                html = get_body_text(driver, body_xpath)
                soup = bs(html, "lxml")
                all_p = soup.find_all(['p'])
                for p in all_p:
                    p = str(p).replace("<br/>", "\n")
                    p = re.sub(r'<span class="num-comment">.*?</span>', "", p, flags=re.DOTALL)
                    f.write(bs(p, "lxml").getText())
                    f.write('\n')

                #compare URLS to see if next page is also part of segment
                this_page_url = driver.current_url
                next_page_url = driver.find_element(By.XPATH, next_ch_button_xpath).get_attribute('href')
                this_page_chapter = re.findall(r'\d+', this_page_url)[1]
                next_page_chapter = re.findall(r'\d+', next_page_url)[1]
                if this_page_chapter == next_page_chapter:
                    driver.get(next_page_url)
                else:
                    still_on_curr_chapter = False

            # add author's note to end of chapter
            try:
                f.write(driver.find_element(By.XPATH, "//div[@class='authorsay']").text)
                f.write('\n')
            except NoSuchElementException:
                print("No Author's Note found for this chapter")


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

            #enter pwd
            pwd_submit_buttons = driver.find_elements(By.XPATH,"//input[@value='Submit password']")
            if len(pwd_submit_buttons)>0:
                pwd = "ItsGettingKindOfHot"
                enter_pwd(driver, pwd, "//input[@name='site-pass']", "//input[@value='Submit password']")

            html = get_body_text(driver, body_xpath)
            html = remove_from_html_by_xpath(html, ["//*[contains(@style, 'hidden')]"])
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
                # p = re.sub(r"(<[a-z]*? style=.*?>.*?</[a-z]*?>) <[a-z]*? style=.*?hidden.*?>.*?</[a-z]*?>", r"\1",
                #            p, flags=re.DOTALL)
                # p = re.sub(r"<[a-z]*? style=.*?hidden.*?>.*?</[a-z]*?>", "", p, flags=re.DOTALL) #should be taken care of by remove by xpath function above
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

        elif tags == 'no_tags':
            html = get_body_text(driver, body_xpath)
            if footnote_xpath:
                html = move_footnote_to_bottom(html, footnote_xpath)
            html = html_str_substitutions_for_removing_wordpress_links(html)
            if remove_xpath:
                html = remove_from_html_by_xpath(html, [remove_xpath])
            html = html_str_substitutions_for_footnote_formatting(html)
            html = html_add_brackets_around_superscript(html)
            html = html.replace("<br/>", "<p>\n</p>")
            html = html.replace("<br>", "<p>\n</p>")
            f.write(bs(html, "lxml").getText())
            f.write('\n')
        else:
            # pwd_submit_buttons = driver.find_elements(By.XPATH, "//input[@value='Enter']")
            # if len(pwd_submit_buttons) > 0:
            #     pwd = "3028499"
            #     enter_pwd(driver, pwd, "//input[@name='post_password']", "//input[@value='Enter']")

            html = get_body_text(driver, body_xpath)
            if footnote_xpath:
                html = move_footnote_to_bottom(html, footnote_xpath)
            html = html_str_substitutions_for_removing_wordpress_links(html)
            if remove_xpath:
                html = remove_from_html_by_xpath(html, [remove_xpath])
            html = html_str_substitutions_for_footnote_formatting(html)
            html = html_str_substitutions_dividers(html)
            soup = bs(html, "lxml")
            all_p = soup.find_all(tags)
            for p in all_p:
                p = str(p).replace("<br/>", "\n")
                p = html_add_brackets_around_superscript(p)
                f.write(bs(p, "lxml").getText())
                f.write('\n\n')

            # write Translator's Notes
        close_chapter(f)


        # Is there a next page?
        try:
            next_page_url = driver.find_element(By.XPATH, next_ch_button_xpath).get_attribute('href')
            #driver.find_element(By.XPATH, next_ch_button_xpath).click()
            # url_check: raise error if url is already visited
            driver.get(next_page_url)
            print("prodeeding to next page: " + next_page_url)
            #time.sleep(5)

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
    parser.add_argument("--filter_header", "-f", help="only scrapes page if header contains the following text")
    parser.add_argument("--scrape_tags", "-t", help="Which tags to will be scraped with BeautifulSoup.  Default is ['h1', 'h2', 'h3', 'p', 'cite'].  Use \"no_tags\" to not use BeautifulSoup in cases where text is in the root node.")
    parser.add_argument("--remove", "-rm", help="supply xpath of elements to remove as a list, ex. ['//h1'] or ['//h1','//h2']")
    parser.add_argument("--footnote", "-fn",
                        help="supply xpath of elements to move to bottom, ex. ['//h1'] or ['//h1','//h2']")
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
    if args.filter_header:
        title_must_contain = args.filter_header
    else:
        title_must_contain = ''
    if args.scrape_tags:
        tags = args.scrape_tags
    else:
        tags = ['h1', 'h2', 'h3', 'p', 'cite']
    if args.remove:
        remove_xpath = args.remove
    else:
        remove_xpath = ''
    if args.footnote:
        footnote_xpath = args.footnote
    else:
        footnote_xpath = ''

    main(first_ch_url, output_filename, body_xpath, chapter_header_xpath, next_ch_button_xpath, title_must_contain, tags, remove_xpath, footnote_xpath)

