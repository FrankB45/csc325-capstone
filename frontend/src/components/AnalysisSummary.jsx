// AC5: renders the stored snapshot returned by the API, never live repo data.
export default function AnalysisSummary({ analysis }) {
  return (
    <section>
      <h2>Analysis</h2>
      <p>Page: <code>{analysis.page_path}</code></p>
      <p>{analysis.commits.length} commit(s) captured</p>
      <ol>
        {analysis.commits.map((c) => (
          <li key={c.sha}>
            <code title={c.sha}>{c.sha}</code> — {c.message}
          </li>
        ))}
      </ol>
    </section>
  );
}
