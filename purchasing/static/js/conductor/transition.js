(function() {
  'use strict';

  // format a date to YYYY-MM-DD
  function formatDate(datestr) {
    var _date = new Date(datestr);
    var day = _date.getDate();
    var monthIndex = _date.getMonth().toString().length === 1 ? '0' + (_date.getMonth() + 1) : _date.getMonth() + 1;
    var year = _date.getFullYear();

    return year + '-' + monthIndex + '-' + day;
  }


  var checkUrlBtn = $('#checkUrl');
  var urlIcon = $('#checkUrlIcon');
  var currentHref = $('#contract_href');

  currentHref.on('change', function() {
    urlIcon.removeClass('fa-minus fa-ban ban-error fa-check check-success').addClass('fa-minus');
  });

  checkUrlBtn.on('click', function() {
    var currentHrefVal = currentHref.val();
    $.ajax({
      url: '/conductor/contract/' + contractId + '/edit/url-exists',
      type: 'POST',
      data: JSON.stringify({url: currentHrefVal}),
      contentType: 'application/json;charset=UTF-8',
      success: function(data, status, xhr) {
        if (data.status === 200) {
          urlIcon.removeClass('fa-minus fa-ban ban-error').addClass('fa-check check-success');
        } else {
          urlIcon.removeClass('fa-minus fa-check check-success').addClass('fa-ban ban-error');
        }
      },
      error: function(data, status, xhr) {
        urlIcon.removeClass('fa-minus fa-check check-success').addClass('fa-ban ban-error');
      }
    });
  });

  if (activeTab) {
    $('#tablist a[href="' + activeTab + '"]').tab('show');
  }

  var detailBtns = $('.btn-detail');
  detailBtns.on('click', function() {
    var btn = $(this);
    btn.addClass('disabled');
    btn.append('<span style="padding-left:5px;"><i class="fa fa-refresh fa-spin"></i></span>');
  });

  var currentEvent = $('.event-current');
  if (currentEvent.length === 1) {
    currentEvent.get(0).scrollIntoView(false);
  }

})();
