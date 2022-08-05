import re

import pandas as pd
import plotly.graph_objects as go

from src.load.load_default_data import all_routes
from src.plotting.styling.styling import defaultStyling


def plotValueCreation(costData: pd.DataFrame, config: dict):
    # make adjustments to data
    costDataNew = __adjustData(costData, config)

    # produce figure
    fig = __produceFigure(costDataNew, config)

    # styling figure
    defaultStyling(fig)
    __styling(fig)

    return {'fig2': fig}


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    showRoute = 'ELEC_H2DR_EAF_2' if 'ELEC_H2DR_EAF_2' in costData['route'].unique() else 'H2DR_EAF_2'

    years = costData['val_year'].unique()
    baseRoute = re.sub('_\\d', '', showRoute)

    costDataNew = costData.query(f"route=='{showRoute}' & val_year=={config['show_year']}").drop(columns=['component', 'route', 'val_year'])
    processes = all_routes['Steel'][baseRoute]['processes']
    processes_keys = list(processes.keys())

    mapping = {t: 'non-energy' for t in costDataNew['type'] if t!='energy'}
    costDataNew.replace({'type': mapping}, inplace=True)

    for i, p in enumerate(processes_keys[:-1]):
        upstreamCostData = costDataNew.query(f"process=='{p}'").assign(type='upstream')
        costDataNew = pd.concat([costDataNew, upstreamCostData.assign(process=processes_keys[i+1])], ignore_index=True)

    costDataNew = costDataNew.groupby(['process', 'type'])\
                             .agg({'process': 'first', 'type': 'first', 'val': 'sum'})\
                             .reset_index(drop=True)

    dummyData = pd.DataFrame.from_records([{'process': p, 'type': 'dummy', 'val': 0.0, 'val_year': y}
                                           for p in processes for y in years])

    return pd.concat([costDataNew, dummyData])


def __produceFigure(costData: pd.DataFrame, config: dict):
    # create figure
    fig = go.Figure()

    # add dummy entries such that the order is correct
    dummyData = costData.query(f"type=='dummy'")
    fig.add_trace(go.Bar(
        x=dummyData.process,
        y=dummyData.val,
        showlegend=False,
    ))

    # add traces for all cost types
    keys = config['labels'].keys()
    for stack in keys:
        plotData = costData.query(f"type=='{stack}'")

        fig.add_trace(go.Bar(
            x=plotData.process,
            y=plotData.val,
            marker_color=config['colours'][stack],
            name=config['labels'][stack],
            hovertemplate=f"<b>{config['labels'][stack]}</b><br>LCoS: %{{y}} EUR/t<extra></extra>",
        ))

    # set axes labels
    fig.update_layout(
        barmode='stack',
        xaxis=dict(title=''),
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        legend_title=''
    )

    return fig


def __styling(fig: go.Figure):
    # update axis styling
    for axis in ['xaxis', 'yaxis']:
        update = {axis: dict(
            showline=True,
            linewidth=2,
            linecolor='black',
            showgrid=False,
            zeroline=False,
            mirror=True,
            ticks='outside',
        )}
        fig.update_layout(**update)
