import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  BrainCircuit,
  Check,
  Eye,
  EyeOff,
  Info,
  LockKeyhole,
  Stethoscope,
} from "lucide-react";
import { Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { getApiErrorMessage } from "../api/client";
import { Button, Field, IntelligenceArt } from "./WorkspaceUI";

export function AuthPage({ mode }: { mode: "login" | "register" }) {
  const creating = mode === "register";
  const { login, register, isLoading } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Staff");
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (errorMessage) errorRef.current?.focus();
  }, [errorMessage]);
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    try {
      if (creating)
        await register(fullName.trim(), email.trim(), password, role);
      else await login(email.trim(), password);
    } catch (error) {
      setErrorMessage(
        getApiErrorMessage(
          error,
          creating ? "Unable to create an account." : "Unable to sign in.",
        ),
      );
    }
  }
  return (
    <div className="auth-page">
      <section className="auth-story">
        <div className="eyebrow">
          <span className="eyebrow-line" />
          CLINICAL INTELLIGENCE, CONNECTED
        </div>
        <h1>
          More context.
          <br />
          <span>A clearer perspective.</span>
        </h1>
        <p>
          One focused workspace for the information that shapes your next
          clinical decision.
        </p>
        <IntelligenceArt />
        <div className="auth-benefits">
          {[
            {
              icon: Stethoscope,
              title: "Patient information, together",
              detail: "Profiles, history, medications, and symptoms.",
            },
            {
              icon: BrainCircuit,
              title: "Intelligence that supports you",
              detail: "AI-assisted insights for qualified clinical review.",
            },
          ].map(({ icon: Icon, title, detail }) => (
            <div key={title}>
              <span className="auth-benefit-icon">
                <Icon size={21} />
              </span>
              <span>
                <strong>{title}</strong>
                <small>{detail}</small>
              </span>
            </div>
          ))}
        </div>
        <p className="auth-story-footer">
          Your expertise. A more connected perspective.
        </p>
      </section>
      <section className="auth-form-panel">
        <div className="auth-form-inner">
          <span className="auth-form-icon">
            <LockKeyhole size={23} />
          </span>
          <div className="eyebrow">WELCOME TO CLINICALAI</div>
          <h2>{creating ? "Create your account" : "Welcome back."}</h2>
          <p>
            {creating
              ? "Set up your access to the clinical workspace."
              : "Sign in to your clinical workspace."}
          </p>
          <form
            onSubmit={handleSubmit}
            aria-label={creating ? "Create account" : "Sign in"}
          >
            {errorMessage ? (
              <div
                ref={errorRef}
                tabIndex={-1}
                className="notice notice-error"
                role="alert"
              >
                <Info size={18} />
                <span>{errorMessage}</span>
              </div>
            ) : null}
            <fieldset disabled={isLoading}>
              {creating ? (
                <Field label="Full name">
                  <input
                    name="name"
                    autoComplete="name"
                    placeholder="Your full name"
                    maxLength={255}
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    required
                  />
                </Field>
              ) : null}
              <Field label="Email address">
                <input
                  name="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@hospital.org"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </Field>
              <div className="field">
                <label htmlFor="account-password">
                  Password <span className="required-mark">*</span>
                </label>
                <span className="password-input">
                  <input
                    id="account-password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={
                      creating ? "new-password" : "current-password"
                    }
                    placeholder={
                      creating ? "Create a password" : "Enter your password"
                    }
                    minLength={creating ? 8 : 1}
                    maxLength={255}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    className="icon-button"
                    type="button"
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    aria-pressed={showPassword}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </span>
                {creating ? <small>Use at least 8 characters.</small> : null}
              </div>
              {creating ? (
                <Field label="Clinical role">
                  <select
                    name="role"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                  >
                    <option>Staff</option>
                    <option>Doctor</option>
                    <option>Admin</option>
                  </select>
                </Field>
              ) : null}
              <Button type="submit" busy={isLoading} className="auth-submit">
                {isLoading
                  ? creating
                    ? "Creating account…"
                    : "Signing in…"
                  : creating
                    ? "Create account"
                    : "Sign in"}
                <ArrowRight size={17} />
              </Button>
            </fieldset>
          </form>
          <p className="auth-switch">
            {creating ? "Already have an account?" : "New to ClinicalAI?"}{" "}
            <Link to={creating ? "/login" : "/register"}>
              {creating ? "Sign in" : "Create an account"}
            </Link>
          </p>
          <div className="auth-form-note">
            <Check size={15} />
            <span>Clinical decision support. Your judgment comes first.</span>
          </div>
        </div>
      </section>
    </div>
  );
}
