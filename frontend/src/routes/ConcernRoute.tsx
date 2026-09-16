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
          registration_reference_text: submission.registrationId,
          topic: submission.topic,
          description: submission.description,
          contact_back: submission.contactBack,
        });
      }}
      onBackToStatus={() => navigate(-1)}
    />
  );
}
