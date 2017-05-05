require("./css/testrun-overview.css");
var dtMixins = require('datatables-mixins');
var htmlify = require("./lib/htmlify.js");
var Cookies = require('js-cookie');
var Vue = require("vue");
var _p = require("./lib/sharedParameters.js");

var dashboard = require("./lib/dashboard.js");

var vm = new Vue({
  el: "#testrun-overview",
  delimiters: ['${', '}'],
  data: {
    availTags: [],
    checkedTags: [],
    submitStatus: 'all',
    containsAutocase: '',
    containsManualcase: '',
    showSearchPanel: false,
    dtTable: null,
  },
  methods: {
    reloadTable: function(){
      if(!this.dtTable){
        return;
      }
      this.dtTable.ajax.reload();
      this.dtTable.draw();
    }
  },
  created: function(){
    window.fetch("/api/tag")
      .then(data => data.json().then(tags => this.availTags = tags))
      .catch(err => null); //TODO
    this.checkedTags = JSON.parse(Cookies.get('checkedTags') || "[]");
  },
  watch: {
    checkedTags: function(){
      Cookies.set('checkedTags', JSON.stringify(this.checkedTags));
      this.reloadTable();
    },
    submitStatus: function() {this.reloadTable();},
    containsAutocase: function() {this.reloadTable();},
    containsManualcase: function() {this.reloadTable();},
  },
  mounted: function(){
    let vm = this;
    var table = this.dtTable = $('#column_table').DataTableWithChildRow({
      BaseTable: [dtMixins.DataTableJumpPageButton],
      processing: true,
      serverSide: true,
      ajax: {
        url: _p.get("datatablesAPIURL"),
        data: function(d) {
          d.hasTags = JSON.stringify(vm.checkedTags);
          d.submitStatus = vm.submitStatus;
          d.containsAutocase = vm.containsAutocase;
          d.containsManualcase = vm.containsManualcase;
        }
      },
      dom: '<t><"row"<"col-md-3"f><"col-md-4"i><"col-md-5"p>>',
      pageLength: 100,
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
          "data":"submit_status",
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
        {
          "data":'submit_task',
          visible: false
        },

      ],
      order: [[1, 'desc']],
      childContent: function(row, child, slideDown){
        var childVm = new TestRunChildRow({
          el: child.get(0),
          parent: vm,
          propsData: {
            testRun: row.data()
          },
          mounted: function(){
            slideDown();
          },
        });
      }
    });
  }
});

var TestRunChildRow = Vue.extend({
  template: "#testrun-child-row",
  delimiters: ['${', '}'],
  props: [ 'testRun' ],
  methods: {
    submitTestRun: function(){
      dashboard.submitTestRun(this.testRun.id);
    },
    deleteTestRun: function(){
      let r = confirm("Delete this test run and all related autotest/manual results?");
      if (r === true){
        $.ajax("/api/run/" + this.testRun.id + "/", {
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
    }
  },
  data: function() {
    return {};
  },
  computed: {
    polarionUrl: function() {return `${_p.get('polarionURL')}/#/project/RedHatEnterpriseLinux7/testrun?id=${this.testRun.polarion_id}`;},
    manualResolveUrl: function()  {return `/resolve/run/${this.testRun.id}/manual/`;},
    manualTableUrl:function() {return `/table/run/${this.testRun.id}/manual/`;},
    manualApi: function(){return `/api/run/${this.testRun.id}/manual/`;},
    manualSummary: function() {return `${this.testRun.manual_error} errors, ${this.testRun.manual_passed} passed, ${this.testRun.manual_failed} failed`;},
    autoResolveUrl: function()  {return `/resolve/run/${this.testRun.id}/auto/`;},
    autoTableUrl:function() {return `/table/run/${this.testRun.id}/auto/`;},
    autoApi: function(){return `/api/run/${this.testRun.id}/auto/`;},
    autoSummary: function() {return `${this.testRun.auto_error} errors, ${this.testRun.auto_passed} passed, ${this.testRun.auto_failed} failed, ${this.testRun.auto_missing} missing`;},
  },
});
