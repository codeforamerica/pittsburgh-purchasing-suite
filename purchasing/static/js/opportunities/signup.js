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
          '<input id="subcategories-"' + i + ' name="subcategories" type="checkbox" value="' + newSubcats[i] + '">' +
          '<label for="">' + newSubcats[i] + '</label>' +
        '</div>' +
      '</div>';
    }

    subcatGroup.append(newCheckboxes);

    return true;
  }

  function generateNewSubcats() {
    $('.js-category-select').change(function() {
      var subcatGroup = '#js-subcategory-group-' + this.id.split('-')[1];
      displayNewSubcats($(subcatGroup), this.value);
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
