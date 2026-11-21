import { useEffect, useState } from "react";

const pending = (status) => status === "queued" || status === "processing";
const detailUrl = (id) => `/api/comparisons/${encodeURIComponent(id)}/`;

export function useCommitComparison() {
  const [request, setRequest] = useState(null);
  const [record, setRecord] = useState(null);
  const busy = record?.status === "starting" || pending(record?.status);

  useEffect(() => {
    if (!request) return;

    const controller = new AbortController();
    let timer;

    async function load(url, options) {
      try {
        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
        });
        const data = await response.json().catch(() => null);
        if (controller.signal.aborted) return;

        // Another client may already have retried this comparison.
        if (response.status === 409 && options?.method === "POST" && request.retryId) {
          return load(detailUrl(request.retryId));
        }

        if (!response.ok) {
          throw new Error(
            data?.error || data?.detail ||
            `Comparison service unavailable (HTTP ${response.status}).`
          );
        }

        if (!data?.id || !["queued", "processing", "complete", "failed"].includes(data.status)) {
          throw new Error("The comparison service returned an unexpected response.");
        }

        if (
          data.status === "complete" &&
          (!Array.isArray(data.result?.changes) || !Array.isArray(data.result?.limitations))
        ) {
          throw new Error("The comparison result could not be read.");
        }

        setRecord(data);

        if (pending(data.status)) {
          timer = setTimeout(() => load(detailUrl(data.id)), 2000);
        }
      } catch (error) {
        if (!controller.signal.aborted) {
          setRecord({ status: "error", error_message: error.message });
        }
      }
    }

    load(request.url, request.options);

    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [request]);

  function compare(jobId, first, second) {
    if (busy) return;

    const retryId = record?.status === "failed" ? record.id : null;
    setRecord({ status: "starting" });

    if (retryId) {
      setRequest({
        retryId,
        url: `${detailUrl(retryId)}retry/`,
        options: { method: "POST" },
      });
    } else {
      setRequest({
        url: `/api/jobs/${encodeURIComponent(jobId)}/comparisons/`,
        options: {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            first_position: first,
            second_position: second,
          }),
        },
      });
    }
  }

  return { record, busy, compare };
}