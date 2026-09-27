import { Route, Routes } from "react-router-dom";
import AboutPage from "./components/AboutPage";
import SupportPage from "./components/Donation";
import SaurathMelaPage from "./components/Mela";
import PanjikarPage from "./components/PanjikarPage";
import RegistrationFlow from "./components/RegistrationFlow";
import { Cta } from "./components/landing-page/Cta";
import { Hero } from "./components/landing-page/Hero";
import { HowItWorks } from "./components/landing-page/HowItWorks";
import { Privacy } from "./components/landing-page/Privacy";
import { Quotes } from "./components/landing-page/Quotes";
import { Standards } from "./components/landing-page/Standards";
import { Tradition } from "./components/landing-page/Tradition";
import { ConcernRoute } from "./routes/ConcernRoute";
import { ProposalRoute } from "./routes/ProposalRoute";
import { PublicLayout } from "./routes/PublicLayout";
import { StatusRoute } from "./routes/StatusRoute";
import TokenCheckPage from "./components/TokenCheckPage";
import { LoginPage } from "./components/LoginPage";
import { SignupPage } from "./components/SignupPage";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { AdminRoute } from "./components/AdminRoute";

function LandingPage() {
  return (
    <>
      <Hero />
      <Tradition />
      <Quotes />
      <HowItWorks />
      <Standards />
      <Privacy />
      <Cta />
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route element={<PublicLayout />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/about" element={<AboutPage />} />
        <Route path="/mela" element={<SaurathMelaPage />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/status-check" element={<TokenCheckPage />} />
        <Route
          path="/register/*"
          element={
            <ProtectedRoute>
              <RegistrationFlow />
            </ProtectedRoute>
          }
        />
        <Route
          path="/status"
          element={
            <ProtectedRoute>
              <StatusRoute />
            </ProtectedRoute>
          }
        />
        <Route
          path="/status/:reference"
          element={
            <ProtectedRoute>
              <StatusRoute />
            </ProtectedRoute>
          }
        />
        <Route
          path="/status/match/:matchId"
          element={
            <ProtectedRoute>
              <ProposalRoute />
            </ProtectedRoute>
          }
        />
        <Route
          path="/concern"
          element={
            <ProtectedRoute>
              <ConcernRoute />
            </ProtectedRoute>
          }
        />
      </Route>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/signup" element={<SignupPage />} />
      <Route path="/panjikar/*" element={<AdminRoute><PanjikarPage /></AdminRoute>} />
    </Routes>
  );
}
