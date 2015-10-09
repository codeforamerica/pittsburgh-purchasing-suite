(function() {
  var dayInSeconds = 60 * 60 * 24;
  var defaultBuckets = {
    '< 1 day': 0, '< 7 days': 0, '8 - 15 days': 0,
    '16 - 30 days': 0, '30+ days': 0,
    order: ['< 1 day', '< 7 days', '8 - 15 days', '16 - 30 days', '30+ days']
  };

  function buildChartData(data) {
    var chartDataObj = {}, chartData = [];
    d3.map(data).forEach(function(ix, i) {
      return d3.map(i.stages).forEach(function(idx, d) {
        if (chartDataObj[d.name]) {
          chartDataObj[d.name].push(d.seconds);
        } else {
          chartDataObj[d.name] = [{name: d.name, id: d.id}, d.seconds];
        }
      });
    });

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

    d3.map(chartDataObj).values().forEach(function(d) {
      chartData.push({
        category: {name: d[0].name, id: d[0]},
        average: d3.mean(d.slice(1).map(function(e) {
          return d3.round(e/dayInSeconds, 1);
        })),
        count: d.slice(1).length,
        buckets: makeBuckets(d.slice(1))
      });
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
      size: { height: 400 },
      axis: {
        x: { type: 'category', categories: data.map(function(d) { return d.category.name; }) },
        y: {
          label: { text: '# of Contracts Spent in Each Stage by Days', position: 'outer-middle'},
          format: 'f'
        }
      },
    });
  }

  $.ajax({
    url: ajaxUrl,
  }).done(function(data, status, xhr) {

    currentData = buildChartData(data.current);
    completeData = buildChartData(data.complete);

    var averageDaysChart = drawAverageChart(completeData);
    var bucketDaysChart = drawBucketChart(currentData);

  }).fail(function() {

  });
})();
