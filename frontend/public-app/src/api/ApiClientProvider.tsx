import { createContext, useContext, useMemo, type ReactNode } from "react";

import { createAppClient, type PalmsClient } from "@/api/client";

const ApiClientContext = createContext<PalmsClient | null>(null);

export function ApiClientProvider({
  client,
  children,
}: {
  client?: PalmsClient;
  children: ReactNode;
}) {
  const value = useMemo(() => client ?? createAppClient(), [client]);
  return (
    <ApiClientContext.Provider value={value}>{children}</ApiClientContext.Provider>
  );
}

export function useApiClient(): PalmsClient {
  const client = useContext(ApiClientContext);
  if (!client) {
    throw new Error("useApiClient must be used within ApiClientProvider");
  }
  return client;
}
