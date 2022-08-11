import re

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_routes
from src.plotting.styling.styling import defaultStyling


def plotCostDiffElecPrice(costData: pd.DataFrame, prices: pd.DataFrame, config: dict):
    # make adjustments to data
    plotData = __adjustData(costData, prices, config)

    # produce figure
    fig = __produceFigure(plotData, config)

    # styling figure
    defaultStyling(fig)
    __styling(fig)

    return {'fig3': fig}


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, prices: pd.DataFrame, config: dict):
    comp = 'electricity'
    prices = prices.query(f"id.str.startswith('price {comp}')").filter(['id', 'val', 'val_year']).rename(columns={'id': 'component'}).reset_index(drop=True)
    prices['route'] = '1'
    prices.loc[prices.component.str.endswith(' exporter'), 'route'] = '4'
    prices['component'] = prices['component'].str.replace('price ', '').str.replace(' exporter', '')


    pNew = config['xrange'][1]
    mapping = {t: 'non-energy' for t in costData['type'] if t!='energy'}
    ret = {}
    for c in all_routes:
        costDataNew = costData.query(f"commodity=='{c}' and (route.str.endswith('_1') or route.str.endswith('_4'))")\
                              .replace({'type': mapping})

        baseRoute = re.sub(r'_\d+$', '', costDataNew.route.iloc[0])
        pricesOld = prices.copy()
        pricesOld.route = baseRoute + '_' + pricesOld.route.str[:]
        pricesNew = pd.concat([prices.query(f"route=='4'"), prices.query(f"route=='4'").assign(val=lambda r: r.val+pNew, route='1')])
        # pricesNew = prices.copy()
        # pricesNew.loc[pricesNew.route=='4', 'val'] = pricesNew.loc[pricesNew.route=='1', 'val'] - pNew
        pricesNew.route = baseRoute + '_' + pricesNew.route.str[:]

        cond = "(type=='energy' and component=='electricity')"
        costDataNewVarying = costDataNew.query(cond)\
                                        .merge(pricesOld, on=['route', 'component', 'val_year']) \
                                        .assign(val=lambda x: x.val_x / x.val_y) \
                                        .drop(columns=['val_x', 'val_y'])\
                                        .merge(pricesNew, on=['route', 'component', 'val_year']) \
                                        .assign(val=lambda x: x.val_x * x.val_y) \
                                        .drop(columns=['val_x', 'val_y'])
        costDataNewConstant = costDataNew.query('not' + cond)

        costDataNewMin = costDataNewConstant\
                           .groupby(['route', 'val_year'])\
                           .agg({'route': 'first', 'val_year': 'first', 'val': 'sum'})\
                           .reset_index(drop=True)

        costDataNewMax = pd.concat([costDataNewVarying, costDataNewConstant])\
                           .groupby(['route', 'val_year'])\
                           .agg({'route': 'first', 'val_year': 'first', 'val': 'sum'})\
                           .reset_index(drop=True)

        ret[c] = {}
        for y in costDataNewMax.val_year.unique():
            dMin = costDataNewMin.query(f"val_year=={y}")
            dMax = costDataNewMax.query(f"val_year=={y}")
            ret[c][int(y)] = [0.0, dMin.iloc[0].val-dMin.iloc[1].val, pNew, dMax.iloc[0].val-dMax.iloc[1].val]


    return ret


def __produceFigure(printData: dict, config: dict):
    # create figure
    fig = make_subplots(
        cols=len(printData),
        shared_yaxes=True,
        horizontal_spacing=0.025,
    )


    # plot lines
    hasLegend = []
    for c, item in printData.items():
        for year, data in item.items():
            x0, y0, x1, y1 = data

            fig.add_trace(
                go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode='lines',
                    name=year,
                    line=dict(color=config['line_colour'][year], width=config['global']['lw_default']),
                    showlegend=year not in hasLegend,
                    legendgroup=year,
                ),
                col=list(printData.keys()).index(c)+1,
                row=1,
            )

            if year not in hasLegend:
                hasLegend.append(year)


    # set axes labels
    fig.update_layout(
        legend_title='',
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']]),
        **{
            f"xaxis{n+1 if n else ''}": dict(title='', range=config['xrange'])
            for n in range(len(printData))
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
