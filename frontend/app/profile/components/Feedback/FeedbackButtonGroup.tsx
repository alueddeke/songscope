'use client'

import {
  FeedbackType,
  FeedbackButton,
  SelectableFeedbackType,
} from "./FeedbackButton";
import { post, get } from "@/services/axios";
import { useCallback, useEffect, useState } from "react";

interface FeedbackResponse {
  status: string;
  action?: string; // Added for like/unlike action
}

interface FeedbackStatus {
  loading: boolean;
  error: string | null;
  success: boolean;
}

interface FeedbackButtonGroupProps {
  trackId: string;
  onTrackRemoved?: () => void; // Callback when track is removed (for thumbs down)
}

export default function FeedbackButtonGroup({ trackId, onTrackRemoved }: FeedbackButtonGroupProps) {
  const [selectedFeedback, setSelectedFeedback] =
    useState<SelectableFeedbackType | null>(null);

  const [status, setStatus] = useState<FeedbackStatus>({
    loading: false,
    error: null,
    success: false,
  });

  const [notification, setNotification] = useState<string | null>(null);

  const checkInitialLikeState = useCallback(async () => {
    try {
      const response = await get<{liked: boolean}>(`/api/check-track-feedback/${trackId}/`);
      if (response.liked) {
        setSelectedFeedback("LIKE");
      }
    } catch (error) {
      console.error("Error checking initial like state:", error);
    }
  }, [trackId]);

  useEffect(() => {
    setSelectedFeedback(null);
    checkInitialLikeState();
  }, [trackId, checkInitialLikeState]);

  const handleSubmit = async (feedbackType: FeedbackType) => {
    setStatus({ loading: true, error: null, success: false });

    try {
      const response = await post<FeedbackResponse>("/api/submit-feedback/", {
        track_id: trackId,
        feedback_type: feedbackType,
      });

      if (feedbackType === "DISLIKE") {
        // Remove track from UI and show notification
        setNotification("Song removed");
        setTimeout(() => {
          setNotification(null);
          onTrackRemoved?.(); // Callback to remove track from parent component
        }, 1500);
      } else if (feedbackType === "LIKE") {
        // Handle like/unlike based on backend response
        if (response.action === 'removed') {
          // User unliked the track
          setSelectedFeedback(null);
          setNotification("Song unliked");
        } else {
          // User liked the track
          setSelectedFeedback("LIKE");
          setNotification("Song liked");
        }
        setTimeout(() => {
          setNotification(null);
        }, 1500);
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
    <div className="relative">
      {/* Notification */}
      {notification && (
        <div className="absolute -top-12 left-1/2 transform -translate-x-1/2 bg-green text-black px-4 py-2 rounded-lg shadow-lg z-10 animate-fade-in">
          {notification}
        </div>
      )}

      <div className="flex gap-2 items-center">
        <span className="text-white">Good Recommendation?</span>
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
