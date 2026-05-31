import type { Theme } from 'vitepress'
import DefaultTheme from 'vitepress/theme'
import { useRoute } from 'vitepress'
import imageViewer from 'vitepress-plugin-image-viewer'
import vImageViewer from 'vitepress-plugin-image-viewer/lib/vImageViewer.vue'
import CommitInfo from './components/CommitInfo.vue'
import 'viewerjs/dist/viewer.min.css'

export default {
  extends: DefaultTheme,
  enhanceApp({ app }) {
    app.component('vImageViewer', vImageViewer)
    app.component('CommitInfo', CommitInfo)
  },
  setup() {
    const route = useRoute()
    imageViewer(route, '.vp-doc', {
      filter: (img: HTMLImageElement) => {
        img.style.cursor = 'zoom-in'
        return true
      }
    })
  },
} satisfies Theme
