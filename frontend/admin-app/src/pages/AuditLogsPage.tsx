import { useQuery } from "@tanstack/react-query";
import { Box, Card, CardContent, Stack, Typography } from "@mui/material";
import { queryKeys } from "@palms/shared";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { useListQueryState } from "@/hooks/useListQueryState";
import { formatDateTime } from "@/utils/format";
import { getErrorMessage } from "@/utils/errors";
import { DataTable } from "@/components/DataTable";
import { useMemo } from "react";
import type { ColumnDef } from "@tanstack/react-table";
import type { Activity } from "./auditTypes";

export function AuditLogsPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const list = useListQueryState({ pageSize: 25 });

  const activityQuery = useQuery({
    queryKey: queryKeys.dashboard.activity({
      page: list.state.page,
      page_size: list.state.pageSize,
    }),
    queryFn: ({ signal }) =>
      client.dashboard.activity(
        { page: list.state.page, page_size: list.state.pageSize },
        { signal },
      ),
    enabled: can(PERMISSIONS.palmsRead) || can(PERMISSIONS.auditLogsRead),
  });

  const columns = useMemo<ColumnDef<Activity, unknown>[]>(
    () => [
      {
        id: "created_at",
        header: "When",
        cell: ({ row }) => formatDateTime(row.original.created_at),
      },
      { id: "action", accessorKey: "action", header: "Action" },
      { id: "entity_type", accessorKey: "entity_type", header: "Entity" },
      {
        id: "message",
        header: "Message",
        cell: ({ row }) => row.original.message ?? "—",
      },
    ],
    [],
  );

  if (!can(PERMISSIONS.palmsRead) && !can(PERMISSIONS.auditLogsRead)) {
    return (
      <ErrorState
        title="Access denied"
        description="You do not have permission to view audit activity."
      />
    );
  }

  return (
    <Box>
      <PageHeader
        title="Audit logs"
        description="Operational activity feed. Detailed per-user audit trails are available on each user detail page."
      />
      {can(PERMISSIONS.auditLogsRead) ? (
        <Card variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="body2" color="text.secondary">
              Tip: open Users → a user → Audit logs for mutation-level history for that actor.
            </Typography>
          </CardContent>
        </Card>
      ) : null}
      {activityQuery.isLoading ? (
        <LoadingState />
      ) : activityQuery.isError || !activityQuery.data ? (
        <ErrorState
          description={getErrorMessage(activityQuery.error)}
          onRetry={() => activityQuery.refetch()}
        />
      ) : (
        <Stack spacing={2}>
          <DataTable
            columns={columns}
            data={activityQuery.data.items}
            total={activityQuery.data.pagination.total}
            page={list.state.page}
            pageSize={list.state.pageSize}
            onPageChange={list.setPage}
            onPageSizeChange={list.setPageSize}
            getRowId={(row) => row.id}
            emptyTitle="No activity yet"
          />
        </Stack>
      )}
    </Box>
  );
}
