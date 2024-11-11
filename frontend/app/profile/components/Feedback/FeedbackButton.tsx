import { ThumbsUp, ThumbsDown, Forward, BookmarkPlus } from "lucide-react";
import { useState } from "react";

export type SelectableFeedbackType = "LIKE" | "DISLIKE" | "SAVE";
export type FeedbackType = SelectableFeedbackType | "SKIP";

export interface FeedbackButtonProps {
  feedbackType: FeedbackType;
  onSubmit: (feedbackType: FeedbackType) => Promise<void>;
  isSelected?: boolean;
  size?: "sm" | "md" | "lg";
  disabled?: boolean;
}
export const feedbackConfig = {
  LIKE: {
    icon: ThumbsUp,
    label: "Like this song",
    hoverColor: "hover:bg-green-100",
    selectedColor: "bg-green-100",
    iconColor: "text-white",
    selectedIconColor: "text-green-700",
  },
  DISLIKE: {
    icon: ThumbsDown,
    label: "Dislike this song",
    hoverColor: "hover:bg-red-100",
    selectedColor: "bg-red-100",
    iconColor: "text-red-600",
    selectedIconColor: "text-red-700",
  },
  SKIP: {
    icon: Forward,
    label: "Skip this song",
    hoverColor: "hover:bg-gray-100",
    selectedColor: "", // Skip doesn't have a selected state
    iconColor: "text-gray-600",
    selectedIconColor: "text-gray-600",
  },
  SAVE: {
    icon: BookmarkPlus,
    label: "Save to library",
    hoverColor: "hover:bg-blue-100",
    selectedColor: "bg-blue-100",
    iconColor: "text-blue-600",
    selectedIconColor: "text-blue-700",
  },
} as const;

export function FeedbackButton({
  feedbackType,
  onSubmit,
  isSelected = false,
  size = "md",
  disabled = false,
}: FeedbackButtonProps) {
  const [isLoading, setIsLoading] = useState(false);

  const config = feedbackConfig[feedbackType];
  const Icon = config.icon;

  const sizeClasses = {
    sm: {
      button: "p-1.5",
      icon: "w-4 h-4",
    },
    md: {
      button: "p-2",
      icon: "w-5 h-5",
    },
    lg: {
      button: "p-3",
      icon: "w-6 h-6",
    },
  };

  const handleClick = async () => {
    if (isLoading) return;

    try {
      setIsLoading(true);
      await onSubmit(feedbackType);
    } catch (error) {
      console.error("Error submitting feedback:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <button
      onClick={handleClick}
      disabled={disabled || isLoading}
      className={`
        rounded-full 
        transition-all 
        duration-200
        ${!isSelected ? config.hoverColor : config.selectedColor}
        ${sizeClasses[size].button}
        ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        ${isLoading ? "animate-pulse" : ""}
        ${isSelected ? "ring-2 ring-offset-2 ring-offset-white" : ""}
        ${isSelected ? `ring-${config.iconColor.split("-")[1]}-600` : ""}
      `}
      aria-label={config.label}
      aria-pressed={isSelected}
    >
      <Icon
        className={`
          ${sizeClasses[size].icon} 
          ${isSelected ? config.selectedIconColor : config.iconColor}
        `}
      />
    </button>
  );
}
