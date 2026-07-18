import { useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import {
  AppBar,
  Avatar,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Toolbar,
  Typography,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";

import { useAuth } from "@/auth/useAuth";
import { DRAWER_WIDTH } from "@/layout/Sidebar";
import { useUiStore } from "@/stores/uiStore";

export function Header() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);

  return (
    <AppBar
      position="fixed"
      color="inherit"
      elevation={0}
      sx={{
        borderBottom: 1,
        borderColor: "divider",
        width: { md: sidebarOpen ? `calc(100% - ${DRAWER_WIDTH}px)` : "100%" },
        ml: { md: sidebarOpen ? `${DRAWER_WIDTH}px` : 0 },
        transition: (theme) =>
          theme.transitions.create(["width", "margin"], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
      }}
    >
      <Toolbar>
        <IconButton
          edge="start"
          color="inherit"
          aria-label="Toggle navigation"
          onClick={toggleSidebar}
          sx={{ mr: 1 }}
        >
          <MenuIcon />
        </IconButton>
        <Typography variant="subtitle1" sx={{ flexGrow: 1 }} noWrap>
          Lifemaker Foundation · Palms
        </Typography>
        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ display: { xs: "none", sm: "block" } }}>
            {user?.full_name}
          </Typography>
          <IconButton
            onClick={(event) => setAnchorEl(event.currentTarget)}
            aria-label="Open user menu"
            aria-controls={anchorEl ? "user-menu" : undefined}
            aria-haspopup="true"
            aria-expanded={anchorEl ? "true" : undefined}
          >
            <Avatar
              src={user?.avatar_url ?? undefined}
              alt={user?.full_name ?? "User"}
              sx={{ width: 36, height: 36, bgcolor: "primary.main" }}
            >
              {user?.full_name?.charAt(0)?.toUpperCase() ?? "U"}
            </Avatar>
          </IconButton>
          <Menu
            id="user-menu"
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={() => setAnchorEl(null)}
            anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
            transformOrigin={{ vertical: "top", horizontal: "right" }}
          >
            <MenuItem
              component={RouterLink}
              to="/profile"
              onClick={() => setAnchorEl(null)}
            >
              Profile
            </MenuItem>
            <MenuItem
              onClick={async () => {
                setAnchorEl(null);
                await logout.mutateAsync();
                navigate("/login", { replace: true });
              }}
            >
              Sign out
            </MenuItem>
          </Menu>
        </Box>
      </Toolbar>
    </AppBar>
  );
}
