import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Database,
  HardDrive,
  Info,
  RefreshCw,
  Server,
} from "lucide-react";
import { useState } from "react";
import { getApiErrorMessage, getHealthStatus } from "../api";
import { Badge, Button, CardHeading, Reveal } from "../components/WorkspaceUI";

type ConnectionState =
  "unchecked" | "checking" | "healthy" | "unknown" | "unavailable";
export function StatusPage() {
  const [state, setState] = useState<ConnectionState>("unchecked");
  const [detail, setDetail] = useState(
    "Run a health check to verify the backend connection.",
  );
  const [checkedAt, setCheckedAt] = useState<string | null>(null);
  const isLoading = state === "checking";
  async function checkBackendStatus() {
    setState("checking");
    try {
      const response = await getHealthStatus();
      if (!response.success)
        throw new Error(
          response.message || "Backend reported an unsuccessful check.",
        );
      const healthy = response.data?.status === "ok";
      setState(healthy ? "healthy" : "unknown");
      setDetail(
        response.message ||
          (healthy
            ? "Backend responded successfully."
            : "The backend responded without a confirmed healthy status."),
      );
    } catch (error) {
      setState("unavailable");
      setDetail(getApiErrorMessage(error, "Backend status check failed."));
    } finally {
      setCheckedAt(new Date().toLocaleTimeString());
    }
  }
  const label = {
    unchecked: "Not checked",
    checking: "Checking…",
    healthy: "Connection healthy",
    unknown: "Status unverified",
    unavailable: "Connection unavailable",
  }[state];
  const tone =
    state === "healthy"
      ? "success"
      : state === "unavailable"
        ? "error"
        : "warning";
  const panels = [
    {
      label: "Backend connection",
      icon: Server,
      value: label,
      detail: "Verified only by the latest health endpoint response.",
      badge:
        state === "healthy"
          ? "Verified healthy"
          : state === "unavailable"
            ? "Unavailable"
            : isLoading
              ? "Pending"
              : "Unverified",
      tone,
    },
    {
      label: "Database",
      icon: Database,
      value: "Managed by backend",
      detail: "The health endpoint does not test database connectivity.",
      badge: "Unverified",
      tone: "warning",
    },
    {
      label: "AI provider",
      icon: BrainCircuit,
      value: import.meta.env.VITE_AI_PROVIDER || "Not exposed",
      detail: import.meta.env.VITE_AI_PROVIDER
        ? "Frontend configuration hint; provider availability has not been tested."
        : "Provider configuration is managed by the backend and is not returned by this check.",
      badge: import.meta.env.VITE_AI_PROVIDER
        ? "Configured · unverified"
        : "Unverified",
      tone: "warning",
    },
    {
      label: "Upload storage",
      icon: HardDrive,
      value: import.meta.env.VITE_UPLOAD_FOLDER || "Managed by backend",
      detail:
        "Storage availability and write access are not tested by this endpoint.",
      badge: "Unverified",
      tone: "warning",
    },
    {
      label: "API version",
      icon: Activity,
      value: import.meta.env.VITE_API_VERSION || "Not reported",
      detail:
        "Only an explicitly configured frontend version is shown; the health response does not return a version.",
      badge: import.meta.env.VITE_API_VERSION
        ? "Configuration hint"
        : "Not reported",
      tone: "neutral",
    },
  ] as const;
  return (
    <div className="status-page">
      <div className="page-title-row">
        <div className="eyebrow">
          <span className="eyebrow-line" />
          WORKSPACE OPERATIONS
        </div>
        <Badge>System overview</Badge>
      </div>
      <div className="status-title">
        <div>
          <h1>
            Confidence starts
            <br className="mobile-break" /> with connection.
          </h1>
          <p>A transparent view of your backend and supporting services.</p>
        </div>
        <Button onClick={checkBackendStatus} busy={isLoading}>
          <RefreshCw size={16} />
          {isLoading ? "Checking backend…" : "Run health check"}
          <ArrowRight size={16} />
        </Button>
      </div>
      <section
        className={`connection-banner connection-${state}`}
        role="status"
        aria-live="polite"
        aria-busy={isLoading}
      >
        <span className="connection-symbol">
          <Server size={24} />
        </span>
        <div>
          <span className="small-caps">BACKEND STATUS</span>
          <h2>{label}</h2>
          <p>{detail}</p>
        </div>
        <div className="last-checked">
          <Badge tone={tone}>
            {state === "healthy"
              ? "Verified"
              : state === "unavailable"
                ? "Error"
                : "Unverified"}
          </Badge>
          <small>
            {checkedAt
              ? `Last checked at ${checkedAt}`
              : "No checks performed yet"}
          </small>
        </div>
      </section>
      <div className="health-grid">
        {panels.map(({ label, icon, value, detail, badge, tone }, i) => (
          <Reveal delay={i * 75} key={label}>
            <section className="panel health-panel">
              <CardHeading icon={icon} title={label} description="" />
              <strong className="health-value">{value}</strong>
              <p>{detail}</p>
              <Badge tone={tone}>{badge}</Badge>
            </section>
          </Reveal>
        ))}
      </div>
      <div className="notice status-explanation">
        <Info size={20} />
        <div>
          <strong>Configuration is not a health check.</strong>
          <p>
            This endpoint confirms backend responsiveness only. Database, AI
            provider, and upload storage remain unverified until dedicated
            service checks are available.
          </p>
        </div>
      </div>
    </div>
  );
}
