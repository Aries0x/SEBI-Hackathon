"use client";

interface PipelineProgressProps {
  status: string;
  step: string | null;
  mediaType: string;
}

const PIPELINE_STEPS: Record<string, string[]> = {
  video: [
    "Downloading video",
    "Extracting metadata",
    "Extracting keyframes",
    "Extracting audio",
    "Transcribing audio",
    "Running OCR on frames",
    "Extracting claims",
    "Verifying evidence",
    "Calculating trust score",
  ],
  image: [
    "Downloading image",
    "Extracting metadata",
    "Running OCR",
    "Checking for forgery",
    "Extracting claims",
    "Verifying evidence",
    "Calculating trust score",
  ],
  email: [
    "Downloading email",
    "Parsing email",
    "Checking authentication",
    "Extracting claims",
    "Verifying evidence",
    "Calculating trust score",
  ],
  website: [
    "Rendering website",
    "Extracting content",
    "Checking domain WHOIS",
    "Checking SSL certificate",
    "Extracting claims",
    "Verifying evidence",
    "Calculating trust score",
  ],
};

export default function PipelineProgress({
  status,
  step,
  mediaType,
}: PipelineProgressProps) {
  const steps = PIPELINE_STEPS[mediaType] || PIPELINE_STEPS.image;
  const isCompleted = status === "completed";
  const isFailed = status === "failed";

  // Determine current step index
  let currentStepIndex = -1;
  if (step) {
    const stepLower = step.toLowerCase();
    currentStepIndex = steps.findIndex(
      (s) => stepLower.includes(s.toLowerCase().split(" ")[0])
    );
    if (currentStepIndex === -1) {
      // Try fuzzy match
      currentStepIndex = steps.findIndex(
        (s) => {
          const words = s.toLowerCase().split(" ");
          return words.some((w) => stepLower.includes(w) && w.length > 3);
        }
      );
    }
  }

  if (isCompleted) currentStepIndex = steps.length;

  return (
    <div className="pipeline-progress">
      <div className="pipeline-header">
        <h3>Pipeline Progress</h3>
        {isFailed && (
          <span className="pipeline-status failed">
            Failed{step ? `: ${step}` : ""}
          </span>
        )}
      </div>

      <div className="pipeline-steps">
        {steps.map((stepName, i) => {
          let state: "completed" | "active" | "pending" = "pending";
          if (isCompleted || i < currentStepIndex) state = "completed";
          else if (i === currentStepIndex) state = "active";

          return (
            <div key={i} className={`pipeline-step ${state}`}>
              <div className="step-indicator">
                {state === "completed" && (
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path
                      d="M4 8L7 11L12 5"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
                {state === "active" && <div className="step-pulse" />}
                {state === "pending" && <div className="step-dot" />}
              </div>
              {i < steps.length - 1 && (
                <div
                  className={`step-line ${
                    state === "completed" ? "completed" : ""
                  }`}
                />
              )}
              <span className="step-label">{stepName}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
