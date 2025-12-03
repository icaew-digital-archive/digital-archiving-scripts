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

    // Function to click buttons within a dynamic filter with a delay
    function clickButtonsInFilter(selector, delay = 500) {
      const parentElement = document.querySelector(selector);

      if (parentElement) {
        const buttons = parentElement.querySelectorAll("button");

        function clickButtonAtIndex(index) {
          if (index < buttons.length) {
            buttons[index].click();
            setTimeout(() => clickButtonAtIndex(index + 1), delay);
          }
        }

        clickButtonAtIndex(0);
      } else {
        console.log(`Parent element with selector '${selector}' not found`);
      }
    }

    // Trigger the function for "dynamic filter" buttons
    clickButtonsInFilter(
      "div.c-filter.c-filter--dynamic > div.c-filter__filters"
    );

    // Function to click all matching elements with a delay
    function clickAllElementsWithDelay(selector, delay = 500) {
      const elements = document.querySelectorAll(selector);

      if (elements.length === 0) {
        console.log(`No elements found with selector '${selector}'`);
        return;
      }

      // Click each element sequentially with a delay
      function clickElementAtIndex(index) {
        if (index < elements.length) {
          elements[index].click();
          setTimeout(() => clickElementAtIndex(index + 1), delay);
        } else {
          // After clicking all elements, check again for new ones (in case pagination loaded more)
          setTimeout(() => clickAllElementsWithDelay(selector, delay), delay);
        }
      }

      clickElementAtIndex(0);
    }

    // Start clicking all "pagination control" elements with a delay
    clickAllElementsWithDelay(
      "div.c-navigation-pagination > nav > a.page.next"
    );

    // Function to click an element repeatedly until it is hidden
    function clickUntilHidden(selector, delay = 500) {
      const interval = setInterval(() => {
        const element = document.querySelector(selector);

        if (element && getComputedStyle(element).display !== "none") {
          element.click();
        } else {
          console.log(
            `Element with selector '${selector}' not found or hidden`
          );
          clearInterval(interval);
        }
      }, delay);
    }

    // Call the function for the "more-link"
    clickUntilHidden("div.more-link > a");

    yield ctx.Lib.getState(ctx, "icaew-stat");
  }
}
