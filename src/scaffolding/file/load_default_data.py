from src.scaffolding.file.file_load import loadYAMLDataFile, loadCSVDataFile


# load options, assumptions, units, and technology data
default_options = loadYAMLDataFile('options')
units = loadYAMLDataFile('units')

default_techdata = loadCSVDataFile('technologies').astype({'val': 'float32', 'period': 'int32'}, errors='ignore')
default_other_prices = loadCSVDataFile('other_prices').astype({'val': 'float32', 'period': 'int32'}, errors='ignore')
default_elec_prices = loadCSVDataFile('elec_prices').astype({'val': 'float32', 'period': 'int32'}, errors='ignore')
all_processes = loadCSVDataFile('processes').set_index('id').to_dict('index')
all_routes = loadYAMLDataFile('routes')
commodities = [c for c in all_routes]
