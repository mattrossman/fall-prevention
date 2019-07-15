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
        avgSpeedCol: Object.values(dailyAverages).map(entry => entry.avgSpeed),
        strideLengthCol: Object.values(dailyAverages).map(entry => entry.strideLength),
        supportTimeCol: Object.values(dailyAverages).map(entry => entry.supportTime),
        strideLengthCOVCol: Object.values(dailyAverages).map(entry => entry.strideLengthCOV),
        stepWidthCOVCol: Object.values(dailyAverages).map(entry => entry.stepWidthCOV),
        stepLengthVarCol: Object.values(dailyAverages).map(entry => entry.stepLengthVar)
    }

    var trace1 = {
        x: Object.keys(dailyAverages),
        y: propertyCols.avgSpeedCol,
        type: 'scatter'
    };
    var data = [trace1];

    Plotly.newPlot('trend', data);
}

loadJSON(myCallback);




