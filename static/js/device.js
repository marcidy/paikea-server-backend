import { sanitize, delay, log } from './utils.js';
import { Upgrade } from './firmware.js';

function update( key, value ) {
    switch ( key ) {
        case "info":
            log( "info", value );
            break;
        case "error":
            log( "error", value );
            break;
        case "lora/msg":
            $( "#lora_messages" ).append( '<div class="lora-packet">' + sanitize(value) + '</div>' );
            break;
        case "rb/msg":
            out = JSON.stringify( value );
            $( "#rb_messages" ).append( '<div class="rb-packet">' + sanitize(out) +'</div>' );
            break;
        default:
            let sel = "#" + key.split( "/" ).join( "_" );
            $( sel ).text( value );
            $( sel ).change()
    }
}

class Device {

    constructor(host, iam) {
        this.host = host;
        this.iam = iam;
        this.connected = false;
        this.data = "";
        this.send_q = [];
        this.dev = '';
    }

    connect () {
        let self = this;
        let ws_addr = '';

        if ( window.location.host.indexOf('localhost') == 0 ) {
            ws_addr = 'ws://localhost:7770/' + this.iam;
        } else {
            ws_addr = 'wss://fqdn:port:7778/' + this.iam;
        }
        this.socket = new WebSocket( ws_addr );

        this.socket.onopen = function(e) {
            self.connected = true;
            let ii;
            let loops = self.send_q.length;
            for (ii = 0; ii < loops; ii++) {
                self.socket.send(self.send_q.shift());
            };

            self.send_q = [];
        };

        this.socket.onmessage = function(event) {
            let data = JSON.parse(event.data);
            const keys = Object.keys(data);

            keys.forEach((key, index) => {
                update(key, data[key]);

                if ( key === 'dev' ) {
                    self.dev = data['dev'];
                }
            });

        };

        this.socket.onclose = function(event) {
            if (event.wasClean) {
                alert(`[close] Connection closed=${event.code} reason=${event.reason}`);
            } else {
                alert('[close] Connection died');
            };
            self.connected = false;
        };

        this.socket.onerror = function(error){
            alert(`[error] ${error.message}`);
        };
    }

    req (item) {
        let out = JSON.stringify(['GET', item, []]);
        if (this.connected) {
            this.socket.send(out);
        } else {
            this.send_q.push(out);
        };
    }

    cmd (item, params=[]) {
        let out = JSON.stringify(['CMD', item, params]);
        if (this.connected) {
            this.socket.send(out);
        } else {
            this.send_q.push(out);
        };
    }

};

let path = window.location.pathname.split("/");
let iam = path[ path.length - 1];
let device = new Device(window.location.host, iam);
var upgrade = null;

$(function(){
    $(".card-header").click(function(){
        $(this).siblings().toggle();
    });

    $("#dev").change( () => {
        device.dev = $("#dev").text();
        $("#dev").off('change');

        upgrade = new Upgrade(device);
        upgrade.check();
    });

    device.connect();
    log("info", "Requesting network parameters");
    device.req('wifi');
    log("info", "Requesting device drivers");
    device.cmd('hal');

    $("#gps_running").change(function() {
        if ($("#gps_running").text() == "true") {
            $("#gps_toggle").text("Stop");
        } else {
            $("#gps_toggle").text("Start");
        };
    });

    $("#gps_enabled").change(function() {
        if ($("#gps_enabled").text() == "1") {
            $("#gps_enable").text("Disable");
        } else {
            $("#gps_enable").text("Enable");
        };
    });

    $("#rb_running").change(function() {
        if ($("#rb_running").text() == "true") {
            $("#rb_toggle").text("Stop");
        } else {
            $("#rb_toggle").text("Start");
        };
    });

    $("#rb_enabled").change(function() {
        if ($("#rb_enabled").text() == "1") {
            $("#rb_enable").text("Disable");
        } else {
            $("#rb_enable").text("Enable");
        };
    });

    $("#gps_toggle").click(function() {
        if ($(this).text() == "Start") {
            device.cmd('start_gps');
            $(this).text("Stop");
        } else {
            device.cmd('stop_gps');
            $(this).text("Start");
        };
    });

    $("#rb_toggle").click(function() {
        if ($(this).text() == "Start") {
            device.cmd('start_rb');
            $(this).text("Stop");
        } else {
            device.cmd('stop_rb');
            $(this).text("Start");
        };
    });

    $("#lora_toggle").click(function() {
        if ($(this).text() == "Start") {
            device.cmd('start_lora');
            $(this).text("Stop");
        } else {
            device.cmd('stop_lora');
            $(this).text("Start");
        };
    });

    $("#lora_running").change(function() {
        if ($("#lora_running").text() == "true") {
            $("#lora_toggle").text("Stop");
        } else {
            $("#lora_toggle").text("Start");
        };
    });

    $("#test_new_sta").click(function() {
        let msg = "This will disconnected the device from the server, and impact all connected clients."
        msg += "\n\nThe device will attempt to reconnect to the stored network on failure."
        msg += "\n\nYou will have to reload this page after this operation."
        msg += "\n\nProceed?"
        if (confirm(msg)) {
            let ssid = $("#ssid").val();
            let pword = $("#pass").val();
            device.cmd("test_new_sta", [ssid, pword]);
        }
    });

    $("#store_new_sta").click(function() {
        let msg = "This will save the wifi credentials on the device."
        msg += "\n\nIt will not be remotely recoverable if they are incorrect"
        msg += "\n\nThis will not force the device to disconnect, but it will take effect on reboot."
        msg += "\n\nProceed?"
        if (confirm(msg)) {
            let ssid = $("#ssid").val();
            let pword = $("#pass").val();
            device.cmd("store_new_sta", [ssid, pword]);
        }
    });

    $("#lora-send-msg").click(function() {
        let msg = $("#lora-text").val();
        $("#lora-text").val("");
        device.cmd("send_lora", [msg]);
    });

    $("#service").click(function() {
        let msg = "This will return the deice to it's primary mode on the next reset, disabling"
        msg += " the Support Interface.\n\nProceed?"
        if (confirm(msg)) {
            device.cmd("service");
        }
    });

    $("#switch-app").click(function() {
        let app = $("#app option:selected").val();
        device.cmd("switch_app", [app]);
    });

    $("#reset").click(function() {
        let msg = "This will reset the device.\n\nProceed?"
        if (confirm(msg)) {
            device.cmd("reset", []);
        }
    });
});
