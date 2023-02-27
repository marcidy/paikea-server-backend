import { sanitize, delay, log } from './utils.js';

const upgrade_states = [
    "Initializing",
    "Pending",
    "Ready",
    "Upgrading Device",
    "Upgrade Failed on Device",
    "Upgrade Succeeded on Device",
    "Server Cleanup",
    "Upgrade Succeeded",
    "Upgrade Failed",
    "No Upgrade Available",
    "No Upgrade",
    "Server Error"
];

function handleServerErrors( errors ) {
    for ( let item of errors ) {
        log( 'error', item );
    }
}

class Upgrade {

    constructor( device ) {
        this.device = device;
        this.device_type = device.dev;
        this.device_id = device.iam;
        this.ep = `/${device.dev}/${device.iam}/upgrade`;
        this.job_id = null;
        this.job_status = null;
        this.task = false;
        this.progress = '';
        this.avail = '';
    }

    async req( data ) {
        let api_base = '';

        if ( window.location.host.indexOf('localhost') == 0 ) {
            api_base = 'http://' + window.location.host + '/v1';
        } else {
            api_base = 'https://' + window.location.host + '/v1';
        }

        data['device_type'] = this.device_type;
        data['device_id'] = this.device_id;

        const options = {
            method: 'POST',
            body: JSON.stringify( data ),
            headers: {
                'Content-Type': 'application/json'
            }
        }

        let response = await fetch(api_base + this.ep, options);
        let code = response.status;
        let content = await response.json();

        if ( code == 200 ) {
            return content;
        } else {
            handleServerErrors( content.errors );
        }
    }

    setJobId( job_id ) {
        if ( this.job_id && this.job_id != job_id ){
            // shouldn't change job id of this upgrade once set.
        }

        this.job_id = job_id;
        $( '#firmware-job-id' ).text( job_id );
    }

    setJobStatus( job_status ) {
        this.job_status = job_status;
        let state = parseInt( job_status );
        if ( !isNaN( state ) ) {
            $( '#firmware-job-status' ).text( upgrade_states[job_status] );
        }
    }

    async check() {
        let data = {'cmd': 'check'};

        if ( this.job_id ) {
            data['job_id'] = this.job_id;
        }
        data = await this.req( data );

        if ( !this.job_id && data['job_id'] && data['job_id'] > 0 ) {
            this.setJobId( data['job_id'] );
        }

        this.setJobStatus( data['status'] );

        switch ( data['status'] ) {
            case 0:
                this.progress = '10%';
                this.avail = 'Initializing';
                break;
            case 1:
                this.progress = '20%';
                this.avail = 'Deploying on Server';
                break;
            case 2:
                this.progress = '30%';
                this.avail = 'Yes';
                $('#upgrade-button').text("Perform Device Upgrade");
                $('#upgrade-button').click( () => { this.perform() } );
                break;
            case 3:
                this.progress = '40%';
                this.avail = 'Device updating';
                $('#upgrade-button').disabled = true;
                break;
            case 4:
                this.progress = '80%';
                this.avail = 'Device upgrade failed';
                $('#upgrade-button').disabled = true;
                break;
            case 5:
                this.progress = '80%';
                this.avail = 'Device upgrade succeeded';
                $('#upgrade-button').disabled = true;
                break;
            case 6:
                this.progress = '90%';
                this.avail = 'Server Cleanup';
                $('#upgrade-button').disabled = true;
                break;
            case 7:
                this.progress = '100%';
                this.avail = 'Upgrade Completed Successfully';
                $('#upgrade-button').text("Create New Upgrade");
                $('#upgrade-button').click( () => { this.create() } );
                break;
            case 8:
                this.progress = '100%';
                this.avail = 'Upgrade Failed';
                $('#upgrade-button').text("Create New Upgrade");
                $('#upgrade-button').click( () => { this.create() } );
                break;
            case 9:
            case 10:
                this.progress = '';
                this.avail = 'Upgrade not deployed on Server'
                $('#upgrade-button').text("Create New Upgrade");
                $('#upgrade-button').click( () => { this.create() } );
                break;
            case 11:
                this.progress = 'Error';
                this.avail = 'Server side Error';
                break;
            default:
                this.progress = 'Unknown';
                this.avail = 'Unknown';
        }

        $('#firmware-avail').text( this.avail );

        return data;

    }

    async create() {
        let data = await this.check();

        // If a job is available, it needs to be cleaned up before a new one is created
        if ( [ 0, 1, 2, 3, 4, 5, 6 ].indexOf( this.job_status ) != -1 ) {
            // upgrade on server is in progress.  Don't start another one.
            return;
        } else if ( [7, 8, 9, 10].indexOf( this.job_status ) != -1 ) {
            // upgrade on server is finished or doesn't exit

        } else {
            // server error
            return;
        }

        data = await this.req({'cmd': 'init'});

        this.setJobId( data['job_id'] );
        this.setJobStatus( data['status'] );
        this.task = true;

        while ( this.task ) {
            await delay( 3000 );
            await this.check();
            if ( [2, 11].indexOf( this.job_status ) != -1 ) {
                this.task = false;
            }
        }

    }

    async perform() {
        let self = this;

        let msg = "This will disconnect the device while it attempts to upgrade.  The device must remain on during this process.";
        msg += "\nProceed?";

        if ( !confirm(msg) ) {
            return;
        }

        self.device.cmd("switch_app", ["updatepy"]);
        self.device.cmd("reset", []);

        self.task = true;

        while ( self.task ) {
            await delay( 3000 );
            await self.check();

            if ( [11, 10, 9, 8, 7,].indexOf(self.job_status) != -1 ) {
                self.stop();
            }
        }
    }

    async stop() {
        this.task = false;
    }

}

export { Upgrade };
