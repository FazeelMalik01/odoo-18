export default [
  {
    files: ["**/*.js"],
    languageOptions: {
      ecmaVersion: "2024",
      sourceType: "module",
      globals: {
        odoo: "readonly",
        rpc: "readonly",
        registry: "readonly",
        OpenLocationCode: "readonly",
        navigator: "readonly",
        document: "readonly",
        console: "readonly",
        window: "readonly",
        alert: "readonly",
        module: "readonly",
        $: "readonly",
        jQuery: "readonly",
      },
    },
    rules: {
      "no-undef": "error",
      "no-restricted-globals": ["error", "event", "self"],
      "no-const-assign": "error",
      "no-debugger": "error",
      "no-dupe-class-members": "error",
      "no-dupe-keys": "error",
      "no-dupe-args": "error",
      "no-dupe-else-if": "error",
      "no-unsafe-negation": "error",
      "no-duplicate-imports": "error",
      "valid-typeof": "error",
      "no-unused-vars": [
        "error",
        { "vars": "all", "args": "none", "ignoreRestSiblings": false, "caughtErrors": "all" }
      ],
      curly: ["error", "all"],
      "no-restricted-syntax": ["error", "PrivateIdentifier"],
      "prefer-const": ["error", { destructuring: "all", ignoreReadBeforeAssign: true }],
    },
  },
];
