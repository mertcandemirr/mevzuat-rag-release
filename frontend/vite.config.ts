import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({plugins:[react(),tailwindcss()],server:{proxy:{'/api':{target:'http://127.0.0.1:8011',changeOrigin:false,timeout:130000,proxyTimeout:130000}}},preview:{proxy:{'/api':{target:'http://127.0.0.1:8011'}}},resolve:{alias:{'@':new URL('./src',import.meta.url).pathname}}});
