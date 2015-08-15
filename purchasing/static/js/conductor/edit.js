(function() {

  'use strict';

  function initUi() {
    $('.js-company-name-select2').select2({
      placeholder: 'Pick one'
    });
    $('.datepicker').datepicker({
      todayHighlight: true,
      format: 'yyyy-mm-dd',
      autoclose: true,
      orientation: 'auto top'
    });
    return;
  }

  initUi();

  function showHideClose() {
    if ($('.js-multiform-remove').length > 1) {
      $('.js-multiform-remove').removeClass('hidden');
    } else {
      $('.js-multiform-remove').addClass('hidden');
    }
  }

  function removeForm(elems) {
    $(elems).on('click', function() {
      console.log('click!')
      $(this).multiFormHandler('remove');

      initUi();
      showHideClose();
    });
  }

  $('.js-multiform-add').on('click', function(e) {
    $(this).multiFormHandler('add');

    initUi();
    showHideClose();
    removeForm($('.js-multiform-remove'));
  });

  showHideClose();
  removeForm($('.js-multiform-remove'));

})();
