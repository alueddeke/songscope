import {
  FeedbackType,
  FeedbackButton,
  SelectableFeedbackType,
} from "./FeedbackButton";
import { useState } from "react";
import { post } from "@/services/axios";

interface FeedbackResponse {
  status: string;
}

export default function FeedbackButtonGroup({ trackId }: { trackId: string }) {
  const [selectedFeedback, setSelectedFeedback] =
    useState<SelectableFeedbackType | null>(null);

  const handleSubmit = async (feedbackType: FeedbackType) => {
    try {
      await post<FeedbackResponse>("/api/submit-feedback/", {
        track_id: trackId,
        feedback_type: feedbackType,
      });

      // Only update selection for non-skip feedback
      if (feedbackType !== "SKIP") {
        setSelectedFeedback(feedbackType as SelectableFeedbackType);
      }
    } catch (error) {
      console.error("Error submitting feedback:", error);
      //could show a toast notification
      throw error;
    }
  };
  return (
    <div className="flex gap-2 items-center">
      <FeedbackButton
        feedbackType="LIKE"
        onSubmit={handleSubmit}
        isSelected={selectedFeedback === "LIKE"}
      />
      <FeedbackButton
        feedbackType="DISLIKE"
        onSubmit={handleSubmit}
        isSelected={selectedFeedback === "DISLIKE"}
      />
      <FeedbackButton feedbackType="SKIP" onSubmit={handleSubmit} />
      <FeedbackButton
        feedbackType="SAVE"
        onSubmit={handleSubmit}
        isSelected={selectedFeedback === "SAVE"}
      />
    </div>
  );
}
