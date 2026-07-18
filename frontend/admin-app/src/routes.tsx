import { Navigate, Route, Routes } from "react-router-dom";

import { AuthGuard } from "@/auth/AuthGuard";
import { PERMISSIONS } from "@/auth/permissions";
import { AdminShell } from "@/layout/AdminShell";
import { LoginPage } from "@/pages/auth/LoginPage";
import { ForgotPasswordPage } from "@/pages/auth/ForgotPasswordPage";
import { ResetPasswordPage } from "@/pages/auth/ResetPasswordPage";
import { OverviewPage } from "@/pages/OverviewPage";
import { PalmsListPage } from "@/pages/palms/PalmsListPage";
import { PalmCreatePage, PalmEditPage } from "@/pages/palms/PalmFormPage";
import { PalmDetailPage } from "@/pages/palms/PalmDetailPage";
import {
  DonorCreatePage,
  DonorDetailPage,
  DonorsListPage,
} from "@/pages/donors/DonorsPages";
import {
  SectionCreatePage,
  SectionDetailPage,
  SectionsListPage,
} from "@/pages/sections/SectionsPages";
import {
  ReportScheduleDetailPage,
  ReportScheduleFormPage,
  ReportSchedulesListPage,
  ReportsPage,
  ReportTemplatesPage,
} from "@/pages/reports/ReportsPages";
import { ProfilePage } from "@/pages/ProfilePage";
import {
  UserDetailPage,
  UserInvitePage,
  UsersListPage,
} from "@/pages/users/UsersPages";
import { AuditLogsPage } from "@/pages/AuditLogsPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<AuthGuard />}>
        <Route element={<AdminShell />}>
          <Route index element={<Navigate to="/overview" replace />} />
          <Route
            path="/overview"
            element={<AuthGuard permission={PERMISSIONS.palmsRead} />}
          >
            <Route index element={<OverviewPage />} />
          </Route>
          <Route path="/palms" element={<AuthGuard permission={PERMISSIONS.palmsRead} />}>
            <Route index element={<PalmsListPage />} />
            <Route path="new" element={<AuthGuard permission={PERMISSIONS.palmsCreate} />}>
              <Route index element={<PalmCreatePage />} />
            </Route>
            <Route path=":id" element={<PalmDetailPage />} />
            <Route path=":id/edit" element={<AuthGuard permission={PERMISSIONS.palmsUpdate} />}>
              <Route index element={<PalmEditPage />} />
            </Route>
          </Route>
          <Route path="/donors" element={<AuthGuard permission={PERMISSIONS.donorsRead} />}>
            <Route index element={<DonorsListPage />} />
            <Route path="new" element={<AuthGuard permission={PERMISSIONS.donorsCreate} />}>
              <Route index element={<DonorCreatePage />} />
            </Route>
            <Route path=":id" element={<DonorDetailPage />} />
          </Route>
          <Route path="/sections" element={<AuthGuard permission={PERMISSIONS.sectionsRead} />}>
            <Route index element={<SectionsListPage />} />
            <Route path="new" element={<AuthGuard permission={PERMISSIONS.sectionsCreate} />}>
              <Route index element={<SectionCreatePage />} />
            </Route>
            <Route path=":id" element={<SectionDetailPage />} />
          </Route>
          <Route path="/reports" element={<AuthGuard permission={PERMISSIONS.reportsRead} />}>
            <Route index element={<ReportsPage />} />
            <Route path="templates" element={<ReportTemplatesPage />} />
          </Route>
          <Route
            path="/report-schedules"
            element={<AuthGuard permission={PERMISSIONS.reportsRead} />}
          >
            <Route index element={<ReportSchedulesListPage />} />
            <Route
              path="new"
              element={<AuthGuard permission={PERMISSIONS.reportsSchedule} />}
            >
              <Route index element={<ReportScheduleFormPage />} />
            </Route>
            <Route path=":id" element={<ReportScheduleDetailPage />} />
          </Route>
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/users" element={<AuthGuard permission={PERMISSIONS.usersRead} />}>
            <Route index element={<UsersListPage />} />
            <Route path="new" element={<AuthGuard permission={PERMISSIONS.usersInvite} />}>
              <Route index element={<UserInvitePage />} />
            </Route>
            <Route path=":id" element={<UserDetailPage />} />
          </Route>
          <Route
            path="/audit-logs"
            element={
              <AuthGuard
                permission={[PERMISSIONS.auditLogsRead, PERMISSIONS.palmsRead]}
              />
            }
          >
            <Route index element={<AuditLogsPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/overview" replace />} />
    </Routes>
  );
}
