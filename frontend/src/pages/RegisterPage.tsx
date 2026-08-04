import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";
import { getApiErrorMessage } from "../api/client";

export function RegisterPage() {
  const { register, isLoading } = useAuth();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("Staff");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrorMessage(null);
    try {
      await register(fullName, email, password, role);
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error, "Unable to create an account."));
    }
  }

  return (
    <div className="mx-auto flex max-w-md flex-col gap-6 rounded-xl border border-zinc-200 bg-white p-8 shadow-sm">
      <div>
        <p className="text-sm font-medium text-teal-700">ClinicalAI</p>
        <h2 className="text-2xl font-semibold">Create an account</h2>
        <p className="mt-2 text-sm text-zinc-600">Register to use the secure patient workspace.</p>
      </div>
      <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
        {errorMessage ? <div className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{errorMessage}</div> : null}
        <label className="flex flex-col gap-1 text-sm font-medium text-zinc-700">
          Full name
          <input className="rounded-md border border-zinc-300 px-3 py-2" type="text" value={fullName} onChange={(event) => setFullName(event.target.value)} required />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-zinc-700">
          Email
          <input className="rounded-md border border-zinc-300 px-3 py-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-zinc-700">
          Password
          <input className="rounded-md border border-zinc-300 px-3 py-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        </label>
        <label className="flex flex-col gap-1 text-sm font-medium text-zinc-700">
          Role
          <select className="rounded-md border border-zinc-300 px-3 py-2" value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="Staff">Staff</option>
            <option value="Doctor">Doctor</option>
            <option value="Admin">Admin</option>
          </select>
        </label>
        <button className="rounded-md bg-teal-700 px-4 py-2 font-medium text-white disabled:cursor-not-allowed disabled:bg-teal-400" disabled={isLoading} type="submit">
          {isLoading ? "Creating account..." : "Create account"}
        </button>
      </form>
      <p className="text-sm text-zinc-600">
        Already have an account? <Link className="font-medium text-teal-700" to="/login">Sign in</Link>
      </p>
    </div>
  );
}
