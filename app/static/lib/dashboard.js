(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define(['exports', 'jquery'], factory);
  } else if (typeof exports === 'object' && typeof exports.nodeName !== 'string') {
    factory(exports, require('jquery'));
  } else {
    factory((root.commonJsStrict = {}), root.$);
  }
}(this, function (exports, $) {
  function _API(method, url, data){
    return $.ajax(url, {
      contentType: "application/json; charset=utf-8",
      method: method,
      dataType: "json",
      data: JSON.stringify(data || {}),
    }).fail(function(err){
      alert("Ajax failed with: " + JSON.stringify(err));
    });
  }

  function _Trigger(method, url, data){
    return $.ajax(url, {
      contentType: "application/json; charset=utf-8",
      method: method,
      dataType: "json",
      data: JSON.stringify(data || {}),
    }).fail(function(err){
      alert("Ajax failed with: " + JSON.stringify(err));
    }).done(function(data){
      let text = "";
      if(data.message){
        text += "Message: " + data.message + "\n";
      }
      if(data.error){
        text += "Error: " + data.error + "\n";
      }
      alert(text);
    });
  }

  function _manualCaseAPI(method, run, caseName, data){
    return _API(method, "/api/run/" + run + "/manual/" + (caseName ? caseName + "/" : ""), data);
  }

  function _autoCaseAPI(method, run, caseName, data){
    return _API(method, "/api/run/" + run + "/auto/" + (caseName ? caseName + "/" : ""), data);
  }

  function _testRunAPI(method, run, data){
    return _API(method, "/api/run/" + run + "/", data);
  }

  function _tagAPI(method, run, tagName, data){
    return _API(method, "/api/run/" + run + "/manual/" + (caseName ? caseName + "/" : ""), data);
  }

  exports.autoCaseAPI = _autoCaseAPI;
  exports.manualCaseAPI = _manualCaseAPI;
  exports.tagAPI = _tagAPI;

  exports.refreshAutoCase = function(run, caseName){
    return _Trigger("GET", "/trigger/run/" + run + "/auto/" + caseName + "/refresh");
  };

  exports.regenerateManual = function(run){
    return _Trigger("GET", "/trigger/run/" + run + "/refresh" );
  };

  exports.submitTestRun = function(run, forced){
    return _Trigger("GET", "/trigger/run/" + run + "/submit" + (forced ? "?forced=true" : ""))
      .done(function(data){
        if (data.submitted && data.not_submitted){
          alert(
            'Successfully submitted: ' + JSON.stringify(data.submitted) + '.' +
            'Failed to submit: ' + JSON.stringify(data.not_submitted) + '.'
          );
          if (data.error.length !== 0){
            if (confirm("Some Test run failed to submit, would you like to issue a forced submit?")){
              exports.submitTestRun(run, true);
            }
          }
        }
      });
  };

}));
