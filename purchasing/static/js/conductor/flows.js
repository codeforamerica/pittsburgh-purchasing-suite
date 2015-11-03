(function() {
  'use strict';

  function showHideClose() {
    if ($('.js-multiform-stage-remove').length > 1) {
      $('.js-multiform-stage-remove').removeClass('disabled').find('i').removeClass('text-muted').addClass('text-danger');
    } else {
      $('.js-multiform-stage-remove').addClass('disabled').find('i').addClass('text-muted').removeClass('text-danger');
    }
  }

  function initUi() {
    $('.js-select2').select2({
      placeholder: 'Pick one',
      tags: true,
      multiple: false
    });
  }

  function removeForm(elems) {
    $(elems).on('click', function() {
      if ($('.js-multiform-stage-remove').length > 1) {
        $(this).multiFormHandler('remove');
      }
      showHideClose();
    });
  }

  initUi();
  showHideClose();
  removeForm($('.js-multiform-stage-remove'));

  $('.js-stage-multiform-add').on('click', function(e) {
    $(this).multiFormHandler('add');
    initUi();
    showHideClose();
    removeForm($('.js-multiform-stage-remove'));
  });
})();
