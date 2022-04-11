from typing import Union

from src.config_load import default_assumptions as assumpts
from src.data.params.full_params import convertValue

simpleParams = ['elec_price_importer',
                'elec_price_exporter',
                'ng_price']


def getSimpleParamsTable():
    r = []

    subtypes = {
        'cost_green_elec': ['RE'],
    }

    for parName in simpleParams:
        r.append({
            'name': parName,
            'desc': assumpts[parName]['short'] if 'short' in assumpts[parName] else assumpts[parName]['desc'],
            'unit': assumpts[parName]['unit'],
            'val_2025': assumpts[parName][2025],
            'val_2050': assumpts[parName][2050],
        })

    return r


def __getParamValue(value: Union[dict, float], year: int, subtypes: list = []):
    if subtypes:
        return __getParamValue(value[subtypes[0]], year, subtypes[1:])

    if isinstance(value, dict):
        return convertValue(value[year])[0]
    else:
        return convertValue(value)[0]

