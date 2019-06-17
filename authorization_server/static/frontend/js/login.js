const INVALID_EMAIL = 'Please enter a valid email address';
const PASSWORD_INVALID = 'Your password must be between 8  and 15 characters long';

const NOT_IMPLEMENTED_SMS = 'This functionality is not currently implemented';

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

    addOnclickEventToForgotPassword() {
        jQuery('#forgot_password').click(() => {this.modalDialog.open()})
    }

    getValidationObject() {
        return this.validationObj;
    }

    init(modalDialog) {
        this.modalDialog = modalDialog;
        this.modalDialog.setConfirmButton(NOT_IMPLEMENTED_SMS, 'Close')
        this.modalDialog.setMessage(NOT_IMPLEMENTED_SMS);
        this.addOnclickEventToForgotPassword()
    }

}

jQuery(document).ready(function () {

    let login = new Login();
    let modalDialog = new ModalDialog('#dialog-confirm', login);
    login.init(modalDialog);
    jQuery('#signin-form').validate(login.getValidationObject());

});
