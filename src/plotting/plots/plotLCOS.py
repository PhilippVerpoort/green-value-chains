from string import ascii_lowercase

import pandas as pd
import plotly.graph_objects as go

from src.load.load_default_data import process_data, process_routes
from src.plotting.styling.styling import defaultStyling


def plotLCOS(costData: pd.DataFrame, config: dict):
    # make adjustments to data
    costDataAggregated = __adjustData(costData, config)

    # produce fig1
    fig1 = __produceFigure(costDataAggregated, config)

    # produce SI figs
    process_groups = ['Steel', 'Fertiliser']
    subfigs = []
    for process_group in process_groups:
        subfigs.append(__produceFigure(costDataAggregated, config, process_group=process_group))

    # styling figure
    for f in [fig1, *subfigs]:
        defaultStyling(f)
        __styling(f)

    return {
        'fig1': fig1,
        **{f"figS1{ascii_lowercase[k]}": fig for k, fig in enumerate(subfigs)},
    }


# make adjustments to data (route names, component labels)
def __adjustData(costData: pd.DataFrame, config: dict):
    routes = costData['route'].unique()
    years = costData['val_year'].unique()

    # remove upstream cost entries
    costDataNew = costData.copy().query(f"type!='upstream'")

    # rename iron feedstock entries
    costDataNew.loc[(costDataNew['type'] == 'feedstock') & costDataNew['component'].isin(['ore', 'scrap']), 'type'] = 'iron'

    # define route names and ordering
    route_names_woimp = {route_id: route_vals['name'] for routes in process_routes.values() for route_id, route_vals in sorted(routes.items()) if route_id in costDataNew['route'].unique()}
    route_names_wiimp = {route_id: f"Case {route_id.split('_')[-1]}" for route_id in costDataNew['route'].unique() if route_id not in route_names_woimp}
    route_names = {**route_names_woimp, **route_names_wiimp}

    # replace route names and add dummy data to force correct ordering
    costDataNew.replace({'route': route_names}, inplace=True)
    dummyData = pd.DataFrame.from_records([{'process_group': pg, 'route': route_names[r], 'type': 'dummy', 'val': 0.0, 'val_year': y}
                                           for r in route_names for y in years for pg in costData['process_group'].unique() if r in process_routes[pg]])

    # determine breakdown level of bars and associated hover labels
    if config['aggregate_by'] in ['none', 'subcomponent']:
        if config['aggregate_by'] == 'subcomponent':
            group_cols = ['type', 'val_year', 'process_group', 'route', 'process', 'component']
            costDataNew = costDataNew.fillna({'component': 'empty'}) \
                                     .groupby(group_cols).sum() \
                                     .sort_values('process', key=lambda col: [list(process_data.keys()).index(p) for p in col]) \
                                     .reset_index()
        costDataNew['hover_label'] = [process_data[p]['label'] for p in costDataNew['process']]
        costDataNew.loc[costDataNew['component']!='empty', 'hover_label'] = [f"{row['component'].capitalize()} ({row['hover_label']})" for index, row in costDataNew.loc[costDataNew['component']!='empty',:].iterrows()]
    elif config['aggregate_by'] == 'component':
        group_cols = ['type', 'val_year', 'process_group', 'route', 'process']
        costDataNew = costDataNew.groupby(group_cols).sum() \
                                 .sort_values('process', key=lambda col: [list(process_data.keys()).index(p) for p in col]) \
                                 .reset_index()
        costDataNew['hover_label'] = [process_data[p]['label'] for p in costDataNew['process']]
    elif config['aggregate_by'] == 'process':
        group_cols = ['type', 'val_year', 'process_group', 'route', 'component']

        costDataNew = costDataNew.fillna({'component': 'empty'}) \
                                 .groupby(group_cols).sum() \
                                 .sort_values('component', key=lambda col: [list(config['component_labels']).index(c) if c!='empty' else -1 for c in col]) \
                                 .reset_index()
        costDataNew['hover_label'] = [config['component_labels'][c] if c!='empty' else None for c in costDataNew['component']]
    elif config['aggregate_by'] == 'all':
        group_cols = ['type', 'val_year', 'process_group', 'route']
        costDataNew = costDataNew.groupby(group_cols).sum().reset_index()
    else:
        raise Exception('Value of aggregate_by in the plot config is invalid.')

    return pd.concat([costDataNew, dummyData])


def __produceFigure(costData: pd.DataFrame, config: dict, process_group: str = ''):
    if process_group:
        costData = costData.query(f"process_group=='{process_group}'")
    else:
        costData = costData.query(f"val_year=={config['show_year']} & route.str.startswith('Case')")

    # create figure
    fig = go.Figure()

    # add dummy entries such that the order is correct
    dummyData = costData.query(f"type=='dummy'")
    fig.add_trace(go.Bar(
        x=[dummyData.val_year, dummyData.route] if process_group else [dummyData.process_group, dummyData.route],
        y=dummyData.val,
        showlegend=False,
    ))

    # add traces for all cost types
    keys = config['labels'].keys()
    for stack in keys:
        plotData = costData.query(f"type=='{stack}'")
        hoverLabel = 'hover_label' in plotData.columns and any(plotData.hover_label.unique())

        fig.add_trace(go.Bar(
            x=[plotData.val_year, plotData.route] if process_group else [plotData.process_group, plotData.route],
            y=plotData.val,
            marker_color=config['colours'][stack],
            name=config['labels'][stack],
            customdata=plotData.hover_label if hoverLabel else None,
            hovertemplate=f"<b>{config['labels'][stack]}</b>{'<br>%{customdata}' if hoverLabel else ''}<br>LCoS: %{{y}} EUR/t<extra></extra>",
        ))

    # add vertical line
    nGroups = costData['process_group'].nunique() if process_group else costData['val_year'].nunique()
    nRoutes = costData['route'].nunique()
    for i in range(nGroups-1):
        fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')
        fig.add_vline(nRoutes*(i+1)-0.5, line_width=0.5, line_color='black')

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
