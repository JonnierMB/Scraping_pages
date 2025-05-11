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
TYPE_PROPERTY = "casa"
# condition = ["venta", "arriendo"]
OPERATION = "venta"
# city = ["medellin", "envigado"]
CITY ="envigado"
#https://casas.trovit.com.co/index.php/cod.search_homes/{OPERATION}/what_d.{CITY}/sug.0/isUserSearch.1/order_by.relevance/property_type.{TYPE_PROPERTY}/
BASE_URL = f"https://casas.trovit.com.co/index.php/cod.search_homes/{OPERATION}/what_d.{CITY}/sug.0/isUserSearch.1/order_by.relevance/property_type.{TYPE_PROPERTY}/"

HEADERS = {
    "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape():
    print("scraping Trovit...")
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
            # Intentar encontrar y hacer clic en el botón de siguiente página
            # Esperar a que el botón de "siguiente" esté presente
            next_a = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, '//a[contains(@class, "next-button")]')))
            # Scroll al elemento y clic
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_a)
            driver.execute_script("arguments[0].click();", next_a) 

            # Esperar que cargue la siguiente página
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
    listings = soup.find_all("article", class_="snippet-listing")
    
    results = []
    count = 0
    for listing in listings:
        try:
            # Extracción de título
            titleandaddress_tag = listing.find("div", class_ = "snippet-listing-content-header-title-left")
            title_tag = titleandaddress_tag.find("span")
            title = title_tag.get_text(strip=True) if title_tag else "No disponible"

            address_tag = titleandaddress_tag.find("address")
            address = address_tag.get_text(strip=True) if address_tag else "No disponible"

            # Extracción de la url
            url_tag = listing.find("a", class_= "js-listing")
            url = url_tag['href'] if url_tag else ""
            
            #Extracción de descripción y dirección
            response2 = requests.get(url, headers=HEADERS)
            if response2.status_code != 200:
                raise Exception("No se pudo acceder a la propiedad de Trovit")
            count += 1
            if count == 50:
                time.sleep(5)
                count = 0

            soup2 = BeautifulSoup(response2.text, "html.parser")
            page2= soup2.find("div", class_ = "detail-page__main-content")
            description_tag = page2.find("div", id= "description-text")
            description = description_tag.get_text(strip=True) if description_tag else "No disponible"
            
            # Extracción de precio
            price_tag = listing.find("span", class_ = "price__actual")
            price = price_tag.get_text(strip=True).replace("$", "").replace(".","") if price_tag else "No disponible"

            # imagen 
            img_tag = listing.find("img", class_ = "swiper-lazy swiper-lazy-loaded")
            img = img_tag["src"] if img_tag else "No disponible"

            # Características conjuntas
            features_tag = listing.find("div", class_ = "snippet-listing-content-header-icons")
            features = features_tag.get_text(strip=True)
            match_squaremeter = re.search(r"(\d+)\s*m²",features)
            squaremeter = match_squaremeter.group(1) if match_squaremeter else "No disponible"
            match_bedrooms = re.search(r"(\d+)\s*habitaciones.",features)
            bedrooms = match_bedrooms.group(1) if match_bedrooms else "No disponible"
            match_inttoilet = re.search(r"(\d+)\s*,",features)
            inttoilets = match_inttoilet.group(1) + "." if match_inttoilet else ""
            match_toilets = re.search(r"(\d+)\s*baños",features)
            toilets = f"{inttoilets}{match_toilets.group(1)}"  if match_toilets else "No disponible"

            # Caracteristicas de la propiedad

            property_obj = Property(
                title=title,
                address=address,
                price=price,
                squaremeter=squaremeter,
                bedrooms=bedrooms,
                toilets=toilets,
                parking="Leer en página",
                url=url,
                img = img,
                description=description,
                source="Trovit"
            )
            results.append(property_obj.to_dict())

        except Exception as e:
            print(f"Error procesando un anuncio: {e}")
            continue

    return results