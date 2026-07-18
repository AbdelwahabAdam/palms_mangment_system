import { create } from "zustand";

export type SnackbarSeverity = "success" | "info" | "warning" | "error";

interface SnackbarState {
  open: boolean;
  message: string;
  severity: SnackbarSeverity;
  show: (message: string, severity?: SnackbarSeverity) => void;
  close: () => void;
}

export const useSnackbarStore = create<SnackbarState>((set) => ({
  open: false,
  message: "",
  severity: "info",
  show: (message, severity = "info") =>
    set({ open: true, message, severity }),
  close: () => set({ open: false }),
}));

interface UiState {
  sidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}));
