const Vue = require("vue");
const jobTrigger = require("./component/job-trigger.vue");

var vm = new Vue({
  el: "#job-trigger",
  components: {
    'job-trigger': jobTrigger,
  },
});
