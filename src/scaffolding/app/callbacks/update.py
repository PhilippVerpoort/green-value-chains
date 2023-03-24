import pandas as pd

from src.scaffolding.file.load_data import default_input_data, default_elec_prices


# define year and epdcases to show in table
showYear = 2040
showCases = ['weak', 'medium', 'strong']

locations = ('importer', 'exporter')


# update callback function
def updateScenarioInput(simple_elec_prices: list):
    inputDataUpdated = default_input_data.copy()

    inputDataUpdated['elec_prices'] = convertPricesT2DF(simple_elec_prices, default_elec_prices)


    return inputDataUpdated


# convert prices from dataframe to table
def convertPricesDF2T(prices: pd.DataFrame):
    tmp = prices \
        .query(f"period=={showYear} & epdcase in {showCases}") \
        .filter(['epdcase', 'location', 'val']) \

    ret = pd.merge(
        *(tmp.query(f"location=='{l}'").drop(columns=['location']) for l in locations),
        on='epdcase',
        suffixes=(f"_{l}" for l in locations),
    )

    # set display column
    ret = ret.assign(epdcaseDisplay = lambda row: row['epdcase'].str.capitalize() + ' pull')

    return ret.to_dict('records')


# convert prices from table back to dataframe
def convertPricesT2DF(prices: list, default_elec_prices: pd.DataFrame):
    updatedElecPrices = default_elec_prices.copy()

    for row in prices:
        for l in locations:
            loc = (updatedElecPrices['epdcase'] == row['epdcase']) & \
                  (updatedElecPrices['period'] == showYear) & \
                  (updatedElecPrices['location'] == l)
            updatedElecPrices.loc[loc, 'val'] = float(row[f"val_{l}"])

    print(updatedElecPrices)

    return updatedElecPrices
