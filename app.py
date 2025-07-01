import os
import time
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup as bs
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import re
import uuid
from requests import get

DATA_FOLDER = "data"
KOBOTOOLBOX_TOKEN = "b9213902dbef007b15c310d7c87db94cbb1c42a6"
ASSET_UID = "au8WkpWicrphysLDaMHFWL"
INSTANCE_ID = uuid.uuid4()

st.set_page_config(page_title="Web Scraper App", layout="wide", page_icon="🕷️")
st.title("🕷️ Web Scraper Dashboard App")
st.logo("./assets/logo.svg", size="large")

# # Style custom
st.markdown(
    """
    <style>
    .stAppHeader{
    position: relative;
    }
    .stAppToolbar {
        background-color:#f0f2f6 !important;
        padding-left:2rem;
        padding-right:2rem;
    }
    .stMainBlockContainer {
        padding-left:2rem;
        padding-right:2rem;
        padding-top:0;
        position: relative;
    }
    .st-emotion-cache-77vupy {
        margin-left:0;
    }
    .st-emotion-cache-scp8yw {
        margin-right:0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def send_to_kobo(name, rating, comment):
    url = "https://kc.kobotoolbox.org/api/v1/submissions"
    headers = {
        "Authorization": f"Token {KOBOTOOLBOX_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "id": "au8WkpWicrphysLDaMHFWL",
        "submission": {
            "meta": {"instanceId": str(INSTANCE_ID)},
            "Votre_nom": name,
            "Noter_l_application_de_1_a_10": rating,
            "Votre_commentaire": comment,
        },
    }
    response = requests.post(url, json=payload, headers=headers, verify=True)
    return response.status_code == 201


# @st.cache_data
def clean_price(price_str):
    if pd.isna(price_str):
        return None
    price_clean = re.sub(r"[^\d]", "", str(price_str))
    return int(price_clean) if price_clean else None


# # Fonction de nettoyage
# def clean_data(df):
#     df_clean = df.copy()
#     if "Prix" in df_clean.columns:
#         df_clean["Prix"] = (
#             df_clean["Prix"]
#             .str.replace(" FCFA", "")
#             .str.replace(" ", "")
#             .str.replace("\n", "")
#         )
#         df_clean["Prix"] = pd.to_numeric(df_clean["Prix"], errors="coerce")
#         df_clean = df_clean.dropna(subset=["Prix"])
#     return df_clean


# Tabs
tab1, tab2, tab3 = st.tabs(
    ["📂 Données sauvegardées", "🌐 Scraper site", "📝 Évaluation"]
)


# # ----------------- TAB 2 : Import fichier local ---------------------
with tab1:
    st.header("📂 Données déjà scrapées")
    try:
        files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".csv")]

        if files:
            st.markdown(
                f"📄 **{len(files)} fichier(s) CSV trouvé(s)** dans le dossier `data/`."
            )
            selected_file = st.selectbox("🗂️ Choisir un fichier CSV", files)

            if selected_file:
                filepath = os.path.join(DATA_FOLDER, selected_file)
                df = pd.read_csv(filepath).fillna("non disponible")
                dfclean = df.drop(
                    ["pagination", "web-scraper-order", "web-scraper-start-url"],
                    axis=1,
                    errors="ignore",
                )

                # Nettoyage des prix et superficie
                prix_valides = dfclean["prix"].apply(clean_price).dropna()

                # 📊 Statistiques en haut
                st.markdown("### 📊 Statistiques")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("📦 Annonces", len(dfclean))
                with col2:
                    st.metric(
                        "📏 Prix moyen",
                        (
                            f"{prix_valides.mean():0,.0f}"
                            if not prix_valides.empty
                            else "N/A"
                        ),
                    )
                with col3:
                    st.metric(
                        "📏 Prix max",
                        (
                            f"{prix_valides.max():,.0f}"
                            if not prix_valides.empty
                            else "N/A"
                        ),
                    )
                with col4:
                    st.metric(
                        "📈 Prix min",
                        (
                            f"{prix_valides.min():,.0f} FCFA"
                            if not prix_valides.empty
                            else "N/A"
                        ),
                    )

                # 🔽 Données en dessous
                st.divider()
                st.success(f"{selected_file} chargé avec succès ✅")
                st.dataframe(dfclean)

                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Télécharger ce fichier CSV",
                    data=csv_bytes,
                    file_name=selected_file,
                    mime="text/csv",
                )
        else:
            st.warning("⚠️ Aucun fichier CSV trouvé dans le dossier.")
    except FileNotFoundError:
        st.error(
            f"❌ Dossier `{DATA_FOLDER}` introuvable. Crée-le dans le répertoire du projet."
        )


# ----------------- TAB 3 : Scraping site ---------------------
with tab2:
    st.markdown(
        "<p style='font-size:1.5rem; color:black'>Scraper les données depuis un site</p>",
        unsafe_allow_html=True,
    )
    selected_url = st.selectbox(
        "Sélectionner un site à scraper",
        [
            " https://sn.coinafrique.com/categorie/vetements-homme",
            "https://sn.coinafrique.com/categorie/chaussures-homme",
            "https://sn.coinafrique.com/categorie/vetements-enfants",
            "https://sn.coinafrique.com/categorie/chaussures-enfants",
        ],
    )
    page_limit = st.slider("Nombre de pages à scraper", 1)
    if selected_url:
        if st.button("Lancer le scraping"):
            with st.spinner("Scraping en cours..."):
                base_url = f"{selected_url}?page="
                data = []

                for page in range(1, page_limit + 1):
                    full_url = f"{base_url}{page}"
                    html_code = get(full_url)
                    soup = bs(html_code.text, "html.parser")
                    containers = soup.find_all("div", class_="col s6 m4 l3")

                    for container in containers:
                        try:
                            title = container.find(
                                "p", class_="ad__card-description"
                            ).a.text
                            price = container.find("p", class_="ad__card-price").a.text
                            adress = container.find(
                                "p", class_="ad__card-location"
                            ).span.text
                            img_src = container.find("img", class_="ad__card-img").get(
                                "src"
                            )
                            dic = {
                                "type": title.strip(),
                                "prix": price.strip(),
                                "adresse": adress.strip(),
                                "image url": img_src,
                            }
                            data.append(dic)
                        except Exception as e:
                            print(f"Erreur sur la page {page}: {e}")
                            continue

                scraped_df = pd.DataFrame(data)
                st.session_state["raw_data"] = scraped_df
                st.success(f"{len(scraped_df)} lignes récupérées.")
                st.dataframe(scraped_df)

# ----------------- TAB 4 : Feedback ---------------------
with tab3:
    st.header("Formulaire d'évaluation")
    with st.form("feedback_form"):
        name = st.text_input("Votre nom (facultatif)")
        rating = st.slider("Notez cette application", 1, 5, 3)
        comment = st.text_area("Commentaires / Suggestions")
        if st.form_submit_button("Envoyer"):
            success = send_to_kobo(name, rating, comment)
            if success:
                st.success("Merci pour votre retour 💬 !")
                st.balloons()
            else:
                st.error(
                    f"❌ Erreur survenue lors de la soummission de votre evaluation merci de reesayer"
                )

st.markdown("---")
st.markdown("*Web Scraper Dashboard - Développé avec ❤️ par abdoul*")
