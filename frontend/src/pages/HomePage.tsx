import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  BrainCircuit,
  Check,
  CheckCircle2,
  ChevronRight,
  ClipboardList,
  FileText,
  Info,
  Pill,
  RefreshCw,
  Stethoscope,
  UploadCloud,
  UserRound,
  X,
} from "lucide-react";
import {
  AnimatedBackground,
  Badge,
  Button,
  CardHeading,
  Field,
  NextButton,
  Reveal,
  SaveButton,
} from "../components/WorkspaceUI";
import { AnalysisResults } from "../components/AnalysisResults";
import toast from "react-hot-toast";

import { useAuth } from "../contexts/AuthContext";
import {
  analyzePatient,
  createAllergy,
  createMedicalHistory,
  createMedication,
  createPatient,
  updatePatient,
  createSymptom,
  getApiErrorMessage,
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
  first_name: "",
  last_name: "",
  age: "",
  biological_sex: "",
  blood_group: "",
  height_cm: "",
  weight_kg: "",
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
  severity: "",
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
  severity: "",
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
  const [uploadProgress, setUploadProgress] = useState<number | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [historyForm, setHistoryForm] =
    useState<HistoryFormState>(initialHistoryForm);
  const [allergyForm, setAllergyForm] =
    useState<AllergyFormState>(initialAllergyForm);
  const [medicationForm, setMedicationForm] = useState<MedicationFormState>(
    initialMedicationForm,
  );
  const [symptomForm, setSymptomForm] =
    useState<SymptomFormState>(initialSymptomForm);
  const [historyItems, setHistoryItems] = useState<MedicalHistoryRead[]>([]);
  const [allergyItems, setAllergyItems] = useState<AllergyRead[]>([]);
  const [medicationItems, setMedicationItems] = useState<MedicationRead[]>([]);
  const [symptomItems, setSymptomItems] = useState<SymptomRead[]>([]);
  const [reportItems, setReportItems] = useState<MedicalReportRead[]>([]);
  const [statusMessage, setStatusMessage] = useState(
    "Create a patient profile, add relevant clinical context, upload a report, and run the AI workflow.",
  );
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreatingPatient, setIsCreatingPatient] = useState(false);
  const [isCreatingHistory, setIsCreatingHistory] = useState(false);
  const [isCreatingAllergy, setIsCreatingAllergy] = useState(false);
  const [isCreatingMedication, setIsCreatingMedication] = useState(false);
  const [isCreatingSymptom, setIsCreatingSymptom] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const [stage, setStage] = useState(0);
  const [editingPatient, setEditingPatient] = useState(false);
  const [analysisStale, setAnalysisStale] = useState(false);
  const errorRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const resetDialog = useRef<HTMLDialogElement>(null);
  const stageHeading = useRef<HTMLHeadingElement>(null);
  const canAnalyze =
    Boolean(patient) && (symptomItems.length > 0 || reportItems.length > 0);
  const busy =
    isCreatingPatient ||
    isCreatingHistory ||
    isCreatingAllergy ||
    isCreatingMedication ||
    isCreatingSymptom ||
    isUploading ||
    isAnalyzing;
  const contextCount = [
    historyItems,
    allergyItems,
    medicationItems,
    symptomItems,
  ].filter((items) => items.length > 0).length;
  useEffect(() => {
    if (errorMessage) errorRef.current?.focus();
  }, [errorMessage]);
  function goToStage(next: number) {
    setStage(next);
    requestAnimationFrame(() =>
      stageHeading.current?.focus({ preventScroll: true }),
    );
  }

  const canUseAi = user?.role === "Doctor" || user?.role === "Admin";

  function updatePatientField(field: keyof PatientFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function resetWorkflow() {
    resetDialog.current?.close();
    setStage(0);
    setEditingPatient(false);
    setAnalysisStale(false);
    if (fileRef.current) fileRef.current.value = "";
    setForm(initialPatientForm);
    setPatient(null);
    setAnalysis(null);
    setSelectedFile(null);
    setUploadProgress(null);
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
    setStatusMessage(
      "Workflow reset. Create a new patient profile to begin again.",
    );
    toast.success("Workflow reset.");
  }

  async function handleCreatePatient(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    setStatusMessage(
      editingPatient ? "Updating patient record…" : "Creating patient record…",
    );

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

    if (
      !/^[A-Za-zÀ-ÿ' -]+$/.test(trimmedFirstName) ||
      !/^[A-Za-zÀ-ÿ' -]+$/.test(trimmedLastName)
    ) {
      const message =
        "Names may only contain letters, spaces, apostrophes, or hyphens.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!Number.isInteger(age) || age < 1 || age > 120) {
      const message =
        "Age must be a whole number between 1 and 120, as required by the patient API.";
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
        pregnancy_status:
          form.biological_sex === "Female"
            ? form.pregnancy_status || "Unknown"
            : null,
      };

      const response =
        editingPatient && patient
          ? await updatePatient(patient.id, payload)
          : await createPatient(payload);
      if (!response.success || !response.data) {
        throw new Error(
          response.message || "The backend did not return a patient.",
        );
      }

      setPatient(response.data);
      setEditingPatient(false);
      setAnalysisStale(true);
      goToStage(1);
      setStatusMessage(
        editingPatient
          ? "Patient profile updated."
          : "Patient created. Add clinical context to continue.",
      );
      toast.success(
        response.message ||
          (editingPatient
            ? "Patient profile updated."
            : "Patient created successfully."),
      );
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

    setErrorMessage(null);
    setIsCreatingHistory(true);
    try {
      const response = await createMedicalHistory(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(response.message || "The record could not be created.");
      }
      const item = response.data;
      setHistoryItems((items) => [...items, item]);
      setAnalysisStale(true);
      setHistoryForm(initialHistoryForm);
      setStatusMessage("Medical history record added.");
      toast.success(response.message || "Medical history record added.");
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        "Unable to add medical history.",
      );
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

    setErrorMessage(null);
    setIsCreatingAllergy(true);
    try {
      const response = await createAllergy(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(
          response.message || "The allergy could not be created.",
        );
      }
      const item = response.data;
      setAllergyItems((items) => [...items, item]);
      setAnalysisStale(true);
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

  async function handleCreateMedication(
    event: React.FormEvent<HTMLFormElement>,
  ) {
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

    if (
      !payload.medication_name ||
      !payload.dosage ||
      !payload.frequency ||
      !payload.start_date
    ) {
      setErrorMessage(
        "Medication name, dosage, frequency, and start date are required.",
      );
      return;
    }

    setErrorMessage(null);
    setIsCreatingMedication(true);
    try {
      const response = await createMedication(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(
          response.message || "The medication could not be created.",
        );
      }
      const item = response.data;
      setMedicationItems((items) => [...items, item]);
      setAnalysisStale(true);
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

    setErrorMessage(null);
    setIsCreatingSymptom(true);
    try {
      const response = await createSymptom(patient.id, payload);
      if (!response.success || !response.data) {
        throw new Error(
          response.message || "The symptom could not be created.",
        );
      }
      const item = response.data;
      setSymptomItems((items) => [...items, item]);
      setAnalysisStale(true);
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
      const message =
        "Unsupported file type. Please use PDF, DOCX, TXT, JPG, JPEG, or PNG.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    setErrorMessage(null);
    setStatusMessage("Uploading report...");
    setIsUploading(true);
    setUploadProgress(null);

    try {
      const response = await uploadReport(patient.id, selectedFile, (percent) =>
        setUploadProgress(percent),
      );
      if (!response.success || !response.data) {
        throw new Error(
          response.message || "The report upload did not complete.",
        );
      }
      const report = response.data;
      setReportItems((items) => [...items, report]);
      setAnalysisStale(true);
      setSelectedFile(null);
      if (fileRef.current) fileRef.current.value = "";
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
    if (!canUseAi) {
      setErrorMessage("AI analysis requires Doctor or Admin access.");
      return;
    }
    if (!patient) {
      const message = "Create a patient before running the analysis.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    if (!canAnalyze) {
      const message =
        "Add at least one symptom or upload a report before running analysis.";
      setErrorMessage(message);
      toast.error(message);
      return;
    }

    setErrorMessage(null);
    setStatusMessage(
      "Preparing clinical context and running the AI workflow...",
    );
    setIsAnalyzing(true);

    try {
      const response = await analyzePatient(patient.id);
      if (!response.success || !response.data) {
        throw new Error(
          response.message || "The analysis could not be completed.",
        );
      }
      setAnalysis(response.data);
      setAnalysisStale(false);
      setStatusMessage("Analysis completed successfully.");
      toast.success(response.message || "Analysis completed successfully.");
    } catch (error) {
      const message = getApiErrorMessage(
        error,
        "The AI workflow could not be completed.",
      );
      setErrorMessage(message);
      toast.error(message);
    } finally {
      setIsAnalyzing(false);
    }
  }

  function handleFileSelection(file: File | null) {
    if (isUploading || isAnalyzing) return;
    setErrorMessage(null);
    if (
      file &&
      !allowedFileTypes.includes(
        file.name.split(".").pop()?.toUpperCase() ?? "",
      )
    ) {
      setErrorMessage(
        "Unsupported file type. Please use PDF, DOCX, TXT, JPG, JPEG, or PNG.",
      );
      if (fileRef.current) fileRef.current.value = "";
      return;
    }
    setSelectedFile(file);
    setUploadProgress(null);
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragActive(false);
    const file = event.dataTransfer.files?.[0] ?? null;
    handleFileSelection(file);
  }

  const stages = [
    {
      title: "Patient profile",
      detail: patient ? "Profile saved" : "Start with the essentials",
      icon: UserRound,
      complete: Boolean(patient),
    },
    {
      title: "Clinical context",
      detail: `${contextCount} of 4 sections recorded`,
      icon: ClipboardList,
      complete: contextCount > 0,
    },
    {
      title: "Medical reports",
      detail: reportItems.length
        ? `${reportItems.length} report${reportItems.length === 1 ? "" : "s"} uploaded`
        : "Add supporting documents",
      icon: FileText,
      complete: reportItems.length > 0,
    },
    {
      title: "AI analysis",
      detail: analysis
        ? analysisStale
          ? "Context updated · rerun"
          : "Analysis available"
        : "Bring the picture together",
      icon: BrainCircuit,
      complete: Boolean(analysis) && !analysisStale,
    },
  ];

  return (
    <div className="workspace-page">
      <AnimatedBackground />
      <div className="page-title-row">
        <div className="eyebrow">
          <span className="eyebrow-line" />
          YOUR CLINICAL WORKSPACE
        </div>
        <Button
          type="button"
          variant="secondary"
          disabled={busy}
          onClick={() => resetDialog.current?.showModal()}
        >
          <RefreshCw size={14} />
          New patient
        </Button>
      </div>
      <div className="workspace-hero">
        <div>
          <h1>
            A clearer picture.
            <br />
            <span>Better-informed care.</span>
          </h1>
          <p>
            From patient context to clinical insight.
            <br className="mobile-break" /> Every detail, connected in one
            workspace.
          </p>
        </div>
        <div className="hero-caption">
          <span className="hero-caption-mark">
            <BrainCircuit size={21} />
          </span>
          <span>
            Clinical precision.
            <br />
            <strong>Intelligent support.</strong>
          </span>
        </div>
      </div>
      <nav className="workflow-stepper" aria-label="Clinical workflow stages">
        {stages.map(({ title, detail, icon: Icon, complete }, index) => (
          <button
            key={title}
            type="button"
            aria-current={stage === index ? "step" : undefined}
            className={`workflow-step ${stage === index ? "step-active" : ""} ${complete ? "step-complete" : ""}`}
            onClick={() => goToStage(index)}
          >
            <span className="step-icon">
              {complete ? <Check size={18} /> : <Icon size={18} />}
            </span>
            <span className="step-copy">
              <small>0{index + 1}</small>
              <strong>{title}</strong>
              <span>{detail}</span>
            </span>
            {index < 3 ? (
              <ChevronRight size={15} className="step-chevron" />
            ) : null}
          </button>
        ))}
      </nav>
      <div className="workspace-columns">
        <div className="workspace-main">
          <div className="section-intro">
            <h2 ref={stageHeading} tabIndex={-1}>
              {stages[stage].title}
            </h2>
            <span>STEP 0{stage + 1} / 04</span>
          </div>
          {errorMessage ? (
            <div
              ref={errorRef}
              tabIndex={-1}
              role="alert"
              className="notice notice-error"
            >
              <AlertTriangle size={18} />
              <span>{errorMessage}</span>
              <button
                type="button"
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setErrorMessage(null)}
              >
                <X size={16} />
              </button>
            </div>
          ) : null}
          {stage === 0 ? (
            <Reveal>
              <section className="panel profile-panel">
                <CardHeading
                  icon={UserRound}
                  title={
                    patient
                      ? "Patient details"
                      : "Let's start with your patient"
                  }
                  description={
                    patient
                      ? "Review the saved patient record before continuing."
                      : "A few essentials to establish the clinical context."
                  }
                  trailing={
                    <Badge tone={patient ? "success" : "neutral"}>
                      {patient ? "Saved" : "New patient"}
                    </Badge>
                  }
                />
                {patient && !editingPatient ? (
                  <>
                    <div className="patient-detail-grid">
                      {[
                        [
                          "Patient",
                          `${patient.first_name} ${patient.last_name}`,
                        ],
                        ["Record ID", `#${patient.id}`],
                        ["Age", `${patient.age} years`],
                        ["Biological sex", patient.biological_sex],
                        ["Blood group", patient.blood_group],
                        ["Height", `${patient.height_cm} cm`],
                        ["Weight", `${patient.weight_kg} kg`],
                        ...(patient.pregnancy_status
                          ? [["Pregnancy status", patient.pregnancy_status]]
                          : []),
                      ].map(([label, value]) => (
                        <div key={label}>
                          <span>{label}</span>
                          <strong>{value}</strong>
                        </div>
                      ))}
                    </div>
                    <div className="panel-actions">
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => setEditingPatient(true)}
                      >
                        Edit patient details
                      </Button>
                      <NextButton onClick={() => goToStage(1)}>
                        Clinical context
                      </NextButton>
                    </div>
                  </>
                ) : (
                  <form
                    onSubmit={handleCreatePatient}
                    aria-label="Patient profile"
                  >
                    <fieldset disabled={isCreatingPatient || isAnalyzing}>
                      <div className="form-grid">
                        <Field label="First name">
                          <input
                            autoComplete="off"
                            placeholder="Enter first name"
                            maxLength={100}
                            pattern="[A-Za-zÀ-ÿ' \-]+"
                            title="Letters, spaces, apostrophes, or hyphens"
                            value={form.first_name}
                            onChange={(e) =>
                              updatePatientField("first_name", e.target.value)
                            }
                            required
                          />
                        </Field>
                        <Field label="Last name">
                          <input
                            autoComplete="off"
                            placeholder="Enter last name"
                            maxLength={100}
                            pattern="[A-Za-zÀ-ÿ' \-]+"
                            title="Letters, spaces, apostrophes, or hyphens"
                            value={form.last_name}
                            onChange={(e) =>
                              updatePatientField("last_name", e.target.value)
                            }
                            required
                          />
                        </Field>
                        <Field label="Age" hint="Years">
                          <input
                            type="number"
                            placeholder="Enter age"
                            min="1"
                            max="120"
                            value={form.age}
                            onChange={(e) =>
                              updatePatientField("age", e.target.value)
                            }
                            required
                          />
                        </Field>
                        <Field label="Biological sex">
                          <select
                            value={form.biological_sex}
                            onChange={(e) => {
                              updatePatientField(
                                "biological_sex",
                                e.target.value,
                              );
                              if (e.target.value !== "Female")
                                updatePatientField(
                                  "pregnancy_status",
                                  "Unknown",
                                );
                            }}
                            required
                          >
                            <option value="" disabled>
                              Select sex
                            </option>
                            <option>Male</option>
                            <option>Female</option>
                          </select>
                        </Field>
                        <Field label="Blood group">
                          <select
                            value={form.blood_group}
                            onChange={(e) =>
                              updatePatientField("blood_group", e.target.value)
                            }
                            required
                          >
                            <option value="" disabled>
                              Select blood group
                            </option>
                            {[
                              "A+",
                              "A-",
                              "B+",
                              "B-",
                              "AB+",
                              "AB-",
                              "O+",
                              "O-",
                              "Unknown",
                            ].map((v) => (
                              <option key={v}>{v}</option>
                            ))}
                          </select>
                        </Field>
                        <Field label="Pregnancy status" optional>
                          <select
                            value={form.pregnancy_status}
                            disabled={form.biological_sex !== "Female"}
                            onChange={(e) =>
                              updatePatientField(
                                "pregnancy_status",
                                e.target.value,
                              )
                            }
                          >
                            <option>Unknown</option>
                            <option>Pregnant</option>
                            <option>Not Pregnant</option>
                          </select>
                        </Field>
                        <Field label="Height" hint="Centimeters (cm)">
                          <input
                            type="number"
                            placeholder="Enter height"
                            min="30"
                            max="250"
                            step="0.1"
                            value={form.height_cm}
                            onChange={(e) =>
                              updatePatientField("height_cm", e.target.value)
                            }
                            required
                          />
                        </Field>
                        <Field label="Weight" hint="Kilograms (kg)">
                          <input
                            type="number"
                            placeholder="Enter weight"
                            min="1"
                            max="400"
                            step="0.1"
                            value={form.weight_kg}
                            onChange={(e) =>
                              updatePatientField("weight_kg", e.target.value)
                            }
                            required
                          />
                        </Field>
                      </div>
                      <div className="form-footnote">
                        <Info size={14} />
                        <span>
                          Required fields are marked with an asterisk. Enter
                          verified patient information.
                        </span>
                      </div>
                      <div className="panel-actions">
                        <span className="subtle-text">
                          {editingPatient
                            ? "Updates apply to this patient record."
                            : "Your next step: clinical context"}
                        </span>
                        <Button type="submit" busy={isCreatingPatient}>
                          {isCreatingPatient
                            ? "Saving patient…"
                            : editingPatient
                              ? "Save patient details"
                              : "Create patient"}
                          <ArrowRight size={16} />
                        </Button>
                      </div>
                    </fieldset>
                  </form>
                )}
              </section>
            </Reveal>
          ) : null}

          {stage === 1 ? (
            <>
              <p className="section-description">
                Add what you know. Each section saves independently; record only
                verified information.
              </p>
              {!patient ? (
                <div className="notice">
                  <Info size={18} />
                  <span>
                    Create a patient profile before adding clinical records.
                  </span>
                  <Button variant="secondary" onClick={() => goToStage(0)}>
                    Create profile
                  </Button>
                </div>
              ) : null}
              <div className="context-grid">
                <Reveal>
                  <section className="panel context-card">
                    <CardHeading
                      icon={ClipboardList}
                      title="Medical history"
                      description="Conditions and relevant background."
                      trailing={
                        <span className="count-tag">{historyItems.length}</span>
                      }
                    />
                    <form
                      onSubmit={handleCreateHistory}
                      aria-label="Medical history"
                    >
                      <fieldset
                        disabled={!patient || isCreatingHistory || isAnalyzing}
                      >
                        <Field label="Condition">
                          <input
                            placeholder="Condition name"
                            value={historyForm.condition_name}
                            onChange={(e) =>
                              setHistoryForm((f) => ({
                                ...f,
                                condition_name: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Diagnosis date" optional>
                          <input
                            type="date"
                            value={historyForm.diagnosis_date}
                            onChange={(e) =>
                              setHistoryForm((f) => ({
                                ...f,
                                diagnosis_date: e.target.value,
                              }))
                            }
                          />
                        </Field>
                        <Field label="Clinical notes">
                          <textarea
                            rows={2}
                            placeholder="Relevant history and context"
                            value={historyForm.notes}
                            onChange={(e) =>
                              setHistoryForm((f) => ({
                                ...f,
                                notes: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <SaveButton
                          busy={isCreatingHistory}
                          disabled={!patient || isAnalyzing}
                        >
                          Add history
                        </SaveButton>
                      </fieldset>
                    </form>
                    <div className="record-list">
                      {historyItems.length ? (
                        historyItems.map((item) => (
                          <article className="record-item" key={item.id}>
                            <CheckCircle2 size={15} />
                            <div>
                              <strong>{item.condition_name}</strong>
                              {item.diagnosis_date ? (
                                <small>Diagnosed {item.diagnosis_date}</small>
                              ) : null}
                              <p>{item.notes}</p>
                            </div>
                          </article>
                        ))
                      ) : (
                        <p className="empty-caption">
                          No history recorded yet.
                        </p>
                      )}
                    </div>
                  </section>
                </Reveal>
                <Reveal delay={75}>
                  <section className="panel context-card">
                    <CardHeading
                      icon={AlertTriangle}
                      title="Allergies"
                      description="Known allergens and reactions."
                      trailing={
                        <span className="count-tag">{allergyItems.length}</span>
                      }
                    />
                    <form onSubmit={handleCreateAllergy} aria-label="Allergies">
                      <fieldset
                        disabled={!patient || isCreatingAllergy || isAnalyzing}
                      >
                        <Field label="Allergen">
                          <input
                            placeholder="Allergen name"
                            value={allergyForm.allergen}
                            onChange={(e) =>
                              setAllergyForm((f) => ({
                                ...f,
                                allergen: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Reaction">
                          <input
                            placeholder="Observed reaction"
                            value={allergyForm.reaction}
                            onChange={(e) =>
                              setAllergyForm((f) => ({
                                ...f,
                                reaction: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Severity">
                          <input
                            placeholder="Describe severity"
                            value={allergyForm.severity}
                            onChange={(e) =>
                              setAllergyForm((f) => ({
                                ...f,
                                severity: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <SaveButton
                          busy={isCreatingAllergy}
                          disabled={!patient || isAnalyzing}
                        >
                          Add allergy
                        </SaveButton>
                      </fieldset>
                    </form>
                    <div className="record-list">
                      {allergyItems.length ? (
                        allergyItems.map((item) => (
                          <article
                            className="record-item allergy-record"
                            key={item.id}
                          >
                            <AlertTriangle size={15} />
                            <div>
                              <strong>{item.allergen}</strong>
                              <p>
                                {item.reaction} · {item.severity}
                              </p>
                            </div>
                          </article>
                        ))
                      ) : (
                        <p className="empty-caption">
                          No allergies recorded. Allergy status is unconfirmed.
                        </p>
                      )}
                    </div>
                  </section>
                </Reveal>
                <Reveal delay={75}>
                  <section className="panel context-card">
                    <CardHeading
                      icon={Pill}
                      title="Medications"
                      description="Current treatment and dosage."
                      trailing={
                        <span className="count-tag">
                          {medicationItems.length}
                        </span>
                      }
                    />
                    <form
                      onSubmit={handleCreateMedication}
                      aria-label="Medications"
                    >
                      <fieldset
                        disabled={
                          !patient || isCreatingMedication || isAnalyzing
                        }
                      >
                        <Field label="Medication">
                          <input
                            placeholder="Medication name"
                            value={medicationForm.medication_name}
                            onChange={(e) =>
                              setMedicationForm((f) => ({
                                ...f,
                                medication_name: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <div className="form-grid compact">
                          <Field label="Dosage">
                            <input
                              placeholder="Dose and unit"
                              value={medicationForm.dosage}
                              onChange={(e) =>
                                setMedicationForm((f) => ({
                                  ...f,
                                  dosage: e.target.value,
                                }))
                              }
                              required
                            />
                          </Field>
                          <Field label="Frequency">
                            <input
                              placeholder="Dosing frequency"
                              value={medicationForm.frequency}
                              onChange={(e) =>
                                setMedicationForm((f) => ({
                                  ...f,
                                  frequency: e.target.value,
                                }))
                              }
                              required
                            />
                          </Field>
                        </div>
                        <Field label="Start date">
                          <input
                            type="date"
                            value={medicationForm.start_date}
                            onChange={(e) =>
                              setMedicationForm((f) => ({
                                ...f,
                                start_date: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Notes" optional>
                          <textarea
                            rows={2}
                            value={medicationForm.notes}
                            onChange={(e) =>
                              setMedicationForm((f) => ({
                                ...f,
                                notes: e.target.value,
                              }))
                            }
                          />
                        </Field>
                        <SaveButton
                          busy={isCreatingMedication}
                          disabled={!patient || isAnalyzing}
                        >
                          Add medication
                        </SaveButton>
                      </fieldset>
                    </form>
                    <div className="record-list">
                      {medicationItems.length ? (
                        medicationItems.map((item) => (
                          <article className="record-item" key={item.id}>
                            <Pill size={15} />
                            <div>
                              <strong>{item.medication_name}</strong>
                              <p>
                                {item.dosage} · {item.frequency}
                              </p>
                              <small>Started {item.start_date}</small>
                              {item.notes ? <p>{item.notes}</p> : null}
                            </div>
                          </article>
                        ))
                      ) : (
                        <p className="empty-caption">
                          No medications recorded yet.
                        </p>
                      )}
                    </div>
                  </section>
                </Reveal>
                <Reveal delay={150}>
                  <section className="panel context-card">
                    <CardHeading
                      icon={Stethoscope}
                      title="Symptoms"
                      description="Presenting concerns and duration."
                      trailing={
                        <span className="count-tag">{symptomItems.length}</span>
                      }
                    />
                    <form onSubmit={handleCreateSymptom} aria-label="Symptoms">
                      <fieldset
                        disabled={!patient || isCreatingSymptom || isAnalyzing}
                      >
                        <Field label="Symptom">
                          <input
                            placeholder="Presenting symptom"
                            value={symptomForm.symptom_name}
                            onChange={(e) =>
                              setSymptomForm((f) => ({
                                ...f,
                                symptom_name: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Duration">
                          <input
                            placeholder="Duration and onset"
                            value={symptomForm.duration}
                            onChange={(e) =>
                              setSymptomForm((f) => ({
                                ...f,
                                duration: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Severity">
                          <input
                            placeholder="Describe severity"
                            value={symptomForm.severity}
                            onChange={(e) =>
                              setSymptomForm((f) => ({
                                ...f,
                                severity: e.target.value,
                              }))
                            }
                            required
                          />
                        </Field>
                        <Field label="Notes" optional>
                          <textarea
                            rows={2}
                            value={symptomForm.notes}
                            onChange={(e) =>
                              setSymptomForm((f) => ({
                                ...f,
                                notes: e.target.value,
                              }))
                            }
                          />
                        </Field>
                        <SaveButton
                          busy={isCreatingSymptom}
                          disabled={!patient || isAnalyzing}
                        >
                          Add symptom
                        </SaveButton>
                      </fieldset>
                    </form>
                    <div className="record-list">
                      {symptomItems.length ? (
                        symptomItems.map((item) => (
                          <article className="record-item" key={item.id}>
                            <Stethoscope size={15} />
                            <div>
                              <strong>{item.symptom_name}</strong>
                              <p>
                                {item.duration} · {item.severity}
                              </p>
                              {item.notes ? <p>{item.notes}</p> : null}
                            </div>
                          </article>
                        ))
                      ) : (
                        <p className="empty-caption">
                          No symptoms recorded yet.
                        </p>
                      )}
                    </div>
                  </section>
                </Reveal>
              </div>
              <div className="stage-actions">
                <NextButton onClick={() => goToStage(2)}>
                  Medical reports
                </NextButton>
                <NextButton onClick={() => goToStage(3)}>
                  Review for analysis
                </NextButton>
              </div>
            </>
          ) : null}

          {stage === 2 ? (
            <Reveal>
              <section className="panel">
                <CardHeading
                  icon={FileText}
                  title="Supporting medical reports"
                  description="Connect source documents to the active patient."
                  trailing={<Badge>{reportItems.length} uploaded</Badge>}
                />
                {!patient ? (
                  <div className="notice">
                    <Info size={18} />
                    <span>Create a patient profile before uploading.</span>
                  </div>
                ) : null}
                <div
                  className={`upload-zone ${dragActive ? "drag-active" : ""} ${!patient || isUploading || isAnalyzing ? "upload-disabled" : ""}`}
                  onDragOver={(e) => {
                    e.preventDefault();
                    if (patient && !isUploading && !isAnalyzing)
                      setDragActive(true);
                  }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={(e) => {
                    if (!patient || isUploading || isAnalyzing) {
                      e.preventDefault();
                      setDragActive(false);
                      return;
                    }
                    handleDrop(e);
                  }}
                >
                  <span className="upload-icon">
                    <UploadCloud size={29} />
                  </span>
                  <h3>
                    {dragActive
                      ? "Drop your report here"
                      : "Drop a report to connect the details"}
                  </h3>
                  <p>
                    or{" "}
                    <label htmlFor="report-file" className="text-link">
                      browse your files
                    </label>
                  </p>
                  <input
                    ref={fileRef}
                    id="report-file"
                    type="file"
                    accept={acceptedFileExtensions}
                    disabled={!patient || isUploading || isAnalyzing}
                    onChange={(e) =>
                      handleFileSelection(e.target.files?.[0] ?? null)
                    }
                    aria-label="Choose medical report"
                  />
                  <small>PDF, DOCX, TXT, JPG, JPEG or PNG</small>
                  <small>File size limits are enforced by the backend.</small>
                </div>
                {selectedFile ? (
                  <div className="selected-file">
                    <FileText size={23} />
                    <div>
                      <strong>{selectedFile.name}</strong>
                      <small>
                        {new Intl.NumberFormat(undefined, {
                          maximumFractionDigits: 1,
                        }).format(selectedFile.size / 1024)}{" "}
                        KB · Ready to upload
                      </small>
                    </div>
                    <button
                      className="icon-button"
                      type="button"
                      aria-label="Remove selected file"
                      disabled={isUploading || isAnalyzing}
                      onClick={() => {
                        handleFileSelection(null);
                        if (fileRef.current) fileRef.current.value = "";
                      }}
                    >
                      <X size={17} />
                    </button>
                  </div>
                ) : null}
                {isUploading ? (
                  <div className="upload-progress" role="status">
                    <p>
                      {uploadProgress === 100
                        ? "File transferred. Waiting for server confirmation…"
                        : "Uploading report…"}
                      {uploadProgress !== null ? (
                        <span>{uploadProgress}% transferred</span>
                      ) : null}
                    </p>
                    <progress
                      max="100"
                      value={uploadProgress ?? undefined}
                      aria-label="File transfer progress"
                    />
                  </div>
                ) : null}
                <div className="panel-actions">
                  <span className="subtle-text">
                    Documents are attached to this patient.
                  </span>
                  <Button
                    type="button"
                    busy={isUploading}
                    disabled={!patient || !selectedFile || isAnalyzing}
                    onClick={handleUploadReport}
                  >
                    <UploadCloud size={16} />
                    {isUploading ? "Uploading…" : "Upload report"}
                  </Button>
                </div>
                <div className="uploaded-reports">
                  <h3>
                    Uploaded documents{" "}
                    <span className="count-tag">{reportItems.length}</span>
                  </h3>
                  {reportItems.length ? (
                    reportItems.map((report, i) => (
                      <Reveal key={report.id} delay={i * 65}>
                        <article className="document-card">
                          <span className="document-type">
                            {report.file_type}
                          </span>
                          <div>
                            <strong>{report.original_filename}</strong>
                            <small>
                              {new Date(
                                report.upload_timestamp,
                              ).toLocaleString()}
                            </small>
                          </div>
                          <Badge tone="success">Uploaded</Badge>
                        </article>
                      </Reveal>
                    ))
                  ) : (
                    <div className="empty-state">
                      <FileText size={26} />
                      <p>No reports uploaded yet.</p>
                      <small>
                        Reports are optional when symptoms are recorded.
                      </small>
                    </div>
                  )}
                </div>
                <div className="stage-actions">
                  <NextButton onClick={() => goToStage(3)}>
                    Review for analysis
                  </NextButton>
                </div>
              </section>
            </Reveal>
          ) : null}

          {stage === 3 ? (
            <section className="panel analysis-panel">
              <CardHeading
                icon={BrainCircuit}
                title="AI-assisted clinical analysis"
                description="Review the available context, then request decision support."
                trailing={
                  <Badge
                    tone={analysis && !analysisStale ? "success" : "neutral"}
                  >
                    {analysis && !analysisStale
                      ? "Result available"
                      : "Clinical review"}
                  </Badge>
                }
              />
              <div className="analysis-readiness">
                <h3>Patient readiness</h3>
                {[
                  [Boolean(patient), "Patient profile saved"],
                  [canAnalyze, "At least one symptom or uploaded report"],
                  [canUseAi, "Doctor or Admin access"],
                ].map(([ready, label]) => (
                  <div className="readiness-item" key={String(label)}>
                    {ready ? <CheckCircle2 size={17} /> : <Info size={17} />}
                    <span>{label}</span>
                    <small>{ready ? "Ready" : "Required"}</small>
                  </div>
                ))}
              </div>
              <p className="analysis-explainer">
                The analysis sends the saved patient profile, clinical records,
                and available report text to the configured AI provider. Review
                all returned findings against the source information.
              </p>
              <Button
                type="button"
                busy={isAnalyzing}
                disabled={!canAnalyze || !canUseAi || busy}
                onClick={handleAnalyzePatient}
              >
                <BrainCircuit size={18} />
                {isAnalyzing
                  ? "Analysis in progress…"
                  : analysis
                    ? "Run analysis again"
                    : "Run clinical analysis"}
                <ArrowRight size={16} />
              </Button>
              {!canUseAi ? (
                <p className="access-note">
                  Your {user?.role || "current"} role can record patient
                  information. AI analysis requires Doctor or Admin access.
                </p>
              ) : null}
              {isAnalyzing ? (
                <div className="processing-state" role="status">
                  <span className="processing-symbol">
                    <BrainCircuit size={28} />
                  </span>
                  <div>
                    <strong>Reviewing clinical information</strong>
                    <p>
                      Waiting for the AI service. Results appear after the
                      backend confirms completion.
                    </p>
                  </div>
                </div>
              ) : null}
              {analysis ? (
                <AnalysisResults analysis={analysis} stale={analysisStale} />
              ) : !isAnalyzing ? (
                <div className="empty-state analysis-empty">
                  <BrainCircuit size={34} />
                  <h3>Context first. Insights next.</h3>
                  <p>
                    Your analysis will appear here when the request completes.
                  </p>
                </div>
              ) : null}
              <div className="clinical-disclaimer">
                <Info size={16} />
                <p>
                  AI output is clinical decision support. It may be incomplete
                  or incorrect and requires review by a qualified clinician.
                </p>
              </div>
            </section>
          ) : null}
          <div className="workflow-status" role="status" aria-live="polite">
            <span className="status-line" />
            {statusMessage}
          </div>
        </div>
        <aside className="case-sidebar" aria-label="Current case summary">
          <Reveal delay={90}>
            <section className="panel case-summary">
              <div className="summary-header">
                <h2>At a glance</h2>
                <span className="small-caps">CURRENT CASE</span>
              </div>
              {patient ? (
                <div className="case-patient">
                  <span className="patient-avatar">
                    {patient.first_name[0]}
                    {patient.last_name[0]}
                  </span>
                  <div>
                    <strong>
                      {patient.first_name} {patient.last_name}
                    </strong>
                    <p>
                      Patient #{patient.id} · {patient.age} years ·{" "}
                      {patient.biological_sex}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="case-patient">
                  <span className="patient-avatar">
                    <UserRound size={23} />
                  </span>
                  <div>
                    <strong>No patient selected</strong>
                    <p>Create a profile to get started.</p>
                  </div>
                </div>
              )}
              <div className="case-checklist">
                {[
                  {
                    icon: UserRound,
                    label: "Patient profile",
                    value: patient ? "Saved" : "Not started",
                    saved: Boolean(patient),
                    index: 0,
                  },
                  {
                    icon: ClipboardList,
                    label: "Medical history",
                    value: `${historyItems.length} recorded`,
                    saved: historyItems.length > 0,
                    index: 1,
                  },
                  {
                    icon: AlertTriangle,
                    label: "Allergies",
                    value: allergyItems.length
                      ? `${allergyItems.length} recorded`
                      : "Unconfirmed",
                    saved: allergyItems.length > 0,
                    index: 1,
                  },
                  {
                    icon: Pill,
                    label: "Medications",
                    value: `${medicationItems.length} recorded`,
                    saved: medicationItems.length > 0,
                    index: 1,
                  },
                  {
                    icon: Stethoscope,
                    label: "Symptoms",
                    value: `${symptomItems.length} recorded`,
                    saved: symptomItems.length > 0,
                    index: 1,
                  },
                  {
                    icon: FileText,
                    label: "Medical reports",
                    value: `${reportItems.length} uploaded`,
                    saved: reportItems.length > 0,
                    index: 2,
                  },
                ].map(({ icon: Icon, label, value, saved, index }) => (
                  <button
                    key={label}
                    className="case-check-item"
                    type="button"
                    onClick={() => goToStage(index)}
                  >
                    <Icon size={16} />
                    <span>{label}</span>
                    <small className={saved ? "recorded" : ""}>{value}</small>
                  </button>
                ))}
              </div>
              <div className="case-summary-footer">
                <Info size={14} />
                <span>Only saved information is included in analysis.</span>
              </div>
            </section>
          </Reveal>
          <Reveal delay={165}>
            <section className="insight-card">
              <div className="insight-top">
                <span className="insight-icon">
                  <BrainCircuit size={22} />
                </span>
                <span className="small-caps">THE NEXT PERSPECTIVE</span>
              </div>
              <h2>Connect the clinical dots.</h2>
              <p>
                Turn patient context into a structured starting point for
                clinical review.
              </p>
              <div className="insight-readiness">
                <span
                  className={`readiness-dot ${canAnalyze ? "ready" : ""}`}
                />
                {canAnalyze
                  ? "Clinical information available"
                  : "Awaiting patient information"}
              </div>
              <Button
                type="button"
                variant="secondary"
                onClick={() => goToStage(3)}
              >
                Review for analysis
                <ArrowRight size={16} />
              </Button>
            </section>
          </Reveal>
          <div className="care-note">
            <Stethoscope size={17} />
            <p>
              Your expertise leads.
              <br />
              <span>ClinicalAI supports the next step.</span>
            </p>
          </div>
        </aside>
      </div>
      <dialog
        ref={resetDialog}
        className="confirmation-dialog"
        aria-labelledby="reset-title"
        aria-describedby="reset-description"
      >
        <span className="warning-icon">
          <RefreshCw size={24} />
        </span>
        <h2 id="reset-title">Start a new patient workspace?</h2>
        <p id="reset-description">
          This clears the current workspace and any unsaved entries. Saved
          records remain on the server. The workspace does not currently offer a
          way to reopen this case.
        </p>
        <div className="dialog-actions">
          <Button
            variant="secondary"
            autoFocus
            onClick={() => resetDialog.current?.close()}
          >
            Keep working
          </Button>
          <Button variant="danger" onClick={resetWorkflow}>
            Start new patient
          </Button>
        </div>
      </dialog>
    </div>
  );
}
