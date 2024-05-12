import requests
import pandas as pd

def fetch_game_details(app_ids):
    games_details = []
    
    for app_id in app_ids:
        url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            game_info = data[str(app_id)]
            if game_info['success']:
                details = game_info['data']
                games_details.append({
                    'App ID': app_id,
                    'Name': details.get('name', 'N/A'),
                    'Type': details.get('type', 'N/A'),
                    'Is Free': details.get('is_free', 'N/A'),
                    'Required Age': details.get('required_age', 'N/A'),
                    'Detailed Description': details.get('detailed_description', 'N/A'),
                    'About The Game': details.get('about_the_game', 'N/A'),
                    'Short Description': details.get('short_description', 'N/A'),
                    'Supported Languages': details.get('supported_languages', 'N/A'),
                    'Header Image': details.get('header_image', 'N/A'),
                    'Website': details.get('website', 'N/A'),
                    'Developers': ', '.join(details.get('developers', [])),
                    'Publishers': ', '.join(details.get('publishers', [])),
                    'Price': details.get('price_overview', {}).get('final_formatted', 'N/A') if 'price_overview' in details else 'N/A',
                    'Platforms': ', '.join([platform for platform, available in details.get('platforms', {}).items() if available]),
                    'Categories': ', '.join([category['description'] for category in details.get('categories', [])]),
                    'Genres': ', '.join([genre['description'] for genre in details.get('genres', [])]),
                    'Release Date': details.get('release_date', {}).get('date', 'N/A'),
                    'Background Image': details.get('background', 'N/A')
                })
            else:
                print(f"Failed to fetch details for App ID {app_id}: API returned success=False.")
        else:
            print(f"Failed to fetch details for App ID {app_id}: Status code {response.status_code}.")
    
    return pd.DataFrame(games_details)

# This list of game ids is just for testing the code
app_ids = [2728090, 2171530, 2169845, 2169844] 

# Fetching game details
game_details_df_games = fetch_game_details(app_ids)
#uncomment this line to use the list extracted from the other code
#game_details_df_games = fetch_game_details(games_list)

# Displaying the DataFrame
print(game_details_df_games)

# Optionally save to CSV
game_details_df_games.to_csv('steam_game_details.csv', index=False)