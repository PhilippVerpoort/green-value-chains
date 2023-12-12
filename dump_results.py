#!/usr/bin/env python
from pathlib import Path

import pandas as pd

from posted.ted.TEDataFile import TEDataFile
from posted.calc_routines.LCOX import LCOX
from posted.config.config import techs

from src.load import load_data, load_posted, load_other
from src.plots.LevelisedPlot import LevelisedPlot
from src.proc import process_inputs


# load required data and dump into Excel spreadsheet
def export():
    # load inputs and outputs
    inputs = {}
    outputs = {}
    load_data(inputs)
    load_posted(inputs)
    load_other(inputs)
    process_inputs(inputs, outputs)

    # create a writer object for an Excel spreadsheet
    with pd.ExcelWriter(Path(__file__).parent / 'dump' / 'results.xlsx') as writer:
        # loop over commodities
        commodities = list(inputs['value_chains'].keys())
        for c, comm in enumerate(commodities):
            # produce LCOX DataTable by assuming final elec prices and applying calc routine
            lcox = outputs['tables'][comm] \
                .assume(outputs['cases'][comm]) \
                .calc(LCOX)

            # extract dataframe from LCOX DataTable and convert to plottable format
            commData = lcox.data['LCOX'] \
                .pint.dequantify().droplevel('unit', axis=1) \
                .stack(['process', 'type']).to_frame('value') \
                .reset_index() \
                .query(f"epdcase=='medium'") \
                .drop(columns=['epdcase', 'impcase'])

            # set index
            commData = commData.set_index(['impsubcase', 'type', 'process']).unstack('type').sort_index()

            # dump to spreadsheet
            commData.to_excel(writer, sheet_name=comm, index=True)


# call export function when running as script
if __name__ == '__main__':
    export()
