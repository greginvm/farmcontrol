var isUndefined = function (obj) {
    return obj === void 0 || obj == null;
};

var ifUndefinedUse = function (obj, def, el) {
    if (isUndefined(obj)) {
        return def;
    }
    if (!isUndefined(el)) {
        return el;
    }
    return obj;
};


// Based on: http://stackoverflow.com/questions/7837456/comparing-two-arrays-in-javascript
var arraysEqual = function (array1, array2) {
    if (!array1 || !array2)
        return false;

    // compare lengths
    if (array1.length != array2.length)
        return false;

    for (var i = 0, l = array1.length; i < l; i++) {
        // Check if we have nested arrays
        if (array1[i] instanceof Array && array2[i] instanceof Array) {

            // recurse into the nested arrays
            if (!array1[i].equals(array2[i]))
                return false;
        }
        else if (array1[i] != array2[i]) {
            // Warning - two different object instances will never be equal: {x:20} != {x:20}
            return false;
        }
    }
    return true;
};


var isVisibleOnDevice = function (alias) {
    return $('#media-id-' + alias).is(':visible');
};

