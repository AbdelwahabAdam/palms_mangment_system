import {
  AuditLogSchema,
  InvitationSchema,
  InviteUserRequestSchema,
  PaginatedSchema,
  PasswordResetRequestedByAdminSchema,
  UserPatchRequestSchema,
  UserSchema,
  UuidSchema,
} from "../contracts";
import type { InviteUserRequest, UserPatchRequest } from "../contracts";
import type { HttpClient } from "../http";
import type { ListQuery, RequestContext } from "./types";

export type UsersListQuery = ListQuery;

export function createUsersApi(http: HttpClient) {
  return {
    list: (
      query: UsersListQuery = {},
      context: RequestContext = {},
    ) =>
      http.request({
        method: "GET",
        path: "/admin/users",
        params: query,
        response: PaginatedSchema(UserSchema),
        signal: context.signal,
      }),
    invite: (input: InviteUserRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/admin/users/invite",
        data: InviteUserRequestSchema.parse(input),
        response: InvitationSchema,
        signal: context.signal,
      }),
    get: (userId: string, context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: `/admin/users/${UuidSchema.parse(userId)}`,
        response: UserSchema,
        signal: context.signal,
      }),
    update: (
      userId: string,
      input: UserPatchRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "PATCH",
        path: `/admin/users/${UuidSchema.parse(userId)}`,
        data: UserPatchRequestSchema.parse(input),
        response: UserSchema,
        signal: context.signal,
      }),
    disable: (userId: string, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: `/admin/users/${UuidSchema.parse(userId)}/disable`,
        response: UserSchema,
        signal: context.signal,
      }),
    enable: (userId: string, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: `/admin/users/${UuidSchema.parse(userId)}/enable`,
        response: UserSchema,
        signal: context.signal,
      }),
    requestPasswordReset: (userId: string, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: `/admin/users/${UuidSchema.parse(userId)}/reset-password`,
        response: PasswordResetRequestedByAdminSchema,
        signal: context.signal,
      }),
    auditLogs: (
      userId: string,
      query: Omit<ListQuery, "query"> = {},
      context: RequestContext = {},
    ) =>
      http.request({
        method: "GET",
        path: `/admin/users/${UuidSchema.parse(userId)}/audit-logs`,
        params: query,
        response: PaginatedSchema(AuditLogSchema),
        signal: context.signal,
      }),
  };
}

export type UsersApi = ReturnType<typeof createUsersApi>;
