(function() {
  'use strict';

  // grab all of the transition buttons
  var transitionBtns = $('.js-transition');

  transitionBtns.on('click', function() {
    var clickedStage = this.id.split('-')[1];
    var currentStage = this.attributes.getNamedItem('data-current').value;
    $.ajax({
      type: 'POST',
      url: '/conductor/' + contractId + '/transition',
      data: JSON.stringify({clicked: clickedStage, current: currentStage}),
      contentType: 'application/json;charset=UTF-8',
      success: function(data, status, xhr) {
        debugger;
      }, error: function(data, status, xhr) {
        debugger;
      }
    });

  });
})();
