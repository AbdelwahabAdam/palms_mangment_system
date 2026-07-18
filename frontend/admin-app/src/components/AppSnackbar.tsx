import { Alert, Snackbar } from "@mui/material";

import { useSnackbarStore } from "@/stores/uiStore";

export function AppSnackbar() {
  const { open, message, severity, close } = useSnackbarStore();

  return (
    <Snackbar
      open={open}
      autoHideDuration={4500}
      onClose={close}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
    >
      <Alert
        onClose={close}
        severity={severity}
        variant="filled"
        sx={{ width: "100%" }}
        role="status"
      >
        {message}
      </Alert>
    </Snackbar>
  );
}
