import requests
import pandas as pd


api_key = "D6D1CE08CB30226CDC"

def get_steam_gamesIDs():
    url = f"http://api.steampowered.com/ISteamApps/GetAppList/v2/"
    response = requests.get(url)
    data = response.json()
    return data['applist']['apps']  # This is a list of dictionaries with 'appid' and 'name'

def get_steam_reviews(app_id):
    url = f"https://store.steampowered.com/appreviews/{app_id}?json=1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data['success'] == 1:
            return data
        else:
            print(f"Failed to get valid reviews for app ID {app_id}.")
            return None
    else:
        print(f"Failed to get reviews for app ID {app_id}. Status code: {response.status_code}")
        return None

def process_reviews_and_summary(data, app_id, game_name):
    summary_data = data.get('query_summary', [])
    reviews_data = data.get('reviews', [])
    

    # Normalize reviews data
    reviews_df = pd.json_normalize(reviews_data, sep='_')
    reviews_df['game_id'] = app_id
    reviews_df['game_name'] = game_name
    
    # Add summary data to each row
    for key, value in summary_data.items():
        reviews_df[key] = value

    return reviews_df


games_list = get_steam_gamesIDs()
#games_list = games_list[:20]
reviews_dfs = []

for game in games_list:
    app_id = game['appid']
    game_name = game['name']
    reviews_data = get_steam_reviews(app_id)
    if reviews_data:
        reviews_df = process_reviews_and_summary(reviews_data, app_id, game_name)
        reviews_dfs.append(reviews_df)

# Concatenate all the DataFrames into a single DataFrame
complete_reviews = pd.concat(reviews_dfs, ignore_index=True)

# Display the concatenated DataFrame
print(complete_reviews.head())

# Save to Excel
complete_reviews.to_excel('steam_reviews.xlsx', index=False)
