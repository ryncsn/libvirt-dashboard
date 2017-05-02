const dashboard = require("../lib/dashboard.js");
const colorize = require("../lib/colorize.js");
const htmlify = require("../lib/htmlify.js");
const _ = require("lodash");
const Vue = require('vue');
const dtMixins = require("datatables-mixins");

const manuaresultView = Vue.extend(require("./manualresult-view.vue"));

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
        vm.dtTable.$('tr', { filter:'applied' }).each(function(){
          table.row(this).select();
        });
      }
    },
    {
      text: 'Mark Pass',
      className: 'btn-warning',
      titleAttr: 'Mark selected manual test result as passed.',
      action() {
        vm.dtTable.rows( { selected: true } ).every(function(){
          setRowResult(this, "passed");
        });
      },
    },
    {
      text: 'Makr Fail',
      className: 'btn-warning',
      titleAttr: 'Mark selected manual test result as failed.',
      action() {
        table.rows( { selected: true } ).every(function(){
          setRowResult(this, "failed");
        });
      },
    },
    {
      text: 'Delete',
      className: 'btn-danger',
      titleAttr: 'Delete selected test results, to recovery deleted manual test result, you have to regenerate all manual test cases.',
      action() {
        table.rows( { selected: true } ).every(function(){
          var row = this, d = this.data();
          dashboard.manualCaseAPI("DELETE", run_id, d.case)
            .done((data) => vm.dtTable.row(row).remove().draw());
        });
      },

    },
    {
      text: 'Regenerate',
      className: 'btn-info',
      titleAttr: 'Regenerate all Manual test result according to auto test results and linkage on Caselink. (slow, page will be refreshed after finished)',
      action() {
        dashboard.regenerateManual(run_id)
          .done((data) => window.location.reload(false));
      },
    },
    {
      text: 'Submit to Polarion',
      className: 'btn-success',
      action() {
        dashboard.submitTestRun(run_id, false);
      },
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
      dashboard.manualCaseAPI("PUT", this.runId, d.case, {result: result})
        .done((data) => row.data(data).draw());
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
        var childVm = new manualresultView({
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
