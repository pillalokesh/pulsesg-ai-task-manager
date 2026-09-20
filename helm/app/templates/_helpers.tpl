{{- define "pulsesg-ai-task-manager.name" -}}{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}{{- end }}
{{- define "pulsesg-ai-task-manager.fullname" -}}{{- .Release.Name | trunc 63 | trimSuffix "-" }}{{- end }}
{{- define "pulsesg-ai-task-manager.serviceAccountName" -}}{{- if .Values.serviceAccount.create }}{{ default (include "pulsesg-ai-task-manager.fullname" .) .Values.serviceAccount.name }}{{- else }}default{{- end }}{{- end }}
