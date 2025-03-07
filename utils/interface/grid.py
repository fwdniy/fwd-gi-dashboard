import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import math

def format_numbers(decimal_points = 2, divide_by = 1):
    number_formatting = """
            function(params) {
                if (params.value == null) {
                    return params.value;
                } else {
                    var value = params.value / divide_by;
                    if (value === 0) {
                        return '-';
                    }
                    value = value.toLocaleString(undefined, { minimumFractionDigits: decimal_points, maximumFractionDigits: decimal_points });
                    return value;
                }
            }
        """
    
    number_formatting = number_formatting.replace('decimal_points', str(decimal_points)).replace('divide_by', str(divide_by))

    return JsCode(number_formatting)

def conditional_formatting(lower_bound = -5, mid_point = 0, upper_bound = 5):
    conditional_formatting = """
        function(params) {
            var value = params.value;
            var color = '';
            var ratio = (1 - Math.abs(value / upper_bound)) * 255;
                                   
            if (value >= upper_bound) {
                color = 'rgb(0, 127, 0)';
            } else if (value < upper_bound && value > mid_point) {
                var pRatio = (1 - Math.abs(value / upper_bound / 2)) * 255;
                color = 'rgb(' + ratio + ',' + pRatio + ',' + ratio + ')';
            } else if (value == mid_point) {
                color = 'white';
            } else if (value < mid_point && value > lower_bound) {
                var pRatio = (1 - Math.abs(value / upper_bound / 5)) * 255;
                color = 'rgb(' + pRatio + ',' + ratio + ',' + ratio + ')';
            } else if (value <= lower_bound) {
                color = 'rgb(190, 0, 0)';
            }
                    
            var fontColor = 'black';
                                   
            if(value >= (upper_bound - mid_point) * 0.4 || value <= (lower_bound - mid_point) * 0.4){
                fontColor = 'white';
            }
                    
            return {
                'color': fontColor,
                'backgroundColor': color
            };
        };
    """

    conditional_formatting = conditional_formatting.replace('lower_bound', str(lower_bound)).replace('mid_point', str(mid_point)).replace('upper_bound', str(upper_bound))

    return JsCode(conditional_formatting)

class AgGridBuilder:
    custom_css = {
            ".ag-cell": {"font-size": "90%"},
            ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
            ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
            ".ag-header-cell-resize": {"display": "none"},
            ".ag-header-group-cell.ag-header-group-cell-with-group": {"display": "flex", "justify-content": "flex-start"},
            ".ag-header-group-cell.ag-header-group-cell-with-group[aria-expanded='true']": {"display": "flex", "justify-content": "flex-start"},
        }
    
    customOrderComparatorString = """
        function orderComparator(a, b) {
            const customOrder = ['value'];
            return customOrder.indexOf(a) - customOrder.indexOf(b);
        }
    """

    weightedAverageFuncString = """
    function weightedAverage(params) {
            let assetType = params.rowNode.key;
            let fund = params.pivotResultColumn.colId.split("_")[3].split("-").slice(1).join("-");
            let totalWeight = 0;
            let weightedSum = 0;
            let group = false;
            let rowTotal = false;
            let grandTotal = false;

            if (assetType == null) {
                grandTotal = true;
                group = true;
            }

            if (fund == "") {
                const tempFund = params.pivotResultColumn.colId;

                if (tempFund.includes("PivotRowTotal")) {
                    rowTotal = true;
                }
                
                group = true;
                fund = params.pivotResultColumn.colId.split("_")[3];
            }

            // Individual Row
            if (!group) {
                params.rowNode.allLeafChildren.forEach((value) => {
                    const rowFund = value.data.FUND_CODE;
                    const rowAssetType = value.data.FWD_ASSET_TYPE;

                    if (rowFund == fund && rowAssetType == assetType) {
                        matchingWeight = value.data.weightColumn;
                    }
                });

                params.values.forEach((value, index) => {
                    totalWeight += matchingWeight;
                    weightedSum += value;
                });
            } else if (group) {
                params.rowNode.allLeafChildren.forEach((value) => {
                    const rowEntity = value.data.ENTITY;
                    const rowFund = value.data.FUND_CODE;
                    const rowAssetType = value.data.FWD_ASSET_TYPE;

                    if (rowEntity == fund && rowAssetType == assetType || rowTotal && rowAssetType == assetType || grandTotal && (rowFund == fund || rowEntity == fund) || rowTotal && assetType == null) {
                        totalWeight += value.data.weightColumn;
                        weightedSum += value.data.aggColumn;
                    }
                });
            }

            return totalWeight === 0 ? 0 : weightedSum / totalWeight;
        }
    """
    
    def __init__(self, df, editable=False, min_width=None):
        self.df = df
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_default_column(resizable=True, editable=editable, minWidth=min_width, filter=False)
        self.gb = gb
        self.charts = []

    def add_options(self, pivot_total=None, group_total='top', group_open=False, remove_pivot_headers=False, pivot_mode=True, group_expanded=-1, cell_value_change=None, pinned_top=None, group_display_type=None, row_selection=None, header_name=None):
        #pivotRowTotals='left'
        #onCellValueChanged='onCellValueChanged'
        #groupDisplayType="multipleColumns"
        #rowSelection={'mode': 'multiRow', 'groupSelects': 'filteredDescendants', 'checkboxLocation': 'autoGroupColumn'}
        group_column_def = {'cellRendererParams': { 'suppressCount': 'true' }, 'pinned': 'left'}
        if header_name != None:
            group_column_def['headerName'] = header_name
        
        self.gb.configure_grid_options(pivotMode=pivot_mode, autoGroupColumnDef=group_column_def, suppressAggFuncInHeader=True, groupDefaultExpanded=group_expanded, isGroupOpenByDefault=group_open, pivotDefaultExpanded=-1, pivotRowTotals=pivot_total, grandTotalRow=group_total, removePivotHeaderRowWhenSingleValueColumn=remove_pivot_headers, onCellValueChanged=cell_value_change, pinnedTopRowData=pinned_top, groupDisplayType=group_display_type, rowSelection=row_selection, animateRows=False, suppressRowHoverHighlight=True)

    def add_columns(self, columns, row_group=True, value_formatter=format_numbers, sort=None, hide=False, comparator=None, labels=None, editable=False, filter=False):
        pinned = "left"

        if not row_group:
            pinned = None

        if comparator != None:
            comparator = JsCode(comparator)

        if labels == None:
            labels = columns
        
        for column in columns:
            label = labels[columns.index(column)]
            
            if comparator != None and value_formatter == None:
                self.gb.configure_column(field=column, pinned=pinned, rowGroup=row_group, sort=sort, hide=hide, comparator=comparator, header_name=label, editable=editable, filter=False)
            elif value_formatter == None:
                self.gb.configure_column(field=column, pinned=pinned, rowGroup=row_group, sort=sort, hide=hide, header_name=label, editable=editable, filter=False)
            else:
                self.gb.configure_column(field=column, valueFormatter=value_formatter(), pinned=pinned, rowGroup=row_group, sort=sort, hide=hide, header_name=label, editable=editable, filter=False)

    def add_column(self, column, value_formatter=format_numbers, cell_style=conditional_formatting, cell_style_ranges=None, filter=False):
        if cell_style == None and value_formatter == None:
            self.gb.configure_column(field=column, filter=False)
        elif cell_style == None:
            self.gb.configure_column(field=column, valueFormatter=value_formatter(), filter=filter)
        elif type(cell_style) == dict and value_formatter == None:
            self.gb.configure_column(field=column, cellStyle=cell_style, filter=filter)
        elif cell_style_ranges == None:
            self.gb.configure_column(field=column, valueFormatter=value_formatter(), cellStyle=cell_style(), filter=filter)
        else:
            self.gb.configure_column(field=column, valueFormatter=value_formatter(), cellStyle=cell_style(cell_style_ranges[0], cell_style_ranges[1], cell_style_ranges[2]), filter=filter)
        
    def set_pivot_column(self, column='CLOSING_DATE', comparator = None):
        if comparator != None:
            comparator = JsCode(comparator)
        
        self.gb.configure_column(column, pivot=True, pivotComparator=comparator)

    def add_values(self, values, labels=None, filter=False):
        if labels == None:
            labels = values

        for column in values:
            label = labels[values.index(column)]
            self.gb.configure_column(column, aggFunc='sum', header_name=label, valueFormatter=format_numbers(), filter=filter)

    def add_value(self, column, label, comparator = None, sort=None, filter=False):
        if comparator != None:
            comparator = JsCode(comparator)
        else:
            comparator = 'sum'
        
        if sort != None:
            self.gb.configure_column(column, aggFunc=comparator, header_name=label, valueFormatter=format_numbers(), sort=sort, filter=filter)
        else:
            self.gb.configure_column(column, aggFunc=comparator, header_name=label, valueFormatter=format_numbers(), filter=filter)

    def add_chart(self, chart_type: str, categories: list, values: list, chart_title: str):
        for category in categories:
            self.gb.configure_column(field=category, headerName=category.title(), filter='agSetColumnFilter', chartDataType='category')
            
            chart_dict = """chartType: "{chartType}",
                        cellRange: {
                            columns: ["{columns}"]
                        },
                        aggFunc: "sum",
                        chartThemeOverrides: {
                            common : {
                                title : {
                                    enabled: true,
                                    text: '{title}'
                                }
                            }
                        },
                        chartContainer: document.querySelector("#chart{count}"),"""
            
            chart_dict = chart_dict.replace("{chartType}", chart_type)
            chart_dict = chart_dict.replace("{columns}", '", "'.join([category] + values))
            chart_dict = chart_dict.replace("{count}", str(len(self.charts) + 1))
            chart_dict = chart_dict.replace("{title}", category.replace("_", " ").title() + chart_title)
            
            self.charts.append(chart_dict)
        
        for value in values:
            self.gb.configure_column(field=value, headerName=value.title(), chartDataType='series')
        
    def build_charts(self, grid_height = 400, chart_height = 400):
        
        charts = self.charts
        
        chart_count = len(charts)
        div_count = math.ceil(chart_count / 2)
        
        charts_code = ""
        divs_code = ""
        
        height = grid_height + div_count * chart_height
        
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
                    chartDiv{count}.style.marginTop = "20px"; 
                    chartDiv{count}.style.display = "flex";
                    chartDiv{count}.style.justifyContent = "space-between";
                    grid.appendChild(chartDiv{count});
                """
            
            div_code = div_code.replace("{count}", str(i + 1))
            div_code = div_code.replace("{chart_height}", str(chart_height))
            
            divs_code += div_code
        
        generate_charts_code = """
            function onFirstDataRendered(params) {
                var grid = document.querySelector("#gridContainer");
                var table = grid.childNodes[0];
                table.style.height = "{grid_height}px";
                
                {divs}
                {charts}
            }
        """
        
        generate_charts_code = generate_charts_code.replace("{grid_height}", str(grid_height))
        generate_charts_code = generate_charts_code.replace("{divs}", divs_code)
        generate_charts_code = generate_charts_code.replace("{charts}", charts_code)
        
        return (JsCode(generate_charts_code), height)
    
    def show_grid(self, height=630, reload_data=False, update_on=[], update_mode='MODEL_CHANGED', custom_functions={}):
        go = self.gb.build()
        
        if len(custom_functions) > 0:
            for key, value in custom_functions.items():
                go[key] = value
        
        autofit = JsCode("""
        function onFirstDataRendered(params) {
            params.api.autoSizeAllColumns();
        }
        """)
        
        go["onFirstDataRendered"] = autofit
        
        if self.charts != []:
            (on_first_data_rendered, height) = self.build_charts()
            go["onFirstDataRendered"] = on_first_data_rendered
        
        self.go = go
        self.grid = AgGrid(self.df, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=self.custom_css, reload_data=reload_data, update_on=update_on, update_mode=update_mode)