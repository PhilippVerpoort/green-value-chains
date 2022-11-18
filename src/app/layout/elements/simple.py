from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc

from src.app.callbacks.simple_params import convertPricesDF2T
from src.load.load_default_data import default_prices, default_options


def getElementSimpleControlsCard():
    return html.Div(
        id='simple-controls-card',
        children=[
            html.Div(
                [
                    dbc.Label(
                        'Most important parameters and assumptions:',
                        html_for='simple-important-params',
                    ),
                    dash_table.DataTable(
                        id='simple-important-params',
                        columns=[
                            {'id': 'component', 'name': 'ID', 'editable': False},
                            {'id': 'location', 'name': 'Location', 'editable': False},
                            {'id': 'label', 'name': 'Parameter', 'editable': False,},
                            {'id': 'unit', 'name': 'Unit', 'editable': False,},
                            *({'id': f"val_{year}", 'name': f"Value {year}", 'type': 'numeric'} for year in default_options['times']),
                        ],
                        data=convertPricesDF2T(default_prices),
                        editable=True,
                        style_cell={'whiteSpace': 'pre-line'},
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'component'},
                                'display': 'none',
                            },
                            {
                                'if': {'column_id': 'location'},
                                'display': 'none',
                            },
                            {
                                'if': {'column_id': 'label'},
                                'width': '45%',
                            },
                            {
                                'if': {'column_id': 'unit'},
                                'width': '15%',
                            },
                            *(
                                {
                                    'if': {'column_id': f"val_{year}"},
                                    'width': f"{0.2/len(default_options['times']):.2%}%",
                                }
                                for year in default_options['times']
                            ),
                        ],
                    ),
                ],
                className='card-element',
            ),
            html.Div(
                [
                    dbc.Label(
                        'Include water electrolysis:',
                        html_for='simple-electrolysis',
                    ),
                    dcc.RadioItems(
                        id='simple-electrolysis',
                        options=[
                            dict(value=True, label='Yes'),
                            dict(value=False, label='No')
                        ],
                        value=default_options['include_electrolysis'],
                    ),
                ],
                className='card-element',
            ),
            html.Div(
                [
                    dbc.Label(
                        'Global Warming Potential (GWP) reference time scale:',
                        html_for='simple-gwp',
                    ),
                    dcc.RadioItems(
                        id='simple-gwp',
                        options=[
                            dict(value='gwp100', label='GWP100'),
                            dict(value='gwp20', label='GWP20'),
                        ],
                        value=default_options['gwp'],
                    ),
                ],
                className='card-element',
            ),
            html.Div(
                children=html.Button(id='simple-update', n_clicks=0, children='GENERATE', className='scenario-buttons'),
                className='card-element',
            ),
        ],
        className='side-card elements-card',
    )
