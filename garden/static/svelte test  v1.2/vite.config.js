import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path'; // 1. Add this import line


export default defineConfig({
  base: '/garden/',
  plugins: [svelte()],
  resolve: {
    alias: {
      // 2. Add this alias definition
      $lib: path.resolve(__dirname, './src/lib'),
    },
  },
});