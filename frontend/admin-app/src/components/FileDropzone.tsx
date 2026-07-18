import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Box, Stack, Typography } from "@mui/material";
import CloudUploadOutlinedIcon from "@mui/icons-material/CloudUploadOutlined";

interface FileDropzoneProps {
  onFile: (file: File) => void;
  accept?: Record<string, string[]>;
  label?: string;
  disabled?: boolean;
  maxSizeMb?: number;
}

export function FileDropzone({
  onFile,
  accept = { "image/*": [".png", ".jpg", ".jpeg", ".webp"] },
  label = "Drop an image here, or click to browse",
  disabled = false,
  maxSizeMb = 10,
}: FileDropzoneProps) {
  const onDrop = useCallback(
    (files: File[]) => {
      const file = files[0];
      if (file) onFile(file);
    },
    [onFile],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept,
    multiple: false,
    disabled,
    maxSize: maxSizeMb * 1024 * 1024,
  });

  return (
    <Box
      {...getRootProps()}
      sx={{
        border: "1px dashed",
        borderColor: isDragActive ? "primary.main" : "divider",
        bgcolor: isDragActive ? "action.hover" : "background.paper",
        borderRadius: 2,
        p: 3,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <input {...getInputProps()} aria-label={label} />
      <Stack spacing={1} alignItems="center">
        <CloudUploadOutlinedIcon color="primary" />
        <Typography textAlign="center">{label}</Typography>
        <Typography variant="caption" color="text.secondary">
          Max {maxSizeMb} MB
        </Typography>
      </Stack>
    </Box>
  );
}
