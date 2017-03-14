var dtMixins = require('datatables-mixins');
var htmlify = require("./lib/htmlify.js");
var colorize = require("./lib/colorize.js");
var dashboard = require("./lib/dashboard.js");
var _p = require("./lib/sharedParameters.js");

var columns = [];

var autoresultView = require("./component/autoresult-view.vue");

var Vue = require("vue");

for (var columnSrc of _p.get("templateColumns")){
  columns.push({
    "render": htmlify,
    "data": columnSrc
  });
}

var autoresultView = Vue.extend(autoresultView);

var vm = new Vue({
  el: "#autoresult-resolving",
  data: {
    runID: null,
  },
  methods: {
    setRowResult(row, result){
      let d = row.data();
      dashboard.autoCaseAPI("PUT", this.runID, d.case, {result: result}).done(function(data){
        row.data(data);
        row.draw();
      });
    }
  },
  mounted(){
    this.runID = window.location.pathname.match("\/run\/([0-9]*)")[1];
    var table = $('#autoresult-table').DataSearchTable({
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
            table.rows({ selected: true }).every(() => vm.setRowResult(this, 'ignored'));
          },
          className: 'btn-warning',
          titleAttr: 'Ignore selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
        },
        {
          text: 'Pass',
          action: function ( e, dt, node, config ) {
            table.rows({ selected: true }).every(() => vm.setRowResult(this, 'passed'));
          },
          className: 'btn-warning',
          titleAttr: 'Pass selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
        },
        {
          text: 'Fail',
          action: function ( e, dt, node, config ) {
            table.rows({ selected: true }).every(() => vm.setRowResult(this, 'failed'));
          },
          className: 'btn-warning',
          titleAttr: 'Fail selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
        },
        {
          text: 'Refresh',
          action: function ( e, dt, node, config ) {
            table.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
              var row = this, d = this.data();
              dashboard.refreshAutoCase(this.runID, d.case).done(function(data){
                dashboard.autoCaseAPI("GET", this.runID, d.case).done(function(data){
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
              var row = this, d = this.data();
              dashboard.autoCaseAPI("DELETE", this.runID, d.case).done(function(data){
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
      ajax: {
        url: _p.get("ajaxURL"),
        dataSrc: ''
      },
      rowCallback(row, data, index){
        if(data.result != 'passed'){
          $(row).addClass('error');
        }
        else{
          $(row).removeClass('error');
        }
      },
      childContent(row, child, slideDown, slideUp){
        var childVm = new autoresultView({
          el: child.get(0),
          parent: vm,
          propsData: {
            dtData: row.data(),
            runID: vm.runID,
          },
          mounted() {
            slideDown();
          },
        });
      },
    });
  }
});

