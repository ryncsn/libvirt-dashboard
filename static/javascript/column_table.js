require('./lib/datatables-templates.js')
var htmlify = require('./lib/htmlify.js')
var columns = []
var columnSrcs = window.templateColumns;
for (var columnSrc of columnSrcs){
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
      url: window.ajaxURL,
      dataSrc: ''
    },
  });
});
