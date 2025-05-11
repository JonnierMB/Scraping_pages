from scrapers import scraper_site1, scraper_site2, scraper_site3

def main():

    #Scraping
    all_properties = []
    #[scraper_site1, scraper_site2, scraper_site3]
    for scraper in [scraper_site1, scraper_site2, scraper_site3]:
        try: 
            properties = scraper.scrape() 
            all_properties.extend(properties)
            print(f"✔ {scraper.__name__}: {len(properties)} propiedades extraídas.")
        except Exception as e:
            print(f"⚠ Error en {scraper.__name__}: {e}")
    
    print(f"propiedades recopiladas: {all_properties}")
    print(f"Total propiedades recopiladas: {len(all_properties)}")

if __name__ == "__main__":
    main()