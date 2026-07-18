import { Breadcrumbs, Button, Link as MuiLink, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

export interface Crumb {
  label: string;
  to?: string;
}

interface PageHeaderProps {
  title: string;
  description?: string;
  crumbs?: Crumb[];
  actions?: React.ReactNode;
}

export function PageHeader({
  title,
  description,
  crumbs,
  actions,
}: PageHeaderProps) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "stretch", sm: "flex-start" }}
      spacing={2}
      sx={{ mb: 3 }}
    >
      <Stack spacing={0.75}>
        {crumbs?.length ? (
          <Breadcrumbs aria-label="Breadcrumb">
            {crumbs.map((crumb) =>
              crumb.to ? (
                <MuiLink
                  key={crumb.label}
                  component={RouterLink}
                  to={crumb.to}
                  underline="hover"
                  color="inherit"
                >
                  {crumb.label}
                </MuiLink>
              ) : (
                <Typography key={crumb.label} color="text.primary">
                  {crumb.label}
                </Typography>
              ),
            )}
          </Breadcrumbs>
        ) : null}
        <Typography variant="h4" component="h1">
          {title}
        </Typography>
        {description ? (
          <Typography color="text.secondary">{description}</Typography>
        ) : null}
      </Stack>
      {actions ? (
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          {actions}
        </Stack>
      ) : null}
    </Stack>
  );
}

export function PrimaryAction({
  to,
  label,
  onClick,
}: {
  to?: string;
  label: string;
  onClick?: () => void;
}) {
  if (to) {
    return (
      <Button component={RouterLink} to={to} variant="contained">
        {label}
      </Button>
    );
  }
  return (
    <Button variant="contained" onClick={onClick}>
      {label}
    </Button>
  );
}
