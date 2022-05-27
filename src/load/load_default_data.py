import pandas as pd

from src.load.file_paths import getFilePathInput
from src.load.yaml_load import loadYamlFile


# load options, assumptions, units, and technology data
options = loadYamlFile('data/options.yml')
units = loadYamlFile('data/units.yml')

fname = getFilePathInput('./data/technology_data_v07_pcv_2022-05-20.xlsx')
default_techdata = pd.read_excel(fname, sheet_name='technology_data')
default_assumptions = pd.read_excel(fname, sheet_name='default_assumptions')

process_routes = loadYamlFile('data/process_routes.yml')
