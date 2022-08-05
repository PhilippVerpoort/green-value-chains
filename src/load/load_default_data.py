import pandas as pd

from src.load.file_paths import getFilePathInput
from src.load.yaml_load import loadYamlFile


# load options, assumptions, units, and technology data
default_options = loadYamlFile('data/options.yml')
units = loadYamlFile('data/units.yml')

default_techdata = pd.read_csv(getFilePathInput('./data/technologies.csv')).astype({'val': 'float32', 'val_year': 'int32'}, errors='ignore')
default_prices = pd.read_csv(getFilePathInput('./data/prices.csv')).astype({'val': 'float32', 'val_year': 'int32'}, errors='ignore')
all_processes = pd.read_csv(getFilePathInput('./data/processes.csv')).set_index('id').to_dict('index')
all_routes = loadYamlFile('data/routes.yml')
