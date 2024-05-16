import json

def save_data_to_json(data, file_path):
    with open(file_path, 'w') as file:
        json.dump(data, file)
    return file_path