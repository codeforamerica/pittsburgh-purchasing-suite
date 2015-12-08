$(document).ready(function() {
  $.fn.dataTableExt.afnFiltering.push(function (oSettings, aData, iDataIndex) {
    if (oSettings.sTableId === "js-table-progress" || oSettings.sTableId === "js-table-all") {
      if ($('#' + oSettings.sTableId + '-container').find('.js-show-only-mine').is(':checked')) {
        return aData[0] === currentUser;
      }
      return true;
    }
    return true;
  });

  var progressTable = $('#js-table-progress').DataTable({
    // order by expiration date -- column 4
    'order': [[8, 'asc']],

    'aoColumnDefs': [
      { 'orderable': false, 'aTargets': [1] },
      { 'bVisible': false, 'aTargets': [0, 4, 7, 11] },
      { 'iDataSort': 7, 'aTargets': [8] },
      { 'iDataSort': 4, 'aTargets': [5] }
    ],
  });

  var allTable = $('#js-table-all').DataTable({
    // order by expiration date -- column 4
    'order': [[7, 'asc']],
    // use column 3 (actual timestamps) as a sort proxy for
    // column 4 (formatted "days since")
    'aoColumnDefs': [
      { 'orderable': false, 'aTargets': [1] },
      { 'bVisible': false, 'aTargets': [0, 6, 10] },
      { 'iDataSort': 6, 'aTargets': [7] }
    ],
  });

  $('.js-show-only-mine').on('change', function() {
    var checked = $(this);
    if (checked.attr('data-table-name') === 'progress') {
      progressTable.draw();
    } else if (checked.attr('data-table-name') === 'all') {
      allTable.draw();
    }
  });

  function format(itemNumber, description, department, controller, spec, parentSpec, companies) {
    var table = '<table class="table table-condensed table-bordered"><tbody>';
    if (itemNumber) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Item #</strong></td><td>' + itemNumber + '</td></tr>' }
    if (description) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Full Description</strong></td><td>' + description + '</td></tr>' }
    if (department) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Department</strong></td><td>' + department + '</td></tr>' }
    if (controller) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Controller #</strong></td><td>' + controller + '</td></tr>' }
    if (spec) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Spec #</strong></td><td>' + spec + '</td></tr>' }
    if (parentSpec) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Old Spec #</strong></td><td>' + parentSpec + '</td></tr>' }
    if (companies) { table += '<tr><td class="dropdown-table-border-right col-md-3"><strong>Companies</strong></td><td>' + companies + '</td></tr>' }
    table += '</tbody></table></div>';

    return table;
  }

  function showHideAdditionalInformation(clickedElem, table, formatMethod) {
    var clicked = $(clickedElem);
    var tr = clicked.closest('tr');
    var row = table.row(tr);

    if (row.child.isShown()) {
      row.child.hide();
      tr.removeClass('shown');
      clicked.find('.fa').removeClass('fa-minus').addClass('fa-plus');
    } else {
      row.child(format(
        tr.attr('data-item-number'), tr.attr('data-full-description'),
        tr.attr('data-department'), tr.attr('data-controller'),
        tr.attr('data-spec-number'), tr.attr('data-parent-spec-number'),
        tr.attr('data-companies')
      )).show();
      tr.addClass('shown');
      clicked.find('.fa').removeClass('fa-plus').addClass('fa-minus');
    }
  }

  $('#js-table-progress tbody').on('click', 'td.details-control', function() {
    showHideAdditionalInformation(this, progressTable);
  });

  $('#js-table-all tbody').on('click', 'td.details-control', function() {
    showHideAdditionalInformation(this, allTable);
  });

  $('.js-conductor-init-hidden').removeClass('hidden');
  $('#js-loading-spinner').addClass('hidden');

  // custom styling for datatables
  $('.dataTables_filter').find('input').addClass('form-control datatables-form-controls');
  $('.dataTables_length').find('select').addClass('form-control input-sm datatables-form-controls');

});
