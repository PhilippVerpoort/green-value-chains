#!/usr/bin/env python
from pathlib import Path

import pandas as pd

from posted.ted.TEDataFile import TEDataFile
from posted.config.config import techs

from src.load import load_data, load_posted


DUMPDIR = Path(__file__).parent / 'dump'


# load required data and dump into Excel spreadsheet
def dump():
    # load POSTED data
    inputs = {}
    load_data(inputs)
    load_posted(inputs)

    # set file path for dumping
    DUMPDIR.mkdir(parents=True, exist_ok=True)
    file_path = Path(__file__).parent / 'dump' / 'posted.xlsx'

    # create a writer object for an Excel spreadsheet
    with pd.ExcelWriter(file_path) as writer:
        # loop over TIDs
        tids = list(dict.fromkeys([
            k
            for comm in inputs['value_chains']
            for k in reversed(inputs['value_chains'][comm]['graph'].keys())])
        )
        for tid in tids:
            tedf = TEDataFile(tid)
            tedf.load()
            df1 = tedf \
                .data \
                .drop(columns=['region']) \
                .rename(columns=lambda s: s.replace('_', ' ')) \
                .rename(columns=str.capitalize)
            df1['Type'] = df1['Type'].str.upper()
            df1.to_excel(writer, sheet_name=f"{techs[tid]['name']} (raw)")
            df2 = inputs['proc_tables'][tid].data['value']
            df2.to_excel(writer, sheet_name=f"{techs[tid]['name']} (processed)", index=(len(df2)>1))


# call dump function when running as script
if __name__ == '__main__':
    dump()
