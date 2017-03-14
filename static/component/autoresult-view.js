var dashboard = require("../lib/dashboard.js");
var colorize = require("../lib/colorize.js");
var htmlify = require("../lib/htmlify.js");

export default {
  props: ['dtData', 'runId'],
  data(){
    return {
      logContentHTML: "Loading...",
    };
  },
  methods: {
    refreshResult(){
      let vm = this;
      dashboard.refreshAutoCase(d.case).done(function(data){
        dashboard.autoCaseAPI("GET", this.runId, this.dtData.case).done(vm.refreshData);
      });
    },
    deleteResult(){
      let vm = this;
      dashboard.autoCaseAPI("DELETE", this.runId, this.dtData.case).done(vm.refreshData);
    },
    ignoreResult(){
      let vm = this;
      dashboard.autoCaseAPI("PUT", this.runId, this.dtData.case, {result: "skipped"}).done(vm.refreshData);
    },
    refreshData(){
      let vm = this;
      $.get("/api/run/" + this.runId + "/auto/" + this.dtData.case + "/")
        .done(function(data){
          vm.logContentHTML = `<p>Test Output: ${colorize(htmlify(data.output))}</p>
          <p> Test Failure Message: ${colorize(htmlify(data.failure))}</p>
          <p> Test Skip Message : ${colorize(htmlify(data.skip))}</p>`;
        })
        .fail(function(err){
          vm.logContentHTML = `<p> <strong> Failed to Load Result detail! </strong> </p>`;
        });
    }
  },
  computed: {
    noError(){
      return !!this.dtData.linkage_result;
    }
  },

  created(){
    this.refreshData();
  },
};
