function prettier(data){
    if(!data)
        return "---"
    if(typeof data === 'string')
        return data.replace(/(?:\r\n|\r|\n)/g, '<br/>');
    return data
}
