import { useCallback, useEffect, useRef, useState } from "react";

const FALLBACK_ERROR =
  "Link is either invalid or repository is set to private. Please try again.";

/**
 * Calls POST /api/repo/info/ (same endpoint the old RepositoryValidation used).
 * status: "idle" | "loading" | "invalid" | "valid"
 */
export function useRepositoryLookup() {
  const [status, setStatus] = useState("idle");
  const [repository, setRepository] = useState(null);
  const [error, setError] = useState("");
  const abortRef = useRef(null);

  useEffect(() => () => abortRef.current?.abort(), []);

  const lookup = useCallback(async (rawUrl) => {
    const url = rawUrl.trim();
    if (!url) {
      setStatus("invalid");
      setError("Enter a repository URL.");
      return null;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setStatus("loading");
    setError("");

    try {
      const response = await fetch("/api/repo/info/", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ url }),
        signal: controller.signal,
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || data.detail || FALLBACK_ERROR);

      setRepository(data);
      setStatus("valid");
      return data;
    } catch (err) {
      if (err.name === "AbortError") return null;
      setRepository(null);
      setStatus("invalid");
      setError(err.message || FALLBACK_ERROR);
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setStatus("idle");
    setRepository(null);
    setError("");
  }, []);

  return { status, repository, error, lookup, reset };
}
