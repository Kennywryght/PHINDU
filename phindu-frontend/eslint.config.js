import js from "@eslint/js";
import svelte from "eslint-plugin-svelte";
import globals from "globals";

export default [
  js.configs.recommended,
  ...svelte.configs["flat/recommended"],
  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    rules: {
      // ── Errors ─────────────────────────────────────────────
      "no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-undef": "error",
      "no-console": "off", // allow console.error/warn in dev
      "no-alert": "off",   // alert() → prefer toast in future
      "no-debugger": "error",

      // ── Style (soft warnings) ──────────────────────────────
      eqeqeq: ["warn", "always", { null: "ignore" }],
      "no-var": "warn",
      "prefer-const": "warn",
    },
  },
  {
    // Test files can use vitest globals
    files: ["**/*.test.js", "**/*.spec.js", "tests/**/*.js"],
    languageOptions: {
      globals: {
        ...globals.node,
        describe: "readonly",
        it: "readonly",
        test: "readonly",
        expect: "readonly",
        beforeEach: "readonly",
        afterEach: "readonly",
        vi: "readonly",
      },
    },
  },
  {
    ignores: [
      "node_modules/",
      "dist/",
      "build/",
      ".svelte-kit/",
      "coverage/",
      "package-lock.json",
    ],
  },
];