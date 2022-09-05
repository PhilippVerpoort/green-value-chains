import re

import pandas as pd
import plotly.graph_objects as go

from src.load.load_default_data import all_routes, all_processes


def plotValueCreation(costData: pd.DataFrame, config: dict, subfigs_needed: list, is_webapp: bool = False):
    ret = {}


    # make adjustments to data
    costDataNew = __adjustData(costData, config) if subfigs_needed else None


    # produce figure
    ret['fig2'] = __produceFigure(costDataNew, config) if 'fig2' in subfigs_needed else None


    return ret


# make adjustments to data before plotting
def __adjustData(costData: pd.DataFrame, config: dict):
    # replace non-energy types with generic label
    if config['simplify_types']:
        mapping = {t: 'non-energy' for t in costData['type'] if t!='energy'}
        costDataNew = costData.replace({'type': mapping})
    else:
        costDataNew = costData


    # determine the route to plot for each commodity
    plottedRoutes = {
        c: next(key for key in costDataNew.query(f"commodity=='{c}'").route.unique()
        if key.endswith(str(config['import_route'][c])))
        for c in all_routes
    }


    # modify data for each commodity
    ret = []
    for commodity, showRoute in plottedRoutes.items():
        # query relevant commodity data for given route
        costDataNewComm = costDataNew.query(f"route=='{showRoute}' & val_year=={config['show_year']}")\
                                     .drop(columns=['component', 'route', 'val_year'])

        # get processes in the route
        processes = all_routes[commodity][re.sub('_\\d', '', showRoute)]['processes']
        processes_keys = list(processes.keys())

        # add upstream data for plotting
        for i, p in enumerate(processes_keys[:-1]):
            upstreamCostData = costDataNewComm.query(f"process=='{p}'").assign(type='upstream')
            costDataNewComm = pd.concat([costDataNewComm, upstreamCostData.assign(process=processes_keys[i+1])], ignore_index=True)

        # aggregate data over processes and types
        costDataNewComm = costDataNewComm.groupby(['commodity', 'process', 'type'])\
                                 .agg({'commodity': 'first', 'process': 'first', 'type': 'first', 'val': 'sum'})\
                                 .reset_index(drop=True)

        # add process labels
        costDataNewComm['process_label'] = [all_processes[p]['label'] for p in costDataNewComm['process']]

        # append data
        ret.append(costDataNewComm)

        # append dummy data for ordering entries correctly
        dummyData = pd.DataFrame.from_records([
            {
                'commodity': commodity,
                'process': p,
                'process_label': all_processes[p]['label'],
                'type': 'dummy',
                'val': 0.0,
            }
            for p in processes_keys
        ])

        ret.append(dummyData)


    return pd.concat(ret)


def __produceFigure(costData: pd.DataFrame, config: dict):
    # create figure
    fig = go.Figure()


    # add dummy entries such that the order is correct
    dummyData = costData.query(f"type=='dummy'")
    fig.add_trace(go.Bar(
        x=[dummyData.commodity, dummyData.process_label],
        y=dummyData.val,
        showlegend=False,
    ))


    # add traces for all cost types
    showTypes = [(t, d) for t, d in config['types'].items() if t != 'dummy']
    hasLegend = []
    index = 0
    total = len([p for c in costData.commodity.unique() for p in dummyData.query(f"commodity=='{c}'").process.unique()])
    for c in costData.commodity.unique():
        plotDataComm = costData.query(f"commodity=='{c}' and type!='dummy'")

        for p in dummyData.query(f"commodity=='{c}'").process.unique():
            plotDataProc = plotDataComm.query(f"process=='{p}'")

            # add pie charts
            plotDataPie = plotDataProc.query(f"type!='upstream'")
            fig.add_trace(go.Pie(
                labels=plotDataPie.replace({'type': {t: d['label'] for t,d in showTypes}}).type,
                values=plotDataPie.val,
                marker_colors=plotDataPie.replace({'type': {t: d['colour'] for t,d in showTypes}}).type,
                hovertemplate='<b>%{label}</b><extra></extra>',
                showlegend=False,
                domain=dict(x=[1.0/total*index, 1.0/total*(index+1)], y=[0.0, 0.23]),
            ))
            index += 1

            # add bar charts
            base = 0.0
            for type, display in showTypes:
                plotData = plotDataProc.query(f"type=='{type}'")
                addHeight = plotData.val.sum()

                if type == 'upstream' and p in config['skip_upstream']:
                    base += addHeight
                    continue

                fig.add_trace(go.Bar(
                    x=[plotData.commodity, plotData.process_label],
                    y=plotData.val,
                    base=base,
                    marker_color=display['colour'],
                    name=display['label'],
                    hovertemplate=f"<b>{display['label']}</b><br>Cost: %{{y}} EUR/t<extra></extra>",
                    showlegend=type not in hasLegend,
                    legendgroup=type,
                ))

                base += addHeight

                if type not in hasLegend:
                    hasLegend.append(type)


    # add vertical line
    for i, c in enumerate(costData.commodity.unique()[:-1]):
        nProcesses = costData.query(f"commodity=='{c}'").process.nunique()
        fig.add_vline(nProcesses*(i+1)-0.5, line_width=0.5, line_color='black')
        fig.add_vline(nProcesses*(i+1)-0.5, line_width=0.5, line_color='black')


    # set axes labels
    fig.update_layout(
        barmode='stack',
        xaxis=dict(title=''),
        yaxis=dict(title=config['yaxislabel'], range=[0.0, config['ymax']], domain=[0.4, 1.0]),
        legend_title='',
    )


    return fig
