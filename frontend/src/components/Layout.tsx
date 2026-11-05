import { useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowUpRight,
  ChevronRight,
  LayoutDashboard,
  LogIn,
  LogOut,
  Menu,
  Stethoscope,
  UserPlus,
  X,
} from "lucide-react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { Brand } from "./WorkspaceUI";

export function Layout() {
  const { isAuthenticated, user, logout } = useAuth();
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const main = useRef<HTMLElement>(null);
  const previousPath = useRef(pathname);
  useEffect(() => {
    setMenuOpen(false);
    if (previousPath.current !== pathname) {
      main.current?.focus({ preventScroll: true });
      window.scrollTo(0, 0);
      previousPath.current = pathname;
    }
  }, [pathname]);
  useEffect(() => {
    if (!menuOpen) return;
    function close(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        document.getElementById("menu-toggle")?.focus();
      }
    }
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [menuOpen]);
  const authPage = pathname === "/login" || pathname === "/register";
  return (
    <div className={`app-shell ${authPage ? "auth-shell" : ""}`}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="app-header">
        <NavLink
          to={isAuthenticated ? "/" : "/login"}
          aria-label="ClinicalAI home"
          className="brand-link"
        >
          <Brand />
        </NavLink>
        <div className="header-divider" />
        <span className="workspace-label">
          Clinical workspace
          <ChevronRight size={13} />
          <span>
            {authPage
              ? "Account access"
              : pathname === "/status"
                ? "System health"
                : "Patient intake"}
          </span>
        </span>
        <div className="header-account">
          {isAuthenticated ? (
            <>
              <span className="avatar">
                {(user?.full_name || user?.email || "C")
                  .slice(0, 1)
                  .toUpperCase()}
              </span>
              <span className="account-name">
                {user?.full_name || user?.email}
                <small>{user?.role}</small>
              </span>
              <button
                className="icon-button logout-button"
                type="button"
                onClick={logout}
                aria-label="Log out"
                title="Log out"
              >
                <LogOut size={18} />
                <span>Log out</span>
              </button>
            </>
          ) : (
            <span className="header-tag">
              <Stethoscope size={16} />
              Built for clinical clarity
            </span>
          )}
        </div>
        <button
          id="menu-toggle"
          type="button"
          className="icon-button menu-toggle"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          aria-label={menuOpen ? "Close navigation" : "Open navigation"}
        >
          {menuOpen ? <X size={21} /> : <Menu size={21} />}
        </button>
      </header>
      <aside
        id="primary-navigation"
        className={`sidebar ${menuOpen ? "sidebar-open" : ""}`}
      >
        <div className="sidebar-section-label">WORKSPACE</div>
        <nav aria-label="Primary navigation">
          {(isAuthenticated
            ? [
                { to: "/", label: "Patient workspace", icon: LayoutDashboard },
                { to: "/status", label: "System health", icon: Activity },
              ]
            : [
                { to: "/login", label: "Sign in", icon: LogIn },
                { to: "/register", label: "Create account", icon: UserPlus },
              ]
          ).map(({ to, label, icon: Icon }) => (
            <NavLink
              end
              key={to}
              to={to}
              className={({ isActive }) =>
                `nav-item ${isActive ? "nav-active" : ""}`
              }
            >
              <Icon size={18} />
              <span>{label}</span>
              <ChevronRight className="nav-arrow" size={14} />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="icon-tile">
            <Stethoscope size={20} />
          </span>
          <h3>Care, with context.</h3>
          <p>
            Bring patient information together for better-informed clinical
            decisions.
          </p>
          <span className="sidebar-note-caption">
            AI-assisted decision support
            <ArrowUpRight size={13} />
          </span>
        </div>
        <div className="sidebar-footer">
          <span className="mini-brand">
            C<span>+</span>
          </span>
          <span>
            ClinicalAI<small>Clarity at every step.</small>
          </span>
        </div>
      </aside>
      {menuOpen ? (
        <button
          type="button"
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      ) : null}
      <main ref={main} id="main-content" tabIndex={-1} className="main-content">
        <div key={pathname} className="route-transition">
          <Outlet />
        </div>
        <footer className="page-footer">
          <span>ClinicalAI · Clinical decision support</span>
          <span>Designed to support your clinical judgment.</span>
        </footer>
      </main>
    </div>
  );
}
