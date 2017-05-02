(function(root, factory){
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  }
  else if (typeof exports === 'object') {
    module.exports = factory();
  } else {
    factory();
  }
})(this, function(){
  function colorize(data){
    if(typeof data === 'string'){
      var color_keyword = {
        'HEADER': 'blue',
        'INFO': 'green',
        'PASS': 'green',
        'DEBUG': 'gray',
        'SKIP': 'yellow',
        'WARNI': 'yellow',
        'WARN': 'yellow',
        'ERROR': 'red',
        'FAIL': 'red',
        'TIMEOUT': 'red',
        'INVALID': 'red',
      };
      var regex = Object.keys(color_keyword).join("|");
      data = data.replace(new RegExp("(" + regex + ")", "g"), function(m){
        return '<span style="color:' + color_keyword[m] + '">' + m + '</span>';
      });
    }
    return data;
  }
  return colorize;
});
