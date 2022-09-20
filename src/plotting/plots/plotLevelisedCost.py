from string import ascii_lowercase

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.load.load_default_data import all_processes, all_routes


def plotLevelisedCost(costData: pd.DataFrame, costDataRec: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataAggregated, routeorder = __adjustData(costData, config) if any(fName in subfigs_needed for fName in ['fig1', 'figS1a', 'figS1b']) else (None, None)
    costDataRecAggregated, _ = __adjustData(costDataRec, config) if 'figS2' in subfigs_needed else (None, None)


    # produce fig1
    ret['fig1'] = __produceFigure(costDataAggregated, routeorder, config, is_webapp) if 'fig1' in subfigs_needed else None


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
    route_names_wiimp = {route_id: f"Case {route_id.split('_')[-1]}" for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
    route_names = {**route_names_woimp, **route_names_wiimp}

    # rename routes into something readable
    costDataNew.replace({'route': route_names}, inplace=True)

    # determine breakdown level of bars and associated hover labels
    if config['aggregate_by'] in ['none', 'subcomponent']:
        if config['aggregate_by'] == 'subcomponent':
            group_cols = ['type', 'val_year', 'commodity', 'route', 'process', 'component']
            costDataNew = costDataNew.fillna({'component': 'empty'}) \
                                     .groupby(group_cols).sum() \
                                     .sort_values('process', key=lambda col: [list(all_processes.keys()).index(p) for p in col]) \
                                     .reset_index()
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'component':
        group_cols = ['type', 'val_year', 'commodity', 'route', 'process']
        costDataNew = costDataNew.groupby(group_cols).sum() \
                                 .sort_values('process', key=lambda col: [list(all_processes.keys()).index(p) for p in col]) \
                                 .reset_index()
        costDataNew['hover_label'] = [all_processes[p]['label'] for p in costDataNew['process']]
    elif config['aggregate_by'] == 'process':
        group_cols = ['type', 'val_year', 'commodity', 'route', 'component']

        costDataNew = costDataNew.fillna({'component': 'empty'}) \
                                 .groupby(group_cols).sum() \
                                 .sort_values('component', key=lambda col: [list(config['components']).index(c) if c!='empty' else -1 for c in col]) \
                                 .reset_index()
        costDataNew['hover_label'] = [config['components'][c] if c!='empty' else None for c in costDataNew['component']]
    elif config['aggregate_by'] == 'all':
        group_cols = ['type', 'val_year', 'commodity', 'route']
        costDataNew = costDataNew.groupby(group_cols).sum().reset_index()
    else:
        raise Exception('Value of aggregate_by in the plot config is invalid.')

    return costDataNew, list(route_names.values())


def __produceFigure(costData: pd.DataFrame, routeorder: list, config: dict, commodity: str = '', is_webapp: bool = False):
    if commodity:
        costData = costData.query(f"commodity=='{commodity}'")
        subplots = [int(y) for y in sorted(costData.val_year.unique())]
    else:
        costData = costData.query(f"val_year=={config['show_year']} & route.str.startswith('Case')")
        subplots = costData.commodity.unique().tolist()+['Ethylene']


    # create figure
    fig = make_subplots(
        cols=len(subplots),
        shared_yaxes=True,
        horizontal_spacing=0.0,
    )


    # add bars for each subplot
    for i, subplot in enumerate(subplots):
        plotData = costData.query(f"val_year=={subplot}" if commodity else f"commodity=='{subplot}'")


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
            **{f"xaxis{i+1 if i else ''}": dict(title='', categoryorder='array', categoryarray=[r for r in routeorder if r in plotData.route.unique()])},
        )


        # add cost differences from Base Case
        if not commodity and not is_webapp:
            correction = 10.0
            xshift = 2.5

            baseCost = plotData.query("route.str.endswith(' 1')").val.sum()
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
                    ay=baseCost+correction,
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
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']['commodity' if commodity else 'overview']]),
        legend_title='',
    )


    # set legend position
    fig.update_layout(
        legend=dict(
            yanchor='top',
            y=1.0,
            xanchor='right',
            x=1.0,
        ),
    )


    return fig
