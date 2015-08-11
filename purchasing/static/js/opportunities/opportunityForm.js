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

  var documentUploadId = $('.js-upload-document-input').length;

  $('#js-add-document').on('click', function(e) {
    $('.js-document-container').append(
      '<div class="form-group">' +
        '<p>Document Name: </p>' +
        '<input class="form-control" id="document-' + documentUploadId +
          '-title" name="document-' + documentUploadId +
          '-title" type="text" value="">' +
      '</div>' +
      '<div class="form-group">' +
        '<input class="js-upload-document-input" id="document-' + documentUploadId +
          '-document" name="document-' + documentUploadId +
          '-document" type="file">' +
      '</div>'
    );

    documentUploadId++;
  });

})();
