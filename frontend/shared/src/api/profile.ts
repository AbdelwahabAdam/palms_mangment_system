import {
  AvatarUploadResponseSchema,
  ChangeEmailRequestSchema,
  ChangePasswordRequestSchema,
  CurrentUserSchema,
  PasswordChangedSchema,
  ProfilePatchRequestSchema,
  UserWithPermissionsSchema,
} from "../contracts";
import type {
  ChangeEmailRequest,
  ChangePasswordRequest,
  ProfilePatchRequest,
} from "../contracts";
import type { HttpClient } from "../http";
import {
  createMultipartBody,
  defaultFormDataFactory,
} from "../multipart";
import type { BinaryUpload, FormDataFactory } from "../multipart";
import type { RequestContext } from "./types";

export function createProfileApi(
  http: HttpClient,
  createFormData: FormDataFactory = defaultFormDataFactory,
) {
  return {
    get: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/admin/profile",
        response: CurrentUserSchema,
        signal: context.signal,
      }),
    update: (input: ProfilePatchRequest, context: RequestContext = {}) =>
      http.request({
        method: "PATCH",
        path: "/admin/profile",
        data: ProfilePatchRequestSchema.parse(input),
        response: UserWithPermissionsSchema,
        signal: context.signal,
      }),
    changePassword: (
      input: ChangePasswordRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/admin/profile/change-password",
        data: ChangePasswordRequestSchema.parse(input),
        response: PasswordChangedSchema,
        signal: context.signal,
      }),
    changeEmail: (input: ChangeEmailRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/profile/change-email",
        data: ChangeEmailRequestSchema.parse(input),
        response: UserWithPermissionsSchema,
        signal: context.signal,
      }),
    uploadAvatar: (upload: BinaryUpload, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/profile/avatar",
        data: createMultipartBody(upload, createFormData),
        response: AvatarUploadResponseSchema,
        signal: context.signal,
      }),
  };
}

export type ProfileApi = ReturnType<typeof createProfileApi>;
