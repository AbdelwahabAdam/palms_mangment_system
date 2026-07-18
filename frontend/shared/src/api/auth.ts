import {
  ChangePasswordRequestSchema,
  CurrentUserSchema,
  ForgotPasswordRequestSchema,
  LoggedOutSchema,
  LoginRequestSchema,
  LoginResponseSchema,
  PasswordChangedSchema,
  PasswordResetRequestedSchema,
  PasswordResetSchema,
  ResetPasswordRequestSchema,
  TwoFactorSchema,
} from "../contracts";
import type {
  ChangePasswordRequest,
  ForgotPasswordRequest,
  LoginRequest,
  ResetPasswordRequest,
} from "../contracts";
import type { HttpClient } from "../http";
import type { RequestContext } from "./types";

export function createAuthApi(http: HttpClient) {
  return {
    login: (input: LoginRequest, context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/auth/login",
        data: LoginRequestSchema.parse(input),
        response: LoginResponseSchema,
        signal: context.signal,
      }),
    logout: (context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/auth/logout",
        response: LoggedOutSchema,
        signal: context.signal,
      }),
    me: (context: RequestContext = {}) =>
      http.request({
        method: "GET",
        path: "/auth/me",
        response: CurrentUserSchema,
        signal: context.signal,
      }),
    forgotPassword: (
      input: ForgotPasswordRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/auth/forgot-password",
        data: ForgotPasswordRequestSchema.parse(input),
        response: PasswordResetRequestedSchema,
        signal: context.signal,
      }),
    resetPassword: (
      input: ResetPasswordRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/auth/reset-password",
        data: ResetPasswordRequestSchema.parse(input),
        response: PasswordResetSchema,
        signal: context.signal,
      }),
    changePassword: (
      input: ChangePasswordRequest,
      context: RequestContext = {},
    ) =>
      http.request({
        method: "POST",
        path: "/auth/change-password",
        data: ChangePasswordRequestSchema.parse(input),
        response: PasswordChangedSchema,
        signal: context.signal,
      }),
    enableTwoFactor: (context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/auth/2fa/enable",
        response: TwoFactorSchema,
        signal: context.signal,
      }),
    disableTwoFactor: (context: RequestContext = {}) =>
      http.request({
        method: "POST",
        path: "/auth/2fa/disable",
        response: TwoFactorSchema,
        signal: context.signal,
      }),
  };
}

export type AuthApi = ReturnType<typeof createAuthApi>;
