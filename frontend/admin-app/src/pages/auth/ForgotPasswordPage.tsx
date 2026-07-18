import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link as RouterLink } from "react-router-dom";
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
  ForgotPasswordRequestSchema,
  type ForgotPasswordRequest,
} from "@palms/shared";

import { useApiClient } from "@/api/ApiClientProvider";
import { AuthLayout } from "@/pages/auth/LoginPage";
import { getErrorMessage } from "@/utils/errors";

export function ForgotPasswordPage() {
  const client = useApiClient();
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordRequest>({
    resolver: zodResolver(ForgotPasswordRequestSchema),
    defaultValues: { email: "" },
  });

  const mutation = useMutation({
    mutationFn: (input: ForgotPasswordRequest) =>
      client.auth.forgotPassword(input),
  });

  return (
    <AuthLayout
      title="Forgot password"
      subtitle="We'll email a reset link if the account exists."
    >
      <Box
        component="form"
        noValidate
        onSubmit={handleSubmit(async (values) => {
          await mutation.mutateAsync(values);
        })}
      >
        <Stack spacing={2}>
          {mutation.isSuccess ? (
            <Alert severity="success">{mutation.data.message}</Alert>
          ) : null}
          {mutation.isError ? (
            <Alert severity="error">
              {getErrorMessage(mutation.error, "Request failed.")}
            </Alert>
          ) : null}
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            required
            fullWidth
            error={Boolean(errors.email)}
            helperText={errors.email?.message}
            {...register("email")}
          />
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={mutation.isPending}
          >
            {mutation.isPending ? "Sending…" : "Send reset link"}
          </Button>
          <Link component={RouterLink} to="/login" underline="hover">
            Back to sign in
          </Link>
        </Stack>
      </Box>
    </AuthLayout>
  );
}
