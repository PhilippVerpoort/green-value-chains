import numpy as np
import pandas as pd

from src.load.load_default_data import default_techdata


# Calculate parameters including uncertainty at different times, using linear interpolation if needed.
def getFullTechData(times: list, process_group: str):
    # filter for params relevant for application
    techdata = default_techdata.query(f"process_group=='{process_group}'")

    # convert to standard units
    techdata = __convertUnits(techdata)

    # impute entries for missing years
    techdata = __imputeYears(techdata, times)

    return techdata


def __convertUnits(techdata: pd.DataFrame):
    return techdata


def __imputeYears(techdata: pd.DataFrame, times: list):
    # before imputing check consistency of data
    # for every process and variable type there is either exactly one entry with no year or an entry for every year
    techdataGrouped = techdata.groupby(['process_group', 'process', 'type', 'component'])
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
