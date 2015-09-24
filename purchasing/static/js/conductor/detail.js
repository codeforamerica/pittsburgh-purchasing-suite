(function() {

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

})();
