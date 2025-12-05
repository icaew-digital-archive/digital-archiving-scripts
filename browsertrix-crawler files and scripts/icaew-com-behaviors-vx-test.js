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

    // Click buttons within a dynamic filter
    const filterSelector = "div.c-filter > div.c-filter__filters";
    
    try {
      const parentElement = await waitUntilNode(
        () => document.querySelector(filterSelector),
        5000
      );
      
      if (parentElement) {
        ctx.log(`Found filter using selector: ${filterSelector}`);
        // Wait a bit for buttons to be fully rendered
        await sleep(500);
        const buttons = parentElement.querySelectorAll("button");
        ctx.log(`Found ${buttons.length} filter button(s)`);
        if (buttons.length === 0) {
          ctx.log("No buttons found in filter element");
        } else {
          for (let i = 0; i < buttons.length; i++) {
            if (isInViewport(buttons[i]) || buttons[i].offsetParent !== null) {
              await scrollAndClick(buttons[i]);
              yield ctx.Lib.getState(ctx, `Clicked filter button ${i + 1}/${buttons.length}`);
              await sleep(1500);
            }
          }
        }
      }
    } catch (e) {
      ctx.log(`Filter element not found: ${e.message}`);
    }

    yield ctx.Lib.getState(ctx, "icaew-stat");
  }
}
