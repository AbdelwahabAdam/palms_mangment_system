import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Card,
  CardContent,
  Grid,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Link as RouterLink } from "react-router-dom";
import { Button } from "@mui/material";
import { queryKeys } from "@palms/shared";

import { useApiClient } from "@/api/ApiClientProvider";
import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS } from "@/auth/permissions";
import { ErrorState, LoadingState } from "@/components/ErrorState";
import { PageHeader } from "@/components/PageHeader";
import { formatDate, formatMoney, formatNumber, formatRelative } from "@/utils/format";
import { getErrorMessage } from "@/utils/errors";

export function OverviewPage() {
  const client = useApiClient();
  const { can } = useAuth();
  const overviewQuery = useQuery({
    queryKey: queryKeys.dashboard.overview,
    queryFn: ({ signal }) => client.dashboard.overview({ signal }),
  });

  if (overviewQuery.isLoading) return <LoadingState label="Loading overview" />;
  if (overviewQuery.isError || !overviewQuery.data) {
    return (
      <ErrorState
        title="Could not load overview"
        description={getErrorMessage(overviewQuery.error)}
        onRetry={() => overviewQuery.refetch()}
      />
    );
  }

  const data = overviewQuery.data;
  const chartData = [
    { name: "Active", value: data.totals.active_palms },
    { name: "Inactive", value: data.totals.inactive_palms },
  ];

  return (
    <Box>
      <PageHeader
        title="Overview"
        description="Operational snapshot of palms, donors, and recent activity."
        actions={
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            {can(PERMISSIONS.palmsCreate) ? (
              <Button component={RouterLink} to="/palms/new" variant="contained">
                New palm
              </Button>
            ) : null}
            {can(PERMISSIONS.donorsCreate) ? (
              <Button component={RouterLink} to="/donors/new" variant="outlined">
                New donor
              </Button>
            ) : null}
            {can(PERMISSIONS.reportsGenerate) ? (
              <Button component={RouterLink} to="/reports" variant="outlined">
                Reports
              </Button>
            ) : null}
          </Stack>
        }
      />

      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: "Palms", value: formatNumber(data.totals.palms) },
          { label: "Donors", value: formatNumber(data.totals.donors) },
          { label: "Sections", value: formatNumber(data.totals.sections) },
          { label: "Revenue", value: formatMoney(data.totals.revenue) },
        ].map((item) => (
          <Grid key={item.label} size={{ xs: 12, sm: 6, md: 3 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography color="text.secondary" variant="body2">
                  {item.label}
                </Typography>
                <Typography variant="h4">{item.value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Palm status
              </Typography>
              <Box sx={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#1b5e4a" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined" sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent harvests
              </Typography>
              <List dense>
                {data.recent_harvests.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="No recent harvests" />
                  </ListItem>
                ) : (
                  data.recent_harvests.map((harvest) => (
                    <ListItem
                      key={harvest.id}
                      component={RouterLink}
                      to={`/palms/${harvest.palm_id}`}
                      sx={{ color: "inherit", textDecoration: "none" }}
                    >
                      <ListItemText
                        primary={`${formatNumber(harvest.amount)} ${harvest.unit}`}
                        secondary={`${formatDate(harvest.harvest_date)} · ${formatMoney(harvest.revenue)}`}
                      />
                    </ListItem>
                  ))
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Recent activity
              </Typography>
              <List dense>
                {data.activity.map((item) => (
                  <ListItem key={item.id}>
                    <ListItemText
                      primary={item.message ?? item.action}
                      secondary={`${item.entity_type} · ${formatRelative(item.created_at)}`}
                    />
                  </ListItem>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Upcoming reports
              </Typography>
              <List dense>
                {data.upcoming_reports.length === 0 ? (
                  <ListItem>
                    <ListItemText primary="No upcoming scheduled reports" />
                  </ListItem>
                ) : (
                  data.upcoming_reports.map((item) => (
                    <ListItem
                      key={item.id}
                      component={RouterLink}
                      to={`/report-schedules/${item.id}`}
                      sx={{ color: "inherit", textDecoration: "none" }}
                    >
                      <ListItemText
                        primary={item.name}
                        secondary={`${item.format.toUpperCase()} · ${formatRelative(item.next_run_at)}`}
                      />
                    </ListItem>
                  ))
                )}
              </List>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
