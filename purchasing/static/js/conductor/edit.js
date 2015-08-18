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
      $(this).multiFormHandler('remove');

      initUi();
      showHideClose();
    });
  }

  $('.js-multiform-add').on('click', function(e) {
    var _this = $(this);
    $(this).multiFormHandler('add');

    $('.' + _this.attr('data-hide-row')).last().hide();
    $('.' + _this.attr('data-show-row')).last().show();

    initUi();
    showHideClose();
    removeForm($('.js-multiform-remove'));
  });

  // render the proper field (wherever data is)
  $('.company-form-container').each(function() {
    var _this = $(this);
    if (_this.find('input[value!=""]').length > 0 && _this.find('input[value!=""]')[0].id.indexOf('new') >= 0) {
      _this.find('.new-company-row').show();
      _this.find('.existing-company-row').hide();
    }
  });

  showHideClose();
  removeForm($('.js-multiform-remove'));

})();
