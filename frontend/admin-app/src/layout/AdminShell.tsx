import { Box, Toolbar } from "@mui/material";
import { Outlet } from "react-router-dom";

import { Header } from "@/layout/Header";
import { Sidebar, DRAWER_WIDTH } from "@/layout/Sidebar";
import { useUiStore } from "@/stores/uiStore";

export function AdminShell() {
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", bgcolor: "background.default" }}>
      <Header />
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : "100%" },
          p: { xs: 2, md: 3 },
          transition: (theme) =>
            theme.transitions.create("width", {
              easing: theme.transitions.easing.sharp,
              duration: theme.transitions.duration.leavingScreen,
            }),
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
