$(document).ready(function() {

  'use strict';

  $('.js-email-contact-card').on('click', function(e) {
    var clicked = $(e.target);
    var email = clicked.text();
    var input = clicked.closest('.form-group').find('input');
    input.val(function(index, val) {
      return val + email + ';';
    });
  });

  $('.js-filter-btn').on('click', function(e) {

    // get the classname to show/hide

    // show or hide that specific classname

    var selectedBtn = $(this);

    $('.action-event').hide();

    selectedBtn.hasClass('js-filter-active') ?
      selectedBtn.removeClass('js-filter-active') :
      selectedBtn.addClass('js-filter-active');

    var activeBtns = $('.js-filter-active');

    if (activeBtns.length) {
      activeBtns.each(function() {
        var toFilter = 'js-filter-action-' + this.getAttribute('data-js-filter');
        $('.' + toFilter).show();
      });
    } else {
      $('.action-event').show();
    }

  });

  $('#js-send-email-update-form').dirtyForms();

  if (currentStageEnter || false) {

    var e = $('.datetimepicker');

    e.datetimepicker({
      format: 'YYYY-MM-DD h:mma',
      maxDate: moment(e.attr('data-maximum'), 'YYYY-MM-DD HH:mm').format('YYYY-MM-DD HH:mm'),
      minDate: moment(e.attr('data-started'), 'YYYY-MM-DD HH:mm').format('YYYY-MM-DD HH:mm'),
      defaultDate: moment(e.attr('data-maximum'), 'YYYY-MM-DD HH:mm').format('YYYY-MM-DD HH:mm'),
      keepInvalid: true
    }).on('dp.error', function(e) {
      $('.js-datepicker-validator').removeClass('hidden');
    }).on('dp.change', function(e) {
      $('.js-datepicker-validator').addClass('hidden');
    });

  }

});
