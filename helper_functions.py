import json
import os
import re
import polars as pl
import glob
from collections import defaultdict
import subprocess
import sys
import requests
from zipfile import ZipFile
from io import BytesIO
from sklearn.model_selection import train_test_split
import functools


def save_data_to_json(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file)
    return file_path


@functools.lru_cache(maxsize=None)
def load_json(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return pl.DataFrame(data)


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


@functools.lru_cache(maxsize=None)
def load_parquets(parquet_dir, selection_file=None):
    """
    Load all .parquet files from the specified directory, optionally filtering by a selection list.

    Args:
        parquet_dir (str): The directory containing the .parquet files.
        selection_file (str, optional): Path to a file containing selected app IDs. Defaults to None.

    Returns:
        polars.DataFrame: Concatenated DataFrame of all loaded parquet files.
    """
    # Load selection list if provided
    selection_list = None
    if selection_file:
        with open(selection_file, "r") as file:
            selection_list = set(line.strip() for line in file)

    # Load all .parquet files, optionally filtering by selection list
    dfs = []
    for file_path in glob.glob(os.path.join(parquet_dir, "*.parquet")):
        appid = os.path.basename(file_path).split("_")[0]
        if selection_list is None or appid in selection_list:
            try:
                df = pl.read_parquet(file_path)
                df = df.with_columns([pl.lit(appid).cast(pl.Utf8).alias("appid")])
                dfs.append(df)
            except Exception as e:
                print(f"Failed to load {file_path}: {e}")

    if not dfs:
        raise ValueError("No dataframes were loaded successfully.")

    # Unify columns across all dataframes
    unified_dfs = unify_columns(dfs)

    # Concatenate dataframes
    concatenated_df = pl.concat(unified_dfs)

    return concatenated_df


def unify_columns(dfs):
    all_columns = set()
    column_types = {}

    # Gather all column names and their data types
    for df in dfs:
        for col in df.columns:
            if col not in column_types:
                column_types[col] = df[col].dtype
            all_columns.add(col)

    unified_dfs = []
    for df in dfs:
        for col in all_columns:
            if col not in df.columns:
                # Add the missing column with the appropriate data type
                if column_types[col] == pl.Utf8:
                    df = df.with_columns([pl.lit(None).cast(pl.Utf8).alias(col)])
                elif column_types[col] == pl.Int64:
                    df = df.with_columns([pl.lit(None).cast(pl.Int64).alias(col)])
                elif column_types[col] == pl.Float64:
                    df = df.with_columns([pl.lit(None).cast(pl.Float64).alias(col)])
                elif column_types[col] == pl.Boolean:
                    df = df.with_columns([pl.lit(None).cast(pl.Boolean).alias(col)])
                else:
                    df = df.with_columns([pl.lit(None).alias(col)])
            else:
                # Ensure the existing column has the correct data type
                df = df.with_columns([df[col].cast(column_types[col]).alias(col)])
        unified_dfs.append(
            df.select(sorted(all_columns))
        )  # sort to maintain column order

    return unified_dfs


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


def save_appids_to_txt(appids, output_path, limit=100):
    """
    Save a list of appids to a text file.

    Args:
    appids (list): List of appids to save.
    output_path (str): Path to the output text file. Default is 'high_review_appids.txt'.
    limit (int): The maximum number of appids to save. Default is 100.
    """
    with open(
        output_path, "w"
    ) as file:  # 'w' mode ensures a new file is created or an existing file is overwritten
        for appid in appids[:limit]:
            file.write(f"{appid}\n")


def download_and_extract_zip_from_gdrive(gdrive_url, extract_to):
    # Function to clear the target directory
    def clear_parquet_files(directory):
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if file_path.endswith(".parquet"):
                os.remove(file_path)

    # Extract the file ID from the Google Drive URL
    def get_gdrive_file_id(url):
        if "id=" in url:
            return url.split("id=")[1]
        elif "drive.google.com/file/d/" in url:
            return url.split("/d/")[1].split("/")[0]
        else:
            raise ValueError("Invalid Google Drive URL")

    # Create the direct download URL
    file_id = get_gdrive_file_id(gdrive_url)
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    # Clear the target directory
    # clear_parquet_files(extract_to)

    # Download the .zip file
    response = requests.get(download_url)
    if response.status_code != 200:
        raise Exception(f"Failed to download file: Status code {response.status_code}")

    # Extract the .zip file
    with ZipFile(BytesIO(response.content)) as zip_ref:
        zip_ref.extractall(extract_to)

    print(f"Extracted files to {extract_to}")


def load_data(reviews_dir, game_details_path, selection_file):
    reviews = load_parquets(reviews_dir, selection_file)

    # Check if 'appid' column exists in reviews
    if "appid" not in reviews.columns:
        raise ValueError("The 'appid' column is not found in the reviews dataframe.")

    game_details = load_json(game_details_path)

    # Check if 'appid' column exists in game details
    if "appid" not in game_details.columns:
        raise ValueError(
            "The 'appid' column is not found in the game details dataframe."
        )

    # Integrate game details with reviews
    game_details = game_details.with_columns([pl.col("appid").cast(pl.Utf8)])
    reviews = reviews.join(game_details, on="appid", how="inner")

    # Split the data into train and test sets
    train_data, test_data = train_test_split(
        reviews.to_pandas(), test_size=0.2, random_state=42
    )

    # Prepare the data for models
    train_data = train_data.rename(
        columns={"user_steamid": "user_id", "appid": "game_id", "votes_up": "rating"}
    )

    test_data = test_data.rename(
        columns={"user_steamid": "user_id", "appid": "game_id", "votes_up": "rating"}
    )

    return train_data, test_data


# Load config
def load_config():
    with open("config.json", "r") as file:
        return json.load(file)


def format_timedelta(td):
    """Format timedelta to display hours, minutes, and seconds."""
    total_seconds = int(td.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"
