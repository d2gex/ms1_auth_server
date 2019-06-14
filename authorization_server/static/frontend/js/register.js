
const INVALID_EMAIL = 'Please enter a valid email address';
const PASSWORD_MISSING = 'Please provide a password';
const PASSWORD_INVALID = 'Your password must be at least 8 characters long';

class Register {

    constructor() {
        this.validationObj = {
            rules: {
                firstname: {
                    required: true
                },
                lastname: {
                    required: true
                },
                email: {
                    required: true,
                    isEmailValid: true,
                    email: true
                },
                password: {
                    required: true,
                    minlength: 8
                },
                confirm_password: {
                    required: true,
                    minlength: 8,
                    equalTo: "#password"
                },
            },
            messages: {
                email: INVALID_EMAIL,
                password: {
                    required: PASSWORD_MISSING,
                    minlength: PASSWORD_INVALID
                }
            },
            errorClass: "errorFloat",
            submitHandler: function (form) {
                form.submit();
            }
        };
    }
    getValidationObject() {
        return this.validationObj
    }


}

jQuery(document).ready(function () {

    let register = new Register()
    jQuery('#signup-form').validate(register.getValidationObject());

});