export const PERMISSIONS = {
  usersRead: "users.read",
  usersInvite: "users.invite",
  usersUpdate: "users.update",
  usersDisable: "users.disable",
  usersResetPassword: "users.reset_password",
  donorsRead: "donors.read",
  donorsCreate: "donors.create",
  donorsUpdate: "donors.update",
  donorsDelete: "donors.delete",
  sectionsRead: "sections.read",
  sectionsCreate: "sections.create",
  sectionsUpdate: "sections.update",
  sectionsDelete: "sections.delete",
  palmsRead: "palms.read",
  palmsCreate: "palms.create",
  palmsUpdate: "palms.update",
  palmsDelete: "palms.delete",
  palmsBulkUpdate: "palms.bulk_update",
  palmsExport: "palms.export",
  reportsRead: "reports.read",
  reportsGenerate: "reports.generate",
  reportsSchedule: "reports.schedule",
  auditLogsRead: "audit_logs.read",
} as const;

export type PermissionCode = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

export function hasPermission(
  permissions: readonly string[] | undefined,
  required: PermissionCode | PermissionCode[],
): boolean {
  if (!permissions?.length) return false;
  const set = new Set(permissions);
  const needed = Array.isArray(required) ? required : [required];
  return needed.some((code) => set.has(code));
}

export function hasAllPermissions(
  permissions: readonly string[] | undefined,
  required: readonly PermissionCode[],
): boolean {
  if (!permissions?.length) return false;
  const set = new Set(permissions);
  return required.every((code) => set.has(code));
}
