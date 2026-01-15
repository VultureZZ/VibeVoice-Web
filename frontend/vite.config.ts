import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Allow both local dev and systemd service usage without hardcoding a domain.
  // Vite will only expose env vars prefixed with VITE_ to the browser; here we're
  // using loadEnv for config-time values (server/preview/proxy).
  const env = loadEnv(mode, process.cwd(), '');

  const host = env.VITE_DEV_HOST || '0.0.0.0';
  const port = Number(env.VITE_DEV_PORT || '3001');
  const apiProxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host,
      port,
      proxy: {
        '/api': {
          target: apiProxyTarget,
          changeOrigin: true,
        },
      },
    },
    preview: {
      host,
      port,
    },
  };
});
