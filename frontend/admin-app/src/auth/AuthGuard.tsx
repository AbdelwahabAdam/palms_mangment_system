import { Navigate, Outlet, useLocation } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";

import { useAuth } from "@/auth/useAuth";
import { hasPermission, type PermissionCode } from "@/auth/permissions";
import { ErrorState } from "@/components/ErrorState";

interface AuthGuardProps {
  permission?: PermissionCode | PermissionCode[];
}

export function AuthGuard({ permission }: AuthGuardProps) {
  const location = useLocation();
  const { user, isLoading, isError, permissions } = useAuth();

  if (isLoading) {
    return (
      <Box
        role="status"
        aria-live="polite"
        aria-label="Checking authentication"
        sx={{
          minHeight: "100vh",
          display: "grid",
          placeItems: "center",
        }}
      >
        <CircularProgress />
      </Box>
    );
  }

  if (isError || !user) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: location.pathname + location.search }}
      />
    );
  }

  if (permission && !hasPermission(permissions, permission)) {
    return (
      <Box sx={{ p: 4 }}>
        <ErrorState
          title="Access denied"
          description="You do not have permission to view this page."
        />
      </Box>
    );
  }

  return <Outlet />;
}
