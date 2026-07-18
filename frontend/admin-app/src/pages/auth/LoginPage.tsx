import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link as RouterLink, Navigate, useLocation, useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Link,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { LoginRequestSchema, type LoginRequest } from "@palms/shared";

import { useAuth } from "@/auth/useAuth";
import { LoadingState } from "@/components/ErrorState";

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, isLoading, login } = useAuth();
  const from =
    (location.state as { from?: string } | null)?.from &&
    (location.state as { from: string }).from !== "/login"
      ? (location.state as { from: string }).from
      : "/overview";

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginRequest>({
    resolver: zodResolver(LoginRequestSchema),
    defaultValues: { email: "", password: "" },
  });

  if (isLoading) return <LoadingState label="Checking session" />;
  if (isAuthenticated) return <Navigate to={from} replace />;

  return (
    <AuthLayout title="Sign in" subtitle="Manage palms, donors, and reports.">
      <Box
        component="form"
        noValidate
        onSubmit={handleSubmit(async (values) => {
          await login.mutateAsync(values);
          navigate(from, { replace: true });
        })}
      >
        <Stack spacing={2}>
          {login.isError ? (
            <Alert severity="error">{login.error.message}</Alert>
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
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            fullWidth
            error={Boolean(errors.password)}
            helperText={errors.password?.message}
            {...register("password")}
          />
          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={login.isPending}
          >
            {login.isPending ? "Signing in…" : "Sign in"}
          </Button>
          <Link component={RouterLink} to="/forgot-password" underline="hover">
            Forgot password?
          </Link>
        </Stack>
      </Box>
    </AuthLayout>
  );
}

export function AuthLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        px: 2,
        background:
          "radial-gradient(circle at top left, rgba(46, 125, 100, 0.18), transparent 40%), linear-gradient(160deg, #f4f7f5 0%, #e8f0ec 55%, #f7f3ec 100%)",
      }}
    >
      <Paper sx={{ width: "100%", maxWidth: 440, p: { xs: 3, sm: 4 } }} elevation={0} variant="outlined">
        <Stack spacing={0.5} sx={{ mb: 3 }}>
          <Typography variant="overline" color="primary" fontWeight={700}>
            Palms Admin
          </Typography>
          <Typography variant="h4" component="h1">
            {title}
          </Typography>
          <Typography color="text.secondary">{subtitle}</Typography>
        </Stack>
        {children}
      </Paper>
    </Box>
  );
}
