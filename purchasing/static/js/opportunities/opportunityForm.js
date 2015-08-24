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

  function showHideClose() {
    if ($('.js-multiform-remove').length > 1) {
      $('.js-multiform-remove').removeClass('hidden');
    } else {
      $('.js-multiform-remove').addClass('hidden');
    }
  }

  function removeForm(elems) {
    $(elems).on('click', function() {
      $(this).multiFormHandler('remove');
      showHideClose();
    });
  }

  $('.js-multiform-add').on('click', function(e) {
    $(this).multiFormHandler('add');
    showHideClose();
    removeForm($('.js-multiform-remove'));
  });

})();
