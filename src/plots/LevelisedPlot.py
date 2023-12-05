import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from posted.calc_routines.LCOX import LCOX
from posted.config.config import flowTypes, techs

from src.utils import load_yaml_config_file
from src.plots.BasePlot import BasePlot


class LevelisedPlot(BasePlot):
    figs = load_yaml_config_file(f"figures/LevelisedPlot")
    _add_subfig_name = True

    def _decorate(self, inputs: dict, outputs: dict, subfigs: dict):
        super(LevelisedPlot, self)._decorate(inputs, outputs, subfigs)

        # loop over commodities (three columns)
        commodities = list(inputs['value_chains'].keys())
        for c, comm in enumerate(commodities):
            # add commodity annotations above subplot
            for subfigPlot in subfigs.values():
                self._add_annotation_comm(subfigPlot, comm, c)

    type_mapping = {
        r'^cap$': 'capital',
        r'^fop$': 'fonmco',
        r'^transp_cost:.*$': 'transport',
        r'^dem_cost:elec$': 'elec',
        r'^dem_cost:(coal|ng)$': 'energy',
        r'^dem_cost:\b(?!(elec|coal|ng))\b.*$': 'rawmat',
    }

    def plot(self, inputs: dict, outputs: dict, subfig_names: list) -> dict:
        cfg = self._fig_cfgs['fig5']
        commodities = list(inputs['value_chains'].keys())

        # create figure
        fig = make_subplots(
            cols=len(commodities),
            horizontal_spacing=0.035,
        )

        # add bars for each subplot
        for c, comm in enumerate(commodities):
            comm_data = self._prepare(outputs, comm, cfg)

            ymax = self._add_bars(fig, c, comm_data)

            # update layout of subplot
            self._update_axis_layout(
                fig, c,
                xaxis=dict(
                    title='',
                    categoryorder='array',
                    categoryarray=sorted(comm_data['impcase_display']),
                ),
                yaxis=dict(
                    title='',
                    range=[0.0, ymax]
                ),
            )

            # add cost differences from Base Case
            if self._target != 'webapp':
                self._add_annotations(fig, c, comm_data, ymax)

        # update layout of all plots
        fig.update_layout(
            barmode='stack',
            yaxis_title=cfg['yaxis_title'],
            legend_title='',
        )

        return {'fig5': fig}

    def _prepare(self, outputs: dict, comm: str, cfg: dict):
        # produce LCOX DataTable by assuming final elec prices and applying calc routine
        lcox = outputs['tables'][comm] \
            .assume(outputs['cases'][comm]) \
            .calc(LCOX)

        # extract dataframe from LCOX DataTable and convert to plottable format
        comm_data = lcox.data['LCOX'] \
            .pint.dequantify().droplevel('unit', axis=1) \
            .stack(['process', 'type']).to_frame('value') \
            .reset_index() \
            .query(f"epdcase=='{cfg['epdcase']}'") \
            .drop(columns=['epdcase'])

        # map types
        comm_data['ptype'] = comm_data['type'].replace(regex=self.type_mapping)

        # rename import cases (1 to 1A/B and add subtitles)
        comm_data['impcase_display'] = comm_data['impcase'] \
            .map({
                case_name: f"<b>{case_name + ('A/B' if case_name == 'Case 1' else '')}</b>:<br>{case_desc}"
                for case_name, case_desc in cfg['case_names'].items()
            })

        # prepare hover data
        if self._target == 'webapp':
            comm_data['hover_ptype'] = comm_data['ptype'].map({
                ptype: display['label']
                for ptype, display in cfg['cost_types'].items()
            })
            comm_data['hover_flow'] = comm_data['type'].map({
                f"dem_cost:{flow_id}": flowSpecs['name']
                for flow_id, flowSpecs in flowTypes.items()
            } | {
                f"transp_cost:{flow_id}": flow_specs['name']
                for flow_id, flow_specs in flowTypes.items()
            })
            comm_data['hover_proc'] = comm_data['process'].map({
                tid: tech_specs['name']
                for tid, tech_specs in techs.items()
            })

        return comm_data

    # add stacked bars showing levelised cost components
    def _add_bars(self, fig: go.Figure, c: int, comm_data: pd.DataFrame):
        # determine ymax
        ymax = (1.15 if self._target == 'print' else 1.05) * comm_data.query("impcase=='Base Case'").value.sum()

        # split up into main data and h2 cases data
        main_data = comm_data \
            .query("impsubcase!='Case 1A' & type!='transp_cost:h2'") \
            .assign(impsubcase=lambda df: df['impcase'])
        h2transp_data = comm_data \
            .query("impcase=='Case 1' & type=='transp_cost:h2'")

        # prepare hover info
        hover = self._target == 'webapp'
        hovercols = ['impsubcase', 'hover_ptype', 'hover_flow', 'hover_proc', 'value'] if hover else None
        hovercomp = {
            'header_basic': '<b>%{customdata[1]}</b><br>',
            'header_flow': '<b>%{customdata[1]} (%{customdata[2]})</b><br>',
            'impcase': 'Import case: %{customdata[0]}<br>',
            'process': 'Process: %{customdata[3]}<br>',
            'cost': 'Cost: %{customdata[4]} EUR/t',
            'extra': '<extra></extra>',
        }
        hovertemplate_basic = ''.join(hovercomp[c] for c in ['header_basic', 'impcase', 'process', 'cost', 'extra'])
        hovertemplate_flow = ''.join(hovercomp[c] for c in ['header_flow', 'impcase', 'process', 'cost', 'extra'])
        hovertemplate_transp = ''.join(hovercomp[c] for c in ['header_flow', 'impcase', 'cost', 'extra'])

        # add traces for all cost types
        for ptype, display in self._glob_cfg['cost_types'].items():
            this_data = main_data \
                .query(f"ptype=='{ptype}'") \
                .sort_index(level='impcase') \

            if self._target == 'print':
                this_data = this_data \
                    .groupby(['ptype', 'impcase_display']) \
                    .agg({'value': 'sum'}) \
                    .reset_index()

            # for hover template determine if this type has a flow associated
            hovertemplate = (
                None if not hover else
                hovertemplate_transp if ptype == 'transport' else
                hovertemplate_flow if ptype != 'elec' and this_data['hover_flow'].notna().all() else
                hovertemplate_basic
            )

            fig.add_trace(
                go.Bar(
                    x=this_data['impcase_display'],
                    y=this_data['value'],
                    marker_color=display['colour'],
                    name=display['label'],
                    showlegend=not c,
                    width=0.8,
                    hoverinfo='text' if hover else 'skip',
                    hovertemplate=hovertemplate,
                    customdata=this_data[hovercols] if hover else None,
                ),
                row=1,
                col=c + 1,
            )

        display = self._glob_cfg['cost_types']['transport']
        base_val = main_data.query(f"impcase=='Case 1'").value.sum()

        for s, subcase in enumerate(h2transp_data.impsubcase.unique()):
            p = h2transp_data.query(f"impsubcase=='{subcase}'")
            fig.add_trace(
                go.Bar(
                    x=p['impcase_display'],
                    y=p['value'],
                    base=base_val,
                    marker_color=display['colour'],
                    name=display['label'],
                    showlegend=False,
                    width=0.4,
                    offset=-0.4 + 0.4 * s,
                    hoverinfo='text' if hover else 'skip',
                    hovertemplate=hovertemplate_transp,
                    customdata=p[hovercols] if hover else None,
                ),
                row=1,
                col=c + 1,
            )

        return ymax

    # add arrows indicating difference between cases
    def _add_annotations(self, fig: go.Figure, c: int, comm_data: pd.DataFrame, ymax: float):
        # select relevant x and y axes
        xref = f"x{c + 1 if c else ''}"
        yref = f"y{c + 1 if c else ''}"

        # select data for each subplot
        base_cost = comm_data.query("impcase=='Base Case'").value.sum()

        # deeper relocation arrow
        fig.add_annotation(
            showarrow=True,
            text=None,
            ax=0.15,
            ay=0.3,
            axref=xref + ' domain',
            ayref=yref + ' domain',
            x=0.85,
            y=0.3,
            xref=xref + ' domain',
            yref=yref + ' domain',
            arrowhead=1,
            arrowsize=0.8,
            arrowwidth=4,
            arrowcolor='#000000',
            opacity=1.0,
        )

        fig.add_annotation(
            showarrow=False,
            text='Deeper relocation',
            x=0.5,
            y=0.26,
            xref=xref + ' domain',
            yref=yref + ' domain',
        )

        # relocation savings horizontal line
        fig.add_hline(
            base_cost,
            line_color='black',
            line_width=self._styles['lw_thin'],
            row=1,
            col=c + 1,
        )

        fig.add_annotation(
            showarrow=False,
            text='Relocation savings',
            x=1.0,
            y=base_cost,
            xref=xref + ' domain',
            yref=yref,
            xanchor='right',
            yanchor='bottom',
        )

        # savings arrows
        correction = 0.018
        xshift = 2.5
        yshift = 28.0
        for i, impsubcase in enumerate(comm_data['impsubcase'].unique()[1:]):
            this_cost = comm_data.query(f"impsubcase=='{impsubcase}'").value.sum()

            cost_diff = this_cost - base_cost
            cost_diff_abs = abs(cost_diff)
            cost_diff_sign = '+' if cost_diff > 0.0 else '-'

            case_pos = float(i)+1
            if impsubcase == 'Case 1A':
                case_pos -= 0.2
            elif impsubcase == 'Case 1B':
                case_pos += 0.2
                case_pos -= 1
            if i > 1:
                case_pos -= 1

            fig.add_annotation(
                x=case_pos,
                y=min(this_cost, ymax),
                yref=yref,
                ax=case_pos,
                ay=base_cost + (correction * ymax if cost_diff < 0.0 else -correction * ymax),
                ayref=yref,
                arrowcolor='black',
                arrowwidth=self._styles['lw_thin'],
                arrowhead=2,
                row=1,
                col=c + 1,
            )

            fig.add_annotation(
                text=f" {cost_diff_sign}{cost_diff_abs:.1f}<br>({cost_diff_abs / base_cost * 100:.1f}%)",
                align='left',
                showarrow=False,
                x=case_pos,
                xanchor='left',
                xshift=xshift,
                y=base_cost,
                yanchor='middle',
                yref=yref,
                yshift=-yshift if impsubcase != 'Case 1A' else +yshift,
                row=1,
                col=c + 1,
            )
