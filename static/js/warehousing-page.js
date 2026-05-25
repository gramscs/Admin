document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("form").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            var hasError = false;
            form.querySelectorAll("[required]").forEach(function (field) {
                if (!field.value.trim()) {
                    field.classList.add("is-invalid");
                    hasError = true;
                } else {
                    field.classList.remove("is-invalid");
                }
            });
            if (hasError) {
                e.preventDefault();
            }
        });
    });

    
});

(function () {
    var options = {
        whatsapp: "+91-9910417643",
        email: "info@gramsec.com",
        sms: "+91-9910417643",
        call: "+91-9910417643",
        company_logo_url: "https://www.gramscs.com/images/logo.jpg",
        greeting_message: "Connect with Gram Experts. Connect with us for any assistance.",
        call_to_action: "Connect with us",
        button_color: "#E74339",
        position: "left",
        order: "whatsapp,sms,call,email"
    };

    var proto = document.location.protocol;
    var host = "whatshelp.io";
    var url = proto + "//static." + host;
    var s = document.createElement("script");
    s.type = "text/javascript";
    s.async = true;
    s.src = url + "/widget-send-button/js/init.js";
    s.onload = function () {
        if (typeof WhWidgetSendButton !== "undefined") {
            WhWidgetSendButton.init(host, proto, options);
        }
    };

    var x = document.getElementsByTagName("script")[0];
    if (x && x.parentNode) {
        x.parentNode.insertBefore(s, x);
    }
})();
