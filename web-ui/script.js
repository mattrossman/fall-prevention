const gaitPlotConfig = {
    marginTop: 50,
    subplotHeight: 300
}

const colorCycle = [
    '#1f77b4',  // muted blue
    '#ff7f0e',  // safety orange
    '#2ca02c',  // cooked asparagus green
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
            trace: {},
            thresholdMean: 94.25, /* cm/s */ 
            thresholdSD: 23.60
        },
        strideLength : {
            title: 'Stride Length',
            units: '(cm)',
            active: true,
            trace: {},
            thresholdMean: 111.15, /* cm */
            thresholdSD: 22.53

        },
        supportTime : {
            title: 'Support Time',
            units: '(s)',
            active: true,
            trace: {},
            thresholdMean: 0.29, /* s */ 
            thresholdSD: 0.07
        },
        strideLengthCOV : {
            title: 'Stride Length Variance',
            units: '(%)',
            active: true,
            trace: {},
            thresholdMean: 2.63, /* % */
            thresholdSD: 1.62
        },
        stepWidthCOV : {
            title: 'Step Width Variance',
            units: '(%)',
            active: true,
            trace: {},
            thresholdMean: 19.6, /* % */
            thresholdSD: 16.6
        },
        stepLengthVar : {
            title: 'Step Length Variance',
            units: '(cm)',
            active: true,
            trace: {},
            thresholdMean: .69, /* cm */
            thresholdSD: .157 
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

    //create 1D arrays for each property to later be used as y values
    propertyCols = {};
    Object.keys(properties).forEach(function(property) {
        propertyCols[property] = Object.values(dailyAverages).map(entry => entry[property])
    });

    Object.keys(properties).forEach(function(property, i) {
        /*sidebar*/
        const entry = document.createElement("li");
        const input = document.createElement("input");
        const label = document.createElement("label");
        input.type = "checkbox"; input.id = property + 'Switch'; input.class = "checkbox-switch";
        label.htmlFor = input.id;
        label.appendChild(document.createTextNode(properties[property].title))
        entry.appendChild(label);
        entry.appendChild(input);
        document.getElementById('toggle-container').appendChild(entry);
        /* switches */
        const mySwitch = new Switch(input, {
            checked: true,
            size: 'small',
            onChange: function(){ plotlyToggleSubplot(properties, property) }
        });

        // Create traces for each property
        const axisSuffix = (i === 0 ? '' : i + 1);
        properties[property]['trace'] = {
            name: property,
            x: Object.keys(dailyAverages).map(string => new Date(parseInt(string))),
            y: propertyCols[property],
            mode: 'markers+lines',
            type: 'scatter',
            yaxis: 'y' + axisSuffix,
            marker: {
                size: 12,      
                color: colorCycle[i]
            },
            line: {
                color: colorCycle[i]
            },
            hoverinfo: 'y+x'
        }
        // threshold
        const lowerBound = properties[property]['thresholdMean'] - 2*properties[property]['thresholdSD'];
        const upperBound = properties[property]['thresholdMean'] + 2*properties[property]['thresholdSD'];
        for(const index in propertyCols[property]) {
            if (propertyCols[property][index] >=  upperBound || propertyCols[property][index] <=  lowerBound) {
                properties[property]['trace']['marker']['color'] = '#FF0000';
            }
        }
    });
    
    Plotly.newPlot('plot', plotlyGetInitData(properties), plotlyGetInitLayout(properties), plotlyGetInitConfig());

    //clickable
    const myPlot = document.getElementById('plot');           
    myPlot.on('plotly_click', function(data){
        const x = data.points[0].x;
        const y = data.points[0].y;
        const property = data.points[0].curveNumber;
        clearSliderContent();
        loadSliderContent(binsDaily, x, y, (property + 1));
        const slider = $('#slider').slideReveal({
            push: false,
            overlay: true,
            position: "right",
            width: 300
        });
        slider.slideReveal('show');
    });
}

function plotlyGetInitLayout(properties) {
    const numActive = Object.values(properties).filter(p => p.active).length
    const layout = {
        height: gaitPlotConfig.marginTop + gaitPlotConfig.subplotHeight * numActive,
        margin: {
            b: 0,
            r: 0,
            t: gaitPlotConfig.marginTop
        },
        showlegend: false,
        grid: {
            xaxes: ['x'],
            ygap: 0,
            yaxes: Object.values(properties).map(p => p.trace.yaxis),
            xside: 'top plot'
        },
        xaxis: {
            linecolor: 'black',
            mirror: 'all',
        },
        shapes: getActivePlotShapes(properties),
        dragmode: 'pan'
    }
    Object.keys(properties).forEach(function(property, i) {
        const axisSuffix = (i === 0 ? '' : i + 1);
        const propertyMin = propertyCols[property].reduce(function(a, b) {return Math.min(a, b);});
        const propertyMax = propertyCols[property].reduce(function(a, b) {return Math.max(a, b);});
        const rangeBuffer = 2*properties[property].thresholdSD;
        layout['yaxis' + axisSuffix] = {
            title: { text: properties[property].title + ' ' + properties[property].units },
            range: [propertyMin - rangeBuffer, propertyMax + rangeBuffer],
        }
    });  
    return layout;
}

function getActivePlotShapes(properties) {
    const activeShapes = [];
    Object.keys(properties).forEach(function(property, i) {
        if(properties[property].active) {
            //add upper bound alert shape
            const upperBound = properties[property]['thresholdMean'] + 2*properties[property]['thresholdSD'];
            const upperShape = {
                type : 'rect',
                xref : 'paper',
                // y-reference is assigned to the y values
                yref : properties[property]['trace']['yaxis'],
                x0 : 0,
                y0 : upperBound,
                x1 : 1,
                y1 : 1000, //TODO
                fillcolor : '#FF0000',
                opacity : 0.2,
                line : {
                    width: 0
                },
                width : 0
            };

            //add lower bound alert shape
            const lowerBound = properties[property]['thresholdMean'] - 2*properties[property]['thresholdSD'];
            const lowerShape = {
                type : 'rect',
                xref : 'paper',
                // y-reference is assigned to the y values
                yref : properties[property]['trace']['yaxis'],
                x0 : 0,
                y0 : (-1)*Number.MAX_SAFE_INTEGER,
                x1 : 1,
                y1 : lowerBound,
                fillcolor : '#FF0000',
                opacity : 0.2,
                line : {
                    width: 0
                },
                width : 0
                
            };

            activeShapes.push(upperShape);
            activeShapes.push(lowerShape);
        }
    });
    return activeShapes;
}

function plotlyGetInitData(properties) {
    return Object.values(properties).map(p => p.trace);
}

function plotlyGetInitConfig() {
    return {
        responsive: true,
        displayModeBar: false,
        doubleClick: 'reset'
    }
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
    const numActive = Object.values(properties).filter(p => p.active).length;
    const layout = {
        'height': gaitPlotConfig.marginTop + gaitPlotConfig.subplotHeight * numActive,
        'grid.yaxes': Object.values(properties).filter(p => p.active).map(p => p.trace.yaxis),
        'shapes': getActivePlotShapes(properties)
    };
    return layout;
    
}

function clearSliderContent() {
    const content = document.getElementById('slideContent');
    if (content != null) {
        content.parentNode.removeChild(content);
    }
}

function loadSliderContent(binsDaily, x, y, property) {
    const date = x.split("-").map(string => parseInt(string));
    const dateObj = new Date(date[0], date[1] - 1, date[2]);
    const unixTime = Math.round(dateObj);
    //access walking segments from that day in binsDaily
    segments = binsDaily[unixTime];

    const slider = document.getElementById('slider');
    const content = document.createElement('div');
    content.setAttribute('id', 'slideContent');

    //header
    const header = document.createElement('header');
    const options = {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'};
    const headerText = document.createElement('a');
    headerText.innerHTML = dateObj.toLocaleDateString("en-US", options);

    //timeline
    const tlContainer = document.createElement('div');
    tlContainer.setAttribute('class', 'col-sm-12');
    const tl = document.createElement('div');
    tl.setAttribute('class', 'cntl');
    const tlBar = document.createElement('span');
    tlBar.setAttribute('class', 'cntl-bar cntl-center');
    const tlBarFill = document.createElement('span');
    tlBarFill.setAttribute('class', 'cntl-bar-fill');
    tlBar.appendChild(tlBarFill);
    tl.appendChild(tlBar);
    const tlStates = document.createElement('div');
    tlStates.setAttribute('class', 'cntl-states');
    //walking segments
    for (var i = 0; i < segments.length; i++) {
        const tlSubState = document.createElement('div');
        tlSubState.setAttribute('class', 'cntl-state');
        const tlContent = document.createElement('div');
        tlContent.setAttribute('class', 'cntl-content');
        const segmentAnchor = document.createElement('a');
        segmentAnchor.setAttribute('class', 'click');
        segmentAnchor.onclick = function() {

            //key is a ____??
            //const key = segments[i]['time'];
            //alert(key);
            const slider = $('#slider').slideReveal({
                push: false,
                overlay: true,
                position: "right",
                width: 850
            });
            slider.slideReveal('show');

            tlContainer.setAttribute('class', 'col-sm-4');
            const rendererContainer = document.createElement('div');
            rendererContainer.setAttribute('class', 'col-sm-8');

            tlContent.setAttribute('class', 'ccntl-content');

        
        }
        const contentHeader = document.createElement('h4');
        const segmentTime = new Date(parseInt(segments[i]['time']));
        const stringTime = segmentTime.toLocaleTimeString("en-US");
        contentHeader.innerHTML = stringTime;
        const description = document.createElement('p')
        description.innerHTML = Object.values(segments[i])[property];
        tlContent.appendChild(contentHeader);
        tlContent.appendChild(description);
        segmentAnchor.appendChild(tlContent);
        tlSubState.appendChild(segmentAnchor);
        const tlIcon = document.createElement('div');
        tlIcon.setAttribute('class', 'cntl-icon cntl-center');
        tlIcon.innerHTML = segmentTime.toLocaleTimeString([], {hour: 'numeric', minute:'2-digit'});
        tlSubState.appendChild(tlIcon);
        tlStates.appendChild(tlSubState);
    }
    tl.appendChild(tlStates);
    tlContainer.appendChild(tl);
    //tl.setAttribute('style', 'overflow-y:auto;');
    header.appendChild(headerText);
    content.appendChild(header);
    content.appendChild(tlContainer);
    slider.appendChild(content);
}

function showSkeleton(key) {

    //key is a ____??
    const slider = document.getElementById('slider');
    alert('bitch');
    slider.style.width = 600;

}

$(document).ready(function(e){
    $('.cntl').cntl({
        revealbefore: 300,
        anim_class: 'cntl-animate',
        onreveal: function(e){
            console.log(e);
        }
    });
});

loadJSON(myCallback);