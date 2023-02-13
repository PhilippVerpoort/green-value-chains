import copy

from src.scaffolding.app.callbacks.simple_params import convertPricesT2DF

from src.scaffolding.file.load_default_data import default_options


def updateScenarioInput(simple_important_params: list, simple_electrolysis: bool, simple_gwp: str):
    options = copy.deepcopy(default_options)

    options['gwp'] = simple_gwp
    options['include_electrolysis'] = simple_electrolysis

    return {
        'prices': convertPricesT2DF(simple_important_params),
        'options': options,
    }
