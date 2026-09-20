document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById(
        "listing-create-form"
    );

    const amenitiesContainer = document.getElementById(
        "amenities-list"
    );

    const amenitiesCounter = document.getElementById(
        "amenities-counter"
    );

    const message = document.getElementById(
        "listing-message"
    );

    const submitButton = document.getElementById(
        "listing-submit-button"
    );

    if (
        !form ||
        !amenitiesContainer ||
        !amenitiesCounter ||
        !message ||
        !submitButton
    ) {
        return;
    }

    const listingTypeInput =
        form.elements.namedItem("listing_type");

    const bedroomsInput =
        form.elements.namedItem("bedrooms");

    const imagesInput =
        form.elements.namedItem("images");

    const maximumAmenities = 20;
    const maximumImages = 4;

    let previousBedrooms = bedroomsInput.value || "1";
    let createdListingId = null;

    function redirectToLogin() {
        window.TernNestAuth.clearTokens();

        const nextPage = encodeURIComponent(
            window.location.pathname
        );

        window.location.href =
            `/login/?next=${nextPage}`;
    }

    if (
        !window.TernNestAuth.getAccessToken() &&
        !window.TernNestAuth.getRefreshToken()
    ) {
        redirectToLogin();
        return;
    }

    function showMessage(text, type) {
        message.textContent = text;
        message.className =
            `form-message form-message--${type}`;

        message.hidden = false;
    }

    function hideMessage() {
        message.hidden = true;
        message.textContent = "";
    }

    function setButtonState(disabled, text) {
        submitButton.disabled = disabled;
        submitButton.textContent = text;
    }

    function formatFieldName(fieldName) {
        return fieldName
            .replaceAll("_", " ")
            .replace(
                /^\w/,
                (character) => character.toUpperCase()
            );
    }

    function formatApiErrors(data) {
        if (!data) {
            return "An unexpected server error occurred.";
        }

        if (typeof data === "string") {
            return data;
        }

        if (Array.isArray(data)) {
            return data
                .map((item) => formatApiErrors(item))
                .join(" ");
        }

        if (typeof data === "object") {
            return Object.entries(data)
                .map(([field, errors]) => {
                    return (
                        `${formatFieldName(field)}: ` +
                        formatApiErrors(errors)
                    );
                })
                .join(" ");
        }

        return String(data);
    }

    async function readResponseData(response) {
        try {
            return await response.json();
        } catch (error) {
            return null;
        }
    }

    function getSelectedAmenities() {
        return Array.from(
            amenitiesContainer.querySelectorAll(
                'input[name="amenities"]:checked'
            )
        ).map((input) => Number(input.value));
    }

    function updateAmenitiesCounter() {
        amenitiesCounter.textContent =
            getSelectedAmenities().length;
    }

    function createAmenityOption(amenity) {
        const label = document.createElement("label");
        label.className = "amenity-option";

        const input = document.createElement("input");
        input.type = "checkbox";
        input.name = "amenities";
        input.value = amenity.id;

        const name = document.createElement("span");
        name.textContent = amenity.name;

        input.addEventListener("change", () => {
            const selected = getSelectedAmenities();

            if (selected.length > maximumAmenities) {
                input.checked = false;

                showMessage(
                    `You can select up to ` +
                    `${maximumAmenities} amenities.`,
                    "error"
                );
            }

            updateAmenitiesCounter();
        });

        label.append(input, name);

        return label;
    }

    async function loadAmenities() {
        try {
            const response = await fetch(
                "/api/v1/listings/amenities/"
            );

            if (!response.ok) {
                throw new Error(
                    `Request failed: ${response.status}`
                );
            }

            const data = await response.json();

            const amenities = Array.isArray(data)
                ? data
                : data.results || [];

            amenitiesContainer.replaceChildren();

            if (amenities.length === 0) {
                const emptyMessage =
                    document.createElement("p");

                emptyMessage.className =
                    "amenities-status";

                emptyMessage.textContent =
                    "No amenities have been added yet.";

                amenitiesContainer.append(emptyMessage);
                return;
            }

            amenities.forEach((amenity) => {
                amenitiesContainer.append(
                    createAmenityOption(amenity)
                );
            });
        } catch (error) {
            console.error(
                "Could not load amenities:",
                error
            );

            amenitiesContainer.replaceChildren();

            const errorMessage =
                document.createElement("p");

            errorMessage.className =
                "amenities-status amenities-status--error";

            errorMessage.textContent =
                "Could not load amenities.";

            amenitiesContainer.append(errorMessage);
        }
    }

    function synchronizeBedrooms() {
        const isStudio =
            listingTypeInput.value === "studio";

        if (isStudio) {
            if (bedroomsInput.value !== "0") {
                previousBedrooms =
                    bedroomsInput.value || "1";
            }

            bedroomsInput.value = "0";
            bedroomsInput.disabled = true;
            return;
        }

        bedroomsInput.disabled = false;

        if (bedroomsInput.value === "0") {
            bedroomsInput.value =
                previousBedrooms || "1";
        }
    }

    listingTypeInput.addEventListener(
        "change",
        synchronizeBedrooms
    );

    imagesInput.addEventListener("change", () => {
        const images = Array.from(imagesInput.files);

        if (images.length > maximumImages) {
            imagesInput.value = "";

            showMessage(
                `You can upload up to ` +
                `${maximumImages} images.`,
                "error"
            );
        }
    });

    async function uploadImages(listingId, images) {
        for (
            let index = 0;
            index < images.length;
            index += 1
        ) {
            setButtonState(
                true,
                `Uploading image ${index + 1} ` +
                `of ${images.length}...`
            );

            const imageData = new FormData();

            imageData.append(
                "image",
                images[index]
            );

            imageData.append(
                "is_main",
                String(index === 0)
            );

            const response =
                await window.TernNestAuth.authenticatedFetch(
                    `/api/v1/listings/${listingId}/images/`,
                    {
                        method: "POST",
                        body: imageData,
                    }
                );

            const responseData =
                await readResponseData(response);

            if (!response.ok) {
                throw new Error(
                    `Image ${index + 1}: ` +
                    formatApiErrors(responseData)
                );
            }
        }
    }

    async function activateListing(listingId) {
        setButtonState(
            true,
            "Activating listing..."
        );

        const response =
            await window.TernNestAuth.authenticatedFetch(
                `/api/v1/listings/${listingId}/`,
                {
                    method: "PATCH",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        is_active: true,
                    }),
                }
            );

        const responseData =
            await readResponseData(response);

        if (!response.ok) {
            throw new Error(
                formatApiErrors(responseData)
            );
        }
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        hideMessage();
        createdListingId = null;

        if (!form.reportValidity()) {
            return;
        }

        const images = Array.from(
            imagesInput.files
        );

        if (
            images.length < 1 ||
            images.length > maximumImages
        ) {
            showMessage(
                "Select between 1 and 4 images.",
                "error"
            );
            return;
        }

        const selectedAmenities =
            getSelectedAmenities();

        if (
            selectedAmenities.length >
            maximumAmenities
        ) {
            showMessage(
                `You can select up to ` +
                `${maximumAmenities} amenities.`,
                "error"
            );
            return;
        }

        const formData = new FormData(form);

        const earliestCheckInTime =
            formData.get("earliest_check_in_time");

        const latestCheckOutTime =
            formData.get("latest_check_out_time");

        if (
            earliestCheckInTime <=
            latestCheckOutTime
        ) {
            showMessage(
                "Check-in time must be later than " +
                "check-out time.",
                "error"
            );
            return;
        }

        const listingType =
            formData.get("listing_type");

        const payload = {
            title: formData.get("title").trim(),
            description:
                formData.get("description").trim(),
            listing_type: listingType,
            country: formData.get("country").trim(),
            city: formData.get("city").trim(),
            address: formData.get("address").trim(),
            earliest_check_in_time:
                earliestCheckInTime,
            latest_check_out_time:
                latestCheckOutTime,
            price_per_night:
                formData.get("price_per_night"),
            max_guests: Number(
                formData.get("max_guests")
            ),
            bedrooms:
                listingType === "studio"
                    ? 0
                    : Number(bedroomsInput.value),
            beds: Number(formData.get("beds")),
            bathrooms: Number(
                formData.get("bathrooms")
            ),
            amenities: selectedAmenities,
            is_active: false,
        };

        setButtonState(
            true,
            "Creating listing..."
        );

        try {
            const response =
                await window.TernNestAuth.authenticatedFetch(
                    "/api/v1/listings/",
                    {
                        method: "POST",
                        headers: {
                            "Content-Type":
                                "application/json",
                        },
                        body: JSON.stringify(payload),
                    }
                );

            if (response.status === 401) {
                redirectToLogin();
                return;
            }

            const responseData =
                await readResponseData(response);

            if (!response.ok) {
                throw new Error(
                    formatApiErrors(responseData)
                );
            }

            createdListingId = responseData.id;

            if (!createdListingId) {
                throw new Error(
                    "The API did not return a listing ID."
                );
            }

            await uploadImages(
                createdListingId,
                images
            );

            await activateListing(createdListingId);

            showMessage(
                `Listing #${createdListingId} ` +
                "was published successfully.",
                "success"
            );

            form.reset();
            updateAmenitiesCounter();

            window.setTimeout(
                synchronizeBedrooms,
                0
            );
        } catch (error) {
            console.error(
                "Listing creation failed:",
                error
            );

            if (createdListingId) {
                showMessage(
                    `Listing #${createdListingId} was saved ` +
                    "as an inactive draft. " +
                    error.message,
                    "error"
                );
            } else {
                showMessage(
                    error.message ||
                    "Could not create the listing.",
                    "error"
                );
            }
        } finally {
            setButtonState(
                false,
                "Publish listing"
            );
        }
    });

    synchronizeBedrooms();
    loadAmenities();
});