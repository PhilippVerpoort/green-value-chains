import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_routes
from src.plotting.styling.styling import defaultStyling


def plotCostDiffElecPrice(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # make adjustments to data
    plotData = __adjustData(costData, costDataRef, prices, config)

    # produce figure
    fig = __produceFigure(plotData, config)

    # styling figure
    defaultStyling(fig)
    __styling(fig)

    return {'fig3': fig}


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # cost delta of scenarios 2-4 in relation to scenario 1
    cost = costData \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costDelta = cost.query(r"(not route.str.endswith('_1')) and route.str.match('.*_\d+$')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)) \
        .merge(cost.query("route.str.endswith('_1')").assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # cost delta of scenarios 2-4 in relation to scenario 1 for reference with zero elec price difference
    costRef = costDataRef \
        .groupby(['commodity', 'route', 'val_year']) \
        .agg({'commodity': 'first', 'route': 'first', 'val_year': 'first', 'val': 'sum'}) \
        .reset_index(drop=True)

    costRefDelta = costRef.query(r"(not route.str.endswith('_1')) and route.str.match('.*_\d+$')") \
        .assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)) \
        .merge(costRef.query("route.str.endswith('_1')").assign(baseRoute=lambda x: x.route.str.replace(r'_\d+$', '', regex=True)).drop(columns=['route']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # electricity price difference from prices object
    elecPriceDiff = prices \
        .query("id=='price electricity'").filter(['val_year', 'val']) \
        .merge(prices.query("id=='price electricity exporter'").filter(['val_year', 'val']), on=['val_year']) \
        .assign(priceDiff=lambda x: x.val_x - x.val_y) \
        .drop(columns=['val_x', 'val_y'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRefDelta \
        .merge(costDelta, on=['commodity', 'route', 'val_year']) \
        .merge(elecPriceDiff, on=['val_year'])

    pdMax = config['xrange'][1]
    plotData = pd.concat([
        tmp.assign(pd=pd, cd=lambda r: r.costRef + (r.cost-r.costRef)/r.priceDiff * pd)
        for pd in np.linspace(config['xrange'][0], config['xrange'][1], config['xsamples'])
    ]).drop(columns=['cost', 'costRef', 'priceDiff'])


    return plotData


def __produceFigure(plotData: dict, config: dict):
    commodities = plotData.commodity.unique().tolist()


    # create figure
    fig = make_subplots(
        cols=len(commodities),
        shared_yaxes=True,
        horizontal_spacing=0.025,
    )


    # plot lines
    hasLegend = []
    for i, commodity in enumerate(commodities):
        commData = plotData.query(f"commodity=='{commodity}'")

        for j, year in enumerate(plotData.val_year.unique()):
            yearData = commData.query(f"val_year=={year}")

            for route in plotData.route.unique():
                routeID = int(route[-1])
                thisData = yearData.query(f"route=='{route}'")

                fig.add_trace(
                    go.Scatter(
                        x=thisData.pd,
                        y=thisData.cd,
                        mode='lines',
                        name=year,
                        legendgroup=routeID,
                        legendgrouptitle=dict(text=f"<b>Case {routeID}</b>"),
                        line=dict(color=config['line_colour'][routeID], width=config['global']['lw_default'], dash='dot' if j else None),
                        showlegend=not i,
                    ),
                    col=i+1,
                    row=1,
                )

            if year not in hasLegend:
                hasLegend.append(year)


    # set axes labels
    fig.update_layout(
        legend_title='',
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        **{
            f"xaxis{i+1 if i else ''}": dict(title=f"{config['xaxislabel']}<br>{commodity}", range=config['xrange'])
            for i, commodity in enumerate(commodities)
        }
    )


    return fig


def __styling(fig: go.Figure):
    # update axis styling
    for axis in [f"{t}axis{n+1 if n else ''}" for t in ['x', 'y'] for n in range(3)]:
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
