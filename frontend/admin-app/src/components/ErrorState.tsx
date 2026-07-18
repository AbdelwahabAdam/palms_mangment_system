import { Box, Button, Stack, Typography } from "@mui/material";

interface ErrorStateProps {
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Something went wrong",
  description = "Please try again.",
  onRetry,
}: ErrorStateProps) {
  return (
    <Stack
      role="alert"
      spacing={1.5}
      alignItems="flex-start"
      sx={{ py: 4 }}
    >
      <Typography variant="h6">{title}</Typography>
      <Typography color="text.secondary">{description}</Typography>
      {onRetry ? (
        <Button variant="outlined" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </Stack>
  );
}

interface EmptyStateProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <Box
      sx={{
        py: 6,
        px: 2,
        textAlign: "center",
        border: "1px dashed",
        borderColor: "divider",
        borderRadius: 2,
        bgcolor: "background.paper",
      }}
    >
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      {description ? (
        <Typography color="text.secondary" sx={{ mb: action ? 2 : 0 }}>
          {description}
        </Typography>
      ) : null}
      {action}
    </Box>
  );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <Box
      role="status"
      aria-live="polite"
      aria-label={label}
      sx={{ py: 8, display: "grid", placeItems: "center" }}
    >
      <Box
        sx={{
          width: 36,
          height: 36,
          borderRadius: "50%",
          border: "3px solid",
          borderColor: "primary.light",
          borderTopColor: "primary.main",
          animation: "spin 0.8s linear infinite",
          "@keyframes spin": {
            to: { transform: "rotate(360deg)" },
          },
        }}
      />
    </Box>
  );
}
