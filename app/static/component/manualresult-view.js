var dashboard = require("../lib/dashboard.js");

export default {
  props: ['dtData', 'runId'],
  methods: {
    failResult(){
      let vm = this;
      dashboard.manualCaseAPI("PUT", this.runId, this.dtData.case, {result: "failed"}).done(function(data){
        //TODO
      });
    },
    passResult(){
      let vm = this;
      dashboard.manualCaseAPI("PUT", this.runId, this.dtData.case, {result: "passed"}).done(function(data){
        //TODO
      });
    },
    deleteResult(){
      let vm = this;
      dashboard.manualCaseAPI("DELETE", this.runId, this.dtData.case).done(function(data){
        //TODO
      });
    },
  },
  computed: {
    noError(){
      return this.dtData.result != "incomplete";
    }
  },
};
