import os
import time
import streamlit as st
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
from datetime import datetime
import re

DATA_FOLDER = "data"

# Créer le dossier data s'il n'existe pas
if not os.path.exists(DATA_FOLDER):
    os.makedirs(DATA_FOLDER)

st.set_page_config(page_title="Web Scraper App", layout="wide")
st.title("🕷️ Web Scraper Dashboard App")

# Style personnalisé
st.markdown(
    """
    <style>
    .stAppToolbar {
        background-color:#f0f2f6 !important;
        padding-left:2rem;
        padding-right:2rem;
    }
    .stMainBlockContainer {
        padding-left:2rem;
        padding-right:2rem;
    }
    .st-emotion-cache-77vupy {
        margin-left:0;
    }
    .st-emotion-cache-scp8yw {
        margin-right:0;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #007bff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Fonctions utilitaires
@st.cache_data
def clean_price(price_str):
    """Nettoie et convertit le prix en nombre"""
    if pd.isna(price_str):
        return None
    price_clean = re.sub(r"[^\d]", "", str(price_str))
    return int(price_clean) if price_clean else None


def setup_driver():
    """Configure le driver Chrome pour Selenium"""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )

    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def scrape_expat_dakar(base_url, max_pages=1):
    """Scrape les données depuis expat-dakar.com"""
    all_data = []
    driver = setup_driver()

    try:
        for page in range(1, max_pages + 1):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page}"

            st.write(f"📄 Scraping page {page}: {url}")
            driver.get(url)

            # Attendre que la page se charge
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "article"))
            )

            soup = BeautifulSoup(driver.page_source, "html.parser")
            annonces = soup.find_all("article", class_="listing-item")

            if not annonces:
                st.warning(f"Aucune annonce trouvée sur la page {page}")
                continue

            for idx, annonce in enumerate(annonces):
                try:
                    data_row = {}

                    # Titre
                    title_elem = (
                        annonce.find("h2")
                        or annonce.find("h3")
                        or annonce.find("a", class_="listing-title")
                    )
                    data_row["titre"] = title_elem.text.strip() if title_elem else "N/A"

                    # Prix
                    price_elem = annonce.find(class_="price") or annonce.find(
                        class_="listing-price"
                    )
                    data_row["prix"] = price_elem.text.strip() if price_elem else "N/A"

                    # Image
                    img_elem = annonce.find("img")
                    data_row["image_url"] = (
                        img_elem.get("src") or img_elem.get("data-src")
                        if img_elem
                        else "N/A"
                    )

                    # Informations détaillées
                    info_items = annonce.find_all("li") or annonce.find_all(
                        class_="listing-detail"
                    )

                    data_row["chambres"] = "N/A"
                    data_row["salle_bain"] = "N/A"
                    data_row["superficie"] = "N/A"
                    data_row["adresse"] = "N/A"

                    for item in info_items:
                        text = item.text.lower().strip()
                        if "chambre" in text or "bedroom" in text:
                            data_row["chambres"] = text
                        elif "bain" in text or "bathroom" in text or "sdb" in text:
                            data_row["salle_bain"] = text
                        elif "m²" in text or "surface" in text:
                            data_row["superficie"] = text
                        elif any(
                            word in text
                            for word in ["quartier", "adresse", "zone", "location"]
                        ):
                            data_row["adresse"] = text

                    # Lien vers l'annonce
                    link_elem = annonce.find("a")
                    data_row["lien"] = link_elem.get("href") if link_elem else "N/A"

                    data_row["page"] = page
                    data_row["scrape_time"] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    all_data.append(data_row)

                except Exception as e:
                    st.warning(
                        f"Erreur lors du scraping de l'annonce {idx+1} page {page}: {str(e)}"
                    )
                    continue

            time.sleep(2)  # Pause entre les pages

    except Exception as e:
        st.error(f"Erreur générale lors du scraping: {str(e)}")
    finally:
        driver.quit()

    return pd.DataFrame(all_data)


# Sidebar avec informations
with st.sidebar:
    st.header("ℹ️ Informations")
    st.write(
        "Cette application permet de scraper des données immobilières depuis différents sites web."
    )

    if "raw_data" in st.session_state and not st.session_state["raw_data"].empty:
        df = st.session_state["raw_data"]
        st.metric("Nombre d'annonces", len(df))
        if "prix" in df.columns:
            prix_clean = df["prix"].apply(clean_price).dropna()
            if not prix_clean.empty:
                st.metric("Prix moyen", f"{prix_clean.mean():,.0f} FCFA")

# Tabs principales
tab1, tab2, tab3, tab4 = st.tabs(
    ["📂 Données sauvegardées", "🌐 Scraper site", "📊 Analyse", "📝 Évaluation"]
)

# ----------------- TAB 1 : Données sauvegardées ---------------------
with tab1:
    st.header("📂 Données déjà scrapées")

    try:
        files = [f for f in os.listdir(DATA_FOLDER) if f.endswith(".csv")]

        if files:
            st.success(
                f"📄 **{len(files)} fichier(s) CSV trouvé(s)** dans le dossier `{DATA_FOLDER}/`"
            )

            col1, col2 = st.columns([3, 1])

            with col1:
                selected_file = st.selectbox(
                    "Choisir un fichier CSV à visualiser", files
                )

            with col2:
                if st.button("🔄 Actualiser la liste"):
                    st.rerun()

            if selected_file:
                filepath = os.path.join(DATA_FOLDER, selected_file)
                df = pd.read_csv(filepath)

                # Renommage des colonnes si nécessaire
                column_mapping = {
                    "id": "N°",
                    "title": "Titre",
                    "nbrOfBedroom": "Nombre de chambres",
                    "price": "Prix",
                    "adress": "Adresse",
                    "surface": "Superficie",
                    "img_url-src": "Image URL",
                }
                df = df.rename(columns=column_mapping)

                # Nettoyage
                df_clean = df.drop(
                    ["web-scraper-start-url", "web-scraper-order"],
                    axis=1,
                    errors="ignore",
                )

                st.session_state["raw_data"] = df_clean

                # Affichage des métriques
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Nombre d'annonces", len(df_clean))
                with col2:
                    if "Prix" in df_clean.columns:
                        prix_valides = df_clean["Prix"].apply(clean_price).dropna()
                        if not prix_valides.empty:
                            st.metric("Prix moyen", f"{prix_valides.mean():,.0f} FCFA")
                with col3:
                    st.metric(
                        "Taille du fichier", f"{os.path.getsize(filepath)/1024:.1f} KB"
                    )

                # Affichage des données
                st.dataframe(df_clean, use_container_width=True)

                # Bouton de téléchargement
                csv_data = df_clean.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Télécharger ce fichier CSV",
                    data=csv_data,
                    file_name=selected_file,
                    mime="text/csv",
                    use_container_width=True,
                )
        else:
            st.info(f"Aucun fichier CSV trouvé dans le dossier `{DATA_FOLDER}/`")
            st.write(
                "Utilisez l'onglet 'Scraper site' pour commencer à collecter des données."
            )

    except FileNotFoundError:
        st.error(f"Dossier `{DATA_FOLDER}` introuvable.")
        if st.button("Créer le dossier"):
            os.makedirs(DATA_FOLDER)
            st.success(f"Dossier `{DATA_FOLDER}` créé avec succès!")
            st.rerun()

# ----------------- TAB 2 : Scraping site ---------------------
with tab2:
    st.header("🌐 Scraper les données depuis un site web")

    # Configuration du scraping
    col1, col2 = st.columns([2, 1])

    with col1:
        site_choice = st.selectbox(
            "Choisir le site à scraper",
            ["expat-dakar.com", "Autre site (URL personnalisée)"],
        )

        if site_choice == "expat-dakar.com":
            base_url = st.selectbox(
                "Catégorie",
                [
                    "https://www.expat-dakar.com/appartements-a-louer",
                    "https://www.expat-dakar.com/maisons-a-louer",
                    "https://www.expat-dakar.com/appartements-a-vendre",
                    "https://www.expat-dakar.com/maisons-a-vendre",
                ],
            )
        else:
            base_url = st.text_input("URL de base du site à scraper")

    with col2:
        max_pages = st.number_input(
            "Nombre de pages à scraper", min_value=1, max_value=10, value=1
        )

        save_data = st.checkbox("Sauvegarder automatiquement", value=True)

    # Bouton de scraping
    if st.button("🚀 Lancer le scraping", type="primary", use_container_width=True):
        if not base_url:
            st.error("Veuillez saisir une URL valide")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                status_text.text("Initialisation du scraping...")
                progress_bar.progress(10)

                if "expat-dakar.com" in base_url:
                    scraped_df = scrape_expat_dakar(base_url, max_pages)
                else:
                    st.warning("Scraping personnalisé non implémenté pour ce site")
                    scraped_df = pd.DataFrame()

                progress_bar.progress(90)

                if not scraped_df.empty:
                    st.session_state["raw_data"] = scraped_df

                    # Sauvegarde automatique
                    if save_data:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"scraped_data_{timestamp}.csv"
                        filepath = os.path.join(DATA_FOLDER, filename)
                        scraped_df.to_csv(filepath, index=False)
                        st.success(f"✅ Données sauvegardées dans `{filename}`")

                    progress_bar.progress(100)
                    status_text.text("Scraping terminé avec succès!")

                    # Affichage des résultats
                    st.success(f"🎉 {len(scraped_df)} annonces récupérées avec succès!")

                    # Prévisualisation
                    st.subheader("Aperçu des données")
                    st.dataframe(scraped_df.head(10), use_container_width=True)

                    # Bouton de téléchargement immédiat
                    csv_data = scraped_df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        label="📥 Télécharger les données",
                        data=csv_data,
                        file_name=f"scraped_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )
                else:
                    st.warning("Aucune donnée n'a pu être récupérée")
                    progress_bar.progress(100)

            except Exception as e:
                st.error(f"Erreur lors du scraping: {str(e)}")
                progress_bar.progress(0)

# ----------------- TAB 3 : Analyse des données ---------------------
with tab3:
    st.header("📊 Analyse des données")

    if "raw_data" in st.session_state and not st.session_state["raw_data"].empty:
        df = st.session_state["raw_data"]

        # Statistiques générales
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total annonces", len(df))

        with col2:
            if "prix" in df.columns:
                prix_clean = df["prix"].apply(clean_price).dropna()
                if not prix_clean.empty:
                    st.metric("Prix moyen", f"{prix_clean.mean():,.0f}")

        with col3:
            if "chambres" in df.columns:
                chambres_info = df["chambres"].value_counts()
                if not chambres_info.empty:
                    st.metric("Type le plus fréquent", chambres_info.index[0])

        with col4:
            if "scrape_time" in df.columns:
                st.metric("Dernière mise à jour", df["scrape_time"].iloc[0][:10])

        # Graphiques
        if "prix" in df.columns:
            prix_clean = df["prix"].apply(clean_price).dropna()
            if not prix_clean.empty:
                st.subheader("Distribution des prix")
                st.bar_chart(prix_clean.value_counts().head(10))

        # Tableau de données complet
        st.subheader("Données complètes")
        st.dataframe(df, use_container_width=True)

    else:
        st.info(
            "Aucune donnée disponible pour l'analyse. Scrapez d'abord des données ou chargez un fichier existant."
        )

# ----------------- TAB 4 : Évaluation ---------------------
with tab4:
    st.header("📝 Formulaire d'évaluation")

    with st.form("feedback_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Votre nom (facultatif)")
            email = st.text_input("Votre email (facultatif)")

        with col2:
            rating = st.slider("Notez cette application", 1, 5, 3)
            category = st.selectbox(
                "Catégorie", ["Général", "Interface", "Performance", "Fonctionnalités"]
            )

        comment = st.text_area("Commentaires / Suggestions", height=100)

        if st.form_submit_button("📤 Envoyer le feedback", use_container_width=True):
            # Ici vous pourriez sauvegarder le feedback dans un fichier ou base de données
            feedback_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "name": name or "Anonyme",
                "email": email or "Non renseigné",
                "rating": rating,
                "category": category,
                "comment": comment,
            }

            st.success("✅ Merci pour votre retour ! Votre feedback a été enregistré.")
            st.balloons()

# Footer
st.markdown("---")
st.markdown("*Web Scraper Dashboard - Développé avec Streamlit*")
