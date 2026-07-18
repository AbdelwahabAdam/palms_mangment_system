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
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { ColumnDef } from "@tanstack/react-table";
import {
  DonorCreateRequestSchema,
  queryKeys,
  type Donor,
  type DonorCreateRequest,
  type DonorPatchRequest,
} from "@palms/shared";
import { z } from "zod";

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

export function DonorsListPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const list = useListQueryState({ sort: "full_name", order: "asc" });
  const debouncedQuery = useDebouncedValue(list.searchDraft);

  const donorsQuery = useQuery({
    queryKey: queryKeys.donors.list({
      page: list.state.page,
      page_size: list.state.pageSize,
      query: debouncedQuery || undefined,
      sort: list.state.sort,
      order: list.state.order,
    }),
    queryFn: ({ signal }) =>
      client.donors.list(
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

  const columns = useMemo<ColumnDef<Donor, unknown>[]>(
    () => [
      {
        id: "full_name",
        accessorKey: "full_name",
        header: "Name",
        enableSorting: true,
        cell: ({ row }) => (
          <Button component={RouterLink} to={`/donors/${row.original.id}`} size="small">
            {row.original.full_name}
          </Button>
        ),
      },
      { id: "email", accessorKey: "email", header: "Email", cell: ({ row }) => row.original.email ?? "—" },
      { id: "phone", accessorKey: "phone", header: "Phone", cell: ({ row }) => row.original.phone ?? "—" },
      {
        id: "donation_date",
        accessorKey: "donation_date",
        header: "Donation date",
        enableSorting: true,
        cell: ({ row }) => formatDate(row.original.donation_date),
      },
      {
        id: "palm_count",
        header: "Palms",
        cell: ({ row }) => row.original.palm_count ?? "—",
      },
    ],
    [],
  );

  return (
    <Box>
      <PageHeader
        title="Donors"
        description="Manage donor records and linked palms."
        actions={
          can(PERMISSIONS.donorsCreate) ? (
            <PrimaryAction to="/donors/new" label="New donor" />
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
      {donorsQuery.isLoading ? (
        <LoadingState />
      ) : donorsQuery.isError || !donorsQuery.data ? (
        <ErrorState description={getErrorMessage(donorsQuery.error)} onRetry={() => donorsQuery.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={donorsQuery.data.items}
          total={donorsQuery.data.pagination.total}
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

const DonorFormSchema = DonorCreateRequestSchema;
type DonorFormValues = z.infer<typeof DonorFormSchema>;

export function DonorFormPage({ mode }: { mode: "create" | "edit" }) {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);

  const donorQuery = useQuery({
    queryKey: queryKeys.donors.detail(id),
    queryFn: ({ signal }) => client.donors.get(id, { signal }),
    enabled: mode === "edit" && Boolean(id),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DonorFormValues>({
    resolver: zodResolver(DonorFormSchema),
    defaultValues: {
      full_name: "",
      phone: null,
      email: null,
      address: null,
      donation_date: null,
      notes: null,
    },
  });

  useEffect(() => {
    if (donorQuery.data) {
      reset({
        full_name: donorQuery.data.full_name,
        phone: donorQuery.data.phone,
        email: donorQuery.data.email,
        address: donorQuery.data.address,
        donation_date: donorQuery.data.donation_date,
        notes: donorQuery.data.notes,
      });
    }
  }, [donorQuery.data, reset]);

  const createMutation = useMutation({
    mutationFn: (input: DonorCreateRequest) => client.donors.create(input),
    onSuccess: async (donor) => {
      show("Donor created.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.donors.all });
      navigate(`/donors/${donor.id}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (input: DonorPatchRequest) => client.donors.update(id, input),
    onSuccess: async (donor) => {
      show("Donor updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.donors.all });
      navigate(`/donors/${donor.id}`);
    },
  });

  if (mode === "edit" && donorQuery.isLoading) return <LoadingState />;
  if (mode === "edit" && (donorQuery.isError || !donorQuery.data)) {
    return <ErrorState description={getErrorMessage(donorQuery.error)} onRetry={() => donorQuery.refetch()} />;
  }

  const mutationError = createMutation.error ?? updateMutation.error;

  return (
    <Box>
      <PageHeader
        title={mode === "create" ? "New donor" : `Edit ${donorQuery.data?.full_name ?? "donor"}`}
        crumbs={[
          { label: "Donors", to: "/donors" },
          { label: mode === "create" ? "New" : "Edit" },
        ]}
      />
      <Box
        component="form"
        noValidate
        sx={{ maxWidth: 720 }}
        onSubmit={handleSubmit(async (values) => {
          const payload = {
            ...values,
            phone: values.phone || null,
            email: values.email || null,
            address: values.address || null,
            donation_date: values.donation_date || null,
            notes: values.notes || null,
          };
          if (mode === "create") await createMutation.mutateAsync(payload);
          else await updateMutation.mutateAsync(payload);
        })}
      >
        <Stack spacing={2}>
          {mutationError ? <Alert severity="error">{getErrorMessage(mutationError)}</Alert> : null}
          <TextField label="Full name" required fullWidth error={Boolean(errors.full_name)} helperText={errors.full_name?.message} {...register("full_name")} />
          <TextField label="Email" type="email" fullWidth error={Boolean(errors.email)} helperText={errors.email?.message} {...register("email")} />
          <TextField label="Phone" fullWidth {...register("phone")} />
          <TextField label="Address" fullWidth multiline minRows={2} {...register("address")} />
          <TextField label="Donation date" type="date" fullWidth InputLabelProps={{ shrink: true }} {...register("donation_date")} />
          <TextField label="Notes" fullWidth multiline minRows={3} {...register("notes")} />
          <Stack direction="row" spacing={1}>
            <Button type="submit" variant="contained" disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}>
              {mode === "create" ? "Create donor" : "Save changes"}
            </Button>
            <Button onClick={() => navigate(-1)}>Cancel</Button>
          </Stack>
        </Stack>
      </Box>
    </Box>
  );
}

export function DonorCreatePage() {
  return <DonorFormPage mode="create" />;
}

export function DonorDetailPage() {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [editing, setEditing] = useState(false);

  const donorQuery = useQuery({
    queryKey: queryKeys.donors.detail(id),
    queryFn: ({ signal }) => client.donors.get(id, { signal }),
    enabled: Boolean(id),
  });
  const palmsQuery = useQuery({
    queryKey: queryKeys.donors.palms(id, { page: 1, page_size: 50 }),
    queryFn: ({ signal }) => client.donors.palms(id, { page: 1, page_size: 50 }, { signal }),
    enabled: Boolean(id),
  });

  const deleteMutation = useMutation({
    mutationFn: () => client.donors.remove(id),
    onSuccess: async () => {
      show("Donor deleted.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.donors.all });
      navigate("/donors");
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  if (donorQuery.isLoading) return <LoadingState />;
  if (donorQuery.isError || !donorQuery.data) {
    return <ErrorState description={getErrorMessage(donorQuery.error)} onRetry={() => donorQuery.refetch()} />;
  }

  const donor = donorQuery.data;

  if (editing && can(PERMISSIONS.donorsUpdate)) {
    return (
      <Box>
        <Button sx={{ mb: 2 }} onClick={() => setEditing(false)}>
          Back to detail
        </Button>
        <DonorFormPage mode="edit" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={donor.full_name}
        crumbs={[{ label: "Donors", to: "/donors" }, { label: donor.full_name }]}
        actions={
          <>
            {can(PERMISSIONS.donorsUpdate) ? (
              <Button variant="contained" onClick={() => setEditing(true)}>
                Edit
              </Button>
            ) : null}
            {can(PERMISSIONS.donorsDelete) ? (
              <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
                Delete
              </Button>
            ) : null}
          </>
        }
      />
      <GridInfo
        items={[
          ["Email", donor.email ?? "—"],
          ["Phone", donor.phone ?? "—"],
          ["Donation date", formatDate(donor.donation_date)],
          ["Address", donor.address ?? "—"],
          ["Notes", donor.notes ?? "—"],
        ]}
      />
      <Typography variant="h6" sx={{ mt: 3, mb: 1 }}>
        Linked palms
      </Typography>
      {palmsQuery.isLoading ? (
        <LoadingState />
      ) : (
        <Stack spacing={1}>
          {(palmsQuery.data?.items ?? []).map((palm) => (
            <Button key={palm.id} component={RouterLink} to={`/palms/${palm.id}`} sx={{ justifyContent: "flex-start" }}>
              {palm.code} · {palm.status}
            </Button>
          ))}
          {(palmsQuery.data?.items.length ?? 0) === 0 ? (
            <Typography color="text.secondary">No palms linked to this donor.</Typography>
          ) : null}
        </Stack>
      )}
      <ConfirmDialog
        open={confirmDelete}
        title="Delete donor?"
        description="This permanently removes the donor record."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
    </Box>
  );
}

function GridInfo({ items }: { items: Array<[string, string]> }) {
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          {items.map(([label, value]) => (
            <Box key={label}>
              <Typography variant="body2" color="text.secondary">
                {label}
              </Typography>
              <Typography>{value}</Typography>
            </Box>
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}
