(function() {
  'use strict';

  $('.datepicker').datetimepicker({
    format: 'YYYY-MM-DD',
    widgetPositioning: {
      vertical: 'bottom',
    }
  });
  $('.datetimepicker').datetimepicker({
    format: 'YYYY-MM-DD h:mma',
    widgetPositioning: {
      vertical: 'bottom',
    }
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
