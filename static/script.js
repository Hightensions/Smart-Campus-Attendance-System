const darkModeBtn =
document.getElementById("darkModeBtn");

if (darkModeBtn) {

    darkModeBtn.addEventListener(
        "click",
        () => {

            document.body.classList.toggle(
                "dark-mode"
            );

            const isDark =
                document.body.classList.contains(
                    "dark-mode"
                );

            localStorage.setItem(
                "darkMode",
                isDark
            );

            darkModeBtn.innerHTML =
                isDark
                ? "☀️ Light Mode"
                : "🌙 Dark Mode";
        }
    );

    if (
        localStorage.getItem("darkMode")
        === "true"
    ) {

        document.body.classList.add(
            "dark-mode"
        );

        darkModeBtn.innerHTML =
            "☀️ Light Mode";
    }
}