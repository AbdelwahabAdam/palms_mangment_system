import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import type { ColumnDef, RowSelectionState } from "@tanstack/react-table";
import { queryKeys, type Palm } from "@palms/shared";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { DataTable } from "@/components/DataTable";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { PageHeader, PrimaryAction } from "@/components/PageHeader";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useListQueryState } from "@/hooks/useListQueryState";
import { useSnackbarStore } from "@/stores/uiStore";
import { formatDate } from "@/utils/format";
import { getErrorMessage } from "@/utils/errors";

export function PalmsListPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const list = useListQueryState({
    sort: "code",
    order: "asc",
    filterKeys: ["status", "section_id", "donor_id"],
  });
  const debouncedQuery = useDebouncedValue(list.searchDraft);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [bulkSectionId, setBulkSectionId] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const palmsListParams = {
    page: list.state.page,
    page_size: list.state.pageSize,
    query: debouncedQuery || undefined,
    sort: list.state.sort,
    order: list.state.order,
    status: list.state.filters.status || undefined,
    section_id: list.state.filters.section_id || undefined,
    donor_id: list.state.filters.donor_id || undefined,
  };

  const palmsQuery = useQuery({
    queryKey: [...queryKeys.palms.all, "list", palmsListParams] as const,
    queryFn: ({ signal }) => client.palms.list(palmsListParams, { signal }),
  });

  const sectionsQuery = useQuery({
    queryKey: queryKeys.sections.list({ page_size: 100 }),
    queryFn: ({ signal }) =>
      client.sections.list({ page: 1, page_size: 100 }, { signal }),
  });

  const selectedIds = Object.keys(rowSelection);

  const bulkDelete = useMutation({
    mutationFn: () => client.palms.bulkDelete(selectedIds),
    onSuccess: async (result) => {
      show(`Deleted ${result.deleted_count} palm(s).`, "success");
      setRowSelection({});
      setConfirmDelete(false);
      await queryClient.invalidateQueries({ queryKey: queryKeys.palms.all });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const bulkSection = useMutation({
    mutationFn: () => client.palms.bulkUpdateSection(selectedIds, bulkSectionId),
    onSuccess: async (result) => {
      show(`Updated section for ${result.updated_count} palm(s).`, "success");
      setRowSelection({});
      setBulkSectionId("");
      await queryClient.invalidateQueries({ queryKey: queryKeys.palms.all });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const columns = useMemo<ColumnDef<Palm, unknown>[]>(
    () => [
      {
        id: "code",
        accessorKey: "code",
        header: "Code",
        enableSorting: true,
        cell: ({ row }) => (
          <Button
            component={RouterLink}
            to={`/palms/${row.original.id}`}
            size="small"
          >
            {row.original.code}
          </Button>
        ),
      },
      {
        id: "donor",
        header: "Donor",
        cell: ({ row }) => row.original.donor?.full_name ?? "—",
      },
      {
        id: "section",
        header: "Section",
        cell: ({ row }) => row.original.section?.name ?? "—",
      },
      {
        id: "status",
        accessorKey: "status",
        header: "Status",
        enableSorting: true,
      },
      {
        id: "plantation_date",
        accessorKey: "plantation_date",
        header: "Planted",
        enableSorting: true,
        cell: ({ row }) => formatDate(row.original.plantation_date),
      },
    ],
    [],
  );

  return (
    <Box>
      <PageHeader
        title="Palms"
        description="Search, filter, and manage palm records."
        actions={
          can(PERMISSIONS.palmsCreate) ? (
            <PrimaryAction to="/palms/new" label="New palm" />
          ) : null
        }
      />

      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={1.5}
        sx={{ mb: 2 }}
        useFlexGap
        flexWrap="wrap"
      >
        <TextField
          label="Search"
          size="small"
          value={list.searchDraft}
          onChange={(event) => {
            list.setSearchDraft(event.target.value);
            list.setQuery(event.target.value);
          }}
          sx={{ minWidth: 220 }}
        />
        <TextField
          label="Status"
          size="small"
          select
          value={list.state.filters.status ?? ""}
          onChange={(event) => list.setFilter("status", event.target.value)}
          sx={{ minWidth: 160 }}
        >
          <MenuItem value="">All</MenuItem>
          <MenuItem value="active">Active</MenuItem>
          <MenuItem value="inactive">Inactive</MenuItem>
        </TextField>
        <TextField
          label="Section"
          size="small"
          select
          value={list.state.filters.section_id ?? ""}
          onChange={(event) => list.setFilter("section_id", event.target.value)}
          sx={{ minWidth: 180 }}
        >
          <MenuItem value="">All</MenuItem>
          {(sectionsQuery.data?.items ?? []).map((section) => (
            <MenuItem key={section.id} value={section.id}>
              {section.name}
            </MenuItem>
          ))}
        </TextField>
      </Stack>

      {selectedIds.length > 0 ? (
        <Stack direction="row" spacing={1} sx={{ mb: 2 }} alignItems="center" flexWrap="wrap" useFlexGap>
          <Box sx={{ typography: "body2" }}>{selectedIds.length} selected</Box>
          {can(PERMISSIONS.palmsBulkUpdate) ? (
            <>
              <TextField
                label="Move to section"
                size="small"
                select
                value={bulkSectionId}
                onChange={(event) => setBulkSectionId(event.target.value)}
                sx={{ minWidth: 200 }}
              >
                {(sectionsQuery.data?.items ?? []).map((section) => (
                  <MenuItem key={section.id} value={section.id}>
                    {section.name}
                  </MenuItem>
                ))}
              </TextField>
              <Button
                variant="outlined"
                disabled={!bulkSectionId || bulkSection.isPending}
                onClick={() => bulkSection.mutate()}
              >
                Update section
              </Button>
            </>
          ) : null}
          {can(PERMISSIONS.palmsDelete) ? (
            <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
              Delete selected
            </Button>
          ) : null}
        </Stack>
      ) : null}

      {palmsQuery.isLoading ? (
        <LoadingState label="Loading palms" />
      ) : palmsQuery.isError || !palmsQuery.data ? (
        <ErrorState
          description={getErrorMessage(palmsQuery.error)}
          onRetry={() => palmsQuery.refetch()}
        />
      ) : (
        <DataTable
          columns={columns}
          data={palmsQuery.data.items}
          total={palmsQuery.data.pagination.total}
          page={list.state.page}
          pageSize={list.state.pageSize}
          onPageChange={list.setPage}
          onPageSizeChange={list.setPageSize}
          sort={list.state.sort}
          order={list.state.order}
          onSortChange={list.setSort}
          getRowId={(row) => row.id}
          selectable={can([PERMISSIONS.palmsDelete, PERMISSIONS.palmsBulkUpdate])}
          rowSelection={rowSelection}
          onRowSelectionChange={setRowSelection}
          emptyTitle="No palms found"
        />
      )}

      <ConfirmDialog
        open={confirmDelete}
        title="Delete selected palms?"
        description={`This will permanently delete ${selectedIds.length} palm(s).`}
        confirmLabel="Delete"
        danger
        loading={bulkDelete.isPending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => bulkDelete.mutate()}
      />
    </Box>
  );
}
