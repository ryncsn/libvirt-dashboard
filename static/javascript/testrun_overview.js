require("../css/testrun-overview.css");
var dtMixins = require('datatables-mixins');
var htmlify = require("./lib/htmlify.js");
var Cookies = require('js-cookie');
var Vue = require("vue");

var dashboard = require("./lib/dashboard.js");
var child_panel = $("#_proto_child").removeClass('hidden').detach();

var vm = new Vue({
  el: "#testrun-overview",
  data: {
    availTags: [],
    checkedTags: [],
    containAuto: '',
    containManual: '',
    showSearchPanel: false,
    dtTable: {}
  },
  methods: {
    applyTags: function(tags){
      this.dtTable.tagsColumn.search(JSON.stringify(tags));
      this.dtTable.table.draw();
    },
    applyCase: function(auto, manual){
      this.dtTable.autoColumn.search(auto);
      this.dtTable.manualColumn.search(manual);
      this.dtTable.table.draw();
    },
    updateCaseSearch: function(){
      this.applyCase(this.containAuto, this.containManual);
    }
  },
  delimiters: ['${', '}'],
  created: function(){
    let that = this;
    $.get("/api/tag").done(function(data){
      that.availTags = data;
    });
    this.checkedTags = JSON.parse(Cookies.get('checkedTags') || "[]");
  },
  watch: {
    checkedTags: function(newTag){
      try {
        this.applyTags(this.checkedTags);
        Cookies.set('checkedTags', JSON.stringify(this.checkedTags));
      } catch (e) {
        console.log(e);
      }
    },
  },
  mounted: function(){
    let vm = this;
    var table = this.dtTable.table = $('#column_table').DataTableWithChildRow({
      ajax: window.templateDTAPIURL,
      dom: '<t><"row"<"col-md-3"f><"col-md-4"i><"col-md-5"p>>',
      pageLength: 100,
      processing: true,
      serverSide: true,
      "aoSearchCols": [
        null,
        null,
        null,
        null,
        null,
        null,
        { "sSearch": JSON.stringify(vm.checkedTags) },
      ],
      columns: [
        {
          "data": function(data){
            var html = data.name;
            data.tags.sort();
            for (let tag of data.tags){
              html += `<span class="label label-info" style="margin-left: 10px;">${tag}</span>`;
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
            var total = row.auto_passed + row.auto_failed + row.auto_skipped + row.auto_ignored + row.auto_error;
            return (total === 0) ? "N/a" : `${row.auto_passed} / ${total}`;
          },
        },
        {
          "data":function(row){
            var total = row.auto_passed + row.auto_failed + row.auto_skipped + row.auto_ignored + row.auto_error;
            return (total === 0) ? "N/a" : `${total - row.auto_nolinkage} / ${total}`;
          },
        },
        {
          "data":function(row){
            var total = row.manual_failed + row.manual_passed + row.manual_ignored + row.manual_skipped + row.manual_error;
            return (total === 0) ? "N/a" : `${row.manual_passed} / ${total}`;
          },
        },
        {
          "data":function(row){
            return row.tags.join(", ");
          },
          visible: false
        },
      ],
      order: [[1, 'desc']],
      rowCallback: function(row, data, index){},
      childContent: function(row, child, finish){
        var d = row.data(), head = child_panel.clone();
        $(head).find(".dashboard-submit").click(function(){
          dashboard.submitTestRun(d.id);
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
        $(head).find(".dashboard-info-manual").text(d.manual_error + ' errors, ' + d.manual_passed + ' passed, ' + d.manual_failed + ' failed');
        if(d.manual_error){
          $(head).find(".dashboard-info-manual").addClass("label-danger");
        }
        else{
          $(head).find(".dashboard-info-manual").addClass("label-info").append(' ,Cleared!');
        }

        $(head).find(".dropdown-auto .dashboard-resolve").attr('href', '/resolve/run/' + d.id + '/auto/');
        $(head).find(".dropdown-auto .dashboard-table").attr('href', '/table/run/' + d.id + '/auto/');
        $(head).find(".dropdown-auto .dashboard-api").attr('href', '/api/run/' + d.id + '/auto/');
        $(head).find(".dashboard-info-auto").text(d.auto_error + ' errors, ' + d.auto_passed + ' passed, ' + d.auto_failed + ' failed, ' + d.auto_missing + ' missing');
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
    this.dtTable.tagsColumn = table.column(function(idx, data, node){return $(node).text() == ("Tags");});
    this.dtTable.autoColumn = table.column(function(idx, data, node){return $(node).text() == ("Auto");});
    this.dtTable.manualColumn = table.column(function(idx, data, node){return $(node).text() == ("Manual");});
    console.log("funied");
  }
});
