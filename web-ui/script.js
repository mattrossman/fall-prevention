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

var allSegments;

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
    binsDaily = _.groupBy(allSegments, function(s) {
        // Zero out the time data, just compare by the date information
        return new Date(s.time).setHours(0, 0, 0, 0);
    })
    function avgWalkingSpeed(segments) {
        sum = segments.reduce(function(acc, segment) { return acc + segment.avgSpeed; }, 0);
        return sum / segments.length;
    }

    for (var day in binsDaily) {
        binsDaily[day] = avgWalkingSpeed(binsDaily[day]);
    }
    console.log(binsDaily);
}

loadJSON(myCallback);


var trace1 = {
    x: [1, 2, 3, 4],
    y: [10, 15, 13, 17],
    type: 'scatter'
};

var data = [trace1];

Plotly.newPlot('trend', data);