const gaitPlotConfig = {
    marginTop: 50,
    subplotHeight: 300
}

const colorCycle = [
    '#1f77b4',  // muted blue
    '#ff7f0e',  // safety orange
    '#2ca02c',  // cooked asparagus green
    '#d62728',  // brick red
    '#9467bd',  // muted purple
    '#8c564b',  // chestnut brown
    '#e377c2',  // raspberry yogurt pink
    '#7f7f7f',  // middle gray
    '#bcbd22',  // curry yellow-green
    '#17becf'   // blue-teal
]

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
 
    const properties = {
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
            marker: {size: 12},
            line: {
                color: colorCycle[i]
            }
        }
    });
    Plotly.newPlot('plot', plotlyGetInitData(properties), plotlyGetInitLayout(properties));
}

function plotlyGetInitLayout(properties) {
    const numActive = Object.values(properties).filter(p => p.active).length
    const layout = {
        height: gaitPlotConfig.marginTop + gaitPlotConfig.subplotHeight * numActive,
        margin: {
            b: 0,
            t: gaitPlotConfig.marginTop
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
    const numActive = Object.values(properties).filter(p => p.active).length
    const layout = {
        'height': gaitPlotConfig.marginTop + gaitPlotConfig.subplotHeight * numActive,
        'grid.yaxes': Object.values(properties).filter(p => p.active).map(p => p.trace.yaxis)
    };
    return layout;
}

loadJSON(myCallback);