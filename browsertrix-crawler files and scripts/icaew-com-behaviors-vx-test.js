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

    const { sleep, waitUntilNode, scrollAndClick, isInViewport } = ctx.Lib;

    // Click cookie consent button - wait for it to appear
    try {
      const cookieButton = await waitUntilNode(
        () => document.getElementById("CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"),
        5000
      );
      if (cookieButton) {
        await scrollAndClick(cookieButton);
        yield ctx.Lib.getState(ctx, "Clicked cookie consent button");
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
        yield ctx.Lib.getState(ctx, "Clicked banner cookie");
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
        yield ctx.Lib.getState(ctx, "Clicked survey toggle");
        await sleep(500);
      }
    } catch (e) {
      ctx.log("Survey toggle element not found or timeout");
    }

    // Click buttons within a dynamic filter
    const filterSelector = "div.c-filter.c-filter--dynamic > div.c-filter__filters";
    try {
      const parentElement = await waitUntilNode(
        () => document.querySelector(filterSelector),
        5000
      );
      if (parentElement) {
        const buttons = parentElement.querySelectorAll("button");
        for (let i = 0; i < buttons.length; i++) {
          if (isInViewport(buttons[i]) || buttons[i].offsetParent !== null) {
            await scrollAndClick(buttons[i]);
            yield ctx.Lib.getState(ctx, `Clicked filter button ${i + 1}/${buttons.length}`);
            await sleep(500);
          }
        }
      }
    } catch (e) {
      ctx.log(`Filter parent element not found: ${filterSelector}`);
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
          yield ctx.Lib.getState(ctx, `Clicked "Next" button (${i + 1}/${uniqueNextButtons.length}, iteration ${iteration + 1})`);
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
          yield ctx.Lib.getState(ctx, `Clicked more-link (iteration ${moreLinkIterations + 1})`);
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

    yield ctx.Lib.getState(ctx, "icaew-stat");
  }
}
