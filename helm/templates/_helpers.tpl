{{- define "core-api.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "core-api.labels" -}}
helm.sh/chart: {{ include "core-api.chart" . }}
app.kubernetes.io/name: goalixa
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "core-api.selectorLabels" -}}
app.kubernetes.io/name: goalixa
{{- end }}

{{- define "core-api.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}
