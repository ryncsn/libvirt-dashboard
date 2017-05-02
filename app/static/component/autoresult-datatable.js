const dashboard = require("../lib/dashboard.js");
const colorize = require("../lib/colorize.js");
const htmlify = require("../lib/htmlify.js");
const _ = require("lodash");
const Vue = require('vue');
const dtMixins = require("datatables-mixins");

const autoresultView = Vue.extend(require("./autoresult-view.vue"));

const dtColumns = {
  "case": "Case",
  "time": "Time",
  "result": "Test Result",
  "comment": "Comment"
};

const dtSelectorColumns = [
  { column:"result", render: htmlify },
];

const dtButtons = function () {
  let vm = this;
  return [
    'selectNone',
    {
      text: 'Select All Shown',
      action() {
        vm.dtTable.$('tr', {filter:'applied'}).each(function(){ table.row(this).select(); });
      }
    },
    {
      text: 'Ignore',
      action() {
        vm.dtTable.rows({ selected: true }).every(function(){ vm.setRowResult(this, 'ignored'); });
      },
      className: 'btn-warning',
      titleAttr: 'Ignore selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
    },
    {
      text: 'Pass',
      action() {
        vm.dtTable.rows({ selected: true }).every(function(){ vm.setRowResult(this, 'passed'); });
      },
      className: 'btn-warning',
      titleAttr: 'Pass selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
    },
    {
      text: 'Fail',
      action() {
        vm.dtTable.rows({ selected: true }).every(function(){ vm.setRowResult(this, 'failed'); });
      },
      className: 'btn-warning',
      titleAttr: 'Fail selected test results, set test\'s result to ignored and no longer consider this case as a failure bloking polarion submition anymore.',
    },
    {
      text: 'Refresh',
      action() {
        vm.dtTable.rows( { selected: true } ).every(function(idx, tableLoop, rowLoop){
          var row = this, d = this.data();
          dashboard.refreshAutoCase(this.runId, d.case).done(function(data){
            dashboard.autoCaseAPI("GET", this.runId, d.case).done(function(data){
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
          dashboard.autoCaseAPI("DELETE", this.runId, d.case).done(function(data){
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
  ];
};

export default {
  props: ["dtAjaxUrl", "runId"],
  data(){
    return { };
  },
  computed: {
    dtColumnKeys(){
      return _.keys(dtColumns);
    },
    dtColumnNames(){
      return _.values(dtColumns);
    },
    dtColumns() {
      return this.dtColumnKeys.map(key => ({
        "data": key,
        "render":htmlify,
      }));
    },
  },

  methods: {
    setRowResult(row, result){
      let d = row.data();
      dashboard.autoCaseAPI("PUT", this.runId, d.case, {result: result}).done(function(data){
        row.data(data);
        row.draw();
      });
    }
  },

  created(){
  },

  mounted(){
    let vm = this;
    var table = $('#result-table').DataSearchTable({
      BaseTable: [dtMixins.DataTableWithChildRow, dtMixins.DataTableWithInlineButton, dtMixins.DataTableJumpPageButton],
      iDisplayLength: 20,
      bAutoWidth: false,
      select: true,
      selectorColumns: dtSelectorColumns,
      columns: vm.dtColumns,
      buttons: dtButtons.call(vm),
      ajax: {
        url: vm.dtAjaxUrl,
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
            runId: vm.runId,
          },
          mounted() {
            slideDown();
          },
        });
      },
    });
  },
};
