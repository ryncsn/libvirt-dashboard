function prettier(data){
    var regex = /^\s*$/ ;
    if(!data)
        return "---"
    if(typeof data === 'string')
        if(data.match(regex))
            return "---"
        return data.replace(/(?:\r\n|\r|\n)/g, '<br/>');
    return data
}
