import axios from "axios";
import { apiClient } from "./client";
import type {
  AIAnalysisRead,
  AnalysisResult,
  ApiResponse,
  AllergyCreatePayload,
  AllergyRead,
  HealthCheck,
  MedicalHistoryCreatePayload,
  MedicalHistoryRead,
  MedicalReportRead,
  MedicationCreatePayload,
  MedicationRead,
  PatientCreatePayload,
  PatientRead,
  PatientUpdatePayload,
  SymptomCreatePayload,
  SymptomRead,
} from "../types/api";

export { getApiErrorMessage } from "./client";

export async function getHealthStatus() {
  const response = await apiClient.get<ApiResponse<HealthCheck>>("/health");
  return response.data;
}

export async function createPatient(payload: PatientCreatePayload) {
  const response = await apiClient.post<ApiResponse<PatientRead>>("/patients", payload);
  return response.data;
}

export async function listPatients(page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<PatientRead[]>>("/patients", {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function getPatient(patientId: number) {
  const response = await apiClient.get<ApiResponse<PatientRead>>(`/patients/${patientId}`);
  return response.data;
}

export async function updatePatient(patientId: number, payload: PatientUpdatePayload) {
  const response = await apiClient.put<ApiResponse<PatientRead>>(`/patients/${patientId}`, payload);
  return response.data;
}

export async function deletePatient(patientId: number) {
  await apiClient.delete(`/patients/${patientId}`);
}

export async function createMedicalHistory(patientId: number, payload: MedicalHistoryCreatePayload) {
  const response = await apiClient.post<ApiResponse<MedicalHistoryRead>>(
    `/patients/${patientId}/medical-history`,
    payload,
  );
  return response.data;
}

export async function listMedicalHistory(patientId: number, page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<MedicalHistoryRead[]>>(
    `/patients/${patientId}/medical-history`,
    { params: { page, page_size: pageSize } },
  );
  return response.data;
}

export async function updateMedicalHistory(historyId: number, payload: Partial<MedicalHistoryCreatePayload>) {
  const response = await apiClient.put<ApiResponse<MedicalHistoryRead>>(
    `/medical-history/${historyId}`,
    payload,
  );
  return response.data;
}

export async function deleteMedicalHistory(historyId: number) {
  await apiClient.delete(`/medical-history/${historyId}`);
}

export async function createMedication(patientId: number, payload: MedicationCreatePayload) {
  const response = await apiClient.post<ApiResponse<MedicationRead>>(
    `/patients/${patientId}/medications`,
    payload,
  );
  return response.data;
}

export async function listMedications(patientId: number, page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<MedicationRead[]>>(
    `/patients/${patientId}/medications`,
    { params: { page, page_size: pageSize } },
  );
  return response.data;
}

export async function updateMedication(medicationId: number, payload: Partial<MedicationCreatePayload>) {
  const response = await apiClient.put<ApiResponse<MedicationRead>>(
    `/medications/${medicationId}`,
    payload,
  );
  return response.data;
}

export async function deleteMedication(medicationId: number) {
  await apiClient.delete(`/medications/${medicationId}`);
}

export async function createAllergy(patientId: number, payload: AllergyCreatePayload) {
  const response = await apiClient.post<ApiResponse<AllergyRead>>(
    `/patients/${patientId}/allergies`,
    payload,
  );
  return response.data;
}

export async function listAllergies(patientId: number, page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<AllergyRead[]>>(
    `/patients/${patientId}/allergies`,
    { params: { page, page_size: pageSize } },
  );
  return response.data;
}

export async function updateAllergy(allergyId: number, payload: Partial<AllergyCreatePayload>) {
  const response = await apiClient.put<ApiResponse<AllergyRead>>(`/allergies/${allergyId}`, payload);
  return response.data;
}

export async function deleteAllergy(allergyId: number) {
  await apiClient.delete(`/allergies/${allergyId}`);
}

export async function createSymptom(patientId: number, payload: SymptomCreatePayload) {
  const response = await apiClient.post<ApiResponse<SymptomRead>>(
    `/patients/${patientId}/symptoms`,
    payload,
  );
  return response.data;
}

export async function listSymptoms(patientId: number, page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<SymptomRead[]>>(
    `/patients/${patientId}/symptoms`,
    { params: { page, page_size: pageSize } },
  );
  return response.data;
}

export async function updateSymptom(symptomId: number, payload: Partial<SymptomCreatePayload>) {
  const response = await apiClient.put<ApiResponse<SymptomRead>>(`/symptoms/${symptomId}`, payload);
  return response.data;
}

export async function deleteSymptom(symptomId: number) {
  await apiClient.delete(`/symptoms/${symptomId}`);
}

export async function uploadReport(
  patientId: number,
  file: File,
  onProgress?: (percent: number) => void,
) {
  const path = `/patients/${patientId}/reports`;
  const onUploadProgress = ({ loaded, total }: { loaded: number; total?: number }) => {
    if (total) onProgress?.(Math.round((loaded * 100) / total));
  };
  if (import.meta.env.VITE_DIRECT_REPORT_UPLOADS === "true") {
    const intent = await apiClient.post<ApiResponse<{
      token: string;
      url: string;
      fields: Record<string, string>;
    }>>(`${path}/upload-intent`, { filename: file.name, size: file.size });
    const upload = intent.data.data;
    if (!upload) throw new Error("ClinicalAI did not authorize the report upload.");

    const formData = new FormData();
    for (const [name, value] of Object.entries(upload.fields)) {
      formData.append(name, value);
    }
    formData.append("file", file);
    try {
      // Use a separate client so the ClinicalAI bearer token stays on the backend origin.
      await axios.post(upload.url, formData, {
        timeout: 600_000,
        onUploadProgress,
        withCredentials: false,
      });
    } catch {
      throw new Error("The report could not be transferred to storage. Please try again.");
    }
    const response = await apiClient.post<ApiResponse<MedicalReportRead>>(
      `${path}/complete`, { token: upload.token }, { timeout: 310_000 },
    );
    return response.data;
  }

  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<ApiResponse<MedicalReportRead>>(
    path,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress,
    },
  );
  return response.data;
}

export async function listReports(patientId: number, page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<MedicalReportRead[]>>(
    `/patients/${patientId}/reports`,
    { params: { page, page_size: pageSize } },
  );
  return response.data;
}

export async function getReport(reportId: number) {
  const response = await apiClient.get<ApiResponse<MedicalReportRead>>(`/patients/reports/${reportId}`);
  return response.data;
}

export function reportDownloadUrl(reportId: number) {
  return `${apiClient.defaults.baseURL?.replace(/\/$/, "")}/patients/reports/${reportId}/download`;
}

export async function deleteReport(reportId: number) {
  await apiClient.delete(`/patients/reports/${reportId}`);
}

export async function createAnalysis(patientId: number, reportId?: number | null) {
  const response = await apiClient.post<ApiResponse<AIAnalysisRead>>(
    `/patients/${patientId}/analysis`,
    undefined,
    {
      params: reportId ? { report_id: reportId } : undefined,
    },
  );
  return response.data;
}

export async function analyzePatient(patientId: number) {
  const response = await apiClient.post<ApiResponse<AnalysisResult>>(
    `/patients/${patientId}/analyze`, undefined, { timeout: 310_000 },
  );
  return response.data;
}

export async function listAnalyses(patientId: number, page = 1, pageSize = 20) {
  const response = await apiClient.get<ApiResponse<AIAnalysisRead[]>>(
    `/patients/${patientId}/analysis`,
    { params: { page, page_size: pageSize } },
  );
  return response.data;
}

export async function getAnalysis(analysisId: number) {
  const response = await apiClient.get<ApiResponse<AIAnalysisRead>>(`/patients/analysis/${analysisId}`);
  return response.data;
}
