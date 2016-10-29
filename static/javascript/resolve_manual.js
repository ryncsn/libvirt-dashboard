require('./lib/datatables-templates.js')
var htmlify = require("./lib/htmlify.js")
var error_panel = $("#_proto_error_panel").removeClass('hidden').detach()
var run_id = window.location.pathname.match("\/run\/([0-9]*)")[1]
var columns = []
var columnSrcs = window.templateColumns;
for (var columnSrc of columnSrcs){
  columns.push({
    "render": htmlify,
    "data": columnSrc
  });
}

function _ajax_call(method, case_name, data){
  return $.ajax("/api/run/" + run_id + "/manual/" + case_name + "/", {
    contentType: "application/json; charset=utf-8",
    method: method,
    dataType: "json",
    data: JSON.stringify(data),
  }).fail(function(err){
    alert("Ajax failed with: " + JSON.stringify(err));
  });
}

function mark_case_fail(case_name){
  return _ajax_call("PUT", case_name, {
    result: "failed"
  });
}

function mark_case_pass(case_name){
  return _ajax_call("PUT", case_name, {
    result: "passed"
  });
}

function delete_case(case_name){
  return _ajax_call("DELETE", case_name);
}

$(document).ready(function() {
  var table = $('#column_table').DataSearchTable({
    pageLength: 50,
    "iDisplayLength": 20,
    "bAutoWidth": false,
    BaseTable: [$.fn.DataTableWithChildRow, $.fn.DataTableWithInlineButton],
    buttons: [
      {
        text: 'Select All Shown',
        action: function ( e, dt, node, config ) {
          var filterSet = table.$('tr', {filter:'applied'});
          filterSet.each(function(){
            table.row(this).select();
          })
        }
      },
      'selectNone',
      {
        text: 'Mark Pass',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            mark_case_pass(d.case).done(function(data){
              row.data(data);
              row.draw();
            });
          })
        },
        className: 'btn-warning',
        titleAttr: 'Mark selected manual test result as passed.'
      },
      {
        text: 'Makr Fail',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            mark_case_fail(d.case).done(function(data){
              row.data(data);
              row.draw();
            });
          })
        },
        className: 'btn-warning',
        titleAttr: 'Mark selected manual test result as failed.'
      },
      {
        text: 'Delete',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            delete_case(d.case).done(function(data){
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
          $.ajax("/trigger/run/" + run_id + "/manual/refresh", {
            method: "GET",
          }).fail(function(err){
            alert("Ajax failed with: " + JSON.stringify(err));
          }).done(function(data){
            if(data.message == 'success'){
              window.location.reload(false);
            }
            else{
              alert("Failed with: " + JSON.stringify(data));
              window.location.reload(false);
            }
          });
        },
        className: 'btn-info',
        titleAttr: 'Regenerate all Manual test result according to auto test results and linkage on Caselink. (slow, page will be refreshed after finished)'
      },
      {
        text: 'Submit to Polarion',
        action: function ( e, dt, node, config ) {
          $.ajax("/trigger/run/" + run_id + "/submit", {
            method: "GET",
          }).fail(function(err){
            alert("Ajax failed with: " + JSON.stringify(err));
          }).done(function(data){
            if(data.submitted.length == 1){
              alert('Success!')
            }
            else if(data.error.length !== 0){
              alert('Not submitted, please check for errors for both auto results and manual result of this test run then try again.');
            }
          });
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
      url: window.ajaxURL,
      dataSrc: ''
    },

    childContent: function(row, child, finish){
      var d = row.data()
      // Open this row
      var head = error_panel.clone();
      //Add button event
      $(head).find("button").on('click', function(event){
        if($(event.target).hasClass('btn-mark-fail')){
          mark_case_fail(d.case).done(function(data){
            row.data(data);
            row.draw();
          });
        }
        else if($(event.target).hasClass('btn-mark-pass')){
          mark_case_pass(d.case).done(function(data){
            row.data(data);
            row.draw();
          });
        }
        else if($(event.target).hasClass('btn-delete')){
          delete_case(d.case). done(function(data){
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

