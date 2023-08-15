from pathlib import Path

import pint
from posted.units.units import ureg
from piw import Webapp
from dash.dependencies import Input, State

from src.ctrls import mainCtrl
from src.plots.LevelisedPlot import LevelisedPlot
from src.plots.ScenarioPlot import ScenarioPlot
from src.plots.SensitivityPlot import SensitivityPlot
from src.plots.TotalCostPlot import TotalCostPlot
from src.update import updateScenarioInput
from src.utils import loadYAMLConfigFile
from src.load import loadData, loadPOSTED, loadOther
from src.proc import processInputs


# make sure to always use correct units registry
pint.set_application_registry(ureg)


webapp = Webapp(
    piwID='green-value-chains',
    title='Estimating the renewables pull in future global green value chains',
    pages={
        '': 'Simple',
        'advanced': 'Advanced',
    },
    desc='This webapp reproduces results presented in an accompanying manuscript on estimations of the renewables pull '
         'in future global green value chains. It determines energy-cost savings and other relocation penalties for '
         'different import scenarios for the green value chains of steel, urea, and ethylene.',
    authors=['Philipp C. Verpoort', 'Lukas Gast', 'Anke Hofmann', 'Falko Ueckerdt'],
    date='25/03/2023',
    load=[loadData, loadPOSTED, loadOther],
    ctrls=[mainCtrl],
    generate_args=[
        Input('simple-update', 'n_clicks'),
        State('simple-elec-prices', 'data'),
        State('simple-transp-cost', 'data'),
    ],
    update=[updateScenarioInput],
    proc=[processInputs],
    plots=[TotalCostPlot, LevelisedPlot, ScenarioPlot, SensitivityPlot],
    glob_cfg={f: loadYAMLConfigFile(f) for f in ('globPlot', 'globStyle')},
    output=Path(__file__).parent / 'output',
    debug=False,
    input_caching=True,
)


# this will allow running the app locally
if __name__ == '__main__':
    webapp.start()
    webapp.run()
