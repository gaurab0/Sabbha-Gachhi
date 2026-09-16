import { useNavigate, useParams } from "react-router-dom";
import MatchProposalScreen from "../components/MatchProposalScreen";

export function ProposalRoute() {
  const navigate = useNavigate();
  const { matchId } = useParams<{ matchId: string }>();
  return (
    <MatchProposalScreen
      matchId={matchId ?? ""}
      onBackToStatus={() => navigate(-1)}
    />
  );
}
