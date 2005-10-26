function submitNewPassword(form) {
    if (form.newPassword.value != form.confirmPassword.value) {
        alert('Passwords do not match.  Try again.');
    } else {
        if (form.currentPassword) {
            var curPass = form.currentPassword.value;
            form.currentPassword.value = '';
        } else {
            var curPass = null;
        }

        var newPass = form.newPassword.value;
        form.newPassword.value = form.confirmPassword.value = '';

        server.handle('changePassword', curPass, newPass);
    }
}
