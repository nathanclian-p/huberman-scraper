from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from readability import Document
import json
import os
import time

BASE_URL = "https://www.hubermanlab.com/topics"
BASE_DOMAIN = "https://www.hubermanlab.com"

OUTDIR = "huberman_resources"
os.makedirs(OUTDIR, exist_ok=True)


def collect_topic_links(driver):
    driver.get(BASE_URL)
    time.sleep(5)

    # Find all topic cards
    links = driver.find_elements(By.CSS_SELECTOR, "a.topic-card")
    topics = []

    for link in links:
        href = link.get_attribute("href")
        try:
            title_elem = link.find_element(By.CSS_SELECTOR, "h3")
            title = title_elem.text.strip()
        except:
            title = "Untitled"

        if href and title:
            full_url = href if href.startswith("http") else BASE_DOMAIN + href
            topics.append({
                "title": title,
                "url": full_url
            })

    print(f"Found {len(topics)} topics.")
    return topics


def scrape_resources(driver, topic):
    driver.get(topic["url"])
    time.sleep(3)

    page_html = driver.page_source
    soup = BeautifulSoup(page_html, "html.parser")

    resources_div = soup.find("div", class_="topics_resources-rich-text")
    all_resources = []

    if resources_div:
        current_section = None

        for elem in resources_div.find_all(["h4", "ul"]):
            if elem.name == "h4":
                current_section = elem.get_text(strip=True)

            elif elem.name == "ul":
                for li in elem.find_all("li"):
                    link = li.find("a")
                    em = li.find("em")
                    text_after = li.get_text(" ", strip=True)

                    resource = {
                        "section": current_section,
                        "title": None,
                        "url": None,
                        "source_info": None,
                        "full_text": text_after,
                        "clean_text_file": None
                    }

                    if link:
                        resource["title"] = link.get_text(strip=True)
                        resource["url"] = link.get("href")

                    if em:
                        resource["source_info"] = em.get_text(strip=True)

                    all_resources.append(resource)

    print(f"Topic '{topic['title']}' → found {len(all_resources)} resources.")
    return all_resources


def download_clean_text_with_selenium(driver, url, save_dir, title_safe):
    """
    Loads a resource page in Selenium and extracts clean text using Readability.
    """
    try:
        driver.get(url)
        time.sleep(5)

        page_html = driver.page_source

        # Run readability on the HTML
        doc = Document(page_html)
        clean_html = doc.summary()

        # Extract readable text
        clean_text = BeautifulSoup(clean_html, "html.parser").get_text(separator="\n", strip=True)

        filename = os.path.join(save_dir, title_safe + ".txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(clean_text)

        print(f"✅ Clean text extracted for: {url}")
        return filename

    except Exception as e:
        print(f"Failed to extract clean text with Selenium from {url}: {e}")
        return None


def main():
    options = Options()
    # REMOVE comment below to run headless
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)

    all_data = []

    topics = collect_topic_links(driver)

    for topic in topics:
        resources = scrape_resources(driver, topic)

        for resource in resources:
            url = resource.get("url")
            title = resource.get("title")
            if url and title:
                safe_title = "".join(c if c.isalnum() else "_" for c in title)[:80]

                save_folder = os.path.join(OUTDIR, "resource_texts")
                os.makedirs(save_folder, exist_ok=True)

                text_file = download_clean_text_with_selenium(driver, url, save_folder, safe_title)
                resource["clean_text_file"] = text_file

        all_data.append({
            "topic_title": topic["title"],
            "topic_url": topic["url"],
            "resources": resources
        })

    driver.quit()

    output_path = os.path.join(OUTDIR, "huberman_resources_with_clean_text.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    print(f"Scraping complete. Data saved to {output_path}")


if __name__ == "__main__":
    main()