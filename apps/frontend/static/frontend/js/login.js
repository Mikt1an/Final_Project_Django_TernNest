document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("login-form");
    const message = document.getElementById("login-message");
    const submitButton = document.getElementById(
        "login-submit-button"
    );

    if (!form || !message || !submitButton) {
        return;
    }

    function showMessage(text, type) {
        message.textContent = text;
        message.className = `form-message form-message--${type}`;
        message.hidden = false;
    }

    function getErrorMessage(data) {
        if (data.detail) {
            return data.detail;
        }

        const messages = Object.entries(data).map(
            ([field, errors]) => {
                const text = Array.isArray(errors)
                    ? errors.join(" ")
                    : errors;

                return `${field}: ${text}`;
            }
        );

        return messages.join(" ") || "Unable to log in.";
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        message.hidden = true;

        if (!form.reportValidity()) {
            return;
        }

        const formData = new FormData(form);

        const credentials = {
            email: formData.get("email").trim(),
            password: formData.get("password"),
        };

        submitButton.disabled = true;
        submitButton.textContent = "Logging in...";

        try {
            const response = await fetch(
                "/api/v1/accounts/login/",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(credentials),
                }
            );

            const data = await response.json();

            if (!response.ok) {
                showMessage(
                    getErrorMessage(data),
                    "error"
                );
                return;
            }

            if (!data.access || !data.refresh) {
                showMessage(
                    "The server did not return JWT tokens.",
                    "error"
                );
                return;
            }

            window.TernNestAuth.saveTokens(
                data.access,
                data.refresh
            );

            showMessage(
                "Login successful. Redirecting...",
                "success"
            );

            await window.TernNestAuth.updateNavigation();

            window.setTimeout(() => {
                const parameters = new URLSearchParams(
                    window.location.search
                );

                const nextPage = parameters.get("next");

                const safeNextPage =
                    nextPage &&
                    nextPage.startsWith("/") &&
                    !nextPage.startsWith("//")
                        ? nextPage
                        : "/dashboard/";

                window.location.href = safeNextPage;
            }, 600);
        } catch (error) {
            console.error("Login request failed:", error);

            showMessage(
                "Could not connect to the server. Please try again.",
                "error"
            );
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Log in";
        }
    });
});