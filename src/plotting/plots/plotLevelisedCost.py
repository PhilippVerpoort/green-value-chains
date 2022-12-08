from string import ascii_lowercase

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_processes, all_routes
from src.plotting.helperFuncs import groupbySumval


def plotLevelisedCost(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataAggregated, routeorder = __adjustData(costData, config) if any(fName in subfigs_needed for fName in ['fig3', 'figS1a', 'figS1b', 'figS1c', 'figS2']) else (None, None)
    costDataRecAggregated, _ = __adjustData(costDataRec, config) if 'figS2' in subfigs_needed else (None, None)


    # produce fig1
    ret['fig3'] = __produceFigure(costDataAggregated, routeorder, config, show_costdiff=not is_webapp) if 'fig3' in subfigs_needed else None


    # produce figS1
    for k, commodity in enumerate(list(all_routes.keys())):
        subfigName = f"figS1{ascii_lowercase[k]}"
        ret[subfigName] = __produceFigure(costDataAggregated, routeorder, config, commodity=commodity) if subfigName in subfigs_needed else None


    # produce figS2
    ret['figS2'] = __produceFigure(costDataRecAggregated, routeorder, config) if 'figS2' in subfigs_needed else None


    return ret


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    showRoutes = costData['route'].unique()
    showYears = costData['val_year'].unique()

    # remove upstream cost entries
    costDataNew = costData.copy().query(f"type!='upstream'")

    # rename iron feedstock entries
    costDataNew.loc[(costDataNew['type'] == 'feedstock') & costDataNew['component'].isin(['ore', 'scrap']), 'type'] = 'iron'

    # define route names and ordering
    route_names_woimp = {route_id: route_vals['name'] for route_details in all_routes.values() for route_id, route_vals in sorted(route_details.items()) if route_id in costDataNew['route'].unique()}
    route_names_wiimp = {route_id: route_id.split('--')[-1] for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
    route_names = {**route_names_woimp, **route_names_wiimp}

    # rename routes into something readable
    costDataNew.replace({'route': route_names}, inplace=True)

    # determine breakdown level of bars and associated hover labels
    if config['aggregate_by'] == 'none':
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'subcomponent':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route', 'process', 'component'], keep=['case'])
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'component':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route', 'process'], keep=['case'])
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
    elif config['aggregate_by'] == 'process':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route', 'component'], keep=['case'])
        costDataNew['hover_label'] = [config['components'][c] if c!='empty' else None for c in costDataNew['component']]
    elif config['aggregate_by'] == 'all':
        costDataNew = groupbySumval(costDataNew.fillna({'component': 'empty'}),
                                    ['type', 'val_year', 'commodity', 'route'], keep=['case'])
        costDataNew['hover_label'] = [config['types'][t]['label'] for t in costDataNew['type']]
    else:
        raise Exception('Value of aggregate_by in the plot config is invalid.')

    # sort by commodities
    commodityOrder = costData.commodity.unique().tolist()
    costDataNew.sort_values(by='commodity', key=lambda row: [commodityOrder.index(c) for c in row], inplace=True)

    return costDataNew, list(route_names.values())


def __produceFigure(costData: pd.DataFrame, routeorder: list, config: dict, commodity: str = '', show_costdiff: bool = False):
    if commodity:
        costData = costData.query(f"commodity=='{commodity}'")
        subplots = [int(y) for y in sorted(costData.val_year.unique())]
    else:
        costData = costData.query(f"val_year=={config['show_year']} & route.str.contains('Case')")
        subplots = costData.commodity.unique().tolist()


    # create figure
    fig = make_subplots(
        cols=len(subplots),
        horizontal_spacing=0.05,
    )


    # add bars for each subplot
    for i, subplot in enumerate(subplots):
        # select data for each subplot
        plotData = costData.query(f"val_year=={subplot}" if commodity else f"commodity=='{subplot}'")


        # determine ymax
        if config['ymaxcalc']:
            ymax = 1.1 * plotData.query("route=='Base Case'").val.sum()
        else:
            ymax = config['ymax'][commodity] if commodity else config['ymax'][subplot]


        # add traces for all cost types
        for type, display in config['types'].items():
            thisData = plotData.query(f"type=='{type}'")
            hoverLabel = 'hover_label' in thisData.columns and any(thisData.hover_label.unique())

            fig.add_trace(
                go.Bar(
                    x=thisData.route,
                    y=thisData.val,
                    marker_color=display['colour'],
                    name=display['label'],
                    customdata=thisData.hover_label if hoverLabel else None,
                    showlegend=not i,
                    hovertemplate=f"<b>{display['label']}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>Cost: %{{y}} EUR/t<extra></extra>",
                ),
                row=1,
                col=i+1,
            )


        # add annotations
        fig.add_annotation(
            text=f"<b>{subplot}</b>",
            x=0.0,
            xref='x domain',
            xanchor='left',
            y=1.0,
            yref='y domain',
            yanchor='top',
            showarrow=False,
            bordercolor='black',
            borderwidth=2,
            borderpad=3,
            bgcolor='white',
            row=1,
            col=i+1,
        )


        # update layout of subplot
        fig.update_layout(
            **{
                f"xaxis{i+1 if i else ''}": dict(title='', categoryorder='array', categoryarray=[r for r in routeorder if r in plotData.route.unique()]),
                f"yaxis{i+1 if i else ''}": dict(title='', range=[0.0, ymax]),
            },
        )


        # add cost differences from Base Case
        if show_costdiff:
            correction = 0.018
            xshift = 2.5

            baseCost = plotData.query("route=='Base Case'").val.sum()
            fig.add_hline(
                baseCost,
                line_color='black',
                line_width=config['global']['lw_thin'],
                row=1,
                col=i+1,
            )

            for j, route in enumerate(sorted(plotData.route.unique().tolist())[1:]):
                thisCost = plotData.query(f"route=='{route}'").val.sum()

                fig.add_annotation(
                    x=j+1,
                    y=thisCost,
                    yref=f"y{i+1 if i else ''}",
                    ax=j+1,
                    ay=baseCost+correction*ymax,
                    ayref=f"y{i+1 if i else ''}",
                    arrowcolor='black',
                    arrowwidth=config['global']['lw_thin'],
                    arrowhead=2,
                    row=1,
                    col=i+1,
                )

                fig.add_annotation(
                    text=f"{baseCost-thisCost: .2f}<br>({(baseCost-thisCost)/baseCost*100:.2f}%)",
                    align='left',
                    showarrow=False,
                    x=j+1,
                    xanchor='left',
                    xshift=xshift,
                    y=thisCost+(baseCost-thisCost)/2,
                    yref=f"y{i+1 if i else ''}",
                    yanchor='middle',
                    row=1,
                    col=i+1,
                )


    # update layout of all plots
    fig.update_layout(
        barmode='stack',
        yaxis_title=config['yaxislabel'],
        legend_title='',
    )


    return fig
