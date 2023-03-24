from dash import html, dash_table
import dash_bootstrap_components as dbc

from src.scaffolding.app.callbacks.update import convertPricesDF2T
from src.scaffolding.file.load_data import default_elec_prices


def getElementSimpleControlsCard():
    return html.Div(
        id='simple-controls-card',
        children=[
            html.Div(
                [
                    dbc.Label(
                        'Electricity-price cases',
                        html_for='simple-elec-prices',
                    ),
                    dash_table.DataTable(
                        id='simple-elec-prices',
                        columns=[
                            {'id': 'epdcase', 'name': 'epdcase', 'editable': False,},
                            {'id': 'epdcaseDisplay', 'name': 'Price case', 'editable': False,},
                            {'id': 'val_importer', 'name': 'RE-scarce region', 'editable': True,},
                            {'id': 'val_exporter', 'name': 'RE-rich region', 'editable': True,},
                        ],
                        data=convertPricesDF2T(default_elec_prices),
                        editable=True,
                        style_cell={'whiteSpace': 'pre-line'},
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'epdcase'},
                                'display': 'none',
                            },
                            {
                                'if': {'column_id': 'epdcaseDisplay'},
                                'width': '40%',
                            },
                            {
                                'if': {'column_id': 'val_importer'},
                                'width': '30%',
                            },
                            {
                                'if': {'column_id': 'val_exporter'},
                                'width': '30%',
                            },
                        ],
                    ),
                ],
                className='card-element',
            ),
            html.Div(
                children='Values are given in EUR/MWh. These are the electricity-price assumptions for the default '
                         'year 2040. For changing the electricity prices for the year 2030 or for changing any other '
                         'or technology assumptions, please refer to the full source code on GitHub.',
                className='card-element',
            ),
            html.Div(
                children=html.Button(id='simple-update', n_clicks=0, children='GENERATE', className='scenario-buttons'),
                className='card-element',
            ),
        ],
        className='side-card elements-card',
    )
