#import requests
from bs4 import BeautifulSoup
from models.property_model import Property

#utilizando selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager


import time
import re
import requests
STEPS = 500
DELAY = 0.5

# type_property = ["casa", "apartamento", "apartaestudio"]
TYPE_PROPERTY = "casas"
# condition = ["venta", "arriendo"]
OPERATION = "venta"
# city = ["medellin", "envigado"]
CITY ="envigado"
#https://www.fincaraiz.com.co/{TYPE_PROPERTY}/{OPERATION}/{CITY}/
BASE_URL = f"https://www.fincaraiz.com.co/{TYPE_PROPERTY}/{OPERATION}/{CITY}/"

HEADERS = {
    "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape():
    print("scraping FincaRaiz...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--enable-unsafe-swiftshader')

    options.add_argument('--blink-settings=imagesEnabled=false')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(BASE_URL)
    time.sleep(5)

    full_html = ""
    is_next_disabled = False
    while not is_next_disabled:
        # Scroll infinito por página
        last_height = driver.execute_script("return document.body.scrollHeight")
        y_position = 0
        while y_position < last_height:
            driver.execute_script(f"window.scrollTo(0, {y_position});")
            time.sleep(DELAY)
            y_position += STEPS
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height > last_height:
                last_height = new_height  # Se cargó más contenido, seguir

        # Agregar contenido actual al HTML acumulado
        full_html += driver.page_source
        
        try:
            # Esperar a que el botón de ">" esté presente
            next_li = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, '//li[a[contains(@class, "ant-pagination-item-link") and normalize-space(text())=">"]]')))

            # Clic seguro al <a> dentro del <li>
            next_a = next_li.find_element(By.TAG_NAME, 'a')

            # Scroll al elemento y clic
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_a)
            driver.execute_script("arguments[0].click();", next_a)

            # Esperar opcional para carga
            time.sleep(5)    

        except TimeoutException:
            print("Botón siguiente no encontrado, fin de paginación.")
            is_next_disabled = True
            break
        except Exception as e:
            print(f"Se ha encontrado un error {e}")
            is_next_disabled = True  # No se encuentra el botón, fin de paginación

    driver.quit()

    if not full_html:
        raise ValueError("No se pudo obtener el HTML de la página")

    soup = BeautifulSoup(full_html, "html.parser")
    listings = soup.find_all("div", class_="listingCard")
    
    results = []
    count = 0
    for listing in listings:
        try:
            # Extracción de título
            title_tag = listing.find("span", class_ = "lc-title body body-2 body-regular medium")
            title = title_tag.get_text(strip=True) if title_tag else "No disponible"

            # Extracción de la url
            url_tag = listing.find("a", class_= "lc-cardCover")
            url = "https://www.fincaraiz.com.co" + url_tag['href'] if url_tag else ""

            #Extracción de descripción y dirección
            response2 = requests.get(url, headers=HEADERS)
            if response2.status_code != 200:
                raise Exception("No se pudo acceder a propiedad en FincaRaiz")
            count += 1
            if count == 50:
                time.sleep(5)
                count = 0
            soup2 = BeautifulSoup(response2.text, "html.parser")
            page2= soup2.find("div", class_ = "ant-col ant-col-24 pd-main-content")
            address_tag = page2.find("div", class_= "ant-col").get_text(strip=True).replace("Ubicación Principal", "")
            address = address_tag if address_tag else "No disponible"

            description_tag = page2.find("div", class_= "ant-typography property-description body body-regular body-1 high")
            description = description_tag.get_text(strip=True) if description_tag else "No disponible"

            search_parking= page2.find("div", class_ = "jsx-952467510 technical-sheet")
            matching = re.search(r"Parqueaderos(\d+)",search_parking.get_text(strip=True))
            parking = matching.group(1) if matching else "No disponible"

            # Extracción de precio
            price_tag = listing.find("span", class_ = "ant-typography price heading heading-3 high")
            price = price_tag.get_text(strip=True).replace("$", "").replace(".","") if price_tag else "No disponible"

            # imagen 
            img_container = listing.find("div", class_ = "card-image-gallery--cover")
            img_tag = img_container.find("img") if img_container else "No disponible"
            img = img_tag["src"] if img_tag["src"].endswith(".jpg") else ""

            # Características conjuntas
            features_tag = listing.find("span", class_ = "body body-2 body-regular medium")
            match_squaremeter = re.search(r"(\d+)\s*m²",features_tag.get_text(strip=True))
            squaremeter = match_squaremeter.group(1) if match_squaremeter else "No disponible"
            match_bedrooms = re.search(r"(\d+)\s*Habs.",features_tag.get_text(strip=True))
            bedrooms = match_bedrooms.group(1) if match_bedrooms else "No disponible"
            match_toilets = re.search(r"(\d+)\s*Baños",features_tag.get_text(strip=True))
            toilets = match_toilets.group(1) if match_toilets else "No disponible"

            # Caracteristicas de la propiedad

            property_obj = Property(
                title=title,
                address=address,
                price=price,
                squaremeter=squaremeter,
                bedrooms=bedrooms,
                toilets=toilets,
                parking=parking,
                url=url,
                img = img,
                description=description,
                source="FincaRaiz"
            )
            results.append(property_obj.to_dict())

        except Exception as e:
            print(f"Error procesando un anuncio: {e}")
            continue

    
    return results