import {
  createContext,
  useContext,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { createPalmsClient, type PalmsClient } from "@palms/shared";

const ApiClientContext = createContext<PalmsClient | null>(null);

export function ApiClientProvider({
  children,
  client: injectedClient,
}: {
  children: ReactNode;
  client?: PalmsClient;
}) {
  const navigate = useNavigate();
  const navigateRef = useRef(navigate);
  navigateRef.current = navigate;

  const client = useMemo(
    () =>
      injectedClient ??
      createPalmsClient({
        env: import.meta.env,
        onAuthFailure: () => {
          navigateRef.current("/login", { replace: true });
        },
      }),
    [injectedClient],
  );

  return (
    <ApiClientContext.Provider value={client}>{children}</ApiClientContext.Provider>
  );
}

export function useApiClient(): PalmsClient {
  const client = useContext(ApiClientContext);
  if (!client) {
    throw new Error("useApiClient must be used within ApiClientProvider.");
  }
  return client;
}
