function prettier(data){
    var entityMap = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': '&quot;',
        "'": '&#39;',
        "/": '&#x2F;',
        "\n\r": '<br/>',
        "\n": '<br/>',
        "\r": '<br/>',
    };

    var empty_regex = /^\s*$/ ;
    if(!data)
        return "---"
    if(data instanceof Array)
        if(data.length === 0)
            return "---"
    if(typeof data === 'string'){
        if(data.match(empty_regex))
            return "---"
        return data.replace(new RegExp("(" + Object.keys(entityMap).join("|") + ")", "g"), function (s) {
            return entityMap[s];
        });
    }
    return data
}

function colorize(data){
    //TODO performance
    if(typeof data === 'string'){
        var color_keyword = {
            'INFO': '<span style="color:green">INFO</span>',
            'DEBUG': '<span style="color:gray">DEBUG</span>',
            'ERROR': '<span style="color:red">ERROR</span>',
            'WARNI': '<span style="color:yellow">WARNI</span>',
            'WARN': '<span style="color:yellow">WARN</span>',
        };
        var regex = Object.keys(color_keyword).join("|");
        data = data.replace(new RegExp("(" + regex + ")", "g"), function(m){
            return color_keyword[m];
        });
    }
    return data;
}

$.whenWithProgress = function(arrayOfPromises, progessCallback) {
    var cntr = 0;
    for (var i = 0; i < arrayOfPromises.length; i++) {
        arrayOfPromises[i].done(function() {
            progressCallback(++cntr, arrayOfPromises.length);
        });
    }
    return jQuery.when.apply(jQuery, arrayOfPromises);
}
