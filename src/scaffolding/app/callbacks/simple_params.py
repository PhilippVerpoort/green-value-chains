import pandas as pd

from src.scaffolding.file.load_data import default_options


def convertPricesDF2T(prices: pd.DataFrame):
    prices_reformatted = prices.drop(columns=['val', 'period']).drop_duplicates(subset=['component', 'location'])

    for year in default_options['times']:
        m = prices.query(f"period=={year}").filter(['component', 'location', 'val']).rename(columns={'val': f"val_{year}"})
        prices_reformatted = prices_reformatted.merge(m, how='outer')

    return prices_reformatted.to_dict('records')


def convertPricesT2DF(prices: dict):
    prices_reformatted = pd.DataFrame.from_records(prices)

    ret = []
    for year in default_options['times']:
        ret.append(
            prices_reformatted.filter(['component', 'location', 'label', 'unit', f"val_{year}"]).rename(columns={f"val_{year}": 'val'}).assign(period=year)
        )

    return pd.concat(ret)
