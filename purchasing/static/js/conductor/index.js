$(document).ready(function() {
  $.fn.dataTableExt.afnFiltering.push(function (oSettings, aData, iDataIndex) {
    if (oSettings.sTableId === "js-table-progress") {
      if ($('#js-show-only-mine').is(':checked')) {
        return aData[7] === currentUser.split('@')[0];
      }
      return true;
    }
    return true;
  });

  var progressTable = $('#js-table-progress').DataTable({
    // order by expiration date -- column 4
    'order': [[5, 'asc']],
    // use column 3 (actual timestamps) as a sort proxy for
    // column 4 (formatted "days since")
    'aoColumnDefs': [
      { 'orderable': false, 'aTargets': [0] },
      { 'bVisible': false, 'aTargets': [4, 7] },
      { 'iDataSort': 4, 'aTargets': [5] }
    ],
  });

  var allTable = $('#js-table-all').DataTable({
    // order by expiration date -- column 4
    'order': [[5, 'asc']],
    // use column 3 (actual timestamps) as a sort proxy for
    // column 4 (formatted "days since")
    'aoColumnDefs': [
      { 'bVisible': false, 'aTargets': [4, 7] },
      { 'iDataSort': 4, 'aTargets': [5] }
    ]
  });

  $('#js-show-only-mine').on('change', function() {
    progressTable.draw();
  });

  function format(department, controller) {
    return '<div>Department: ' + department + '<br />Controller number: ' + controller + '</div>';
  }

  function showHideTableRows(clicked, table) {
    var tr = $(clicked).closest('tr');
    var row = table.row(tr);
    var child = row.child;

    if (row.child.isShown()) {
      row.child.hide();
      tr.removeClass('shown');
    } else {
      row.child( format( tr.attr('data-department'), tr.attr('data-controller') ) ).show();
      tr.addClass('shown');
    }
  }

  $('#js-table-progress tbody').on('click', 'td.details-control', function() {
    showHideTableRows(this, progressTable);
  });

  $('#js-table-all tbody').on('click', 'td.details-control', function() {
    showHideTableRows(this, allTable);
  })

  $('.hidden').removeClass('hidden');
  $('#js-loading-spinner').addClass('hidden');

});
