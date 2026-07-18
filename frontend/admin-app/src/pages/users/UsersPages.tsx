import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { ColumnDef } from "@tanstack/react-table";
import {
  InviteUserRequestSchema,
  queryKeys,
  type InviteUserRequest,
  type User,
  type UserPatchRequest,
} from "@palms/shared";
import { z } from "zod";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { DataTable } from "@/components/DataTable";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { PageHeader, PrimaryAction } from "@/components/PageHeader";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useListQueryState } from "@/hooks/useListQueryState";
import { useSnackbarStore } from "@/stores/uiStore";
import { formatDateTime } from "@/utils/format";
import { getErrorMessage } from "@/utils/errors";

export function UsersListPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const list = useListQueryState({ sort: "email", order: "asc" });
  const debouncedQuery = useDebouncedValue(list.searchDraft);

  const usersQuery = useQuery({
    queryKey: queryKeys.users.list({
      page: list.state.page,
      page_size: list.state.pageSize,
      query: debouncedQuery || undefined,
      sort: list.state.sort,
      order: list.state.order,
    }),
    queryFn: ({ signal }) =>
      client.users.list(
        {
          page: list.state.page,
          page_size: list.state.pageSize,
          query: debouncedQuery || undefined,
          sort: list.state.sort,
          order: list.state.order,
        },
        { signal },
      ),
  });

  const columns = useMemo<ColumnDef<User, unknown>[]>(
    () => [
      {
        id: "full_name",
        accessorKey: "full_name",
        header: "Name",
        enableSorting: true,
        cell: ({ row }) => (
          <Button component={RouterLink} to={`/users/${row.original.id}`} size="small">
            {row.original.full_name}
          </Button>
        ),
      },
      { id: "email", accessorKey: "email", header: "Email", enableSorting: true },
      {
        id: "role",
        header: "Role",
        cell: ({ row }) => row.original.role.name,
      },
      {
        id: "is_active",
        header: "Status",
        cell: ({ row }) => (
          <Chip
            size="small"
            label={row.original.is_active ? "Active" : "Disabled"}
            color={row.original.is_active ? "success" : "default"}
          />
        ),
      },
      {
        id: "last_login_at",
        header: "Last login",
        cell: ({ row }) => formatDateTime(row.original.last_login_at),
      },
    ],
    [],
  );

  return (
    <Box>
      <PageHeader
        title="Users"
        description="Invite and manage admin portal users."
        actions={
          can(PERMISSIONS.usersInvite) ? (
            <PrimaryAction to="/users/new" label="Invite user" />
          ) : null
        }
      />
      <TextField
        label="Search"
        size="small"
        value={list.searchDraft}
        onChange={(event) => {
          list.setSearchDraft(event.target.value);
          list.setQuery(event.target.value);
        }}
        sx={{ mb: 2, minWidth: 260 }}
      />
      {usersQuery.isLoading ? (
        <LoadingState />
      ) : usersQuery.isError || !usersQuery.data ? (
        <ErrorState description={getErrorMessage(usersQuery.error)} onRetry={() => usersQuery.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={usersQuery.data.items}
          total={usersQuery.data.pagination.total}
          page={list.state.page}
          pageSize={list.state.pageSize}
          onPageChange={list.setPage}
          onPageSizeChange={list.setPageSize}
          sort={list.state.sort}
          order={list.state.order}
          onSortChange={list.setSort}
          getRowId={(row) => row.id}
        />
      )}
    </Box>
  );
}

const InviteFormSchema = InviteUserRequestSchema;
type InviteFormValues = z.infer<typeof InviteFormSchema>;

export function UserInvitePage() {
  const client = useApiClient();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);

  const rolesQuery = useQuery({
    queryKey: queryKeys.users.list({ page_size: 100 }),
    queryFn: ({ signal }) => client.users.list({ page: 1, page_size: 100 }, { signal }),
  });

  const roleOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const user of rolesQuery.data?.items ?? []) {
      map.set(user.role.id, user.role.name);
    }
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [rolesQuery.data]);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<InviteFormValues>({
    resolver: zodResolver(InviteFormSchema),
    defaultValues: { email: "", full_name: "", role_id: "" },
  });

  const inviteMutation = useMutation({
    mutationFn: (input: InviteUserRequest) => client.users.invite(input),
    onSuccess: async () => {
      show("Invitation sent.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      navigate("/users");
    },
  });

  return (
    <Box>
      <PageHeader
        title="Invite user"
        crumbs={[{ label: "Users", to: "/users" }, { label: "Invite" }]}
      />
      <Box
        component="form"
        noValidate
        sx={{ maxWidth: 560 }}
        onSubmit={handleSubmit(async (values) => {
          await inviteMutation.mutateAsync(values);
        })}
      >
        <Stack spacing={2}>
          {inviteMutation.isError ? (
            <Alert severity="error">{getErrorMessage(inviteMutation.error)}</Alert>
          ) : null}
          <TextField
            label="Full name"
            required
            fullWidth
            error={Boolean(errors.full_name)}
            helperText={errors.full_name?.message}
            {...register("full_name")}
          />
          <TextField
            label="Email"
            type="email"
            required
            fullWidth
            error={Boolean(errors.email)}
            helperText={errors.email?.message}
            {...register("email")}
          />
          <TextField
            label="Role"
            select
            required
            fullWidth
            defaultValue=""
            error={Boolean(errors.role_id)}
            helperText={errors.role_id?.message ?? (roleOptions.length ? undefined : "Load existing users to discover role IDs.")}
            {...register("role_id")}
          >
            {roleOptions.map((role) => (
              <MenuItem key={role.id} value={role.id}>
                {role.name}
              </MenuItem>
            ))}
          </TextField>
          <Button type="submit" variant="contained" disabled={isSubmitting || inviteMutation.isPending}>
            Send invitation
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

export function UserDetailPage() {
  const { id = "" } = useParams();
  const client = useApiClient();
  const { can, user: currentUser } = useAuth();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);

  const userQuery = useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: ({ signal }) => client.users.get(id, { signal }),
    enabled: Boolean(id),
  });
  const auditQuery = useQuery({
    queryKey: queryKeys.users.auditLogs(id, { page: 1, page_size: 20 }),
    queryFn: ({ signal }) =>
      client.users.auditLogs(id, { page: 1, page_size: 20 }, { signal }),
    enabled: Boolean(id) && can(PERMISSIONS.auditLogsRead),
  });
  const rolesQuery = useQuery({
    queryKey: queryKeys.users.list({ page_size: 100 }),
    queryFn: ({ signal }) => client.users.list({ page: 1, page_size: 100 }, { signal }),
  });

  const roleOptions = useMemo(() => {
    const map = new Map<string, string>();
    for (const user of rolesQuery.data?.items ?? []) {
      map.set(user.role.id, user.role.name);
    }
    return Array.from(map.entries()).map(([roleId, name]) => ({ id: roleId, name }));
  }, [rolesQuery.data]);

  const [fullName, setFullName] = useState("");
  const [roleId, setRoleId] = useState("");

  useEffect(() => {
    if (userQuery.data) {
      setFullName(userQuery.data.full_name);
      setRoleId(userQuery.data.role.id);
    }
  }, [userQuery.data]);

  const updateMutation = useMutation({
    mutationFn: (input: UserPatchRequest) => client.users.update(id, input),
    onSuccess: async () => {
      show("User updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
      await queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(id) });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const disableMutation = useMutation({
    mutationFn: () => client.users.disable(id),
    onSuccess: async () => {
      show("User disabled.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(id) });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const enableMutation = useMutation({
    mutationFn: () => client.users.enable(id),
    onSuccess: async () => {
      show("User enabled.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(id) });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const resetMutation = useMutation({
    mutationFn: () => client.users.requestPasswordReset(id),
    onSuccess: () => show("Password reset email requested.", "success"),
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  if (userQuery.isLoading) return <LoadingState />;
  if (userQuery.isError || !userQuery.data) {
    return <ErrorState description={getErrorMessage(userQuery.error)} onRetry={() => userQuery.refetch()} />;
  }

  const user = userQuery.data;
  const isSelf = currentUser?.id === user.id;

  return (
    <Box>
      <PageHeader
        title={user.full_name}
        crumbs={[{ label: "Users", to: "/users" }, { label: user.full_name }]}
        actions={
          <>
            {can(PERMISSIONS.usersDisable) && !isSelf ? (
              user.is_active ? (
                <Button color="warning" variant="outlined" onClick={() => disableMutation.mutate()}>
                  Disable
                </Button>
              ) : (
                <Button variant="outlined" onClick={() => enableMutation.mutate()}>
                  Enable
                </Button>
              )
            ) : null}
            {can(PERMISSIONS.usersResetPassword) ? (
              <Button variant="outlined" onClick={() => resetMutation.mutate()}>
                Reset password
              </Button>
            ) : null}
          </>
        }
      />

      <Stack spacing={2} sx={{ maxWidth: 720 }}>
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={1}>
              <Typography>Email: {user.email}</Typography>
              <Typography>Role: {user.role.name}</Typography>
              <Typography>Status: {user.is_active ? "Active" : "Disabled"}</Typography>
              <Typography>Last login: {formatDateTime(user.last_login_at)}</Typography>
            </Stack>
          </CardContent>
        </Card>

        {can(PERMISSIONS.usersUpdate) ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Edit user
              </Typography>
              <Stack spacing={2}>
                <TextField
                  label="Full name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  fullWidth
                />
                <TextField
                  label="Role"
                  select
                  value={roleId}
                  onChange={(event) => setRoleId(event.target.value)}
                  fullWidth
                >
                  {roleOptions.map((role) => (
                    <MenuItem key={role.id} value={role.id}>
                      {role.name}
                    </MenuItem>
                  ))}
                </TextField>
                <Button
                  variant="contained"
                  disabled={updateMutation.isPending}
                  onClick={() =>
                    updateMutation.mutate({
                      full_name: fullName,
                      role_id: roleId,
                    })
                  }
                >
                  Save changes
                </Button>
              </Stack>
            </CardContent>
          </Card>
        ) : null}

        {can(PERMISSIONS.auditLogsRead) ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Audit logs
              </Typography>
              {auditQuery.isLoading ? (
                <LoadingState />
              ) : (
                <Stack spacing={1}>
                  {(auditQuery.data?.items ?? []).map((log) => (
                    <Box key={log.id}>
                      <Typography fontWeight={600}>{log.action}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {log.entity_type} · {formatDateTime(log.created_at)}
                      </Typography>
                    </Box>
                  ))}
                  {(auditQuery.data?.items.length ?? 0) === 0 ? (
                    <Typography color="text.secondary">No audit events for this user.</Typography>
                  ) : null}
                </Stack>
              )}
            </CardContent>
          </Card>
        ) : null}
      </Stack>
    </Box>
  );
}
