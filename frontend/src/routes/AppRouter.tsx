import {
  createBrowserRouter,
  Navigate,
  RouterProvider,
} from "react-router-dom";

import { Layout } from "../components/Layout";
import { HomePage } from "../pages/HomePage";
import { LLMSettingsPage } from "../pages/LLMSettingsPage";
import { StatusPage } from "../pages/StatusPage";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "status", element: <StatusPage /> },
      { path: "settings/llm", element: <LLMSettingsPage /> },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

export function AppRouter() {
  return <RouterProvider router={router} />;
}
