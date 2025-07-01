# scraper.py
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import pandas as pd
import streamlit as st
import time
from requests import get
from bs4 import BeautifulSoup as bs


def scrape_data(url, nb_pages=3):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    all_data = []

    for page in range(1, nb_pages + 1):
        full_url = f"{url}?page={page}"
        driver.get(full_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")

        annonces = soup.find_all("article")

        for a in annonces:
            try:
                titre = a.find("h2").text.strip()
                infos = a.find_all("li")
                prix = a.find(class_="price").text.strip()
                img = a.find("img")["src"]

                row = {"détails": titre, "prix": prix, "image_lien": img}

                for info in infos:
                    txt = info.text.lower()
                    if "chambre" in txt:
                        row["chambre"] = txt
                    elif "bain" in txt:
                        row["salle_bain"] = txt
                    elif "m²" in txt:
                        row["superficie"] = txt
                    elif "quartier" in txt or "adresse" in txt:
                        row["adresse"] = txt
                all_data.append(row)
            except:
                continue

    driver.quit()
    return pd.DataFrame(all_data)

def scrap_data(url):
    html_code= get(url)
    soup=bs(html_code.text,"html.parser")
    containers =soup.find_all("div",class_ ="col s6 m4 l3")
    paginations =soup.find("li",class_="pagination-number")

    data =[]
    for page in range(len(paginations)):
        for container in containers:
            try:
                title =container.find("p", class_="ad__card-description").a.text
                price =container.find("p",class_="ad__card-price").a.text
                adress =container.find("p", class_="ad__card-location").span.text
                img_src=container.find("img",class_="ad__card-img").get("src")
            
                dic={
                    "title":title,
                    "price":price,
                    "adress":adress,
                    "img-url":img_src
                }
                data.append(dic)
            except:
                pass

    df = pd.DataFrame(data)
    df.dropna()
