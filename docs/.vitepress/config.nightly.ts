import { defineConfig } from 'vitepress'
import baseConfig from './config.base'

export default defineConfig({
  ...baseConfig,
  base: '/librislog/next/',
})
