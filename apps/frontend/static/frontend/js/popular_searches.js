document.addEventListener(
    "DOMContentLoaded",
    () => {
        const popularSearchesApiUrl =
            "/api/v1/listings/popular-searches/";

        const section =
            document.getElementById(
                "popular-searches-section"
            );

        const list =
            document.getElementById(
                "popular-searches-list"
            );

        const form =
            document.getElementById(
                "listing-search-form"
            );

        const searchInput =
            form?.querySelector(
                '[name="search"]'
            );

        const advancedFilters =
            document.getElementById(
                "advanced-filters"
            );

        if (
            !section
            || !list
            || !form
            || !searchInput
        ) {
            return;
        }

        function getResults(data) {
            if (Array.isArray(data)) {
                return data;
            }

            return data.results || [];
        }

        function hidePopularSearches() {
            section.hidden = true;
            list.innerHTML = "";
        }

        function usePopularSearch(query) {
            searchInput.value = query;

            if (advancedFilters) {
                advancedFilters.open = true;
            }

            searchInput.dispatchEvent(
                new Event(
                    "input",
                    {
                        bubbles: true,
                    }
                )
            );

            if (
                typeof form.requestSubmit
                === "function"
            ) {
                form.requestSubmit();
                return;
            }

            form.dispatchEvent(
                new Event(
                    "submit",
                    {
                        bubbles: true,
                        cancelable: true,
                    }
                )
            );
        }

        function renderPopularSearches(
            searches
        ) {
            const validSearches =
                searches
                    .filter(
                        item => (
                            item
                            && item.query
                            && Number(
                                item.search_count
                            ) > 0
                        )
                    )
                    .slice(0, 5);

            if (!validSearches.length) {
                hidePopularSearches();
                return;
            }

            list.innerHTML = "";

            validSearches.forEach(
                item => {
                    const query = String(
                        item.query
                    );

                    const count = Number(
                        item.search_count
                    );

                    const button =
                        document.createElement(
                            "button"
                        );

                    button.type = "button";

                    button.className = (
                        "popular-searches-"
                        + "strip__button"
                    );

                    button.setAttribute(
                        "aria-label",
                        (
                            `Search for ${query}. `
                            + `${count} searches.`
                        )
                    );

                    const queryText =
                        document.createElement(
                            "span"
                        );

                    queryText.textContent =
                        query;

                    const countText =
                        document.createElement(
                            "span"
                        );

                    countText.className = (
                        "popular-searches-"
                        + "strip__count"
                    );

                    countText.textContent =
                        `(${count})`;

                    button.append(
                        queryText,
                        countText
                    );

                    button.addEventListener(
                        "click",
                        () => {
                            usePopularSearch(
                                query
                            );
                        }
                    );

                    list.appendChild(
                        button
                    );
                }
            );

            section.hidden = false;
        }

        async function loadPopularSearches() {
            try {
                const response = await fetch(
                    popularSearchesApiUrl
                );

                if (!response.ok) {
                    throw new Error(
                        "Could not load popular searches."
                    );
                }

                const data =
                    await response.json();

                renderPopularSearches(
                    getResults(data)
                );
            } catch (error) {
                hidePopularSearches();
            }
        }

        loadPopularSearches();
    }
);