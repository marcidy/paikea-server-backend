import { sanitize } from './utils.js';

var api_base;

if ( window.location.host.indexOf('localhost') == 0 ) {
    api_base = 'http://' + window.location.host + '/v1';
} else {
    api_base = 'https://' + window.location.host + '/v1';
}

const update = (data, objData) => {
    for (let new_obj in data) {
        objData[data[new_obj]['id']] = data[new_obj];
    }
};


async function fetchAndDecode( url, type ) {
    let response =  await fetch(api_base + url);
    let content;

    if ( !response.ok ) {
        throw new Error(`HTTP error! status: ${response.status}`);
    } else {
        if ( type === 'blob') {
            content = await response.blob();
        } else if ( type === 'json' ) {
            content = await response.json();
        } else if ( type === 'text' ) {
            content = await response.text();
        }
    }

    return content;
}

function log( level, item ) {
    let log_window = $( '#messages' );
    log_window.append( '<span class="' + level +'">' + sanitize( item ) + '</span><br >' );
    $('#messages').scrollTop( $('#messages')[0].scrollHeight);
}


function handleServerErrors( errors ) {

    for ( let item of errors ) {
        log( 'error', item );
    }   
}

class Table {
    constructor(ep, dom_id) {
        this.visible_ids = new Set()
        this.items = {};
        this.ep = ep;
        this.dom_id = dom_id;
        this.form_data = {};
    }

    async get() {
        let data = await fetchAndDecode( this.ep, 'json').then( data => update( data, this.items ) );
    }

    readTable() {
        var visible_items = $( this.dom_id ).children();

        $.each(visible_items, (i, item ) => {
            this.visible_ids.add(item.children[0].textContent);
        });
    }

    updateTable() {
        this.readTable();

        $( this.dom_id ).empty();
        this.visible_ids.clear();

        $.each(this.items, ( i, item ) => {
            $( this.dom_id ).append( this.renderItem( item ) );
            this.visible_ids.add( item.id + '');
        });

    }

    rederItem( item ) {
        return ''
    }

    renderFormFields() {
        return '';
    }

    getFormData() {
    }

    onFormChanges() {
    }

    onTableActions() {
    }

    renderForm() {
        this.getFormData();

        let html = "";
        html += '<div id="' + this.dom_id + '-form">';
        html += this.renderFormFields();
        html += '</div>';

        $( this.dom_id + '-form-area' ).empty();
        $( this.dom_id + '-form-area' ).append( html );

        this.getFormData();
        this.onTableActions();
        this.onFormChanges();
    }
}


class ModemTable extends Table {
    constructor(ep, dom_id) {
        super(ep, dom_id);
    }

    renderItem( item ) {
        let html = "";
        html += '<tr id="modem-' + item.id + '">';
        html += '<td>' + item.id + '</td>' ;
        html += '<td>' + item.imei + '</td>';
        html += '<td>' + item.serial + '</td>';
        html += '<td>' + item.device_type + '</td>';
        html += '</tr>';
        return html
    }
}

class QueueTable extends Table {
    constructor(ep, dom_id) {
        super(ep, dom_id);
    }

    renderItem( item ) {
        let html = "";
        html += '<tr id="queue-' + item.id + '">';
        html += '<td>' + item.id + '</td>';
        html += '<td>' + item.queue_name + '</td>';
        html += '<td>' + item.url + '</td>';
        html += '</tr>';
        return html
    }
}

class BuoyTable extends Table {
    constructor( ep, dom_id, modems ) {
        super( ep, dom_id );
        this.modems = modems;
    }

    renderItem( item ) {
        let html = "";
        html += '<tr id="buoy-' + item.id + '">';
        html += '<td>' + item.id + '</td>';
        html += '<td>' + item.iam + '</td>';
        if ( this.modems[item.rb_id] ) {
            html += '<td>' + this.modems[item.rb_id].serial + '</td>';
            html += '<td><button class="table-button" id="unlink-buoy-' + item.id + '">Unlink</button></td>';
        } else {
            html += '<td>' + this.renderModemSelect( item.id ) + '</td>';
            html += '<td>'
            html += '<button class="table-button" id="link-buoy-' + item.id + '">Link</button>';
            html += '<button class="table-button" id="delete-buoy-' + item.id + '">Delete</button>';
            html += '</td>';
        }
        html += '</tr>';
        return html;
    }

    renderModemSelect(item_id) {
        let html = '';

        if ( item_id ) {
            html += '<select name="buoy-new-modem-select" id="buoy-new-modem-select-' + item_id + '">';
        } else {
            html += '<select name="buoy-new-modem-select" id="buoy-new-modem-select">';
        }

        for ( const [mid, modem] of Object.entries(this.modems) ) {
            if ( modem.device_type == null || modem.device_type === '') {
                html += '<option value="' + mid +'">' + modem.serial + '</option>';
            }
        }
        html += '</select>';
        return html
    }

    renderFormFields() {
        let html = "";
        html += '<table class="form-table"><tr>'
        html += '<td><label for="label">Label:</label></td>';
        html += '<td><input type="text" id="buoy-new-label" name="buoy-new-label"></td>';
        html += '</tr><tr>';
        html += '<td><label for="buoy-modem">Modem:</label></td>';
        html += '<td>' + this.renderModemSelect() + '</tr>'
        html += '</tr></table>';
        html += '<button id="submit-new-buoy">Create new Buoy</button>';
        return html
    }

    getFormData() {
        this.form_data['iam'] = $( '#buoy-new-label' ).val();
        this.form_data['mid'] = $( '#buoy-new-modem-select' ).val();
    }

    async addNewBuoy() {
        this.getFormData();
        
        const data = {
            'iam': this.form_data['iam'],
            'modem': this.form_data['mid'],
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/create', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'New Buoy Added!');
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content );
        }
    }

    async linkModem( buoy_id, modem_id) {
        const data = {
            'id': buoy_id,
            'modem': modem_id
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/link', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'Buoy ' + buoy_id + ' and Modem ' + modem_id + ' linked.');
            init();
            return
        } else {
            let content = await response.json();
            handleServerErrors(content.errors);
        }
    }

    async unlinkItem( item ) {
        const data = {
          'id': item
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/unlink', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'Buoy ' + item + ' Unlinked.');
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content.errors );
        }

    }

    async deleteBuoy( dev_id ){
        const data = {
            'id': dev_id
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/delete', options );
        let code = response.status

        if ( code == 200 ) {
            log('info', 'Buoy ' + dev_id + ' Deleted.');
            delete this.items[dev_id];
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content.errors );
        }
    }

    onFormChanges() {
        $( '#submit-new-buoy' ).off('click');
        $( '#submit-new-buoy').click( () => {
            this.addNewBuoy();
        });
    }

    onTableActions() {
        this.readTable();
        
        for ( let item of this.visible_ids ) {
           if ( $( '#unlink-buoy-' + item ) ) {
               console.log( '#unlink-buoy-' + item );
               $( '#unlink-buoy-' + item ).off('click');
               $( '#unlink-buoy-' + item ).click( () => {
                   this.unlinkItem(item);
                });
           }
           if ( $( '#link-buoy-' + item ) ) {
               $( '#link-buoy-' + item ).off('click');
               $( '#link-buoy-' + item ).click( () => {
                   let modem_id = $( '#buoy-new-modem-select-' + item + ' option:selected').val();
                   this.linkModem(item, modem_id);
                });
           }
           if ( $( '#delete-buoy-' + item ) ) {
               $( '#delete-buoy-' + item ).off('click');
               $( '#delete-buoy-' + item ).click( () => {
                   this.deleteBuoy( item );
                });
           }
        }
    }
}


class HandsetTable extends Table {
    constructor( ep, dom_id, modems ) {
        super( ep, dom_id );
        this.modems = modems;
    }

    renderItem( item ) {
        let html = "";
        html += '<tr id="handset-' + item.id + '">';
        html += '<td>' + item.id + '</td>';
        html += '<td>' + item.iam + '</td>';
        if ( this.modems[item.rb_id] ) {
            html += '<td>' + this.modems[item.rb_id].serial + '</td>';
            html += '<td><button class="table-button" id="unlink-handset-' + item.id + '">Unlink</button></td>';
        } else {
            html += '<td>' + this.renderModemSelect(item.id) + '</td>';
            html += '<td>'
            html += '<button class="table-button" id="link-handset-' + item.id + '">Link</button>'
            html += '<button class="table-button" id="delete-handset-' + item.id + '">Delete</button>'
            html +='</td>';
        }
        html += '</tr>';
        return html;
    }

    renderModemSelect(item_id) {
        let html = '';

        if ( item_id ) {
            html += '<select name="handset-new-modem-select" id="handset-new-modem-select-' + item_id + '">';
        } else {
            html += '<select name="handset-new-modem-select" id="handset-new-modem-select">';
        }
        for ( const [mid, modem] of Object.entries(this.modems) ) {
            if ( modem.device_type == null || modem.device_type === '' ) {
                html += '<option value="' + mid +'">' + modem.serial + '</option>';
            }
        }
        html += '</select>';
        return html;
    }

    renderFormFields() {
        let html = "";
        html += '<table class="form-table"><tr>';
        html += '<td><label for="label">Label:</label></td>';
        html += '<td><input type="text" id="handset-new-label" name="handset-new-label"></td>';
        html += '</tr><tr>';
        html += '<td><label for="handset-modem">Modem:</label></td>';
        html += '<td>' + this.renderModemSelect() + '</td>';
        html += '</tr></table>';
        html += '<button id="submit-new-handset">Create new Handset</button>';

        return html;
    }

    getFormData() {
        this.form_data['iam'] = $( '#handset-new-label' ).val();
        this.form_data['mid'] = $( '#handset-new-modem-select' ).val();
    }

    async addNewHandset() {
        this.getFormData();

        const data = {
            'iam': this.form_data['iam'],
            'modem': this.form_data['mid'],
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/create', options );
        let code = response.status

        if ( code == 200 ) {
            log('info', 'New Handset Added!');
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content );
        }
    }

    async linkModem( handset_id, modem_id) {
        const data = {
            'id': handset_id,
            'modem': modem_id
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/link', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'Handset ' + handset_id + ' and Modem ' + modem_id + ' linked.');
            init();
            return
        } else {
            let content = await response.json();
            handleServerErrors(content.errors);
        }
    }

    async unlinkItem( item ) {
        const data = {
          'id': item
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/unlink', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'Handset ' + item + ' Unlinked.');
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content.errors );
        }
    }

    async deleteHandset( dev_id ) {
        const data = {
            'id': dev_id
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/delete', options );
        let code = response.status;
        
        if ( code == 200 ) {
            log('info', 'Handset ' + dev_id + ' Deleted.');
            delete this.items[dev_id];
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content.errors );
        }
    }

    onFormChanges() {
        $( '#submit-new-handset' ).off('click');
        $( '#submit-new-handset' ).click( () => {
            this.addNewHandset();
        });
    }

    onTableActions() {
        this.readTable();
        
        for ( let item of this.visible_ids ) {
           if ( $( '#unlink-handset-' + item ) ) {
               $( '#unlink-handset-' + item ).click( () => {
                   this.unlinkItem(item);
                });
           }
            if ( $( '#link-handset-' + item ) ) {
                $( '#link-handset-' + item ).click( () => {
                    let modem_id = $( '#handset-new-modem-select-' + item + ' option:selected').val();
                    this.linkModem(item, modem_id);
                });
            }
            if ( $( '#delete-handset-' + item ) ) {
                $( '#delete-handset-' + item ).click( () => {
                    this.deleteHandset( item );
                });
            }
        }
    }
}


class RouteTable extends Table {
    constructor( ep, dom_id, modems, queues ) {
        super( ep, dom_id );
        this.modems = modems;
        this.queues = queues;
    }

    labeler (device_type, d_id) {
        // based on object type, turn object ID into a descriptor
        if ( device_type === 'handset' || device_type === 'buoy' ) { 
            return this.modems[d_id].serial;
        } else if ( device_type == 'sqs' ) {
            return this.queues[d_id].queue_name;
        }
    }

    renderTableEnabled( item ) {
        let html = '';

        html += '<input id="route-enabled-' + item.id + '" name="route-enabled-' + item.id + '" type="checkbox" ';

        if ( item.enabled ) {
            html += 'checked="true"';
        }

        html += '>';
        return html;
    }

    renderItem( item ) {
        let html = "";
        html += '<tr class="endpoint-route">';
        html += '<td>' + this.renderTableEnabled( item ) + '</td>';
        html += '<td class="id">' + item.id + '</td>';
        html += '<td class="device-type">' + item.source_device_type + '</td>';
        html += '<td>' + this.labeler(item.source_device_type, item.source_device) + '</td>';
        html += '<td class="source-device">' + item.source_device + '</td>';
        html += '<td>' + item.msg_type + '</td>';
        html += '<td>' + item.endpoint_type + '</td>';
        html += '<td>' + this.labeler(item.endpoint_type, item.endpoint_id) + '</td>';
        html += '<td>' + item.endpoint_id + '</td>';
        html += '<td><button class="table-button" id="delete-route-' + item.id + '">Delete</button></td>';
        html += '</tr>'
        return html;
    }


    renderEnabled() {
        let html = '';

        if ( this.form_data['enabled'] ) {
            html += '<input id="route-enabled" name="route-enabled" type="checkbox" checked="true">';
        } else {
            html += '<input id="route-enabled" name="route-enabled" type="checkbox" >';
        }
        return html;
    }

    renderSourceDeviceType() {
        let html = '';

        let dev_type = $( '#route-source-device-type-select option:selected' ).val();

        html += '<select name="route-source-device-type-select" id="route-source-device-type-select">';

        if ( dev_type != 'buoy' && dev_type != 'handset' ) {
            html += '<option value="" disabled selected>Select a Type </option>';
        }
        if ( dev_type === 'buoy' ) {
            html += '<option value="buoy" selected>Buoy</option>';
        } else {
            html += '<option value="buoy">Buoy</option>';
        }
        if ( dev_type === 'handset' ) {
            html += '<option value="handset" selected>Handset</option>';
        } else {
            html += '<option value="handset">Handset</option>';
        }
        html += '</select>';

        return html;
    }

    renderSourceDeviceID() {
        let html = '';
        let dev_type = $( '#route-source-device-type-select option:selected' ).val();
        let dev_label = $( '#route-source-device-label option:selected' ).val();

        for ( const [mid, modem] of Object.entries(this.modems) ) {
            if (modem.serial === dev_label && modem.device_type === dev_type) {
                html += modem.id + '' ;
            }
        }
        
        return html;
    }

    renderSourceDeviceLabel() {
        let html = "";
        let options = "";
        let def_opt = false;
        let dev_type = $( '#route-source-device-type-select option:selected' ).val();
        let dev_label = $( '#route-source-device-label option:selected' ).val();

        html += '<select name="route-source-device-label" id="route-source-device-label">';

        if ( dev_label === '' || dev_label == null ) {
            options += '<option selected disabled value="">Select a Modem</option>';
            def_opt = true;
        }
        for ( const [mid, modem] of Object.entries(this.modems) ) {
            if ( modem.device_type === dev_type ) {
                if ( modem.serial === dev_label ){
                    options += '<option value="' + modem.serial +'" selected>' + modem.serial + '</option>';
                    def_opt = true;
                } else {
                    options += '<option value="' + modem.serial +'">' + modem.serial + '</option>';
                }
            }
        }
        if ( !def_opt ) {
            html += '<option selected disabled value="">Select a Modem</option>';
        }
        html += options;
        html += '</select>';

        return html;
    }

    renderMsgType() {
        let html = '';
        let dev_type = $( '#route-source-device-type-select option:selected' ).val();
        let msg_type = $( '#route-msg-type-select option:selected' ).val();

        html += '<select name="route-msg-type-select" id="route-msg-type-select">';

        if ( msg_type === 'pk001' ) {
            html += '<option value="pk001" selected>pk001</option>';
        } else { 
            html += '<option value="pk001">pk001</option>';
        }
        
        if ( dev_type === 'handset' ) {
            if ( msg_type === 'command' ) {
                html += '<option value="command" selected>command</option>';
            } else {
                html += '<option value="command">command</option>';
            }
        }

        html += '</select>';

        return html;
    }

    renderEndpointType() {
        let html = '';
        let dev_type = $( '#route-source-device-type-select option:selected' ).val();
        let ep_type = $( '#route-endpoint-type-select option:selected' ).val()

        html += '<select name="route-endpoint-type-select" id="route-endpoint-type-select">';

        if ( dev_type === '' ) {
            html += '<option value="buoy">buoy</option>';
            html += '<option value="handset">handset</option>';
        }

        if ( dev_type === 'buoy' ) {
            if ( ep_type === 'handset' ) {
                html += '<option value="handset" selected>handset</option>';
            } else {
                html += '<option value="handset">handset</option>';
            }
        }

        if ( dev_type === 'handset' ) {
            if ( ep_type === 'buoy' ) {
                html += '<option value="buoy" selected>buoy</option>';
            } else {
                html += '<option value="buoy">buoy</option>';
            }
        }
        
        if ( ep_type === 'sqs' ) {
            html += '<option value="sqs" selected>sqs</option>';
        } else {
            html += '<option value="sqs">sqs</option>';
        }

        html += '</select>'; 

        return html;
    }

    renderEndpointLabel() {
        let html = '';
        let ep_type = $( '#route-endpoint-type-select option:selected' ).val()
        let ep_label = $( '#route-endpoint-label option:selected' ).text();

        html += '<select name="route-endpoint-label" id="route-endpoint-label">';

        if (ep_type === '' || ep_type == null || ep_label === '' || ep_label == null ) {
            html += '<option selected disabled value="">Select an Endpoint</option>';
        }
        if ( ep_type === 'sqs' ) {
            for ( const [qid, queue] of Object.entries(this.queues) ) {
                if ( queue.queue_name === ep_label ){
                    html += '<option value="' + qid +'" selected>' + queue.queue_name + '</option>';
                } else {
                    html += '<option value="' + qid +'">' + queue.queue_name + '</option>';
                }
            }
        } else {
            for ( const [mid, modem] of Object.entries(this.modems) ) {
                if ( ep_type === modem.device_type ) {

                    if ( modem.serial === ep_label ) {
                        html += '<option value="' + mid + '" selected>' + modem.serial + '</option>';
                    } else {
                        html += '<option value="' + mid + '">' + modem.serial + '</option>';
                    }
                }
            }
        }

        html += '</select>';

        return html;
    }

    renderEndpointID() {
        let html = '';
        let ep_type = $( '#route-endpoint-type-select option:selected' ).val()
        let ep_label = $( '#route-endpoint-label option:selected' ).text();

        if ( ep_type === 'buoy' || ep_type === 'handset' ) {
            for ( const [mid, modem] of Object.entries(this.modems) ) {
                if (modem.serial === ep_label && modem.device_type === ep_type) {
                    html += modem.id + '' ;
                }
            }
        } else if ( ep_type === 'sqs' ) {
            for ( const [qid, queue] of Object.entries(this.queues) ) {
                if ( queue.queue_name === ep_label ) {
                    html += queue.id + '';
                }
            }
        }

        return html;
    }

    renderFormFields() {
        let html = "";
        html += '<table><tr>';
        html += '<th></th>';
        html += '<th colspan=4>Source</th>';
        html += '<th colspan=3>Target</th>';
        html += '</tr>';

        html += '<th><label for="route-enabled" id="head-route-enabled">Enabled </label></th>';
        // html += '<th></th>';  // dummy for ID
        html += '<th><label for="source_device_type" id="head-source_device_type">Type</label></th>';
        html += '<th><label for="source_device_label" id="head-source_device_label">Label</label></th>';
        html += '<th><label for="source_device_id" id="head-source_device_id">ID</label></th>';
        html += '<th><label for="message_type" id="head-message_type">Message Type</Label></th>';
        html += '<th><label for="endpoint_type" id="head-endpoint_type">Type</label></th>';
        html += '<th><label for="endpoint-label" id="head-endpoint-label">Label</label></th>';
        html += '<th><label for="endpoint-id" id="head-endpoint_id">ID</label></th>';

        html += '</tr><tr>';

        // enabled
        html += '<td>' + this.renderEnabled() + '</td>';
        // route id
        // html += '<td id="route-id"></td>';
        // source type selection
        html += '<td>' + this.renderSourceDeviceType() + '</td>';
        // source label
        html += '<td id="route-source-device-label">' + this.renderSourceDeviceLabel() + '</td>'; 
        // source id
        html += '<td id="route-source-device-id">' + this.renderSourceDeviceID() + '</td>';
        // message type
        html += '<td>' + this.renderMsgType() + '</td>'; 
        // endpoint type
        html += '<td>' + this.renderEndpointType() + '</td>'; 
        // endpoint label
        html += '<td>' + this.renderEndpointLabel() + '</td>';
        // endpoint id
        html += '<td id="route-endpoint-id">' + this.renderEndpointID() + '</td>';
        html +=  '</tr></table>';

        return html;
    }

    onFormChanges() {
        $( '#route-source-device-type-select' ).off('change');
        $( '#route-source-device-label' ).off('change');
        $( '#route-endpoint-type-select' ).off('change');
        $( '#route-endpoint-label' ).off('change');

        $( '#route-source-device-type-select' ).change( () => {
            // $( '#route-source-device-label option:selected' ).prop('selected', false);
            $( '#route-source-device-label option:selected' ).remove();
            this.renderForm();
        });

        $( '#route-source-device-label' ).change( () => {
            this.renderForm();
        });

        $( '#route-endpoint-type-select' ).change( () => {
            // $( '#route-endpoint-label option:selected' ).prop('selected', false);
            $( '#route-endpoint-label').remove();
            this.renderForm();
        });

        $( '#route-endpoint-label' ).change( () => {
            this.renderForm();
        });

        $( '#submit-new-route' ).off('click');
        $( '#submit-new-route' ).click( () => {
            this.addNewRoute();
        });
    }

    async addNewRoute() {
        this.getFormData();

        const data = {
            'enabled': this.form_data['enabled'],
            'source': {
                'id': this.form_data['source_device'],
                'type': this.form_data['source_type'],
                'label': this.form_data['source_device_label'],
                'msg': this.form_data['msg_type'],
            },
            'target': {
                'id': this.form_data['endpoint_id'],
                'type': this.form_data['endpoint_type'],
                'label': this.form_data['endpoint_label'],
            }
        }
        
        let errors = [];
        if ( data['enabled'] == null || data['enabled'] === '' ) {
            errors.append( "Selected Enabled for route" );
        }
        if ( data['source']['label'] == null || data['source']['label'] === "" ) {
            errors.append( "Select a source label" );
        }
        if ( data['source']['type'] == null || data['source']['type'] === "" ) {
            errors.append( "Select a source type" );
        }
        if ( data['source']['msg'] == null || data['source']['msg'] === "" ) {
            errors.append( "Select a source message type" );
        }
        if ( data['target']['type'] == null || data['target']['type'] === "" ) {
            errors.append( "Select a target type" );
        }
        if ( data['target']['label'] == null || data['target']['label'] === "" ) {
            errors.append( "Select a target label" );
        }

        if ( errors.length > 0 ) {
            handleServerErrors(errors);
            return;
        }
        
        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/create', options );
        let code = response.status

        if ( code == 200 ) {
            log('info', 'New Route Added!');
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content );
        }
    }
            
    async deleteRoute( route_id ) {
        const data = {
            'id': route_id
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/delete', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'Route ' + route_id + ' deleted.');
            delete this.items[route_id];
            init();
            return;
        } else {
            let content = await reposne.json();
            handleServerErrors( content.errors );
        }
    }

    async disenableRoute( route_id ) {

        let enabled = $('#route-enabled-' + route_id).is( ":checked" );

        const data = {
            'id': route_id,
            'enable': enabled
        }

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch( api_base + this.ep + '/enable', options );
        let code = response.status;

        if ( code == 200 ) {
            log('info', 'Route ' + route_id + ' enabled: ' + enabled );
            this.items[route_id].enabled = enabled;
            init();
            return;
        } else {
            let content = await response.json();
            handleServerErrors( content.errors );
        }
    }

    getFormData() {
        this.form_data['enabled'] = $( '#route-enabled' ).is(":checked");
        this.form_data['source_type'] = $('#route-source-device-type-select option:selected').val();
        this.form_data['source_device'] = $('#route-source-device-id').text();
        this.form_data['source_device_label'] = $('#route-source-device-label option:selected').val();
        this.form_data['msg_type'] = $('#route-msg-type-select option:selected').val();
        this.form_data['endpoint_type'] = $('#route-endpoint-type-select option:selected').val();
        this.form_data['endpoint_id'] = $('#route-endpoint-id').text();
        this.form_data['endpoint_label'] = $('#route-endpoint-label option:selected').text();
    }

    onTableActions() {
        this.readTable();

        for ( let item of this.visible_ids ) {
            if ( $( '#delete-route-' + item ) ) {
                $( '#delete-route-' + item ).click( () => {
                    this.deleteRoute( item );
                });
            }
            if ( $( '#route-enabled-' + item ) ) {
                $( '#route-enabled-' + item ).click( () => {
                    this.disenableRoute( item );
                });
            }
        }
    }

}


var modem_table = new ModemTable( '/rockblocks', '#modems-table' );
var queue_table = new QueueTable( '/queues', '#queues-table' );
var buoy_table = new BuoyTable( '/buoys', '#buoys-table', modem_table.items );
var handset_table = new HandsetTable( '/handsets', '#handsets-table', modem_table.items );
var routing_table = new RouteTable( '/routing', '#routes-table', modem_table.items, queue_table.items );


function renderPage() {

    modem_table.updateTable();
    queue_table.updateTable();
    buoy_table.updateTable();
    handset_table.updateTable();
    routing_table.updateTable();


    buoy_table.renderForm();
    buoy_table.onFormChanges();

    handset_table.renderForm();
    handset_table.onFormChanges();

    routing_table.renderForm();
    routing_table.onFormChanges();

}

async function init() {
    await Promise.all([ 
        modem_table.get(), 
        queue_table.get(),
        buoy_table.get(),
        handset_table.get(),
        routing_table.get()
    ]);

    renderPage();
}

init();
