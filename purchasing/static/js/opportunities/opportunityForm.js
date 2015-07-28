(function() {
  'use strict';

  $('.datepicker').datepicker({
    todayHighlight: true,
    format: 'yyyy-mm-dd',
    autoclose: true,
    orientation: 'auto top'
  });

  $('[data-toggle="tooltip"]').tooltip();

  $('.js-confirm-delete').on('click', function(e) {
    return confirm($(this).data('confirm'));
  });

})();
