$(document).ready(function() {
  $('#column_table').dataTable( {
    pageLength: 50,
    columns: [
      {% for col in column_datas %}
      {
        "data":"{{ col }}",
        "render": prettier
      },
      {% endfor %}
    ],
    ajax: {
      url: '{{ajax}}',
      dataSrc: ''
    },
  });
});
