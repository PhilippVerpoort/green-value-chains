import copy

from src.app.callbacks.simple_params import convertPricesT2DF

from src.load.load_default_data import default_options


def updateScenarioInputSimple(simple_important_params: list, simple_electrolysis: bool, simple_gwp: str):
    options = copy.deepcopy(default_options)

    options['gwp'] = simple_gwp
    options['include_electrolysis'] = simple_electrolysis

    return convertPricesT2DF(simple_important_params), options
