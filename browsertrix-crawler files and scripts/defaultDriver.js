const DELAY = 2000;

module.exports = async ({
    data,
    page,
    crawler
}) => {

    await page.goto(data.url)
    // const title = await page.title();
    // console.log(`The title is: ${title}`);

    ////////// Cookiebot //////////
    // Evaluate if Cookiebot exists
    let cookieBot = await page.evaluate(() => {
        let el = document.querySelector("#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll");
        return el ? el.innerText : null;
    })

    // If Cookiebot exists, click accept button
    if (cookieBot !== null) {
        await page.evaluate(() => {
            try {
                document.querySelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll').click();
            } catch (e) {}
        });
    }

    ////////// more-link //////////
    // Evaluate if more-link exists
    let moreLink = await page.evaluate(() => {
        let el = document.querySelector(".more-link a.cta-link");
        return el ? el.innerText : null;
    })

    // If more-link exists, click the element until display is changed to "none"
    if (moreLink !== null) {
        try {

            // While loop checks for display style not equal to none. If display is anything but none, click the element.
            while (await page.evaluate(() => {
                    return window.getComputedStyle(document.querySelector(".more-link a.cta-link")).display;
                }) !== "none") {
                await page.evaluate(() => {
                    const delayA = ms => new Promise(res => setTimeout(res, ms));

                    async function moreLinkClick() { // Loop is wrapped in an async function for delay() to work
                        document.querySelector('.more-link a.cta-link').click();
                        await delayA(DELAY);
                    };

                    moreLinkClick();
                });
            };

        } catch (e) {};
    };

    ////////// tab-placeholder //////////
    // Evaluate if tab-placeholder exists
    let tabPlaceholder = await page.evaluate(() => {
        let el = document.querySelector(".tab-placeholder .tabs")
        return el ? el.innerText : null
    })

    // If tab-placeholder exists, click through tabs    
    if (tabPlaceholder !== null) {
        await page.evaluate(() => {
            try {
                const delayB = ms => new Promise(res => setTimeout(res, ms))
                const listItemsB = document.querySelector('.tab-placeholder .tabs').children;
                const listArrayB = Array.from(listItemsB);

                async function tabPlaceholderClick() { // Loop is wrapped in an async function for delay() to work
                    for (let i = 0; i < listArrayB.length; i++) {
                        listArrayB[i].children[0].click();
                        await delayB(DELAY);
                    }
                };

                tabPlaceholderClick();
            } catch (e) {}
        });
    }

    ////////// c-filter--dynamic //////////
    // Evaluate if c-filter--dynamic exists
    let cFilterDynamic = await page.evaluate(() => {
        let el = document.querySelector(".c-filter--dynamic")
        return el ? el.innerText : null
    })

    // If c-filter--dynamic exists, click through child buttons  
    if (cFilterDynamic !== null) {
        await page.evaluate(() => {
            try {
                const delayC = ms => new Promise(res => setTimeout(res, ms));
                const listItemsC = document.querySelector('.c-filter__filters').children;
                const listArrayC = Array.from(listItemsC);

                async function cFilterDynamicClick() { // Loop is wrapped in an async function for delay() to work
                    for (let i = 0; i < listArrayC.length; i++) {
                        listArrayC[i].click();
                        await delayC(DELAY);
                    }
                };

                cFilterDynamicClick();
            } catch (e) {}
        });
    }

    await crawler.loadPage(page, data);
};
