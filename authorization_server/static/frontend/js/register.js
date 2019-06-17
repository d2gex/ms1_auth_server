const INVALID_EMAIL = 'Please enter a valid email address';
const PASSWORD_INVALID = 'Your password must be between 8  and 15 characters long';
const CONFIRM_PASSWORD = 'Please enter the same password again';

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
                    minlength: PASSWORD_INVALID
                },
                confirm_password: {
                    equalTo: CONFIRM_PASSWORD
                }
            },
            errorClass: "errorFloat",
            submitHandler: function (form) {
                form.submit();
            }
        };
    }

    getValidationObject() {
        return this.validationObj;
    }


}

jQuery(document).ready(function () {

    let register = new Register();
    jQuery('#signup-form').validate(register.getValidationObject());

});
