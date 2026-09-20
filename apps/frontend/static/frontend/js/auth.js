(() => {
    const ACCESS_TOKEN_KEY = "ternnest_access_token";
    const REFRESH_TOKEN_KEY = "ternnest_refresh_token";

    function getAccessToken() {
        return localStorage.getItem(ACCESS_TOKEN_KEY);
    }

    function getRefreshToken() {
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    }

    function saveTokens(accessToken, refreshToken) {
        localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }

    function clearTokens() {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
    }

    async function refreshAccessToken() {
        const refreshToken = getRefreshToken();

        if (!refreshToken) {
            return false;
        }

        try {
            const response = await fetch(
                "/api/v1/accounts/token/refresh/",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        refresh: refreshToken,
                    }),
                }
            );

            if (!response.ok) {
                clearTokens();
                return false;
            }

            const data = await response.json();

            localStorage.setItem(
                ACCESS_TOKEN_KEY,
                data.access
            );

            if (data.refresh) {
                localStorage.setItem(
                    REFRESH_TOKEN_KEY,
                    data.refresh
                );
            }

            return true;
        } catch (error) {
            console.error("Token refresh failed:", error);
            return false;
        }
    }

    async function authenticatedFetch(url, options = {}) {
        const headers = new Headers(options.headers || {});
        const accessToken = getAccessToken();

        if (accessToken) {
            headers.set(
                "Authorization",
                `Bearer ${accessToken}`
            );
        }

        let response = await fetch(url, {
            ...options,
            headers,
        });

        if (response.status !== 401) {
            return response;
        }

        const refreshed = await refreshAccessToken();

        if (!refreshed) {
            return response;
        }

        headers.set(
            "Authorization",
            `Bearer ${getAccessToken()}`
        );

        response = await fetch(url, {
            ...options,
            headers,
        });

        return response;
    }

    function showGuestNavigation() {
        const guestNavigation = document.querySelector(
            "[data-guest-navigation]"
        );

        const userNavigation = document.querySelector(
            "[data-user-navigation]"
        );

        if (guestNavigation) {
            guestNavigation.hidden = false;
        }

        if (userNavigation) {
            userNavigation.hidden = true;
        }
    }

    function showUserNavigation(user) {
        const guestNavigation = document.querySelector(
            "[data-guest-navigation]"
        );

        const userNavigation = document.querySelector(
            "[data-user-navigation]"
        );

        if (guestNavigation) {
            guestNavigation.hidden = true;
        }

        if (userNavigation) {
            userNavigation.hidden = false;
        }

        const userName = document.querySelector(
            "[data-user-name]"
        );

        if (userName) {
            userName.textContent =
                user.first_name ||
                user.email ||
                "My account";
        }

        const avatar = document.querySelector(
            ".account-link__avatar"
        );

        if (avatar) {
            const initials = [
                user.first_name,
                user.last_name,
            ]
                .filter(Boolean)
                .map((value) => value[0])
                .join("")
                .slice(0, 2)
                .toUpperCase();

            avatar.textContent = initials || "TN";
        }
    }

    async function updateNavigation() {
        if (!getAccessToken() && !getRefreshToken()) {
            showGuestNavigation();
            return;
        }

        try {
            const response = await authenticatedFetch(
                "/api/v1/accounts/me/"
            );

            if (!response.ok) {
                clearTokens();
                showGuestNavigation();
                return;
            }

            const user = await response.json();
            showUserNavigation(user);
        } catch (error) {
            console.error("Could not load current user:", error);
            showGuestNavigation();
        }
    }

    function logout() {
        clearTokens();
        window.location.href = "/";
    }

    window.TernNestAuth = {
        getAccessToken,
        getRefreshToken,
        saveTokens,
        clearTokens,
        authenticatedFetch,
        updateNavigation,
        logout,
    };

    document.addEventListener("DOMContentLoaded", () => {
        updateNavigation();

        const logoutButton = document.querySelector(
            "[data-logout-button]"
        );

        if (logoutButton) {
            logoutButton.addEventListener("click", logout);
        }
    });
})();