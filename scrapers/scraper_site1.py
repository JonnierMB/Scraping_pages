#import requests
from bs4 import BeautifulSoup
from models.property_model import Property

#utilizando selenium
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

import time
import requests
STEPS = 500
DELAY = 0.5

# type_property = ["casa", "apartamento", "apartaestudio"]
TYPE_PROPERTY = "casa"
# condition = ["venta", "arriendo"]
OPERATION = "venta"
# city = ["medellin", "envigado"]
CITY ="envigado"

BASE_URL = f"https://www.metrocuadrado.com/{TYPE_PROPERTY}/{OPERATION}/{CITY}/"

HEADERS = {
    "User-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

def scrape():
    print("scraping Metrocuadrado...")
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
            time.sleep(2)  # Esperar que cargue la siguiente página

            next_btn = WebDriverWait(driver,2).until(EC.presence_of_element_located(
                (By.CLASS_NAME, 'rc-pagination-next')))
            next_class = next_btn.get_attribute("class")
            if "rc-pagination-disabled" in next_class:
                is_next_disabled = True
                break
            driver.find_element(By.CLASS_NAME, 'rc-pagination-next').click()
            
        except Exception as e:
            print(f"Se ha encontrado un error {e}")
            is_next_disabled = True  # No se encuentra el botón, fin de paginación

    driver.quit()

    if not full_html:
        raise ValueError("No se pudo obtener el HTML de la página")

    soup = BeautifulSoup(full_html, "html.parser")
    listings = soup.find_all("div", class_="property-card__content")
    
    results = []
    count = 0
    for listing in listings:
        try:
            # Extracción de título
            title_tag = listing.find("div", class_ = "property-card__detail-title")
            title = title_tag.get_text(strip=True) if title_tag else "No disponible"

            # Extracción de la url
            url_tag = listing.find("a")
            url = "https://www.metrocuadrado.com" + url_tag['href'] if url_tag else ""

            #Extracción de descripción y dirección
            response2 = requests.get(url, headers=HEADERS)
            if response2.status_code != 200:
                raise Exception("No se pudo acceder a Metrocuadrado")
            count += 1
            if count == 50:
                time.sleep(5)
                count = 0
            soup2 = BeautifulSoup(response2.text, "html.parser")
            page2= soup2.find("div", class_ = "w-full sm:max-w-[920px]") # Tarjetas de la propiedad
            address_tag = page2.find("div", class_= "w-full capitalize text-[18px] font-normal")
            address = address_tag.get_text(strip=True) if address_tag else "No disponible"
            description_tag = page2.find("div", class_= "font-normal text-[14px] leading-[24px] text-justify line-clamp-5")
            description = description_tag.get_text(strip=True) if description_tag else "No disponible"

            # Extracción de precio
            price_tag = listing.find("div", class_ = "property-card__detail-price")
            price = price_tag.get_text(strip=True).replace("$", "").replace(".","") if price_tag else "No disponible"
            
            # imagen 
            img_container = listing.find("div", class_ = "property-card__photo")
            img_tag = img_container.find("img") if img_container else "No disponible"
            img = img_tag["src"] if img_tag["src"].endswith(".jpg") else ""

            # Características conjuntas
            features_tag = listing.find("pt-main-specs", class_ = "hydrated" )
            
            squaremeter = features_tag["squaremeter"] if features_tag.has_attr("squaremeter") else "No disponible"
            bedrooms = features_tag["bedrooms"] if features_tag.has_attr("bedrooms") else "No disponible"
            toilets = features_tag["toilets"] if features_tag.has_attr("toilets") else "No disponible"
            parking = features_tag["parking"] if features_tag.has_attr("parking") else "No disponible"

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
                source="Metrocuadrado"
            )
            results.append(property_obj.to_dict())

        except Exception as e:
            print(f"Error procesando un anuncio: {e}")
            continue

    return results