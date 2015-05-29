(function() {
  'use strict';

  var categoriesContainer = $('#js-categories-container');
  var addAnother = $('#js-add-category');
  var categoryId = 1;

  function displayNewSubcats(subcatGroup, category) {
    var newSubcats = subcategories[category];
    // remove the old radio boxes
    subcatGroup.children().remove();

    // add the new ones
    var newCheckboxes = '';

    for (var i=0; i<newSubcats.length; i++) {
      newCheckboxes += '<div class="col-sm-12">' +
        '<div class="checkbox">' +
          '<input id="subcategories-"' + i + ' name="subcategories" class="js-subcategory" type="checkbox" value="' + newSubcats[i][0] + '" checked=true>' +
          '<label for="">' + newSubcats[i][1] + '</label>' +
        '</div>' +
      '</div>';
    }

    newCheckboxes += '<div class="col-sm-12">' +
      '<div class="checkbox">' +
        '<input type="checkbox" class="js-uncheck-all" data-checked="true" checked="true">' +
        '<label>Check all</label>' +
      '</div>' +
    '</div>';

    subcatGroup.append(newCheckboxes);

    return true;
  }

  function generateNewSubcats() {
    $('.js-category-select').change(function() {
      var subcatGroup = '#js-subcategory-group-' + this.id.split('-')[1];
      displayNewSubcats($(subcatGroup), this.value);
    });

    $('.js-uncheck-all').change(function() {
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

  generateNewSubcats();

  $(addAnother).click(function() {
    var categorySelect = '';

    $.each(subcategories, function(key, value) {
      categorySelect += '<option value="' + key + '">' + key + '</option>';
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

  });

})();
