class ICAEWBehaviors {
  static init() {
    return {
      state: {},
    };
  }

  static get id() {
    return "ICAEWBehaviors";
  }

  static isMatch() {
    const pathRegex = /^(https?:\/\/)?([\w-]+\.)*icaew\.com(\/.*)?$/;
    return window.location.href.match(pathRegex);
  }

  async *run(ctx) {
    ctx.log("Running ICAEW Behaviors");

    // Track active timers for cleanup
    const activeTimers = new Set();

    // Helper to create tracked timeout
    const createTimeout = (fn, delay) => {
      const id = setTimeout(() => {
        activeTimers.delete(id);
        fn();
      }, delay);
      activeTimers.add(id);
      return id;
    };


    // Helper to check if element is visible and clickable
    const isElementClickable = (element) => {
      if (!element) return false;
      const style = getComputedStyle(element);
      return (
        style.display !== "none" &&
        style.visibility !== "hidden" &&
        style.opacity !== "0" &&
        !element.disabled &&
        element.getAttribute("aria-disabled") !== "true" &&
        !element.classList.contains("disabled") &&
        element.offsetParent !== null
      );
    };

    // Helper to wait for element with timeout
    const waitForElement = (selector, timeout = 5000) => {
      return new Promise((resolve) => {
        const startTime = Date.now();
        const check = () => {
          const element = document.querySelector(selector);
          if (element && isElementClickable(element)) {
            resolve(element);
          } else if (Date.now() - startTime < timeout) {
            createTimeout(check, 100);
          } else {
            resolve(null);
          }
        };
        check();
      });
    };

    // Function to click a cookie consent button with retry
    async function clickCookieConsentButton() {
      const buttonId = "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll";
      try {
        const element = await waitForElement(`#${buttonId}`, 3000);
        if (element) {
          element.click();
          ctx.log("Cookie consent button clicked");
        } else {
          ctx.log(`Cookie consent button not found (ID: ${buttonId})`);
        }
      } catch (error) {
        ctx.log(`Error clicking cookie consent: ${error.message}`);
      }
    }

    // Wait for cookie consent and click it
    await clickCookieConsentButton();
    // Wait for cookie dialog to disappear
    yield new Promise((resolve) => createTimeout(resolve, 500));

    // Function to click buttons within a dynamic filter with a delay
    async function* clickButtonsInFilter(selector, delay = 500) {
      try {
        const parentElement = await waitForElement(selector, 3000);
        if (!parentElement) {
          ctx.log(`Filter parent not found: ${selector}`);
          return;
        }

        const buttons = Array.from(parentElement.querySelectorAll("button")).filter(
          isElementClickable
        );

        if (buttons.length === 0) {
          ctx.log(`No clickable buttons found in filter: ${selector}`);
          return;
        }

        ctx.log(`Clicking ${buttons.length} filter buttons`);
        for (let i = 0; i < buttons.length; i++) {
          try {
            buttons[i].click();
            ctx.log(`Clicked filter button ${i + 1}/${buttons.length}`);
            yield new Promise((resolve) => createTimeout(resolve, delay));
          } catch (error) {
            ctx.log(`Error clicking filter button ${i + 1}: ${error.message}`);
          }
        }
      } catch (error) {
        ctx.log(`Error in clickButtonsInFilter: ${error.message}`);
      }
    }

    // Click dynamic filter buttons
    yield* clickButtonsInFilter(
      "div.c-filter.c-filter--dynamic > div.c-filter__filters"
    );

    // Function to click all pagination elements with stop condition
    async function* clickAllPaginationElements(selector, delay = 500, maxIterations = 50) {
      let iterations = 0;
      let previousClickableCount = 0;
      let consecutiveNoChange = 0;

      while (iterations < maxIterations) {
        try {
          // Wait a bit for DOM to update after previous clicks
          yield new Promise((resolve) => createTimeout(resolve, delay));

          // Re-query elements each iteration to avoid stale references
          const elements = Array.from(
            document.querySelectorAll(selector)
          ).filter(isElementClickable);

          if (elements.length === 0) {
            ctx.log("No more pagination elements found");
            break;
          }

          // Check if any elements are actually still enabled/clickable
          const clickableElements = elements.filter((el) => {
            // Additional check: ensure element is not in a disabled state
            const parent = el.closest(".disabled, [aria-disabled='true']");
            return !parent && isElementClickable(el);
          });

          if (clickableElements.length === 0) {
            ctx.log("All pagination elements are disabled");
            break;
          }

          // Stop if we've seen the same number of clickable elements multiple times
          // This handles the case where multiple pagination sections exist
          if (clickableElements.length === previousClickableCount && iterations > 0) {
            consecutiveNoChange++;
            if (consecutiveNoChange >= 2) {
              ctx.log("Pagination appears to be complete (no changes detected)");
              break;
            }
          } else {
            consecutiveNoChange = 0;
          }

          previousClickableCount = clickableElements.length;
          ctx.log(`Found ${clickableElements.length} clickable pagination element(s), clicking...`);

          // Click each element, re-checking before each click
          for (let i = 0; i < clickableElements.length; i++) {
            try {
              // Re-query to get fresh element reference
              const freshElements = Array.from(
                document.querySelectorAll(selector)
              ).filter(isElementClickable);
              
              if (i < freshElements.length && isElementClickable(freshElements[i])) {
                freshElements[i].click();
                ctx.log(`Clicked pagination element ${i + 1}/${clickableElements.length}`);
                // Wait longer after click for content to load
                yield new Promise((resolve) => createTimeout(resolve, delay * 2));
              }
            } catch (error) {
              ctx.log(`Error clicking pagination element ${i + 1}: ${error.message}`);
            }
          }

          iterations++;
        } catch (error) {
          ctx.log(`Error in pagination loop: ${error.message}`);
          break;
        }
      }

      if (iterations >= maxIterations) {
        ctx.log(`Reached maximum pagination iterations (${maxIterations})`);
      }
    }

    // Click all pagination elements
    yield* clickAllPaginationElements(
      "div.c-navigation-pagination > nav > a.page.next"
    );

    // Function to click an element repeatedly until it is hidden
    async function* clickUntilHidden(selector, delay = 500, maxClicks = 250) {
      let clickCount = 0;

      try {
        while (clickCount < maxClicks) {
          const element = await waitForElement(selector, 1000);
          
          if (!element || !isElementClickable(element)) {
            ctx.log(`Element no longer visible or clickable: ${selector}`);
            break;
          }

          try {
            element.click();
            clickCount++;
            ctx.log(`Clicked 'more-link' (${clickCount}/${maxClicks})`);
            yield new Promise((resolve) => createTimeout(resolve, delay));
          } catch (error) {
            ctx.log(`Error clicking element: ${error.message}`);
            break;
          }
        }

        if (clickCount >= maxClicks) {
          ctx.log(`Reached maximum clicks for 'more-link' (${maxClicks})`);
        }
      } catch (error) {
        ctx.log(`Error in clickUntilHidden: ${error.message}`);
      }
    }

    // Click the "more-link" until hidden
    yield* clickUntilHidden("div.more-link > a");

    // Cleanup: clear any remaining timers
    activeTimers.forEach((id) => clearTimeout(id));
    activeTimers.clear();

    ctx.log("ICAEW Behaviors completed");
    yield ctx.Lib.getState(ctx, "icaew-stat");
  }
}

