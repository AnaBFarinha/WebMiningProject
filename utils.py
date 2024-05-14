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
    return data['applist']['app']  # This is a list of dictionaries with 'appid' and 'name'

def clean_games_list(games_list):
    # List of keywords to exclude
    excluded = ['test', 'client', 'server', 'soundtrack', 'demo']
    
    # RegEx pattern for checking European characters
    european_chars_pattern = re.compile(r'^[a-zA-Z0-9 \-\'!@#$%^&*()_+={}[\]|\\:;"<>,.?/~`€£±§]+$')
    
    # Filter the list by removing dictionaries whose 'name' is empty,
    # contains 'test', 'client', 'server', 'soundtrack', or non-European characters.
    filtered_games = [
        game for game in games_list 
        if game['name'] and all(exclude not in game['name'].lower() for exclude in excluded)
        and european_chars_pattern.match(game['name'])
    ]
    return filtered_games

def find_games_by_term(games, term):
    # Check if the term is contained in the 'name' of each dictionary. Ignore case sensitivity.
    matching_games = [game for game in games if term.lower() in game['name'].lower()]
    return matching_games

def find_game_name(games, appid):
    for game in games:
        if game['appid'] == appid:
            return game['name']
    return "Spiel mit dieser AppID nicht gefunden."

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

###########################################################################

# SteamTopseller

###########################################################################

def save_data_to_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file)
    return file_path