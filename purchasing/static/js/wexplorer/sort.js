(function() {
  'use strict';

  var searchResults = $('#js-sort-results');
  if (searchResults.length > 0) {
    searchResults.find('th').click(function() {
      var _table = $(this).parents('table').eq(0);
      var rows = _table.find('tr:gt(0)').toArray().sort(comparer($(this).index()));
      this.asc = !this.asc;
      if (!this.asc) { rows = rows.reverse(); }
      for (var i=0; i<rows.length; i++) {
        _table.append(rows[i]);
      }
    });
  }

  function comparer(index) {
    return function(a,b) {
      var valA = getCellValue(a, index);
      var valB = getCellValue(b, index);
      return $.isNumeric(valA) && $.isNumeric(valB) ? valA - valB : valA.localeCompare(valB);
    };
  }

  function getCellValue(row, index) {
    return $(row).children('td').eq(index).attr('data-sortable');
  }

  $('[data-toggle="tooltip"]').tooltip();

  $('#js-filter-btn-group').children('.btn').each(function(ix, i) {
    var _this = $(i);
    var _input = _this.find('input');
    if (_input.prop('checked') === true) {
      _this.addClass('active');
    }
  });

})();
