import {
  BulkDeleteResponseSchema,
  BulkPalmIdsRequestSchema,
  BulkPalmSectionRequestSchema,
  BulkSectionUpdateResponseSchema,
  DeleteResponseSchema,
  DiseaseCreateRequestSchema,
  DiseasePatchRequestSchema,
  DiseaseSchema,
  HarvestCreateRequestSchema,
  HarvestPatchRequestSchema,
  HarvestSchema,
  PalmCreateRequestSchema,
  PalmDetailSchema,
  PalmImageSchema,
  PalmNoteCreateRequestSchema,
  PalmNoteSchema,
  PalmPatchRequestSchema,
  PalmRelationshipCreateRequestSchema,
  PalmRelationshipCreateResponseSchema,
  PalmSchema,
  PaginatedSchema,
  TreatmentCreateRequestSchema,
  TreatmentPatchRequestSchema,
  TreatmentSchema,
  UuidSchema,
} from "../contracts";
import type {
  DiseaseCreateRequest,
  DiseasePatchRequest,
  HarvestCreateRequest,
  HarvestPatchRequest,
  PalmCreateRequest,
  PalmNoteCreateRequest,
  PalmPatchRequest,
  PalmRelationshipCreateRequest,
  TreatmentCreateRequest,
  TreatmentPatchRequest,
} from "../contracts";
import type { HttpClient } from "../http";
import {
  createMultipartBody,
  defaultFormDataFactory,
} from "../multipart";
import type { BinaryUpload, FormDataFactory } from "../multipart";
import type { ListQuery, RequestContext } from "./types";

export interface PalmsListQuery extends ListQuery {
  donor_id?: string;
  section_id?: string;
  status?: string;
  health_status?: string;
}

const palmPath = (palmId: string): string =>
  `/admin/palms/${UuidSchema.parse(palmId)}`;

export function createPalmsApi(
  http: HttpClient,
  createFormData: FormDataFactory = defaultFormDataFactory,
) {
  return {
    list: (query: PalmsListQuery = {}, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/palms",
        params: query,
        response: PaginatedSchema(PalmSchema),
        signal: context.signal,
      }),
    create: (input: PalmCreateRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/palms",
        data: PalmCreateRequestSchema.parse(input),
        response: PalmSchema,
        signal: context.signal,
      }),
    get: (palmId: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: palmPath(palmId),
        response: PalmDetailSchema,
        signal: context.signal,
      }),
    update: (
      palmId: string,
      input: PalmPatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: palmPath(palmId),
        data: PalmPatchRequestSchema.parse(input),
        response: PalmSchema,
        signal: context.signal,
      }),
    remove: (palmId: string, context: RequestContext = {}) =>
      http.request({
        method: "DELETE",
        path: palmPath(palmId),
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    bulkDelete: (palmIds: readonly string[], context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/palms/bulk-delete",
        data: BulkPalmIdsRequestSchema.parse({ palm_ids: palmIds }),
        response: BulkDeleteResponseSchema,
        signal: context.signal,
      }),
    bulkUpdateSection: (
      palmIds: readonly string[],
      sectionId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/admin/palms/bulk-update-section",
        data: BulkPalmSectionRequestSchema.parse({
          palm_ids: palmIds,
          section_id: sectionId,
        }),
        response: BulkSectionUpdateResponseSchema,
        signal: context.signal,
      }),
    uploadImage: (
      palmId: string,
      upload: BinaryUpload,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `${palmPath(palmId)}/images`,
        data: createMultipartBody(upload, createFormData),
        response: PalmImageSchema,
        signal: context.signal,
      }),
    removeImage: (
      palmId: string,
      imageId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `${palmPath(palmId)}/images/${UuidSchema.parse(imageId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    createHarvest: (
      palmId: string,
      input: HarvestCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `${palmPath(palmId)}/harvests`,
        data: HarvestCreateRequestSchema.parse(input),
        response: HarvestSchema,
        signal: context.signal,
      }),
    updateHarvest: (
      palmId: string,
      harvestId: string,
      input: HarvestPatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `${palmPath(palmId)}/harvests/${UuidSchema.parse(harvestId)}`,
        data: HarvestPatchRequestSchema.parse(input),
        response: HarvestSchema,
        signal: context.signal,
      }),
    removeHarvest: (
      palmId: string,
      harvestId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `${palmPath(palmId)}/harvests/${UuidSchema.parse(harvestId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    createDisease: (
      palmId: string,
      input: DiseaseCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `${palmPath(palmId)}/diseases`,
        data: DiseaseCreateRequestSchema.parse(input),
        response: DiseaseSchema,
        signal: context.signal,
      }),
    updateDisease: (
      palmId: string,
      diseaseId: string,
      input: DiseasePatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `${palmPath(palmId)}/diseases/${UuidSchema.parse(diseaseId)}`,
        data: DiseasePatchRequestSchema.parse(input),
        response: DiseaseSchema,
        signal: context.signal,
      }),
    removeDisease: (
      palmId: string,
      diseaseId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `${palmPath(palmId)}/diseases/${UuidSchema.parse(diseaseId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    createTreatment: (
      palmId: string,
      diseaseId: string,
      input: TreatmentCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `${palmPath(palmId)}/diseases/${UuidSchema.parse(diseaseId)}/treatments`,
        data: TreatmentCreateRequestSchema.parse(input),
        response: TreatmentSchema,
        signal: context.signal,
      }),
    updateTreatment: (
      palmId: string,
      diseaseId: string,
      treatmentId: string,
      input: TreatmentPatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `${palmPath(palmId)}/diseases/${UuidSchema.parse(diseaseId)}/treatments/${UuidSchema.parse(treatmentId)}`,
        data: TreatmentPatchRequestSchema.parse(input),
        response: TreatmentSchema,
        signal: context.signal,
      }),
    removeTreatment: (
      palmId: string,
      diseaseId: string,
      treatmentId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `${palmPath(palmId)}/diseases/${UuidSchema.parse(diseaseId)}/treatments/${UuidSchema.parse(treatmentId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    createNote: (
      palmId: string,
      input: PalmNoteCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `${palmPath(palmId)}/notes`,
        data: PalmNoteCreateRequestSchema.parse(input),
        response: PalmNoteSchema,
        signal: context.signal,
      }),
    removeNote: (
      palmId: string,
      noteId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `${palmPath(palmId)}/notes/${UuidSchema.parse(noteId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
    createRelationship: (
      palmId: string,
      input: PalmRelationshipCreateRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: `${palmPath(palmId)}/relationships`,
        data: PalmRelationshipCreateRequestSchema.parse(input),
        response: PalmRelationshipCreateResponseSchema,
        signal: context.signal,
      }),
    removeRelationship: (
      palmId: string,
      relationshipId: string,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "DELETE",
        path: `${palmPath(palmId)}/relationships/${UuidSchema.parse(relationshipId)}`,
        response: DeleteResponseSchema,
        signal: context.signal,
      }),
  };
}

export type PalmsApi = ReturnType<typeof createPalmsApi>;
