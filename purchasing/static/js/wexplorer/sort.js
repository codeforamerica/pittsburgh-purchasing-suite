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
    return $(row).children('td').eq(index).text();
  }

  $('[data-toggle="tooltip"]').tooltip();

})();
