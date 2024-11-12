import { AlertCircle, CheckCircle } from "lucide-react";

interface AlertProps {
  variant?: "default" | "destructive";
  title: string;
  description: string;
}

export default function Alert({
  variant = "default",
  title,
  description,
}: AlertProps) {
  const Icon = variant === "destructive" ? AlertCircle : CheckCircle;

  return (
    <div
      className={`
      rounded-lg p-4 
      ${
        variant === "destructive"
          ? "bg-red-50 border border-red-200"
          : "bg-green-50 border border-green-200"
      }
      animate-in slide-in-from-bottom duration-300
    `}
    >
      <div className="flex items-start gap-3">
        <Icon
          className={`h-5 w-5 ${
            variant === "destructive" ? "text-red-600" : "text-green-600"
          }`}
        />
        <div>
          <h5
            className={`font-medium ${
              variant === "destructive" ? "text-red-900" : "text-green-900"
            }`}
          >
            {title}
          </h5>
          <p
            className={`text-sm ${
              variant === "destructive" ? "text-red-700" : "text-green-700"
            }`}
          >
            {description}
          </p>
        </div>
      </div>
    </div>
  );
}
