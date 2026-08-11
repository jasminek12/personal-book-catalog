import { useEffect, useRef, useState } from "react";
import { scanApi, type ScanCandidate } from "../services/api";

type Stage = "camera" | "processing" | "candidates" | "manual-confirm";

export function CaptureBook({ onBookAdded }: { onBookAdded: () => void }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [stage, setStage] = useState<Stage>("camera");
  const [error, setError] = useState<string | null>(null);
  const [rawOcrText, setRawOcrText] = useState("");
  const [candidates, setCandidates] = useState<ScanCandidate[]>([]);
  const [selected, setSelected] = useState<ScanCandidate | null>(null);
  const [manualTitle, setManualTitle] = useState("");
  const [cameraActive, setCameraActive] = useState(false);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, []);

  const startCamera = async () => {
    setError(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setError(
        "Camera access is not available. Use HTTPS or localhost in a supported browser."
      );
      return;
    }

    try {
      // Stop any previous camera stream.
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;

      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });

      streamRef.current = stream;

      const video = videoRef.current;

      if (!video) {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        setError("Camera preview could not be initialized.");
        return;
      }

      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;

      setCameraActive(true);

      // Wait until the browser knows the video's dimensions.
      await new Promise<void>((resolve) => {
        if (video.readyState >= HTMLMediaElement.HAVE_METADATA) {
          resolve();
          return;
        }

        video.onloadedmetadata = () => {
          resolve();
        };
      });

      await video.play();
    } catch (err) {
      console.error("Camera error:", err);

      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      setCameraActive(false);

      if (err instanceof DOMException) {
        if (err.name === "NotAllowedError") {
          setError(
            "Camera permission was denied. Allow camera access for this site and try again."
          );
          return;
        }

        if (err.name === "NotFoundError") {
          setError("No camera was found on this device.");
          return;
        }

        if (err.name === "NotReadableError") {
          setError(
            "The camera is already being used by another application."
          );
          return;
        }

        if (err.name === "SecurityError") {
          setError("Camera access requires HTTPS or localhost.");
          return;
        }
      }

      setError(
        "Couldn't access the camera. Check browser permissions and make sure you're using HTTPS or localhost."
      );
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;

    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.srcObject = null;
    }

    setCameraActive(false);
  };

  const capture = async () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;

    if (!video || !canvas) {
      setError("Camera is not ready.");
      return;
    }

    if (!streamRef.current) {
      setError("Camera is not active.");
      return;
    }

    if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      setError("Camera is still loading. Please wait a moment.");
      return;
    }

    if (video.videoWidth === 0 || video.videoHeight === 0) {
      setError("Camera is still loading. Please wait a moment and try again.");
      return;
    }

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext("2d");

    if (!ctx) {
      setError("Could not prepare the captured image.");
      return;
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    setStage("processing");
    setError(null);

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          setError("Failed to capture image.");
          setStage("camera");
          return;
        }

        try {
          const result = await scanApi.identify(blob);

          setRawOcrText(result.raw_ocr_text);
          setCandidates(result.candidates);

          stopCamera();

          if (result.candidates.length === 0) {
            setManualTitle(result.raw_ocr_text);
            setStage("manual-confirm");
          } else {
            setStage("candidates");
          }
        } catch (err) {
          console.error("Scan error:", err);

          setError(
            "Couldn't process that image. Try again with better lighting."
          );
          setStage("camera");
        }
      },
      "image/jpeg",
      0.9
    );
  };

  const confirmCandidate = async (candidate: ScanCandidate) => {
    setSelected(candidate);
    setError(null);

    try {
      await scanApi.confirm({
        title: candidate.title,
        author_name: candidate.author_name ?? undefined,
        isbn: candidate.isbn ?? undefined,
        cover_url: candidate.cover_url ?? undefined,
        publication_year: candidate.publication_year ?? undefined,
        page_count: candidate.page_count ?? undefined,
        raw_ocr_text: rawOcrText,
        ocr_confidence: candidate.confidence,
      });

      reset();
      onBookAdded();
    } catch (err) {
      console.error("Confirm error:", err);
      setSelected(null);
      setError("Couldn't save that book. Try again.");
    }
  };

  const confirmManual = async () => {
    if (!manualTitle.trim()) {
      setError("Please enter a book title.");
      return;
    }

    setError(null);

    try {
      await scanApi.confirm({
        title: manualTitle.trim(),
        raw_ocr_text: rawOcrText || undefined,
      });

      reset();
      onBookAdded();
    } catch (err) {
      console.error("Confirm error:", err);
      setError("Couldn't save that book. Try again.");
    }
  };

  const reset = () => {
    stopCamera();

    setStage("camera");
    setRawOcrText("");
    setCandidates([]);
    setSelected(null);
    setManualTitle("");
    setError(null);
  };

  const retake = async () => {
    reset();
    await startCamera();
  };

  return (
    <div
      style={{
        border: "1px solid #334155",
        borderRadius: 8,
        padding: "1rem",
        marginBottom: "1rem",
      }}
    >
      <h3 style={{ marginTop: 0 }}>Scan a book</h3>

      {error && (
        <p style={{ color: "crimson", marginBottom: "1rem" }}>
          {error}
        </p>
      )}

      {stage === "camera" && (
        <div>
          {!cameraActive && (
            <button onClick={startCamera}>Start camera</button>
          )}

          <div
            style={{
              position: "relative",
              maxWidth: 400,
              width: "100%",
              display: cameraActive ? "block" : "none",
              marginTop: "1rem",
            }}
          >
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              style={{
                display: "block",
                width: "100%",
                height: "auto",
                minHeight: 240,
                objectFit: "cover",
                background: "#000",
                borderRadius: 4,
              }}
            />

            <div
              style={{
                position: "absolute",
                top: "10%",
                left: "15%",
                right: "15%",
                bottom: "10%",
                border: "2px dashed #22d3ee",
                borderRadius: 6,
                pointerEvents: "none",
              }}
            />

            <p style={{ fontSize: "0.85rem", opacity: 0.8 }}>
              Place one book inside the frame, on a plain background.
            </p>

            <button onClick={capture}>Capture</button>

            <button
              onClick={stopCamera}
              style={{ marginLeft: "0.5rem" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {stage === "processing" && <p>Reading cover...</p>}

      {stage === "candidates" && (
        <div>
          <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>
            OCR read: <em>{rawOcrText || "(nothing readable)"}</em>
          </p>

          <p>Which book is this?</p>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
            }}
          >
            {candidates.map((candidate, index) => (
              <button
                key={index}
                onClick={() => confirmCandidate(candidate)}
                disabled={selected !== null}
                style={{
                  textAlign: "left",
                  padding: "0.5rem",
                }}
              >
                <strong>{candidate.title}</strong>

                {candidate.author_name && (
                  <span> by {candidate.author_name}</span>
                )}

                <span
                  style={{
                    float: "right",
                    opacity: 0.6,
                  }}
                >
                  {candidate.confidence.toFixed(0)}% match
                </span>
              </button>
            ))}
          </div>

          <button
            onClick={() => setStage("manual-confirm")}
            style={{ marginTop: "0.5rem" }}
          >
            None of these - enter manually
          </button>

          <button
            onClick={retake}
            style={{
              marginTop: "0.5rem",
              marginLeft: "0.5rem",
            }}
          >
            Retake photo
          </button>
        </div>
      )}

      {stage === "manual-confirm" && (
        <div>
          <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>
            {candidates.length === 0
              ? "No metadata matches found. Enter the title manually:"
              : "Enter the correct title:"}
          </p>

          <input
            value={manualTitle}
            onChange={(e) => setManualTitle(e.target.value)}
            placeholder="Book title"
            style={{
              width: "100%",
              marginBottom: "0.5rem",
              boxSizing: "border-box",
            }}
          />

          <button onClick={confirmManual}>Add book</button>

          <button
            onClick={retake}
            style={{ marginLeft: "0.5rem" }}
          >
            Retake photo
          </button>
        </div>
      )}

      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
}