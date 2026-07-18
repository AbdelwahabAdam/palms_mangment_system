import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Card,
  CardContent,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import {
  ChangeEmailRequestSchema,
  ChangePasswordRequestSchema,
  ProfilePatchRequestSchema,
  queryKeys,
  type ChangeEmailRequest,
  type ChangePasswordRequest,
  type ProfilePatchRequest,
} from "@palms/shared";
import { z } from "zod";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { FileDropzone } from "@/components/FileDropzone";
import { PageHeader } from "@/components/PageHeader";
import { useSnackbarStore } from "@/stores/uiStore";
import { getErrorMessage } from "@/utils/errors";

const PasswordFormSchema = ChangePasswordRequestSchema.extend({
  confirm_password: z.string().min(12),
}).refine((value) => value.new_password === value.confirm_password, {
  message: "Passwords must match.",
  path: ["confirm_password"],
});

type PasswordFormValues = z.infer<typeof PasswordFormSchema>;

export function ProfilePage() {
  const client = useApiClient();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const { refresh } = useAuth();

  const profileQuery = useQuery({
    queryKey: queryKeys.profile,
    queryFn: ({ signal }) => client.profile.get({ signal }),
  });

  const profileForm = useForm<ProfilePatchRequest>({
    resolver: zodResolver(ProfilePatchRequestSchema),
    defaultValues: { full_name: "" },
  });

  const emailForm = useForm<ChangeEmailRequest>({
    resolver: zodResolver(ChangeEmailRequestSchema),
    defaultValues: { current_password: "", new_email: "" },
  });

  const passwordForm = useForm<PasswordFormValues>({
    resolver: zodResolver(PasswordFormSchema),
    defaultValues: {
      current_password: "",
      new_password: "",
      confirm_password: "",
    },
  });

  useEffect(() => {
    if (profileQuery.data) {
      profileForm.reset({ full_name: profileQuery.data.full_name });
    }
  }, [profileQuery.data, profileForm]);

  const updateProfile = useMutation({
    mutationFn: (input: ProfilePatchRequest) => client.profile.update(input),
    onSuccess: async () => {
      show("Profile updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.profile });
      await queryClient.invalidateQueries({ queryKey: queryKeys.me });
      await refresh();
    },
  });

  const changeEmail = useMutation({
    mutationFn: (input: ChangeEmailRequest) => client.profile.changeEmail(input),
    onSuccess: async () => {
      show("Email updated.", "success");
      emailForm.reset();
      await queryClient.invalidateQueries({ queryKey: queryKeys.profile });
      await queryClient.invalidateQueries({ queryKey: queryKeys.me });
      await refresh();
    },
  });

  const changePassword = useMutation({
    mutationFn: (input: ChangePasswordRequest) =>
      client.profile.changePassword(input),
    onSuccess: async () => {
      show("Password changed. Please sign in again.", "success");
      passwordForm.reset();
      await client.auth.logout().catch(() => undefined);
      await queryClient.clear();
      window.location.assign("/admin/login");
    },
  });

  const avatarMutation = useMutation({
    mutationFn: (file: File) =>
      client.profile.uploadAvatar({ file, filename: file.name }),
    onSuccess: async () => {
      show("Avatar updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.profile });
      await queryClient.invalidateQueries({ queryKey: queryKeys.me });
      await refresh();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const [twoFactorPending, setTwoFactorPending] = useState(false);

  const toggle2fa = useMutation({
    mutationFn: async () => {
      setTwoFactorPending(true);
      if (profileQuery.data?.two_factor.enabled) {
        return client.auth.disableTwoFactor();
      }
      return client.auth.enableTwoFactor();
    },
    onSuccess: async () => {
      show("Two-factor setting updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.profile });
      await queryClient.invalidateQueries({ queryKey: queryKeys.me });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
    onSettled: () => setTwoFactorPending(false),
  });

  if (profileQuery.isLoading) return <LoadingState />;
  if (profileQuery.isError || !profileQuery.data) {
    return (
      <ErrorState
        description={getErrorMessage(profileQuery.error)}
        onRetry={() => profileQuery.refetch()}
      />
    );
  }

  const profile = profileQuery.data;

  return (
    <Box>
      <PageHeader title="Profile" description="Manage your account details and security." />
      <Stack spacing={2} sx={{ maxWidth: 720 }}>
        <Card variant="outlined">
          <CardContent>
            <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
              <Avatar
                src={profile.avatar_url ?? undefined}
                alt={profile.full_name}
                sx={{ width: 72, height: 72 }}
              />
              <Box>
                <Typography variant="h6">{profile.full_name}</Typography>
                <Typography color="text.secondary">{profile.email}</Typography>
                <Typography variant="body2">{profile.role.name}</Typography>
              </Box>
            </Stack>
            <FileDropzone
              label="Upload a new avatar"
              onFile={(file) => avatarMutation.mutate(file)}
              disabled={avatarMutation.isPending}
            />
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Display name
            </Typography>
            <Box
              component="form"
              noValidate
              onSubmit={profileForm.handleSubmit(async (values) => {
                await updateProfile.mutateAsync(values);
              })}
            >
              <Stack spacing={2}>
                {updateProfile.isError ? (
                  <Alert severity="error">{getErrorMessage(updateProfile.error)}</Alert>
                ) : null}
                <TextField
                  label="Full name"
                  fullWidth
                  error={Boolean(profileForm.formState.errors.full_name)}
                  helperText={profileForm.formState.errors.full_name?.message}
                  {...profileForm.register("full_name")}
                />
                <Button type="submit" variant="contained" disabled={updateProfile.isPending}>
                  Save name
                </Button>
              </Stack>
            </Box>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Change email
            </Typography>
            <Box
              component="form"
              noValidate
              onSubmit={emailForm.handleSubmit(async (values) => {
                await changeEmail.mutateAsync(values);
              })}
            >
              <Stack spacing={2}>
                {changeEmail.isError ? (
                  <Alert severity="error">{getErrorMessage(changeEmail.error)}</Alert>
                ) : null}
                <TextField
                  label="New email"
                  type="email"
                  fullWidth
                  error={Boolean(emailForm.formState.errors.new_email)}
                  helperText={emailForm.formState.errors.new_email?.message}
                  {...emailForm.register("new_email")}
                />
                <TextField
                  label="Current password"
                  type="password"
                  fullWidth
                  error={Boolean(emailForm.formState.errors.current_password)}
                  helperText={emailForm.formState.errors.current_password?.message}
                  {...emailForm.register("current_password")}
                />
                <Button type="submit" variant="contained" disabled={changeEmail.isPending}>
                  Update email
                </Button>
              </Stack>
            </Box>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Change password
            </Typography>
            <Box
              component="form"
              noValidate
              onSubmit={passwordForm.handleSubmit(async (values) => {
                await changePassword.mutateAsync({
                  current_password: values.current_password,
                  new_password: values.new_password,
                });
              })}
            >
              <Stack spacing={2}>
                {changePassword.isError ? (
                  <Alert severity="error">{getErrorMessage(changePassword.error)}</Alert>
                ) : null}
                <TextField
                  label="Current password"
                  type="password"
                  fullWidth
                  error={Boolean(passwordForm.formState.errors.current_password)}
                  helperText={passwordForm.formState.errors.current_password?.message}
                  {...passwordForm.register("current_password")}
                />
                <TextField
                  label="New password"
                  type="password"
                  fullWidth
                  error={Boolean(passwordForm.formState.errors.new_password)}
                  helperText={passwordForm.formState.errors.new_password?.message}
                  {...passwordForm.register("new_password")}
                />
                <TextField
                  label="Confirm password"
                  type="password"
                  fullWidth
                  error={Boolean(passwordForm.formState.errors.confirm_password)}
                  helperText={passwordForm.formState.errors.confirm_password?.message}
                  {...passwordForm.register("confirm_password")}
                />
                <Button type="submit" variant="contained" disabled={changePassword.isPending}>
                  Update password
                </Button>
              </Stack>
            </Box>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Two-factor authentication
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              Status: {profile.two_factor.enabled ? "Enabled" : "Disabled"} (placeholder mode)
            </Typography>
            <Button
              variant="outlined"
              disabled={twoFactorPending || toggle2fa.isPending}
              onClick={() => toggle2fa.mutate()}
            >
              {profile.two_factor.enabled ? "Disable 2FA" : "Enable 2FA"}
            </Button>
          </CardContent>
        </Card>
      </Stack>
    </Box>
  );
}
