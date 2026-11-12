import { useEffect, useRef, useState, type FormEvent } from "react";
import { isAxiosError } from "axios";
import { KeyRound } from "lucide-react";
import { getApiErrorMessage } from "../api/client";
import {
  getLLMProviders, getLLMStatus, providerNames, removeLLM, saveLLM, testLLM,
  type LLMStatus, type Provider, type ProviderCatalog,
} from "../api/llm";
import { Badge, Button, CardHeading, Field } from "../components/WorkspaceUI";

export function LLMSettingsPage() {
  const [providers, setProviders] = useState<ProviderCatalog | null>(null);
  const [catalogError, setCatalogError] = useState("");
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [workspaceReady, setWorkspaceReady] = useState(false);
  const [workspaceError, setWorkspaceError] = useState("");
  const [workspaceAttempt, setWorkspaceAttempt] = useState(0);
  const draftEdited = useRef(false);
  const [config, setConfig] = useState<LLMStatus | null>(null);
  const [provider, setProvider] = useState<Provider>("openai");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const request = new AbortController();
    getLLMProviders(request.signal).then((options) => {
      if (!request.signal.aborted) setProviders(options);
    }).catch((failure: unknown) => {
      if (!request.signal.aborted) setCatalogError(getApiErrorMessage(failure));
    });
    return () => request.abort();
  }, [catalogAttempt]);

  useEffect(() => {
    const request = new AbortController();
    getLLMStatus(request.signal).then((saved) => {
      if (request.signal.aborted) return;
      setConfig(saved);
      if (!draftEdited.current) {
        setProvider(saved.provider ?? "openai");
        setModel(saved.model ?? "");
        setRemember(saved.remember ?? false);
      }
      setWorkspaceReady(true);
    }).catch((failure: unknown) => {
      if (!request.signal.aborted) setWorkspaceError(getApiErrorMessage(failure));
    });
    return () => request.abort();
  }, [workspaceAttempt]);

  const models = providers?.[provider] ?? [];
  const validModel = models.includes(model);
  const hasSavedKey = config?.provider === provider && config.has_api_key;
  const hasEnteredKey = Boolean(apiKey.trim());
  const canTest = workspaceReady && validModel && hasEnteredKey && !busy;
  const canSave = workspaceReady && validModel && (hasEnteredKey || hasSavedKey) && !busy;
  const canRemove = workspaceReady && Boolean(config?.has_api_key) && !busy;

  async function submit(action: "test" | "save" | "remove") {
    if (!(action === "test" ? canTest : action === "save" ? canSave : canRemove)) return;
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const selection = { provider, model, api_key: apiKey.trim() || undefined };
      if (action === "test") {
        await testLLM(selection);
        setMessage("Connection tested. The provider accepted this model request.");
      } else if (action === "save") {
        setConfig(await saveLLM({ ...selection, remember }));
        setApiKey("");
        setShowKey(false);
        setMessage("LLM configuration saved.");
      } else {
        await removeLLM();
        setConfig(null);
        setApiKey("");
        setShowKey(false);
        setRemember(false);
        setMessage("Saved LLM configuration removed.");
      }
    } catch (failure) {
      const message = getApiErrorMessage(failure, "Unable to update LLM settings.");
      if (isAxiosError(failure) && failure.response?.status === 401) {
        setWorkspaceReady(false);
        setWorkspaceError(message);
      } else {
        setError(message);
      }
    } finally {
      setBusy(false);
    }
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void submit("save");
  }

  return (
    <section className="panel llm-settings">
      <CardHeading
        icon={KeyRound}
        title="LLM configuration"
        description="Choose the provider and model for your workspace."
        trailing={<Badge tone={config?.configured ? "success" : "warning"}>
          {workspaceReady
            ? config?.configured ? "LLM Configured" : "LLM Not Configured"
            : workspaceError ? "Workspace unavailable" : "Loading workspace"}
        </Badge>}
      />
      <form onSubmit={save} aria-label="LLM configuration">
        <Field label="Provider">
          <select value={provider} disabled={busy} onChange={(event) => {
            draftEdited.current = true;
            const next = event.target.value as Provider;
            setProvider(next);
            setModel("");
            setApiKey("");
            setShowKey(false);
            setMessage("");
          }}>
            <option value="openai">OpenAI</option>
            <option value="gemini">Google Gemini</option>
          </select>
        </Field>
        <Field label="Model" hint="ClinicalAI supports the listed models. Test the selected model to check access for your key.">
          <select value={validModel ? model : ""} disabled={busy || models.length === 0} onChange={(event) => {
            draftEdited.current = true;
            setModel(event.target.value);
            setMessage("");
          }}>
            <option value="">{catalogError ? "Models unavailable" : !providers ? "Loading models…" : models.length ? "Choose a model" : "No models available"}</option>
            {models.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </Field>
        {catalogError && (
          <div className="llm-actions">
            <p className="access-note" role="alert">Unable to load available models. {catalogError}</p>
            <Button type="button" variant="secondary" onClick={() => {
              setCatalogError("");
              setCatalogAttempt((attempt) => attempt + 1);
            }}>Retry models</Button>
          </div>
        )}
        {workspaceError && (
          <div className="llm-actions">
            <p className="access-note" role="alert">Unable to open your guest workspace. {workspaceError}</p>
            <Button type="button" variant="secondary" onClick={() => {
              setWorkspaceError("");
              setWorkspaceAttempt((attempt) => attempt + 1);
            }}>Retry workspace</Button>
          </div>
        )}
        <div className="llm-key-row">
          <Field label="API key" optional={Boolean(hasSavedKey)} hint={hasSavedKey ? "A key is saved. Leave blank to reuse it." : undefined}>
            <input
              type={showKey ? "text" : "password"} value={apiKey}
              autoComplete="off" spellCheck={false} maxLength={4096} disabled={busy}
              onChange={(event) => { draftEdited.current = true; setApiKey(event.target.value); setMessage(""); }}
            />
          </Field>
          <Button type="button" variant="secondary" disabled={busy} onClick={() => setShowKey(!showKey)}>
            {showKey ? "Hide key" : "Show key"}
          </Button>
        </div>
        <label className="llm-remember">
          <input type="checkbox" checked={remember} disabled={busy} onChange={(event) => {
            draftEdited.current = true;
            setRemember(event.target.checked);
          }} />
          Remember this encrypted key for up to 7 days
        </label>
        <p className="field-hint">Session keys expire after 8 hours or when the browser session ends.</p>
        {config?.configured && config.provider && (
          <p className="field-hint">Saved and tested · {providerNames[config.provider]} · {config.model}</p>
        )}
        <p className="analysis-explainer">
          Your provider may charge for connection tests, saving a configuration, and analysis.
          Analysis sends clinical information to that provider. Use a provider approved for your data.
        </p>
        {error && <p className="access-note" role="alert">{error}</p>}
        {message && <p role="status">{message}</p>}
        <div className="llm-actions">
          <Button type="button" variant="secondary" disabled={!canTest} onClick={() => void submit("test")}>
            Test connection
          </Button>
          <Button type="submit" busy={busy} disabled={!canSave}>Save configuration</Button>
          <Button type="button" variant="danger" disabled={!canRemove} onClick={() => void submit("remove")}>
            Remove configuration
          </Button>
        </div>
      </form>
    </section>
  );
}
