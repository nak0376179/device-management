import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import tailwindcss from '@tailwindcss/vite';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';

// Runs every Storybook story as a component test in a real browser (chromium via
// Playwright): each story is smoke-tested for render errors and its `play`
// function (if any) is executed. See https://storybook.js.org/docs/writing-tests
export default defineConfig({
  plugins: [
    tailwindcss(),
    storybookTest({
      configDir: fileURLToPath(new URL('./.storybook', import.meta.url)),
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  test: {
    name: 'storybook',
    browser: {
      enabled: true,
      provider: playwright(),
      headless: true,
      instances: [{ browser: 'chromium' }],
    },
  },
});
