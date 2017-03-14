var dashboard = require("../lib/dashboard.js");
var colorize = require("../lib/colorize.js");
var htmlify = require('../lib/htmlify.js');

export default {
  props: ['dtData', 'runID'],
  data(){
    return {
      logContentHTML: "Loading...",
    };
  },
  methods: {
    refreshResult(){
      dashboard.refreshAutoCase(d.case).done(function(data){
        dashboard.autoCaseAPI("GET", this.runID, d.case).done(function(data){
          row.data(data).draw();
        });
      });
    },
    deleteResult(){
      dashboard.autoCaseAPI("DELETE", this.runID, d.case).done(function(data){
        table
          .row(tr)
          .remove()
          .draw();
      });
    },
    ignoreResult(){
      dashboard.autoCaseAPI("PUT", this.runID, d.case, {result: "skipped"}).done(function(data){
        row.data(data);
        row.draw();
      });
    },
  },

  computed: {
    noError(){
      return !!this.dtData.linkage_result;
    }
  },

  watch: { },

  delimiters: ['${', '}'],

  created(){
    let d = this.dtData;
    let vm = this;
    //Load Detail
    $.get("/api/run/" + this.runID + "/auto/" + d.case + "/")
      .done(function(data){
        vm.logContentHTML = `<p>Test Output: ${colorize(htmlify(data.output))}</p>
          <p> Test Failure Message: ${colorize(htmlify(data.failure))}</p>
          <p> Test Skip Message : ${colorize(htmlify(data.skip))}</p>`;
      })
      .fail(function(err){
        vm.logContentHTML = `<p> <strong> Failed to Load Result detail! </strong> </p>`;
      });
  },
};
