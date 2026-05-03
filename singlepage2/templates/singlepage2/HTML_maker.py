from bs4 import BeautifulSoup
import requests
URL = 'https://guidetothephilippines.ph/articles/ultimate-guides/sagada-travel-guide'
page = requests.get(URL)
  
# load the page content
text = page.content
  
# make a soup object by using beautiful
# soup and set the markup as html parser
soup = BeautifulSoup(text, "html.parser")
with open("output.html", "w", encoding = 'utf-8') as file:
    
    # prettify the soup object and convert it into a string  
    file.write(str(soup.prettify()))