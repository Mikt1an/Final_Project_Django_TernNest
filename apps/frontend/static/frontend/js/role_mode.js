(function () {
    "use strict";

    const TENANT_ROLE = "Tenant";
    const LANDLORD_ROLE = "Landlord";
    const STORAGE_PREFIX = "ternnest_active_role";

    let currentUser = null;
    let activeRole = null;
    let initializationPromise = null;


    function normalizeRole(value) {
        const role = String(value || "").toLowerCase();

        if (role === "tenant") {
            return TENANT_ROLE;
        }

        if (role === "landlord") {
            return LANDLORD_ROLE;
        }

        return null;
    }


    function getUserRoles(user) {
        if (!user || !Array.isArray(user.roles)) {
            return [];
        }

        return user.roles
            .map(normalizeRole)
            .filter(Boolean);
    }


    function hasRole(user, role) {
        const normalizedRole = normalizeRole(role);

        return (
            normalizedRole !== null
            && getUserRoles(user).includes(normalizedRole)
        );
    }


    function getStorageKey(user) {
        if (
            !user
            || user.id === undefined
            || user.id === null
        ) {
            return null;
        }

        return `${STORAGE_PREFIX}_${user.id}`;
    }


    function readStoredRole(user) {
        const storageKey = getStorageKey(user);

        if (!storageKey) {
            return null;
        }

        try {
            return normalizeRole(
                window.localStorage.getItem(
                    storageKey
                )
            );
        } catch {
            return null;
        }
    }


    function storeRole(user, role) {
        const storageKey = getStorageKey(user);

        if (!storageKey) {
            return;
        }

        try {
            window.localStorage.setItem(
                storageKey,
                role
            );
        } catch {
            // The selected mode still works
            // for the current page.
        }
    }


    function chooseActiveRole(user) {
        const storedRole = readStoredRole(user);

        if (
            storedRole
            && hasRole(user, storedRole)
        ) {
            return storedRole;
        }

        if (hasRole(user, TENANT_ROLE)) {
            return TENANT_ROLE;
        }

        if (hasRole(user, LANDLORD_ROLE)) {
            return LANDLORD_ROLE;
        }

        return null;
    }


    function applyRoleVisibility(role) {
        const visibleRole = role
            ? role.toLowerCase()
            : "guest";

        document.documentElement.dataset.activeRole =
            visibleRole;

        document
            .querySelectorAll(
                "[data-role-visible]"
            )
            .forEach(element => {
                const allowedRoles = String(
                    element.dataset.roleVisible || ""
                )
                    .split(",")
                    .map(
                        value =>
                            value
                                .trim()
                                .toLowerCase()
                    )
                    .filter(Boolean);

                element.hidden =
                    !allowedRoles.includes(
                        visibleRole
                    );
            });
    }


    function getState() {
        return {
            user: currentUser,
            activeRole,
            roles: getUserRoles(currentUser),
        };
    }


    function publishRoleChange() {
        window.dispatchEvent(
            new CustomEvent(
                "ternnest:rolechange",
                {
                    detail: getState(),
                }
            )
        );
    }


    function setActiveRole(role) {
        const normalizedRole =
            normalizeRole(role);

        if (
            !normalizedRole
            || !hasRole(
                currentUser,
                normalizedRole
            )
        ) {
            return false;
        }

        activeRole = normalizedRole;

        storeRole(
            currentUser,
            activeRole
        );

        applyRoleVisibility(
            activeRole
        );

        publishRoleChange();

        return true;
    }


    function setCurrentUser(user) {
        currentUser = user || null;

        activeRole =
            chooseActiveRole(currentUser);

        if (activeRole) {
            storeRole(
                currentUser,
                activeRole
            );
        }

        applyRoleVisibility(
            activeRole
        );

        publishRoleChange();

        return getState();
    }


    async function initialize(
        options = {}
    ) {
        const force =
            Boolean(options.force);

        if (force) {
            initializationPromise = null;
        }

        if (initializationPromise) {
            await initializationPromise;

            return getState();
        }

        initializationPromise =
            (async () => {
                if (
                    !window.TernNestAuth
                    || !window.TernNestAuth
                        .authenticatedFetch
                ) {
                    return setCurrentUser(
                        null
                    );
                }

                const hasToken =
                    Boolean(
                        window.TernNestAuth
                            .getAccessToken()
                        ||
                        window.TernNestAuth
                            .getRefreshToken()
                    );

                if (!hasToken) {
                    return setCurrentUser(
                        null
                    );
                }

                const response =
                    await window.TernNestAuth
                        .authenticatedFetch(
                            "/api/v1/accounts/me/"
                        );

                if (!response.ok) {
                    return setCurrentUser(
                        null
                    );
                }

                const user =
                    await response.json();

                return setCurrentUser(user);
            })();

        try {
            await initializationPromise;

            return getState();
        } catch (error) {
            initializationPromise = null;

            applyRoleVisibility(null);

            throw error;
        }
    }


    async function becomeLandlord() {
        if (
            !window.TernNestAuth
            || !window.TernNestAuth
                .authenticatedFetch
        ) {
            throw new Error(
                "Authentication is unavailable."
            );
        }

        const response =
            await window.TernNestAuth
                .authenticatedFetch(
                    (
                        "/api/v1/accounts/"
                        +
                        "become-landlord/"
                    ),
                    {
                        method: "POST",
                    }
                );

        let data = null;

        try {
            data = await response.json();
        } catch {
            data = null;
        }

        if (!response.ok) {
            const error = new Error(
                data && data.detail
                    ? data.detail
                    : (
                        "Unable to activate "
                        +
                        "landlord mode."
                    )
            );

            error.data = data;
            error.status = response.status;

            throw error;
        }

        currentUser = {
            ...(currentUser || {}),
            roles: Array.isArray(
                data.roles
            )
                ? data.roles
                : getUserRoles(
                    currentUser
                ),
        };

        setActiveRole(
            LANDLORD_ROLE
        );

        return {
            data,
            ...getState(),
        };
    }


    window.TernNestRoleMode = {
        TENANT_ROLE,
        LANDLORD_ROLE,
        initialize,
        getState,
        hasRole,
        setActiveRole,
        becomeLandlord,
    };


    document.addEventListener(
        "DOMContentLoaded",
        () => {
            initialize()
                .catch(error => {
                    console.error(
                        (
                            "Role mode "
                            +
                            "initialization error:"
                        ),
                        error
                    );
                });
        }
    );
})();