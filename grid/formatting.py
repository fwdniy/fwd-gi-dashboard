from st_aggrid import JsCode

def format_numbers(decimal_points = 2, divide_by = 1, percentage = False):
    number_formatting = """
            function(params) {
                if (params.value == null) {
                    return params.value;
                } else {
                    var value = params.value / divide_by;
                    if (value === 0) {
                        return '-';
                    }
                    decimal_logic
                    return value;
                }
            }
        """
        
    if not percentage:
        number_formatting = number_formatting.replace('decimal_logic', 'value = value.toLocaleString(undefined, { minimumFractionDigits: decimal_points, maximumFractionDigits: decimal_points });')
    else:
        number_formatting = number_formatting.replace('decimal_logic', "value = value.toLocaleString(undefined, { style: 'percent', minimumFractionDigits: decimal_points, maximumFractionDigits: decimal_points });")
    
    number_formatting = number_formatting.replace('decimal_points', str(decimal_points)).replace('divide_by', str(divide_by))

    return JsCode(number_formatting)


def conditional_formatting(**kwargs):
    lower_bound = kwargs.get('lower_bound', -5)
    mid_point = kwargs.get('mid_point', 0)
    upper_bound = kwargs.get('upper_bound', 5)

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