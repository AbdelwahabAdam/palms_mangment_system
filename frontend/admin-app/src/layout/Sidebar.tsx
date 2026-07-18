import { useMemo, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import {
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import ParkOutlinedIcon from "@mui/icons-material/ParkOutlined";
import VolunteerActivismOutlinedIcon from "@mui/icons-material/VolunteerActivismOutlined";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import PeopleOutlineIcon from "@mui/icons-material/PeopleOutline";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";

import { useAuth } from "@/auth/useAuth";
import { PERMISSIONS, hasPermission } from "@/auth/permissions";
import { useUiStore } from "@/stores/uiStore";

export const DRAWER_WIDTH = 260;

interface NavItem {
  label: string;
  to: string;
  icon: ReactNode;
  permission?: (typeof PERMISSIONS)[keyof typeof PERMISSIONS] | Array<(typeof PERMISSIONS)[keyof typeof PERMISSIONS]>;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: "Overview",
    to: "/overview",
    icon: <DashboardOutlinedIcon />,
    permission: PERMISSIONS.palmsRead,
  },
  {
    label: "Palms",
    to: "/palms",
    icon: <ParkOutlinedIcon />,
    permission: PERMISSIONS.palmsRead,
  },
  {
    label: "Donors",
    to: "/donors",
    icon: <VolunteerActivismOutlinedIcon />,
    permission: PERMISSIONS.donorsRead,
  },
  {
    label: "Sections",
    to: "/sections",
    icon: <MapOutlinedIcon />,
    permission: PERMISSIONS.sectionsRead,
  },
  {
    label: "Reports",
    to: "/reports",
    icon: <AssessmentOutlinedIcon />,
    permission: PERMISSIONS.reportsRead,
  },
  {
    label: "Schedules",
    to: "/report-schedules",
    icon: <ScheduleOutlinedIcon />,
    permission: PERMISSIONS.reportsRead,
  },
  {
    label: "Users",
    to: "/users",
    icon: <PeopleOutlineIcon />,
    permission: PERMISSIONS.usersRead,
  },
  {
    label: "Audit logs",
    to: "/audit-logs",
    icon: <HistoryOutlinedIcon />,
    permission: [PERMISSIONS.auditLogsRead, PERMISSIONS.palmsRead],
  },
  {
    label: "Profile",
    to: "/profile",
    icon: <PersonOutlineIcon />,
  },
];

export function Sidebar() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const location = useLocation();
  const { permissions } = useAuth();
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);

  const items = useMemo(
    () =>
      NAV_ITEMS.filter(
        (item) => !item.permission || hasPermission(permissions, item.permission),
      ),
    [permissions],
  );

  const content = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar sx={{ gap: 1, justifyContent: "space-between" }}>
        <Typography variant="h6" color="primary" noWrap>
          Palms Admin
        </Typography>
        {isMobile ? (
          <IconButton
            aria-label="Close navigation"
            onClick={() => setSidebarOpen(false)}
          >
            <ChevronLeftIcon />
          </IconButton>
        ) : null}
      </Toolbar>
      <Divider />
      <List sx={{ flex: 1, px: 1, py: 1 }}>
        {items.map((item) => {
          const selected =
            location.pathname === item.to ||
            location.pathname.startsWith(`${item.to}/`);
          return (
            <ListItemButton
              key={item.to}
              component={NavLink}
              to={item.to}
              selected={selected}
              onClick={() => {
                if (isMobile) setSidebarOpen(false);
              }}
              sx={{ borderRadius: 1.5, mb: 0.5 }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  if (isMobile) {
    return (
      <Drawer
        variant="temporary"
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          "& .MuiDrawer-paper": { width: DRAWER_WIDTH },
        }}
      >
        {content}
      </Drawer>
    );
  }

  return (
    <Drawer
      variant="persistent"
      open={sidebarOpen}
      sx={{
        width: sidebarOpen ? DRAWER_WIDTH : 0,
        flexShrink: 0,
        "& .MuiDrawer-paper": {
          width: DRAWER_WIDTH,
          boxSizing: "border-box",
        },
      }}
    >
      {content}
    </Drawer>
  );
}
