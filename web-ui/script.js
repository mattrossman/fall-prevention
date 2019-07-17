function loadJSON(callback) {
    var xobj = new XMLHttpRequest();
    xobj.overrideMimeType("application/json");
    xobj.open('GET', 'dummy-segments.json', true);
    xobj.onreadystatechange = function () {
        if (xobj.readyState == 4 && xobj.status == "200") {
            callback(JSON.parse(xobj.responseText));
        }
    };
    xobj.send(null);
}

var myCallback = function(json) {
    allSegments = json;

    /*
        e.g.:
        {
            1234567: [
                { segment 1 .... },
                { segment 2 .... },
                { segment 3 .... }
            ]
        }
    */
    const binsDaily = _.groupBy(allSegments, function(s) {
        // Zero out the time data, just compare by the date information
        return new Date(s.time).setHours(0, 0, 0, 0);
    })
    function propertyAverage(segments, param) {
        sum = segments.reduce(function(acc, segment) { return acc + segment[param]; }, 0);
        return sum / segments.length;
    }
    dailyAverages = {};
    const properties = ['avgSpeed', 'strideLength', 'supportTime', 'strideLengthCOV', 'stepWidthCOV', 'stepLengthVar'];
    for (let day in binsDaily) {
        dailyAverages[day] = {};
        properties.forEach(function(property) {
            dailyAverages[day][property] = propertyAverage(binsDaily[day], property)
        });
    }
    console.log(dailyAverages);

    //create 1D arrays for each property to later be used as y values
    const propertyCols = {
        avgSpeed: Object.values(dailyAverages).map(entry => entry.avgSpeed),
        strideLength: Object.values(dailyAverages).map(entry => entry.strideLength),
        supportTime: Object.values(dailyAverages).map(entry => entry.supportTime),
        strideLengthCOV: Object.values(dailyAverages).map(entry => entry.strideLengthCOV),
        stepWidthCOV: Object.values(dailyAverages).map(entry => entry.stepWidthCOV),
        stepLengthVar: Object.values(dailyAverages).map(entry => entry.stepLengthVar)
    }

    properties.forEach(function(property) {
        var trace = {
            x: Object.keys(dailyAverages).map(string => new Date(parseInt(string))),
            y: propertyCols[property],
            mode: 'markers+lines',
            type: 'scatter',
            marker: {size: 12}
        };
        let plotTitle = '';
        let plotUnits = '';
        switch(property) {
            case 'avgSpeed':
                plotTitle = 'Average Speed';
                plotUnits = '(cm/s)';
                break;
            case 'strideLength':
                plotTitle = 'Stride Length';
                plotUnits = '(cm)';
                break;
            case 'supportTime':
                plotTitle = 'Support Time';
                plotUnits = '(s)';
                break;
            case 'strideLengthCOV':
                plotTitle = 'Stide Length Variance';
                plotUnits = '(%)';
                break;
            case 'stepWidthCOV':
                plotTitle = 'Step Width Variance';
                plotUnits = '(%)';
                break;
            case 'stepLengthVar':
                plotTitle = 'Step Length Variance';
                plotUnits = '(cm)';
                break;
            default:
                //error
        }
        var layout = {
            title: {
              text: plotTitle,
              font: {
                family: 'Arial, monospace', //gross
                size: 24
              },
              xref: 'paper',
              x: 0.00,
            },
            yaxis: {
                title: {
                  text: plotTitle + '  ' + plotUnits,
                  font: {
                    family: 'Arial, monospace',
                    size: 14,
                    color: '#7f7f7f'
                  }
                }
              }
        };
        const div = document.createElement("div");
        div.id = property + 'Plot';
        document.getElementById('plot-container').appendChild(div);
        Plotly.newPlot(property + 'Plot', [trace], layout);
        div.on('plotly_relayout', function(eventdata){
            if ('xaxis.range[0]' in eventdata && 'xaxis.range[1]' in eventdata) {
                console.log('X-axis was changed');
                const xMin = eventdata['xaxis.range[0]'];
                const xMax = eventdata['xaxis.range[1]'];
                $('.js-plotly-plot').each(function() {
                    // `this` refers to the DOM element for this iteration, i.e. a plot div
                    Plotly.relayout(this, {'xaxis.range': [xMin, xMax]});
                });
            }
            /*
            Monitoring changes to xaxis.autorange and calling relayout accordingly will result
            in an infinite loop, so the plotly_doubleclick event is used instead below.
            */
        });
        div.on('plotly_doubleclick', function() {
            console.log('X-axis was reset');
            $('.js-plotly-plot').each(function() {
                // `this` refers to the DOM element for this iteration, i.e. a plot div
                Plotly.relayout(this, {"xaxis.autorange": true});
            })
        });
    });
}

loadJSON(myCallback);

const el = document.querySelector('.checkbox-switch');
const mySwitch = new Switch(el, {
    checked: true,
    onChange: function(){ $('#avgSpeedPlot').toggle() }
});