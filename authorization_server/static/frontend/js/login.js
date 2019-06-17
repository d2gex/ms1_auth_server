
const INVALID_EMAIL = 'Please enter a valid email address';
const PASSWORD_INVALID = 'Your password must be between 8  and 15 characters long';

class Login {

    constructor() {
        this.validationObj = {
            rules: {
                email: {
                    required: true,
                    isEmailValid: true,
                    email: true
                },
                password: {
                    required: true,
                    minlength: 8
                }
            },
            messages: {
                email: INVALID_EMAIL,
                password: {
                    minlength: PASSWORD_INVALID
                }
            },
            errorClass: "errorFloat",
            submitHandler: function (form) {
                form.submit();
            }
        };

    }

    send() {
        this.popup.open()
    }

    addOnclickEventToSignInButton() {
        jQuery('#sing_in').click(() => {this.send();})
    }

    getValidationObject() {
        return this.validationObj
    }

    init(popup) {
        this.popup = popup
        this.addOnclickEventToSignInButton()
    }


}

jQuery(document).ready(function () {

    let login = new Login()
    let modalDialog = new ModalDialog('#dialog-confirm', login)
    login.init(modalDialog)
    jQuery('#signin-form').validate(login.getValidationObject());

});