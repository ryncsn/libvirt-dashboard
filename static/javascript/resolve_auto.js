require('./lib/datatables-templates.js')
var htmlify = require("./lib/htmlify.js")
var colorize = require("./lib/colorize.js")
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
  return $.ajax("/api/run/" + run_id + "/auto/" + case_name + "/" , {
    contentType: "application/json; charset=utf-8",
    method: method,
    dataType: "json",
    data: JSON.stringify(data),
  }).fail(function(err){
    alert("Ajax failed with: " + JSON.stringify(err));
  })
}

function skip_case(case_name){
  return _ajax_call("PUT", case_name, {
    linkage_result: "ignored"
  })
}

function refresh_case(case_name, error, result){
  if(error){
    error = 'true';
  }
  if(result){
    result = 'true';
  }
  return $.ajax("/trigger/run/" + run_id + "/auto/" + case_name + "/refresh?error=" + error + "&result=" + result , {
    method: 'GET',
  }).fail(function(err){
    alert("Ajax failed with: " + JSON.stringify(err));
  })
}

function delete_case(case_name){
  return _ajax_call("DELETE", case_name, {
  })
}

$(document).ready(function() {
  var table = $('#column_table').DataSearchTable({
    BaseTable: [$.fn.DataTableWithChildRow, $.fn.DataTableWithInlineButton],
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
          })
        }
      },
      'selectNone',
      {
        text: 'Refresh',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            refresh_case(d.case, true, false).done(function(data){
              _ajax_call("GET", d.case).done(function(data){
                row.data(data).draw();
              });
            });
          })
        },
        className: 'btn-success',
        titleAttr: 'Refresh selected test results, Libvirt-Dashboard will lookup in Caselink, override test results\' "error" column.',
      },
      {
        text: 'Ignore',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            skip_case(d.case).done(function(data){
              row.data(data);
              row.draw();
            });
          })
        },
        className: 'btn-warning',
        titleAttr: 'Ignore selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
      },
      {
        text: 'Reset',
        action: function ( e, dt, node, config ) {
          table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
            var row = this;
            var d = this.data();
            refresh_case(d.case, true, true).done(function(data){
              _ajax_call("GET", d.case).done(function(data){
                row.data(data).draw();
              });
            });
          })
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
            delete_case(d.case).done(function(data){
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
      if(!data.linkage_result){
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
      var d = row.data();
      var head = error_panel.clone();
      if(d.linkage_result){
        head.find('.detail-operatoins').remove();
        head.prepend('<div class="alert alert-success" role="alert">Nothing to process</div>');
      }

      //Add button event
      $(head).find("button").on('click', function(event){
        if($(event.target).hasClass('btn-ignore')){
          skip_case(d.case).done(function(data){
            row.data(data);
            row.draw();
          });
        }
        else if($(event.target).hasClass('btn-refresh')){
          refresh_case(d.case).done(function(data){
            _ajax_call("GET", d.case).done(function(data){
              row.data(data).draw();
            });
          });
        }
        else if($(event.target).hasClass('btn-delete')){
          delete_case(d.case).done(function(data){
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
            .append("<p> Test Skip Message : "+ colorize(htmlify(data.skip)) +"</p>")
        })
        .fail(function(err){
          $('code.detail-well', head)
            .append("<p> <strong> Failed to Load Result detail! </strong> </p>")
        })
        .always(function(){
          child.append(head)
          finish()
        });
    },
  });
});

