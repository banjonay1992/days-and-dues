// Run this function through the Playwright browser tool after opening the site home page.
async (page) => {
  const base = new URL('./', page.url()).href;
  const failures = [], consoleErrors = [];
  const onError = error => consoleErrors.push(String(error));
  const onConsole = message => {
    if (['error', 'warning'].includes(message.type())) consoleErrors.push(message.text());
  };
  page.on('pageerror', onError);
  page.on('console', onConsole);
  const check = (condition, message) => { if (!condition) throw Error(message); };
  const routes = ['', 'features.html', 'for-your-work.html', 'how-it-works.html',
    'pricing.html', 'faq.html', 'support.html', 'privacy.html', 'terms.html'];
  try {
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({width, height: 900});
      for (const route of routes) {
        const response = await page.goto(base + route);
        await page.locator('img').evaluateAll(images => images.forEach(image => image.loading = 'eager'));
        await page.waitForFunction(() => Array.from(document.images).every(image => image.complete));
        const state = await page.evaluate(() => ({
          overflow: document.documentElement.scrollWidth > innerWidth,
          brokenImages: Array.from(document.images).filter(image => !image.naturalWidth).map(image => image.src),
          headings: document.querySelectorAll('h1').length
        }));
        if (response.status() !== 200 || state.overflow || state.brokenImages.length || state.headings !== 1)
          failures.push({route: route || 'home', width, status: response.status(), ...state});
      }
    }
    check(failures.length === 0, JSON.stringify(failures));
    await page.setViewportSize({width: 390, height: 844});
    await page.goto(base);
    for (const screen of ['work', 'clients', 'money', 'today']) {
      await page.locator(`[data-screen="${screen}"]`).click();
      check(await page.locator('#tour-image').getAttribute('src') === `assets/screens/${screen}.jpg`, 'Tour image mismatch');
      check(await page.locator('[data-screen][aria-pressed=true]').count() === 1, 'Tour state is ambiguous');
      check((await page.locator('#tour-caption').innerText()).toLowerCase().startsWith(screen), 'Tour caption mismatch');
    }
    await page.keyboard.press('End');
    check(await page.locator('#tour-image').getAttribute('src') === 'assets/screens/money.jpg', 'End key failed');
    await page.keyboard.press('ArrowRight');
    check(await page.locator('#tour-image').getAttribute('src') === 'assets/screens/today.jpg', 'Forward wrap failed');
    await page.keyboard.press('ArrowLeft');
    check(await page.locator('#tour-image').getAttribute('src') === 'assets/screens/money.jpg', 'Backward wrap failed');
    await page.keyboard.press('Home');
    check(await page.locator('#tour-image').getAttribute('src') === 'assets/screens/today.jpg', 'Home key failed');
    await page.locator('.mobile-menu summary').click();
    check(await page.locator('.mobile-menu').getAttribute('open') !== null, 'Menu did not open');
    await page.keyboard.press('Escape');
    check(await page.locator('.mobile-menu').getAttribute('open') === null, 'Menu did not close');
    check(await page.locator('.mobile-menu summary').evaluate(element => element === document.activeElement), 'Focus was not restored');
    await page.locator('.mobile-menu summary').click();
    await page.getByRole('navigation', {name: 'Mobile', exact: true}).getByRole('link', {name: 'Pricing', exact: true}).click();
    await page.waitForURL(base + 'pricing.html');
    const question = page.getByText('Do I need to cancel the three-day app trial?', {exact: true});
    await question.click();
    check(await question.evaluate(element => element.parentElement.open), 'FAQ did not open');
    await question.press('Enter');
    check(!await question.evaluate(element => element.parentElement.open), 'FAQ did not close');
    await page.goto(base + 'features.html');
    const contrast = await page.locator('.note-paper').evaluate(card => {
      const luminance = value => {
        const rgb = value.match(/[\d.]+/g).slice(0, 3).map(Number).map(channel => {
          const fraction = channel / 255;
          return fraction <= 0.04045 ? fraction / 12.92 : ((fraction + 0.055) / 1.055) ** 2.4;
        });
        return rgb[0] * 0.2126 + rgb[1] * 0.7152 + rgb[2] * 0.0722;
      };
      const background = luminance(getComputedStyle(card).backgroundColor);
      return Array.from(card.querySelectorAll('p, .eyebrow')).map(element => {
        const foreground = luminance(getComputedStyle(element).color);
        return (Math.max(background, foreground) + 0.05) / (Math.min(background, foreground) + 0.05);
      });
    });
    check(contrast.every(ratio => ratio >= 4.5), 'Day-note text contrast below 4.5:1');
    check(consoleErrors.length === 0, JSON.stringify(consoleErrors));
    return {base, responsiveChecks: 36, tour: 'passed', menu: 'passed', faq: 'passed', noteContrast: 'passed', failures, consoleErrors};
  } finally {
    page.off('pageerror', onError);
    page.off('console', onConsole);
  }
}
