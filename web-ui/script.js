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
 
    const properties = ['avgSpeed', 'strideLength', 'supportTime', 'strideLengthCOV', 'stepWidthCOV', 'stepLengthVar'];
    propertyInfo = {
        avgSpeed : ['Average Speed', '(cm/s)'],
        strideLength : ['Stride Length', '(cm)'],
        supportTime : ['Support Time', '(s)'],
        strideLengthCOV : ['Stride Length Variance', '(%)'],
        stepWidthCOV : ['Step Width Variance', '(%)'],
        stepLengthVar : ['Step Length Variance', '(cm)'] 
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
            side: 'top'
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
        var layout = {
            title: {
              text: propertyInfo[property][0],
              font: {
                family: 'Arial, monospace', 
                size: 24
              },
              xref: 'paper',
              x: 0.00,
            },
            yaxis: {
                title: {
                  text: propertyInfo[property][0] + ' ' + propertyInfo[property][1],
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

        /*sidebar*/
        const li = document.createElement("li");
        li.id = propertyInfo[property][0];
        li.innerHTML = propertyInfo[property][0] + "     ";
        const input = document.createElement("input");
        input.type = "checkbox"; input.id = property + 'Switch'; input.class = "checkbox-switch";
        document.getElementById('toggle-container').appendChild(li);
        document.getElementById(li.id).appendChild(input);
        
        Plotly.newPlot(property + 'Plot', [trace], layout);
        
    });
    Plotly.newPlot('plot', traces, layout);
}

loadJSON(myCallback);

const el = document.querySelector('.checkbox-switch');
const mySwitch = new Switch(el, {
    checked: true,
    onChange: function(){ $('#avgSpeedPlot').toggle() }
});