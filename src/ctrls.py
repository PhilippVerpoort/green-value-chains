from dash import html, dash_table
import dash_bootstrap_components as dbc

from posted.config.config import flowTypes


# create main control card
def main_ctrl(default_inputs: dict):
    table_data_elec_price = default_inputs['epdcases'] \
        .pint.dequantify() \
        .droplevel(level='unit', axis=1) \
        .assign(epdcaseDisplay=lambda df: df['epdcase'].str.capitalize()) \
        .assign(processDisplay=lambda df: df['process'].map({'ELH2': 'Electrolysis', 'OTHER': 'Other'})) \
        .to_dict('records')

    table_data_transp_cost = default_inputs['transp_cost'] \
        .assign(tradedDisplay=lambda df: df['traded'].map({
            flowid: flowSpecs['name']
            for flowid, flowSpecs in flowTypes.items()
        })) \
        .to_dict('records')

    return [html.Div(
        id='simple-controls-card',
        children=[
            html.Div(
                children='Please enter your own assumptions in the table below and press the GENERATE button to update '
                         'the results. Electricity prices are assumed in EUR/MWh. For changing other assumptions, '
                         'please refer to the full source code on GitHub.',
                className='card-element',
            ),
            dbc.Label(
                'Electricity-price cases',
                html_for='simple-elec-prices',
            ),
            html.Div(
                [
                    dash_table.DataTable(
                        id='simple-elec-prices',
                        columns=[
                            {'id': 'epdcase', 'name': 'epdcase', 'editable': False, },
                            {'id': 'epdcaseDisplay', 'name': 'Price case', 'editable': False, },
                            {'id': 'process', 'name': 'Process', 'editable': False, },
                            {'id': 'processDisplay', 'name': 'Process type', 'editable': False, },
                            {'id': 'RE-rich', 'name': 'RE-rich region', 'editable': True, },
                            {'id': 'RE-scarce', 'name': 'RE-scarce region', 'editable': True, },
                        ],
                        data=table_data_elec_price,
                        editable=True,
                        style_cell={'whiteSpace': 'pre-line'},
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'process'},
                                'display': 'none',
                            },
                            {
                                'if': {'column_id': 'processDisplay'},
                                'width': '30%',
                            },
                            {
                                'if': {'column_id': 'epdcase'},
                                'display': 'none',
                            },
                            {
                                'if': {'column_id': 'epdcaseDisplay'},
                                'width': '30%',
                            },
                            {
                                'if': {'column_id': 'val_importer'},
                                'width': '20%',
                            },
                            {
                                'if': {'column_id': 'val_exporter'},
                                'width': '20%',
                            },
                        ],
                    ),
                ],
                className='card-element',
            ),
            dbc.Label(
                'Spec. transport cost',
                html_for='simple-transp-cost',
            ),
            html.Div(
                [
                    dash_table.DataTable(
                        id='simple-transp-cost',
                        columns=[
                            {'id': 'traded', 'name': 'traded', 'editable': False, },
                            {'id': 'tradedDisplay', 'name': 'Commodity', 'editable': False, },
                            {'id': 'impsubcase', 'name': 'Subcase', 'editable': False, },
                            {'id': 'assump', 'name': 'Assumption', 'editable': True, },
                            {'id': 'unit', 'name': 'Value', 'editable': False, },
                        ],
                        data=table_data_transp_cost,
                        editable=True,
                        style_cell={'whiteSpace': 'pre-line'},
                        style_cell_conditional=[
                            {
                                'if': {'column_id': 'traded'},
                                'display': 'none',
                            },
                            {
                                'if': {'column_id': 'tradedDisplay'},
                                'width': '25%',
                            },
                            {
                                'if': {'column_id': 'impsubcase'},
                                'width': '15%',
                            },
                            {
                                'if': {'column_id': 'assump'},
                                'width': '30%',
                            },
                            {
                                'if': {'column_id': 'unit'},
                                'width': '30%',
                            },
                        ],
                    ),
                ],
                className='card-element',
            ),
            html.Div(
                children=html.Button(id='simple-update', n_clicks=0, children='GENERATE', className='btn btn-primary'),
                className='card-element',
            ),
        ],
        className='side-card elements-card',
    )]
