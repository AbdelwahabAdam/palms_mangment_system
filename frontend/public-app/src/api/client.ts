import { createPalmsClient } from "@palms/shared";
import type { PalmsClient } from "@palms/shared";

export function createAppClient(): PalmsClient {
  return createPalmsClient({
    env: import.meta.env,
  });
}

export type { PalmsClient };
