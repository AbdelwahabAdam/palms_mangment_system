import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { ApiClientProvider } from "@/api/ApiClientProvider";
import { AppShell } from "@/components/layout/AppShell";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

const HomePage = lazy(async () => {
  const module = await import("@/pages/HomePage");
  return { default: module.HomePage };
});
const SearchPage = lazy(async () => {
  const module = await import("@/pages/SearchPage");
  return { default: module.SearchPage };
});
const PalmProfilePage = lazy(async () => {
  const module = await import("@/pages/PalmProfilePage");
  return { default: module.PalmProfilePage };
});
const AboutPage = lazy(async () => {
  const module = await import("@/pages/AboutPage");
  return { default: module.AboutPage };
});

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function PageFallback() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-14 sm:px-6">
      <LoadingSkeleton lines={5} />
    </div>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ApiClientProvider>
        <BrowserRouter>
          <Suspense fallback={<PageFallback />}>
            <Routes>
              <Route element={<AppShell />}>
                <Route index element={<HomePage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="palms/:palmCode" element={<PalmProfilePage />} />
                <Route path="about" element={<AboutPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ApiClientProvider>
    </QueryClientProvider>
  );
}
