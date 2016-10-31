require("../css/dashboard.css");
var TestRunStackGraph = require("./lib/test-run-stack-graph.js");
var graph = new TestRunStackGraph('.d3');
function updateKeys(){
  var selected = [];
  return $('input:checked[name="showing"]').each(function() {
    selected.push($(this).val());
  }).promise().done(function(){
    graph.changeKeys(selected);
  });
}
$('[name="showing"]').change(function(){
  updateKeys();
});
updateKeys();
$.ajax(window.templateStatisticURL)
  .done(function(data){
    var selector = $('[name="test_run"]');
    for (var key in data){
      selector.append("<option value=\"" + key + "\">"+ key +"</option>");
    }
    selector.change(function(){
      graph.updateData(this.value);
    });
  });
