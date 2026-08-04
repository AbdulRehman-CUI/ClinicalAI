import { Activity, Home, LogOut, LogIn, UserPlus } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../contexts/AuthContext";

const navItems = [
  { to: "/", label: "Home", icon: Home },
  { to: "/status", label: "Status", icon: Activity },
];

export function Layout() {
  const { isAuthenticated, user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950">
      <header className="border-b border-zinc-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
          <div>
            <p className="text-sm font-medium text-teal-700">ClinicalAI</p>
            <h1 className="text-xl font-semibold">Project Foundation</h1>
          </div>
          <nav className="flex flex-wrap items-center gap-2" aria-label="Primary navigation">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  [
                    "inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium transition",
                    isActive
                      ? "bg-teal-700 text-white"
                      : "text-zinc-700 hover:bg-zinc-100 hover:text-zinc-950",
                  ].join(" ")
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                <span>{label}</span>
              </NavLink>
            ))}
            {isAuthenticated ? (
              <>
                <span className="rounded-full bg-zinc-100 px-3 py-2 text-sm text-zinc-700">
                  {user?.full_name || user?.email || "Signed in"}
                </span>
                <button className="inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100" onClick={logout} type="button">
                  <LogOut className="h-4 w-4" />
                  <span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <NavLink className="inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100" to="/login">
                  <LogIn className="h-4 w-4" />
                  <span>Login</span>
                </NavLink>
                <NavLink className="inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium text-zinc-700 transition hover:bg-zinc-100" to="/register">
                  <UserPlus className="h-4 w-4" />
                  <span>Register</span>
                </NavLink>
              </>
            )}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}

