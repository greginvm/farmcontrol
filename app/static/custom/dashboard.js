'use strict';

/*global console:true, moment:true, Espresso: true, io: true, $: true*/

var socket = socket || io.connect('http://' + document.domain + ':' + location.port + '/dashboard');

var ENTER_KEY = 13;
var ESC_KEY = 27;


var getDate = function (utc_timestamp) {
    return moment(utc_timestamp, 'X');
};

var formatDate = function (utc_timestamp) {
    if (isUndefined(utc_timestamp)) {
        return '';
    }
    return getDate(utc_timestamp).format();
};

var RelayState = {
    Off: 0, PendingOff: 1, On: 2, PendingOn: 3, Error: 4
};

var DefaultCollection = Espresso.Collection.extend({
    all: function () {
        return this.toArray();
    },
    update: function (data) {
        if (isUndefined(this.get(data))) {
            this.add(data);
        }
        else {
            this.set(data);
        }
    },

    add: function (data) {
        this.push(data);
    }
});

var DefaultLimitedSizeCollection = DefaultCollection.extend({
    max_length: 6,

    remove_first: function () {
        if (this.items.length > this.max_length) {
            this.splice(0, this.items.length - this.max_length)
        }

        return this.items.length;
    }

});

var NotificationCollection = DefaultLimitedSizeCollection.extend({
    push: function (data) {
        DefaultLimitedSizeCollection.prototype.push.call(this, data);
        this.items.sort(function (a, b) {
            return a.created_ts - b.created_ts;
        });

        var last_id = _.last(this.items).id;
        this.forEach(function (each) {
            this.set({id: each.id, is_first: last_id === each.id});
        }.bind(this));

        var length = DefaultLimitedSizeCollection.prototype.remove_first.call(this);
        this.all().reverse();
        return length;
    }

});

var SensorCollection = Espresso.extend(DefaultCollection, {
    idAttribute: 'sensor_code'
});

var Sensor = Espresso.Controller.extend({
    init: function () {
        var show_gauge = this.render_gauge(),
            show_chart = this.render_chart();

        this.set({show_gauge: show_gauge, show_chart: show_chart});
        this.gauge = null;
        this.chart = null;

        if (show_gauge) {
            this.gauge = new SensorGauge(this.model, this.ref.gauge);
        }

        if (show_chart) {
            this.chart = new SensorChart(this.model, this.ref.chart, this.model.history);
        }

        var read_ts = null, value = null;
        this.listenTo(this.model, 'change', function () {
            if ((read_ts !== this.model.read_ts || value !== this.model.value) &&
                (!isUndefined(this.model.read_ts) && !isUndefined((this.model.value)))) {
                read_ts = this.model.read_ts;
                value = this.model.value;
                if (this.render_gauge()) {
                    this.gauge.addPoint(this.model.value);
                }
                if (this.render_chart()) {
                    this.chart.addPoint({
                        y: this.model.value,
                        x: this.model.read_ts
                    });
                }
            }

        }.bind(this));

        $(this.ref.show_gauge_button).click(this.toggle_display_gauge.bind(this));
        $(this.ref.show_chart_button).click(this.toggle_display_chart.bind(this));

    },

    render_chart: function () {
        return !isVisibleOnDevice('xs') && !isVisibleOnDevice('sm') && window.charts_enabled;
    },

    render_gauge: function () {
        return !isVisibleOnDevice('xs') && window.charts_enabled;
    },

    show_chart: function () {
        return this.render_chart() && this.model.show_chart;
    },

    show_gauge: function () {
        return this.render_gauge() && this.model.show_gauge;
    },

    open_max_warning_value_edit: function () {
        this.ref.max_warning_input.focus();
        this.open_edit();
    },

    open_min_warning_value_edit: function () {
        this.ref.min_warning_input.focus();
        this.open_edit();
    },

    key: function (e) {
        if (e.which === ENTER_KEY) {
            this.confirm_edit();
        }
        else if (e.which === ESC_KEY) {
            this.cancel_edit();
            e.target.value = this.model.text;
        }
    },
    open_edit: function () {
        this.set({editing: true});
    },
    confirm_edit: function () {
        var pending_min = parseFloat(this.ref.min_warning_input.value),
            pending_max = parseFloat(this.ref.max_warning_input.value);
        if (isNaN(pending_min))
            pending_min = null;
        if (isNaN(pending_max))
            pending_max = null;
        if (this.model.min_warning_value !== pending_min) {
            this.set({pending_min_warning_input: true});
        }
        if (this.model.max_warning_value !== pending_max) {
            this.set({pending_max_warning_input: true});
        }
        this.set({editing: false});
        var data = {
            sensor_code: this.model.sensor_code,
            min_warning_value: pending_min,
            max_warning_value: pending_max,
            enable_warnings: this.ref.enable_warnings.checked,
            observable_measurements: parseInt(this.ref.observable_measurements.value),
            observable_alarming_measurements: parseInt(this.ref.observable_alarming_measurements.value),
            warning_wait_minutes: parseInt(this.ref.warning_wait_minutes.value)
        };
        sensor_store.set(data);
        socket.emit('sensor update warning values', this.model);
    },

    cancel_edit: function () {
        this.set({editing: false});
    },

    formatValue: function (key) {
        if (isUndefined(this.model[key]))
            return 'âˆž';
        return this.model[key] + this.model.unit;
    },

    warning_wait_minutes: function () {
        return this.model.warning_wait_minutes;
    },

    toggle_display_gauge: function (e) {
        var show = !(this.model.show_gauge === true);
        if (show) {
            this.gauge.enableRedraw();
        }
        else {
            this.gauge.disableRedraw();
        }
        this.set({show_gauge: show});
    },
    toggle_display_chart: function (e) {
        var show = !(this.model.show_chart === true);
        if (show) {
            this.chart.enableRedraw();
        }
        else {
            this.chart.disableRedraw();
        }
        this.set({show_chart: show});
        this.chart.resize();
    },
    toggle_warnings: function (e) {
        sensor_store.set({
            sensor_code: this.model.sensor_code,
            enable_warnings: !this.model.enable_warnings
        });
        socket.emit('sensor update warning values', this.model);
        return false;
    },
    render: function () {
        return {
            has_warning: {
                classList: {
                    'panel-default': this.model.has_warning !== true && this.model.has_notification !== true,
                    'panel-warning': this.model.has_warning === true && this.model.has_notification !== true,
                    'panel-danger': this.model.has_notification === true
                }
            },
            show_gauge_button: {
                display: this.render_gauge() === true
            },
            gauge: {display: this.model.show_gauge},
            show_chart_button: {
                display: this.render_chart() === true
            },
            chart: {display: this.model.show_chart},
            description: {html: this.model.description},
            min_warning_value: {
                text: this.formatValue('min_warning_value') + ((this.model.pending_min_warning_input === true) ? '*' : ''),  //this.model.min_warning_value + this.model.unit,
                ondblclick: this.open_min_warning_value_edit,
                display: this.model.editing !== true
            },
            max_warning_value: {
                text: this.formatValue('max_warning_value') + ((this.model.pending_max_warning_input === true) ? '*' : ''),  //ifUndefined(this.model.max_warning_value, '') + this.model.unit,
                ondblclick: this.open_max_warning_value_edit,
                display: this.model.editing !== true
            },
            min_warning_input: {
                value: this.model.min_warning_value,
                onkeydown: this.key,
                display: this.model.editing === true
            },
            max_warning_input: {
                value: this.model.max_warning_value,
                onkeydown: this.key,
                display: this.model.editing === true
            },
            enable_warnings: {
                checked: this.model.enable_warnings === true
            },
            enable_warnings_bell: {
                onclick: this.toggle_warnings,
                classList: {
                    'fa-bell': this.model.enable_warnings === true,
                    'fa-bell-slash': this.model.enable_warnings !== true,
                    'btn-warning': this.model.enable_warnings === true,
                    'btn-default': this.model.enable_warnings !== true
                }
            },
            observable_measurements: {
                value: this.model.observable_measurements,
                onkeydown: this.key
            },
            observable_alarming_measurements: {
                value: this.model.observable_alarming_measurements,
                onkeydown: this.key
            },
            warning_wait_minutes: {
                value: this.warning_wait_minutes(),
                onkeydown: this.key
            },
            value: {html: this.formatValue('value')},
            read_ts: {html: formatDate(this.model.read_ts)},
            enable_form: {
                onkeydown: this.key,
                display: this.model.editing === true
            },
            open_edit: {
                display: this.model.editing !== true,
                onclick: this.open_edit
            },
            confirm_edit: {
                display: this.model.editing === true,
                onclick: this.confirm_edit
            },
            cancel_edit: {
                display: this.model.editing === true,
                onclick: this.cancel_edit
            }
        };
    }
});

var Relay = Espresso.Controller.extend({
    init: function () {
    },
    toggle_on: function () {
        this.toggle_switch(RelayState.PendingOn);
        return false;
    },
    toggle_off: function () {
        this.toggle_switch(RelayState.PendingOff);
        return false;
    },
    toggle_switch: function (state) {
        if (this.model.editing === true) {
            relay_store.update({id: this.model.id, state: state});
            socket.emit('relay switch', this.model);
        }
    },
    refresh_state: function () {
        relay_store.update({id: this.model.id, pending_refresh: true});
        socket.emit('relay refresh state', this.model);
        return false;
    },
    render: function () {
        return {
            description: {html: this.model.description + ' (' + this.model.arduino_pin + ')'},
            changed_ts: {html: formatDate(this.model.changed_ts)},
            refresh_state: {
                classList: {
                    'btn-warning': this.model.pending_refresh === true,
                    'btn-default': this.model.pending_refresh !== true
                },
                onclick: this.refresh_state
            },
            switch_on: {
                html: this.model.switch_on_text,
                classList: {
                    'btn-default': !_.include([RelayState.On, RelayState.PendingOn, RelayState.Error], this.model.state),
                    'btn-info': this.model.state === RelayState.On,
                    'btn-warning': this.model.state === RelayState.PendingOn,
                    'btn-danger': this.model.state === RelayState.Error,
                    'disabled': this.model.is_initialized === false
                },
                onclick: this.toggle_on
            },

            switch_off: {
                html: this.model.switch_off_text,
                classList: {
                    'btn-default': !_.include([RelayState.Off, RelayState.PendingOff, RelayState.Error], this.model.state),
                    'btn-primary': this.model.state === RelayState.Off,
                    'btn-warning': this.model.state === RelayState.PendingOff,
                    'btn-danger': this.model.state === RelayState.Error,
                    'disabled': this.model.is_initialized === false
                },
                onclick: this.toggle_off
            }
        };
    }
});

var Notification = Espresso.Controller.extend({
    init: function () {
        this.set_is_first_render();
        this.listenTo(this.model, 'change', this.set_is_first_render.bind(this));

        this.interval = setInterval(function () {
            if (isUndefined(notification_store.get({id: this.model.id}))) {
                clearInterval(this.interval);
            }
            this.render();
        }.bind(this), 30 * 1000);
    },

    set_is_first_render: function () {
        if (this.model.is_first) {
            $(this.ref.is_first).parent().addClass('list-group-item-danger');
        }
        else {
            $(this.ref.is_first).parent().removeClass('list-group-item-danger');
        }
    },

    render: function () {
        return {
            text: {html: this.model.text},
            badge: {html: formatDate(this.model.created_ts)},
            icon: {classList: {'fa': true, 'fa-fw': true, 'fa-comment': true}},
            is_first: {},
            time_ago: {html: getDate(this.model.created_ts).fromNow()}
        };
    }
});

var Call = Espresso.Controller.extend({
    hang: function () {
        socket.emit('call cancel', this.model);
    },
    render: function () {
        return {
            phone: {html: this.model.id},
            hang: {onclick: this.hang}
        }

    }
});

var Contact = Espresso.Controller.extend({

    init: function () {
        this.toggle_switch(this.ref.enable_email_warnings, this.model.enable_email_warnings);
        this.toggle_switch(this.ref.enable_sms_warnings, this.model.enable_sms_warnings);
        this.toggle_switch(this.ref.enable_phone_call_warnings, this.model.enable_phone_call_warnings);
        $(this.ref.enable_sms_warnings).change(this.toggleSms.bind(this));
        $(this.ref.enable_email_warnings).change(this.toggleEmail.bind(this));
        $(this.ref.enable_phone_call_warnings).change(this.toggleCalls.bind(this));
    },

    toggleSms: function (e) {
        this.set_toggle('enable_sms_warnings', e.target.checked);
    },

    toggleEmail: function (e) {
        this.set_toggle('enable_email_warnings', e.target.checked);
    },

    toggleCalls: function (e) {
        this.set_toggle('enable_phone_call_warnings', e.target.checked);
    },

    toggle_switch: function (ref, toggle) {
        $(ref).bootstrapToggle(toggle ? 'on' : 'off');
    },

    set_toggle: function (key, toggle) {
        var data = {id: this.model.id};
        data[key] = toggle === true;
        contacts_store.set(data);
        socket.emit('contact notification update', this.model);
    },

    getEmailToggle: function () {
        this.toggle_switch(this.ref.enable_email_warnings, this.model.enable_email_warnings);
        return this.model.enable_email_warnings;
    },

    getSmsToggle: function () {
        this.toggle_switch(this.ref.enable_sms_warnings, this.model.enable_sms_warnings);
        return this.model.enable_sms_warnings;
    },

    getCallsToggle: function () {
        this.toggle_switch(this.ref.enable_phone_call_warnings, this.model.enable_phone_call_warnings);
        return this.model.enable_phone_call_warnings;
    },

    key: function (e) {
        if (e.which === ENTER_KEY) {
            this.confirm_edit();
        }
        else if (e.which === ESC_KEY) {
            this.cancel_edit();
            e.target.value = this.model.text;
        }
    },
    open_edit: function () {
        this.set({editing: true});
    },
    confirm_edit: function () {
        var call_wait_minutes = parseInt(this.ref.call_wait_minutes.value);
        if (isNaN(call_wait_minutes))
            call_wait_minutes = null;

        var data = {id: this.model.id, pending: true, editing: false, call_wait_minutes: call_wait_minutes};
        contacts_store.set(data);

        socket.emit('contact notification update', data);
    },

    cancel_edit: function () {
        this.set({editing: false});
    },

    render: function () {
        return {
            name: {text: this.model.name + ((this.model.pending === true) ? '*' : '')},
            phone: {html: '<i class="fa fa-comment-o"></i>' + this.model.phone},
            phone_call: {html: '<i class="fa fa-phone"></i>' + this.model.phone},
            email: {html: '<i class="fa fa-envelope"></i>' + this.model.email},
            enable_sms_warnings: {checked: this.getSmsToggle()},
            enable_email_warnings: {checked: this.getEmailToggle()},
            enable_phone_call_warnings: {checked: this.getCallsToggle()},
            last_phone_call: {html: formatDate(this.model.last_phone_call_ts)},
            next_available_phone_call: {html: formatDate(this.model.next_available_phone_call)},
            call_wait_minutes_text: {
                html: this.model.call_wait_minutes
            },
            call_wait_minutes: {
                value: this.model.call_wait_minutes,
                onkeydown: this.key,
                display: this.model.editing === true
            },
            enable_form: {
                onkeydown: this.key,
                display: this.model.editing === true
            },
            open_edit: {
                display: this.model.editing !== true,
                onclick: this.open_edit
            },
            confirm_edit: {
                display: this.model.editing === true,
                onclick: this.confirm_edit
            },
            cancel_edit: {
                display: this.model.editing === true,
                onclick: this.cancel_edit
            }
        };
    }
});

var FarmaApp = Espresso.Controller.extend({
    init: function () {
        this.sensor_list = new Espresso.List(Sensor);
        this.listenTo(sensor_store, 'change', this.render);
        this.listenTo(sensor_store, 'change', this.render_datgui);

        this.relay_list = new Espresso.List(Relay);
        this.listenTo(relay_store, 'change', this.render);

        $(this.ref.toggle_relays_locked).prop('checked', false).change();
        $(this.ref.toggle_relays_locked).change(this.toggle_locked.bind(this));

        this.notification_list = new Espresso.List(Notification);
        this.listenTo(notification_store, 'change', this.render);

        this.contact_list = new Espresso.List(Contact);
        this.listenTo(contacts_store, 'change', this.render);

        this.calls_list = new Espresso.List(Call);
        this.listenTo(calls_store, 'change', this.render);

        socket.on('initial data', this.init_data.bind(this));
    },
    init_data: function (data) {
        var i, l;
        for (i = 0, l = data.sensors.length; i < l; i++) {
            sensor_store.push(data.sensors[i]);
        }
        for (i = 0, l = data.relays.length; i < l; i++) {
            relay_store.push(data.relays[i]);
        }
        for (i = 0, l = data.contacts.length; i < l; i++) {
            contacts_store.push(data.contacts[i]);
        }
        for (i = 0, l = data.notifications.length; i < l; i++) {
            notification_store.push(data.notifications[i]);
        }
        for (i = 0, l = data.calls.length; i < l; i++) {
            calls_store.push(data.calls[i]);
        }


        $(window).resize();
        this.init_socket_events();
        socket.removeAllListeners('initial data')
    },
    init_socket_events: function () {
        socket.on('sensor update', function (data) {
            sensor_store.update(data);
        });
        socket.on('sensor update warning values', function (data) {
            sensor_store.update(data);
        });

        socket.on('relay update', function (data) {
            relay_store.update(data);
        });

        socket.on('relay switch', function (data) {
            relay_store.update(data);
        });

        socket.on('notification update', function (data) {
            notification_store.update(data);
        });

        socket.on('contact update', function (data) {
            contacts_store.update(data);
        });

        socket.on('call in progress', function (data) {
            calls_store.update(data);
        });

        socket.on('call ended', function (data) {
            calls_store.remove({id: data.id});
        });
    },

    toggle_locked: function () {
        var checked = $(this.ref.toggle_relays_locked).prop('checked') === true;
        relay_store.forEach(function (relay, i) {
            relay_store.update({id: relay.id, editing: checked});
        });
    },

    render: function () {
        return {
            sensor_list: this.sensor_list.set(sensor_store.all()),
            relay_list: this.relay_list.set(relay_store.all()),
            notification_list: this.notification_list.reset(notification_store.all()),
            contact_list: this.contact_list.set(contacts_store.all()),
            calls: this.calls_list.set(calls_store.all())
        };
    },
    render_datgui: function () {
        datgui.render();
    }
});

var SensorDummy = function (sensor) {
    this.sensor_code = sensor.sensor_code;
    this.value = 0;
    this.min_warning_value = sensor.min_warning_value;
    this.max_warning_value = sensor.max_warning_value;

};

SensorDummy.prototype.emit = function () {
    var self = this;
    var d = {
        sensor_code: self.sensor_code,
        value: self.value,
        min_possible_value: self.min_possible_value,
        max_possible_value: self.max_possible_value
    };
    console.log('apply dummy', d);
    socket.emit('apply dummy', d);
};

var FarmaDatGui = Espresso.extend(Object, {
    constructor: function () {
        this.gui = null;
        console.log('Init dat gui');
        if (window.FarmaAppDebug === true) {
            console.log('Init dat gui - debug mode');
            this.gui = new dat.GUI();
        }
        this.sensors_controllers = {};
    },
    render: function () {
        if (isUndefined(this.gui)) {
            return 0;
        }
        for (var i = 0, l = sensor_store.count(); i < l; i++) {
            var s = sensor_store.get(i);
            if (!_.has(this.sensors_controllers, s.sensor_code)) {
                var ds = new SensorDummy(s);
                var f = this.gui.addFolder(s.description);

                var c = f.add(ds, 'value').min(s.min_possible_value).max(s.max_possible_value).step(1);
                c.onFinishChange(function (val) {
                    ds.emit();
                });

                f.open();

                this.sensors_controllers[s.sensor_code] = ds;
            }
        }
    }

});

var sensor_store = new SensorCollection();
var relay_store = new DefaultCollection();
var notification_store = new NotificationCollection();
var contacts_store = new DefaultCollection();
var calls_store = new DefaultCollection();
var datgui = new FarmaDatGui();

window.FarmaApp = new FarmaApp({view: document.getElementById('farma-temp-app')});


