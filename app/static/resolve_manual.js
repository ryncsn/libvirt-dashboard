const Vue = require("vue");
const manualresultTable = require("./component/manualresult-datatable.vue");

var vm = new Vue({
  el: "#manualresult-resolving",
  components: {
    'manualresult-table': manualresultTable,
  },
});
