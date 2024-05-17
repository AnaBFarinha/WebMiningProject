import json
import os
import re
import polars as pl
import glob
from collections import defaultdict
import subprocess
import sys


def save_data_to_json(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file)
    return file_path


def clean_parquet_files(directory):
    """
    Clean up .parquet files in the specified directory.

    - Deletes .parquet files with count ≤ 250.
    - Ensures only one file with the highest count for each appid is retained.

    Args:
        directory (str): The path to the directory containing the .parquet files.
    """
    # Regular expression to extract appid and count from filenames
    pattern = re.compile(r"(\d+)_reviews_(\d+)\.parquet")

    # Dictionary to store the highest count for each appid
    file_dict = defaultdict(lambda: (0, ""))

    # Step 1: Check all .parquet files and store the file with the highest count for each appid
    for filename in os.listdir(directory):
        if filename.endswith(".parquet"):
            match = pattern.match(filename)
            if match:
                appid, count = match.groups()
                count = int(count)
                if count > 250 and count > file_dict[appid][0]:
                    file_dict[appid] = (count, filename)

    # Step 2: Delete all .parquet files that do not have the highest count or count ≤ 250
    for filename in os.listdir(directory):
        if filename.endswith(".parquet"):
            match = pattern.match(filename)
            if match:
                appid, count = match.groups()
                count = int(count)
                # Delete file if it does not have the highest count or if count ≤ 250
                if filename != file_dict[appid][1]:
                    os.remove(os.path.join(directory, filename))
                    print(f"Deleted: {filename}")

    # Output the files that were kept
    print("Files kept:")
    for appid, (count, filename) in file_dict.items():
        print(f"Kept: {filename} with count: {count}")


# Example usage
directory = "data/parquets"
clean_parquet_files(directory)


# Function to load and concatenate selected parquet files
def load_parquets(parquet_dir, selection_file=None):
    if selection_file:
        with open(selection_file, "r") as f:
            selected_appids = set(line.strip() for line in f.readlines())
        parquet_files = []
        for appid in selected_appids:
            parquet_files.extend(glob.glob(f"{parquet_dir}/{appid}_reviews_*.parquet"))
    else:
        parquet_files = glob.glob(f"{parquet_dir}/*.parquet")

    dfs = [pl.read_parquet(file) for file in parquet_files]
    return pl.concat(dfs)


def load_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return pl.DataFrame(data)


def get_parquets_data_info(parquet_folder_path):
    """
    Process all .parquet files in the specified folder, extracting information from the filenames
    and creating a Polars DataFrame with file name, appid, name, and review count.

    Args:
    parquet_folder_path (str): Path to the folder containing .parquet files.

    Returns:
    polars.DataFrame: A DataFrame containing the file name, appid, name, and review count.
    """

    # Path to the SteamGames.json file
    steam_games_path = "data/jsons/SteamGames.json"

    # Function to extract information from the filename
    def extract_info_from_filename(filename):
        match = re.match(r"(\d+)_reviews_(\d+)", filename)
        if match:
            appid = match.group(1)  # Keep appid as a string
            review_count = int(match.group(2))
            return appid, review_count
        return None, None

    # Search for all .parquet files in the folder
    parquet_files = [
        f for f in os.listdir(parquet_folder_path) if f.endswith(".parquet")
    ]

    # List to store the extracted information
    data = []

    # Extract information from the filenames and store it
    for file in parquet_files:
        file_name = file.split(".")[0]  # Remove the file extension
        appid, review_count = extract_info_from_filename(file_name)
        if appid is not None and review_count is not None:
            data.append(
                {"file_name": file, "appid": appid, "review_count": review_count}
            )

    # Load the SteamGames.json file
    with open(steam_games_path, "r") as file:
        steam_games = json.load(file)

    # Convert the list of dictionaries to a Polars DataFrame
    steam_games_df = pl.DataFrame(steam_games)

    # Convert the DataFrame to a dictionary for fast lookups
    appid_to_name = steam_games_df.select(["appid", "name"]).to_dict(as_series=False)

    # Create a lookup dictionary
    lookup = dict(zip(appid_to_name["appid"], appid_to_name["name"]))

    # Add the name to the collected data
    for item in data:
        item["name"] = lookup.get(item["appid"], "Unknown")

    # Create a Polars DataFrame
    parquets_df = pl.DataFrame(data)

    return parquets_df


def install_requirements(requirements_file="requirements.txt"):
    """
    Install the packages listed in the requirements.txt file using pip.

    Args:
        requirements_file (str): Path to the requirements.txt file. Default is 'requirements.txt'.
    """
    try:
        # Execute the pip command to install the requirements
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", requirements_file]
        )
        print(f"Successfully installed packages from {requirements_file}")
    except subprocess.CalledProcessError:
        print(f"Failed to install packages from {requirements_file}")
