(function(root){
    var $ = root.$,
        d3 = root.d3;

    var margin = {top: 40, right: 10, bottom: 20, left: 10},
        width = 960 - margin.left - margin.right,
        height = 500 - margin.top - margin.bottom;

    var keyword_colors = {
        "auto_passed": "limegreen",
        "auto_failed": "tomato",
        "auto_skipped": "darkorange",
        "auto_error": "lightgray"
    };

    var TestRunStackGraph = function(dom_selector, testRun){
        this.layer_keys = Object.keys(keyword_colors);
        this.n = this.layer_keys.length;
        this.stack = d3.stack()
            .keys(this.layer_keys)
            .order(d3.stackOrderNone)
            .offset(d3.stackOffsetNone);

        this.initGraph(dom_selector);
        var that = this;
        this.ajaxData(testRun).then(function(){
            that.render();
        });
    };

    TestRunStackGraph.prototype.changeKeys = function(keys){
        this.layer_keys = keys;
        this.n = this.layer_keys.length;
        this.stack.keys(this.layer_keys);
        if(this.data){
            //If data is undefined, graph is still initializing.
            this.render();
        }
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

    TestRunStackGraph.prototype.render = function(){
        var n = this.n,// number of layers
            m = this.data.length, // number of samples per layer
            layers = this.stack(this.data),
            yStackMax = d3.max(layers, function(layer) { return d3.max(layer, function(d) { return d[1]; }); });

        var x = this.x,
            y = this.y,
            xAxis = this.xAxis,
            svg = this.svg;

        var that = this;

        //Update scale, layer etc.
        this.x.domain(d3.range(m));
        this.y.domain([yStackMax, 0]);

        xAxis.scale(x);

        var layer = this.svg.selectAll(".layer")
            .data(layers);

        svg.selectAll("g.xAxis").transition().call(xAxis);

        //perform redraw and transition
        layer.enter().append("g")
            .attr("class", "layer")
            .merge(layer)
            .style("fill", function(d, i) { return keyword_colors[that.layer_keys[i]] || 'red'; });

        layer.exit().remove();

        layer = this.svg.selectAll(".layer");

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
            .attr("y", function(d) { return height - y(d[0]) - (y(d[1]) - y(d[0])); })
            .attr("height", function(d, i) { return y(d[1]) - y(d[0]); });
    };

    TestRunStackGraph.prototype.updateData = function(testRun){
        var that = this;
        this.ajaxData(testRun).then(function(){
            that.render();
        });
    };

    TestRunStackGraph.prototype.ajaxData = function(testRun){
        var that = this;
        // TODO: hard coded url
        return $.get('/statistics/run/' + (testRun || ''), function(data){
            results = [];
            for (var key in data){
                results = results.concat(data[key]);
            }

            that.data = results;
        }).promise();
    };

    root.TestRunStackGraph = TestRunStackGraph;
}(this));
