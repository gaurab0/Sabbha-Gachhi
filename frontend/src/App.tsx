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
import { StatusLookup } from "./routes/StatusLookup";
import { StatusRoute } from "./routes/StatusRoute";

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
        <Route path="/register/*" element={<RegistrationFlow />} />
        <Route path="/status" element={<StatusLookup />} />
        <Route path="/status/:reference" element={<StatusRoute />} />
        <Route path="/status/match/:matchId" element={<ProposalRoute />} />
        <Route path="/support" element={<SupportPage />} />
        <Route path="/concern" element={<ConcernRoute />} />
      </Route>
      <Route path="/panjikar/*" element={<PanjikarPage />} />
    </Routes>
  );
}
