import { z } from "zod";

export type JsonPrimitive = boolean | number | string | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };
export type JsonObject = { [key: string]: JsonValue };

export const JsonValueSchema: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.string(),
    z.number().finite(),
    z.boolean(),
    z.null(),
    z.array(JsonValueSchema),
    z.record(z.string(), JsonValueSchema),
  ]),
);
export const JsonObjectSchema: z.ZodType<JsonObject> = z.record(
  z.string(),
  JsonValueSchema,
);

export const UuidSchema = z.string().uuid();
export const DateStringSchema = z
  .string()
  .regex(/^\d{4}-\d{2}-\d{2}$/, "Expected an ISO calendar date")
  .refine((value) => !Number.isNaN(Date.parse(`${value}T00:00:00Z`)), {
    message: "Expected a valid ISO calendar date",
  });
export const DateTimeStringSchema = z
  .string()
  .min(1)
  .refine((value) => !Number.isNaN(Date.parse(value)), {
    message: "Expected an ISO date-time string",
  });
export const TimeStringSchema = z
  .string()
  .regex(/^\d{2}:\d{2}$/, "Expected HH:MM");
export const DecimalStringSchema = z.string().regex(/^-?\d+(?:\.\d+)?$/);
/** Accepts backend Decimal strings or numeric zeros produced by empty aggregates. */
export const DecimalValueSchema = z.union([
  DecimalStringSchema,
  z
    .number()
    .finite()
    .transform((value) => String(value)),
]);
export const EmailSchema = z.string().trim().email().max(320);
export const NonEmptyStringSchema = z.string().trim().min(1);

const strictObject = <Shape extends z.ZodRawShape>(shape: Shape) =>
  z.object(shape).strict();
const nonEmptyPatch = <Shape extends z.ZodRawShape>(shape: Shape) =>
  strictObject(shape).refine((value) => Object.keys(value).length > 0, {
    message: "At least one field must be provided.",
  });

export const ApiEnvelopeSchema = <Schema extends z.ZodTypeAny>(data: Schema) =>
  z.object({ data });

export const ApiErrorDetailSchema = z.object({
  field: z.string(),
  code: z.string(),
  message: z.string(),
});
export const ApiErrorBodySchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.array(ApiErrorDetailSchema).optional(),
  }),
});
export type ApiErrorBody = z.infer<typeof ApiErrorBodySchema>;

export const PaginationSchema = z.object({
  page: z.number().int().positive(),
  page_size: z.number().int().positive().max(100),
  total: z.number().int().nonnegative(),
  total_pages: z.number().int().nonnegative(),
});
export const PaginatedSchema = <Schema extends z.ZodType>(item: Schema) =>
  z.object({
    items: z.array(item),
    pagination: PaginationSchema,
  });
export type Pagination = z.infer<typeof PaginationSchema>;

export const RoleSchema = z.object({
  id: UuidSchema,
  name: z.string(),
});
export const TwoFactorSchema = z.object({
  enabled: z.boolean(),
  mode: z.literal("placeholder"),
});
export const UserSchema = z.object({
  id: UuidSchema,
  email: EmailSchema,
  full_name: z.string(),
  is_active: z.boolean(),
  role: RoleSchema,
  last_login_at: DateTimeStringSchema.nullable(),
  avatar_url: z.string().nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
});
export const UserWithPermissionsSchema = UserSchema.extend({
  permissions: z.array(z.string()),
});
export const CurrentUserSchema = UserWithPermissionsSchema.extend({
  two_factor: TwoFactorSchema,
});

export const LoginRequestSchema = strictObject({
  email: EmailSchema,
  password: z.string().min(1).max(256),
});
export const ForgotPasswordRequestSchema = strictObject({ email: EmailSchema });
export const ResetPasswordRequestSchema = strictObject({
  token: z.string().min(32).max(512),
  password: z.string().min(12).max(256),
});
export const ChangePasswordRequestSchema = strictObject({
  current_password: z.string().min(1).max(256),
  new_password: z.string().min(12).max(256),
});
export const ChangeEmailRequestSchema = strictObject({
  current_password: z.string().min(1).max(256),
  new_email: EmailSchema,
});
export const ProfilePatchRequestSchema = nonEmptyPatch({
  full_name: NonEmptyStringSchema.max(160).optional(),
});
export const InviteUserRequestSchema = strictObject({
  email: EmailSchema,
  full_name: NonEmptyStringSchema.max(160),
  role_id: UuidSchema,
});
export const UserPatchRequestSchema = nonEmptyPatch({
  full_name: NonEmptyStringSchema.max(160).optional(),
  role_id: UuidSchema.optional(),
  permission_overrides: z.record(z.string(), z.boolean()).optional(),
});
export const LoginResponseSchema = z.object({ user: UserWithPermissionsSchema });
export const LoggedOutSchema = z.object({ logged_out: z.literal(true) });
export const PasswordResetRequestedSchema = z.object({ message: z.string() });
export const PasswordResetSchema = z.object({ password_reset: z.literal(true) });
export const PasswordChangedSchema = z.object({
  password_changed: z.literal(true),
  reauthentication_required: z.literal(true),
});
export const InvitationSchema = z.object({
  id: UuidSchema,
  email: EmailSchema,
  full_name: z.string(),
  role: RoleSchema,
  expires_at: DateTimeStringSchema,
});
export const PasswordResetRequestedByAdminSchema = z.object({
  password_reset_requested: z.literal(true),
});

export const DonorSchema = z.object({
  id: UuidSchema,
  full_name: z.string(),
  phone: z.string().nullable(),
  email: EmailSchema.nullable(),
  address: z.string().nullable(),
  donation_date: DateStringSchema.nullable(),
  notes: z.string().nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
  palm_count: z.number().int().nonnegative().optional(),
});
export const DonorCreateRequestSchema = strictObject({
  full_name: NonEmptyStringSchema.max(180),
  phone: z.string().max(50).nullable().optional(),
  email: EmailSchema.nullable().optional(),
  address: z.string().max(5_000).nullable().optional(),
  donation_date: DateStringSchema.nullable().optional(),
  notes: z.string().max(10_000).nullable().optional(),
});
export const DonorPatchRequestSchema = nonEmptyPatch({
  full_name: NonEmptyStringSchema.max(180).optional(),
  phone: z.string().max(50).nullable().optional(),
  email: EmailSchema.nullable().optional(),
  address: z.string().max(5_000).nullable().optional(),
  donation_date: DateStringSchema.nullable().optional(),
  notes: z.string().max(10_000).nullable().optional(),
});

export const SectionSchema = z.object({
  id: UuidSchema,
  name: z.string(),
  description: z.string().nullable(),
  location_name: z.string().nullable(),
  soil_type: z.string().nullable(),
  irrigation_type: z.string().nullable(),
  gps_latitude: DecimalValueSchema.nullable(),
  gps_longitude: DecimalValueSchema.nullable(),
  image_url: z.string().nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
  palm_count: z.number().int().nonnegative().optional(),
});
export const SectionCreateRequestSchema = strictObject({
  name: NonEmptyStringSchema.max(160),
  description: z.string().max(10_000).nullable().optional(),
  location_name: z.string().max(255).nullable().optional(),
  soil_type: z.string().max(120).nullable().optional(),
  irrigation_type: z.string().max(120).nullable().optional(),
  gps_latitude: DecimalStringSchema.nullable().optional(),
  gps_longitude: DecimalStringSchema.nullable().optional(),
});
export const SectionPatchRequestSchema = nonEmptyPatch({
  name: NonEmptyStringSchema.max(160).optional(),
  description: z.string().max(10_000).nullable().optional(),
  location_name: z.string().max(255).nullable().optional(),
  soil_type: z.string().max(120).nullable().optional(),
  irrigation_type: z.string().max(120).nullable().optional(),
  gps_latitude: DecimalStringSchema.nullable().optional(),
  gps_longitude: DecimalStringSchema.nullable().optional(),
});
export const SectionImageUploadResponseSchema = z.object({
  image_url: z.string(),
  thumbnail_url: z.string(),
});
export const AvatarUploadResponseSchema = z.object({
  avatar_url: z.string(),
});
export const ImageUploadResponseSchema = z.union([
  SectionImageUploadResponseSchema,
  AvatarUploadResponseSchema,
]);

export const PalmOwnerSchema = z.object({
  id: UuidSchema,
  full_name: z.string(),
});
export const PalmSectionReferenceSchema = z.object({
  id: UuidSchema,
  name: z.string(),
});
export const HarvestSchema = z.object({
  id: UuidSchema,
  harvest_date: DateStringSchema,
  amount: DecimalValueSchema,
  unit: z.string(),
  revenue: DecimalValueSchema.nullable(),
  notes: z.string().nullable(),
  created_by_user_id: UuidSchema.nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
});
export const TreatmentSchema = z.object({
  id: UuidSchema,
  treatment_name: z.string(),
  treatment_date: DateStringSchema,
  notes: z.string().nullable(),
  created_by_user_id: UuidSchema.nullable(),
  created_at: DateTimeStringSchema,
});
export const DiseaseSchema = z.object({
  id: UuidSchema,
  disease_name: z.string(),
  detected_at: DateStringSchema,
  status: z.string(),
  notes: z.string().nullable(),
  created_by_user_id: UuidSchema.nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
  treatments: z.array(TreatmentSchema).optional(),
});
export const PalmNoteSchema = z.object({
  id: UuidSchema,
  body: z.string(),
  created_by_user_id: UuidSchema.nullable(),
  created_at: DateTimeStringSchema,
});
export const PalmImageSchema = z.object({
  id: UuidSchema,
  thumbnail_url: z.string(),
  medium_url: z.string(),
  full_url: z.string(),
  webp_url: z.string(),
  captured_at: DateTimeStringSchema.nullable().optional(),
  uploaded_at: DateTimeStringSchema,
  metadata: JsonObjectSchema.nullable().optional(),
});
export const PalmRelationshipSchema = z.object({
  id: UuidSchema,
  relationship_type: z.string(),
  child_palm: z.object({ id: UuidSchema, code: z.string() }).optional(),
  parent_palm: z.object({ id: UuidSchema, code: z.string() }).optional(),
  created_at: DateTimeStringSchema,
});
export const PalmSchema = z.object({
  id: UuidSchema,
  code: z.string(),
  donor_id: UuidSchema,
  section_id: UuidSchema,
  plantation_date: DateStringSchema.nullable(),
  status: z.string(),
  current_health_status: z.string().nullable(),
  description: z.string().nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
  donor: PalmOwnerSchema.nullable(),
  section: PalmSectionReferenceSchema.nullable(),
});
export const PalmDetailSchema = PalmSchema.extend({
  harvests: z.array(HarvestSchema),
  diseases: z.array(DiseaseSchema),
  notes: z.array(PalmNoteSchema),
  children: z.array(PalmRelationshipSchema),
  parents: z.array(PalmRelationshipSchema),
  images: z.array(PalmImageSchema),
});
export const PalmCreateRequestSchema = strictObject({
  code: z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_-]*$/).max(80),
  donor_id: UuidSchema,
  section_id: UuidSchema,
  plantation_date: DateStringSchema.nullable().optional(),
  status: NonEmptyStringSchema.max(80).optional(),
  current_health_status: z.string().max(120).nullable().optional(),
  description: z.string().max(10_000).nullable().optional(),
});
export const PalmPatchRequestSchema = nonEmptyPatch({
  code: z
    .string()
    .regex(/^[A-Za-z0-9][A-Za-z0-9_-]*$/)
    .max(80)
    .optional(),
  donor_id: UuidSchema.optional(),
  section_id: UuidSchema.optional(),
  plantation_date: DateStringSchema.nullable().optional(),
  status: NonEmptyStringSchema.max(80).optional(),
  current_health_status: z.string().max(120).nullable().optional(),
  description: z.string().max(10_000).nullable().optional(),
});
export const BulkPalmIdsRequestSchema = strictObject({
  palm_ids: z.array(UuidSchema).min(1).max(200),
}).refine((value) => new Set(value.palm_ids).size === value.palm_ids.length, {
  message: "palm_ids must not contain duplicates.",
});
export const BulkPalmSectionRequestSchema = BulkPalmIdsRequestSchema.extend({
  section_id: UuidSchema,
});
export const HarvestCreateRequestSchema = strictObject({
  harvest_date: DateStringSchema,
  amount: DecimalStringSchema.refine((value) => Number(value) > 0),
  unit: NonEmptyStringSchema.max(32),
  revenue: DecimalStringSchema.nullable().optional(),
  notes: z.string().max(10_000).nullable().optional(),
});
export const HarvestPatchRequestSchema = nonEmptyPatch({
  harvest_date: DateStringSchema.optional(),
  amount: DecimalStringSchema.refine((value) => Number(value) > 0).optional(),
  unit: NonEmptyStringSchema.max(32).optional(),
  revenue: DecimalStringSchema.nullable().optional(),
  notes: z.string().max(10_000).nullable().optional(),
});
export const DiseaseCreateRequestSchema = strictObject({
  disease_name: NonEmptyStringSchema.max(180),
  detected_at: DateStringSchema,
  status: NonEmptyStringSchema.max(80).optional(),
  notes: z.string().max(10_000).nullable().optional(),
});
export const DiseasePatchRequestSchema = nonEmptyPatch({
  disease_name: NonEmptyStringSchema.max(180).optional(),
  detected_at: DateStringSchema.optional(),
  status: NonEmptyStringSchema.max(80).optional(),
  notes: z.string().max(10_000).nullable().optional(),
});
export const TreatmentCreateRequestSchema = strictObject({
  treatment_name: NonEmptyStringSchema.max(180),
  treatment_date: DateStringSchema,
  notes: z.string().max(10_000).nullable().optional(),
});
export const TreatmentPatchRequestSchema = nonEmptyPatch({
  treatment_name: NonEmptyStringSchema.max(180).optional(),
  treatment_date: DateStringSchema.optional(),
  notes: z.string().max(10_000).nullable().optional(),
});
export const PalmNoteCreateRequestSchema = strictObject({
  body: NonEmptyStringSchema.max(10_000),
});
export const PalmRelationshipCreateRequestSchema = strictObject({
  child_palm_id: UuidSchema,
  relationship_type: NonEmptyStringSchema.max(60).optional(),
});
export const PalmRelationshipCreateResponseSchema = z.object({
  id: UuidSchema,
  parent_palm_id: UuidSchema,
  child_palm_id: UuidSchema,
  relationship_type: z.string(),
  created_at: DateTimeStringSchema,
});
export const DeleteResponseSchema = z.object({
  deleted: z.literal(true),
  id: UuidSchema,
});
export const BulkDeleteResponseSchema = z.object({
  deleted_count: z.number().int().nonnegative(),
});
export const BulkSectionUpdateResponseSchema = z.object({
  updated_count: z.number().int().nonnegative(),
  section_id: UuidSchema,
});
export const SectionDeleteResponseSchema = DeleteResponseSchema.extend({
  reassigned_palm_count: z.number().int().nonnegative(),
  reassigned_to_section_id: UuidSchema.nullable(),
});

export const PublicAgeSchema = z.object({
  years: z.number().int().nonnegative(),
  months: z.number().int().nonnegative().max(11),
});
export const PublicSearchItemSchema = z.object({
  palm_id: UuidSchema,
  palm_code: z.string(),
  donor_name: z.string(),
  section_name: z.string(),
  plantation_date: DateStringSchema.nullable(),
  current_age: PublicAgeSchema.nullable(),
  thumbnail_url: z.string().nullable(),
});
export const PublicDonorSuggestionSchema = z.object({
  id: UuidSchema,
  full_name: z.string(),
});
export const PublicDiseaseSchema = z.object({
  disease_name: z.string(),
  detected_at: DateStringSchema,
  status: z.string(),
  notes: z.string().nullable(),
  treatments: z.array(
    z.object({
      treatment_name: z.string(),
      treatment_date: DateStringSchema,
      notes: z.string().nullable(),
    }),
  ),
});
export const PublicPalmProfileSchema = z.object({
  id: UuidSchema,
  code: z.string(),
  plantation_date: DateStringSchema.nullable(),
  status: z.string(),
  current_health_status: z.string().nullable(),
  description: z.string().nullable(),
  current_age: PublicAgeSchema.nullable(),
  donor: z.object({ full_name: z.string() }),
  section: z.object({
    name: z.string(),
    location_name: z.string().nullable(),
    image_url: z.string().nullable(),
  }),
  images: z.array(PalmImageSchema),
  harvest_summary: z.object({
    total_amount: DecimalValueSchema,
    total_revenue: DecimalValueSchema,
    records_count: z.number().int().nonnegative(),
  }),
  diseases: z.array(PublicDiseaseSchema),
  children: z.array(
    z.object({
      id: UuidSchema,
      code: z.string(),
      relationship_type: z.string(),
    }),
  ),
});

export const ActivitySchema = z.object({
  id: UuidSchema,
  action: z.string(),
  entity_type: z.string(),
  entity_id: UuidSchema.nullable(),
  message: z.string().nullable(),
  actor_user_id: UuidSchema.nullable(),
  created_at: DateTimeStringSchema,
});
export const DashboardOverviewSchema = z.object({
  totals: z.object({
    palms: z.number().int().nonnegative(),
    donors: z.number().int().nonnegative(),
    sections: z.number().int().nonnegative(),
    revenue: DecimalValueSchema,
    active_palms: z.number().int().nonnegative(),
    inactive_palms: z.number().int().nonnegative(),
  }),
  recent_harvests: z.array(
    z.object({
      id: UuidSchema,
      palm_id: UuidSchema,
      harvest_date: DateStringSchema,
      amount: DecimalValueSchema,
      unit: z.string(),
      revenue: DecimalValueSchema.nullable(),
    }),
  ),
  activity: z.array(ActivitySchema),
  upcoming_reports: z.array(
    z.object({
      id: UuidSchema,
      name: z.string(),
      next_run_at: DateTimeStringSchema.nullable(),
      format: z.string(),
    }),
  ),
});
export const ItemsSchema = <Schema extends z.ZodType>(item: Schema) =>
  z.object({
    items: z.array(item),
  });

export const ReportTypeSchema = z.object({
  code: z.enum(["palms", "donors", "sections"]),
  fields: z.array(z.string()),
  formats: z.array(z.enum(["csv", "pdf"])),
});
export const ReportFiltersSchema = z.record(z.string(), JsonValueSchema);
export const ReportPreviewRequestSchema = strictObject({
  report_type: z.enum(["palms", "donors", "sections"]),
  fields: z.array(z.string()).max(20).nullable().optional(),
  filters: ReportFiltersSchema.nullable().optional(),
});
export const ReportGenerateRequestSchema = ReportPreviewRequestSchema.extend({
  format: z.enum(["csv", "pdf"]).optional(),
});
export const ReportPreviewResponseSchema = z.object({
  fields: z.array(z.string()),
  items: z.array(JsonObjectSchema),
  total: z.number().int().nonnegative(),
  truncated: z.boolean(),
});
export const ReportTemplateSchema = z.object({
  id: UuidSchema,
  name: z.string(),
  report_type: z.enum(["palms", "donors", "sections"]),
  fields: z.array(z.string()),
  filters: ReportFiltersSchema.nullable(),
  created_at: DateTimeStringSchema,
});
export const ReportTemplateCreateRequestSchema = strictObject({
  name: NonEmptyStringSchema.max(160),
  report_type: z.enum(["palms", "donors", "sections"]),
  fields: z.array(z.string()).min(1).max(20),
  filters: ReportFiltersSchema.nullable().optional(),
});
export const ReportFileSchema = z.object({
  id: UuidSchema,
  filename: z.string(),
  content_type: z.string(),
  size_bytes: z.number().int().nonnegative(),
  created_at: DateTimeStringSchema,
});
export const ReportRunSchema = z.object({
  id: UuidSchema,
  schedule_id: UuidSchema.nullable(),
  report_type: z.enum(["palms", "donors", "sections"]),
  format: z.enum(["csv", "pdf"]),
  fields: z.array(z.string()),
  filters: ReportFiltersSchema.nullable(),
  status: z.string(),
  error_message: z.string().nullable(),
  started_at: DateTimeStringSchema.nullable(),
  finished_at: DateTimeStringSchema.nullable(),
  created_at: DateTimeStringSchema,
  files: z.array(ReportFileSchema),
  download_urls: z.array(z.string()).optional(),
});
export const ReportRunDownloadSchema = z.object({
  run_id: UuidSchema,
  files: z.array(
    z.object({
      filename: z.string(),
      download_url: z.string(),
    }),
  ),
});
export const ReportScheduleSchema = z.object({
  id: UuidSchema,
  name: z.string(),
  report_type: z.enum(["palms", "donors", "sections"]),
  template_id: UuidSchema.nullable(),
  frequency: z.enum(["daily", "weekly", "monthly", "cron"]),
  cron_expression: z.string().nullable(),
  day_of_month: z.number().int().nullable(),
  weekday: z.number().int().nullable(),
  run_time: TimeStringSchema.nullable(),
  timezone: z.string(),
  format: z.enum(["csv", "pdf"]),
  fields: z.array(z.string()).nullable(),
  filters: ReportFiltersSchema.nullable(),
  email_subject: z.string().nullable(),
  include_summary: z.boolean(),
  attach_file: z.boolean(),
  enabled: z.boolean(),
  recipients: z.array(EmailSchema),
  last_run_at: DateTimeStringSchema.nullable(),
  next_run_at: DateTimeStringSchema.nullable(),
  created_at: DateTimeStringSchema,
  updated_at: DateTimeStringSchema,
});
export const ReportScheduleCreateRequestSchema = strictObject({
  name: NonEmptyStringSchema.max(160),
  report_type: z.enum(["palms", "donors", "sections"]),
  template_id: UuidSchema.nullable().optional(),
  frequency: z.enum(["daily", "weekly", "monthly", "cron"]),
  cron_expression: z.string().max(120).nullable().optional(),
  day_of_month: z.number().int().min(1).max(28).nullable().optional(),
  weekday: z.number().int().min(0).max(6).nullable().optional(),
  run_time: TimeStringSchema.nullable().optional(),
  timezone: NonEmptyStringSchema.max(64),
  format: z.enum(["csv", "pdf"]),
  fields: z.array(z.string()).max(20).nullable().optional(),
  filters: ReportFiltersSchema.nullable().optional(),
  recipients: z.array(EmailSchema).min(1).max(50),
  email_subject: z.string().max(255).nullable().optional(),
  include_summary: z.boolean().optional(),
  attach_file: z.boolean().optional(),
  enabled: z.boolean().optional(),
}).refine(
  (value) => new Set(value.recipients.map((email) => email.toLowerCase())).size === value.recipients.length,
  { message: "recipients must not contain duplicates." },
);
export const ReportSchedulePatchRequestSchema = nonEmptyPatch({
  name: NonEmptyStringSchema.max(160).optional(),
  report_type: z.enum(["palms", "donors", "sections"]).optional(),
  template_id: UuidSchema.nullable().optional(),
  frequency: z.enum(["daily", "weekly", "monthly", "cron"]).optional(),
  cron_expression: z.string().max(120).nullable().optional(),
  day_of_month: z.number().int().min(1).max(28).nullable().optional(),
  weekday: z.number().int().min(0).max(6).nullable().optional(),
  run_time: TimeStringSchema.nullable().optional(),
  timezone: NonEmptyStringSchema.max(64).optional(),
  format: z.enum(["csv", "pdf"]).optional(),
  fields: z.array(z.string()).max(20).nullable().optional(),
  filters: ReportFiltersSchema.nullable().optional(),
  recipients: z.array(EmailSchema).min(1).max(50).optional(),
  email_subject: z.string().max(255).nullable().optional(),
  include_summary: z.boolean().optional(),
  attach_file: z.boolean().optional(),
  enabled: z.boolean().optional(),
});

export const AuditLogSchema = z.object({
  id: UuidSchema,
  actor_user_id: UuidSchema.nullable(),
  action: z.string(),
  entity_type: z.string(),
  entity_id: UuidSchema.nullable(),
  old_values: JsonObjectSchema.nullable(),
  new_values: JsonObjectSchema.nullable(),
  ip_address: z.string().nullable(),
  user_agent: z.string().nullable(),
  created_at: DateTimeStringSchema,
});
export const HealthSchema = z.object({
  status: z.enum(["ok", "degraded"]),
  database: z.enum(["ok", "unavailable"]),
  version: z.string(),
});
export const MetaSchema = z.object({
  service: z.string(),
  version: z.string(),
  api_version: z.literal("v1"),
});

export type LoginRequest = z.infer<typeof LoginRequestSchema>;
export type ForgotPasswordRequest = z.infer<typeof ForgotPasswordRequestSchema>;
export type ResetPasswordRequest = z.infer<typeof ResetPasswordRequestSchema>;
export type ChangePasswordRequest = z.infer<typeof ChangePasswordRequestSchema>;
export type ChangeEmailRequest = z.infer<typeof ChangeEmailRequestSchema>;
export type ProfilePatchRequest = z.infer<typeof ProfilePatchRequestSchema>;
export type InviteUserRequest = z.infer<typeof InviteUserRequestSchema>;
export type UserPatchRequest = z.infer<typeof UserPatchRequestSchema>;
export type User = z.infer<typeof UserSchema>;
export type CurrentUser = z.infer<typeof CurrentUserSchema>;
export type Donor = z.infer<typeof DonorSchema>;
export type DonorCreateRequest = z.infer<typeof DonorCreateRequestSchema>;
export type DonorPatchRequest = z.infer<typeof DonorPatchRequestSchema>;
export type Section = z.infer<typeof SectionSchema>;
export type SectionCreateRequest = z.infer<typeof SectionCreateRequestSchema>;
export type SectionPatchRequest = z.infer<typeof SectionPatchRequestSchema>;
export type Palm = z.infer<typeof PalmSchema>;
export type PalmDetail = z.infer<typeof PalmDetailSchema>;
export type PalmCreateRequest = z.infer<typeof PalmCreateRequestSchema>;
export type PalmPatchRequest = z.infer<typeof PalmPatchRequestSchema>;
export type HarvestCreateRequest = z.infer<typeof HarvestCreateRequestSchema>;
export type HarvestPatchRequest = z.infer<typeof HarvestPatchRequestSchema>;
export type DiseaseCreateRequest = z.infer<typeof DiseaseCreateRequestSchema>;
export type DiseasePatchRequest = z.infer<typeof DiseasePatchRequestSchema>;
export type TreatmentCreateRequest = z.infer<typeof TreatmentCreateRequestSchema>;
export type TreatmentPatchRequest = z.infer<typeof TreatmentPatchRequestSchema>;
export type PalmNoteCreateRequest = z.infer<typeof PalmNoteCreateRequestSchema>;
export type PalmRelationshipCreateRequest = z.infer<
  typeof PalmRelationshipCreateRequestSchema
>;
export type PublicPalmProfile = z.infer<typeof PublicPalmProfileSchema>;
export type DashboardOverview = z.infer<typeof DashboardOverviewSchema>;
export type ReportPreviewRequest = z.infer<typeof ReportPreviewRequestSchema>;
export type ReportGenerateRequest = z.infer<typeof ReportGenerateRequestSchema>;
export type ReportTemplateCreateRequest = z.infer<
  typeof ReportTemplateCreateRequestSchema
>;
export type ReportScheduleCreateRequest = z.infer<
  typeof ReportScheduleCreateRequestSchema
>;
export type ReportSchedulePatchRequest = z.infer<
  typeof ReportSchedulePatchRequestSchema
>;
export type ReportRun = z.infer<typeof ReportRunSchema>;
export type ReportSchedule = z.infer<typeof ReportScheduleSchema>;
