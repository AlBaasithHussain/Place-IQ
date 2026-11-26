import { BrowserRouter, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import DashboardPage from "./pages/DashboardPage";
import InterviewResultsPage from "./pages/InterviewResultsPage";
import InterviewSessionPage from "./pages/InterviewSessionPage";
import InterviewSetupPage from "./pages/InterviewSetupPage";
import JobDetailPage from "./pages/JobDetailPage";
import JobsPage from "./pages/JobsPage";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import MatchResultPage from "./pages/MatchResultPage";
import MatchSetupPage from "./pages/MatchSetupPage";
import NotFoundPage from "./pages/NotFoundPage";
import ProfilePage from "./pages/ProfilePage";
import RegisterPage from "./pages/RegisterPage";
import ResumeDetailPage from "./pages/ResumeDetailPage";
import ResumesPage from "./pages/ResumesPage";
import RoadmapPage from "./pages/RoadmapPage";
import RoadmapSetupPage from "./pages/RoadmapSetupPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/resumes"
            element={
              <ProtectedRoute>
                <ResumesPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/resumes/:id"
            element={
              <ProtectedRoute>
                <ResumeDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/jobs"
            element={
              <ProtectedRoute>
                <JobsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/jobs/:id"
            element={
              <ProtectedRoute>
                <JobDetailPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/new"
            element={
              <ProtectedRoute>
                <MatchSetupPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/analysis/:id"
            element={
              <ProtectedRoute>
                <MatchResultPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/roadmaps/new"
            element={
              <ProtectedRoute>
                <RoadmapSetupPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/roadmaps/:id"
            element={
              <ProtectedRoute>
                <RoadmapPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/interviews/start"
            element={
              <ProtectedRoute>
                <InterviewSetupPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/interviews/:id/results"
            element={
              <ProtectedRoute>
                <InterviewResultsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/interviews/:id"
            element={
              <ProtectedRoute>
                <InterviewSessionPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
