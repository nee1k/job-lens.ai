import time

import pymongo
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

def getdriver():
    path = '/Users/neeleshkarthikeyan/d2i/job-lens.ai/chromedriver-mac-arm64/chromedriver'
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    service = Service(path)
    driver = webdriver.Chrome(service=service, options=options)

    driver.implicitly_wait(10)
    driver.set_script_timeout(120)
    driver.set_page_load_timeout(30)

    return driver

def writePage(fname, content):
    with open(fname, "w", encoding="utf-8") as file:
        file.write(str(content))


def read_file(name):
    try:
        with open(name, "r", encoding="utf-8") as HTMLFile:
            htmlfiledata = HTMLFile.read()
            if not htmlfiledata.strip():
                print(f"File {name} is empty.")
                return None
            return BeautifulSoup(htmlfiledata, 'lxml')
    except Exception as e:
        print(f"Error reading file {name}: {e}")
        return None

def connect_mongodb(db_name, collection_name):
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client[db_name]
    collection = db[collection_name]
    return collection


def loadWebsiteData(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        page = requests.get(url, headers=headers)
        # Create a beautifulsoup object
        return BeautifulSoup(page.text, 'lxml')
    except:
        print("Error connecting to website")

def scroll_and_save(url, role):
    files_list = []
    driver = getdriver()
    driver.get(url)
    scroll_pause_time = 2
    screen_height = driver.execute_script("return window.screen.height;")
    i = 1
    link_num = 1

    while True:
        # Scroll down by one screen height
        driver.execute_script(f"window.scrollTo(0, {screen_height}*{i});")
        i += 1
        time.sleep(scroll_pause_time)

        # Check if "See more jobs" button is present and click it
        try:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'See more jobs')]"))
            )
            button.click()
            time.sleep(scroll_pause_time)
        except Exception as e:
            print(f"No 'See more jobs' button found: {e}")

        # Check if we've reached the bottom of the page
        scroll_height = driver.execute_script("return document.body.scrollHeight;")
        if (screen_height) * i > scroll_height:
            break

    # Save all job links
    links = driver.find_elements(By.CSS_SELECTOR, "a.base-card__full-link")
    if not links:
        print("No job links found. Check page source.")
        with open(f"debug_page_{role}.html", "w", encoding="utf-8") as file:
            file.write(driver.page_source)
        driver.quit()
        return []

    for link in links:
        try:
            href = link.get_attribute('href')
            print(f"Saving job posting: {href}")
            fname = f"{role}_{link_num}.html"
            files_list.append(fname)
            writePage(fname, loadWebsiteData(href))
            link_num += 1
        except Exception as e:
            print(f"Error saving job link: {e}")

    print(f"Total job links found: {len(links)}")
    driver.quit()
    return files_list

def parse_and_save(files_list):
    if not files_list:
        print("No files to parse.")
        return

    job_posting_list = []
    collection = connect_mongodb('job_postings', 'job_postings_data')

    for file in files_list:
        try:
            print(f"Parsing file: {file}")
            job_soup = read_file(file)

            # Extract details using updated selectors
            role = job_soup.select_one("h1.topcard__title").text.strip() if job_soup.select_one("h1.topcard__title") else 'NA'
            company = job_soup.select_one("a.topcard__org-name-link").text.strip() if job_soup.select_one("a.topcard__org-name-link") else 'NA'
            location = job_soup.select_one("span.topcard__flavor--bullet").text.strip() if job_soup.select_one("span.topcard__flavor--bullet") else 'NA'
            description = job_soup.select_one("div.show-more-less-html__markup").text.strip() if job_soup.select_one("div.show-more-less-html__markup") else 'NA'

            # Skip invalid postings
            if role == 'NA' or company == 'NA':
                print(f"Skipping invalid posting in file: {file}")
                continue

            posting = {
                'Job Role': role,
                'Company': company,
                'Location': location,
                'Job Description': description
            }
            job_posting_list.append(posting)

        except Exception as e:
            print(f"Error parsing file {file}: {e}")

    # Insert into MongoDB
    if job_posting_list:
        collection.insert_many(job_posting_list)
        print(f"Inserted {len(job_posting_list)} job postings into MongoDB.")
    else:
        print("No valid postings found.")

if __name__ == '__main__':
    datascience_url = "https://www.linkedin.com/jobs/search?keywords=data%20scientist&location=california&geoId=&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0"
    # dataanalyst_url = "https://www.linkedin.com/jobs/search/?currentJobId=3489147354&geoId=102095887&keywords=Data%20Analyst&location=California%2C%20United%20States&refresh=true"
    # businessanalyst_url = "https://www.linkedin.com/jobs/search?keywords=business%20analyst&location=california&geoId=&trk=public_jobs_jobs-search-bar_search-submit&position=1&pageNum=0"

    parse_and_save(scroll_and_save(datascience_url, 'ds'))
    # parse_and_save(scroll_and_save(dataanalyst_url, 'da'))
    # parse_and_save(scroll_and_save(businessanalyst_url, 'ba'))