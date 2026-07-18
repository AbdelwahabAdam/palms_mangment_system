import { ApiError } from "./errors";

export interface BinaryUpload {
  file: Blob;
  filename?: string;
  field?: "file" | "image";
}

export type FormDataFactory = () => FormData;

export function defaultFormDataFactory(): FormData {
  if (typeof FormData === "undefined") {
    throw new ApiError({
      status: 0,
      code: "form_data_unavailable",
      message: "FormData is unavailable in this runtime.",
      kind: "invalid_response",
    });
  }
  return new FormData();
}

/**
 * Builds a multipart body without setting Content-Type. Axios/browser transport
 * must add the boundary, and tests can inject their own FormData implementation.
 */
export function createMultipartBody(
  upload: BinaryUpload,
  createFormData: FormDataFactory = defaultFormDataFactory,
): FormData {
  const form = createFormData();
  const field = upload.field ?? "file";
  if (upload.filename === undefined) {
    form.append(field, upload.file);
  } else {
    form.append(field, upload.file, upload.filename);
  }
  return form;
}
