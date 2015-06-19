(function() {
  'use strict';

  // format a date to YYYY-MM-DD
  function formatDate(datestr) {
    var _date = new Date(datestr);
    var day = _date.getDate();
    var monthIndex = _date.getMonth().toString().length === 1 ? '0' + (_date.getMonth() + 1) : _date.getMonth() + 1;
    var year = _date.getFullYear();

    return year + '-' + monthIndex + '-' + day;
  }

})();
