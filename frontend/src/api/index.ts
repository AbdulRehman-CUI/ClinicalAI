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
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<ApiResponse<MedicalReportRead>>(
    `/patients/${patientId}/reports`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress?.(percent);
        }
      },
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
  const response = await apiClient.get<ApiResponse<MedicalReportRead>>(`/reports/${reportId}`);
  return response.data;
}

export async function deleteReport(reportId: number) {
  await apiClient.delete(`/reports/${reportId}`);
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
  const response = await apiClient.post<ApiResponse<AnalysisResult>>(`/patients/${patientId}/analyze`);
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
  const response = await apiClient.get<ApiResponse<AIAnalysisRead>>(`/analysis/${analysisId}`);
  return response.data;
}
