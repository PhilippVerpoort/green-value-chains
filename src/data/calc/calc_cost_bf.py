import pandas as pd


def calcCostComponentsBF(ref_data: dict, years: list):
    records = [
        {'type': 'direct', 'unit': 'EUR/t', 'case': 'BF', 'val': ref_data['bf_cost']},
        {'type': 'carbon', 'unit': 'tCO2eq/t', 'case': 'BF', 'val': ref_data['bf_ghgi']},
    ]
    refDataBF = pd.DataFrame.from_records([{**record, 'year': year} for record in records for year in years])

    return refDataBF
