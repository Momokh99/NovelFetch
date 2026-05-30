import requests
from bs4 import BeautifulSoup

url = "https://novelbin.com/b/lord-of-the-mysteries/"

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


print("Fetching documentation..")
Response = requests.get(url, headers=headers)

soup = BeautifulSoup(Response.text, "html.parser")

main_cont = soup.find("div", class_="chr-c")

if main_cont:
    for paragraph in main_cont.find_all("p"):
        print(paragraph.text)
