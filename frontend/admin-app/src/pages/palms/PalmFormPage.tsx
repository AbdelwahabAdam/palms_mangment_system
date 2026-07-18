import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import {
  PalmCreateRequestSchema,
  queryKeys,
  type PalmCreateRequest,
  type PalmPatchRequest,
} from "@palms/shared";
import { z } from "zod";

import { useApiClient } from "@/api/ApiClientProvider";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { useSnackbarStore } from "@/stores/uiStore";
import { getErrorMessage } from "@/utils/errors";

const FormSchema = PalmCreateRequestSchema;
type FormValues = z.infer<typeof FormSchema>;

export function PalmFormPage({ mode }: { mode: "create" | "edit" }) {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);

  const donorsQuery = useQuery({
    queryKey: queryKeys.donors.list({ page_size: 100, sort: "full_name" }),
    queryFn: ({ signal }) =>
      client.donors.list({ page: 1, page_size: 100, sort: "full_name" }, { signal }),
  });
  const sectionsQuery = useQuery({
    queryKey: queryKeys.sections.list({ page_size: 100, sort: "name" }),
    queryFn: ({ signal }) =>
      client.sections.list({ page: 1, page_size: 100, sort: "name" }, { signal }),
  });
  const palmQuery = useQuery({
    queryKey: queryKeys.palms.detail(id),
    queryFn: ({ signal }) => client.palms.get(id, { signal }),
    enabled: mode === "edit" && Boolean(id),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      code: "",
      donor_id: "",
      section_id: "",
      plantation_date: null,
      status: "active",
      current_health_status: null,
      description: null,
    },
  });

  useEffect(() => {
    if (palmQuery.data) {
      reset({
        code: palmQuery.data.code,
        donor_id: palmQuery.data.donor_id,
        section_id: palmQuery.data.section_id,
        plantation_date: palmQuery.data.plantation_date,
        status: palmQuery.data.status,
        current_health_status: palmQuery.data.current_health_status,
        description: palmQuery.data.description,
      });
    }
  }, [palmQuery.data, reset]);

  const createMutation = useMutation({
    mutationFn: (input: PalmCreateRequest) => client.palms.create(input),
    onSuccess: async (palm) => {
      show("Palm created.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.palms.all });
      navigate(`/palms/${palm.id}`);
    },
  });

  const updateMutation = useMutation({
    mutationFn: (input: PalmPatchRequest) => client.palms.update(id, input),
    onSuccess: async (palm) => {
      show("Palm updated.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.palms.all });
      await queryClient.invalidateQueries({ queryKey: queryKeys.palms.detail(id) });
      navigate(`/palms/${palm.id}`);
    },
  });

  if (mode === "edit" && palmQuery.isLoading) {
    return <LoadingState label="Loading palm" />;
  }
  if (mode === "edit" && (palmQuery.isError || !palmQuery.data)) {
    return (
      <ErrorState
        description={getErrorMessage(palmQuery.error)}
        onRetry={() => palmQuery.refetch()}
      />
    );
  }

  const mutationError = createMutation.error ?? updateMutation.error;

  return (
    <Box>
      <PageHeader
        title={mode === "create" ? "New palm" : `Edit ${palmQuery.data?.code ?? "palm"}`}
        crumbs={[
          { label: "Palms", to: "/palms" },
          { label: mode === "create" ? "New" : "Edit" },
        ]}
      />
      <Box
        component="form"
        noValidate
        onSubmit={handleSubmit(async (values) => {
          const payload = {
            ...values,
            plantation_date: values.plantation_date || null,
            current_health_status: values.current_health_status || null,
            description: values.description || null,
          };
          if (mode === "create") {
            await createMutation.mutateAsync(payload);
          } else {
            await updateMutation.mutateAsync(payload);
          }
        })}
        sx={{ maxWidth: 720 }}
      >
        <Stack spacing={2}>
          {mutationError ? (
            <Alert severity="error">{getErrorMessage(mutationError)}</Alert>
          ) : null}
          <TextField
            label="Code"
            required
            fullWidth
            error={Boolean(errors.code)}
            helperText={errors.code?.message}
            {...register("code")}
          />
          <TextField
            label="Donor"
            select
            required
            fullWidth
            error={Boolean(errors.donor_id)}
            helperText={errors.donor_id?.message}
            defaultValue=""
            {...register("donor_id")}
          >
            {(donorsQuery.data?.items ?? []).map((donor) => (
              <MenuItem key={donor.id} value={donor.id}>
                {donor.full_name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Section"
            select
            required
            fullWidth
            error={Boolean(errors.section_id)}
            helperText={errors.section_id?.message}
            defaultValue=""
            {...register("section_id")}
          >
            {(sectionsQuery.data?.items ?? []).map((section) => (
              <MenuItem key={section.id} value={section.id}>
                {section.name}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Plantation date"
            type="date"
            fullWidth
            InputLabelProps={{ shrink: true }}
            {...register("plantation_date")}
          />
          <TextField
            label="Status"
            select
            fullWidth
            defaultValue="active"
            {...register("status")}
          >
            <MenuItem value="active">Active</MenuItem>
            <MenuItem value="inactive">Inactive</MenuItem>
          </TextField>
          <TextField
            label="Health status"
            fullWidth
            {...register("current_health_status")}
          />
          <TextField
            label="Description"
            fullWidth
            multiline
            minRows={3}
            {...register("description")}
          />
          <Stack direction="row" spacing={1}>
            <Button
              type="submit"
              variant="contained"
              disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
            >
              {mode === "create" ? "Create palm" : "Save changes"}
            </Button>
            <Button onClick={() => navigate(-1)}>Cancel</Button>
          </Stack>
        </Stack>
      </Box>
    </Box>
  );
}

export function PalmCreatePage() {
  return <PalmFormPage mode="create" />;
}

export function PalmEditPage() {
  return <PalmFormPage mode="edit" />;
}
