'use strict';

/*global console:true, moment:true, Espresso: true, io: true, $: true*/

var DefaultChart = Espresso.extend(Object, {
    constructor: function (options, dom, initialData) {
        this.options = options;
        this.dom = dom;
        this.initialData = initialData;
        this.chart = null;

        this.init();
        this._redraw = this.chart.redraw;
    },
    init: _.noop,
    addPoint: _.noop,
    chart_defaults: {},
    disableRedraw: function () {
        this.chart.redraw = _.noop
    },

    enableRedraw: function () {
        this.chart.redraw = this._redraw;
        this.chart.redraw();
    },

    resize: function () {
        $(window).resize();
    }
});

var DefaultSensorChart = Espresso.extend(DefaultChart, {
    getPlotBandValues: function () {
        var vals = [
            this.options.min_possible_value,
            ifUndefinedUse(this.options.min_warning_value, this.options.min_possible_value),
            ifUndefinedUse(this.options.max_warning_value, this.options.max_possible_value),
            this.options.max_possible_value
        ];
        return [
            (vals[1] < vals[0] ? vals[1] : vals[0]),
            vals[1],
            vals[2],
            (vals[2] > vals[3] ? vals[2] : vals[3])];
    },
    plotBands: function () {
        var arr = this.getPlotBandValues();
        return [
            {
                from: arr[0],
                to: arr[1],
                color: '#3498DB'
            },
            {
                from: arr[1],
                to: arr[2],
                color: '#00BC8C'
            },
            {
                from: arr[2],
                to: arr[3],
                color: '#E74C3C'
            }
        ];
    },
    updatePlotBands: function () {

        var new_vals = this.getPlotBandValues();
        if (!arraysEqual(this.plotBandsValues, new_vals)) {
            this.chart.yAxis[0].update({
                min: new_vals[0],
                max: new_vals[new_vals.length - 1],
                plotBands: this.plotBands()
            });
            this.plotBandsValues = new_vals;
        }
    }
});

var SensorChart = Espresso.extend(DefaultSensorChart, {
    plotLines: function () {
        var arr = this.getPlotBandValues();
        return [
            {
                value: arr[1],
                color: '#3498DB',
                dashStyle: 'LongDash',
                width: 2
            },
            {
                value: arr[2],
                color: '#E74C3C',
                dashStyle: 'LongDash',
                width: 2
            }
        ]
    },
    updatePlotBands: function () {

        var new_vals = this.getPlotBandValues();
        if (!arraysEqual(this.plotBandsValues, new_vals)) {
            this.chart.yAxis[0].update({
                min: new_vals[0],
                max: new_vals[new_vals.length - 1],
                plotLines: this.plotLines()
            });
            this.plotBandsValues = new_vals;
        }
    },
    addPoint: function (data) {
        this._addPoint(data, 'ser');
        this.updatePlotBands();
        this.chart.redraw();
    },

    _addPoint: function (data, series_name) {
        // does not call redraw
        if (!isUndefined(data.x)) {
            var remove = false, series = this.chart.get(series_name);
            if (series.points.length > 0) {
                var first = series.points[0];
                if (moment().unix() - first.x > 24 * 60 * 60) {
                    remove = true;
                }
            }

            series.addPoint(
                this._getPoint(data.x, ifUndefinedUse(data.y, null)), false, remove);
        }
    },

    _getPoint: function (x, y) {
        //return {x:moment(x * 1000), y: y};
        return [x * 1000, y];
    },

    init: function () {
        this.plotBandsValues = [];
        var options = this.options,
            plot_bands = this.plotBands();
        $(this.dom).highcharts('StockChart', _.extend(this.chart_defaults, {
            chart: {
                zoomType: 'x'
            },
            xAxis: {
                type: 'datetime',
                title: {text: null},
                tickPixelInterval: 40,
                ordinal: true
            },
            yAxis: {
                min: this.options.min_possible_value,
                max: this.options.max_possible_value,
                tickPixelInterval: 30,
                title: {
                    text: null
                },
                labels: {
                    align: 'right',
                    x: -10,
                    formatter: function () {
                        return this.value + options.unit;
                    }
                }
            },
            series: [{
                id: 'ser',
                type: 'line',
                marker: {
                    enabled: false
                },
                name: this.options.description,
                color: plot_bands[1].color,
                zIndex: 5,
                width: 2,
                enableMouseTracking: false
                //pointInterval: this.options.step
            }],
            rangeSelector: {
                buttons: [
                    {
                        type: 'hour',
                        count: 1,
                        text: '1h'
                    },
                    {
                        type: 'hour',
                        count: 6,
                        text: '6h'
                    },
                    {
                        type: 'hour',
                        count: 12,
                        text: '12h'
                    },
                    {
                        type: 'hour',
                        count: 18,
                        text: '18h'
                    },
                    {
                        type: 'all',
                        text: 'All'
                    }
                ],
                inputEnabled: false, // it supports only days
                selected: 0
            },
            scrollbar: {
                enabled: false
            },
            navigator: {
                height: 20
            },
            title: {
                text: null
            },
            subtitle: {
                text: null
            },
            legend: {
                enabled: false
            }
        }));
        this.chart = $(this.dom).highcharts();
        this.init_data();
        this.updatePlotBands();
    },

    init_data: function () {
        if (isUndefined(this.initialData))
            return;

        var start = this.initialData.from,
            step = this.initialData.step,
            data = this.initialData.data,
            chart_data = {'ser': [], 'ser-min': [], 'ser-max': []},
            date;

        for (var i = 0, l = data.length; i < l; i++) {
            date = start + i * step;
            chart_data['ser'].push(this._getPoint(date, data[i]));
        }
        this.chart.get('ser').setData(chart_data['ser']);
    }

});

var SensorGauge = Espresso.extend(DefaultSensorChart, {
    addPoint: function (data) {
        var series = this.chart.get('ser');
        if (series.points.length === 0) {
            series.addPoint(data);
        }
        else {
            series.points[0].update(data);
        }
        this.updatePlotBands();
    },
    init: function () {
        this.plotBandsValues = [];
        var options = _.extend(this.chart_defaults, {
            chart: {
                type: 'gauge',
                margin: [0, 0, 0, 0]
            },
            title: {
                text: null
            },
            pane: {
                startAngle: -120,
                endAngle: 120,
                background: [
                    {
                        backgroundColor: 'rgba(255,255,255,0.1)'
                    }
                ],
                size: '100%',
                center: ['50%', '65%']
            },
            yAxis: {
                minorTickInterval: 'auto',
                minorTickWidth: 1,
                minorTickLength: 10,
                minorTickPosition: 'inside',
                minorTickColor: '#666',

                tickPixelInterval: 30,
                tickWidth: 2,
                tickPosition: 'inside',
                tickLength: 10,
                tickColor: '#666',

                labels: {
                    step: 2,
                    rotation: 'auto',
                    style: {
                        fontSize: '16px'
                    }
                },

                title: {
                    text: this.options.unit,
                    style: {
                        fontSize: '22px'
                    }
                }
            },
            series: [
                {
                    id: 'ser',
                    name: this.options.description,
                    data: [],
                    dataLabels: {
                        borderWidth: 0,
                        format: '<div style="text-align:center"><span style="font-size:30px;color:' +
                        ((Highcharts.theme && Highcharts.theme.contrastTextColor) || 'black') + '">{y} ' +
                        this.options.unit + '</span></div>'
                    },
                    tooltip: {
                        valueSuffix: this.options.unit
                    }
                }
            ]
        });
        $(this.dom).highcharts(options);
        this.chart = $(this.dom).highcharts();
        this.updatePlotBands();
    }

});
