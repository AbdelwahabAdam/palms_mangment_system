export interface RequestContext {
  signal?: AbortSignal;
}

export interface ListQuery {
  page?: number;
  page_size?: number;
  sort?: string;
  order?: "asc" | "desc";
  query?: string;
}
