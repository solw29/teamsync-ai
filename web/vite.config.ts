import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
export default defineConfig({plugins:[react(),tailwind()],server:{proxy:{'/api':'http://127.0.0.1:8090'}},test:{environment:'jsdom'}});
