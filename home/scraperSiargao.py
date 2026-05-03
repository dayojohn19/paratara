from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import csv
import json
# Chrome options
def SiargaoScrapper():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # run in background
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    # chrome_options = Options()
    # chrome_options.add_argument("--headless")  # remove or comment this
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    # Initialize driver (system chromedriver)
    # driver = webdriver.Chrome(options=chrome_options)
    driver = webdriver.Safari()
    # driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
    #     "source": """
    #     Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    #     """
    # })
    url = "https://siargaovibes.com/explore/?type=event&sort=random"
    driver.get(url)

    # Wait for JS to render
    time.sleep(35)

    # Confirm page loaded
    print("Page title:", driver.title)

    # Select all grid items
    grid_items = driver.find_elements(By.CSS_SELECTOR, ".results-view.grid .grid-item")
    print(f"Found {len(grid_items)} items.")
    csv_file = "siargao_events.csv"
    csv_columns = [
        "Title", "Link", "Background", "Thumbnail", "Marker",
        "Location", "Date", "Host Name", "Host Link", "Locations JSON"
    ]

    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_columns)
        writer.writeheader()

        for item in grid_items:
            # Basic info
            title = item.find_element(By.CSS_SELECTOR, ".listing-preview-title").text
            link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
            
            # Background image
            background_div = item.find_element(By.CSS_SELECTOR, ".lf-background")
            background_url = background_div.value_of_css_property("background-image")
            
            # Data attributes
            thumbnail = item.get_attribute("data-thumbnail")
            marker = item.get_attribute("data-marker")
            data_locations = item.get_attribute("data-locations")
            locations = json.loads(data_locations) if data_locations else []
            
            # Contact info
            contact_li = item.find_elements(By.CSS_SELECTOR, ".lf-contact li")
            location_text = contact_li[0].text if len(contact_li) > 0 else ""
            date_text = contact_li[1].text if len(contact_li) > 1 else ""
            
            # Host info
            host_name = ""
            host_link = ""
            try:
                host_el = item.find_element(By.CSS_SELECTOR, ".event-host .host-name")
                host_name = host_el.text
                host_link = host_el.find_element(By.XPATH, "..").get_attribute("href")
            except:
                pass

            writer.writerow({
                "Title": title,
                "Link": link,
                "Background": background_url,
                "Thumbnail": thumbnail,
                "Marker": marker,
                "Location": location_text,
                "Date": date_text,
                "Host Name": host_name,
                "Host Link": host_link,
                "Locations JSON": json.dumps(locations, ensure_ascii=False)
            })

    driver.quit()
    print(f"Data saved to {csv_file}")