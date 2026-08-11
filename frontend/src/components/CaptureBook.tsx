import { useRef, useState } from "react";
import { scanApi, type ScanCandidate } from "../services/api";

type Stage = "camera" | "processing" | "candidates" | "manual-confirm";

/**
 * Single-book capture flow (Phase 1). Deliberately tap-to-scan, not
 * continuous auto-capture - see project notes on why: same underlying
 * pipeline, much simpler to build, most of the "point and go" feel
 * without the complexity of repeatedly running OCR on a live stream.
 *
 * Frame guide overlay is a plain visual aid, not an actual crop
 * boundary enforced in code - it exists to guide the user toward the
 * "single book, filling the frame, clean background" capture condition
 * the whole OCR pipeline is built around.
 */
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

  const startCamera = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCameraActive(true);
    } catch {
      setError(
        "Couldn't access the camera. Check browser permissions, and make sure you're on https:// or localhost."
      );
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setCameraActive(false);
  };

  const capture = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    setStage("processing");
    setError(null);

    canvas.toBlob(async (blob) => {
      if (!blob) {
        setError("Failed to capture image");
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
      } catch {
        setError("Couldn't process that image. Try again with better lighting.");
        setStage("camera");
      }
    }, "image/jpeg", 0.9);
  };

  const confirmCandidate = async (candidate: ScanCandidate) => {
    setSelected(candidate);
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
    } catch {
      setError("Couldn't save that book. Try again.");
    }
  };

  const confirmManual = async () => {
    if (!manualTitle.trim()) return;
    try {
      await scanApi.confirm({
        title: manualTitle.trim(),
        raw_ocr_text: rawOcrText || undefined,
      });
      reset();
      onBookAdded();
    } catch {
      setError("Couldn't save that book. Try again.");
    }
  };

  const reset = () => {
    setStage("camera");
    setRawOcrText("");
    setCandidates([]);
    setSelected(null);
    setManualTitle("");
  };

  const retake = () => {
    reset();
    startCamera();
  };

  return (
    <div style={{ border: "1px solid #334155", borderRadius: 8, padding: "1rem", marginBottom: "1rem" }}>
      <h3 style={{ marginTop: 0 }}>Scan a book</h3>

      {error && <p style={{ color: "crimson" }}>{error}</p>}

      {stage === "camera" && (
        <div>
          {!cameraActive ? (
            <button onClick={startCamera}>Start camera</button>
          ) : (
            <div style={{ position: "relative", maxWidth: 400 }}>
              <video ref={videoRef} style={{ width: "100%", borderRadius: 4 }} playsInline muted />
              {/* Frame guide - visual aid only, guides the user to fill
                  the frame with a single book on a clean background */}
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
              <button onClick={stopCamera} style={{ marginLeft: "0.5rem" }}>
                Cancel
              </button>
            </div>
          )}
        </div>
      )}

      {stage === "processing" && <p>Reading cover...</p>}

      {stage === "candidates" && (
        <div>
          <p style={{ fontSize: "0.85rem", opacity: 0.7 }}>
            OCR read: <em>{rawOcrText || "(nothing readable)"}</em>
          </p>
          <p>Which book is this?</p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {candidates.map((c, i) => (
              <button
                key={i}
                onClick={() => confirmCandidate(c)}
                disabled={selected !== null}
                style={{ textAlign: "left", padding: "0.5rem" }}
              >
                <strong>{c.title}</strong>
                {c.author_name && <span> by {c.author_name}</span>}
                <span style={{ float: "right", opacity: 0.6 }}>
                  {c.confidence.toFixed(0)}% match
                </span>
              </button>
            ))}
          </div>
          <button onClick={() => setStage("manual-confirm")} style={{ marginTop: "0.5rem" }}>
            None of these - enter manually
          </button>
          <button onClick={retake} style={{ marginTop: "0.5rem", marginLeft: "0.5rem" }}>
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
            style={{ width: "100%", marginBottom: "0.5rem" }}
          />
          <button onClick={confirmManual}>Add book</button>
          <button onClick={retake} style={{ marginLeft: "0.5rem" }}>
            Retake photo
          </button>
        </div>
      )}

      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
}
