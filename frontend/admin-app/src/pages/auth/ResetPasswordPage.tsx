import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Link,
  Stack,
  TextField,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import {
  ResetPasswordRequestSchema,
  type ResetPasswordRequest,
} from "@palms/shared";
import { z } from "zod";

import { useApiClient } from "@/api/ApiClientProvider";
import { AuthLayout } from "@/pages/auth/LoginPage";
import { getErrorMessage } from "@/utils/errors";

const FormSchema = ResetPasswordRequestSchema.extend({
  confirm_password: z.string().min(12).max(256),
}).refine((value) => value.password === value.confirm_password, {
  message: "Passwords must match.",
  path: ["confirm_password"],
});

type FormValues = z.infer<typeof FormSchema>;

export function ResetPasswordPage() {
  const client = useApiClient();
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      token,
      password: "",
      confirm_password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: (input: ResetPasswordRequest) =>
      client.auth.resetPassword(input),
  });

  return (
    <AuthLayout
      title="Reset password"
      subtitle="Choose a new password of at least 12 characters."
    >
      <Box
        component="form"
        noValidate
        onSubmit={handleSubmit(async (values) => {
          await mutation.mutateAsync({
            token: values.token,
            password: values.password,
          });
        })}
      >
        <Stack spacing={2}>
          {mutation.isSuccess ? (
            <Alert severity="success">
              Password updated. You can sign in with your new password.
            </Alert>
          ) : null}
          {mutation.isError ? (
            <Alert severity="error">
              {getErrorMessage(mutation.error, "Reset failed.")}
            </Alert>
          ) : null}
          <TextField
            label="Reset token"
            required
            fullWidth
            error={Boolean(errors.token)}
            helperText={errors.token?.message}
            {...register("token")}
          />
          <TextField
            label="New password"
            type="password"
            autoComplete="new-password"
            required
            fullWidth
            error={Boolean(errors.password)}
            helperText={errors.password?.message}
            {...register("password")}
          />
          <TextField
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            required
            fullWidth
            error={Boolean(errors.confirm_password)}
            helperText={errors.confirm_password?.message}
            {...register("confirm_password")}
          />
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={mutation.isPending || mutation.isSuccess}
          >
            {mutation.isPending ? "Updating…" : "Update password"}
          </Button>
          <Link component={RouterLink} to="/login" underline="hover">
            Back to sign in
          </Link>
        </Stack>
      </Box>
    </AuthLayout>
  );
}
