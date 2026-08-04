import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";

import { Layout } from "../components/Layout";
import { AuthProvider, useAuth } from "../contexts/AuthContext";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { RegisterPage } from "../pages/RegisterPage";
import { StatusPage } from "../pages/StatusPage";

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <div className="rounded-lg border border-zinc-200 bg-white p-6 text-sm text-zinc-600">Loading your session…</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AuthProvider>
        <Layout />
      </AuthProvider>
    ),
    children: [
      { index: true, element: <ProtectedRoute><HomePage /></ProtectedRoute> },
      { path: "status", element: <ProtectedRoute><StatusPage /></ProtectedRoute> },
      { path: "login", element: <LoginPage /> },
      { path: "register", element: <RegisterPage /> },
      { path: "*", element: <Navigate to="/login" replace /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}

