var dtMixins = require('datatables-mixins');
var htmlify = require('./lib/htmlify.js');
var _p = require("./lib/sharedParameters.js");
var columns = [];

for (var columnSrc of _p.get("templateColumns")){
  columns.push({
    "render": htmlify,
    "data": columnSrc
  });
}


$(document).ready(function() {
  $('#column_table').dataTable( {
    pageLength: 50,
    columns: columns,
    ajax: {
      url: _p.get("ajaxURL"),
      dataSrc: ''
    },
  });
});
