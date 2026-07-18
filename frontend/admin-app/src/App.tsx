import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CssBaseline, ThemeProvider } from "@mui/material";

import { ApiClientProvider } from "@/api/ApiClientProvider";
import { AppSnackbar } from "@/components/AppSnackbar";
import { AppRoutes } from "@/routes";
import { theme } from "@/theme";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <BrowserRouter basename="/admin">
          <ApiClientProvider>
            <AppRoutes />
            <AppSnackbar />
          </ApiClientProvider>
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
