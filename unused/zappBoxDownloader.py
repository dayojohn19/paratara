from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import os

# === CONFIG ===
shared_folder_url = 'https://app.box.com/s/yp7ndu8us80l6yhnk8nkq71vzlhgsd02/folder/187500886350'

# Download folder path — change to your preferred path
download_dir = os.path.abspath('box_downloads')

if not os.path.exists(download_dir):
    os.makedirs(download_dir)

# === SETUP CHROME OPTIONS ===
chrome_options = Options()
chrome_options.add_argument('--headless')  # comment this out if you want to watch the browser
chrome_options.add_experimental_option('prefs', {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True
})

# Path to your ChromeDriver executable (update if needed)
chromedriver_path = 'chromedriver'  # or full path like 'C:/path/to/chromedriver.exe'

# driver = webdriver.Chrome(executable_path=chromedriver_path, options=chrome_options)

chromedriver_path = 'chromedriver'  # or full path to chromedriver.exe
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
chrome_options = Options()
chrome_options.add_argument('--headless')

service = Service(executable_path=chromedriver_path)
driver = webdriver.Chrome(service=service, options=chrome_options)

try:
    print(f"Opening folder: {shared_folder_url}")
    driver.get(shared_folder_url)
    time.sleep(5)  # wait for page load

    # Scroll down to load all files (adjust scroll count if needed)
    for _ in range(5):
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(1)

    # Find all file rows with download buttons
    files = driver.find_elements(By.CSS_SELECTOR, 'div.item-row')
    print(f"Found {len(files)} items on the page.")

    for i, file_row in enumerate(files, 1):
        try:
            file_name = file_row.find_element(By.CSS_SELECTOR, 'div.name').text
            print(f"[{i}] Processing file: {file_name}")

            # Find the dropdown menu button for file actions
            menu_btn = file_row.find_element(By.CSS_SELECTOR, 'button.item-actions-button')
            menu_btn.click()
            time.sleep(1)

            # Find the "Download" button inside dropdown menu
            download_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Download')]")
            download_btn.click()

            print(f"Downloading '{file_name}'...")

            # Wait enough time for download to start before continuing
            time.sleep(10)

        except Exception as e:
            print(f"Skipping file {file_name} due to error: {e}")

finally:
    driver.quit()
    print(f"All done. Files should be downloaded to: {download_dir}")
