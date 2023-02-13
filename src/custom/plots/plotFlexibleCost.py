import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.scaffolding.plotting.helperFuncs import groupbySumval


def plotFlexibleCost(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict,
                          subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    pd_samples, ocf_samples, plotData = __adjustData(costData, costDataRef, prices, config) if subfigs_needed else None


    # produce figure
    ret['figS2'] = __produceFigure(pd_samples, ocf_samples, plotData, config) if 'figS2' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, costDataRef: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # cost delta of Cases 1-3 in relation to Base Case
    cost = groupbySumval(costData.query("type!='capital'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

    costDelta = cost.query("case=='Case 3'") \
        .merge(cost.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
        .assign(cost=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # cost delta of Cases 1-3 in relation to Base Case for reference with zero elec price difference
    costRef = groupbySumval(costDataRef.query("type!='capital'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case'])

    costRefDelta = costRef.query("case=='Case 3'") \
        .merge(costRef.query("case=='Base Case'").drop(columns=['route', 'case']), on=['commodity', 'baseRoute', 'period']) \
        .assign(costRef=lambda x: x.val_y - x.val_x) \
        .drop(columns=['val_x', 'val_y', 'baseRoute'])


    # capital cost data
    costCap = groupbySumval(costData.query("type=='capital' & case=='Case 3'"), ['commodity', 'route', 'period'], keep=['baseRoute', 'case']) \
        .rename(columns={'val': 'costCap'})


    # electricity price difference from prices object
    elecPriceDiff = prices \
        .query("component=='electricity' and location=='importer'").filter(['period', 'val']) \
        .merge(prices.query("component=='electricity' and location=='exporter'").filter(['period', 'val']), on=['period']) \
        .assign(priceDiff=lambda x: x.val_x - x.val_y) \
        .drop(columns=['val_x', 'val_y'])


    # linear interpolation of cost difference as a function of elec price
    tmp = costRefDelta \
        .merge(costDelta, on=['commodity', 'route', 'case', 'period']) \
        .merge(costCap, on=['commodity', 'route', 'case', 'period']) \
        .merge(elecPriceDiff, on=['period'])

    pd_samples = np.linspace(config['xrange'][0], config['xrange'][1], config['samples'])
    ocf_samples = np.linspace(config['yrange'][0], config['yrange'][1], config['samples'])
    pd, ocf = np.meshgrid(pd_samples, ocf_samples)

    plotData = {c: 0.0 for c in costData.commodity.unique().tolist()}
    for index, r in tmp.iterrows():
        if r.period != config['showYear']: continue
        plotData[r.commodity] = r.costCap * (100.0/ocf - 1.0) + r.costRef + (r.cost - r.costRef) / r.priceDiff * pd


    return pd_samples, ocf_samples, plotData


def __produceFigure(pd_samples: np.ndarray, ocf_samples: np.ndarray, plotData: dict, config: dict):
    # create figure
    fig = make_subplots(
        cols=len(plotData),
        shared_yaxes=True,
        horizontal_spacing=0.025,
    )


    # plot heatmaps and contours
    for i, commodity in enumerate(plotData):
        tickvals = [100 * i for i in range(6)]
        ticktext = [str(v) for v in tickvals]

        fig.add_trace(
            go.Heatmap(
                x=pd_samples,
                y=ocf_samples,
                z=plotData[commodity],
                zsmooth='best',
                zmin=config['zrange'][0],
                zmax=config['zrange'][1],
                colorscale=[
                    [0.0, config['zcolours'][0]],
                    [1.0, config['zcolours'][1]],
                ],
                colorbar=dict(
                    x=1.02,
                    y=0.5,
                    len=1.0,
                    title='Cost difference (EUR/t)',
                    titleside='right',
                    tickvals=tickvals,
                    ticktext=ticktext,
                ),
                showscale=True,
                hoverinfo='skip',
            ),
            col=i+1,
            row=1,
        )

        fig.add_trace(
            go.Contour(
                x=pd_samples,
                y=ocf_samples,
                z=plotData[commodity],
                contours_coloring='lines',
                colorscale=[
                    [0.0, '#000000'],
                    [1.0, '#000000'],
                ],
                line_width=config['global']['lw_thin'],
                contours=dict(
                    showlabels=True,
                    start=config['zrange'][0],
                    end=config['zrange'][1],
                    size=config['zdelta'],
                ),
                showscale=False,
                hoverinfo='skip',
            ),
            col=i+1,
            row=1,
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


    # set axes labels
    fig.update_layout(
        legend_title='',
        yaxis=dict(title=config['yaxislabel'], range=config['yrange']),
        **{
            f"xaxis{i+1 if i else ''}": dict(range=config['xrange'])
            for i, commodity in enumerate(plotData)
        },
        xaxis2_title=config['xaxislabel'],
    )


    return fig
