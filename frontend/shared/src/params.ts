export type QueryPrimitive = string | number | boolean;
export type QueryValue =
  | QueryPrimitive
  | readonly QueryPrimitive[]
  | null
  | undefined;
export type QueryParams = object;

function assertQueryPrimitive(key: string, value: unknown): asserts value is QueryPrimitive {
  if (typeof value === "string" || typeof value === "boolean") {
    return;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return;
  }
  throw new TypeError(
    `Query parameter "${key}" must be a finite string, number, or boolean.`,
  );
}

/**
 * Serializes only scalar query values. Arrays are emitted as repeated keys,
 * avoiding ambiguous JSON blobs and preserving URLSearchParams escaping.
 */
export function serializeParams(params: QueryParams): string {
  const output = new URLSearchParams();

  for (const [key, rawValue] of Object.entries(
    params as Record<string, QueryValue>,
  )) {
    if (!key) {
      throw new TypeError("Query parameter names must not be empty.");
    }
    if (rawValue === undefined || rawValue === null) {
      continue;
    }

    const values = Array.isArray(rawValue) ? rawValue : [rawValue];
    for (const value of values) {
      assertQueryPrimitive(key, value);
      output.append(key, String(value));
    }
  }

  return output.toString();
}
