var dtMixins = require('datatables-mixins');
var htmlify = require("./lib/htmlify.js");
var Cookies = require('js-cookie');
var Vue = require("vue");
var _p = require("./lib/sharedParameters.js");
var _ = require("lodash");

var dashboard = require("./lib/dashboard.js");

var vm = new Vue({
  el: "#testrun-diff",
  delimiters: ['${', '}'],
  data: function() {
    return {
      ready: false,
      testRuns: [],
      testRunIds: [1, 2],
      testAttrs: ["case", "comment", "result"],
      testAttrsKeys: ["case", "comment", "result"]
    };
  },
  methods: {
  },
  created: function(){
    this.testRuns = this.testRunIds.map((value, idx, arr) =>
      window.fetch(`/api/run/${value}/auto/`)
        .then(res => res.json()
            .then(data => this.testRuns[idx] = data)
            .catch(err => alert(`Failing json parsing with ${err}`))
        )
    );
    Promise.all(this.testRuns).then(() => {
      let casesByName = _.groupBy(_.concat(...this.testRuns), testcase => testcase.case);
      let commonCases = _.intersectionBy(...this.testRuns, "case");
      let commonCasesByName = _.groupBy(commonCases, testcase => testcase.case);
      _.forEach(this.testRuns, testrun => {
        _.forEach(testrun, testcase => {
          if(!commonCasesByName[testcase.case])
            testcase.different = "new";
          else if(_.some(casesByName[testcase.case], (otherTestcase) => {console.log(otherTestcase);return otherTestcase.result != testcase.result;}))
            testcase.different = "diff";
          else
            testcase.different = "";
        });
      });
      this.ready = true;
    });
  },
  watch: {
  },
  mounted: function(){
  }
});

var TestRunChildRow = Vue.extend({
});
