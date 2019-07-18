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
 
    properties = {
        avgSpeed : {
            title: 'Average Speed',
            units: '(cm/s)',
            active: true,
            trace: {}
        },
        strideLength : {
            title: 'Stride Length',
            units: '(cm)',
            active: true,
            trace: {}
        },
        supportTime : {
            title: 'Support Time',
            units: '(s)',
            active: true,
            trace: {}
        },
        strideLengthCOV : {
            title: 'Stride Length Variance',
            units: '(%)',
            active: true,
            trace: {}
        },
        stepWidthCOV : {
            title: 'Step Width Variance',
            units: '(%)',
            active: true,
            trace: {}
        },
        stepLengthVar : {
            title: 'Step Length Variance',
            units: '(cm)',
            active: true,
            trace: {}
        } 
    }
    

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

    for (let day in binsDaily) {
        dailyAverages[day] = {};
        Object.keys(properties).forEach(function(property) {
            dailyAverages[day][property] = propertyAverage(binsDaily[day], property)
        });
    }
    console.log(dailyAverages);

    //create 1D arrays for each property to later be used as y values
    propertyCols = {};
    Object.keys(properties).forEach(function(property) {
        propertyCols[property] = Object.values(dailyAverages).map(entry => entry[property])
    });

    Object.keys(properties).forEach(function(property, i) {
        /*sidebar*/
        const li = document.createElement("li");
        li.id = properties[property].title;
        li.innerHTML = properties[property].title + "     ";
        const input = document.createElement("input");
        input.type = "checkbox"; input.id = property + 'Switch'; input.class = "checkbox-switch";
        document.getElementById('toggle-container').appendChild(li);
        document.getElementById(li.id).appendChild(input);
        /* switches */
        const el = document.getElementById(property + 'Switch');
        const mySwitch = new Switch(el, {
            checked: true,
            size: 'small'
            //onChange: function(){ $('#avgSpeedPlot').toggle() }
        });

        // Create traces for each property
        const axisSuffix = (i === 0 ? '' : i + 1);
        properties[property]['trace'] = {
            x: Object.keys(dailyAverages).map(string => new Date(parseInt(string))),
            y: propertyCols[property],
            mode: 'markers+lines',
            type: 'scatter',
            yaxis: 'y' + axisSuffix,
            marker: {size: 12}
        }
    });
    Plotly.newPlot('plot', plotlyGetInitData(properties), plotlyGetInitLayout(properties));
}

function plotlyGetInitLayout(properties) {
    const topMarginHeight = 50;
    const subplotHeight = 300;
    const layout = {
        height: topMarginHeight + subplotHeight * Object.values(properties).filter(p => p.active).length,
        margin: {
            b: 0,
            t: topMarginHeight
        },
        grid: {
            xaxes: ['x'],
            ygap: 0,
            yaxes: Object.values(properties).map(p => p.trace.yaxis),
            xside: 'top plot'
        },
        xaxis: {
            linecolor: 'black',
            mirror: 'all',
        }
    }
    Object.values(properties).forEach(function(propertyVal, i) {
        const axisSuffix = (i === 0 ? '' : i + 1);
        layout['yaxis' + axisSuffix] = {
            title: { text: propertyVal.title + ' ' + propertyVal.units }
        }
    });
    return layout;
}

function plotlyGetInitData(properties) {
    return Object.values(properties).map(p => p.trace);
}

function plotlyToggleSubplot(properties, property) {
    properties[property].active = !properties[property].active;
    if (properties[property].active) {
        const newIndex = Object.entries(properties).filter(([k, v]) => v.active).map(([k, v]) => k).indexOf(property)
        Plotly.addTraces('plot', properties[property].trace, newIndex);
    }
    else {
        const oldIndex = Object.entries(properties).filter(([k, v]) => (v.active || k == property)).map(([k, v]) => k).indexOf(property)
        Plotly.deleteTraces('plot', oldIndex);
    }
    Plotly.relayout('plot', plotlyGetRelayout(properties))
}

function plotlyGetRelayout(properties) {
    const topMarginHeight = 50;
    const subplotHeight = 300;
    var layout = {
        'height': topMarginHeight + subplotHeight * Object.values(properties).filter(p => p.active).length,
        'grid.yaxes': Object.values(properties).filter(p => p.active).map(p => p.trace.yaxis)
    };
    return layout;
}

loadJSON(myCallback);

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

function togglePlotTest(plotId) {
    traces[plotId].active = !traces[plotId].active;
    if (traces[plotId].active) {
        const newIndex = Object.entries(traces).filter(([k, v]) => v.active).map(([k, v]) => k).indexOf(plotId.toString())
        Plotly.addTraces('test-plot', traces[plotId].trace, newIndex);
    }
    else {
        const oldIndex = Object.entries(traces).filter(([k, v]) => (v.active || k == plotId)).map(([k, v]) => k).indexOf(plotId.toString())
        Plotly.deleteTraces('test-plot', oldIndex);
    }
    Plotly.relayout('test-plot', getRelayoutTest())
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

function getActiveDataTest() {
    return Object.values(traces).filter(x => x.active).map(x => x.trace);
}

function getRelayoutTest() {
    const topMarginHeight = 50;
    const subplotHeight = 300;
    var layout = {
        'height': topMarginHeight + subplotHeight * Object.values(traces).filter(x => x.active).length,
        'grid.yaxes': Object.values(traces).filter(x => x.active).map(x => x.trace.yaxis)
    };
    return layout;
}

function initLayoutTest() {
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
        },
        yaxis: {
            title: { text: 'Y1' }
        },
        yaxis2: {
            title: { text: 'Y2' }
        },
        yaxis3: {
            title: { text: 'Y3' }
        }
    };
    return layout;
}

Plotly.newPlot('test-plot', getActiveDataTest(), initLayoutTest(), {responsive: true});