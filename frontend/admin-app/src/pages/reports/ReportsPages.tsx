import { useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  Chip,
  FormControlLabel,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import {
  openReportDownloads,
  queryKeys,
  ReportScheduleCreateRequestSchema,
  ReportTemplateCreateRequestSchema,
  type ReportSchedule,
  type ReportScheduleCreateRequest,
} from "@palms/shared";
import { z } from "zod";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { PageHeader, PrimaryAction } from "@/components/PageHeader";
import { useSnackbarStore } from "@/stores/uiStore";
import { formatDateTime, formatRelative } from "@/utils/format";
import { getErrorMessage } from "@/utils/errors";

export function ReportsPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const show = useSnackbarStore((s) => s.show);
  const [reportType, setReportType] = useState<"palms" | "donors" | "sections">("palms");
  const [fields, setFields] = useState<string[]>([]);
  const [format, setFormat] = useState<"csv" | "pdf">("csv");
  const [templateName, setTemplateName] = useState("");

  const typesQuery = useQuery({
    queryKey: queryKeys.reports.types,
    queryFn: ({ signal }) => client.reports.types({ signal }),
  });

  const selectedType = typesQuery.data?.items.find((item) => item.code === reportType);

  const previewMutation = useMutation({
    mutationFn: () =>
      client.reports.preview({
        report_type: reportType,
        fields: fields.length ? fields : null,
        filters: null,
      }),
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      client.reports.generate({
        report_type: reportType,
        fields: fields.length ? fields : null,
        filters: null,
        format,
      }),
    onSuccess: (run) => {
      show(`Report ${run.status}.`, "success");
      if (run.download_urls?.length) {
        for (const url of run.download_urls) {
          window.open(url, "_blank", "noopener,noreferrer");
        }
      }
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  const templateMutation = useMutation({
    mutationFn: () =>
      client.reports.createTemplate(
        ReportTemplateCreateRequestSchema.parse({
          name: templateName,
          report_type: reportType,
          fields: fields.length ? fields : selectedType?.fields.slice(0, 5) ?? ["id"],
          filters: null,
        }),
      ),
    onSuccess: async () => {
      show("Template saved.", "success");
      setTemplateName("");
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  if (typesQuery.isLoading) return <LoadingState />;
  if (typesQuery.isError || !typesQuery.data) {
    return <ErrorState description={getErrorMessage(typesQuery.error)} onRetry={() => typesQuery.refetch()} />;
  }

  return (
    <Box>
      <PageHeader
        title="Reports"
        description="Preview, generate, and save report templates."
        actions={
          <Button component={RouterLink} to="/reports/templates" variant="outlined">
            Templates
          </Button>
        }
      />
      <Stack spacing={2} sx={{ maxWidth: 960 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <TextField
            label="Report type"
            select
            value={reportType}
            onChange={(event) => {
              setReportType(event.target.value as typeof reportType);
              setFields([]);
            }}
            sx={{ minWidth: 200 }}
          >
            {typesQuery.data.items.map((item) => (
              <MenuItem key={item.code} value={item.code}>
                {item.code}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Format"
            select
            value={format}
            onChange={(event) => setFormat(event.target.value as "csv" | "pdf")}
            sx={{ minWidth: 140 }}
          >
            {(selectedType?.formats ?? ["csv", "pdf"]).map((item) => (
              <MenuItem key={item} value={item}>
                {item.toUpperCase()}
              </MenuItem>
            ))}
          </TextField>
        </Stack>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle1" gutterBottom>
              Fields
            </Typography>
            <Stack direction="row" flexWrap="wrap" useFlexGap spacing={1}>
              {(selectedType?.fields ?? []).map((field) => {
                const checked = fields.includes(field);
                return (
                  <FormControlLabel
                    key={field}
                    control={
                      <Checkbox
                        checked={checked}
                        onChange={() =>
                          setFields((current) =>
                            checked
                              ? current.filter((item) => item !== field)
                              : [...current, field],
                          )
                        }
                      />
                    }
                    label={field}
                  />
                );
              })}
            </Stack>
          </CardContent>
        </Card>

        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {can(PERMISSIONS.reportsGenerate) ? (
            <>
              <Button variant="outlined" onClick={() => previewMutation.mutate()} disabled={previewMutation.isPending}>
                Preview
              </Button>
              <Button variant="contained" onClick={() => generateMutation.mutate()} disabled={generateMutation.isPending}>
                Generate {format.toUpperCase()}
              </Button>
            </>
          ) : null}
        </Stack>

        {can(PERMISSIONS.reportsGenerate) ? (
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <TextField
              label="Template name"
              size="small"
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
              sx={{ minWidth: 240 }}
            />
            <Button
              variant="outlined"
              disabled={!templateName.trim() || templateMutation.isPending}
              onClick={() => templateMutation.mutate()}
            >
              Save template
            </Button>
          </Stack>
        ) : null}

        {previewMutation.data ? (
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Preview ({previewMutation.data.total}
                {previewMutation.data.truncated ? ", truncated" : ""})
              </Typography>
              <Box sx={{ overflowX: "auto" }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      {previewMutation.data.fields.map((field) => (
                        <TableCell key={field}>{field}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {previewMutation.data.items.slice(0, 25).map((row, index) => (
                      <TableRow key={index}>
                        {previewMutation.data.fields.map((field) => (
                          <TableCell key={field}>
                            {row[field] === null || row[field] === undefined
                              ? "—"
                              : String(row[field])}
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Box>
            </CardContent>
          </Card>
        ) : null}
      </Stack>
    </Box>
  );
}

export function ReportTemplatesPage() {
  const client = useApiClient();
  const templatesQuery = useQuery({
    queryKey: queryKeys.reports.templates,
    queryFn: ({ signal }) => client.reports.listTemplates({ signal }),
  });

  if (templatesQuery.isLoading) return <LoadingState />;
  if (templatesQuery.isError || !templatesQuery.data) {
    return <ErrorState description={getErrorMessage(templatesQuery.error)} onRetry={() => templatesQuery.refetch()} />;
  }

  return (
    <Box>
      <PageHeader
        title="Report templates"
        crumbs={[{ label: "Reports", to: "/reports" }, { label: "Templates" }]}
      />
      <Stack spacing={1.5}>
        {templatesQuery.data.items.length === 0 ? (
          <Typography color="text.secondary">No saved templates yet.</Typography>
        ) : (
          templatesQuery.data.items.map((template) => (
            <Card key={template.id} variant="outlined">
              <CardContent>
                <Typography variant="h6">{template.name}</Typography>
                <Stack direction="row" spacing={1} sx={{ my: 1 }} flexWrap="wrap" useFlexGap>
                  <Chip label={template.report_type} size="small" />
                  {template.fields.map((field) => (
                    <Chip key={field} label={field} size="small" variant="outlined" />
                  ))}
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  Created {formatDateTime(template.created_at)}
                </Typography>
              </CardContent>
            </Card>
          ))
        )}
      </Stack>
    </Box>
  );
}

export function ReportSchedulesListPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const schedulesQuery = useQuery({
    queryKey: queryKeys.reports.schedules,
    queryFn: ({ signal }) => client.reports.listSchedules({ signal }),
  });

  if (schedulesQuery.isLoading) return <LoadingState />;
  if (schedulesQuery.isError || !schedulesQuery.data) {
    return <ErrorState description={getErrorMessage(schedulesQuery.error)} onRetry={() => schedulesQuery.refetch()} />;
  }

  return (
    <Box>
      <PageHeader
        title="Report schedules"
        description="Automated report delivery schedules."
        actions={
          can(PERMISSIONS.reportsSchedule) ? (
            <PrimaryAction to="/report-schedules/new" label="New schedule" />
          ) : null
        }
      />
      <Stack spacing={1.5}>
        {schedulesQuery.data.items.map((schedule) => (
          <Card key={schedule.id} variant="outlined">
            <CardContent sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
              <Box>
                <Button component={RouterLink} to={`/report-schedules/${schedule.id}`} sx={{ px: 0 }}>
                  {schedule.name}
                </Button>
                <Typography color="text.secondary">
                  {schedule.report_type} · {schedule.frequency} · {schedule.format.toUpperCase()}
                </Typography>
                <Typography variant="body2">
                  Next run: {formatRelative(schedule.next_run_at)} ·{" "}
                  {schedule.enabled ? "Enabled" : "Paused"}
                </Typography>
              </Box>
              <Chip
                label={schedule.enabled ? "Active" : "Paused"}
                color={schedule.enabled ? "success" : "default"}
                size="small"
              />
            </CardContent>
          </Card>
        ))}
        {schedulesQuery.data.items.length === 0 ? (
          <Typography color="text.secondary">No schedules configured.</Typography>
        ) : null}
      </Stack>
    </Box>
  );
}

const ScheduleFormSchema = ReportScheduleCreateRequestSchema;
type ScheduleFormValues = z.infer<typeof ScheduleFormSchema>;

export function ReportScheduleFormPage() {
  const client = useApiClient();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const typesQuery = useQuery({
    queryKey: queryKeys.reports.types,
    queryFn: ({ signal }) => client.reports.types({ signal }),
  });

  const {
    register,
    control,
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
  } = useForm<ScheduleFormValues>({
    defaultValues: {
      name: "",
      report_type: "palms",
      frequency: "weekly",
      timezone: "Africa/Cairo",
      format: "csv",
      recipients: ["admin@example.com"],
      run_time: "08:00",
      enabled: true,
      include_summary: true,
      attach_file: true,
      fields: null,
      filters: null,
      cron_expression: null,
      day_of_month: null,
      weekday: 1,
      email_subject: null,
      template_id: null,
    },
  });

  const [recipientsDraft, setRecipientsDraft] = useState("");

  const createMutation = useMutation({
    mutationFn: (input: ReportScheduleCreateRequest) =>
      client.reports.createSchedule(input),
    onSuccess: async (schedule) => {
      show("Schedule created.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.reports.schedules });
      navigate(`/report-schedules/${schedule.id}`);
    },
  });

  return (
    <Box>
      <PageHeader
        title="New report schedule"
        crumbs={[
          { label: "Schedules", to: "/report-schedules" },
          { label: "New" },
        ]}
      />
      <Box
        component="form"
        noValidate
        sx={{ maxWidth: 720 }}
        onSubmit={handleSubmit(async (values) => {
          const recipients = recipientsDraft
            .split(/[,;\s]+/)
            .map((item) => item.trim())
            .filter(Boolean);
          const parsed = ScheduleFormSchema.safeParse({ ...values, recipients });
          if (!parsed.success) {
            const issue = parsed.error.issues[0];
            setError("recipients", {
              message: issue?.message ?? "Invalid schedule.",
            });
            return;
          }
          await createMutation.mutateAsync(parsed.data);
        })}
      >
        <Stack spacing={2}>
          {createMutation.isError ? (
            <Alert severity="error">{getErrorMessage(createMutation.error)}</Alert>
          ) : null}
          <TextField label="Name" required fullWidth error={Boolean(errors.name)} helperText={errors.name?.message} {...register("name")} />
          <Controller
            name="report_type"
            control={control}
            render={({ field }) => (
              <TextField label="Report type" select fullWidth {...field}>
                {(typesQuery.data?.items ?? [{ code: "palms" }, { code: "donors" }, { code: "sections" }]).map((item) => (
                  <MenuItem key={item.code} value={item.code}>
                    {item.code}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
          <Controller
            name="frequency"
            control={control}
            render={({ field }) => (
              <TextField label="Frequency" select fullWidth {...field}>
                {["daily", "weekly", "monthly", "cron"].map((item) => (
                  <MenuItem key={item} value={item}>
                    {item}
                  </MenuItem>
                ))}
              </TextField>
            )}
          />
          <TextField label="Run time (HH:MM)" fullWidth {...register("run_time")} />
          <TextField label="Timezone" fullWidth {...register("timezone")} />
          <TextField label="Cron expression" fullWidth {...register("cron_expression")} />
          <Controller
            name="format"
            control={control}
            render={({ field }) => (
              <TextField label="Format" select fullWidth {...field}>
                <MenuItem value="csv">CSV</MenuItem>
                <MenuItem value="pdf">PDF</MenuItem>
              </TextField>
            )}
          />
          <TextField
            label="Recipients (comma-separated emails)"
            fullWidth
            value={recipientsDraft}
            onChange={(event) => setRecipientsDraft(event.target.value)}
            error={Boolean(errors.recipients)}
            helperText={errors.recipients?.message as string | undefined}
          />
          <TextField label="Email subject" fullWidth {...register("email_subject")} />
          <Button type="submit" variant="contained" disabled={isSubmitting || createMutation.isPending}>
            Create schedule
          </Button>
        </Stack>
      </Box>
    </Box>
  );
}

export function ReportScheduleDetailPage() {
  const { id = "" } = useParams();
  const client = useApiClient();
  const navigate = useNavigate();
  const { can } = useAuth();
  const queryClient = useQueryClient();
  const show = useSnackbarStore((s) => s.show);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const scheduleQuery = useQuery({
    queryKey: queryKeys.reports.schedule(id),
    queryFn: ({ signal }) => client.reports.getSchedule(id, { signal }),
    enabled: Boolean(id),
  });
  const runsQuery = useQuery({
    queryKey: queryKeys.reports.scheduleRuns(id, { page: 1, page_size: 20 }),
    queryFn: ({ signal }) =>
      client.reports.listScheduleRuns(id, { page: 1, page_size: 20 }, { signal }),
    enabled: Boolean(id),
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.reports.schedule(id) });
    await queryClient.invalidateQueries({ queryKey: queryKeys.reports.schedules });
  };

  const pauseMutation = useMutation({
    mutationFn: () => client.reports.pauseSchedule(id),
    onSuccess: async () => {
      show("Schedule paused.", "success");
      await invalidate();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });
  const resumeMutation = useMutation({
    mutationFn: () => client.reports.resumeSchedule(id),
    onSuccess: async () => {
      show("Schedule resumed.", "success");
      await invalidate();
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });
  const deleteMutation = useMutation({
    mutationFn: () => client.reports.removeSchedule(id),
    onSuccess: async () => {
      show("Schedule deleted.", "success");
      await queryClient.invalidateQueries({ queryKey: queryKeys.reports.schedules });
      navigate("/report-schedules");
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });
  const downloadMutation = useMutation({
    mutationFn: (runId: string) => client.reports.downloadRun(runId),
    onSuccess: (result) => {
      openReportDownloads(result.files, (url) =>
        window.open(url, "_blank", "noopener,noreferrer"),
      );
    },
    onError: (error) => show(getErrorMessage(error), "error"),
  });

  if (scheduleQuery.isLoading) return <LoadingState />;
  if (scheduleQuery.isError || !scheduleQuery.data) {
    return <ErrorState description={getErrorMessage(scheduleQuery.error)} onRetry={() => scheduleQuery.refetch()} />;
  }

  const schedule: ReportSchedule = scheduleQuery.data;

  return (
    <Box>
      <PageHeader
        title={schedule.name}
        crumbs={[
          { label: "Schedules", to: "/report-schedules" },
          { label: schedule.name },
        ]}
        actions={
          can(PERMISSIONS.reportsSchedule) ? (
            <>
              {schedule.enabled ? (
                <Button variant="outlined" onClick={() => pauseMutation.mutate()} disabled={pauseMutation.isPending}>
                  Pause
                </Button>
              ) : (
                <Button variant="outlined" onClick={() => resumeMutation.mutate()} disabled={resumeMutation.isPending}>
                  Resume
                </Button>
              )}
              <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
                Delete
              </Button>
            </>
          ) : null
        }
      />
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack spacing={1}>
            <Typography>Type: {schedule.report_type}</Typography>
            <Typography>Frequency: {schedule.frequency}</Typography>
            <Typography>Format: {schedule.format.toUpperCase()}</Typography>
            <Typography>Recipients: {schedule.recipients.join(", ")}</Typography>
            <Typography>Next run: {formatDateTime(schedule.next_run_at)}</Typography>
            <Typography>Last run: {formatDateTime(schedule.last_run_at)}</Typography>
            <Chip
              label={schedule.enabled ? "Enabled" : "Paused"}
              color={schedule.enabled ? "success" : "default"}
              size="small"
              sx={{ width: "fit-content" }}
            />
          </Stack>
        </CardContent>
      </Card>

      <Typography variant="h6" gutterBottom>
        Execution history
      </Typography>
      {runsQuery.isLoading ? (
        <LoadingState />
      ) : (
        <Stack spacing={1}>
          {(runsQuery.data?.items ?? []).map((run) => (
            <Card key={run.id} variant="outlined">
              <CardContent sx={{ display: "flex", justifyContent: "space-between", gap: 2, flexWrap: "wrap" }}>
                <Box>
                  <Typography fontWeight={600}>
                    {run.status} · {run.format.toUpperCase()}
                  </Typography>
                  <Typography color="text.secondary">
                    {formatDateTime(run.created_at)}
                    {run.error_message ? ` · ${run.error_message}` : ""}
                  </Typography>
                </Box>
                <Button
                  size="small"
                  variant="outlined"
                  disabled={downloadMutation.isPending}
                  onClick={() => downloadMutation.mutate(run.id)}
                >
                  Download
                </Button>
              </CardContent>
            </Card>
          ))}
          {(runsQuery.data?.items.length ?? 0) === 0 ? (
            <Typography color="text.secondary">No runs yet.</Typography>
          ) : null}
        </Stack>
      )}

      <ConfirmDialog
        open={confirmDelete}
        title="Delete schedule?"
        description="This removes the schedule and stops future runs."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => deleteMutation.mutate()}
      />
    </Box>
  );
}
