import { Activity, Database, HardDrive, Server, Sparkles } from "lucide-react";
import { useState } from "react";
import toast from "react-hot-toast";

import { getApiErrorMessage, getHealthStatus } from "../api";

type HealthPanel = {
  label: string;
  value: string;
  detail: string;
  isHealthy: boolean;
  icon: typeof Activity;
};

export function StatusPage() {
  const [status, setStatus] = useState<string>("Not checked");
  const [detail, setDetail] = useState<string>("Run the health check to verify the backend connection.");
  const [panels, setPanels] = useState<HealthPanel[]>([
    { label: "Backend", value: "Pending", detail: "Awaiting health check", isHealthy: false, icon: Server },
    { label: "Database", value: "SQLite", detail: "Configured for local persistence", isHealthy: true, icon: Database },
    { label: "AI Provider", value: import.meta.env.VITE_AI_PROVIDER || "OpenAI", detail: "Configured via frontend environment", isHealthy: true, icon: Sparkles },
    { label: "Upload Folder", value: import.meta.env.VITE_UPLOAD_FOLDER || "backend/data/uploads", detail: "Managed by backend storage settings", isHealthy: true, icon: HardDrive },
    { label: "API Version", value: import.meta.env.VITE_API_VERSION || "0.1.0", detail: "Backend API version", isHealthy: true, icon: Activity },
  ]);
  const [isLoading, setIsLoading] = useState(false);

  async function checkBackendStatus() {
    setIsLoading(true);
    try {
      const response = await getHealthStatus();
      const nextStatus = response.data?.status ?? "Unknown";
      setStatus(nextStatus);
      setDetail(response.message || "Backend connection is healthy.");
      setPanels((current) => current.map((panel) => (panel.label === "Backend" ? { ...panel, value: nextStatus, detail: response.message || "Backend responded successfully", isHealthy: nextStatus === "ok" } : panel)));
      toast.success(response.message || "Backend connection is healthy.");
    } catch (error) {
      const message = getApiErrorMessage(error, "Backend status check failed.");
      setStatus("Unavailable");
      setDetail(message);
      setPanels((current) => current.map((panel) => (panel.label === "Backend" ? { ...panel, value: "Unavailable", detail: message, isHealthy: false } : panel)));
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="space-y-6 rounded-xl border border-zinc-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-zinc-950">System health dashboard</h2>
          <p className="mt-2 text-sm text-zinc-600">Monitor the backend and supporting services for the clinical workflow.</p>
        </div>
        <button
          type="button"
          onClick={checkBackendStatus}
          disabled={isLoading}
          className="h-10 rounded-md bg-teal-700 px-4 text-sm font-medium text-white transition hover:bg-teal-800 disabled:cursor-not-allowed disabled:bg-zinc-400"
        >
          {isLoading ? "Checking" : "Check status"}
        </button>
      </div>

      <div className="mt-6 rounded-lg border border-zinc-200 bg-zinc-50 p-4">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-600">
          <span className={`inline-flex h-3 w-3 rounded-full ${status === "ok" ? "bg-emerald-500" : "bg-amber-500"}`} />
          <span>Current backend status</span>
        </div>
        <p className="mt-2 text-lg font-semibold text-zinc-950">{status}</p>
        <p className="mt-1 text-sm text-zinc-600">{detail}</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {panels.map((panel) => {
          const Icon = panel.icon;
          return (
            <div key={panel.label} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-900">
                  <Icon className="h-4 w-4 text-teal-700" />
                  {panel.label}
                </div>
                <span className={`inline-flex h-2.5 w-2.5 rounded-full ${panel.isHealthy ? "bg-emerald-500" : "bg-amber-500"}`} />
              </div>
              <p className="mt-4 text-lg font-semibold text-zinc-950">{panel.value}</p>
              <p className="mt-2 text-sm text-zinc-600">{panel.detail}</p>
            </div>
          );
        })}
      </div>
    </section>
  );
}

