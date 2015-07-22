(function () {
  'use strict';

  var categoriesContainer = $('#js-categories-container');
  var addAnother = $('#js-add-category');
  var categoryId = 1;

  function displayNewSubcats (subcatGroup, category) {
    var newSubcats = subcategories[category];
    // remove the old radio boxes
    subcatGroup.children().remove();

    // return if we don't have any categories
    if (!newSubcats) {
      return;
    }

    // otherwise add the new ones
    var newCheckboxes = '<div class="col-sm-12">' +
      '<div class="checkbox signup-checkbox">' +
        '<input id="check-all-' + categoryId + '" type="checkbox" class="js-uncheck-all" data-checked="true" checked="true" name="check-all">' +
        '<label for="check-all-' + categoryId + '">Check all</label>' +
      '</div>' +
    '</div>';

    for (var i = 0; i < newSubcats.length; i++) {
      newCheckboxes += '<div class="col-sm-12">' +
        '<div class="checkbox signup-checkbox">' +
          '<input id="subcategories-' + newSubcats[i][0] + '" class="js-subcategory" name="subcategories-' + newSubcats[i][0] +
            '" type="checkbox" checked=true>' +
          '<label for="subcategories-' + newSubcats[i][0] + '">' + newSubcats[i][1] + '</label>' +
        '</div>' +
      '</div>';
    }

    subcatGroup.append(newCheckboxes);

    return true;
  }

  function uncheckAll () {
    $('.js-uncheck-all').change(function () {
      var subcatGroup = $(this).parents('.form-group');
      var _this = $(this);

      if (_this.attr('data-checked') === 'true') {
        subcatGroup.find('input:checkbox').prop('checked', false);
        _this.attr('data-checked', 'false');

      } else {
        subcatGroup.find('input:checkbox').prop('checked', true);
        _this.attr('data-checked', 'true');
      }
    });
  }

  function showSubcats (subcatLabel) {
    var subcatGroup = '#js-subcategory-group-' + subcatLabel.id.split('-')[1];
    displayNewSubcats($(subcatGroup), subcatLabel.value);
    uncheckAll();

    if (subcatLabel.value !== '') {
      $('#js-add-another-container').removeClass('hidden');
    } else if (subcatLabel.value === '' && categoryId === 1) {
      $('#js-add-another-container').addClass('hidden');
    }
  }

  function generateNewSubcats () {
    $('.js-category-select').change(function () {
      showSubcats(this);
    });
  }

  generateNewSubcats();

  $(addAnother).click(function () {
    var categorySelect = '<option value="">-- Choose One --</option>';

    $.each(categories, function (ix, value) {
      categorySelect += '<option value="' + value + '">' + value + '</option>';
    });

    categoriesContainer.append('<div class="form-group">' +
      '<div class="col-sm-12">' +
        '<select class="form-control col-sm-12 js-category-select" id="categories-' + categoryId + '" name="categories-' + categoryId + '">' +
      categorySelect +
        '</select>' +
      '</div>' +
    '</div>' +
    '<div class="form-group" id="js-subcategory-group-' + categoryId + '">' +
    '</div>');

    var newCategory = $('#categories-' + categoryId);

    displayNewSubcats($('#js-subcategory-group-' + categoryId), newCategory.val());

    categoryId += 1;

    generateNewSubcats();
    uncheckAll();

  });

  var initCategorySelect = $('.js-category-select');

  if (initCategorySelect.length > 0 && initCategorySelect !== '---') {
    showSubcats($('.js-category-select')[0]);
  }

})();
