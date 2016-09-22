(function(root){
    var $ = root.$,
        d3 = root.d3;

    var layer_keys = ["auto_passed", "auto_failed", "auto_skipped", "auto_error"],
        layer_colors = ["limegreen", "tomato", "darkorange", "lightgray"],
        layer_color_gen = function(idx){ return layer_colors[idx];};

    var stack = d3.stack()
        .keys(["auto_passed", "auto_failed", "auto_skipped", "auto_error"])
        .order(d3.stackOrderNone)
        .offset(d3.stackOffsetNone);

    var margin = {top: 40, right: 10, bottom: 20, left: 10},
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;

    var TestRunStackGraph = function(dom_selector, testRun){
        this.transitionGrouped = function(){};
        this.transitionStacked = function(){};
        this.timeout = null;
        this.initGraph(dom_selector);
        this.updateData(testRun);
        this.presentation = "stacked";
    };

    TestRunStackGraph.prototype.changePresentation = function(value){
        this.presentation = value;
        if (this.timeout !== null){
            clearTimeout(this.timeout);
            this.timeout = null;
        }
        if (value === "grouped")
            this.transitionGrouped();
        else
            this.transitionStacked();
    };

    TestRunStackGraph.prototype.initGraph = function(dom_selector){
        this.x = d3.scaleBand()
            .domain(d3.range(0))
            .rangeRound([0, width])
            .paddingInner(0.05);

        this.y = d3.scaleLinear()
            .domain([0, 0])
            .range([height, 0]);

        this.xAxis = d3.axisBottom()
            .scale(this.x)
            .tickSize(0)
            .tickPadding(6);

        this.svg = d3.select(dom_selector).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

        this.svg.append("g")
            .attr("class", "xAxis")
            .attr("transform", "translate(0," + height + ")");
    };

    TestRunStackGraph.prototype.updateData = function(testRun){
        var x = this.x,
            y = this.y,
            xAxis = this.xAxis,
            svg = this.svg;

        var that = this;
        // TODO: hard coded url
        $.get('/statistics/run/' + (testRun || ''), function(data){
            results = [];
            for (var key in data){
                results = results.concat(data[key]);
            }

            var n = 4,// number of layers
                m = results.length, // number of samples per layer
                layers = stack(results),
                yGroupMax = d3.max(layers, function(layer) { return d3.max(layer, function(d) { return d[0]; }); }),
                yStackMax = d3.max(layers, function(layer) { return d3.max(layer, function(d) { return d[0] + d[1]; }); });

            that.x.domain(d3.range(m));

            that.y.domain([0, yStackMax]);

            xAxis.scale(x);

            svg.selectAll("g.xAxis").transition().call(xAxis);

            //Update data for each layer
            var layer = that.svg.selectAll(".layer")
                .data(layers);

            layer.enter().append("g")
                .attr("class", "layer")
                .style("fill", function(d, i) { return layer_color_gen(i); });

            layer = that.svg.selectAll(".layer");

            var rect = layer.selectAll("rect")
                .data(function(d) { return d; });

            rect.exit()
                .transition()
                .attr("y", height)
                .attr("height", 0)
                .remove();

            rect = rect.enter().append("rect")
                //Set start point for new added rect
                .attr("x", function(d, i) { return x(i); })
                .attr("y", height)
                .attr("width", x.bandwidth())
                .attr("height", 0)
                //Merge new added(enter) and existing(update)
                .merge(rect);

            rect.transition()
                //Transform to zero
                .attr("y", height)
                .attr("x", function(d, i) { return x(i); })
                .attr("width", x.bandwidth())
                .attr("height", 0)
                //Transform to the right positoin
                .transition()
                .delay(function(d, i) { return i * 10; })
                .attr("y", function(d) { return y(d[0] + d[1]); })
                .attr("height", function(d) {return y(d[0]) - y(d[0] + d[1]); });

            that.transitionGrouped = function() {
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
            };

            that.transitionStacked = function() {
                y.domain([0, yStackMax]);

                rect.transition()
                    .duration(500)
                    .delay(function(d, i) { return i * 10; })
                    .attr("y", function(d) { return y(d[0] + d[1]); })
                    .attr("height", function(d) { return y(d[0]) - y(d[0] + d[1]); })
                .transition()
                    .attr("x", function(d, i) { return x(i); })
                    .attr("width", x.bandwidth());
            };

            that.timeout = setTimeout(that.transitionGrouped, 2000);
        });
    };

    root.TestRunStackGraph = TestRunStackGraph;
}(this));
