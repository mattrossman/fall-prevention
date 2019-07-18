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

    const domainSize = 1 / properties.length;
    const subplotHeight = 300;

    const traces = [];
    const layout = {
        shapes: [],
        height: subplotHeight * properties.length,
        xaxis: {
            side: 'top',
        }
    };
    properties.forEach(function(property, i) {
        const axisSuffix = (i === 0 ? '' : i + 1);
        const trace = {
            x: Object.keys(dailyAverages).map(string => new Date(parseInt(string))),
            y: propertyCols[property],
            mode: 'markers+lines',
            type: 'scatter',
            yaxis: 'y' + axisSuffix,
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
        const yTop = 1 - i * domainSize;
        const yBottom = 1 - (i + 1) * domainSize;
        const yaxisLayout = {
            domain: [yBottom, yTop],
            title: {
                text: plotTitle + ' ' + plotUnits
            }
        };
        layout['yaxis' + axisSuffix] = yaxisLayout;
        // Black line at the bottom of each subplot
        const divider = {
            type: 'line',
            xref: 'paper',
            yref: 'paper',
            x0: 0,
            x1: 1,
            y0: yBottom,
            y1: yBottom
        };
        layout.shapes.push(divider);
        traces.push(trace);
    });
    Plotly.newPlot('plot', traces, layout);
}

loadJSON(myCallback);

const el = document.querySelector('.checkbox-switch');
const mySwitch = new Switch(el, {
    checked: true,
    onChange: function(){ $('#avgSpeedPlot').toggle() }
});

var trace1 = {
    x: [0, 1, 2],
    y: [10, 11, 12],
    // domain: { row: 0 },
    yaxis: 'y',
    type: 'scatter'
};

var trace2 = {
    x: [2, 3, 4],
    y: [100, 110, 120],
    // domain: { row: 1 },
    yaxis: 'y2',
    type: 'scatter'
};

var trace3 = {
    x: [3, 4, 5],
    y: [1000, 1100, 1200],
    // domain: { row: 2 },
    yaxis: 'y3',
    type: 'scatter'
};

function togglePlot(plotId) {
    traces[plotId].active = !traces[plotId].active;
    Plotly.react('test-plot', getActiveData(), getActiveLayout())
}

var traces = {
    1: {
        active: true,
        trace: trace1
    },
    2: {
        active: true,
        trace: trace2
    },
    3: {
        active: true,
        trace: trace3
    }
}

function getActiveData() {
    return Object.values(traces).filter(x => x.active).map(x => x.trace);
}

function getActiveLayout() {
    const topMarginHeight = 50;
    const subplotHeight = 300;
    var layout = {
        height: topMarginHeight + subplotHeight * Object.values(traces).filter(x => x.active).length,
        margin: {
            b: 0,
            t: topMarginHeight
        },
        grid: {
            xaxes: ['x'],
            ygap: 0,
            yaxes: Object.values(traces).filter(x => x.active).map(x => x.trace.yaxis),
            // yaxes: data.map(trace => trace.yaxis)
            xside: 'top plot'
        },
        xaxis: {
            linecolor: 'black',
            mirror: 'all',
        }
    };
    return layout;
}



Plotly.newPlot('test-plot', getActiveData(), getActiveLayout(), {responsive: true});