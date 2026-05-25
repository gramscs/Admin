document.addEventListener("DOMContentLoaded", function () {
	var openBtn = document.getElementById("openMenuModal");
	var modal = document.getElementById("menuModal");
	var closeBtn = modal ? modal.querySelector(".menu-modal-close") : null;

	function openModal() {
		if (!modal || !openBtn) {
			return;
		}
		modal.classList.add("active");
		openBtn.setAttribute("aria-expanded", "true");
		modal.focus();
		document.body.style.overflow = "hidden";
	}

	function closeModal() {
		if (!modal || !openBtn) {
			return;
		}
		modal.classList.remove("active");
		openBtn.setAttribute("aria-expanded", "false");
		openBtn.focus();
		document.body.style.overflow = "";
	}

	if (openBtn && modal && closeBtn) {
		openBtn.addEventListener("click", openModal);
		closeBtn.addEventListener("click", closeModal);

		modal.addEventListener("keydown", function (e) {
			if (e.key === "Escape") {
				closeModal();
			}
		});

		modal.addEventListener("click", function (e) {
			if (e.target === modal) {
				closeModal();
			}
		});

		modal.addEventListener("keydown", function (e) {
			if (e.key !== "Tab") {
				return;
			}

			var focusable = modal.querySelectorAll("a,button,[tabindex]:not([tabindex='-1'])");
			if (!focusable.length) {
				return;
			}

			var first = focusable[0];
			var last = focusable[focusable.length - 1];

			if (e.shiftKey && document.activeElement === first) {
				e.preventDefault();
				last.focus();
			} else if (!e.shiftKey && document.activeElement === last) {
				e.preventDefault();
				first.focus();
			}
		});
	}

	document.querySelectorAll(".dropdown-toggle").forEach(function (toggle) {
		toggle.addEventListener("mouseenter", function () {
			var dropdown = this.closest(".dropdown");
			if (dropdown) {
				dropdown.classList.add("show");
			}
		});

		var dropdown = toggle.closest(".dropdown");
		if (dropdown) {
			dropdown.addEventListener("mouseleave", function () {
				this.classList.remove("show");
			});
		}

		toggle.addEventListener("click", function (e) {
			e.preventDefault();
			var dropdownOnClick = this.closest(".dropdown");
			if (dropdownOnClick) {
				dropdownOnClick.classList.toggle("show");
			}
		});
	});

	var mainMenu = document.querySelector(".main-menu");
	if (!mainMenu) {
		return;
	}

	var lastScrollTop = 0;
	window.addEventListener("scroll", function () {
		var scrollTop = window.pageYOffset || document.documentElement.scrollTop;

		if (scrollTop > 100) {
			mainMenu.classList.add("scrolled");
		} else {
			mainMenu.classList.remove("scrolled");
		}

		if (scrollTop > lastScrollTop && scrollTop > 200) {
			mainMenu.classList.add("nav-up");
		} else {
			mainMenu.classList.remove("nav-up");
		}

		lastScrollTop = scrollTop;
	});
});
