{{/*
Expand the chart name.
*/}}
{{- define "palms.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "palms.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Chart label.
*/}}
{{- define "palms.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "palms.labels" -}}
helm.sh/chart: {{ include "palms.chart" . }}
{{ include "palms.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels (release-level).
*/}}
{{- define "palms.selectorLabels" -}}
app.kubernetes.io/name: {{ include "palms.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Component labels helper — usage: include "palms.componentLabels" (dict "ctx" . "component" "backend")
*/}}
{{- define "palms.componentLabels" -}}
{{ include "palms.labels" .ctx }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Component selector labels.
*/}}
{{- define "palms.componentSelectorLabels" -}}
{{ include "palms.selectorLabels" .ctx }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{/*
Stable in-cluster DNS names (must match frontend nginx + app config).
*/}}
{{- define "palms.backend.name" -}}backend{{- end }}
{{- define "palms.frontend.name" -}}frontend{{- end }}
{{- define "palms.postgres.name" -}}postgres{{- end }}
{{- define "palms.redis.name" -}}redis{{- end }}
{{- define "palms.minio.name" -}}minio{{- end }}
{{- define "palms.mailhog.name" -}}mailhog{{- end }}

{{- define "palms.configMapName" -}}
{{- printf "%s-env" (include "palms.fullname" .) }}
{{- end }}

{{- define "palms.secretName" -}}
{{- printf "%s-secret" (include "palms.fullname" .) }}
{{- end }}

{{- define "palms.publicBaseUrl" -}}
{{- printf "http://%s:%v" .Values.global.publicHost .Values.global.publicPort }}
{{- end }}

{{- define "palms.s3PublicBaseUrl" -}}
{{- printf "http://%s:%v/%s" .Values.global.publicHost .Values.global.minioPublicPort .Values.config.S3_BUCKET_NAME }}
{{- end }}

{{- define "palms.databaseUrl" -}}
{{- printf "postgresql+psycopg://%s:%s@%s:%v/%s" .Values.postgres.auth.username .Values.postgres.auth.password (include "palms.postgres.name" .) .Values.postgres.service.port .Values.postgres.auth.database }}
{{- end }}
