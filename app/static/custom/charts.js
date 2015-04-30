$(function () {
    $.getJSON('history.json', function (obj) {
        var series_data = obj.series, series = [],
            yAxes_data = obj.yAxes, yAxes = [],
            yAxes_top_padding = 5,
            unit_map = {};
        var afterSetExtremes = function (yAxis, doAllYAxes) {
            if (isUndefined(yAxis) && doAllYAxes === true) {
                var chart = $('#main_chart').highcharts();
                _.each(yAxes_data, function (each) {
                    afterSetExtremes(chart.get(each.label), false);
                });
            }
            if (!isUndefined(yAxis)) {
                var ex = yAxis.getExtremes();
                yAxis.update({
                    plotBands: [{
                        color: '#3C3C3C',
                        from: ifUndefinedUse(ex.min, ex.dataMin, ex.min + (ex.dataMin - ex.min) * .1),
                        to: ifUndefinedUse(ex.max, ex.dataMax, ex.max - (ex.max - ex.dataMax) * .1),
                        label: {
                            text: yAxis.options.title.text,
                            align: 'center',
                            verticalAlign: 'center',
                            style: {
                                color: '#fff',
                                backgroundColor: '#3C3C3C',
                                fontSize: '200%',
                                fontWeight: 'bold'
                            }
                        }
                    }]
                });
            }
        };
        _.each(yAxes_data, function (yAxis_data, index) {
            var yAxis = {
                id: yAxis_data.label,
                labels: {
                    align: 'right',
                    x: -3
                },
                gridLineDashStyle: 'longdash',
                events: {
                    afterSetExtremes: function () {
                        afterSetExtremes(this, false);
                    }
                },
                title: {
                    text: yAxis_data.label
                },
                height: (100 / yAxes_data.length),
                top: 0,
                offset: 0,
                format: '{value} ' + yAxis_data.unit,
                lineWidth: 2
            };
            if (index > 0) {
                yAxis.height -= yAxes_top_padding;
                yAxis.top = (index * 100 / yAxes_data.length) + yAxes_top_padding;
            }

            yAxis.height += '%';
            yAxis.top += '%';

            unit_map[yAxis_data.label] = yAxis_data.unit;

            yAxes.push(yAxis);

        });
        _.each(series_data, function (serie_data, index) {
            var chart_data = serie_data.data;
            var serie = {
                type: 'line',
                name: serie_data.name,
                yAxis: serie_data.yAxis,
                data: chart_data,
                width: 2,
                unit: unit_map[serie_data.yAxis],
                enableMouseTracking: true,
                tooltip: {
                    valueDecimals: 2
                },
                dataGrouping: {
                    groupPixelWidth: 30
                }
            };

            series.push(serie);

        });
        $('#main_chart').highcharts('StockChart', {
            chart: {
                zoomType: 'x',
                backgroundColor: '#222',
                events: {
                    load: function () {
                        afterSetExtremes(undefined, true);
                    }
                }
            },
            rangeSelector: {
                selected: 1
            },

            title: {
                text: null
            },
            legend: {
                enabled: true
            },
            tooltip: {
                shared: true,
                formatter: function () {
                    var s = '<b>' + moment(this.x).format() + '</b>';
                    $.each(this.points, function () {
                        s += '<br/><span style="color:' + this.series.color + ';">\u25CF</span>' + this.series.name + ': '
                        + '<b>' + this.y.toFixed(2) + '</b>' + this.series.options.unit;
                    });

                    return s;
                },
            },
            xAxis: {
                type: 'datetime',
                title: {text: null},
                events: {
                    afterSetExtremes: function () {
                        afterSetExtremes(undefined, true);
                    }
                }
            },
            yAxis: yAxes,
            series: series
        });

        $(window).resize();
    });
});