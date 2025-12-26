import json
import os

CONFIG_FILE = 'config.json'

def save_setting(key, value):
    """Saves a setting to the config.json file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {}
    
    config[key] = value
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_setting(key):
    """Loads a setting from the config.json file."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get(key)
    except (FileNotFoundError, json.JSONDecodeError):
        return None