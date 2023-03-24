from src.scaffolding.file.file_load import loadYAMLDataFile, loadCSVDataFile


# load tech data
techdata_raw = loadCSVDataFile('technologies').astype({'val': 'float32', 'period': 'int32'}, errors='ignore')


# load default options and prices
default_options = loadYAMLDataFile('options')
default_other_prices = loadCSVDataFile('other_prices').astype({'val': 'float32', 'period': 'int32'}, errors='ignore')
default_elec_prices = loadCSVDataFile('elec_prices').astype({'val': 'float32', 'period': 'int32'}, errors='ignore')


# load specifications of processes and routes
all_processes = loadCSVDataFile('processes').set_index('id').to_dict('index')
all_routes = loadYAMLDataFile('routes')
commodities = [c for c in all_routes]


# collect input data for calculations
default_input_data = {
    'other_prices': default_other_prices,
    'elec_prices': default_elec_prices,
    'options': default_options,
}
