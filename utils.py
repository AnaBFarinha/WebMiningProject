import requests
import polars as pl
import re
import json
import os
import time
from urllib.parse import quote

###########################################################################

# Steam Games

###########################################################################

def get_steam_gamesIDs():
    url = f"http://api.steampowered.com/ISteamApps/GetAppList/v2/"
    response = requests.get(url)
    data = response.json()
    return data['applist']['apps']  # This is a list of dictionaries with 'appid' and 'name'

def clean_app_list(games_list):
    # List of keywords to exclude
    excluded = ['test', 'client', 'server', 'soundtrack', 'demo']
    
    # RegEx pattern for checking European characters
    european_chars_pattern = re.compile(r'^[a-zA-Z0-9 \-\'!@#$%^&*()_+={}[\]|\\:;"<>,.?/~`€£±§]+$')
    
    # Filter the list by removing dictionaries whose 'name' is empty,
    # contains 'test', 'client', 'server', 'soundtrack', or non-European characters.
    filtered_games = [
        app for app in games_list 
        if app['name'] and all(exclude not in app['name'].lower() for exclude in excluded)
        and european_chars_pattern.match(app['name'])
    ]
    return filtered_games

def find_apps_by_term(apps, term):
    # Check if the term is contained in the 'name' of each dictionary. Ignore case sensitivity.
    matching_apps = [app for app in apps if term.lower() in app['name'].lower()]
    return matching_apps

def find_game_name(games, appid):
    for game in games:
        if game['appid'] == appid:
            return game['name']
    return "Spiel mit dieser AppID nicht gefunden."

def save_progress(game_list, games_details, filename='data\\game_progress.json'):
    """Saves the current processing state including unprocessed games and details of processed games."""
    data_to_save = {
        'remaining_games': game_list,
        'processed_details': games_details
    }
    with open(filename, 'w') as f:
        json.dump(data_to_save, f)

def load_progress(filename='data\\game_progress.json'):
    """Loads the saved processing state if it exists, including both unprocessed and processed games."""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return None


def get_nested(dictionary, keys, default=None):
    """Safely retrieves a nested value from a dictionary given a list of keys."""
    for key in keys:
        dictionary = dictionary.get(key) if dictionary is not None else None
        if dictionary is None:
            return default
    return dictionary


def format_game_data(game_info, game_name, app_id):
    """Formats and extracts the necessary fields from the game info data, including the appid, using safe dictionary access for top-level data and handling nested data where applicable."""
    data = game_info.get('data', {})
    return {
        "name": game_name,
        "appid": app_id,
        "required_age": data.get("required_age", 0),
        "is_free": data.get("is_free", False),
        "detailed_description": data.get("detailed_description", ""),
        "supported_languages": [lang.split('<')[0] for lang in data.get("supported_languages", "").split(',')],
        "developers": data.get("developers", []),
        "publishers": data.get("publishers", []),
        "price": 0 if data.get("is_free", False) else get_nested(data, ["price_overview", "final"], 0) / 100,
        "platforms": [key for key, value in data.get("platforms", {}).items() if value],
        "metacritic_score": get_nested(data, ["metacritic", "score"], None),
        "categories": [category["description"] for category in data.get("categories", [])],
        "genres": [genre["description"] for genre in data.get("genres", [])],
        "release_date": get_nested(data, ["release_date", "date"], ""),
        "content_descriptors": data.get("content_descriptors", {}).get("notes", ""),
        "usk_rating": get_nested(data, ["ratings", "usk", "rating"], None),
        "number_of_reviews": get_nested(data, ["recommendations", "total"], 0)  # Use get_nested to safely access nested data
    }

def fetch_recommendations(game_list):
    """Fetches information for each game in the list and updates the game dictionaries with the data."""
    base_url = "https://store.steampowered.com/api/appdetails"
    games_details = []  # List to store all processed games details
    processed_count = 0

    while game_list:  # Process until the list is empty
        game = game_list.pop(0)  # Remove and return the first game from the list
        app_id = game['appid']
        
        # Construct the URL for the API request
        params = {'appids': app_id}

        # Make the API request
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses
            data = response.json()
            game_info = data[str(app_id)]
            game_name = data.get('name')
            if game_info['success']:
                games_details.append(format_game_data(game_info, game_name, app_id))
                processed_count += 1

                if processed_count % 10 == 0:
                    print(f"Processed {processed_count} games so far.")

        except requests.RequestException as e:
            print(f"Failed to fetch data for {game_name}: {str(e)}")
            exit()

        # Save progress periodically to avoid data loss
        if processed_count % 10 == 0:
            save_progress(game_list, games_details)
            time.sleep(10)

    # Save final progress
    save_progress(game_list, games_details)


###########################################################################

# Steam Reviews

###########################################################################

def get_steam_reviews(app_id, cursor='*'):
    url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&filter=recent&language=english&cursor={cursor}&num_per_page=100"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['success'] == 1:
            return data
        else:
            print(f"Failed to get valid reviews for app ID {app_id}.")
            print(data)
            return data
    else:
        print(f"Failed to get reviews for app ID {app_id}. Status code: {response.status_code}")
        return None

def fetch_all_reviews(app_id):
    cursor = '*'
    all_reviews = []
    
    while True:
        data = get_steam_reviews(app_id, cursor)
        if data is None or data['query_summary']['num_reviews'] == 0:
            break
        
        # Collect reviews
        reviews = data['reviews']
        all_reviews.extend(reviews)
        
        # Update cursor
        cursor = quote(data['cursor'])
    
    # Create a DataFrame from reviews
    reviews_df = pl.DataFrame(all_reviews)
    num_entries = len(reviews_df)

    # Specify the directory and file name for the parquet file
    directory = "data\\parquets"
    file_name = f"{app_id}_reviews_{num_entries}.parquet"
    file_path = os.path.join(directory, file_name)
    
    # Save to parquet
    reviews_df.write_parquet(file_path)

    return num_entries