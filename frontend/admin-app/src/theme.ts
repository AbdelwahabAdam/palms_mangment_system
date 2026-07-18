import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#1b5e4a",
      light: "#2e7d64",
      dark: "#0f3d30",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#c47a2c",
      light: "#d99752",
      dark: "#8f5418",
    },
    background: {
      default: "#f4f7f5",
      paper: "#ffffff",
    },
    divider: "rgba(27, 94, 74, 0.12)",
  },
  typography: {
    fontFamily: '"IBM Plex Sans", "Segoe UI", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 650 },
    h6: { fontWeight: 600 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: "1px solid rgba(27, 94, 74, 0.12)",
        },
      },
    },
  },
});
