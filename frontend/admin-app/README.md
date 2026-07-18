# @palms/admin-app

Admin portal for the Palms platform. Served under the `/admin/` base path.

## Stack

React + TypeScript + Vite, Material UI, TanStack Query, Zustand, React Hook Form, Zod, TanStack Table, Recharts, React Dropzone, and `@palms/shared`.

## Commands

From `frontend/`:

```bash
npm run dev:admin
npm run build --workspace=@palms/admin-app
npm run test --workspace=@palms/admin-app
```

Dev server proxies `/api` and `/health` to `http://localhost:8000`.
