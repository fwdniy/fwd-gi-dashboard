import streamlit as st
import pandas as pd
from tools import filter, snowflake
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
from styles.formatting import format_numbers, conditional_formatting
from streamlit_tree_select import tree_select
from streamlit.components.v1 import html

with st.expander("Filters"):
    filter.build_date_filter()
    filter.build_lbu_tree(True)

current_date = st.session_state['Valuation Date'].strftime('%Y-%m-%d')
compare_date = st.session_state['Comparison Date'].strftime('%Y-%m-%d')
lbu_selection = st.session_state['lbu_tree_data']

fund_codes = str(lbu_selection).replace("[", "").replace("]", "")

if fund_codes == '':
    st.write('No funds selected!')
    st.stop()



#region CSS

custom_css = {
        ".ag-cell": {"font-size": "90%"},
        ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
        ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
        ".ag-header-cell-resize": {"display": "none"},
        ".ag-header-group-cell.ag-header-group-cell-with-group": {"display": "flex", "justify-content": "flex-end"},
        ".ag-header-group-cell.ag-header-group-cell-with-group[aria-expanded='true']": {"display": "flex", "justify-content": "flex-start"},
}

entityComparatorString = """
function entityPivotComparator(a, b) {
    const customOrder = ['value'];
    return customOrder.indexOf(a) - customOrder.indexOf(b);
}
"""

fundComparatorString = """
function fundPivotComparator(a, b) {
    const customOrder = ['value'];
    return customOrder.indexOf(a) - customOrder.indexOf(b);
}
"""

#endregion

#region Actual Allocation by Bloomberg Asset Type

st.write("Actual Allocation by Bloomberg Asset Type")

query = f"SELECT closing_date, bbg_asset_type, sum(net_mv) / 1000000 As sum_net_mv FROM funnelweb WHERE closing_date IN ('{current_date}', '{compare_date}') AND fund_code IN ({fund_codes}) GROUP BY closing_date, bbg_asset_type ORDER BY closing_date, bbg_asset_type;"
df = snowflake.query(query)
df['CLOSING_DATE'] = df['CLOSING_DATE'].replace({current_date: 'Current Date', compare_date: 'Compare Date'})
df = df.pivot(index='BBG_ASSET_TYPE', columns='CLOSING_DATE', values='SUM_NET_MV')
df = df[['Current Date', 'Compare Date']]
df.reset_index(inplace=True)
df.rename(columns={'BBG_ASSET_TYPE': 'Bloomberg Asset Type'}, inplace=True)
df.fillna(0, inplace=True)

df['Delta Δ'] = df['Current Date'] - df['Compare Date']
df['Current %'] = (df['Current Date'] / df['Current Date'].sum()) * 100
df['Compare %'] = (df['Compare Date'] / df['Compare Date'].sum()) * 100
df['Delta Δ %'] = df['Current %'] - df['Compare %']
total_row = pd.DataFrame(df.sum(numeric_only=True)).T
df = pd.concat([df, total_row], ignore_index=True)
df.iloc[-1, df.columns.get_loc('Bloomberg Asset Type')] = 'Total'

gb = GridOptionsBuilder.from_dataframe(df)

gb.configure_default_column(
    resizable=True,
    filterable=True,
    editable=False,
)

for column in df.columns:
    if column != "Bloomberg Asset Type" and "Δ" not in column:
        gb.configure_column(field=column, valueFormatter=format_numbers())

gb.configure_column(field='Delta Δ', valueFormatter=format_numbers(), cellStyle=conditional_formatting(sum(df['Current Date']) * -0.05 / 2, 0, sum(df['Current Date']) * 0.05 / 2))
gb.configure_column(field='Delta Δ %', valueFormatter=format_numbers(), cellStyle=conditional_formatting())

go = gb.build()

AgGrid(df, gridOptions=go, height=450, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)

#endregion

#region Entity / Fund Actual Allocation by FWD Asset Type

#region Sum Tables

def build_sum_aggrid(df, column, columnName, groupField = "FWD_ASSET_TYPE", groupFieldName = "FWD Asset Type", sort = "asc", height=630):
    gb = GridOptionsBuilder.from_dataframe(df)
    
    gb.configure_default_column(resizable=True, filterable=True, editable=False, flex=1, minWidth=170)
    gb.configure_grid_options(pivotMode=True, autoGroupColumnDef={'cellRendererParams': { 'suppressCount': 'true'}, 'pinned': 'left'}, suppressAggFuncInHeader=True, isGroupOpenByDefault=True, pivotDefaultExpanded=-1, pivotRowTotals='left', groupIncludeTotalFooter=True)

    gb.configure_column(groupField, header_name=groupFieldName, pinned="left", rowGroup=True, sort=sort)
    gb.configure_column('ENTITY', pivot=True, pivotComparator=JsCode(entityComparatorString))
    gb.configure_column('FUND_CODE', pivot=True, pivotComparator=JsCode(fundComparatorString))
    gb.configure_column(column, aggFunc='sum', header_name=columnName, valueFormatter=format_numbers())

    go = gb.build()
    
    AgGrid(df, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)

query = f"SELECT fund_code, fwd_asset_type, sum(net_mv) / 1000000 As sum_net_mv, sum(dv01_000) / 1000 AS sum_dv01, sum(cs01_000) / 100 AS sum_cs01 FROM funnelweb WHERE closing_date  = '{current_date}' AND fund_code IN ({fund_codes}) GROUP BY fund_code, fwd_asset_type ORDER BY fund_code, fwd_asset_type;"
df = snowflake.query(query)

fund_entity_dict = {}
for key, value_list in st.session_state['hk_entities'].items():
    for value in value_list:
        fund_entity_dict[value] = key

df['ENTITY'] = df['FUND_CODE'].map(fund_entity_dict)
df = df[['ENTITY', 'FUND_CODE', 'FWD_ASSET_TYPE', 'SUM_NET_MV', 'SUM_DV01', 'SUM_CS01']]

assetTypeCount = len(df['FWD_ASSET_TYPE'].unique())
height = 120 + 30 * assetTypeCount

entityComparatorString = entityComparatorString.replace('value', "', '".join(df.groupby('ENTITY').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))
fundComparatorString = fundComparatorString.replace('value', "', '".join(df.groupby('FUND_CODE').agg({'SUM_NET_MV': 'sum'}).sort_values(by='SUM_NET_MV', ascending=False).index.tolist()))

st.write("Actual Allocation by FWD Asset Type")
build_sum_aggrid(df, 'SUM_NET_MV', 'Net MV', height=height)

st.write("DV01 by FWD Asset Type")
build_sum_aggrid(df, 'SUM_DV01', 'DV01', height=height)

st.write("CS01 by FWD Asset Type")
build_sum_aggrid(df, 'SUM_CS01', 'CS01', height=height)

#endregion

#region Weighted Average Tables

#region Weighted Average Functions

def build_wa_df(field, fieldName):
    query = f"""WITH mvs AS (SELECT fund_code, fwd_asset_type, sum(net_mv) AS sum_net_mv FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND {field} <> 0 GROUP BY fund_code, fwd_asset_type ORDER BY fund_code, fwd_asset_type), 
    weight AS (SELECT fund_code, fwd_asset_type, sum({field} * net_mv) AS {fieldName} FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) GROUP BY fund_code, fwd_asset_type ORDER BY fund_code, fwd_asset_type)
    SELECT weight.fund_code, weight.fwd_asset_type, COALESCE(sum_net_mv, 0) AS sum_net_mv, COALESCE({fieldName}, 0) AS {fieldName} FROM weight LEFT JOIN mvs ON mvs.fund_code = weight.fund_code AND mvs.fwd_asset_type = weight.fwd_asset_type;"""

    df = snowflake.query(query)
    df['ENTITY'] = df['FUND_CODE'].map(fund_entity_dict)
    df = df[['ENTITY', 'FUND_CODE', 'FWD_ASSET_TYPE', 'SUM_NET_MV', fieldName]]

    return df

def build_wa_aggrid(df, column, toBeName, weightColumn, height=630):
    gb = GridOptionsBuilder.from_dataframe(df)
    
    gb.configure_default_column(resizable=True, filterable=True, editable=False, flex=1, minWidth=170)
    gb.configure_grid_options(pivotMode=True, autoGroupColumnDef={'cellRendererParams': { 'suppressCount': 'true'}, 'pinned': 'left'}, suppressAggFuncInHeader=True, isGroupOpenByDefault=True, pivotDefaultExpanded=-1, pivotRowTotals='left', groupIncludeTotalFooter=True)

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

    weightedAverageFuncString = weightedAverageFuncString.replace("aggColumn", column)
    weightedAverageFuncString = weightedAverageFuncString.replace("weightColumn", weightColumn)
    
    gb.configure_column(field='FWD_ASSET_TYPE', header_name="FWD Asset Type", pinned="left", rowGroup=True, sort='asc')
    gb.configure_column('ENTITY', pivot=True, pivotComparator=JsCode(entityComparatorString))
    gb.configure_column('FUND_CODE', pivot=True, pivotComparator=JsCode(fundComparatorString))
    gb.configure_column(column, aggFunc=JsCode(weightedAverageFuncString), header_name=toBeName, valueFormatter=format_numbers())

    go = gb.build()

    AgGrid(df, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)

#endregion

st.write("Credit Spread by FWD Asset Type")
df = build_wa_df('credit_spread_bp', 'SUMPRODUCT_CS')
build_wa_aggrid(df, 'SUMPRODUCT_CS', 'Credit Spread', 'SUM_NET_MV', height)

st.write("Duration by FWD Asset Type")
df = build_wa_df('duration', 'SUMPRODUCT_DUR')
build_wa_aggrid(df, 'SUMPRODUCT_DUR', 'Duration', 'SUM_NET_MV', height)

st.write("Yield by FWD Asset Type")
df = build_wa_df('ytm', 'SUMPRODUCT_YTM')
build_wa_aggrid(df, 'SUMPRODUCT_YTM', 'YTM', 'SUM_NET_MV', height)

st.write("WARF by FWD Asset Type")
df = build_wa_df('warf', 'SUMPRODUCT_WARF')
build_wa_aggrid(df, 'SUMPRODUCT_WARF', 'WARF', 'SUM_NET_MV', height)

#endregion

#region Ratings Profile

query = f"SELECT fund_code, index, final_rating, sum(net_mv) / 1000000 AS sum_net_mv FROM funnelweb, supp.ratings_ladder WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND funnelweb.warf <> 0 AND final_rating = rating GROUP BY fund_code, index, final_rating ORDER BY index;"
df = snowflake.query(query)
df['ENTITY'] = df['FUND_CODE'].map(fund_entity_dict)
df = df[['ENTITY', 'FUND_CODE', 'FINAL_RATING', 'SUM_NET_MV']]

assetTypeCount = len(df['FINAL_RATING'].unique())
height = 120 + 30 * assetTypeCount

st.write("Actual Allocation by Final Rating")
build_sum_aggrid(df, 'SUM_NET_MV', 'Net MV', 'FINAL_RATING', 'Final Rating', '', height)

#endregion

#region NR Securities

query =f"""WITH mvs AS (SELECT security_name, sum(net_mv) AS sum_net_mv, ROW_NUMBER() OVER (ORDER BY sum_net_mv DESC) AS index FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND final_rating = 'NR' AND bbg_asset_type <> 'Bond Option' GROUP BY security_name ORDER BY sum_net_mv DESC),
fund_mvs AS (SELECT security_name, fund_code, net_mv, ROW_NUMBER() OVER (ORDER BY net_mv DESC) AS index FROM funnelweb WHERE closing_date = '{current_date}' AND fund_code IN ({fund_codes}) AND final_rating = 'NR' AND bbg_asset_type <> 'Bond Option' ORDER BY net_mv DESC)
SELECT mvs.security_name, fund_code, net_mv FROM mvs LEFT JOIN fund_mvs ON mvs.security_name = fund_mvs.security_name ORDER BY mvs.index, fund_mvs.index;"""
df = snowflake.query(query)

st.write("NR Securities by Allocation")

if "nrSecuritiesExpanded" not in st.session_state:
    st.session_state["nrSecuritiesExpanded"] = -1

col1, col2, col3 = st.columns([1, 1, 8])
with col1:
    if st.button("Expand all", use_container_width=True):
        st.session_state["nrSecuritiesExpanded"] = -1
with col2:
    if st.button("Collapse all", use_container_width=True):
        st.session_state["nrSecuritiesExpanded"] = 0

gb = GridOptionsBuilder.from_dataframe(df)
    
gb.configure_default_column(resizable=True, filterable=True, editable=False, flex=1, minWidth=170)
gb.configure_grid_options(autoGroupColumnDef={'cellRendererParams': { 'suppressCount': 'true'}, 'pinned': 'left'}, suppressAggFuncInHeader=True, groupDisplayType='multipleColumns', groupDefaultExpanded=st.session_state["nrSecuritiesExpanded"])

gb.configure_column('SECURITY_NAME', header_name='Security Name', pinned="left", rowGroup=True, hide=True)
gb.configure_column('FUND_CODE', header_name='Fund Code', pinned="left")
gb.configure_column('NET_MV', aggFunc='sum', header_name='Net MV', valueFormatter=format_numbers())

go = gb.build()

AgGrid(df, gridOptions=go, height=height, theme='streamlit', allow_unsafe_jscode=True, custom_css=custom_css)

#endregion

#endregion