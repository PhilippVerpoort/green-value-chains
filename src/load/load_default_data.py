import pandas as pd

from src.load.file_paths import getFilePathInput
from src.load.yaml_load import loadYamlFile


# load options, assumptions, units, and technology data
default_options = loadYamlFile('data/options.yml')
units = loadYamlFile('data/units.yml')

fname = getFilePathInput('./data/data.xlsx')
default_techdata = pd.read_excel(fname, sheet_name='technology_data')
default_prices = pd.read_excel(fname, sheet_name='price_assumptions')
process_data = pd.read_excel(fname, sheet_name='processes').set_index('id').to_dict('index')

process_routes_load = pd.read_excel(fname, sheet_name='routes').set_index(['process_group', 'id']).to_dict('index')

for route in process_routes_load.values():
    tmp = {}
    for p in route['processes'].split(','):
        words = p.strip().split('-')
        if len(words) == 1:
            tmp[p] = {}
        elif len(words) == 2:
            tmp[words[0]] = {'mode': words[1]}
        else:
            raise Exception('Formatting error of processes in route.')
    route['processes'] = tmp

    if route['import_cases'] and isinstance(route['import_cases'], str):
        tmp = {}
        for c in route['import_cases'].split(','):
            words = c.strip().split(':')
            tmp[words[0].strip()] = words[1].strip().split('+')
        route['import_cases'] = tmp
    else:
        route['import_cases'] = False

process_routes = {}
for process_group, route_id in process_routes_load:
    value = process_routes_load[(process_group, route_id)]
    if process_group not in process_routes:
        process_routes[process_group] = {route_id: value}
    else:
        process_routes[process_group][route_id] = value