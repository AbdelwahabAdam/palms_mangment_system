import {
  PaginatedSchema,
  SectionCreateRequestSchema,
  SectionDeleteResponseSchema,
  SectionImageUploadResponseSchema,
  SectionPatchRequestSchema,
  SectionSchema,
  UuidSchema,
} from "../contracts";
import type {
  SectionCreateRequest,
  SectionPatchRequest,
} from "../contracts";
import type { HttpClient } from "../http";
import {
  createMultipartBody,
  defaultFormDataFactory,
} from "../multipart";
import type { BinaryUpload, FormDataFactory } from "../multipart";
import type { ListQuery, RequestContext } from "./types";

export type SectionsListQuery = ListQuery;

export function createSectionsApi(
  http: HttpClient,
  createFormData: FormDataFactory = defaultFormDataFactory,
) {
  return {
    list: (query: SectionsListQuery = {}, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/sections",
        params: query,
        response: PaginatedSchema(SectionSchema),
        signal: context.signal,
      }),
    create: (input: SectionCreateRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/sections",
        data: SectionCreateRequestSchema.parse(input),
        response: SectionSchema,
        signal: context.signal,
      }),
    get: (sectionId: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: `/admin/sections/${UuidSchema.parse(sectionId)}`,
        response: SectionSchema,
        signal: context.signal,
      }),
    update: (
      sectionId: string,
      input: SectionPatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `/admin/sections/${UuidSchema.parse(sectionId)}`,
        data: SectionPatchRequestSchema.parse(input),
        response: SectionSchema,
        signal: context.signal,
      }),
    remove: (
      sectionId: string,
      reassignToSectionId?: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `/admin/sections/${UuidSchema.parse(sectionId)}`,
        params: {
          reassign_to_section_id:
            reassignToSectionId === undefined
              ? undefined
              : UuidSchema.parse(reassignToSectionId),
        },
        response: SectionDeleteResponseSchema,
        signal: context.signal,
      }),
    uploadImage: (
      sectionId: string,
      upload: BinaryUpload,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `/admin/sections/${UuidSchema.parse(sectionId)}/image`,
        data: createMultipartBody(upload, createFormData),
        response: SectionImageUploadResponseSchema,
        signal: context.signal,
      }),
  };
}

export type SectionsApi = ReturnType<typeof createSectionsApi>;
