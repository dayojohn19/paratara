from bs4 import BeautifulSoup
import requests


def get_google_img(query):
    """
    gets a link to the first google image search result
    :param query: search query string
    :result: url string to first result
    """
    # url = "https://www.google.com/search?q=" + str(query) + "&source=lnms&tbm=isch"
    url = "https://keywordimage.com/image.php?q=" + str(query)
    headers={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    html = requests.get(url, headers=headers).text
    soup = BeautifulSoup(html, 'html.parser')
    xx = soup.find_all("img")
    # print(xx[0]['src'])
    return xx[0]['src']


# if __name__ == '__main__':
#     query = input("search term\n")
#     print(get_google_img(query) or "no image found")

# get_google_img('Pegro Gil Avenue')