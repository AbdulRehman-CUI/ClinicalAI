// Shared frontend types that mirror the backend response envelope.
export interface ApiResponse<TData> {
  success: boolean;
  message: string;
  data: TData | null;
  pagination?: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
  };
}

export interface HealthCheck {
  status: string;
}

export interface PatientCreatePayload {
  first_name: string;
  last_name: string;
  age: number;
  biological_sex: string;
  blood_group: string;
  height_cm: number;
  weight_kg: number;
  pregnancy_status?: string | null;
}

export interface PatientUpdatePayload extends Partial<PatientCreatePayload> {}

export interface PatientRead extends PatientCreatePayload {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface MedicalHistoryCreatePayload {
  condition_name: string;
  diagnosis_date?: string | null;
  notes: string;
}

export interface MedicalHistoryRead extends MedicalHistoryCreatePayload {
  id: number;
  patient_id: number;
}

export interface MedicationCreatePayload {
  medication_name: string;
  dosage: string;
  frequency: string;
  start_date: string;
  notes: string;
}

export interface MedicationRead extends MedicationCreatePayload {
  id: number;
  patient_id: number;
}

export interface AllergyCreatePayload {
  allergen: string;
  reaction: string;
  severity: string;
}

export interface AllergyRead extends AllergyCreatePayload {
  id: number;
  patient_id: number;
}

export interface SymptomCreatePayload {
  symptom_name: string;
  duration: string;
  severity: string;
  notes: string;
}

export interface SymptomRead extends SymptomCreatePayload {
  id: number;
  patient_id: number;
}

export interface MedicalReportRead {
  id: number;
  patient_id: number;
  original_filename: string;
  stored_filename: string;
  file_type: string;
  extracted_text?: string | null;
  summary?: string | null;
  upload_timestamp: string;
}

export interface AIAnalysisRead {
  id: number;
  patient_id: number;
  report_id?: number | null;
  medication_warnings: string[];
  possible_diagnoses: string[];
  confidence: number;
  supporting_evidence: string[];
  missing_information: string[];
  suggested_next_steps: string[];
  created_at: string;
}

export type AnalysisValue =
  | string
  | number
  | boolean
  | null
  | AnalysisValue[]
  | { [key: string]: AnalysisValue };

// The analyze endpoint returns the validated provider output, not the stored analysis schema.
export interface AnalysisResult {
  analysis_id: number;
  patient_id: number;
  report_id?: number | null;
  possible_diagnoses: AnalysisValue[];
  medication_warnings: AnalysisValue[];
  critical_alerts: AnalysisValue[];
  recommended_tests: AnalysisValue[];
  recommended_specialist: string;
  summary: string;
}
