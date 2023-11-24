import pathlib

import pandas as pd
import yaml


BASE_PATH = pathlib.Path(__file__).parent.parent.resolve()

def loadCSVDataFile(fname: str):
    path = BASE_PATH / 'data' / f"{fname}.csv"
    return pd.read_csv(path)

def loadYAMLDataFile(fname: str):
    path = BASE_PATH / 'data' / f"{fname}.yml"
    with open(path, 'r') as f:
        ret = yaml.load(f.read(), Loader=yaml.FullLoader)
    return ret

def load_yaml_config_file(fname: str):
    path = BASE_PATH / 'config' / f"{fname}.yml"
    with open(path, 'r') as f:
        ret = yaml.load(f.read(), Loader=yaml.FullLoader)
    return ret
