from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
from .formatting import format_numbers, conditional_formatting
from .js import get_autofit_code, get_default_custom_formatting_css

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import math

@dataclass
class AgGridOptions:
    """Default configuration options for AG Grid."""
    pivot_mode: bool = True
    group_expanded: int = -1
    group_open: bool = False
    pivot_expanded: int = -1
    suppress_agg_header: bool = True
    animate_rows: bool = False
    suppress_hover: bool = True
    
    # Totals and headers
    pivot_total: Optional[str] = None
    group_total: str = 'top'
    remove_pivot_headers: bool = False
    
    # Callbacks and special features
    cell_value_change: Optional[str] = None
    pinned_top: Optional[Dict] = None
    group_display_type: Optional[str] = None
    row_selection: Dict[str, Any] = field(default_factory=dict)  # Use default_factory to avoid mutable default
    header_name: Optional[str] = None

class AgGridBuilder:
    def __init__(self, df, editable=False, min_width=None, max_width=None):
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(resizable=True, editable=editable, minWidth=min_width, filter=False, maxWidth=max_width)
        
        self.gb = gb
        self.df = df.copy()
        self.charts = []
        
    def add_options(self, **kwargs) -> None:
        """
        Configure grid options with sensible defaults.
        
        Args:
            **kwargs: Override default options defined in GridOptions
        """
        # Create options with defaults
        options = AgGridOptions(**kwargs)
        
        # Configure group column definition
        group_column_def = {
            'cellRendererParams': {'suppressCount': 'true'},
            'pinned': 'left'
        }
        
        if options.header_name:
            group_column_def['headerName'] = options.header_name
            
        # Configure grid options
        self.gb.configure_grid_options(
            pivotMode=options.pivot_mode,
            autoGroupColumnDef=group_column_def,
            suppressAggFuncInHeader=options.suppress_agg_header,
            groupDefaultExpanded=options.group_expanded,
            isGroupOpenByDefault=options.group_open,
            pivotDefaultExpanded=options.pivot_expanded,
            pivotRowTotals=options.pivot_total,
            grandTotalRow=options.group_total,
            removePivotHeaderRowWhenSingleValueColumn=options.remove_pivot_headers,
            onCellValueChanged=options.cell_value_change,
            pinnedTopRowData=options.pinned_top,
            groupDisplayType=options.group_display_type,
            rowSelection=options.row_selection,
            animateRows=options.animate_rows,
            suppressRowHoverHighlight=options.suppress_hover
        )
    
    def set_pivot_column(self, column='CLOSING_DATE', comparator = None):
        if comparator != None:
            comparator = JsCode(comparator)
        
        self.gb.configure_column(column, pivot=True, pivotComparator=comparator)

    def add_column(self, column_name, value_formatter=format_numbers, cell_style=conditional_formatting, cell_style_ranges={}, filter=False, row_group=False, sort=None, pinned=None):
        if callable(value_formatter):
            value_formatter = value_formatter()
        if callable(cell_style):
            cell_style = cell_style(**cell_style_ranges)
            
        self.gb.configure_column(field=column_name, filter=filter, valueFormatter=value_formatter, cellStyle=cell_style, rowGroup=row_group, sort=sort, pinned=pinned)
    
    def add_columns(self, column_names, value_formatter=format_numbers, cell_style=None, cell_style_ranges={}, filter=False, row_group=True, sort=None, hide=False, comparator=None, labels=None, editable=False, max_width=None, pinned=None):
        if not row_group and pinned == None:
            pinned = None
            
        if comparator != None:
            comparator = JsCode(comparator)
            
        if labels == None:
            labels = column_names
            
        if callable(value_formatter):
            value_formatter = value_formatter()
        if callable(cell_style):
            cell_style = cell_style(**cell_style_ranges)
        
        for i in range (0, len(column_names)):
            column_name = column_names[i]
            label = labels[i]
            
            self.gb.configure_column(field=column_name, valueFormatter=value_formatter, cellStyle = cell_style, pinned=pinned, rowGroup=row_group, sort=sort, hide=hide, header_name=label, editable=editable, filter=filter, comparator=comparator, maxWidth=max_width)
        
    def add_values(self, values, labels=None, filter=False, max_width=None):
        if labels == None:
            labels = values

        for column in values:
            label = labels[values.index(column)]
            self.gb.configure_column(column, aggFunc='sum', header_name=label, valueFormatter=format_numbers(), filter=filter, maxWidth=max_width)

    def add_value(self, column, label, aggFunc = None, sort=None, filter=False, max_width=None):
        if aggFunc != None:
            aggFunc = JsCode(aggFunc)
        else:
            aggFunc = 'sum'
        
        if sort != None:
            self.gb.configure_column(column, aggFunc=aggFunc, header_name=label, valueFormatter=format_numbers(), sort=sort, filter=filter, maxWidth=max_width)
        else:
            self.gb.configure_column(column, aggFunc=aggFunc, header_name=label, valueFormatter=format_numbers(), filter=filter, maxWidth=max_width)

        
    def add_chart(self, chart_type: str, categories: list, values: list, chart_title: str, reverse: bool = False):
        for category in categories:
            self.gb.configure_column(field=category, headerName=category.title(), filter='agSetColumnFilter', chartDataType='category')
                        
            chart_dict = """chartType: "{chartType}",
                        chartThemeName: 'ag-material',
                        cellRange: {
                            columns: ["{columns}"]
                        },
                        aggFunc: "sum",
                        chartThemeOverrides: {
                            common : {
                                title : {
                                    enabled: true,
                                    text: '{title}',
                                    fontFamily: 'Source Sans Pro, sans-serif'
                                },
                                axes : {
                                    category: {
                                        label: { 
                                            fontFamily: 'Source Sans Pro, sans-serif',
                                        }
                                    },
                                    number : {
                                        reverse: {reverse},
                                        label: { 
                                            fontFamily: 'Source Sans Pro, sans-serif',
                                        }
                                    },
                                },
                            },
                            bar : {
                                series: {
                                    label: {
                                        enabled: true,
                                        placement: 'outside-end',
                                        fontFamily: 'Source Sans Pro, sans-serif',
                                        formatter: (params) => {
                                            const values = ['{values}'];
                                            let lastValue = values.reduce((acc, value) => params.datum[value] != 0 ? value : acc, '');

                                            if (params.yKey === lastValue) {
                                                const total = params.datum['{param_values}'];
                                                if (total != 0) {
                                                    return total.toFixed(0);
                                                }
                                            }

                                            return '';
                                        },
                                        padding: 10,
                                        color: 'black',
                                    },
                                }
                            }
                        },
                        chartContainer: document.querySelector("#chart{count}"),"""
            
            chart_dict = chart_dict.replace("{chartType}", chart_type)
            chart_dict = chart_dict.replace("{columns}", '", "'.join([category] + values))
            chart_dict = chart_dict.replace("{count}", str(len(self.charts) + 1))
            chart_dict = chart_dict.replace("{title}", category.replace("_", " ").title() + chart_title)
            chart_dict = chart_dict.replace("{param_values}", '\'] + params.datum[\''.join(values))
            chart_dict = chart_dict.replace("{values}", '\', \''.join(values))
            chart_dict = chart_dict.replace("{reverse}", str(reverse).lower())
            
            self.charts.append(chart_dict)
        
        for value in values:
            self.gb.configure_column(field=value, headerName=value.title(), chartDataType='series')
        
    def build_charts(self, grid_height = 400, chart_height = 500):
        
        charts = self.charts
        
        margin_height = 20
        chart_count = len(charts)
        div_count = math.ceil(chart_count / 2)
        
        charts_code = ""
        divs_code = ""
        
        height = grid_height + div_count * (chart_height + margin_height)
        
        for i in range(0, chart_count):
            chart_code = """
                    var chart{count} = document.createElement("div");
                    chart{count}.id = "chart{count}";
                    chart{count}.style.height = "{chart_height}px";
                    chart{count}.style.width = "45%";
                    
                    chartDiv{div_count}.appendChild(chart{count});
                    
                    params.api.createCrossFilterChart({
                        {chart}
                    });
                    """
            
            chart_code = chart_code.replace("{count}", str(i + 1))
            chart_code = chart_code.replace("{div_count}", str(math.ceil((i + 1) / 2)))
            chart_code = chart_code.replace("{chart}", charts[i])
            chart_code = chart_code.replace("{chart_height}", str(chart_height))
            
            charts_code += chart_code
        
        for i in range(0, div_count):
            div_code = """
                    var chartDiv{count} = document.createElement("div");
                    chartDiv{count}.id = "chartDiv{count}";
                    chartDiv{count}.style.height = "{chart_height}px";
                    chartDiv{count}.style.width = "100%";
                    chartDiv{count}.style.marginTop = "{margin}px"; 
                    chartDiv{count}.style.display = "flex";
                    chartDiv{count}.style.justifyContent = "space-between";
                    grid.appendChild(chartDiv{count});
                """
            
            div_code = div_code.replace("{count}", str(i + 1))
            div_code = div_code.replace("{chart_height}", str(chart_height))
            div_code = div_code.replace("{margin}", str(margin_height))
            
            divs_code += div_code
        
        first_rendered_code = """
            function(params) {
                var grid = document.querySelector("#gridContainer");
                var table = grid.childNodes[0];
                table.style.height = "{grid_height}px";
                {rowChanged}
                
                {divs}
                {charts}
            }
        """
        
        first_rendered_code = first_rendered_code.replace("{grid_height}", str(grid_height))
        first_rendered_code = first_rendered_code.replace("{divs}", divs_code)
        first_rendered_code = first_rendered_code.replace("{charts}", charts_code)
        
        # Remove existing charts
        row_changed_code = first_rendered_code.replace("{rowChanged}", """while (grid.childNodes.length > 1) {
                                                                            grid.removeChild(grid.childNodes[1]);
                                                                        }""")
        first_rendered_code = first_rendered_code.replace("{rowChanged}", "")
        
        return JsCode(first_rendered_code), JsCode(row_changed_code), height

    def show_grid(self, height: float = 630, reload_data: bool = False, update_on: list[str] = [], update_mode: str = 'MODEL_CHANGED', custom_functions: dict[str, str] = {}, column_order: list[str] = [], autofit = True, key: str = None):
        go = self.gb.build()
        
        if column_order != []:
            column_names = [column['field'] for column in go['columnDefs']]
            column_indexes = [column_names.index(column) for column in column_order]
            go['columnDefs'] = [go['columnDefs'][index] for index in column_indexes]
                    
        if len(custom_functions) > 0:
            for key, value in custom_functions.items():
                go[key] = value
        
        if autofit:
            go["onFirstDataRendered"] = JsCode(get_autofit_code())
        
        if self.charts != []:
            go["onFirstDataRendered"], go["onRowDataUpdated"], height = self.build_charts()
        
        self.go = go
        self.grid = AgGrid(self.df, key=key, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=get_default_custom_formatting_css(), reload_data=reload_data, update_on=update_on, update_mode=update_mode, enable_enterprise_modules='enterprise+AgCharts')
