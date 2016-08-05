$.fn.extend({
    DataSearchTable: function(param){
        // Setup - First add a text input to each footer cell
        that = this
        this.find('tfoot th').each(function(){
            var title = that.find('thead th').eq($(this).index()).text();
            if(title.length > 0){
                $(this).html('<input type="text" placeholder="Search '+title+'"/>');
            }
        });

        initCompleteNext = param.initComplete;
        param.initComplete = function(setting, json){
            selectorColumns = {}
            if(param.selectorColumns){
                for (var i = 0, len = param.selectorColumns.length; i < len; i++) {
                    if(typeof param.selectorColumns[i] === 'object')
                        selectorColumns[param.selectorColumns[i].column] = param.selectorColumns[i];
                    else if(typeof param.selectorColumns[i] === 'string')
                        selectorColumns[param.selectorColumns[i]] = {};
                }
            }
            this.api().columns().every(function(){
                // Use selector filter to replace text input filter
                // for specified columns
                var column = this;
                var title = $(column.header()).text();
                if (title in selectorColumns){
                    var render = selectorColumns[title].render;
                    if(!render)
                        render = function(d){return d;}
                    var selections = [];
                    var select = $('<select><option value=""></option></select>')
                    .appendTo($(column.footer()).empty())
                    .on('change', function () {
                        var val = $.fn.dataTable.util.escapeRegex($(this).val());
                        column
                        .search( val ? val : '', true, false )
                        .draw();
                    });
                    column.data().each(function(d, j){
                        if($.isArray(d)){
                            selections = selections.concat(render($.map(d, function(n){return n})));
                        }
                        else{
                            selections = selections.concat(render(d));
                        }
                    });
                    $.each(
                        $.grep(selections, function(el, index) {
                            return index === $.inArray(el, selections);
                        }),
                        function(key, value){
                            select.append('<option value="'+value+'">'+value+'</option>');
                        }
                    );
                }
                // Apply the search
                var that = this;
                $('input', this.footer()).on('keyup change', function(){
                    that
                    .search( this.value)
                    .draw();
                });
            });
            if(initCompleteNext)
                initCompleteNext(setting, json);
        }
        return this.DataTable(param);
    }
});
