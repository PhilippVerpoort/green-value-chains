import dash
from dash.dependencies import Input, Output, State
from flask import send_file

from src.scaffolding.app.app import dash_app
from src.scaffolding.app.callbacks.commons import subfigsDisplayed, figNames
from src.scaffolding.app.callbacks.init import figsInit
from src.scaffolding.app.callbacks.update import updateScenarioInput
from src.scaffolding.data.data import getFullData
from src.scaffolding.file.load_config import plots
from src.scaffolding.file.file_path import pathOfAssetsFile
from src.scaffolding.plotting.plot_all import plotAllFigs, getFigures


# general callback for (re-)generating plots
@dash_app.callback(
    [*(Output(subfigName, 'figure') for subfigName in subfigsDisplayed),],
    [Input('simple-update', 'n_clicks'),
     State('url', 'pathname'),
     State('plot-cfgs', 'data'),
     State('simple-elec-prices', 'data'),])
def callbackUpdate(n1, route: str, plot_cfgs: dict, simple_elec_prices: list):
    ctx = dash.callback_context

    if not ctx.triggered:
        print("Loading figures from default values")
        figsUpdated = figsInit
    else:
        btnPressed = ctx.triggered[0]['prop_id'].split('.')[0]
        if btnPressed == 'simple-update':
            # get new input and output data
            inputDataUpdated = updateScenarioInput(simple_elec_prices)
            finalData = getFullData(inputDataUpdated)

            # get list of figs required
            figsReq = [figName for plot in plots.values() for figName in plot.getFigs() if appRoute(route) in plot.getFigSpecs(figName)['display']]

            # get figures
            print(inputDataUpdated['elec_prices'])
            updatedPlots = plotAllFigs(inputDataUpdated, finalData, plot_cfgs, figs_req=figsReq, target='webapp')
            figsUpdated = getFigures(updatedPlots)
        else:
            raise Exception(f"Unknown button pressed: {btnPressed}")

    figsSorted = dict(sorted(figsUpdated.items(), key=lambda t: t[0]))

    return *figsSorted.values(),


# update figure plotting settings
@dash_app.callback(
    [Output('plot-config-modal', 'is_open'),
     Output('plot-cfgs', 'data'),
     Output('plot-config-modal-textfield', 'value'),],
    [*(Input(f'{plotName}-settings', 'n_clicks') for plotName in plots),
     Input('plot-config-modal-ok', 'n_clicks'),
     Input('plot-config-modal-cancel', 'n_clicks'),],
    [State('plot-config-modal-textfield', 'value'),
     State('plot-cfgs', 'data'),],
)
def callbackSettingsModal(*args):
    settings_modal_textfield = args[-2]
    plot_cfgs = args[-1]

    ctx = dash.callback_context
    if not ctx.triggered:
        plot_cfgs['last_btn_pressed'] = None
        return False, plot_cfgs, ''
    else:
        btnPressed = ctx.triggered[0]['prop_id'].split('.')[0]
        if btnPressed in [f"{cfgName}-settings" for cfgName in plot_cfgs]:
            fname = btnPressed.split('-')[0]
            plot_cfgs['last_btn_pressed'] = fname
            return True, plot_cfgs, plot_cfgs[fname]
        elif btnPressed == 'plot-config-modal-cancel':
            return False, plot_cfgs, ''
        elif btnPressed == 'plot-config-modal-ok':
            fname = plot_cfgs['last_btn_pressed']
            plot_cfgs[fname] = settings_modal_textfield
            return False, plot_cfgs, ''
        else:
            raise Exception('Unknown button pressed!')


# display of simple or advanced controls
@dash_app.callback(
    *(Output(f'{plotName}-settings-div', 'style') for plotName in plots),
    *(Output(f"card-{figName}", 'style') for figName in figNames),
    [Input('url', 'pathname')]
)
def callbackDisplayForRoutes(route):
    r1 = []
    r2 = []
    displayNone = {'display': 'none'}

    for plot in plots.values():
        # display plot settings button only on advanced
        r1.append({} if appRoute(route) == '/advanced' else displayNone)
        for i, figName in enumerate(plot.getFigs()):
            # display figure card only when listed in figure config
            r2.append({} if appRoute(route) in plot.getFigSpecs(figName)['display'] else displayNone)

    return r1 + r2


# serving asset files
@dash_app.server.route('/assets/<path>')
def callbackServeAssets(path):
    return send_file(pathOfAssetsFile(path), as_attachment=True)


# returning app route based on absolute route
def appRoute(route: str):
    return route
