import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
import time
import re
import requests
from bs4 import BeautifulSoup

# Automatically install and configure the Chrome WebDriver
chromedriver_autoinstaller.install()
options = Options()
options.add_argument('--blink-settings=imagesEnabled=false')  # Disable images to speed up scraping
options.headless = False  # Set to True if you want to run in headless mode
driver = webdriver.Chrome(options=options)

# List of property URLs to scrape
urls = [
    "https://www.airbnb.co.uk/rooms/33571268",
    "https://www.airbnb.co.uk/rooms/20669368",
    "https://www.airbnb.co.uk/rooms/50633275"
]

def format_amenity_text(text):
    """
    Formats the text by introducing a hyphen for extra details and improving readability.
    
    Args:
        text (str): The raw text to format.
    
    Returns:
        str: The formatted text.
    """
    # Add a hyphen between numbers and text
    formatted_text = re.sub(r'(\d+)\s*([A-Za-z])', r'\1 - \2', text)
    # Add a space before capitalized words (if needed)
    formatted_text = re.sub(r'(?<=\w)([A-Z][a-z])', r' \1', formatted_text)
    return formatted_text.strip()

def scrape_property_details(url):
    """
    Scrapes details from an Airbnb property page including name, type, bedrooms, bathrooms, and amenities.
    
    Args:
        url (str): The URL of the Airbnb property page.
    
    Returns:
        dict: A dictionary containing property details.
    """
    # Fetch the page content with requests for initial checks
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return {"error": f"Page not accessible or property does not exist for {url}."}
    
    # Use Selenium to load the page and interact with dynamic content
    try:
        driver.get(url)
        page_detailed = driver.page_source
    except Exception as e:
        return {"error": f"Failed to load page in Selenium: {e}"}
    
    detail_soup = BeautifulSoup(page_detailed, 'lxml')
    
    # Handle the cookie consent pop-up if present
    try:
        WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.XPATH, "//button[contains(text(), 'Accept')]"))
        )
        cookies_element = driver.find_element(By.XPATH, "//button[contains(text(), 'Accept')]")
        cookies_element.click()
    except Exception as e:
        print(f"Cookie consent button not found or already handled.\n{'='*40}\n")
    
    # Wait until the amenities block is clickable and interactable
    try:
        parent_class = 'b9672i7'
        button_class = 'l1ovpqvx'
        selector = f"div.{parent_class} button.{button_class}"
        amenities_element = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
    except Exception as e:
        return {"error": f"Failed to locate amenities element: {e}"}
    
    # Extract property details
    property_name, property_type, bedrooms, bathrooms = None, None, None, None
    try:
        title_element = driver.find_element(By.CSS_SELECTOR, 'h1.hpipapi')
        property_name = title_element.text.strip()
    except Exception as e:
        print(f"Warning: Failed to extract property name: {e}")

    try:
        type_element = driver.find_element(By.CSS_SELECTOR, 'div.parent_class,h2.hpipapi')
        property_type = type_element.text.strip()
    except Exception as e:
        print(f"Warning: Failed to extract property type: {e}")

    try:
        bedroom_element = driver.find_element(By.CSS_SELECTOR, 'ol > li.l7n4lsf:nth-of-type(2)')
        bedrooms = re.search(r'\d+', bedroom_element.text.strip()).group()
    except (AttributeError, IndexError, Exception) as e:
        print(f"Warning: Failed to extract number of bedrooms: {e}")

    try:
        bathroom_element = driver.find_element(By.CSS_SELECTOR, 'ol > li.l7n4lsf:nth-of-type(4)')
        bathrooms = re.search(r'\d+', bathroom_element.text.strip()).group()
    except (AttributeError, IndexError, Exception) as e:
        print(f"Warning: Failed to extract number of bathrooms: {e}")
    
    time.sleep(5)
    
    # Click on the amenities element to load full details
    try:
        amenities_element.click()
    except Exception as e:
        print(f"Warning: Failed to click on the amenities element: {e}")

    time.sleep(4)
    
    # Extract and categorize amenities
    categorized_amenities = {}
    try:
        soup = BeautifulSoup(driver.page_source, 'lxml')
        # Find category headers
        category_headers = soup.find_all('div', class_='_14li9j3g')
        
        for header in category_headers:
            category_name = header.find('h2').text.strip()
            amenities_list = header.find_next_sibling('ul', class_='_2f5j8p')
            if amenities_list:
                amenities = []
                for li in amenities_list.find_all('li'):
                    del_tag = li.find('del')
                    if del_tag:
                        amenity = del_tag.text.strip()
                    else:
                        amenity = li.text.strip()
                    
                    # Clean and format text
                    amenity = amenity.replace("Unavailable:", "").strip()
                    formatted_amenity = format_amenity_text(amenity)
                    amenities.append(formatted_amenity)
                categorized_amenities[category_name] = amenities
    except Exception as e:
        print(f"Warning: Failed to extract amenities: {e}")
        categorized_amenities = None
    
    return {
        "Property Name": property_name,
        "Property Type": property_type,
        "Bedrooms": bedrooms,
        "Bathrooms": bathrooms,
        "Amenities": categorized_amenities if categorized_amenities else None
    }

if __name__ == "__main__":
    for url in urls:
        result = scrape_property_details(url)
        if "error" in result:
            print(result["error"])
        else:
            print(f"Property Name: {result['Property Name']}")
            print(f"Property Type: {result['Property Type']}")
            print(f"Bedrooms: {result['Bedrooms']}")
            print(f"Bathrooms: {result['Bathrooms']}")
            print("Amenities:")
            if result['Amenities']:
                for category, amenities in result['Amenities'].items():
                    print(f"  {category}:")
                    for amenity in amenities:
                        print(f"    - {amenity}")
            else:
                print("  No amenities available.")
        print("\n" + "="*40 + "\n")  # Separator between properties
