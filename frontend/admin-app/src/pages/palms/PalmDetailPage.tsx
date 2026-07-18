import { useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid,
  IconButton,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import { queryKeys } from "@palms/shared";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { FileDropzone } from "@/components/FileDropzone";
import { PageHeader } from "@/components/PageHeader";
import { useSnackbarStore } from "@/stores/uiStore";
import { formatDate, formatDateTime, formatMoney, formatNumber } from "@/utils/format";
import { getErrorMessage } from "@/utils/errors";

export function PalmDetailPage() {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const [tab, setTab] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const palmQuery = useQuery({
    queryKey: queryKeys.palms.detail(id),
    queryFn: ({ signal }) => client.palms.get(id, { signal }),
    enabled: Boolean(id),
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.palms.detail(id) });
    await queryClient.invalidateQueries({ queryKey: queryKeys.palms.all });
  };

  const deleteMutation = useMutation({
    mutationFn: () => client.palms.remove(id),
    onSuccess: async () => {
      show("Palm deleted.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.palms.all });
      navigate("/palms");
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) =>
      client.palms.uploadImage(id, { file, filename: file.name }),
    onSuccess: async () => {
      show("Image uploaded.", "success");
      await invalidate();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const removeImage = useMutation({
    mutationFn: (imageId: string) => client.palms.removeImage(id, imageId),
    onSuccess: async () => {
      show("Image removed.", "success");
      await invalidate();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  if (palmQuery.isLoading) return <LoadingState label="Loading palm" />;
  if (palmQuery.isError || !palmQuery.data) {
    return (
      <ErrorState
        description={getErrorMessage(palmQuery.error)}
        onRetry={() => palmQuery.refetch()}
      />
    );
  }

  const palm = palmQuery.data;

  return (
    <Box>
      <PageHeader
        title={palm.code}
        description={palm.description ?? "Palm detail and related records."}
        crumbs={[
          { label: "Palms", to: "/palms" },
          { label: palm.code },
        ]}
        actions={
          <>
            {can(PERMISSIONS.palmsUpdate) ? (
              <Button component={RouterLink} to={`/palms/${id}/edit`} variant="contained">
                Edit
              </Button>
            ) : null}
            {can(PERMISSIONS.palmsDelete) ? (
              <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
                Delete
              </Button>
            ) : null}
          </>
        }
      />

      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid size={{ xs: 12, md: 8 }}>
          <Card variant="outlined">
            <CardContent>
              <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
                <Chip label={palm.status} color={palm.status === "active" ? "success" : "default"} />
                {palm.current_health_status ? (
                  <Chip label={palm.current_health_status} variant="outlined" />
                ) : null}
              </Stack>
              <Grid container spacing={2}>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="body2" color="text.secondary">
                    Donor
                  </Typography>
                  <Typography>
                    {palm.donor ? (
                      <Button component={RouterLink} to={`/donors/${palm.donor.id}`} size="small">
                        {palm.donor.full_name}
                      </Button>
                    ) : (
                      "—"
                    )}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="body2" color="text.secondary">
                    Section
                  </Typography>
                  <Typography>
                    {palm.section ? (
                      <Button component={RouterLink} to={`/sections/${palm.section.id}`} size="small">
                        {palm.section.name}
                      </Button>
                    ) : (
                      "—"
                    )}
                  </Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="body2" color="text.secondary">
                    Plantation date
                  </Typography>
                  <Typography>{formatDate(palm.plantation_date)}</Typography>
                </Grid>
                <Grid size={{ xs: 12, sm: 6 }}>
                  <Typography variant="body2" color="text.secondary">
                    Updated
                  </Typography>
                  <Typography>{formatDateTime(palm.updated_at)}</Typography>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Images
              </Typography>
              {can(PERMISSIONS.palmsUpdate) ? (
                <Box sx={{ mb: 2 }}>
                  <FileDropzone
                    onFile={(file) => uploadMutation.mutate(file)}
                    disabled={uploadMutation.isPending}
                  />
                </Box>
              ) : null}
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                {palm.images.map((image) => (
                  <Box key={image.id} sx={{ position: "relative" }}>
                    <Box
                      component="img"
                      src={image.thumbnail_url}
                      alt={`Palm ${palm.code}`}
                      sx={{ width: 88, height: 88, objectFit: "cover", borderRadius: 1 }}
                    />
                    {can(PERMISSIONS.palmsUpdate) ? (
                      <IconButton
                        size="small"
                        aria-label="Delete image"
                        onClick={() => removeImage.mutate(image.id)}
                        sx={{ position: "absolute", top: 0, right: 0, bgcolor: "background.paper" }}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    ) : null}
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Tabs value={tab} onChange={(_, value: number) => setTab(value)} sx={{ mb: 2 }}>
        <Tab label={`Harvests (${palm.harvests.length})`} />
        <Tab label={`Diseases (${palm.diseases.length})`} />
        <Tab label={`Notes (${palm.notes.length})`} />
        <Tab label={`Children (${palm.children.length})`} />
      </Tabs>

      {tab === 0 ? (
        <HarvestPanel palmId={id} canEdit={can(PERMISSIONS.palmsUpdate)} onChanged={invalidate} harvests={palm.harvests} />
      ) : null}
      {tab === 1 ? (
        <DiseasePanel palmId={id} canEdit={can(PERMISSIONS.palmsUpdate)} onChanged={invalidate} diseases={palm.diseases} />
      ) : null}
      {tab === 2 ? (
        <NotesPanel palmId={id} canEdit={can(PERMISSIONS.palmsUpdate)} onChanged={invalidate} notes={palm.notes} />
      ) : null}
      {tab === 3 ? (
        <Stack spacing={1}>
          {palm.children.length === 0 ? (
            <Typography color="text.secondary">No child palms linked.</Typography>
          ) : (
            palm.children.map((child) => (
              <Typography key={child.id}>
                {child.child_palm ? (
                  <Button component={RouterLink} to={`/palms/${child.child_palm.id}`}>
                    {child.child_palm.code}
                  </Button>
                ) : (
                  child.relationship_type
                )}{" "}
                · {child.relationship_type}
              </Typography>
            ))
          )}
        </Stack>
      ) : null}

      <ConfirmDialog
        open={confirmDelete}
        title="Delete this palm?"
        description="This action cannot be undone."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
    </Box>
  );
}

function HarvestPanel({
  palmId,
  harvests,
  canEdit,
  onChanged,
}: {
  palmId: string;
  harvests: Array<{
    id: string;
    harvest_date: string;
    amount: string;
    unit: string;
    revenue: string | null;
    notes: string | null;
  }>;
  canEdit: boolean;
  onChanged: () => Promise<void>;
}) {
  const client = useApiClient();
  const show = useSnackbarStore((s) => s.show);
  const [form, setForm] = useState({
    harvest_date: "",
    amount: "",
    unit: "kg",
    revenue: "",
    notes: "",
  });

  const create = useMutation({
    mutationFn: () =>
      client.palms.createHarvest(palmId, {
        harvest_date: form.harvest_date,
        amount: form.amount,
        unit: form.unit,
        revenue: form.revenue || null,
        notes: form.notes || null,
      }),
    onSuccess: async () => {
      show("Harvest added.", "success");
      setForm({ harvest_date: "", amount: "", unit: "kg", revenue: "", notes: "" });
      await onChanged();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const remove = useMutation({
    mutationFn: (harvestId: string) => client.palms.removeHarvest(palmId, harvestId),
    onSuccess: async () => {
      show("Harvest removed.", "success");
      await onChanged();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  return (
    <Stack spacing={2}>
      {canEdit ? (
        <Card variant="outlined">
          <CardContent>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1} useFlexGap flexWrap="wrap">
              <TextField
                label="Date"
                type="date"
                size="small"
                InputLabelProps={{ shrink: true }}
                value={form.harvest_date}
                onChange={(e) => setForm((f) => ({ ...f, harvest_date: e.target.value }))}
              />
              <TextField
                label="Amount"
                size="small"
                value={form.amount}
                onChange={(e) => setForm((f) => ({ ...f, amount: e.target.value }))}
              />
              <TextField
                label="Unit"
                size="small"
                value={form.unit}
                onChange={(e) => setForm((f) => ({ ...f, unit: e.target.value }))}
              />
              <TextField
                label="Revenue"
                size="small"
                value={form.revenue}
                onChange={(e) => setForm((f) => ({ ...f, revenue: e.target.value }))}
              />
              <Button
                variant="contained"
                onClick={() => create.mutate()}
                disabled={create.isPending || !form.harvest_date || !form.amount}
              >
                Add harvest
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : null}
      {harvests.map((item) => (
        <Card key={item.id} variant="outlined">
          <CardContent sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
            <Box>
              <Typography fontWeight={600}>
                {formatNumber(item.amount)} {item.unit} · {formatMoney(item.revenue)}
              </Typography>
              <Typography color="text.secondary">{formatDate(item.harvest_date)}</Typography>
              {item.notes ? <Typography variant="body2">{item.notes}</Typography> : null}
            </Box>
            {canEdit ? (
              <IconButton aria-label="Delete harvest" onClick={() => remove.mutate(item.id)}>
                <DeleteOutlineIcon />
              </IconButton>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

function DiseasePanel({
  palmId,
  diseases,
  canEdit,
  onChanged,
}: {
  palmId: string;
  diseases: Array<{
    id: string;
    disease_name: string;
    detected_at: string;
    status: string;
    notes: string | null;
  }>;
  canEdit: boolean;
  onChanged: () => Promise<void>;
}) {
  const client = useApiClient();
  const show = useSnackbarStore((s) => s.show);
  const [form, setForm] = useState({
    disease_name: "",
    detected_at: "",
    status: "active",
    notes: "",
  });

  const create = useMutation({
    mutationFn: () =>
      client.palms.createDisease(palmId, {
        disease_name: form.disease_name,
        detected_at: form.detected_at,
        status: form.status,
        notes: form.notes || null,
      }),
    onSuccess: async () => {
      show("Disease record added.", "success");
      setForm({ disease_name: "", detected_at: "", status: "active", notes: "" });
      await onChanged();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const remove = useMutation({
    mutationFn: (diseaseId: string) => client.palms.removeDisease(palmId, diseaseId),
    onSuccess: async () => {
      show("Disease record removed.", "success");
      await onChanged();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  return (
    <Stack spacing={2}>
      {canEdit ? (
        <Card variant="outlined">
          <CardContent>
            <Stack direction={{ xs: "column", md: "row" }} spacing={1} useFlexGap flexWrap="wrap">
              <TextField
                label="Disease"
                size="small"
                value={form.disease_name}
                onChange={(e) => setForm((f) => ({ ...f, disease_name: e.target.value }))}
              />
              <TextField
                label="Detected"
                type="date"
                size="small"
                InputLabelProps={{ shrink: true }}
                value={form.detected_at}
                onChange={(e) => setForm((f) => ({ ...f, detected_at: e.target.value }))}
              />
              <TextField
                label="Status"
                size="small"
                value={form.status}
                onChange={(e) => setForm((f) => ({ ...f, status: e.target.value }))}
              />
              <Button
                variant="contained"
                onClick={() => create.mutate()}
                disabled={create.isPending || !form.disease_name || !form.detected_at}
              >
                Add disease
              </Button>
            </Stack>
          </CardContent>
        </Card>
      ) : null}
      {diseases.map((item) => (
        <Card key={item.id} variant="outlined">
          <CardContent sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
            <Box>
              <Typography fontWeight={600}>{item.disease_name}</Typography>
              <Typography color="text.secondary">
                {formatDate(item.detected_at)} · {item.status}
              </Typography>
              {item.notes ? <Typography variant="body2">{item.notes}</Typography> : null}
            </Box>
            {canEdit ? (
              <IconButton aria-label="Delete disease" onClick={() => remove.mutate(item.id)}>
                <DeleteOutlineIcon />
              </IconButton>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

function NotesPanel({
  palmId,
  notes,
  canEdit,
  onChanged,
}: {
  palmId: string;
  notes: Array<{ id: string; body: string; created_at: string }>;
  canEdit: boolean;
  onChanged: () => Promise<void>;
}) {
  const client = useApiClient();
  const show = useSnackbarStore((s) => s.show);
  const [body, setBody] = useState("");

  const create = useMutation({
    mutationFn: () => client.palms.createNote(palmId, { body }),
    onSuccess: async () => {
      show("Note added.", "success");
      setBody("");
      await onChanged();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const remove = useMutation({
    mutationFn: (noteId: string) => client.palms.removeNote(palmId, noteId),
    onSuccess: async () => {
      show("Note removed.", "success");
      await onChanged();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  return (
    <Stack spacing={2}>
      {canEdit ? (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <TextField
            label="Note"
            fullWidth
            multiline
            minRows={2}
            value={body}
            onChange={(e) => setBody(e.target.value)}
          />
          <Button
            variant="contained"
            onClick={() => create.mutate()}
            disabled={!body.trim() || create.isPending}
          >
            Add note
          </Button>
        </Stack>
      ) : null}
      {notes.map((note) => (
        <Card key={note.id} variant="outlined">
          <CardContent sx={{ display: "flex", justifyContent: "space-between", gap: 2 }}>
            <Box>
              <Typography>{note.body}</Typography>
              <Typography variant="caption" color="text.secondary">
                {formatDateTime(note.created_at)}
              </Typography>
            </Box>
            {canEdit ? (
              <IconButton aria-label="Delete note" onClick={() => remove.mutate(note.id)}>
                <DeleteOutlineIcon />
              </IconButton>
            ) : null}
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}
