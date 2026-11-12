import { useEffect, useState, type FormEvent } from "react";
import { KeyRound } from "lucide-react";
import { getApiErrorMessage } from "../api/client";
import {
  getLLMProviders, getLLMStatus, providerNames, removeLLM, saveLLM, testLLM,
  type LLMStatus, type Provider,
} from "../api/llm";
import { Badge, Button, CardHeading, Field } from "../components/WorkspaceUI";

export function LLMSettingsPage() {
  const [providers, setProviders] = useState<Record<Provider, string[]> | null>(null);
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
    let active = true;
    Promise.all([getLLMProviders(), getLLMStatus()]).then(([options, saved]) => {
      if (!active) return;
      const selectedProvider = saved?.provider ?? "openai";
      const available = options?.[selectedProvider] ?? [];
      setProviders(options);
      setConfig(saved);
      setProvider(selectedProvider);
      setModel(saved?.model && available.includes(saved.model) ? saved.model : (available[0] ?? ""));
      setRemember(saved?.remember ?? false);
    }).catch((failure: unknown) => {
      if (active) setError(getApiErrorMessage(failure, "Unable to load LLM settings."));
    });
    return () => { active = false; };
  }, []);

  const hasSavedKey = config?.provider === provider && config.has_api_key;
  const canSubmit = Boolean(model && (apiKey.trim() || hasSavedKey));

  async function submit(action: "test" | "save" | "remove") {
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
      setError(getApiErrorMessage(failure, "Unable to update LLM settings."));
    } finally {
      setBusy(false);
    }
  }

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (canSubmit && !busy) void submit("save");
  }

  return (
    <section className="panel llm-settings">
      <CardHeading
        icon={KeyRound}
        title="LLM configuration"
        description="Choose the provider and model for your workspace."
        trailing={<Badge tone={config?.configured ? "success" : "warning"}>
          {config?.configured ? "LLM Configured" : "LLM Not Configured"}
        </Badge>}
      />
      <form onSubmit={save} aria-label="LLM configuration">
        <Field label="Provider">
          <select value={provider} disabled={busy || !providers} onChange={(event) => {
            const next = event.target.value as Provider;
            setProvider(next);
            setModel(providers?.[next]?.[0] ?? "");
            setApiKey("");
            setShowKey(false);
            setMessage("");
          }}>
            <option value="openai">OpenAI</option>
            <option value="gemini">Google Gemini</option>
          </select>
        </Field>
        <Field label="Model" hint="ClinicalAI supports the listed models. Test the selected model to check access for your key.">
          <select value={model} disabled={busy || !providers} onChange={(event) => {
            setModel(event.target.value);
            setMessage("");
          }}>
            {!model && <option value="">Choose a model</option>}
            {providers?.[provider]?.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </Field>
        <div className="llm-key-row">
          <Field label="API key" optional={Boolean(hasSavedKey)} hint={hasSavedKey ? "A key is saved. Leave blank to reuse it." : undefined}>
            <input
              type={showKey ? "text" : "password"} value={apiKey}
              autoComplete="off" spellCheck={false} maxLength={4096} disabled={busy}
              onChange={(event) => { setApiKey(event.target.value); setMessage(""); }}
            />
          </Field>
          <Button type="button" variant="secondary" disabled={busy} onClick={() => setShowKey(!showKey)}>
            {showKey ? "Hide key" : "Show key"}
          </Button>
        </div>
        <label className="llm-remember">
          <input type="checkbox" checked={remember} disabled={busy} onChange={(event) => setRemember(event.target.checked)} />
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
          <Button type="button" variant="secondary" disabled={!canSubmit || busy} onClick={() => void submit("test")}>
            Test connection
          </Button>
          <Button type="submit" busy={busy} disabled={!canSubmit}>Save configuration</Button>
          <Button type="button" variant="danger" disabled={!config?.has_api_key || busy} onClick={() => void submit("remove")}>
            Remove configuration
          </Button>
        </div>
      </form>
    </section>
  );
}
