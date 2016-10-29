!function(root, factory){
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  }
  else if (typeof exports === 'object') {
    module.exports = function(){
      factory();
    };
  } else {
    factory();
  }
}(this, function(){
  function htmlify(data, emptyReplace){
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

    var emptyRegex = /^\s*$/ ;
    emptyReplace = (emptyReplace === undefined) ? "---" : emptyReplace;
    if(!data){
      return "---";
    }
    if(data instanceof Array)
      if(data.length === 0){
        return "---";
      }
      if(typeof data === 'string'){
        if(data.match(emptyRegex)){
          return "---";
        }
        return data.replace(new RegExp("(" + Object.keys(entityMap).join("|") + ")", "g"), function (s) {
          return entityMap[s];
        });
      }
      return data;
  }
  return htmlify;
});
