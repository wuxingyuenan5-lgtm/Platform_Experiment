module.exports = {
  root: true,
  extends: ['@vben'],
  rules: {
    'no-undef': 'off',
    '@typescript-eslint/no-unused-vars': [1],
  },
  overrides: [
    {
      files: ['src/views/hedgeBoard/aShare/index.vue'],
      rules: {
        // CompactSegmentTabs declares the explicit Vue model event name `update:modelValue`.
        'vue/v-on-event-hyphenation': 'off',
      },
    },
  ],
};
