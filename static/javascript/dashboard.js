$.get('/statistics/run/', function(data){
    results = [];
    for(key in data){
        results = results.concat(data[key]);
    }

    var stack = d3.stack()
        .keys(["auto_passed", "auto_failed", "auto_skipped", "auto_error"])
        .order(d3.stackOrderNone)
        .offset(d3.stackOffsetNone);

    var n = 4 // number of layers
        m = results.length, // number of samples per layer
        layers = stack(results),
        yGroupMax = d3.max(layers, function(layer) { return d3.max(layer, function(d) { return d[0]; }); }),
        yStackMax = d3.max(layers, function(layer) { return d3.max(layer, function(d) { return d[0] + d[1]; }); });

    var margin = {top: 40, right: 10, bottom: 20, left: 10},
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;

    var x = d3.scaleBand()
        .domain(d3.range(m))
        .rangeRound([0, width])
        .paddingInner(0.05);

    var y = d3.scaleLinear()
        .domain([0, yStackMax])
        .range([height, 0]);

    var color = d3.scaleLinear()
        .domain([0, n - 1])
        .range(["#aad", "#556"]);

    var xAxis = d3.axisBottom()
        .scale(x)
        .tickSize(0)
        .tickPadding(6);

    var svg = d3.select(".d3").append("svg")
        .attr("width", width + margin.left + margin.right)
        .attr("height", height + margin.top + margin.bottom)
      .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var layer = svg.selectAll(".layer")
        .data(layers)
      .enter().append("g")
        .attr("class", "layer")
        .style("fill", function(d, i) { return color(i); });

    var rect = layer.selectAll("rect")
        .data(function(d) { return d; })
      .enter().append("rect")
        .attr("x", function(d, i) { return x(i); })
        .attr("y", height)
        .attr("width", x.bandwidth())
        .attr("height", 0);

    rect.transition()
        .delay(function(d, i) { return i * 10; })
        .attr("y", function(d) { return y(d[0] + d[1]); })
        .attr("height", function(d) { return y(d[0]) - y(d[0] + d[1]); });

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis);

    d3.selectAll("input").on("change", change);

    var timeout = setTimeout(function() {
      d3.select("input[value=\"grouped\"]").property("checked", true).each(change);
    }, 2000);

    function change() {
      clearTimeout(timeout);
      if (this.value === "grouped") transitionGrouped();
      else transitionStacked();
    }

    function transitionGrouped() {
      y.domain([0, yGroupMax]);

      rect.transition()
          .duration(500)
          .delay(function(d, i) { return i * 10; })
          //Ouch!
          .attr("x", function(d, i) {return x(i) + x.bandwidth() / n * (Array.prototype.indexOf.call(this.parentNode.parentNode.childNodes, this.parentNode)); })
          .attr("width", x.bandwidth() / n)
        .transition()
          .attr("y", function(d) { return y(d[1]); })
          .attr("height", function(d) { return height - y(d[1]); });
    }

    function transitionStacked() {
      y.domain([0, yStackMax]);

      rect.transition()
          .duration(500)
          .delay(function(d, i) { return i * 10; })
          .attr("y", function(d) { return y(d[0] + d[1]); })
          .attr("height", function(d) { return y(d[0]) - y(d[0] + d[1]); })
        .transition()
          .attr("x", function(d, i) { return x(i); })
          .attr("width", x.bandwidth());
    }
});


