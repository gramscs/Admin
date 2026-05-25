document.addEventListener("DOMContentLoaded", function () {
    function isPopupOpen() {
        return !!document.querySelector(".pop-overlay:target");
    }

    function closeAllPopups() {
        window.location.hash = "#gallery";
    }

    function toggleBodyScroll(disable) {
        document.body.style.overflow = disable ? "hidden" : "";
    }

    window.addEventListener("hashchange", function () {
        toggleBodyScroll(isPopupOpen());
    });
    toggleBodyScroll(isPopupOpen());

    document.querySelectorAll(".pop-overlay").forEach(function (overlay) {
        overlay.addEventListener("click", function (e) {
            if (e.target === overlay) {
                closeAllPopups();
            }
        });
    });

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && isPopupOpen()) {
            closeAllPopups();
        }
    });

    Array.prototype.slice.call(document.querySelectorAll(".needs-validation")).forEach(function (form) {
        form.addEventListener("submit", function (event) {
            if (form.id === "contactForm") {
                event.preventDefault();
                event.stopPropagation();
                return;
            }

            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add("was-validated");
        }, false);
    });

    var statsNumbers = document.querySelectorAll(".stats-number");
    if (statsNumbers.length) {
        var statsObserver = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = "1";
                    entry.target.style.transform = "translateY(0)";
                    statsObserver.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.5,
            rootMargin: "0px"
        });

        statsNumbers.forEach(function (number) {
            number.style.opacity = "0";
            number.style.transform = "translateY(20px)";
            number.style.transition = "opacity 0.6s ease, transform 0.6s ease";
            statsObserver.observe(number);
        });
    }

    document
        .querySelectorAll('a, button, input, textarea, select, [tabindex]:not([tabindex="-1"])')
        .forEach(function (element) {
            element.addEventListener("focus", function () {
                this.style.outline = "2px solid rgba(130, 207, 43, 0.4)";
                this.style.outlineOffset = "2px";
            });

            element.addEventListener("blur", function () {
                this.style.outline = "";
                this.style.outlineOffset = "";
            });
        });

    window.showToast = function (message, type) {
        var toastType = type || "success";
        var toastContainer = document.getElementById("toast-container");
        if (!toastContainer) {
            return;
        }

        var toast = document.createElement("div");
        toast.className = "toast toast-" + toastType;
        toast.style.minWidth = "250px";
        toast.style.backgroundColor = toastType === "success" ? "#82CF2B" : "#dc3545";
        toast.style.color = "white";
        toast.style.padding = "15px 20px";
        toast.style.marginBottom = "10px";
        toast.style.borderRadius = "4px";
        toast.style.boxShadow = "0 4px 8px rgba(0,0,0,0.1)";
        toast.style.opacity = "0";
        toast.style.transition = "opacity 0.3s ease-in-out";
        toast.innerHTML =
            '<div class="d-flex align-items-center">' +
            '<span class="fa fa-' + (toastType === "success" ? "check-circle" : "exclamation-circle") + ' me-2"></span>' +
            "<div>" + message + "</div>" +
            "</div>";

        toastContainer.appendChild(toast);

        setTimeout(function () {
            toast.style.opacity = "1";
        }, 10);

        setTimeout(function () {
            toast.style.opacity = "0";
            setTimeout(function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    };

    

    var currentSlide = 1;
    var totalSlides = 3;
    var slideInterval = 7000;

    function nextSlide() {
        currentSlide = currentSlide >= totalSlides ? 1 : currentSlide + 1;
        var slideInput = document.getElementById("slides_" + currentSlide);
        if (slideInput) {
            slideInput.checked = true;
        }
    }

    var autoSlider = setInterval(nextSlide, slideInterval);
    document.querySelectorAll(".navigation label").forEach(function (label, index) {
        label.addEventListener("click", function () {
            clearInterval(autoSlider);
            currentSlide = index + 1;
            setTimeout(function () {
                autoSlider = setInterval(nextSlide, slideInterval);
            }, slideInterval);
        });
    });

    var carousel = document.getElementById("slider1");
    if (carousel) {
        carousel.addEventListener("mouseenter", function () {
            clearInterval(autoSlider);
        });

        carousel.addEventListener("mouseleave", function () {
            autoSlider = setInterval(nextSlide, slideInterval);
        });
    }
});
