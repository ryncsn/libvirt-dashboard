const _ = require("lodash");

export default {
  props: ["triggerGateUrl", "getJobNamesUrl", ],
  data(){
    return {
      archCandidate: ["x86_64", "ppc64le", "aarch64"],
      tagCandidate: ["7.3", "7.4", "arm"],
      matchedJobs: [],

      pkg_name: "",
      arch: ["x86_64"],
      brew_tag: "",
      message: "{}",
      product: "",
      job_name: "",
    };
  },
  methods: {
    dataForSubmit(){
      return _.pickBy(
        _.pick(this, ["arch", "brew_tag", "message", "product", "job_name", "pkg_name"]),
        v => v !== "" && v.length !== 0
      );
    },
    submit(){
      $.ajax({
        url: this.triggerGateUrl,
        data: this.dataForSubmit(),
        method: "POST",
      })
        .done(() => alert("Submit successful"))
        .fail((err) => alert(`Failed with ${err}`));
    },
    getMatchedJobs: _.debounce(function (){
      $.ajax({
        url: this.getJobNamesUrl,
        data: this.dataForSubmit(),
        method: "POST",
      })
        .done((data) => this.matchedJobs = data);
    }, 500),
    addArch(arch){
      if (this.arch.indexOf(arch) == -1){
        this.arch.push(arch);
      }
    },
    removeArch(arch){
      this.arch.splice(this.arch.indexOf(arch), 1);
    },
    isJsonValid(str) {
      try {
        JSON.parse(str);
      } catch (e) {
        return false;
      }
    return true;
    },
  },
  computed: {
    archValid(){
      return (this.arch.length !== 0);
    },
    packageValid(){
      return true;
    },
    productValid(){
      return true;
    },
    jobNameValid(){
      return true;
    },
    ciMessageValid(){
      return this.isJsonValid(this.message);
    }
  },
  created(){
  },
  watch:{
    job_name(){
      this.getMatchedJobs();
    },
    arch(){
      this.getMatchedJobs();
    },
    product(){
      this.getMatchedJobs();
    },
    brew_tag(){
      this.getMatchedJobs();
    },
    pkg_name(){
      this.getMatchedJobs();
    },
  }
};
