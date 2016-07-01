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
            this.api().columns().every(function(){
                // Use selector filter to replace text input filter
                // for specified columns
                var column = this;
                var title = $(column.header()).text();
                if (param.selectorColumns && param.selectorColumns.indexOf(title) > -1){
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
                            selections = selections.concat($.map(d, function(n){return n}));
                        }
                        else{
                            selections = selections.concat(d);
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
