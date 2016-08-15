function prettier(data){
    var regex = /^\s*$/ ;
    if(!data)
        return "---"
    if(data instanceof Array)
        if(data.length === 0)
            return "---"
    if(typeof data === 'string'){
        if(data.match(regex))
            return "---"
        return data.replace(/(?:\r\n|\r|\n)/g, '<br/>');
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
            'WARN': '<span style="color:yellow">WARN</span>',
            'WARNI': '<span style="color:yellow">WARNI</span>',
        };
        var regex = Object.keys(color_keyword).join("|");
        console.log("(" + regex + ")", "g");
        data = data.replace(new RegExp("(" + regex + ")", "g"), function(m, key){
            return color_keyword[key];
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
