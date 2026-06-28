import { fileURLToPath, URL } from 'node:url';
import { defineConfig } from 'vitest/config';
import { playwright } from '@vitest/browser-playwright';
import tailwindcss from '@tailwindcss/vite';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';

const alias = { '@': fileURLToPath(new URL('./src', import.meta.url)) };

// Two test projects run under one `vitest`:
//
//   unit       — fast Node tests for pure logic (src/**/*.test.ts).
//   storybook  — every Storybook story rendered in a real browser (chromium via
//                Playwright); stories with a `play` function are also driven as
//                interaction tests. See https://storybook.js.org/docs/writing-tests
//
// Run all: `npm test`. One project: `vitest run --project unit`.
export default defineConfig({
  test: {
    projects: [
      {
        resolve: { alias },
        test: {
          name: 'unit',
          environment: 'node',
          include: ['src/**/*.{test,spec}.{ts,tsx}'],
        },
      },
      {
        plugins: [
          tailwindcss(),
          storybookTest({
            configDir: fileURLToPath(new URL('./.storybook', import.meta.url)),
          }),
        ],
        resolve: { alias },
        test: {
          name: 'storybook',
          browser: {
            enabled: true,
            provider: playwright(),
            headless: true,
            instances: [{ browser: 'chromium' }],
          },
        },
      },
    ],
  },
});
