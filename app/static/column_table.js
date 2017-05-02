/* A simple datatable for presenting any db */
var htmlify = require('./lib/htmlify.js');
var _p = require("./lib/sharedParameters.js");
var columns = _p.get("templateColumns").map(col => ({
  "render": htmlify,
  "data": column
}));

$('#column_table').dataTable( {
  columns: columns,
  ajax: {
    url: _p.get("ajaxURL"),
    dataSrc: ''
  },
});
