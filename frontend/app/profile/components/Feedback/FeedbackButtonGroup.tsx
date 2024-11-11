'use client'

import {
  FeedbackType,
  FeedbackButton,
  SelectableFeedbackType,
} from "./FeedbackButton";
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
    <div className="">
      <div className="flex gap-2 items-center">
        <span className="text-white">Good Suggestion?</span>
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
      </div>
    </div>
  );
}
