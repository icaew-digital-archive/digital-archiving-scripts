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

    // Click pagination elements - click all pagination links (Previous, page numbers, Next)
    // Track clicked URLs to avoid duplicates
    const paginationSelector = "div.c-navigation-pagination > nav > a";
    const clickedUrls = new Set();
    const clickedTexts = new Set(); // Also track by text for page numbers
    let maxIterations = 100;
    let iteration = 0;

    while (iteration < maxIterations) {
      const elements = document.querySelectorAll(paginationSelector);

      if (elements.length === 0) {
        ctx.log(`No pagination elements found (iteration ${iteration + 1})`);
        break;
      }

      let clickedAny = false;
      for (let i = 0; i < elements.length; i++) {
        const element = elements[i];
        const href = element.href || element.getAttribute('href');
        const text = element.textContent?.trim();
        
        // Skip if we've already clicked this URL or this text (for page numbers)
        if ((href && clickedUrls.has(href)) || (text && clickedTexts.has(text))) {
          continue;
        }

        // Check if element is visible and clickable
        const style = getComputedStyle(element);
        if (style.display !== "none" && style.visibility !== "hidden" && 
            (isInViewport(element) || element.offsetParent !== null)) {
          await scrollAndClick(element);
          if (href) clickedUrls.add(href);
          if (text) clickedTexts.add(text);
          clickedAny = true;
          yield ctx.Lib.getState(ctx, `Clicked pagination "${text || href}" (${i + 1}/${elements.length}, iteration ${iteration + 1})`);
          await sleep(800);
        }
      }

      if (!clickedAny) {
        ctx.log("No new pagination elements to click");
        break;
      }

      // Wait for new content to load
      await sleep(2000);
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
