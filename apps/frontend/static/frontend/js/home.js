document.addEventListener(
    "DOMContentLoaded",
    () => {
        const listingsApiUrl =
            "/api/v1/listings/";

        const amenitiesApiUrl =
            "/api/v1/listings/amenities/";

        const viewHistoryApiUrl =
            "/api/v1/listings/view-history/";

        const form =
            document.getElementById(
                "listing-search-form"
            );

        const listingsGrid =
            document.getElementById(
                "listings-grid"
            );

        const recentlyViewedSection =
            document.getElementById(
                "recently-viewed-section"
            );

        const recentlyViewedGrid =
            document.getElementById(
                "recently-viewed-grid"
            );

        const resultsSummary =
            document.getElementById(
                "results-summary"
            );

        const searchError =
            document.getElementById(
                "search-error"
            );

        const amenitiesContainer =
            document.getElementById(
                "amenities-filter-options"
            );

        const advancedFilters =
            document.getElementById(
                "advanced-filters"
            );

        const activeFilterCount =
            document.getElementById(
                "active-filter-count"
            );

        const clearFiltersButton =
            document.getElementById(
                "clear-filters-button"
            );

        const orderingSelect =
            document.getElementById(
                "listing-ordering"
            );

        const checkInInput =
            document.getElementById(
                "filter-check-in"
            );

        const checkOutInput =
            document.getElementById(
                "filter-check-out"
            );

        if (
            !form
            || !listingsGrid
            || !resultsSummary
        ) {
            return;
        }

        const filterFieldNames = [
            "search",
            "city",
            "country",
            "listing_type",
            "min_price",
            "max_price",
            "bedrooms",
            "beds",
            "bathrooms",
            "guests",
            "check_in",
            "check_out",
        ];

        const advancedFilterNames = [
            "search",
            "country",
            "listing_type",
            "min_price",
            "max_price",
            "bedrooms",
            "beds",
            "bathrooms",
            "amenities",
        ];

        function getResults(data) {
            if (Array.isArray(data)) {
                return data;
            }

            return data.results || [];
        }

        async function apiFetch(
            url,
            options = {}
        ) {
            const auth =
                window.TernNestAuth;

            if (
                auth
                && (
                    auth.getAccessToken()
                    || auth.getRefreshToken()
                )
            ) {
                return auth.authenticatedFetch(
                    url,
                    options
                );
            }

            return fetch(
                url,
                options
            );
        }

        function escapeHtml(value) {
            return String(
                value ?? ""
            ).replace(
                /[&<>"']/g,
                character => {
                    const replacements = {
                        "&": "&amp;",
                        "<": "&lt;",
                        ">": "&gt;",
                        '"': "&quot;",
                        "'": "&#039;",
                    };

                    return replacements[
                        character
                    ];
                }
            );
        }

        function getLocalDateString(date) {
            const timezoneOffset =
                date.getTimezoneOffset()
                * 60000;

            return new Date(
                date.getTime()
                - timezoneOffset
            )
                .toISOString()
                .split("T")[0];
        }

        function updateDateConstraints() {
            const today =
                getLocalDateString(
                    new Date()
                );

            checkInInput.min = today;

            checkOutInput.min =
                checkInInput.value
                || today;
        }

        function getFormField(name) {
            if (name === "ordering") {
                return orderingSelect;
            }

            return form.querySelector(
                `[name="${name}"]`
            );
        }

        function getSelectedAmenities() {
            return Array.from(
                amenitiesContainer.querySelectorAll(
                    'input[name="amenity"]:checked'
                )
            ).map(
                checkbox => checkbox.value
            );
        }

        function buildQueryParameters() {
            const parameters =
                new URLSearchParams();

            filterFieldNames.forEach(
                name => {
                    const field =
                        getFormField(name);

                    if (!field) {
                        return;
                    }

                    const value =
                        String(
                            field.value || ""
                        ).trim();

                    if (!value) {
                        return;
                    }

                    if (
                        name === "guests"
                        && value === "1"
                    ) {
                        return;
                    }

                    parameters.set(
                        name,
                        value
                    );
                }
            );

            if (
                orderingSelect.value
                && orderingSelect.value
                !== "-created_at"
            ) {
                parameters.set(
                    "ordering",
                    orderingSelect.value
                );
            }

            const amenityIds =
                getSelectedAmenities();

            if (amenityIds.length) {
                parameters.set(
                    "amenities",
                    amenityIds.join(",")
                );
            }

            return parameters;
        }

        function getAmenityIdsFromParameters(
            parameters
        ) {
            const value =
                parameters.get(
                    "amenities"
                );

            if (!value) {
                return new Set();
            }

            return new Set(
                value
                    .split(",")
                    .map(item => item.trim())
                    .filter(Boolean)
            );
        }

        function applyParametersToForm(
            parameters
        ) {
            filterFieldNames.forEach(
                name => {
                    const field =
                        getFormField(name);

                    if (!field) {
                        return;
                    }

                    if (name === "guests") {
                        field.value =
                            parameters.get(name)
                            || "1";

                        return;
                    }

                    field.value =
                        parameters.get(name)
                        || "";
                }
            );

            orderingSelect.value =
                parameters.get("ordering")
                || "-created_at";

            const selectedAmenities =
                getAmenityIdsFromParameters(
                    parameters
                );

            amenitiesContainer
                .querySelectorAll(
                    'input[name="amenity"]'
                )
                .forEach(
                    checkbox => {
                        checkbox.checked =
                            selectedAmenities.has(
                                checkbox.value
                            );
                    }
                );

            advancedFilters.open =
                advancedFilterNames.some(
                    name => parameters.has(name)
                );

            updateDateConstraints();
            updateFilterIndicator();
        }

        function updateFilterIndicator() {
            const parameters =
                buildQueryParameters();

            const activeCount =
                advancedFilterNames.filter(
                    name => parameters.has(name)
                ).length;

            activeFilterCount.textContent =
                activeCount
                    ? `${activeCount} active`
                    : "Optional";
        }

        function updateBrowserUrl(
            parameters,
            replace = false
        ) {
            const query =
                parameters.toString();

            const url = query
                ? `${window.location.pathname}?${query}`
                : window.location.pathname;

            const method = replace
                ? "replaceState"
                : "pushState";

            window.history[method](
                {},
                "",
                url
            );
        }

        function showError(message) {
            if (!message) {
                searchError.hidden = true;
                searchError.textContent = "";
                return;
            }

            searchError.textContent = message;
            searchError.hidden = false;
        }

        function formatApiErrors(data) {
            if (
                !data
                || typeof data !== "object"
            ) {
                return "Could not apply the selected filters.";
            }

            const labels = {
                search: "Keywords",
                city: "Destination",
                country: "Country",
                listing_type: "Property type",
                min_price: "Minimum price",
                max_price: "Maximum price",
                bedrooms: "Bedrooms",
                beds: "Beds",
                bathrooms: "Bathrooms",
                guests: "Guests",
                amenities: "Amenities",
                check_in: "Check in",
                check_out: "Check out",
                ordering: "Sorting",
                non_field_errors: "Filters",
                detail: "Error",
            };

            const messages =
                Object.entries(data)
                    .flatMap(
                        ([field, value]) => {
                            const fieldLabel =
                                labels[field]
                                || field;

                            const values =
                                Array.isArray(value)
                                    ? value
                                    : [value];

                            return values.map(
                                message =>
                                    `${fieldLabel}: ${message}`
                            );
                        }
                    );

            return messages.join(" ");
        }

        function setLoadingState() {
            resultsSummary.textContent =
                "Searching for stays...";

            listingsGrid.innerHTML = `
                <div
                    class="
                        empty-state
                        empty-state--wide
                    "
                >
                    <p>Loading listings...</p>
                </div>
            `;
        }

        function ratingText(listing) {
            const count =
                listing.reviews_count || 0;

            const reviewText =
                count === 1
                    ? "1 review"
                    : `${count} reviews`;

            if (
                listing.rating === null
                || listing.rating === undefined
            ) {
                return (
                    `No rating · ${reviewText}`
                );
            }

            return (
                `★ ${Number(
                    listing.rating
                ).toFixed(1)} · ${reviewText}`
            );
        }

        function viewsText(listing) {
            const viewsCount = Number(
                listing.views_count || 0
            );

            return viewsCount === 1
                ? "1 view"
                : `${viewsCount} views`;
        }

        function updateFavoriteButton(
            button,
            listing
        ) {
            button.textContent =
                listing.is_favorite
                    ? "♥"
                    : "♡";

            button.classList.toggle(
                "listing-card__favorite--active",
                listing.is_favorite
            );

            button.title =
                listing.is_favorite
                    ? "Remove from favorites"
                    : "Add to favorites";

            button.setAttribute(
                "aria-label",
                button.title
            );
        }

        async function toggleFavorite(
            listing,
            button
        ) {
            const auth =
                window.TernNestAuth;

            if (
                !auth
                || (
                    !auth.getAccessToken()
                    && !auth.getRefreshToken()
                )
            ) {
                const nextUrl =
                    window.location.pathname
                    + window.location.search;

                window.location.href =
                    `/login/?next=${encodeURIComponent(
                        nextUrl
                    )}`;

                return;
            }

            button.disabled = true;

            try {
                if (
                    listing.is_favorite
                    && listing.favorite_id
                ) {
                    const response =
                        await auth.authenticatedFetch(
                            `/api/v1/listings/favorites/${listing.favorite_id}/`,
                            {
                                method: "DELETE",
                            }
                        );

                    if (!response.ok) {
                        throw new Error(
                            "Could not remove favorite."
                        );
                    }

                    listing.is_favorite = false;
                    listing.favorite_id = null;
                } else {
                    const response =
                        await auth.authenticatedFetch(
                            "/api/v1/listings/favorites/",
                            {
                                method: "POST",
                                headers: {
                                    "Content-Type":
                                        "application/json",
                                },
                                body: JSON.stringify(
                                    {
                                        listing:
                                            listing.id,
                                    }
                                ),
                            }
                        );

                    if (!response.ok) {
                        throw new Error(
                            "Could not add favorite."
                        );
                    }

                    const favorite =
                        await response.json();

                    listing.is_favorite = true;
                    listing.favorite_id =
                        favorite.id;
                }

                updateFavoriteButton(
                    button,
                    listing
                );
            } catch (error) {
                showError(
                    error.message
                );
            } finally {
                button.disabled = false;
            }
        }

        function renderListings(
            listings,
            {
                targetGrid = listingsGrid,
                updateSummary = true,
            } = {}
        ) {
            targetGrid.innerHTML = "";

            const count =
                listings.length;

            if (updateSummary) {
                resultsSummary.textContent =
                    count === 1
                        ? "1 stay found"
                        : `${count} stays found`;
            }

            if (!count) {
                targetGrid.innerHTML = `
                    <div
                        class="
                            empty-state
                            empty-state--wide
                        "
                    >
                        <h3>
                            No stays match your filters
                        </h3>

                        <p>
                            Try changing the destination,
                            dates or property details.
                        </p>

                        <button
                            class="button button--secondary"
                            type="button"
                            data-clear-search
                        >
                            Clear filters
                        </button>
                    </div>
                `;

                targetGrid
                    .querySelector(
                        "[data-clear-search]"
                    )
                    .addEventListener(
                        "click",
                        clearFilters
                    );

                return;
            }

            listings.forEach(
                listing => {
                    const card =
                        document.createElement(
                            "article"
                        );

                    card.className =
                        "listing-card";

                    card.tabIndex = 0;

                    card.setAttribute(
                        "role",
                        "link"
                    );

                    let imageUrl = "";

                    if (
                        listing.images
                        && listing.images.length
                    ) {
                        const mainImage =
                            listing.images.find(
                                image =>
                                    image.is_main
                            )
                            || listing.images[0];

                        imageUrl =
                            mainImage.image;
                    }

                    const safeTitle =
                        escapeHtml(
                            listing.title
                        );

                    const safeCity =
                        escapeHtml(
                            listing.city
                        );

                    const safeCountry =
                        escapeHtml(
                            listing.country
                        );

                    const safeImageUrl =
                        escapeHtml(
                            imageUrl
                        );

                    const price =
                        Number(
                            listing.price_per_night
                        );

                    const priceText =
                        Number.isFinite(price)
                            ? price.toFixed(2)
                            : escapeHtml(
                                listing.price_per_night
                            );

                    card.innerHTML = `
                        <div
                            class="
                                listing-card__image-wrapper
                            "
                        >
                            ${
                                imageUrl
                                    ? `
                                        <img
                                            src="${safeImageUrl}"
                                            alt="${safeTitle}"
                                            class="
                                                listing-card__image
                                            "
                                        >
                                    `
                                    : `
                                        <div
                                            class="
                                                listing-card__placeholder
                                            "
                                        >
                                            No image
                                        </div>
                                    `
                            }

                            <button
                                type="button"
                                class="
                                    listing-card__favorite
                                "
                            ></button>
                        </div>

                        <div
                            class="
                                listing-card__content
                            "
                        >
                            <div
                                class="
                                    listing-card__header
                                "
                            >
                                <h3>${safeTitle}</h3>
                            </div>

                            <p
                                class="
                                    listing-card__location
                                "
                            >
                                ${safeCity}, ${safeCountry}
                            </p>

                            <p
                                class="
                                    listing-card__reviews
                                "
                            >
                                <strong>
                                    ${escapeHtml(
                                        ratingText(
                                            listing
                                        )
                                    )}
                                </strong>
                            </p>

                            <p
                                class="
                                    listing-card__reviews
                                "
                            >
                                ${escapeHtml(
                                    viewsText(
                                        listing
                                    )
                                )}
                            </p>

                            <p
                                class="
                                    listing-card__details
                                "
                            >
                                ${listing.max_guests}
                                guests ·
                                ${listing.bedrooms}
                                bedrooms ·
                                ${listing.beds}
                                beds ·
                                ${listing.bathrooms}
                                bathrooms
                            </p>

                            <p
                                class="
                                    listing-card__price
                                "
                            >
                                <strong>
                                    €${priceText}
                                </strong>

                                <span>
                                    / night
                                </span>
                            </p>
                        </div>
                    `;

                    const favoriteButton =
                        card.querySelector(
                            ".listing-card__favorite"
                        );

                    updateFavoriteButton(
                        favoriteButton,
                        listing
                    );

                    favoriteButton.addEventListener(
                        "click",
                        async event => {
                            event.stopPropagation();

                            await toggleFavorite(
                                listing,
                                favoriteButton
                            );
                        }
                    );

                    card.addEventListener(
                        "click",
                        () => {
                            window.location.href =
                                `/listings/${listing.id}/`;
                        }
                    );

                    card.addEventListener(
                        "keydown",
                        event => {
                            if (
                                event.key === "Enter"
                            ) {
                                window.location.href =
                                    `/listings/${listing.id}/`;
                            }
                        }
                    );

                    targetGrid.appendChild(
                        card
                    );
                }
            );
        }

        function renderRecentlyViewed(
            historyItems
        ) {
            if (
                !recentlyViewedSection
                || !recentlyViewedGrid
            ) {
                return;
            }

            const seenListingIds =
                new Set();

            const listings = [];

            historyItems.forEach(
                historyItem => {
                    const listing =
                        historyItem.listing;

                    if (
                        !listing
                        || !listing.is_active
                        || seenListingIds.has(
                            listing.id
                        )
                    ) {
                        return;
                    }

                    seenListingIds.add(
                        listing.id
                    );

                    listings.push(
                        listing
                    );
                }
            );

            const recentListings =
                listings.slice(0, 6);

            if (!recentListings.length) {
                recentlyViewedSection.hidden =
                    true;

                recentlyViewedGrid.innerHTML =
                    "";

                return;
            }

            recentlyViewedSection.hidden =
                false;

            renderListings(
                recentListings,
                {
                    targetGrid:
                        recentlyViewedGrid,
                    updateSummary: false,
                }
            );
        }

        async function loadRecentlyViewed() {
            if (
                !recentlyViewedSection
                || !recentlyViewedGrid
            ) {
                return;
            }

            const auth =
                window.TernNestAuth;

            if (
                !auth
                || (
                    !auth.getAccessToken()
                    && !auth.getRefreshToken()
                )
            ) {
                recentlyViewedSection.hidden =
                    true;

                return;
            }

            try {
                const response =
                    await auth.authenticatedFetch(
                        viewHistoryApiUrl
                    );

                if (!response.ok) {
                    throw new Error(
                        "Could not load view history."
                    );
                }

                const data =
                    await response.json();

                renderRecentlyViewed(
                    getResults(data)
                );
            } catch (error) {
                recentlyViewedSection.hidden =
                    true;

                recentlyViewedGrid.innerHTML =
                    "";
            }
        }

        async function loadListings(
            parameters
        ) {
            setLoadingState();
            showError("");

            const query =
                parameters.toString();

            const url = query
                ? `${listingsApiUrl}?${query}`
                : listingsApiUrl;

            try {
                const response =
                    await apiFetch(url);

                let data = null;

                try {
                    data =
                        await response.json();
                } catch (error) {
                    data = null;
                }

                if (!response.ok) {
                    throw new Error(
                        formatApiErrors(data)
                    );
                }

                const listings =
                    getResults(data).filter(
                        listing =>
                            listing.is_active
                    );

                renderListings(
                    listings
                );
            } catch (error) {
                resultsSummary.textContent =
                    "Search failed";

                listingsGrid.innerHTML = `
                    <div
                        class="
                            empty-state
                            empty-state--wide
                        "
                    >
                        <h3>
                            Failed to load listings
                        </h3>

                        <p>
                            Check the selected filters
                            and try again.
                        </p>
                    </div>
                `;

                showError(
                    error.message
                );
            }
        }

        async function loadAmenities(
            selectedIds
        ) {
            try {
                const response =
                    await apiFetch(
                        amenitiesApiUrl
                    );

                if (!response.ok) {
                    throw new Error(
                        "Could not load amenities."
                    );
                }

                const data =
                    await response.json();

                const amenities =
                    getResults(data);

                amenitiesContainer.innerHTML =
                    "";

                if (!amenities.length) {
                    amenitiesContainer.innerHTML = `
                        <p class="filter-placeholder">
                            No amenities available.
                        </p>
                    `;

                    return;
                }

                amenities.forEach(
                    amenity => {
                        const label =
                            document.createElement(
                                "label"
                            );

                        label.className =
                            "filter-checkbox";

                        const checkbox =
                            document.createElement(
                                "input"
                            );

                        checkbox.type =
                            "checkbox";

                        checkbox.name =
                            "amenity";

                        checkbox.value =
                            String(
                                amenity.id
                            );

                        checkbox.checked =
                            selectedIds.has(
                                checkbox.value
                            );

                        checkbox.addEventListener(
                            "change",
                            updateFilterIndicator
                        );

                        const text =
                            document.createElement(
                                "span"
                            );

                        text.textContent =
                            amenity.name;

                        label.append(
                            checkbox,
                            text
                        );

                        amenitiesContainer
                            .appendChild(label);
                    }
                );
            } catch (error) {
                amenitiesContainer.innerHTML = `
                    <p class="filter-placeholder">
                        Amenities could not be loaded.
                    </p>
                `;
            }
        }

        async function submitSearch(
            replaceHistory = false
        ) {
            const parameters =
                buildQueryParameters();

            updateBrowserUrl(
                parameters,
                replaceHistory
            );

            updateFilterIndicator();

            await loadListings(
                parameters
            );
        }

        async function clearFilters() {
            form.reset();

            orderingSelect.value =
                "-created_at";

            amenitiesContainer
                .querySelectorAll(
                    'input[name="amenity"]'
                )
                .forEach(
                    checkbox => {
                        checkbox.checked = false;
                    }
                );

            advancedFilters.open = false;

            updateDateConstraints();
            showError("");

            await submitSearch();
        }

        form.addEventListener(
            "submit",
            async event => {
                event.preventDefault();

                if (!form.reportValidity()) {
                    return;
                }

                await submitSearch();
            }
        );

        form.addEventListener(
            "input",
            updateFilterIndicator
        );

        orderingSelect.addEventListener(
            "change",
            async () => {
                await submitSearch();
            }
        );

        clearFiltersButton.addEventListener(
            "click",
            clearFilters
        );

        checkInInput.addEventListener(
            "change",
            () => {
                updateDateConstraints();

                if (
                    checkOutInput.value
                    && checkInInput.value
                    && checkOutInput.value
                    <= checkInInput.value
                ) {
                    checkOutInput.value = "";
                }
            }
        );

        window.addEventListener(
            "popstate",
            async () => {
                const parameters =
                    new URLSearchParams(
                        window.location.search
                    );

                applyParametersToForm(
                    parameters
                );

                await loadListings(
                    buildQueryParameters()
                );
            }
        );

        async function initializePage() {
            const parameters =
                new URLSearchParams(
                    window.location.search
                );

            updateDateConstraints();

            applyParametersToForm(
                parameters
            );

            await loadAmenities(
                getAmenityIdsFromParameters(
                    parameters
                )
            );

            applyParametersToForm(
                parameters
            );

            await loadListings(
                buildQueryParameters()
            );

            await loadRecentlyViewed();
        }

        initializePage();
    }
);