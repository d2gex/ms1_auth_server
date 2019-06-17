class ModalDialog {

    constructor(dialogId, obj) {

        this.obj = obj;
        this.popup = jQuery(dialogId);
        this.popup.dialog({
            autoOpen: false,
            resizable: false,
            height: "auto",
            width: 400,
            modal: true,
            buttons: {
                OK: () => {
                    this.obj.send()
                },
                Cancel: () => {
                    this.close()
                }
            }
        });
    }

    open() {
        this.popup.dialog('open');
    }

    close() {
        this.popup.dialog('close');
    }

    setMessage(msg) {
        jQuery('#d_content').text(msg)
    }

    setConfirmButton(msg) {
        self.popup.dialog("option", "buttons",
            [
                {
                    text: "OK",
                    click: () => {
                        this.close();
                        this.reset(msg);
                    }
                }
            ]
        );
    }

    reset(msg) {
        if (msg) {
            this.setMessage(msg);
        }
        self.popup.dialog("option", "buttons",
            [
                {
                    text: "OK",
                    click: () => {this.obj.send();}
                },
                {
                    text: "Cancel",
                    click: () => {this.close();}
                }
            ]
        );
    }

}



