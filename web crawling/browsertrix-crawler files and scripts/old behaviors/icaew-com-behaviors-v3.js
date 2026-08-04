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

    // Pure JavaScript helper functions
    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
    
    const waitUntilNode = async (selectorFn, timeout = 5000) => {
      const startTime = Date.now();
      while (Date.now() - startTime < timeout) {
        const element = selectorFn();
        if (element) return element;
        await sleep(100);
      }
      throw new Error("Timeout waiting for element");
    };

    const isInViewport = (element) => {
      const rect = element.getBoundingClientRect();
      return (
        rect.top >= 0 &&
        rect.left >= 0 &&
        rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
        rect.right <= (window.innerWidth || document.documentElement.clientWidth)
      );
    };

    const scrollAndClick = async (element) => {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await sleep(300);
      element.click();
    };

    // Click cookie consent button - wait for it to appear
    try {
      const cookieButton = await waitUntilNode(
        () => document.getElementById("CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"),
        5000
      );
      if (cookieButton) {
        await scrollAndClick(cookieButton);
        yield { msg: "Clicked cookie consent button" };
        await sleep(500);
      }
    } catch (e) {
      ctx.log("Cookie consent button not found or timeout");
    }

    // Click banner cookie element - wait for it to appear
    try {
      const bannerCookie = await waitUntilNode(
        () => document.querySelector("#banner-cookie > span"),
        3000
      );
      if (bannerCookie) {
        await scrollAndClick(bannerCookie);
        yield { msg: "Clicked banner cookie" };
        await sleep(500);
      }
    } catch (e) {
      ctx.log("Banner cookie element not found or timeout");
    }

    // Click survey toggle element - wait for it to appear
    try {
      const surveyToggle = await waitUntilNode(
        () => document.getElementById("hj-survey-toggle-1"),
        3000
      );
      if (surveyToggle) {
        await scrollAndClick(surveyToggle);
        yield { msg: "Clicked survey toggle" };
        await sleep(500);
      }
    } catch (e) {
      ctx.log("Survey toggle element not found or timeout");
    }

    // Click buttons within a dynamic filter (using working pure JS implementation)
    const filterSelector = "div.c-filter > div.c-filter__filters";
    
    try {
      const parentElement = await waitUntilNode(
        () => document.querySelector(filterSelector),
        5000
      );
      
      if (parentElement) {
        ctx.log(`Found filter using selector: ${filterSelector}`);
        // Wait a bit for buttons to be fully rendered and interactive
        await sleep(1000);
        
        // Re-query buttons to ensure we have fresh references
        const buttons = parentElement.querySelectorAll("button");
        ctx.log(`Found ${buttons.length} filter button(s)`);
        
        if (buttons.length === 0) {
          ctx.log("No buttons found in filter element");
        } else {
          for (let i = 0; i < buttons.length; i++) {
            const button = buttons[i];
            
            // Check if button is disabled
            const isDisabled = button.classList.contains('disabled') || 
                            button.hasAttribute('disabled') ||
                            button.getAttribute('aria-disabled') === 'true' ||
                            button.disabled;
            
            if (isDisabled) {
              ctx.log(`Filter button ${i + 1}/${buttons.length} is disabled, skipping`);
              continue;
            }
            
            // Check visibility and clickability
            const style = getComputedStyle(button);
            const isVisible = style.display !== "none" && style.visibility !== "hidden";
            const isClickable = isVisible && (isInViewport(button) || button.offsetParent !== null);
            
            if (isClickable) {
              ctx.log(`Clicking filter button ${i + 1}/${buttons.length}`);
              await scrollAndClick(button);
              yield { msg: `Clicked filter button ${i + 1}/${buttons.length}` };
              
              // Wait for filter to apply and content to update
              await sleep(2000);
              
              // Wait a bit more to ensure any animations/transitions complete
              await sleep(500);
            } else {
              ctx.log(`Filter button ${i + 1}/${buttons.length} is not clickable (not visible or not in viewport)`);
            }
          }
        }
      }
    } catch (e) {
      ctx.log(`Filter element not found: ${e.message}`);
    }

    // Click pagination "Next" buttons repeatedly to go through all pages
    // Use multiple selectors to find "Next" buttons
    const nextButtonSelectors = [
      "div.c-navigation-pagination > nav > a.page.next",
      "div.c-navigation-pagination nav a.page.next",
      "nav > a.page.next"
    ];
    let maxIterations = 200;
    let iteration = 0;

    while (iteration < maxIterations) {
      // Find all "Next" buttons using multiple selectors
      let nextButtons = [];
      for (const selector of nextButtonSelectors) {
        const found = document.querySelectorAll(selector);
        nextButtons.push(...Array.from(found));
      }
      // Remove duplicates
      const uniqueNextButtons = Array.from(new Set(nextButtons));

      if (uniqueNextButtons.length === 0) {
        ctx.log(`No "Next" buttons found (iteration ${iteration + 1})`);
        break;
      }

      let clickedAny = false;
      let allDisabled = true;
      
      // Click all "Next" buttons found (in case there are multiple pagination sections)
      for (let i = 0; i < uniqueNextButtons.length; i++) {
        const nextButton = uniqueNextButtons[i];
        const style = getComputedStyle(nextButton);
        
        // Check if button is disabled
        const isDisabled = nextButton.classList.contains('disabled') || 
                          nextButton.hasAttribute('disabled') ||
                          nextButton.getAttribute('aria-disabled') === 'true';
        
        if (isDisabled) {
          ctx.log(`"Next" button ${i + 1} is disabled, skipping`);
          continue;
        }
        
        allDisabled = false;
        
        // Check if button is visible and clickable
        if (style.display !== "none" && style.visibility !== "hidden" && 
            (isInViewport(nextButton) || nextButton.offsetParent !== null)) {
          await scrollAndClick(nextButton);
          clickedAny = true;
          yield { msg: `Clicked "Next" button (${i + 1}/${uniqueNextButtons.length}, iteration ${iteration + 1})` };
          // Wait 1 second for content to load
          await sleep(1000);
          // Wait 1 second before clicking next
          await sleep(1000);
        }
      }

      // Stop if all buttons are disabled
      if (allDisabled) {
        ctx.log("All 'Next' buttons are disabled. Stopping.");
        break;
      }

      if (!clickedAny) {
        ctx.log("No clickable 'Next' buttons found");
        break;
      }
      iteration++;
    }

    // Click "more-link" element repeatedly until it is hidden
    const moreLinkSelector = "div.more-link > a";
    let moreLinkIterations = 0;
    const maxMoreLinkIterations = 100;

    while (moreLinkIterations < maxMoreLinkIterations) {
      const element = document.querySelector(moreLinkSelector);

      if (element) {
        const style = getComputedStyle(element);
        if (style.display !== "none" && style.visibility !== "hidden") {
          await scrollAndClick(element);
          yield { msg: `Clicked more-link (iteration ${moreLinkIterations + 1})` };
          await sleep(800); // Longer wait for content to expand
          moreLinkIterations++;
        } else {
          ctx.log("More-link element is hidden");
          break;
        }
      } else {
        ctx.log("More-link element not found");
        break;
      }
    }

    yield { msg: "icaew-stat" };
  }
}
