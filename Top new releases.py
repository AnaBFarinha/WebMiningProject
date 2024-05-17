from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

def scrape_steam_top_new_releases():
    # Initialize the Chrome WebDriver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

    # URL of the Steam Top New Releases page
    url = 'https://store.steampowered.com/charts/topnewreleases/top_january_2024'

    # Open the URL in the browser
    driver.get(url)
    
    # Wait until the page is initially loaded
    time.sleep(3)
    
    # Scroll to the end of the page to load all contents
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for new data to load
        time.sleep(0.5)
        
        # Calculate new scroll height and compare it with the last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    
    # Extract the links of the games
    game_elements = driver.find_elements(By.CSS_SELECTOR, 'a.tab_item')
    
    # Collect data about each game
    games_data = []
    for element in game_elements:
        href = element.get_attribute('href')
        title = element.find_element(By.CSS_SELECTOR, '.tab_item_name').text
        release_date = element.find_element(By.CSS_SELECTOR, '.release_date').text
        price = element.find_element(By.CSS_SELECTOR, '.discount_final_price').text if element.find_elements(By.CSS_SELECTOR, '.discount_final_price') else "Free"
        
        game_data = {
            "href": href,
            "title": title,
            "release_date": release_date,
            "price": price
        }
        games_data.append(game_data)
    
    # Close the browser
    driver.quit()
    
    # Return the collected data
    return games_data

# Execute the function and print the results
top_new_releases = scrape_steam_top_new_releases()
print(top_new_releases)

# Define the function to save the data to a JSON file
def save_top_new_releases_to_json(games_data):
    # Define the file path
    file_path = 'data/SteamTopNewReleasesJanuary2024.json'
    
    # Save the data to a JSON file
    with open(file_path, 'w') as file:
        json.dump(games_data, file, indent=4)
    
    # Return the path to the JSON file
    return file_path

# Execute the function and return the file path
file_path = save_top_new_releases_to_json(top_new_releases)
print(file_path)


import json

# Define the file path
file_path = 'data/SteamTopNewReleasesJanuary2024.json'

# Open and read the JSON file
with open(file_path, 'r') as file:
    data = json.load(file)

# Print the contents of the JSON file
print(json.dumps(data, indent=4))