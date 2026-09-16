import { useNavigate, useParams } from "react-router-dom";
import StatusPage from "../components/StatusPage";

export function StatusRoute() {
  const navigate = useNavigate();
  const { reference } = useParams<{ reference: string }>();

  return (
    <StatusPage
      reference={reference ?? ""}
      onOpenMatchProposal={(matchId) => navigate(`/status/match/${matchId}`)}
      onReportConcern={() => navigate(`/concern?ref=${reference}`)}
    />
  );
}
