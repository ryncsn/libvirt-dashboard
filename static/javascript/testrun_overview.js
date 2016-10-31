require("../css/testrun-overview.css");
require('./lib/datatables-templates.js');
var htmlify = require("./lib/htmlify.js");
var child_panel = $("#_proto_child").removeClass('hidden').detach();
$(document).ready(function() {
  var table = $('#column_table').DataTableWithChildRow({
    pageLength: 100,
    dom: '<t><"row"<"col-md-3"f><"col-md-4"i><"col-md-5"p>>',
    columns: [
      {
        "data": function(row){
          var html = row.name;
          row.tags.sort();
          for (var i = 0, len = row.tags.length; i < len; i++){
            var tag = row.tags[i];
            html += "<span class=\"label label-info\" style=\"margin-left: 10px;\">" + tag + "</span>";
          }
          return html;
        }
      },
      {
        "data":"date",
        "render": htmlify
      },
      {
        "data":"submit_date",
        "render": htmlify
      },
      {
        "data":function(row){
          var total = row.auto_passed + row.auto_failed + row.auto_skipped;
          if (total === 0){
            return "N/a";
          }
          return row.auto_passed + " / " + (total);
        },
      },
      {
        "data":function(row){
          var total = row.auto_passed + row.auto_failed + row.auto_skipped;
          if (total === 0){
            return "N/a";
          }
          return (total - row.auto_error) + " / " + (total);
        },
      },
      {
        "data":function(row){
          if (row.manual_failed + row.manual_passed === 0){
            return "N/a";
          }
          return row.manual_passed + " / " + (row.manual_failed + row.manual_passed + row.manual_error);
        },
      },

    ],
    order: [[2, 'desc']],
    rowCallback: function(row, data, index){
    },
    ajax: {
      url: window.templateTestRunListAPIUrl,
      dataSrc: ''
    },

    childContent: function(row, child, finish){
      var d = row.data();
      // Open this row
      var head = child_panel.clone();
      //Add button event
      $(head).find(".dashboard-submit").click(function(){
        $.ajax("/trigger/run/" + d.id + "/submit", {
          method: "GET",
        }).fail(function(err){
          alert("Ajax failed with: " + JSON.stringify(err));
        }).done(function(data){
          if(data.submitted && data.submitted.length > 0){
            alert('Submitted test runs: ' + data.submitted.join("<br>"));
          }
          else if(data.message){
            alert(data.message);
          }
          else if(data.error.length !== 0){
            alert('Not submitted, maybe it\'s submitted already, or please check for errors for both auto results and manual result of this test run then try again.');
          }
        });
      });
      $(head).find(".dashboard-delete").click(function(){
        var r = confirm("Delete this test run and all related autotest/manual results?");
        if (r === true){
          $.ajax("/api/run/" + d.id + "/", {
            method: "DELETE",
          }).fail(function(err){
            alert("Ajax failed with: " + JSON.stringify(err));
          }).done(function(data){
            alert('Test Run deleted.');
            table
              .row(row)
              .remove()
              .draw();
          });
        }
      });

      if(d.submit_date){
        $(head).find(".dashboard-submit").attr('disabled', true);
        $(head).find(".dashboard-jump").attr('href', 'https://polarion.engineering.redhat.com/polarion/#/project/RedHatEnterpriseLinux7/testrun?id=' + d.polarion_id);
      }
      else{
        $(head).find(".dashboard-jump").attr('disabled', true);
      }

      $(head).find(".dropdown-manual .dashboard-resolve").attr('href', '/resolve/run/' + d.id + '/manual/');
      $(head).find(".dropdown-manual .dashboard-table").attr('href', '/table/run/' + d.id + '/manual/');
      $(head).find(".dropdown-manual .dashboard-api").attr('href', '/api/run/' + d.id + '/manual/');
      $(head).find(".dashboard-info-manual").text(d.manual_error + ' errors to resolve, ' + d.manual_passed + ' passed, ' + d.manual_failed + ' failed');
      if(d.manual_error){
        $(head).find(".dashboard-info-manual").addClass("label-danger");
      }
      else{
        $(head).find(".dashboard-info-manual").addClass("label-info").append(' ,Cleared!');
      }

      $(head).find(".dropdown-auto .dashboard-resolve").attr('href', '/resolve/run/' + d.id + '/auto/');
      $(head).find(".dropdown-auto .dashboard-table").attr('href', '/table/run/' + d.id + '/auto/');
      $(head).find(".dropdown-auto .dashboard-api").attr('href', '/api/run/' + d.id + '/auto/');
      $(head).find(".dashboard-info-auto").text(d.auto_error + ' errors to resolve, ' + d.auto_passed + ' passed, ' + d.auto_failed + ' failed');
      if(d.auto_error){
        $(head).find(".dashboard-info-auto").addClass("label-danger");
      }
      else{
        $(head).find(".dashboard-info-auto").addClass("label-info").append(' ,Cleared!');
      }
      child.append(head);
      finish();
    }
  });
});

