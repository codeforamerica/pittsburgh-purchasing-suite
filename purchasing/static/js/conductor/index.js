$(document).ready(function() {
  $.fn.dataTableExt.afnFiltering.push(function (oSettings, aData, iDataIndex) {
    if (oSettings.sTableId === "js-table-progress") {
      if ($('#js-show-only-mine').is(':checked')) {
        return aData[6] === currentUser.split('@')[0];
      }
      return true;
    }
    return true;
  });

  var progressTable = $('#js-table-progress').DataTable({
    // order by expiration date -- column 4
    'order': [[4, 'asc']],
    // use column 3 (actual timestamps) as a sort proxy for
    // column 4 (formatted "days since")
    'aoColumnDefs': [
      { 'bVisible': false, 'aTargets': [3, 6] },
      { 'iDataSort': 3, 'aTargets': [4] }
    ],
  });

  $('#js-table-all').dataTable({
    // order by expiration date -- column 4
    'order': [[4, 'asc']],
    // use column 3 (actual timestamps) as a sort proxy for
    // column 4 (formatted "days since")
    'aoColumnDefs': [
      { 'bVisible': false, 'aTargets': [3, 6] },
      { 'iDataSort': 3, 'aTargets': [4] }
    ]
  });

  $('#js-show-only-mine').on('change', function() {
    progressTable.draw();
  });

  $('#js-loading-spinner').addClass('hidden');
  $('#js-table-container-progress').removeClass('hidden');
  $('#js-table-container-upcoming').removeClass('hidden');
  $('#js-table-container-all').removeClass('hidden');

});
