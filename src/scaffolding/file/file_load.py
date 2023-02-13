import pandas as pd
import yaml

from src.scaffolding.file.file_path import pathOfDataFile
from src.scaffolding.file.file_path import pathOfConfigFile


def loadCSVDataFile(fname: str):
    path = pathOfDataFile(f"{fname}.csv")
    return pd.read_csv(path)


def loadYAMLDataFile(fname: str):
    path = pathOfDataFile(f"{fname}.yml")
    return yaml.load(open(path, 'r').read(), Loader=yaml.FullLoader)


def loadYAMLConfigFile(fname: str):
    path = pathOfConfigFile(f"{fname}.yml")
    return yaml.load(open(path, 'r').read(), Loader=yaml.FullLoader)
