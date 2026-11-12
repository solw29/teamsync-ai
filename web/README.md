# TeamSync Review Dashboard

```bash
npm ci --cache /workspace/.cache/npm
npm run dev
npm run build
npm test
```

Routes: /dashboard, /pulls/:id, /evaluation, /data. Default data is an anonymized real D10 measurement bundle. Import actual `docs/report-example.json` in Data to see commit links and original code. Imports are validated and kept in memory; refresh returns to demo data.

Static deployment: choose `web/` as project root, build `npm run build`, output `dist/`. Set history fallback to index.html (Vercel config included). No environment secrets are needed. Do not copy private reports into public/ or dist/. Deployment has not been performed automatically.
