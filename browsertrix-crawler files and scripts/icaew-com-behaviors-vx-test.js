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

    // Change navbar to pink - FOR TESTING
    // Select all elements matching the specified selector
    //    var navLinks = document.querySelectorAll('#u-nav .u-nav--links > li > a');

    // Iterate over each element and set its color to pink
    //    navLinks.forEach(function(link) {
    //        link.style.color = 'pink';
    //    });

    // Function to click a cookie consent button
    function clickCookieConsentButton() {
      const buttonId = "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll";
      const element = document.getElementById(buttonId);

      if (element) {
        element.click();
      } else {
        console.log(`Element with ID '${buttonId}' not found`);
      }
    }

    // Trigger the function
    clickCookieConsentButton();

    // Function to click banner cookie element
    function clickBannerCookie() {
      const element = document.querySelector("#banner-cookie > span");

      if (element) {
        element.click();
      } else {
        console.log(`Element with selector '#banner-cookie > span' not found`);
      }
    }

    // Trigger the function
    clickBannerCookie();

    // Function to click survey toggle element
    function clickSurveyToggle() {
      const element = document.getElementById("hj-survey-toggle-1");

      if (element) {
        element.click();
      } else {
        console.log(`Element with ID 'hj-survey-toggle-1' not found`);
      }
    }

    // Trigger the function
    clickSurveyToggle();

    // Function to click buttons within a dynamic filter with a delay
    const { sleep } = ctx.Lib;
    const filterSelector = "div.c-filter.c-filter--dynamic > div.c-filter__filters";
    const parentElement = document.querySelector(filterSelector);

    if (parentElement) {
      const buttons = parentElement.querySelectorAll("button");
      for (let i = 0; i < buttons.length; i++) {
        buttons[i].click();
        yield ctx.Lib.getState(ctx, `Clicked filter button ${i + 1}/${buttons.length}`);
        await sleep(500);
      }
    } else {
      ctx.log(`Parent element with selector '${filterSelector}' not found`);
    }

    // Function to click all matching elements with a delay (pagination)
    const paginationSelector = "div.c-navigation-pagination > nav > a.page.next";
    let maxIterations = 50; // Prevent infinite loops
    let iteration = 0;

    while (iteration < maxIterations) {
      const elements = document.querySelectorAll(paginationSelector);

      if (elements.length === 0) {
        ctx.log(`No pagination elements found with selector '${paginationSelector}'`);
        break;
      }

      let clickedAny = false;
      for (let i = 0; i < elements.length; i++) {
        elements[i].click();
        clickedAny = true;
        yield ctx.Lib.getState(ctx, `Clicked pagination element ${i + 1}/${elements.length} (iteration ${iteration + 1})`);
        await sleep(500);
      }

      if (!clickedAny) {
        break;
      }

      // Wait a bit for new content to load
      await sleep(1000);
      iteration++;
    }

    // Function to click an element repeatedly until it is hidden
    const moreLinkSelector = "div.more-link > a";
    let moreLinkIterations = 0;
    const maxMoreLinkIterations = 100;

    while (moreLinkIterations < maxMoreLinkIterations) {
      const element = document.querySelector(moreLinkSelector);

      if (element && getComputedStyle(element).display !== "none") {
        element.click();
        yield ctx.Lib.getState(ctx, `Clicked more-link (iteration ${moreLinkIterations + 1})`);
        await sleep(500);
        moreLinkIterations++;
      } else {
        ctx.log(`Element with selector '${moreLinkSelector}' not found or hidden`);
        break;
      }
    }

    // Function to click all Highcharts chart menu buttons
    const highchartsSelector = "div.highcharts-a11y-proxy-container-after > div.highcharts-a11y-proxy-group.highcharts-a11y-proxy-group-chartMenu > button";
    let highchartsIterations = 0;
    const maxHighchartsIterations = 20;

    while (highchartsIterations < maxHighchartsIterations) {
      const buttons = document.querySelectorAll(highchartsSelector);

      if (buttons.length === 0) {
        ctx.log(`No Highcharts buttons found with selector '${highchartsSelector}'`);
        break;
      }

      let clickedAny = false;
      for (let i = 0; i < buttons.length; i++) {
        const style = window.getComputedStyle(buttons[i]);
        if (style.display !== "none" && style.visibility !== "hidden" && !buttons[i].disabled) {
          buttons[i].click();
          clickedAny = true;
          yield ctx.Lib.getState(ctx, `Clicked Highcharts button ${i + 1}/${buttons.length} (iteration ${highchartsIterations + 1})`);
          await sleep(300);
        }
      }

      if (!clickedAny) {
        break;
      }

      // Wait a bit for new buttons to potentially appear
      await sleep(1000);
      highchartsIterations++;
    }

    yield ctx.Lib.getState(ctx, "icaew-stat");
  }
}
