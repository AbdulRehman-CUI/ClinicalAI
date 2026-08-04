import { useMemo, useState } from "react";
import { Activity, AlertTriangle, ClipboardList, FileText, PlusCircle, RefreshCw, ShieldAlert, Stethoscope, TestTube2 } from "lucide-react";
import toast from "react-hot-toast";

import { useAuth } from "../contexts/AuthContext";
import {
  analyzePatient,
  createAllergy,
  createMedicalHistory,
  createMedication,
  createPatient,
  createSymptom,
  getApiErrorMessage,
  listAllergies,
  listMedicalHistory,
  listMedications,
  listReports,
  listSymptoms,
  uploadReport,
} from "../api";
import type {
  AllergyCreatePayload,
  AllergyRead,
  AnalysisResult,
  MedicalHistoryCreatePayload,
  MedicalHistoryRead,
  MedicalReportRead,
  MedicationCreatePayload,
  MedicationRead,
  PatientRead,
  SymptomCreatePayload,
  SymptomRead,
} from "../types/api";

type PatientFormState = {
  first_name: string;
  last_name: string;
  age: string;
  biological_sex: string;
  blood_group: string;
  height_cm: string;
  weight_kg: string;
  pregnancy_status: string;
};

type HistoryFormState = {
  condition_name: string;
  diagnosis_date: string;
  notes: string;
};

type AllergyFormState = {
  allergen: string;
  reaction: string;
  severity: string;
};

type MedicationFormState = {
  medication_name: string;
  dosage: string;
  frequency: string;
  start_date: string;
  notes: string;
};

type SymptomFormState = {
  symptom_name: string;
  duration: string;
  severity: string;
  notes: string;
};

const initialPatientForm: PatientFormState = {
  first_name: "Alicia",
  last_name: "Nguyen",
  age: "38",
  biological_sex: "Female",
  blood_group: "O+",
  height_cm: "162",
  weight_kg: "63",
  pregnancy_status: "Unknown",
};

const initialHistoryForm: HistoryFormState = {
  condition_name: "",
  diagnosis_date: "",
  notes: "",
};

const initialAllergyForm: AllergyFormState = {
  allergen: "",
  reaction: "",
  severity: "Mild",
};

const initialMedicationForm: MedicationFormState = {
  medication_name: "",
  dosage: "",
  frequency: "",
  start_date: "",
  notes: "",
};

const initialSymptomForm: SymptomFormState = {
  symptom_name: "",
  duration: "",
  severity: "Moderate",
  notes: "",
};

const allowedFileTypes = ["PDF", "DOCX", "TXT", "JPG", "JPEG", "PNG"];
const acceptedFileExtensions = ".pdf,.docx,.txt,.jpg,.jpeg,.png";

export function HomePage() {
  const { user } = useAuth();
  const [form, setForm] = useState<PatientFormState>(initialPatientForm);
  const [patient, setPatient] = useState<PatientRead | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [historyForm, setHistoryForm] = useState<HistoryFormState>(initialHistoryForm);
  const [allergyForm, setAllergyForm] = useState<AllergyFormState>(initialAllergyForm);
  const [medicationForm, setMedicationForm] = useState<MedicationFormState>(initialMedicationForm);
  const [symptomForm, setSymptomForm] = useState<SymptomFormState>(initialSymptomForm);
  const [historyItems, setHistoryItems] = useState<MedicalHistoryRead[]>([]);
  const [allergyItems, setAllergyItems] = useState<AllergyRead[]>([]);
  const [medicationItems, setMedicationItems] = useState<MedicationRead[]>([]);
  const [symptomItems, setSymptomItems] = useState<SymptomRead[]>([]);
  const [reportItems, setReportItems] = useState<MedicalReportRead[]>([]);
  const [statusMessage, setStatusMessage] = useState("Create a patient profile, add relevant clinical context, upload a report, and run the AI workflow.");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreatingPatient, setIsCreatingPatient] = useState(false);
  const [isCreatingHistory, setIsCreatingHistory] = useState(false);
  const [isCreatingAllergy, setIsCreatingAllergy] = useState(false);
  const [isCreatingMedication, setIsCreatingMedication] = useState(false);
  const [isCreatingSymptom, setIsCreatingSymptom] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const canAnalyze = useMemo(() => Boolean(patient) && (symptomItems.length > 0 || reportItems.length > 0), [patient, symptomItems.length, reportItems.length]);
  const canUseAi = user?.role === "Doctor" || user?.role === "Admin";

  function updatePatientField(field: keyof PatientFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function resetWorkflow() {
    setForm(initialPatientForm);
    setPatient(null);
    setAnalysis(null);
    setSelectedFile(null);
    setUploadProgress(0);
    setHistoryForm(initialHistoryForm);
    setAllergyForm(initialAllergyForm);
    setMedicationForm(initialMedicationForm);
    setSymptomForm(initialSymptomForm);
    setHistoryItems([]);
    setAllergyItems([]);
    setMedicationItems([]);
    setSymptomItems([]);
    setReportItems([]);
    setErrorMessage(null);
    setStatusMessage("Workflow reset. Create a new patient profile to begin again.");
    toast.success("Workflow reset.");
  }

  async function refreshPatientCollections(patientId: number) {
    const [historyResponse, allergyResponse, medicationResponse, symptomResponse, reportResponse] = await Promise.all([
      listMedicalHistory(patientId),
      listAllergies(patientId),
      listMedications(patientId),
      listSymptoms(patientId),
      listReports(patientId),
    ]);

    setHistoryItems(historyResponse.data ?? []);
    setAllergyItems(allergyResponse.data ?? []);
    setMedicationItems(medicationResponse.data ?? []);
    setSymptomItems(symptomResponse.data ?? []);
    setReportItems(reportResponse.data ?? []);
  }

  async function handleCreatePatient(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setAnalysis(null);
    setStatusMessage("Creating patient record...");

    const trimmedFirstName = form.first_name.trim();
    const trimmedLastName = form.last_name.trim();
    const age = Number(form.age);
    const height = Number(form.height_cm);
    const weight = Number(form.weight_kg);

    if (!trimmedFirstName || !trimmedLastName) {
      const message = "First and last name are required.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!/^[A-Za-zÀ-ÿ' -]+$/.test(trimmedFirstName) || !/^[A-Za-zÀ-ÿ' -]+$/.test(trimmedLastName)) {
      const message = "Names may only contain letters, spaces, apostrophes, or hyphens.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!Number.isFinite(age) || age < 0 || age > 120) {
      const message = "Age must be between 0 and 120.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!Number.isFinite(height) || height < 30 || height > 250) {
      const message = "Height must be between 30 and 250 cm.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!Number.isFinite(weight) || weight < 1 || weight > 400) {
      const message = "Weight must be between 1 and 400 kg.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!form.biological_sex || !form.blood_group) {
      const message = "Biological sex and blood group are required.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    setIsCreatingPatient(true);

    try {
      const payload = {
        first_name: trimmedFirstName,
        last_name: trimmedLastName,
        age,
        biological_sex: form.biological_sex,
        blood_group: form.blood_group,
        height_cm: height,
        weight_kg: weight,
        pregnancy_status: form.biological_sex === "Female" ? form.pregnancy_status || "Unknown" : null,
      };

      const response = await createPatient(payload);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The backend did not return a patient.");
      }

      setPatient(response.data);
      await refreshPatientCollections(response.data.id);
      setStatusMessage("Patient created successfully. Add history, symptoms, or upload a report to continue.");
      toast.success(response.message || "Patient created successfully.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Unable to create patient.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsCreatingPatient(false);
    }
  }

  async function handleCreateHistory(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patient) {
      setErrorMessage("Create a patient first.");
      return;
    }

    const payload: MedicalHistoryCreatePayload = {
      condition_name: historyForm.condition_name.trim(),
      diagnosis_date: historyForm.diagnosis_date || null,
      notes: historyForm.notes.trim(),
    };

    if (!payload.condition_name) {
      setErrorMessage("Condition name is required.");
      return;
    }

    setIsCreatingHistory(true);
    try {
      const response = await createMedicalHistory(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The record could not be created.");
      }
      await refreshPatientCollections(patient.id);
      setHistoryForm(initialHistoryForm);
      setStatusMessage("Medical history record added.");
      toast.success(response.message || "Medical history record added.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Unable to add medical history.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsCreatingHistory(false);
    }
  }

  async function handleCreateAllergy(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patient) {
      setErrorMessage("Create a patient first.");
      return;
    }

    const payload: AllergyCreatePayload = {
      allergen: allergyForm.allergen.trim(),
      reaction: allergyForm.reaction.trim(),
      severity: allergyForm.severity.trim(),
    };

    if (!payload.allergen || !payload.reaction || !payload.severity) {
      setErrorMessage("All allergy fields are required.");
      return;
    }

    setIsCreatingAllergy(true);
    try {
      const response = await createAllergy(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The allergy could not be created.");
      }
      await refreshPatientCollections(patient.id);
      setAllergyForm(initialAllergyForm);
      setStatusMessage("Allergy entry added.");
      toast.success(response.message || "Allergy entry added.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Unable to add allergy.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsCreatingAllergy(false);
    }
  }

  async function handleCreateMedication(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patient) {
      setErrorMessage("Create a patient first.");
      return;
    }

    const payload: MedicationCreatePayload = {
      medication_name: medicationForm.medication_name.trim(),
      dosage: medicationForm.dosage.trim(),
      frequency: medicationForm.frequency.trim(),
      start_date: medicationForm.start_date,
      notes: medicationForm.notes.trim(),
    };

    if (!payload.medication_name || !payload.dosage || !payload.frequency || !payload.start_date) {
      setErrorMessage("Medication name, dosage, frequency, and start date are required.");
      return;
    }

    setIsCreatingMedication(true);
    try {
      const response = await createMedication(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The medication could not be created.");
      }
      await refreshPatientCollections(patient.id);
      setMedicationForm(initialMedicationForm);
      setStatusMessage("Medication entry added.");
      toast.success(response.message || "Medication entry added.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Unable to add medication.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsCreatingMedication(false);
    }
  }

  async function handleCreateSymptom(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!patient) {
      setErrorMessage("Create a patient first.");
      return;
    }

    const payload: SymptomCreatePayload = {
      symptom_name: symptomForm.symptom_name.trim(),
      duration: symptomForm.duration.trim(),
      severity: symptomForm.severity.trim(),
      notes: symptomForm.notes.trim(),
    };

    if (!payload.symptom_name || !payload.duration || !payload.severity) {
      setErrorMessage("Symptom name, duration, and severity are required.");
      return;
    }

    setIsCreatingSymptom(true);
    try {
      const response = await createSymptom(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The symptom could not be created.");
      }
      await refreshPatientCollections(patient.id);
      setSymptomForm(initialSymptomForm);
      setStatusMessage("Symptom entry added.");
      toast.success(response.message || "Symptom entry added.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Unable to add symptom.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsCreatingSymptom(false);
    }
  }

  async function handleUploadReport() {
    if (!patient) {
      const message = "Create a patient before uploading a report.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!selectedFile) {
      const message = "Choose a report file before uploading.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    const extension = selectedFile.name.split(".").pop()?.toUpperCase() ?? "";
    if (!allowedFileTypes.includes(extension)) {
      const message = "Unsupported file type. Please use PDF, DOCX, TXT, JPG, JPEG, or PNG.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    setErrorMessage(null);
    setStatusMessage("Uploading report...");
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const response = await uploadReport(patient.id, selectedFile, (percent) => setUploadProgress(percent));
      if (!response.success || !response.data) {
        throw new Error(response.message || "The report upload did not complete.");
      }
      await refreshPatientCollections(patient.id);
      setStatusMessage(`Report uploaded: ${response.data.original_filename}`);
      toast.success(response.message || "Report uploaded successfully.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Unable to upload the report.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsUploading(false);
    }
  }

  async function handleAnalyzePatient() {
    if (!patient) {
      const message = "Create a patient before running the analysis.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!canAnalyze) {
      const message = "Add at least one symptom or upload a report before running analysis.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    setErrorMessage(null);
    setStatusMessage("Preparing clinical context and running the AI workflow...");
    setIsAnalyzing(true);

    try {
      const response = await analyzePatient(patient.id);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The analysis could not be completed.");
      }
      setAnalysis(response.data);
      setStatusMessage("Analysis completed successfully.");
      toast.success(response.message || "Analysis completed successfully.");
    } catch (error) {
      const message = getApiErrorMessage(error, "The AI workflow could not be completed.");
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsAnalyzing(false);
    }
  }

  function handleFileSelection(file: File | null) {
    setSelectedFile(file);
    setUploadProgress(0);
  }

  function handleDrop(event: React.DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0] ?? null;
    handleFileSelection(file);
  }

  return (
    <section className="space-y-6">
      <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-2xl font-semibold text-zinc-950">ClinicalAI workflow</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-zinc-600">
              This workflow now covers patient intake, clinical context, report upload, and AI analysis with a production-style experience.
            </p>
            <p className="mt-2 text-sm text-zinc-600">Signed in as {user?.full_name || user?.email || "a clinician"}. Role: {user?.role || "Staff"}.</p>
          </div>
          <div className="flex items-center gap-3">
            {!canUseAi ? (
              <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
                AI analysis is restricted to Doctor and Admin roles.
              </div>
            ) : null}
              <button
              type="button"
              onClick={resetWorkflow}
              className="inline-flex items-center gap-2 rounded-md border border-zinc-300 px-3 py-2 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100"
            >
              <RefreshCw className="h-4 w-4" />
              Reset workflow
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <form onSubmit={handleCreatePatient} className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold text-zinc-950">Patient profile</h3>
              <p className="mt-1 text-sm text-zinc-600">Create the patient record and capture core demographics before adding clinical context.</p>
            </div>
            <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-teal-700">Step 1</span>
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>First name</span>
              <input
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.first_name}
                onChange={(event) => updatePatientField("first_name", event.target.value)}
                required
              />
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Last name</span>
              <input
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.last_name}
                onChange={(event) => updatePatientField("last_name", event.target.value)}
                required
              />
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Age</span>
              <input
                type="number"
                min="0"
                max="120"
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.age}
                onChange={(event) => updatePatientField("age", event.target.value)}
                required
              />
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Biological sex</span>
              <select
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.biological_sex}
                onChange={(event) => {
                  const value = event.target.value;
                  updatePatientField("biological_sex", value);
                  if (value !== "Female") {
                    updatePatientField("pregnancy_status", "Unknown");
                  }
                }}
                required
              >
                <option value="">Select sex</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
              </select>
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Blood group</span>
              <select
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.blood_group}
                onChange={(event) => updatePatientField("blood_group", event.target.value)}
                required
              >
                <option value="">Select blood group</option>
                <option value="A+">A+</option>
                <option value="A-">A-</option>
                <option value="B+">B+</option>
                <option value="B-">B-</option>
                <option value="AB+">AB+</option>
                <option value="AB-">AB-</option>
                <option value="O+">O+</option>
                <option value="O-">O-</option>
                <option value="Unknown">Unknown</option>
              </select>
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Pregnancy status</span>
              <select
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-zinc-100"
                value={form.pregnancy_status}
                onChange={(event) => updatePatientField("pregnancy_status", event.target.value)}
                disabled={form.biological_sex !== "Female"}
              >
                <option value="Pregnant">Pregnant</option>
                <option value="Not Pregnant">Not Pregnant</option>
                <option value="Unknown">Unknown</option>
              </select>
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Height (cm)</span>
              <input
                type="number"
                min="30"
                max="250"
                step="0.1"
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.height_cm}
                onChange={(event) => updatePatientField("height_cm", event.target.value)}
                required
              />
            </label>
            <label className="space-y-2 text-sm font-medium text-zinc-700">
              <span>Weight (kg)</span>
              <input
                type="number"
                min="1"
                max="400"
                step="0.1"
                className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm"
                value={form.weight_kg}
                onChange={(event) => updatePatientField("weight_kg", event.target.value)}
                required
              />
            </label>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="submit"
              disabled={isCreatingPatient}
              className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isCreatingPatient ? "Creating patient..." : "Create patient"}
            </button>
            {patient ? <span className="text-sm text-zinc-600">Current patient: {patient.first_name} {patient.last_name}</span> : null}
          </div>
        </form>

        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-zinc-950">Medical report</h3>
                <p className="mt-1 text-sm text-zinc-600">Upload a PDF, DOCX, TXT, JPG, JPEG, or PNG report for the active patient.</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">Step 2</span>
            </div>

            <label
              className={`mt-6 flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-4 py-8 text-center text-sm transition ${dragActive ? "border-teal-600 bg-teal-50" : "border-zinc-300 bg-zinc-50"}`}
              onDragOver={(event) => {
                event.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
            >
              <FileText className="h-8 w-8 text-zinc-500" />
              <span className="mt-3 font-semibold text-zinc-900">Choose report file or drag and drop</span>
              <span className="mt-2 text-zinc-600">Supported types: {allowedFileTypes.join(", ")}</span>
              <input
                type="file"
                accept={acceptedFileExtensions}
                className="hidden"
                onChange={(event) => handleFileSelection(event.target.files?.[0] ?? null)}
              />
            </label>

            {selectedFile ? <p className="mt-3 text-sm text-zinc-700">Selected file: {selectedFile.name}</p> : <p className="mt-3 text-sm text-zinc-500">No file selected yet.</p>}

            {isUploading ? (
              <div className="mt-4">
                <div className="flex items-center justify-between text-sm text-zinc-600">
                  <span>Uploading</span>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="mt-2 h-2 rounded-full bg-zinc-200">
                  <div className="h-2 rounded-full bg-teal-700 transition-all" style={{ width: `${uploadProgress}%` }} />
                </div>
              </div>
            ) : null}

            <button
              type="button"
              onClick={handleUploadReport}
              disabled={isUploading || !patient}
              className="mt-6 w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isUploading ? "Uploading report..." : "Upload report"}
            </button>
          </div>

          <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-zinc-950">AI analysis</h3>
                <p className="mt-1 text-sm text-zinc-600">The analysis button stays disabled until a patient exists and there is clinical evidence to review.</p>
              </div>
              <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-700">Step 3</span>
            </div>

            <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-900">
              {canAnalyze ? "Clinical context is ready for analysis." : "Add at least one symptom or upload a report to unlock analysis."}
            </div>

            <button
              type="button"
              onClick={handleAnalyzePatient}
              disabled={isAnalyzing || !canAnalyze || !canUseAi}
              className="mt-6 w-full rounded-md bg-amber-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-amber-700 disabled:cursor-not-allowed disabled:bg-zinc-400"
            >
              {isAnalyzing ? "Analyzing..." : canUseAi ? "Run analysis" : "Doctor/Admin access required"}
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-6 2xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-zinc-950">Clinical context</h3>
                <p className="mt-1 text-sm text-zinc-600">Capture supporting medical history, allergies, medications, and symptoms for the active patient.</p>
              </div>
              <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-700">Clinical data</span>
            </div>

            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                  <ClipboardList className="h-4 w-4 text-teal-700" />
                  Medical history
                </div>
                <form onSubmit={handleCreateHistory} className="mt-4 space-y-3">
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Condition" value={historyForm.condition_name} onChange={(event) => setHistoryForm((current) => ({ ...current, condition_name: event.target.value }))} required />
                  <input type="date" className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" value={historyForm.diagnosis_date} onChange={(event) => setHistoryForm((current) => ({ ...current, diagnosis_date: event.target.value }))} />
                  <textarea className="min-h-24 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Notes" value={historyForm.notes} onChange={(event) => setHistoryForm((current) => ({ ...current, notes: event.target.value }))} required />
                  <button type="submit" disabled={isCreatingHistory || !patient} className="inline-flex items-center gap-2 rounded-md bg-teal-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-zinc-400">
                    <PlusCircle className="h-4 w-4" />
                    {isCreatingHistory ? "Saving..." : "Add history"}
                  </button>
                </form>
                {historyItems.length === 0 ? <p className="mt-4 text-sm text-zinc-500">No medical history yet.</p> : <ul className="mt-4 space-y-2 text-sm text-zinc-700">{historyItems.map((item) => <li key={item.id} className="rounded-md bg-zinc-50 px-3 py-2">{item.condition_name}</li>)}</ul>}
              </div>

              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                  <AlertTriangle className="h-4 w-4 text-rose-600" />
                  Allergies
                </div>
                <form onSubmit={handleCreateAllergy} className="mt-4 space-y-3">
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Allergen" value={allergyForm.allergen} onChange={(event) => setAllergyForm((current) => ({ ...current, allergen: event.target.value }))} required />
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Reaction" value={allergyForm.reaction} onChange={(event) => setAllergyForm((current) => ({ ...current, reaction: event.target.value }))} required />
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Severity" value={allergyForm.severity} onChange={(event) => setAllergyForm((current) => ({ ...current, severity: event.target.value }))} required />
                  <button type="submit" disabled={isCreatingAllergy || !patient} className="inline-flex items-center gap-2 rounded-md bg-rose-600 px-3 py-2 text-sm font-semibold text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:bg-zinc-400">
                    <PlusCircle className="h-4 w-4" />
                    {isCreatingAllergy ? "Saving..." : "Add allergy"}
                  </button>
                </form>
                {allergyItems.length === 0 ? <p className="mt-4 text-sm text-zinc-500">No allergies recorded.</p> : <ul className="mt-4 space-y-2 text-sm text-zinc-700">{allergyItems.map((item) => <li key={item.id} className="rounded-md bg-zinc-50 px-3 py-2">{item.allergen} — {item.severity}</li>)}</ul>}
              </div>

              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                  <Activity className="h-4 w-4 text-sky-700" />
                  Medications
                </div>
                <form onSubmit={handleCreateMedication} className="mt-4 space-y-3">
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Medication" value={medicationForm.medication_name} onChange={(event) => setMedicationForm((current) => ({ ...current, medication_name: event.target.value }))} required />
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Dosage" value={medicationForm.dosage} onChange={(event) => setMedicationForm((current) => ({ ...current, dosage: event.target.value }))} required />
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Frequency" value={medicationForm.frequency} onChange={(event) => setMedicationForm((current) => ({ ...current, frequency: event.target.value }))} required />
                  <input type="date" className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" value={medicationForm.start_date} onChange={(event) => setMedicationForm((current) => ({ ...current, start_date: event.target.value }))} required />
                  <textarea className="min-h-24 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Notes" value={medicationForm.notes} onChange={(event) => setMedicationForm((current) => ({ ...current, notes: event.target.value }))} />
                  <button type="submit" disabled={isCreatingMedication || !patient} className="inline-flex items-center gap-2 rounded-md bg-sky-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-sky-800 disabled:cursor-not-allowed disabled:bg-zinc-400">
                    <PlusCircle className="h-4 w-4" />
                    {isCreatingMedication ? "Saving..." : "Add medication"}
                  </button>
                </form>
                {medicationItems.length === 0 ? <p className="mt-4 text-sm text-zinc-500">No medications recorded.</p> : <ul className="mt-4 space-y-2 text-sm text-zinc-700">{medicationItems.map((item) => <li key={item.id} className="rounded-md bg-zinc-50 px-3 py-2">{item.medication_name} • {item.dosage}</li>)}</ul>}
              </div>

              <div className="rounded-lg border border-zinc-200 p-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                  <Stethoscope className="h-4 w-4 text-violet-700" />
                  Symptoms
                </div>
                <form onSubmit={handleCreateSymptom} className="mt-4 space-y-3">
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Symptom" value={symptomForm.symptom_name} onChange={(event) => setSymptomForm((current) => ({ ...current, symptom_name: event.target.value }))} required />
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Duration" value={symptomForm.duration} onChange={(event) => setSymptomForm((current) => ({ ...current, duration: event.target.value }))} required />
                  <input className="w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Severity" value={symptomForm.severity} onChange={(event) => setSymptomForm((current) => ({ ...current, severity: event.target.value }))} required />
                  <textarea className="min-h-24 w-full rounded-md border border-zinc-300 px-3 py-2 text-sm" placeholder="Notes" value={symptomForm.notes} onChange={(event) => setSymptomForm((current) => ({ ...current, notes: event.target.value }))} />
                  <button type="submit" disabled={isCreatingSymptom || !patient} className="inline-flex items-center gap-2 rounded-md bg-violet-700 px-3 py-2 text-sm font-semibold text-white transition hover:bg-violet-800 disabled:cursor-not-allowed disabled:bg-zinc-400">
                    <PlusCircle className="h-4 w-4" />
                    {isCreatingSymptom ? "Saving..." : "Add symptom"}
                  </button>
                </form>
                {symptomItems.length === 0 ? <p className="mt-4 text-sm text-zinc-500">No symptoms recorded.</p> : <ul className="mt-4 space-y-2 text-sm text-zinc-700">{symptomItems.map((item) => <li key={item.id} className="rounded-md bg-zinc-50 px-3 py-2">{item.symptom_name} — {item.severity}</li>)}</ul>}
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-zinc-950">Workflow status</h3>
                <p className="mt-1 text-sm text-zinc-600">{statusMessage}</p>
              </div>
              {patient ? (
                <div className="rounded-md bg-zinc-50 px-3 py-2 text-sm text-zinc-700">
                  <p className="font-semibold text-zinc-950">Active patient</p>
                  <p>{patient.first_name} {patient.last_name}</p>
                </div>
              ) : null}
            </div>

            {errorMessage ? <p className="mt-4 rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{errorMessage}</p> : null}

            {reportItems.length > 0 ? (
              <div className="mt-4 rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                <h4 className="text-sm font-semibold text-zinc-900">Uploaded reports</h4>
                <ul className="mt-3 space-y-2 text-sm text-zinc-700">
                  {reportItems.map((item) => <li key={item.id} className="rounded-md bg-white px-3 py-2">{item.original_filename}</li>)}
                </ul>
              </div>
            ) : null}
          </div>

          {analysis ? (
            <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-zinc-950">Analysis results</h3>
              <div className="mt-4 grid gap-4">
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <ShieldAlert className="h-4 w-4 text-amber-600" />
                    Summary
                  </div>
                  <p className="mt-3 text-sm leading-6 text-zinc-700">{analysis.summary || "No summary available."}</p>
                  <p className="mt-3 text-sm font-medium text-zinc-900">Confidence: {analysis.confidence}</p>
                </div>
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <Stethoscope className="h-4 w-4 text-rose-600" />
                    Possible diagnoses
                  </div>
                  <ul className="mt-3 space-y-2 text-sm text-zinc-700">
                    {analysis.possible_diagnoses.length > 0 ? analysis.possible_diagnoses.map((item) => <li key={item}>• {item}</li>) : <li>No diagnoses returned.</li>}
                  </ul>
                </div>
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    Medication warnings
                  </div>
                  <ul className="mt-3 space-y-2 text-sm text-zinc-700">
                    {analysis.medication_warnings.length > 0 ? analysis.medication_warnings.map((item) => <li key={item}>• {item}</li>) : <li>No medication warnings returned.</li>}
                  </ul>
                </div>
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <TestTube2 className="h-4 w-4 text-sky-700" />
                    Recommended tests
                  </div>
                  <ul className="mt-3 space-y-2 text-sm text-zinc-700">
                    {analysis.recommended_tests.length > 0 ? analysis.recommended_tests.map((item) => <li key={item}>• {item}</li>) : <li>No recommended tests returned.</li>}
                  </ul>
                </div>
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <ShieldAlert className="h-4 w-4 text-violet-700" />
                    Critical alerts
                  </div>
                  <ul className="mt-3 space-y-2 text-sm text-zinc-700">
                    {analysis.critical_alerts.length > 0 ? analysis.critical_alerts.map((item) => <li key={item}>• {item}</li>) : <li>No critical alerts returned.</li>}
                  </ul>
                </div>
                <div className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
                  <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                    <ClipboardList className="h-4 w-4 text-teal-700" />
                    Recommended specialist
                  </div>
                  <p className="mt-3 text-sm text-zinc-700">{analysis.recommended_specialist || "No specialist recommendation returned."}</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm text-sm text-zinc-600">
              No analysis results yet. Complete the workflow and run the analysis to see the report here.
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
