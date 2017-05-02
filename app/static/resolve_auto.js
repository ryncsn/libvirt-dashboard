const Vue = require("vue");
const autoresultTable = require("./component/autoresult-datatable.vue");

var vm = new Vue({
  el: "#autoresult-resolving",
  components: {
    'autoresult-table': autoresultTable,
  },
});
