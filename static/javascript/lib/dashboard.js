(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['exports', 'jquery'], factory);
  } else if (typeof exports === 'object' && typeof exports.nodeName !== 'string') {
    factory(exports, require('jquery'));
  } else {
    factory((root.commonJsStrict = {}), root.$);
  }
}(this, function (exports, $) {
  var run_id = window.location.pathname.match("\/run\/([0-9]*)")[1];

  function _manualCaseAPI(method, caseName, data){
    return $.ajax("/api/run/" + run_id + "/manual/" + (caseName ? caseName + "/" : ""), {
      contentType: "application/json; charset=utf-8",
      method: method,
      dataType: "json",
      data: JSON.stringify(data),
    }).fail(function(err){
      alert("Ajax failed with: " + JSON.stringify(err));
    });
  }

  exports.markManualCase = function(run, caseName, status){
    run = run || run_id;
    return _manualCaseAPI("PUT", caseName, {
      result: status
    });
  };

  exports.deleteManualCase = function(run, caseName){
    run = run || run_id;
    return _manualCaseAPI("DELETE", caseName);
  };
}));
