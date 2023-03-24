import numpy as np
import pandas as pd

from src.scaffolding.file.load_data import techdata_raw


# calculate parameters including uncertainty at different times, using linear interpolation if needed.
def getFullTechData(times: list):
    # aggregate data from separate
    techdata = __aggregate(techdata_raw)

    # impute entries for missing years
    techdata = __imputeYears(techdata, times)

    return techdata



def __aggregate(techdata: pd.DataFrame):
    return techdata.groupby(['process', 'type', 'component', 'subcomponent', 'mode', 'period'], as_index=False, dropna=False)\
                   .agg({'unit': 'first', 'val': lambda x: sum(x)/len(x) if len(x)>0 else 0.0})


def __imputeYears(techdata: pd.DataFrame, times: list):
    # before imputing check consistency of data
    # for every process and variable type there is either exactly one entry with no year or an entry for every year
    techdataGrouped = techdata.groupby(['process', 'type', 'component'])
    for key, item in techdataGrouped:
        years = techdataGrouped.get_group(key)['period'].unique()
        if not (
            (len(years) == 1 and all(np.isnan(years)))
         or (not any(np.isnan(years)) and all(t in years for t in times))
        ):
            raise Exception(f"Variable with conflicting or missing year entries: {key}")

    # create empty return list for concat
    r = []

    # create entry for every year for every line not containing year info
    paramsWOYear = techdata.query('period.isna()')
    for t in times:
        r.append(paramsWOYear.assign(period = t))

    # append data containing year info
    r.append(techdata.query('period.notna()'))

    return pd.concat(r)
