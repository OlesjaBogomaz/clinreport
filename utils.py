import json
import pandas as pd
import socket


def load_config(config_path) -> dict:
    """Загружает настройки из json."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        config = {}  # Если файла нет, начинаем с пустого словаря
    return config


def get_ru_annotations(timeout: int = 10) -> dict | None:
    socket.setdefaulttimeout(timeout)
    url = 'https://docs.google.com/spreadsheets/d/1Zj_Gw-TolcoKljqfk4eCrQ1hyhlZDs44UOZbFTVTfes'
    ru_annotations = {
        'omim': pd.read_csv(f'{url}/export?format=csv&gid=0', index_col=0).to_dict(),
        'secondary': pd.read_csv(f'{url}/export?format=csv&gid=706494431', index_col=0).to_dict()
    }
    return ru_annotations
