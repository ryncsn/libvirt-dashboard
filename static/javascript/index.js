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

$.whenWithProgress = function(arrayOfPromises, progessCallback) {
    var cntr = 0;
    for (var i = 0; i < arrayOfPromises.length; i++) {
        arrayOfPromises[i].done(function() {
            progressCallback(++cntr, arrayOfPromises.length);
        });
    }
    return jQuery.when.apply(jQuery, arrayOfPromises);
}
