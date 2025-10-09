def get_autofit_code():
    js = """
        function onFirstDataRendered(params) {
            params.api.autoSizeAllColumns();
        }
        """
        
    return js

def get_default_custom_formatting_css():
    js = {
            ".ag-cell": {"font-size": "90%"},
            ".ag-theme-streamlit": {"--ag-cell-horizontal-border": "none"},
            ".ag-header-cell": {"color": "white", "background-color": "rgb(232,119,34)", "--ag-header-cell-hover-background-color": "rgb(246,179,128)"},
            ".ag-header-cell-resize": {"display": "none"},
            ".ag-header-group-cell.ag-header-group-cell-with-group": {"display": "flex", "justify-content": "flex-start"},
            ".ag-header-group-cell.ag-header-group-cell-with-group[aria-expanded='true']": {"display": "flex", "justify-content": "flex-start"},
        }
    
    return js

def get_custom_comparator():
    js = """
        function orderComparator(a, b) {
            const customOrder = ['value'];
            return customOrder.indexOf(a) - customOrder.indexOf(b);
        }
    """
    
    return js

def get_weighted_average_sum():
    js = """
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
    
    return js

def get_button_builder():
    js = """
        class BtnCellRenderer {
            init(params) {
                if (params.node.rowPinned === 'top') {
                    this.params = params;
                    this.eGui = document.createElement('div');
                    this.eGui.style.height = '25px';
                    this.eGui.innerHTML = `
                    <span>
                        <button id='click-button' 
                            class='btn-simple' 
                            style='color: ${this.params.color}; background-color: ${this.params.background_color}; text-align: center; line-height: 20px; height: 25px'>Click!</button>
                    </span>
                    `;
                    this.eButton = this.eGui.querySelector('#click-button');
                    this.btnClickedHandler = this.btnClickedHandler.bind(this);
                    this.eButton.addEventListener('click', this.btnClickedHandler);
                }
            }

            getGui() {
                return this.eGui;
            }

            refresh() {
                return true;
            }

            destroy() {
                if (this.eButton) {
                    this.eGui.removeEventListener('click', this.btnClickedHandler);
                }
            }

            btnClickedHandler(event) {
                if (confirm('Are you sure you want to CLICK?') == true) {
                    if(this.params.getValue() == 'clicked') {
                        this.refreshTable('');
                    } else {
                        this.refreshTable('clicked');
                    }
                }
            }

            refreshTable(value) {
                this.params.setValue(value);
            }
        };
    """
    
    return js