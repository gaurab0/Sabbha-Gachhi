import { useNavigate, useSearchParams } from "react-router-dom";
import ReportConcernForm from "../components/ReportConcernForm";
import { submitConcernReport } from "../api/registration";

export function ConcernRoute() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const reference = searchParams.get("ref") ?? "";

  return (
    <ReportConcernForm
      registrationId={reference}
      onSubmit={async (submission) => {
        await submitConcernReport({
          topic: submission.topic,
          description: submission.description,
          contactBack: submission.contactBack,
        });
      }}
      onBackToStatus={() => navigate(-1)}
    />
  );
}
