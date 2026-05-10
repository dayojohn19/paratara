url = "https://www.amazon.com/Bme-Ergonomic-Papasan-Density-Capacity/dp/B0BZ76WFNM/ref=sr_1_31?crid=1ETVKDYVR6APF&dib=eyJ2IjoiMSJ9.-TjwArvqTrnsksCNrjQybZyb2IQpJLAB_XmEEbNafrZ5oPROJqdXTa7IewZKa9VzJJSQPk9NIhH_x4v__Jo5bPNCkOyk2DuI6HfYSO1ECdHECJ5aSoX0MUIvR6I-iIi9643xlJ5j10Sk1-_zDk9LyLVeHKOkG8FQD0CrrRpauCO4Aw7tFd3dAU4yRVCPodoQkpwkwxY8_UeHWx6gmivSdrLojqedKz5JXfP9zoUr72SDQRvXijtU1anRj50wS76h4WL8_CfbWcCgYG5GQB0fMUyWFGI4zbXU3LHdLCzTjJs.Vxymnj6zZkZoh-N8-oS6DogQYDtpCSlns1ImbIAeLX4&dib_tag=se&keywords=chair&qid=1778381828&sprefix=chai%2Caps%2C391&sr=8-31&th=1"

import requests
from bs4 import BeautifulSoup

import requests
from bs4 import BeautifulSoup


def get_product_image(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=20)
    print("STATUS:", response.status_code)
    soup = BeautifulSoup(response.text, "html.parser")
    og = soup.find("meta", property="og:image")
    if og and og.get("content"):
        return og["content"]
    twitter = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter and twitter.get("content"):
        return twitter["content"]
    schema = soup.find("meta", itemprop="image")
    if schema and schema.get("content"):
        return schema["content"]
    images = soup.find_all("img")
    for img in images:
        src = img.get("src")
        if not src:
            continue
        src_lower = src.lower()
        skip_words = [
            "logo",
            "icon",
            "avatar",
            "banner",
            "ads",
            "tracking",
        ]
        if any(word in src_lower for word in skip_words):
            continue
        if src.startswith("//"):
            src = "https:" + src
        elif src.startswith("/"):
            from urllib.parse import urljoin
            src = urljoin(url, src)
        return src
    return None