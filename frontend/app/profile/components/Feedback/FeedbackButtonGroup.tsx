// import {
//   FeedbackType,
//   FeedbackButton,
//   SelectableFeedbackType,
// } from "./FeedbackButton";
// import { useState } from "react";
// import { post } from "@/services/axios";

// interface FeedbackResponse {
//   status: string;
// }

// export default function FeedbackButtonGroup({ trackId }: { trackId: string }) {
//   const [selectedFeedback, setSelectedFeedback] =
//     useState<SelectableFeedbackType | null>(null);

//   const handleSubmit = async (feedbackType: FeedbackType) => {
//     try {
//       await post<FeedbackResponse>("/api/submit-feedback/", {
//         track_id: trackId,
//         feedback_type: feedbackType,
//       });

//       // Only update selection for non-skip feedback
//       if (feedbackType !== "SKIP") {
//         setSelectedFeedback(feedbackType as SelectableFeedbackType);
//       }
//     } catch (error) {
//       console.error("Error submitting feedback:", error);
//       //could show a toast notification
//       throw error;
//     }
//   };
//   return (
//     <div className="flex gap-2 items-center">
//       <FeedbackButton
//         feedbackType="LIKE"
//         onSubmit={handleSubmit}
//         isSelected={selectedFeedback === "LIKE"}
//       />
//       <FeedbackButton
//         feedbackType="DISLIKE"
//         onSubmit={handleSubmit}
//         isSelected={selectedFeedback === "DISLIKE"}
//       />
//       <FeedbackButton feedbackType="SKIP" onSubmit={handleSubmit} />
//       <FeedbackButton
//         feedbackType="SAVE"
//         onSubmit={handleSubmit}
//         isSelected={selectedFeedback === "SAVE"}
//       />
//     </div>
//   );
// }
import {
  FeedbackType,
  FeedbackButton,
  SelectableFeedbackType,
} from "./FeedbackButton";
import Alert from "./Alert";
import { post } from "@/services/axios";
import { useState } from "react";

interface FeedbackResponse {
  status: string;
}

interface FeedbackStatus {
  loading: boolean;
  error: string | null;
  success: boolean;
}

export default function FeedbackButtonGroup({ trackId }: { trackId: string }) {
  const [selectedFeedback, setSelectedFeedback] =
    useState<SelectableFeedbackType | null>(null);
  const [status, setStatus] = useState<FeedbackStatus>({
    loading: false,
    error: null,
    success: false,
  });

  const handleSubmit = async (feedbackType: FeedbackType) => {
    setStatus({ loading: true, error: null, success: false });

    try {
      await post<FeedbackResponse>("/api/submit-feedback/", {
        track_id: trackId,
        feedback_type: feedbackType,
      });

      if (feedbackType !== "SKIP") {
        setSelectedFeedback(feedbackType as SelectableFeedbackType);
      }

      setStatus({ loading: false, error: null, success: true });

      setTimeout(() => {
        setStatus((prev) => ({ ...prev, success: false }));
      }, 2000);
    } catch (error) {
      console.error("Error submitting feedback:", error);
      setStatus({
        loading: false,
        error: "Failed to submit feedback. Please try again.",
        success: false,
      });

      setTimeout(() => {
        setStatus((prev) => ({ ...prev, error: null }));
      }, 3000);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-center">
        <FeedbackButton
          feedbackType="LIKE"
          onSubmit={handleSubmit}
          isSelected={selectedFeedback === "LIKE"}
          disabled={status.loading}
        />
        <FeedbackButton
          feedbackType="DISLIKE"
          onSubmit={handleSubmit}
          isSelected={selectedFeedback === "DISLIKE"}
          disabled={status.loading}
        />
        <FeedbackButton
          feedbackType="SKIP"
          onSubmit={handleSubmit}
          disabled={status.loading}
        />
        <FeedbackButton
          feedbackType="SAVE"
          onSubmit={handleSubmit}
          isSelected={selectedFeedback === "SAVE"}
          disabled={status.loading}
        />
      </div>

      <div className="min-h-[50px] transition-all duration-300">
        {status.error && (
          <Alert
            variant="destructive"
            title="Error"
            description={status.error}
          />
        )}

        {status.success && (
          <Alert
            title="Success"
            description="Your feedback has been recorded"
          />
        )}
      </div>
    </div>
  );
}
