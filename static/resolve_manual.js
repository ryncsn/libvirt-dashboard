var dtMixins = require('datatables-mixins');
var dashboard = require("./lib/dashboard.js");
var htmlify = require("./lib/htmlify.js");
var _p = require("./lib/sharedParameters.js");
var error_panel = $("#_proto_error_panel").removeClass('hidden').detach();
var run_id = window.location.pathname.match("\/run\/([0-9]*)")[1];
var columns = [];

for (var columnSrc of _p.get("templateColumns")){
  columns.push({
    "render": htmlify,
    "data": columnSrc
  });
}

$(document).ready(function() {
  var table = $('#column_table').DataSearchTable({
    pageLength: 50,
    "iDisplayLength": 20,
    "bAutoWidth": false,
    BaseTable: [dtMixins.DataTableWithChildRow, dtMixins.DataTableWithInlineButton, dtMixins.DataTableJumpPageButton],
    buttons: [
      {
        text: 'Select All Shown',
        action: function ( e, dt, node, config ) {
          var filterSet = table.$('tr', {filter:'applied'});
          filterSet.each(function(){
            table.row(this).select();
          });
        }
      },
      'selectNone',
      {
        text: 'Mark Pass',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.manualCaseAPI("PUT", run_id, d.case, {result: "passed"}).done(function(data){
              row
                .data(data)
                .draw();
            });
          });
        },
        className: 'btn-warning',
        titleAttr: 'Mark selected manual test result as passed.'
      },
      {
        text: 'Makr Fail',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.manualCaseAPI("PUT", run_id, d.case, {result: "failed"}).done(function(data){
              row
                .data(data)
                .draw();
            });
          });
        },
        className: 'btn-warning',
        titleAttr: 'Mark selected manual test result as failed.'
      },
      {
        text: 'Delete',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.manualCaseAPI("DELETE", run_id, d.case).done(function(data){
              table
                .row(row)
                .remove()
                .draw();
            });
          });
        },
        className: 'btn-danger',
        titleAttr: 'Delete selected test results, to recovery deleted manual test result, you have to regenerate all manual test cases.'
      },
      {
        text: 'Regenerate',
        action: function ( e, dt, node, config ) {
          dashboard.regenerateManual(run_id)
            .done(function(data){
              window.location.reload(false);
            });
        },
        className: 'btn-info',
        titleAttr: 'Regenerate all Manual test result according to auto test results and linkage on Caselink. (slow, page will be refreshed after finished)'
      },
      {
        text: 'Submit to Polarion',
        action: function ( e, dt, node, config ) {
          dashboard.submitTestRun(run_id, false);
        },
        className: 'btn-success',
      },
    ],
    select: true,
    selectorColumns: [
      {
        column:"result",
        render: htmlify
      },
    ],
    columns: columns,
    rowCallback: function(row, data, index){
      if(data.result == 'incomplete'){
        $(row).addClass('error');
      }
      else{
        $(row).removeClass('error');
      }
    },
    ajax: {
      url: _p.get("ajaxURL"),
      dataSrc: ''
    },

    childContent: function(row, child, finish){
      var d = row.data();
      // Open this row
      var head = error_panel.clone();
      //Add button event
      $(head).find("button").on('click', function(event){
        if($(event.target).hasClass('btn-mark-fail')){
          dashboard.manualCaseAPI("PUT", run_id, d.case, {result: "failed"}).done(function(data){
            row.data(data);
            row.draw();
          });
        }
        else if($(event.target).hasClass('btn-mark-pass')){
          dashboard.manualCaseAPI("PUT", run_id, d.case, {result: "passed"}).done(function(data){
            row.data(data);
            row.draw();
          });
        }
        else if($(event.target).hasClass('btn-delete')){
          dashboard.manualCaseAPI("DELETE", run_id, d.case).done(function(data){
            table
              .row(tr)
              .remove()
              .draw();
          });
        }
      });
      child.append(head);
      finish();
    }
  });
});

