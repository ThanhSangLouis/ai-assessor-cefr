// ESLint for the browser scripts in src/aicefr/api/static.
// The pages load these files as classic <script> tags (no bundler, no modules), so
// helpers defined at the top level of common.js are shared globals for the other files.
import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: ["src/aicefr/api/static/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: { ...globals.browser },
    },
    rules: {
      // Each page script sees the globals of the scripts loaded before it; ESLint
      // checks one file at a time and cannot see that order.
      "no-undef": "off",
      "no-unused-vars": ["warn", { args: "none", caughtErrors: "none" }],
    },
  },
  {
    files: ["src/aicefr/api/static/sw.js"],
    languageOptions: { globals: { ...globals.serviceworker } },
  },
];
