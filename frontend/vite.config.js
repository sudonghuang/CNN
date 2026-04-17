import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  // 预包含所有用到的 Element Plus 组件，避免 Vite 懒发现时触发全页 reload
  optimizeDeps: {
    include: [
      'vue', 'vue-router', 'pinia', 'axios', 'socket.io-client',
      'echarts', 'vue-echarts',
      'element-plus/es',
      'element-plus/es/components/base/style/css',
      'element-plus/es/components/button/style/css',
      'element-plus/es/components/card/style/css',
      'element-plus/es/components/form/style/css',
      'element-plus/es/components/form-item/style/css',
      'element-plus/es/components/input/style/css',
      'element-plus/es/components/input-number/style/css',
      'element-plus/es/components/select/style/css',
      'element-plus/es/components/option/style/css',
      'element-plus/es/components/table/style/css',
      'element-plus/es/components/table-column/style/css',
      'element-plus/es/components/tag/style/css',
      'element-plus/es/components/pagination/style/css',
      'element-plus/es/components/dialog/style/css',
      'element-plus/es/components/date-picker/style/css',
      'element-plus/es/components/upload/style/css',
      'element-plus/es/components/tabs/style/css',
      'element-plus/es/components/tab-pane/style/css',
      'element-plus/es/components/empty/style/css',
      'element-plus/es/components/loading/style/css',
      'element-plus/es/components/message/style/css',
      'element-plus/es/components/scrollbar/style/css',
      'element-plus/es/components/avatar/style/css',
      'element-plus/es/components/badge/style/css',
      'element-plus/es/components/icon/style/css',
      'element-plus/es/components/divider/style/css',
      'element-plus/es/components/row/style/css',
      'element-plus/es/components/col/style/css',
      'element-plus/es/components/container/style/css',
      'element-plus/es/components/header/style/css',
      'element-plus/es/components/aside/style/css',
      'element-plus/es/components/main/style/css',
      'element-plus/es/components/menu/style/css',
      'element-plus/es/components/menu-item/style/css',
      'element-plus/es/components/sub-menu/style/css',
      'element-plus/es/components/popconfirm/style/css',
      'element-plus/es/components/image/style/css',
    ],
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
})
