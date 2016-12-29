var dtMixins = require('datatables-mixins');
var htmlify = require("./lib/htmlify.js");
var colorize = require("./lib/colorize.js");
var error_panel = $("#_proto_error_panel").removeClass('hidden').detach();
var dashboard = require("./lib/dashboard.js");
var _p = require("./lib/sharedParameters.js");

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
    BaseTable: [dtMixins.DataTableWithChildRow, dtMixins.DataTableWithInlineButton, dtMixins.DataTableJumpPageButton],
    pageLength: 50,
    "iDisplayLength": 20,
    "bAutoWidth": false,
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
        text: 'Ignore',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.autoCaseAPI("PUT", run_id, d.case, {result: "ignored"}).done(function(data){
              row.data(data);
              row.draw();
            });
          });
        },
        className: 'btn-warning',
        titleAttr: 'Ignore selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
      },
      {
        text: 'Pass',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.autoCaseAPI("PUT", run_id, d.case, {result: "passed"}).done(function(data){
              row.data(data);
              row.draw();
            });
          });
        },
        className: 'btn-warning',
        titleAttr: 'Pass selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
      },
      {
        text: 'Fail',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.autoCaseAPI("PUT", run_id, d.case, {result: "failed"}).done(function(data){
              row.data(data);
              row.draw();
            });
          });
        },
        className: 'btn-warning',
        titleAttr: 'Fail selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
      },
      {
        text: 'Refresh',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this, d = this.data();
            dashboard.refreshAutoCase(run_id, d.case).done(function(data){
              dashboard.autoCaseAPI("GET", run_id, d.case).done(function(data){
                row.data(data).draw();
              });
            });
          });
        },
        className: 'btn-warning',
        titleAttr: 'Reset selected test results, Libvirt-Dashboard will lookup in Caselink, override test results\' "error" and "result" column.',
      },
      {
        text: 'Delete',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            dashboard.autoCaseAPI("DELETE", run_id, d.case).done(function(data){
              table
                .row(idx)
                .remove()
                .draw();
            });
          });
        },
        className: 'btn-danger',
        titleAttr: 'Delete selected test results, can\'t recovery once deleted.'
      },
    ],
    select: true,
    selectorColumns: [
      {
        column:"error",
        render: htmlify
      },
      {
        column:"result",
        render: htmlify
      },
      {
        column:"linkage_result",
        render: htmlify
      },

    ],
    columns: columns,
    rowCallback: function(row, data, index){
      if(data.result != 'passed'){
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
      var head = error_panel.clone();
      if(d.linkage_result){
        head.find('.detail-operatoins').remove();
        head.prepend('<div class="alert alert-success" role="alert">Nothing to process</div>');
      }

      //Add button event
      $(head).find("button").on('click', function(event){
        if($(event.target).hasClass('btn-ignore')){
          dashboard.autoCaseAPI("PUT", run_id, d.case, {result: "skipped"}).done(function(data){
            row.data(data);
            row.draw();
          });
        }
        else if($(event.target).hasClass('btn-refresh')){
          dashboard.refreshAutoCase(d.case).done(function(data){
            dashboard.autoCaseAPI("GET", run_id, d.case).done(function(data){
              row.data(data).draw();
            });
          });
        }
        else if($(event.target).hasClass('btn-delete')){
          dashboard.autoCaseAPI("DELETE", run_id, d.case).done(function(data){
            table
              .row(tr)
              .remove()
              .draw();
          });
        }
      });

      //Load Detail
      $.get("/api/run/" + run_id + "/auto/" + d.case + "/")
        .done(function(data){
          $('code.detail-well', head)
            .append("<p> Test Output: "+ colorize(htmlify(data.output)) +"</p>")
            .append("<p> Test Failure Message: " + colorize(htmlify(data.failure)) +"</p>")
            .append("<p> Test Skip Message : "+ colorize(htmlify(data.skip)) +"</p>");
        })
        .fail(function(err){
          $('code.detail-well', head)
            .append("<p> <strong> Failed to Load Result detail! </strong> </p>");
        })
        .always(function(){
          child.append(head);
          finish();
        });
    },
  });
});

