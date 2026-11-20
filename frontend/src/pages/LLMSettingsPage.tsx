import { useEffect, useRef, useState, type FormEvent } from "react";
import { KeyRound } from "lucide-react";
import { getApiErrorMessage } from "../api/client";
import { getLLMProviders, getLLMStatus, listLLM, activateLLM, discoverLLM, providerNames, removeLLM, saveLLM, testLLM, type LLMStatus, type Provider, type ProviderCatalog } from "../api/llm";
import { Badge, Button, CardHeading, Field } from "../components/WorkspaceUI";

export function LLMSettingsPage() {
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [entries, setEntries] = useState<LLMStatus[]>([]);
  const [active, setActive] = useState<LLMStatus | null>(null);
  const [id, setId] = useState<string>();
  const [provider, setProvider] = useState<Provider>("openai");
  const [model, setModel] = useState("");
  const [endpoint, setEndpoint] = useState("");
  const [key, setKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [workspaceError, setWorkspaceError] = useState("");
  const [catalogError, setCatalogError] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [models, setModels] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(false);
  const discovery = useRef<AbortController>();
  const mounted = useRef(true);
  const edited = useRef(false);
  const selected = entries.find((entry) => entry.id === id);
  const savedKey = selected?.configured && selected.provider === provider && (selected.base_url ?? "") === endpoint;
  const valid = /^[A-Za-z0-9][A-Za-z0-9._:/+@-]{0,254}$/.test(model);
  const canSubmit = ready && valid && Boolean(key.trim() || savedKey) && !busy && (provider !== "custom" || !!endpoint);
  const options = models ?? catalog?.[provider] ?? [];

  function invalidateDiscovery(preserveCatalogError = false) {
    discovery.current?.abort(); setModels(null); setLoading(false); setMessage(""); if (!preserveCatalogError) setCatalogError(""); edited.current = true;
  }
  function choose(entry?: LLMStatus, preserveCatalogError = false) {
    invalidateDiscovery(preserveCatalogError); setId(entry?.id); setProvider(entry?.provider ?? "openai");
    setModel(entry?.model ?? ""); setEndpoint(entry?.base_url ?? "");
    setRemember(entry?.remember ?? false); setKey(""); setShowKey(false);
  }
  async function refresh(initial = false, signal?: AbortSignal) {
    setWorkspaceError("");
    try {
      const [status, list] = await Promise.all([getLLMStatus(signal), listLLM(signal)]);
      if (!mounted.current || signal?.aborted) return;
      setEntries(list ?? []); setActive(status); setReady(true);
      if (initial && !edited.current && status.id) choose(status, true);
    } catch (failure) { if (mounted.current && !signal?.aborted) { setReady(false); setWorkspaceError(getApiErrorMessage(failure)); } }
  }
  async function loadCatalog(signal?: AbortSignal) {
    try { const result = await getLLMProviders(signal); if (mounted.current && !signal?.aborted) { setCatalog(result); setCatalogError(""); } }
    catch (failure) { if (mounted.current && !signal?.aborted) setCatalogError(getApiErrorMessage(failure)); }
  }
  useEffect(() => {
    mounted.current = true; const request = new AbortController(); void loadCatalog(request.signal); void refresh(true, request.signal);
    return () => { mounted.current = false; request.abort(); discovery.current?.abort(); };
  }, []);
  const selection = { id, provider, model, api_key: key.trim() || undefined, base_url: provider === "custom" ? endpoint : undefined };
  async function discover() {
    discovery.current?.abort(); const request = new AbortController(); discovery.current = request;
    setLoading(true); setCatalogError("");
    try {
      const {model: _model, ...input} = selection;
      const found = await discoverLLM(input, request.signal);
      if (!request.signal.aborted) { setModels(found); if (!found.length) setCatalogError("No compatible models found. Enter a model ID manually or retry."); }
    } catch (failure) { if (!request.signal.aborted) setCatalogError(getApiErrorMessage(failure)); }
    finally { if (!request.signal.aborted) setLoading(false); }
  }
  async function act(action: "test" | "save" | "activate" | "remove") {
    setBusy(true); setError(""); setMessage("");
    try {
      if (action === "test") { await testLLM(selection); setMessage("Connection tested. The provider accepted this model request."); }
      if (action === "save") { const result = await saveLLM({...selection, remember}); setId(result.id); setKey(""); setShowKey(false); setMessage("LLM configuration saved."); }
      if (action === "activate" && id) { await activateLLM(id); setMessage("Active configuration selected."); }
      if (action === "remove" && id) { await removeLLM(id); choose(); setMessage("Saved LLM configuration removed."); }
      await refresh();
    } catch (failure) { setError(getApiErrorMessage(failure)); }
    finally { setBusy(false); }
  }
  function save(event: FormEvent) { event.preventDefault(); if (canSubmit) void act("save"); }
  return <section className="panel llm-settings">
    <CardHeading icon={KeyRound} title="LLM configuration" description="Choose the provider and model for your workspace." trailing={<Badge tone={active?.configured ? "success" : "warning"}>{ready ? active?.configured ? "LLM Configured" : "LLM Not Configured" : workspaceError ? "Workspace unavailable" : "Loading workspace"}</Badge>} />
    <p className="field-hint">Active: {active?.configured ? `${active.provider} · ${active.model}` : "None available. Activate a tested configuration before analysis."}</p>
    <Field label="Saved configurations"><select value={id ?? ""} disabled={busy} onChange={(event) => choose(entries.find((entry) => entry.id === event.target.value))}>
      <option value="">Add configuration</option>{entries.map((entry) => <option key={entry.id} value={entry.id}>{entry.active ? "Active · " : ""}{entry.provider} · {entry.model}{entry.configured ? "" : " · Expired / unavailable"}</option>)}
    </select></Field>
    <Button disabled={busy || !selected?.configured || selected.active} onClick={() => void act("activate")}>Use for analysis</Button>
    <form onSubmit={save} aria-label="LLM configuration">
      <Field label="Provider"><select value={provider} disabled={busy} onChange={(event) => { choose(); setProvider(event.target.value as Provider); }}>
        {Object.entries(providerNames).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
      </select></Field>
      {provider === "custom" && <Field label="Endpoint base URL" hint="OpenAI-compatible Chat Completions (/chat/completions). HTTPS, port 443; enter this endpoint's own key."><input value={endpoint} disabled={busy} onChange={(event) => { invalidateDiscovery(); setEndpoint(event.target.value); setKey(""); }} placeholder="https://provider.example/v1" /></Field>}
      <Field label="Model" hint={models === null ? "Fallback catalog; availability for your account is unverified. Manual model IDs are supported." : "Discovered using your key. A connection test is still required."}>
        <select value={options.includes(model) ? model : ""} disabled={busy || !options.length} onChange={(event) => { edited.current = true; setModel(event.target.value); setMessage(""); }}>
          <option value="">{!catalog ? "Loading models…" : options.length ? "Choose a model" : "No models available"}</option>{options.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </Field>
      <Field label="Manual model ID"><input value={model} maxLength={255} disabled={busy} onChange={(event) => { edited.current = true; setModel(event.target.value); setMessage(""); }} /></Field>
      <div className="llm-key-row"><Field label="API key" optional={!!savedKey} hint={savedKey ? "A key is saved. Leave blank to reuse it." : "Enter your key before discovering models."}>
        <input type={showKey ? "text" : "password"} value={key} autoComplete="off" spellCheck={false} maxLength={4096} disabled={busy} onChange={(event) => { invalidateDiscovery(); setKey(event.target.value); }} />
      </Field><Button type="button" variant="secondary" onClick={() => setShowKey(!showKey)}>{showKey ? "Hide key" : "Show key"}</Button></div>
      <Button type="button" variant="secondary" disabled={!ready || busy || loading || !(key.trim() || savedKey)} onClick={() => void discover()}>{loading ? "Loading models…" : "Load models with key"}</Button>
      {catalogError && <div className="llm-actions"><p role="alert">Unable to load available models. {catalogError}</p><Button type="button" variant="secondary" onClick={() => void (catalog && (key.trim() || savedKey) ? discover() : loadCatalog())}>Retry models</Button></div>}
      {workspaceError && <div className="llm-actions"><p role="alert">Unable to open your guest workspace. {workspaceError}</p><Button type="button" variant="secondary" onClick={() => void refresh()}>Retry workspace</Button></div>}
      <label className="llm-remember"><input type="checkbox" checked={remember} disabled={busy} onChange={(event) => { edited.current = true; setRemember(event.target.checked); }} />Remember this encrypted key for up to 7 days</label>
      <p className="field-hint">Session keys expire after 8 hours or when the browser session ends. Enter a model and key to test or save. Additional configurations require explicit activation.</p>
      <p className="analysis-explainer">Your provider may charge for connection tests, saving a configuration, and analysis. Analysis sends clinical information to the active provider. Use a provider approved for your data.</p>
      {error && <p className="access-note" role="alert">{error}</p>}{message && <p role="status">{message}</p>}
      <div className="llm-actions"><Button type="button" variant="secondary" disabled={!canSubmit} onClick={() => void act("test")}>Test connection</Button><Button type="submit" busy={busy} disabled={!canSubmit}>Save configuration</Button><Button type="button" variant="danger" disabled={busy || !id} onClick={() => void act("remove")}>Remove configuration</Button></div>
    </form>
  </section>;
}
