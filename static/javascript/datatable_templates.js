function DataSearchTable(param){
    // Setup - First add a text input to each footer cell
    var that = this
    this.find('tfoot th').each(function(){
        var title = that.find('thead th').eq($(this).index()).text();
        if(title.length > 0){
            $(this).html('<input type="text" placeholder="Search '+title+'"/>');
        }
    });

    var initCompleteNext = param.initComplete;
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
                    if(selectorColumns[title].strict){
                        var reg = val ? "^" + val + "$" : '^$';
                    }
                    else{
                        var reg = val ? val : '';
                    }
                    column
                    .search(reg , true, false )
                    .draw();
                });
                column.data().each(function(d, j){
                    if($.isArray(d)){
                        if(d.length == 0){
                            var new_select = render(d);
                            if(selections.indexOf(new_select) == -1){
                                selections.push(new_select);
                            }
                        }
                        for (var i = 0, len = d.length; i < len; i++) {
                            var new_select = render(d[i]);
                            if(selections.indexOf(new_select) == -1){
                                selections.push(new_select);
                            };
                        }
                    }
                    else{
                        var new_select = render(d);
                        if(selections.indexOf(new_select) == -1){
                            selections.push(new_select);
                        };
                    }
                });
                selections.sort();
                $.each(
                    selections,
                    function(key, value){
                        select.append('<option value="'+value+'">'+value+'</option>');
                    }
                );
            }
            // Apply the search
            if(column.visible()){
                $('input', column.footer()).on('keyup change', function(){
                    column
                    .search(this.value)
                    .draw();
                });
            }
        });
        if(initCompleteNext)
            initCompleteNext.apply(this, [setting, json]);
    }
    var BaseTable = param.BaseTable || this.DataTable;
    if (BaseTable instanceof Array){
        Base = param.BaseTable.shift();
        if(param.BaseTable.length == 0)
            param.BaseTable = null;
        return Base.apply(this, [param]);
    }
    return BaseTable.apply(this, [param]);
}

function DataTableWithInlineButton(param){
    param.dom = '<<"row" <"col-md-2"l><"col-md-6"B><"col-md-4"f>>r<t><"row"<"col-md-6"i><"col-md-6"p>>>';
    var BaseTable = param.BaseTable || this.DataTable;
    if (BaseTable instanceof Array){
        Base = param.BaseTable.shift();
        if(param.BaseTable.length == 0)
            param.BaseTable = null;
        return Base.apply(this, [param])
    }
    return BaseTable.apply(this, [param]);
}

function DataTableWithChildRow(param){
    //Preconfig params with child.
    //Need fontawesome, bootstrap
    var that = this;
    //Insert a button column
    this.find('thead tr').prepend("<th></th>")
    this.find('tfoot tr').prepend("<th></th>")

    param.columns.unshift(
        {
            "data": null,
            "className": 'details-control',
            "orderable": false,
            "defaultContent": '<i class="fa fa-fw fa-plus" aria-hidden="true"></i>',
            "width": '10',
        }
    );

    var initCompleteNext = param.initComplete;
    param.initComplete = function(setting, json){
        var table = this.api();
        var tbody = this.find('tbody')
        this.on('click', 'tbody td.details-control', function(){
            var tr = $(this).closest('tr');
            var button = $(this).find('i');
            var row = table.row(tr);

            function slideDown(){
                $('div.slider', row.child()).slideDown();
            }

            function slideUp(){
                $('div.slider', row.child()).slideUp(function(){
                    row.child.hide();
                    button.addClass('fa-plus');
                    button.removeClass('fa-minus');
                });
            }

            if (row.child.isShown()) {
                slideUp();
            }
            else {
                // Open this row
                row.child('<div class="slider row-child"><div class="child-content"></div></div>', 'no-padding').show();
                button.removeClass('fa-plus');
                button.addClass('fa-minus');

                //Load Detail
                param.childContent(row, $(row.child()).find(".child-content"), slideDown, slideUp);
            }
        });
        if(initCompleteNext)
            initCompleteNext.apply(this, [setting, json]);
    }
    var BaseTable = param.BaseTable || this.DataTable;
    if (BaseTable instanceof Array){
        Base = param.BaseTable.shift();
        if(param.BaseTable.length == 0)
            param.BaseTable = null;
        return Base.apply(this, [param])
    }
    return BaseTable.apply(this, [param]);
}

$.fn.extend({
    DataSearchTable: DataSearchTable,
    DataTableWithChildRow, DataTableWithChildRow,
    DataTableWithInlineButton, DataTableWithInlineButton,
});
