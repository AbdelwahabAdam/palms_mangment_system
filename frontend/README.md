# Palms Frontend

npm workspaces monorepo for the Palms public site and admin portal.

## Workspaces

- `@palms/shared` — typed API contracts, Axios client factory, Zod schemas, and TanStack Query key factories
- `@palms/public-app` — public React application (Lifemaker palm discovery)
- `@palms/admin-app` — admin React application (Material UI portal under `/admin/`)

## Install

```bash
cd frontend
npm install
```

## Shared package commands

```bash
npm run test --workspace=@palms/shared
npm run lint --workspace=@palms/shared
npm run typecheck --workspace=@palms/shared
npm run build --workspace=@palms/shared
```

Public app:

```bash
npm run dev:public
npm run build:public
npm run test --workspace=@palms/public-app
```

Root shortcuts:

```bash
npm test
npm run lint
npm run typecheck
npm run build
npm run dev:admin
npm run build:admin
npm run test:admin
```

## Consuming `@palms/shared`

```ts
import { createPalmsClient, queryKeys } from "@palms/shared";

const client = createPalmsClient({
  env: import.meta.env,
  onAuthFailure: () => {
    // redirect to login in the admin app
  },
});

const me = await client.auth.me();
const results = await client.public.search({ query: "PALM-001" });
```

Pass Vite env through `createPalmsClient({ env: import.meta.env })`. Supported variables:

- `VITE_API_BASE_URL` (default `/api/v1`)
- `VITE_API_TIMEOUT_MS` (default `15000`)

The shared package never reads browser globals. Tests inject an Axios adapter and optional `FormData` factory.
