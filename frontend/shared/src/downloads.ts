/**
 * Helpers for opening signed report download URLs returned by the API.
 * Apps supply the navigation function so the shared package stays free of
 * browser globals and remains testable in Node.
 */
export type OpenUrl = (url: string) => void;

export function openDownloadUrl(url: string, openUrl: OpenUrl): void {
  if (!url.trim()) {
    throw new TypeError("Download URL must not be empty.");
  }
  openUrl(url);
}

export function openReportDownloads(
  files: ReadonlyArray<{ filename: string; download_url: string }>,
  openUrl: OpenUrl,
): void {
  for (const file of files) {
    openDownloadUrl(file.download_url, openUrl);
  }
}
