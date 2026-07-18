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
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import type { ColumnDef } from "@tanstack/react-table";
import {
  SectionCreateRequestSchema,
  queryKeys,
  type Section,
  type SectionCreateRequest,
  type SectionPatchRequest,
} from "@palms/shared";
import { z } from "zod";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { DataTable } from "@/components/DataTable";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { FileDropzone } from "@/components/FileDropzone";
import { PageHeader, PrimaryAction } from "@/components/PageHeader";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useListQueryState } from "@/hooks/useListQueryState";
import { useSnackbarStore } from "@/stores/uiStore";
import { getErrorMessage } from "@/utils/errors";

export function SectionsListPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const list = useListQueryState({ sort: "name", order: "asc" });
  const debouncedQuery = useDebouncedValue(list.searchDraft);

  const sectionsQuery = useQuery({
    queryKey: queryKeys.sections.list({
      page: list.state.page,
      page_size: list.state.pageSize,
      query: debouncedQuery || undefined,
      sort: list.state.sort,
      order: list.state.order,
    }),
    queryFn: ({ signal }) =>
      client.sections.list(
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

  const columns = useMemo<ColumnDef<Section, unknown>[]>(
    () => [
      {
        id: "name",
        accessorKey: "name",
        header: "Name",
        enableSorting: true,
        cell: ({ row }) => (
          <Button component={RouterLink} to={`/sections/${row.original.id}`} size="small">
            {row.original.name}
          </Button>
        ),
      },
      {
        id: "location_name",
        header: "Location",
        cell: ({ row }) => row.original.location_name ?? "—",
      },
      {
        id: "palm_count",
        header: "Palms",
        cell: ({ row }) => row.original.palm_count ?? "—",
      },
      {
        id: "irrigation_type",
        header: "Irrigation",
        cell: ({ row }) => row.original.irrigation_type ?? "—",
      },
    ],
    [],
  );

  return (
    <Box>
      <PageHeader
        title="Sections"
        description="Orchard sections and planting locations."
        actions={
          can(PERMISSIONS.sectionsCreate) ? (
            <PrimaryAction to="/sections/new" label="New section" />
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
      {sectionsQuery.isLoading ? (
        <LoadingState />
      ) : sectionsQuery.isError || !sectionsQuery.data ? (
        <ErrorState description={getErrorMessage(sectionsQuery.error)} onRetry={() => sectionsQuery.refetch()} />
      ) : (
        <DataTable
          columns={columns}
          data={sectionsQuery.data.items}
          total={sectionsQuery.data.pagination.total}
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

const SectionFormSchema = SectionCreateRequestSchema;
type SectionFormValues = z.infer<typeof SectionFormSchema>;

export function SectionFormPage({ mode }: { mode: "create" | "edit" }) {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);

  const sectionQuery = useQuery({
    queryKey: queryKeys.sections.detail(id),
    queryFn: ({ signal }) => client.sections.get(id, { signal }),
    enabled: mode === "edit" && Boolean(id),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SectionFormValues>({
    resolver: zodResolver(SectionFormSchema),
    defaultValues: {
      name: "",
      description: null,
      location_name: null,
      soil_type: null,
      irrigation_type: null,
      gps_latitude: null,
      gps_longitude: null,
    },
  });

  useEffect(() => {
    if (sectionQuery.data) {
      reset({
        name: sectionQuery.data.name,
        description: sectionQuery.data.description,
        location_name: sectionQuery.data.location_name,
        soil_type: sectionQuery.data.soil_type,
        irrigation_type: sectionQuery.data.irrigation_type,
        gps_latitude: sectionQuery.data.gps_latitude,
        gps_longitude: sectionQuery.data.gps_longitude,
      });
    }
  }, [sectionQuery.data, reset]);

  const createMutation = useMutation({
    mutationFn: (input: SectionCreateRequest) => client.sections.create(input),
    onSuccess: async (section) => {
      show("Section created.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.sections.all });
      navigate(`/sections/${section.id}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (input: SectionPatchRequest) => client.sections.update(id, input),
    onSuccess: async (section) => {
      show("Section updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.sections.all });
      navigate(`/sections/${section.id}`);
    },
  });

  if (mode === "edit" && sectionQuery.isLoading) return <LoadingState />;
  if (mode === "edit" && (sectionQuery.isError || !sectionQuery.data)) {
    return <ErrorState description={getErrorMessage(sectionQuery.error)} onRetry={() => sectionQuery.refetch()} />;
  }

  const mutationError = createMutation.error ?? updateMutation.error;

  return (
    <Box>
      <PageHeader
        title={mode === "create" ? "New section" : `Edit ${sectionQuery.data?.name ?? "section"}`}
        crumbs={[
          { label: "Sections", to: "/sections" },
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
            description: values.description || null,
            location_name: values.location_name || null,
            soil_type: values.soil_type || null,
            irrigation_type: values.irrigation_type || null,
            gps_latitude: values.gps_latitude || null,
            gps_longitude: values.gps_longitude || null,
          };
          if (mode === "create") await createMutation.mutateAsync(payload);
          else await updateMutation.mutateAsync(payload);
        })}
      >
        <Stack spacing={2}>
          {mutationError ? <Alert severity="error">{getErrorMessage(mutationError)}</Alert> : null}
          <TextField label="Name" required fullWidth error={Boolean(errors.name)} helperText={errors.name?.message} {...register("name")} />
          <TextField label="Location" fullWidth {...register("location_name")} />
          <TextField label="Soil type" fullWidth {...register("soil_type")} />
          <TextField label="Irrigation" fullWidth {...register("irrigation_type")} />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField label="Latitude" fullWidth {...register("gps_latitude")} />
            <TextField label="Longitude" fullWidth {...register("gps_longitude")} />
          </Stack>
          <TextField label="Description" fullWidth multiline minRows={3} {...register("description")} />
          <Stack direction="row" spacing={1}>
            <Button type="submit" variant="contained" disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}>
              {mode === "create" ? "Create section" : "Save changes"}
            </Button>
            <Button onClick={() => navigate(-1)}>Cancel</Button>
          </Stack>
        </Stack>
      </Box>
    </Box>
  );
}

export function SectionCreatePage() {
  return <SectionFormPage mode="create" />;
}

export function SectionDetailPage() {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [reassignTo, setReassignTo] = useState("");
  const [editing, setEditing] = useState(false);

  const sectionQuery = useQuery({
    queryKey: queryKeys.sections.detail(id),
    queryFn: ({ signal }) => client.sections.get(id, { signal }),
    enabled: Boolean(id),
  });
  const sectionsQuery = useQuery({
    queryKey: queryKeys.sections.list({ page_size: 100 }),
    queryFn: ({ signal }) => client.sections.list({ page: 1, page_size: 100 }, { signal }),
    enabled: confirmDelete,
  });

  const deleteMutation = useMutation({
    mutationFn: () => client.sections.remove(id, reassignTo || undefined),
    onSuccess: async (result) => {
      show(
        `Section deleted${result.reassigned_palm_count ? ` and ${result.reassigned_palm_count} palms reassigned` : ""}.`,
        "success",
      );
      await queryClient.invalidateQueries({ queryKey: queryKeys.sections.all });
      navigate("/sections");
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      client.sections.uploadImage(id, { file, filename: file.name }),
    onSuccess: async () => {
      show("Section image updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.sections.detail(id) });
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  if (sectionQuery.isLoading) return <LoadingState />;
  if (sectionQuery.isError || !sectionQuery.data) {
    return <ErrorState description={getErrorMessage(sectionQuery.error)} onRetry={() => sectionQuery.refetch()} />;
  }

  const section = sectionQuery.data;

  if (editing && can(PERMISSIONS.sectionsUpdate)) {
    return (
      <Box>
        <Button sx={{ mb: 2 }} onClick={() => setEditing(false)}>
          Back to detail
        </Button>
        <SectionFormPage mode="edit" />
      </Box>
    );
  }

  return (
    <Box>
      <PageHeader
        title={section.name}
        crumbs={[{ label: "Sections", to: "/sections" }, { label: section.name }]}
        actions={
          <>
            {can(PERMISSIONS.sectionsUpdate) ? (
              <Button variant="contained" onClick={() => setEditing(true)}>
                Edit
              </Button>
            ) : null}
            {can(PERMISSIONS.sectionsDelete) ? (
              <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
                Delete
              </Button>
            ) : null}
          </>
        }
      />
      <Stack spacing={2}>
        <Card variant="outlined">
          <CardContent>
            <Stack spacing={1.5}>
              {[
                ["Location", section.location_name ?? "—"],
                ["Soil", section.soil_type ?? "—"],
                ["Irrigation", section.irrigation_type ?? "—"],
                ["Palms", String(section.palm_count ?? 0)],
                ["GPS", section.gps_latitude && section.gps_longitude ? `${section.gps_latitude}, ${section.gps_longitude}` : "—"],
                ["Description", section.description ?? "—"],
              ].map(([label, value]) => (
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
        <Card variant="outlined">
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Section image
            </Typography>
            {section.image_url ? (
              <Box
                component="img"
                src={section.image_url}
                alt={section.name}
                sx={{ maxWidth: "100%", maxHeight: 280, borderRadius: 1, mb: 2 }}
              />
            ) : (
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                No image uploaded.
              </Typography>
            )}
            {can(PERMISSIONS.sectionsUpdate) ? (
              <FileDropzone
                onFile={(file) => uploadMutation.mutate(file)}
                disabled={uploadMutation.isPending}
              />
            ) : null}
          </CardContent>
        </Card>
      </Stack>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete section?"
        description="If palms remain in this section, choose a reassignment target."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
      {confirmDelete ? (
        <Box sx={{ mt: 2, maxWidth: 420 }}>
          <TextField
            label="Reassign palms to"
            select
            fullWidth
            value={reassignTo}
            onChange={(event) => setReassignTo(event.target.value)}
          >
            <MenuItem value="">None</MenuItem>
            {(sectionsQuery.data?.items ?? [])
              .filter((item) => item.id !== id)
              .map((item) => (
                <MenuItem key={item.id} value={item.id}>
                  {item.name}
                </MenuItem>
              ))}
          </TextField>
        </Box>
      ) : null}
    </Box>
  );
}
