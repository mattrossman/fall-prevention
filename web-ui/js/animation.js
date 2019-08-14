import * as THREE from './three.module.js';

function loadJSON(callback) {
    var xobj = new XMLHttpRequest();
    xobj.overrideMimeType("application/json");
    xobj.open('GET', 'walk_segment_1.json', true);
    xobj.onreadystatechange = function () {
        if (xobj.readyState == 4 && xobj.status == "200") {
            callback(JSON.parse(xobj.responseText));
        }
    };
    xobj.send(null);
}


var getAnimationClip = function(json) {
    
    var animations = []

    const time_array = json['0']['0'][1];
    const scale_arrays = json['2']['0'][2];
    const scale_array = array_zipper(scale_arrays)
    var tracks = [];
    var positions = [];
    let j = 0;
    Object.values(json).forEach(function(kf_type, j) {
        Object.values(kf_type).forEach(function(bones) {
            //var kf = 0;
            if (j == 0) {
                var kf = new THREE.VectorKeyframeTrack(bones[0], time_array, array_zipper(bones[2]));
                tracks.push(kf);
                positions.push(bones[2])
            
            } /* else if (j == 1) {
                kf = new THREE.QuaternionKeyframeTrack(bones[0], time_array, array_zipper(bones[2]));
            } else {
                kf = new THREE.VectorKeyframeTrack(bones[0], time_array, scale_array);
            }
            tracks.push(kf);
            */
        });
    });

    const duration = time_array[time_array.length - 1]
    const name = 'walk_1'

    animations.push(new THREE.AnimationClip(name, duration, tracks));
    console.log(animations);
    console.log(positions);
    var scene, camera; 
    var renderer = new THREE.WebGLRenderer({
        antialias: true
    });
    var w = 960;
    var h = 500;
    //renderer.setSize(w, h);
    //document.body.appendChild(renderer.domElement);

    //renderer.setClearColor(0xEEEEEE, 1.0);
    var scene, camera, cube; 
    ///////////////////////////
    scene = new THREE.Scene();
    initCamera();
    initRenderer();
    initCube();
    render()

    
    document.body.appendChild(renderer.domElement);
    function initCamera() {
        camera = new THREE.PerspectiveCamera(70, w / h, 1, 10);
        camera.position.set(0, 3.5, 5);
        camera.lookAt(scene.position);
    }
    
    function initRenderer() {
        renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(w, h);
    }
    function initCube() {
        cube = new THREE.Mesh(new THREE.CubeGeometry(2, 2, 2), new THREE.MeshNormalMaterial());
        scene.add(cube);
    }
    
    var SPEED = 0.01;

    function rotateCube() {
        cube.rotation.x -= SPEED * 2;
        cube.rotation.y -= SPEED;
        cube.rotation.z -= SPEED * 3;
    }

    function render() {
        requestAnimationFrame(render);
        rotateCube();
        renderer.render(scene, camera);
    }
    /*
    var camera = new THREE.PerspectiveCamera(5, w / h, 1, 10000);
    camera.position.z = 0;
    camera.position.x = 0;
    camera.position.y = 1;
    

    var scene = new THREE.Scene();

    var scatterPlot = new THREE.Object3D();
    scene.add(scatterPlot);


    scatterPlot.rotation.y = 0;

    var axesHelper = new THREE.AxesHelper( 5 );
    scene.add( axesHelper );

    var mat = new THREE.PointsMaterial({
        color: 0x000000,
        size: 100
    });

    var pointCount = positions.length;
    var pointGeo = new THREE.Geometry();
    for (var i = 0; i < pointCount; i++) {
        var x = positions[i][0][0];
        var y = positions[i][1][0];
        var z = positions[i][2][0];
        pointGeo.vertices.push(v(x, y, z));
        
        pointGeo.colors.push(new THREE.Color(0xffffff));

    }
    console.log(pointGeo.vertices);
    console.log(scene.position);

    var points = new THREE.Points(pointGeo, mat);
    console.log(points);
    scatterPlot.add(points);

    renderer.render(scene, camera);
    camera.lookAt(0, 0, 0);
    /*
    var paused = false;
    var last = new Date().getTime();
    var down = false;
    var sx = 0,
        sy = 0;
        
    window.onmousedown = function(ev) {
        down = true;
        sx = ev.clientX;
        sy = ev.clientY;
    };
    window.onmouseup = function() {
        down = false;
    };
    window.onmousemove = function(ev) {
        if (down) {
            var dx = ev.clientX - sx;
            var dy = ev.clientY - sy;
            scatterPlot.rotation.y += dx * 0.01;
            camera.position.y += dy;
            sx += dx;
            sy += dy;
        }
    }
    */
}

loadJSON(getAnimationClip);

function array_zipper(a_of_a) {
    var zipped = [];
    for (let i=0; i<a_of_a[0].length; i++) {
        a_of_a.forEach(function(array) {
            zipped.push(array[i]);
        });
    }
    return zipped
}

function v(x, y, z) {
    return new THREE.Vector3(x, y, z);
}

