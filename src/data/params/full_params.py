import numpy as np
import pandas as pd

from src.load.load_default_data import default_techdata


# Calculate parameters including uncertainty at different times, using linear interpolation if needed.
def getFullTechData(times: list):
    # convert to standard units
    techdata = __convertUnits(default_techdata)

    # aggregate data from separate
    techdata = __aggregate(techdata)

    # impute entries for missing years
    techdata = __imputeYears(techdata, times)

    return techdata


def __convertUnits(techdata: pd.DataFrame):
    return techdata


def __aggregate(techdata: pd.DataFrame):
    return techdata.drop(columns=['source', 'comment'])\
                   .groupby(['process', 'type', 'component', 'subcomponent', 'mode', 'val_year'], as_index=False, dropna=False)\
                   .agg({'unit': 'first', 'val': lambda x: sum(x)/len(x) if len(x)>0 else 0.0, 'val_uncertainty': 'first'})


def __imputeYears(techdata: pd.DataFrame, times: list):
    # before imputing check consistency of data
    # for every process and variable type there is either exactly one entry with no year or an entry for every year
    techdataGrouped = techdata.groupby(['process', 'type', 'component'])
    for key, item in techdataGrouped:
        years = techdataGrouped.get_group(key)['val_year'].unique()
        if not (
            (len(years) == 1 and all(np.isnan(years)))
         or (not any(np.isnan(years)) and all(t in years for t in times))
        ):
            raise Exception(f"Variable with conflicting or missing year entries: process_group {key[0]}, process {key[1]}, type {key[2]}, component {key[3]}")

    # create empty return list for concat
    r = []

    # create entry for every year for every line not containing year info
    paramsWOYear = techdata.query('val_year.isna()')
    for t in times:
        r.append(paramsWOYear.assign(val_year = t))

    # append data containing year info
    r.append(techdata.query('val_year.notna()'))

    return pd.concat(r)
