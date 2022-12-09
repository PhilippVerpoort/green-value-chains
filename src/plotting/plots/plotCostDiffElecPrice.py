import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.plotting.helperFuncs import groupbySumval


def plotCostDiffElecPrice(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict,
                          subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    plotData, elecPriceDiff, benchmarkCost = __adjustData(costData, costDataRef, prices, config) if subfigs_needed else None


    # produce figure
    ret['fig5'] = __produceFigure(plotData, elecPriceDiff, benchmarkCost, config) if 'fig5' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # cost delta of Cases 1-3 in relation to Base Case
    cost = groupbySumval(costData, ['commodity', 'route', 'val_year'], keep=['baseRoute', 'case'])

    costDelta = cost.query("case.notnull() & case!='Base Case'") \
        .merge(cost.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # cost delta of Cases 1-3 in relation to Base Case for reference with zero elec price difference
    costRef = groupbySumval(costDataRef, ['commodity', 'route', 'val_year'], keep=['baseRoute', 'case'])

    costRefDelta = costRef.query("case.notnull() & case!='Base Case'") \
        .merge(costRef.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'val_year']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # electricity price difference from prices object
    elecPriceDiff = prices \
        .query("component=='electricity' and location=='importer'").filter(['val_year', 'val']) \
        .merge(prices.query("component=='electricity' and location=='exporter'").filter(['val_year', 'val']), on=['val_year']) \
        .assign(priceDiff=lambda x: x.val_x - x.val_y) \
        .drop(columns=['val_x', 'val_y'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRefDelta \
        .merge(costDelta, on=['commodity', 'route', 'case', 'val_year']) \
        .merge(elecPriceDiff, on=['val_year'])

    plotData = pd.concat([
        tmp.assign(pd=pd, cd=lambda r: r.costRef + (r.cost-r.costRef)/r.priceDiff * pd)
        for pd in np.linspace(config['xrange'][0], config['xrange'][1], config['xsamples'])
    ]).drop(columns=['cost', 'costRef', 'priceDiff'])


    # sort by commodities
    commodityOrder = costData.commodity.unique().tolist()
    plotData.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)


    # benchmark cost
    benchmarkCost = cost.query("case=='Base Case'")


    return plotData, elecPriceDiff, benchmarkCost


def __produceFigure(plotData: pd.DataFrame, elecPriceDiff: pd.DataFrame, benchmarkCost: pd.DataFrame, config: dict):
    commodities = plotData.commodity.unique().tolist()


    # create figure
    fig = make_subplots(
        cols=len(commodities),
        shared_yaxes=True,
        horizontal_spacing=0.03,
        specs=[len(commodities) * [{"secondary_y": True}]],
    )


    # plot lines
    for i, commodity in enumerate(commodities):
        commData = plotData.query(f"commodity=='{commodity}' and val_year=={config['showYear']}")
        defaultPriceDiff = elecPriceDiff.query(f"val_year=={config['showYear']}").iloc[0].priceDiff
        baseCaseCost = benchmarkCost.query(f"commodity=='{commodity}' and val_year=={config['showYear']}").iloc[0].val

        for case in plotData.case.unique():
            thisData = commData.query(f"case=='{case}'")

            if case == 'Case 1a':
                continue

            fig.add_trace(
                go.Scatter(
                    x=thisData.pd,
                    y=thisData.cd,
                    mode='lines',
                    name=case,
                    line=dict(color=config['line_colour'][case], width=config['global']['lw_default']),
                    showlegend=not i,
                    hovertemplate=f"<b>{case}</b><br>{config['xlabelshort']}: %{{x:.2f}}<br>{config['ylabelshort']}: %{{y:.2f}}<extra></extra>",
                ),
                col=i+1,
                row=1,
            )


        # add vertical line indicating default price assumption
        fig.add_vline(
            defaultPriceDiff,
            col=i+1,
            row=1,
            line_dash='dash',
        )


        # add text annotations explaining figure content
        fig.add_annotation(
            x=0.0,
            xref='x domain',
            xanchor='left',
            y=1.0,
            yref='y domain',
            yanchor='top',
            text=f"<b>{commodity}</b>",
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=3,
            bgcolor='white',
            col=i+1,
            row=1,
        )


        # add second yaxis
        fig.add_trace(
            go.Scatter(x=config["xrange"], y=[-10, -10], showlegend=False),
            secondary_y=True,
            col=i+1,
            row=1,
        )

        fig.update_layout(
            **{f"yaxis{2*i+2}": dict(
                range=[0.0, config['ymax']/baseCaseCost*100],
            )}
        )


    # set axes labels
    fig.update_layout(
        legend_title='',
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        **{
            f"xaxis{i+1 if i else ''}": dict(range=config['xrange'])
            for i, commodity in enumerate(commodities)
        },
        xaxis2_title=f"{config['xaxislabel']}",
        yaxis6_title=config['yaxis2label'],
    )


    return fig
