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

    // Click buttons within a dynamic filter
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

    yield { msg: "icaew-stat" };
  }
}
