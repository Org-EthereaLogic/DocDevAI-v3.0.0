

/** @type { import('@storybook/vue3-vite').StorybookConfig } */
const config = {
  "stories": [
    "../src/**/*.mdx",
    "../src/**/*.stories.@(js|jsx|mjs|ts|tsx)"
  ],
  "addons": [
    "@storybook/addon-docs",
    "@storybook/addon-essentials",
    "@storybook/addon-onboarding"
  ],
  "framework": {
    "name": "@storybook/vue3-vite",
    "options": {}
  },
  "docs": {
    "autodocs": "tag",
    "defaultName": "Documentation"
  },
  "staticDirs": ["../public"],
  "viteFinal": async (config) => {
    // Add alias for @ to src
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': new URL('../src', import.meta.url).pathname
    };

    // Include CSS processing for Tailwind
    return config;
  }
};
export default config;