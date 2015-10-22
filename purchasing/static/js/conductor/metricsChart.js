(function() {
  var dayInSeconds = 60 * 60 * 24;
  var defaultBuckets = {
    '< 1 day': 0, '< 7 days': 0, '8 - 15 days': 0,
    '16 - 30 days': 0, '30+ days': 0,
    order: ['< 1 day', '< 7 days', '8 - 15 days', '16 - 30 days', '30+ days']
  };

  function makeBuckets(stage) {
    var newBuckets = $.extend({}, defaultBuckets);
    stage.forEach(function(d) {
      switch (true) {
        case d < dayInSeconds: newBuckets['< 1 day'] += 1 ; break;
        case d < dayInSeconds * 7:  newBuckets['< 7 days'] += 1 ; break;
        case d < dayInSeconds * 15: newBuckets['8 - 15 days'] += 1 ; break;
        case d < dayInSeconds * 30: newBuckets['16 - 30 days'] += 1 ; break;
        default: newBuckets['30+ days'] += 1;
      }
    });
    return newBuckets;
  }

  function buildChartData(data, defaultObj, stageOrder) {
    var chartDataObj = {}, chartData = [];
    d3.map(data).forEach(function(ix, i) {
      return d3.map(i.stages).forEach(function(idx, d) {
        if (chartDataObj[d.id]) {
          chartDataObj[d.id].push(d.seconds);
        } else {
          chartDataObj[d.id] = [{name: d.name, id: d.id}, d.seconds];
        }
      });
    });

    d3.map(defaultObj).values().forEach(function(d, idx) {
      var stage = chartDataObj[d3.map(d).keys()[0]];
      if (stage) {
        chartData.push({
          category: {name: stage[0].name, id: stage[0].id},
          average: d3.mean(stage.slice(1).map(function(e) {
            return d3.round(e/dayInSeconds, 1);
          })),
          count: stage.slice(1).length,
          buckets: makeBuckets(stage.slice(1))
        });
      } else {
        var stageIdx = +d3.map(d).keys()[0];
        stage = defaultObj[stageOrder.indexOf(+stageIdx)][stageIdx];
        chartData.push({
          category: {name: stage.name, id: stage.id},
          buckets: makeBuckets([]),
          average: 0
        });
      }
    });

    return chartData;
  }

  function drawAverageChart(data) {
    return c3.generate({
      bindto: '#js-average-time-chart',
      padding: { bottom: 40 },
      data: {
        columns: [['Stages'].concat(data.map(function(d) { return d.average; }))], type: 'bar'
      },
      size: { height: 400 },
      axis: {
        x: { type: 'category', categories: data.map(function(d) { return d.category.name; }) },
        y: {
          label: { text: 'Average Days Spent in Stage', position: 'outer-middle' },
          format: '.1f'
        }
      },
      legend: { show: false },
      tooltip: {
        format: {
          value: function (value, ratio, id, index) {
            var formatter = d3.format('.1f');
            return formatter(value) + ' Days (' + data[index].count + ' contracts)';
          },
          name: function(name, ratio, id, index) { return data[index].category.name; },
          title: function(d) { return ''; }
        },
      }
    });
  }

  function drawBucketChart(data) {
    return c3.generate({
      bindto: '#js-contract-bucket-chart',
      padding: { bottom: 40 },
      data: {
        columns: defaultBuckets.order.map(function(d) {
          return [d].concat(data.map(function(e) {
            return e.buckets[d];
          }));
        }),
        type: 'bar',
        groups: [defaultBuckets.order]
      },
      color: {
        pattern: ['#feedde','#fdbe85','#fd8d3c','#e6550d','#a63603']
      },
      size: { height: 400 },
      axis: {
        x: { type: 'category', categories: data.map(function(d) { return d.category.name; }) },
        y: {
          label: { text: '# of Contracts Spent in Each Stage by Days', position: 'outer-middle'},
          format: 'f'
        }
      },
      order: null
    });
  }

  $.ajax({
    url: ajaxUrl,
  }).done(function(data, status, xhr) {

    var averageDaysChart = drawAverageChart(buildChartData(data.complete, data.stageDataObj, data.stageOrder));
    var bucketDaysChart = drawBucketChart(buildChartData(data.current, data.stageDataObj, data.stageOrder));

    $('#js-metrics-container').children('.chart-container').removeClass('hidden');
  }).fail(function() {
    $('#js-chart-error-container').html(
      '<div class="alert alert-danger alert-dismissible" role="alert">' +
        '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>' +
          'Something went wrong fetching the charts. We are working on it. Please try again later.' +
      '</div>'
    ).removeClass('hidden');
  }).complete(function() {
    $('#js-metrics-loading').addClass('hidden');
  });
})();
