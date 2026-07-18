"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";

type UploadedDataset = {
  id: string;
  filename: string;
  byte_size: number;
  row_count: number;
  columns: string[];
};

type DatasetProfile = {
  summary: string;
  column_mapping: Record<string, string | string[] | null>;
  service_taxonomy: Array<{
    canonical_service: string;
    observed_variants: string[];
    cadence_days: number;
    rationale: string;
  }>;
  dormancy_rules: Array<{
    canonical_service: string;
    dormant_after_days: number;
    rationale: string;
  }>;
  data_quirks: Array<{ category: string; detail: string }>;
};

type SegmentationResult = {
  totals: { dormant_clients: number; recoverable_revenue: number };
  segments: Array<{ name: string; clients: Array<unknown>; recoverable_revenue: number }>;
  quality?: {
    input_rows: number;
    unique_rows: number;
    accepted_rows: number;
    excluded_duplicate_rows: number;
    excluded_invalid_dates: number;
    excluded_missing_identity: number;
    excluded_unclassified_service: number;
  } | null;
};

type Campaign = {
  id: string;
  segment_name: string;
  recipient_count: number;
  projected_revenue: number;
  subject: string;
  body: string;
  status: string;
};

type RunActivity = {
  id: string;
  agent_name: string;
  model: string;
  status: string;
  latency_ms: number | null;
  created_at: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function label(value: string) {
  return value.split("_").join(" ");
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [dataset, setDataset] = useState<UploadedDataset | null>(null);
  const [profile, setProfile] = useState<DatasetProfile | null>(null);
  const [segmentation, setSegmentation] = useState<SegmentationResult | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [runs, setRuns] = useState<RunActivity[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isProfiling, setIsProfiling] = useState(false);
  const [isSegmenting, setIsSegmenting] = useState(false);
  const [isCreatingCampaigns, setIsCreatingCampaigns] = useState(false);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setDataset(null);
    setProfile(null);
    setSegmentation(null);
    setCampaigns([]);
    setRuns([]);
    setError(null);
  }

  useEffect(() => {
    if (!dataset) return;
    const source = new EventSource(`${apiBaseUrl}/api/datasets/${dataset.id}/runs/stream`);
    source.addEventListener("runs", (event) => {
      setRuns(JSON.parse((event as MessageEvent).data) as RunActivity[]);
    });
    return () => source.close();
  }, [dataset]);

  async function refreshRuns() {
    if (!dataset) return;
    const response = await fetch(`${apiBaseUrl}/api/datasets/${dataset.id}/runs`);
    if (response.ok) setRuns(await response.json() as RunActivity[]);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Choose a clinic CSV before uploading.");
      return;
    }

    setError(null);
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets`, {
        method: "POST",
        body: formData
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The CSV could not be uploaded.");
      }
      setDataset(payload as UploadedDataset);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "The CSV could not be uploaded.");
    } finally {
      setIsUploading(false);
    }
  }

  async function profileUpload() {
    if (!dataset) return;

    setError(null);
    setIsProfiling(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets/${dataset.id}/profile`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail ?? "The clinic profile could not be created.");
      }
      setProfile(payload as DatasetProfile);
      await refreshRuns();
    } catch (profileError) {
      setError(profileError instanceof Error ? profileError.message : "The clinic profile could not be created.");
    } finally {
      setIsProfiling(false);
    }
  }

  async function segmentUpload() {
    if (!dataset) return;
    setError(null);
    setIsSegmenting(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets/${dataset.id}/segment`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Segmentation could not be completed.");
      setSegmentation(payload as SegmentationResult);
      await refreshRuns();
    } catch (segmentError) {
      setError(segmentError instanceof Error ? segmentError.message : "Segmentation could not be completed.");
    } finally {
      setIsSegmenting(false);
    }
  }

  async function createCampaigns() {
    if (!dataset) return;
    setError(null);
    setIsCreatingCampaigns(true);
    try {
      const response = await fetch(`${apiBaseUrl}/api/datasets/${dataset.id}/campaigns`, { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Campaign drafts could not be created.");
      setCampaigns(payload as Campaign[]);
      await refreshRuns();
    } catch (campaignError) {
      setError(campaignError instanceof Error ? campaignError.message : "Campaign drafts could not be created.");
    } finally {
      setIsCreatingCampaigns(false);
    }
  }

  async function approveCampaign(campaignId: string) {
    const response = await fetch(`${apiBaseUrl}/api/campaigns/${campaignId}/approve`, { method: "POST" });
    const payload = await response.json();
    if (!response.ok) {
      setError(payload.detail ?? "Campaign approval failed.");
      return;
    }
    setCampaigns((current) => current.map((campaign) => campaign.id === campaignId ? payload as Campaign : campaign));
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-16 text-slate-100">
      <section className="mx-auto max-w-3xl">
        <p className="mb-5 text-sm font-semibold uppercase tracking-[0.24em] text-cyan-300">Winback Ops</p>
        <h1 className="max-w-2xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Start with the messy booking export.
        </h1>
        <p className="mt-5 max-w-xl text-lg leading-8 text-slate-300">
          Upload a clinic CSV. We will safely store it and show the raw shape of the data before any analysis begins.
        </p>

        <form className="mt-10 rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl" onSubmit={upload}>
          <label className="block text-sm font-medium" htmlFor="dataset-file">Clinic booking CSV</label>
          <input
            accept=".csv,text/csv"
            className="mt-3 block w-full cursor-pointer rounded-lg border border-slate-600 bg-slate-950 p-3 text-sm text-slate-300 file:mr-4 file:rounded-md file:border-0 file:bg-cyan-300 file:px-3 file:py-2 file:font-semibold file:text-slate-950"
            id="dataset-file"
            onChange={selectFile}
            type="file"
          />
          <p className="mt-3 text-sm text-slate-400">CSV only, up to 10 MB. Sample exports are in <code>sample_data/</code>.</p>
          <button
            className="mt-6 rounded-lg bg-cyan-300 px-5 py-3 font-semibold text-slate-950 transition hover:bg-cyan-200 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isUploading}
            type="submit"
          >
            {isUploading ? "Uploading…" : "Upload booking export"}
          </button>
        </form>

        {error && <p className="mt-5 rounded-lg border border-rose-800 bg-rose-950/50 p-4 text-rose-200" role="alert">{error}</p>}

        {!dataset && !error && (
          <section className="mt-8 rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 p-6 text-slate-300">
            <h2 className="font-semibold text-slate-100">Your recovery workflow will appear here</h2>
            <p className="mt-2 text-sm leading-6">Upload any of the four sample exports to see schema profiling, verified segmentation, revenue projections, and approval-gated campaign drafts.</p>
          </section>
        )}

        {dataset && (
          <section className="mt-8 rounded-2xl border border-emerald-800 bg-emerald-950/30 p-6" aria-live="polite">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-emerald-300">Upload stored</p>
            <h2 className="mt-2 text-2xl font-semibold">{dataset.filename}</h2>
            <dl className="mt-5 grid gap-4 sm:grid-cols-3">
              <div><dt className="text-sm text-slate-400">Rows</dt><dd className="mt-1 text-xl font-semibold">{dataset.row_count}</dd></div>
              <div><dt className="text-sm text-slate-400">Columns</dt><dd className="mt-1 text-xl font-semibold">{dataset.columns.length}</dd></div>
              <div><dt className="text-sm text-slate-400">Size</dt><dd className="mt-1 text-xl font-semibold">{(dataset.byte_size / 1024).toFixed(1)} KB</dd></div>
            </dl>
            <p className="mt-5 text-sm text-slate-300">Detected headers: {dataset.columns.join(", ")}</p>
            <button
              className="mt-6 rounded-lg bg-emerald-300 px-5 py-3 font-semibold text-slate-950 transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isProfiling}
              onClick={profileUpload}
              type="button"
            >
              {isProfiling ? "GPT-5.6 is profiling…" : "Profile this dataset"}
            </button>
          </section>
        )}

        {runs.length > 0 && (
          <section className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-6" aria-live="polite">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-300">Agent activity</p>
            <div className="mt-4 space-y-3">
              {runs.map((run) => (
                <div className="flex items-center justify-between gap-4 rounded-lg border border-slate-700 px-4 py-3 text-sm" key={run.id}>
                  <div><span className="font-semibold capitalize">{label(run.agent_name)}</span><span className="ml-2 text-slate-400">{run.model}</span></div>
                  <div className="text-right"><span className={run.status === "completed" ? "text-emerald-300" : run.status === "failed" ? "text-rose-300" : "text-amber-300"}>{run.status}</span>{run.latency_ms !== null && <span className="ml-2 text-slate-400">{run.latency_ms} ms</span>}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {profile && (
          <section className="mt-8 rounded-2xl border border-violet-800 bg-violet-950/30 p-6" aria-live="polite">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-violet-300">What the agent understood</p>
            <p className="mt-3 text-lg leading-7 text-slate-100">{profile.summary}</p>

            <div className="mt-7 grid gap-6 lg:grid-cols-2">
              <div>
                <h2 className="text-lg font-semibold">Column mapping</h2>
                <dl className="mt-3 space-y-2 text-sm">
                  {Object.entries(profile.column_mapping)
                    .filter(([, value]) => Array.isArray(value) ? value.length > 0 : Boolean(value))
                    .map(([concept, value]) => (
                      <div className="flex justify-between gap-4 border-b border-violet-900 pb-2" key={concept}>
                        <dt className="capitalize text-slate-400">{label(concept)}</dt>
                        <dd className="text-right text-slate-100">{Array.isArray(value) ? value.join(", ") : value}</dd>
                      </div>
                    ))}
                </dl>
              </div>

              <div>
                <h2 className="text-lg font-semibold">Service cadence</h2>
                <div className="mt-3 space-y-3">
                  {profile.service_taxonomy.map((service) => (
                    <article className="rounded-lg border border-violet-900 bg-slate-950/40 p-3" key={service.canonical_service}>
                      <div className="flex items-baseline justify-between gap-3">
                        <h3 className="font-medium">{service.canonical_service}</h3>
                        <span className="text-sm font-semibold text-violet-200">{service.cadence_days}-day cadence</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-400">{service.observed_variants.join(", ")}</p>
                    </article>
                  ))}
                </div>
              </div>
            </div>

            <div className="mt-7">
              <h2 className="text-lg font-semibold">Dormancy definitions</h2>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {profile.dormancy_rules.map((rule) => (
                  <li key={rule.canonical_service}>
                    <span className="font-medium text-violet-200">{rule.canonical_service}:</span> dormant after {rule.dormant_after_days} days — {rule.rationale}
                  </li>
                ))}
              </ul>
            </div>

            {profile.data_quirks.length > 0 && (
              <div className="mt-7">
                <h2 className="text-lg font-semibold">Data quirks to handle</h2>
                <ul className="mt-3 space-y-2 text-sm text-slate-300">
                  {profile.data_quirks.map((quirk) => <li key={`${quirk.category}-${quirk.detail}`}><span className="font-medium text-violet-200">{quirk.category}:</span> {quirk.detail}</li>)}
                </ul>
              </div>
            )}
            <button
              className="mt-7 rounded-lg bg-violet-300 px-5 py-3 font-semibold text-slate-950 transition hover:bg-violet-200 disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isSegmenting}
              onClick={segmentUpload}
              type="button"
            >
              {isSegmenting ? "Generating and verifying…" : "Run sandboxed segmentation"}
            </button>
          </section>
        )}

        {segmentation && (
          <section className="mt-8 rounded-2xl border border-cyan-800 bg-cyan-950/25 p-6" aria-live="polite">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-cyan-300">Verified segmentation</p>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <div><p className="text-sm text-slate-400">Dormant clients</p><p className="mt-1 text-3xl font-semibold">{segmentation.totals.dormant_clients}</p></div>
              <div><p className="text-sm text-slate-400">Recoverable revenue</p><p className="mt-1 text-3xl font-semibold">${segmentation.totals.recoverable_revenue.toLocaleString()}</p></div>
              <div><p className="text-sm text-slate-400">Segments</p><p className="mt-1 text-3xl font-semibold">{segmentation.segments.length}</p></div>
            </div>
            {segmentation.quality && (
              <div className="mt-6 rounded-xl border border-cyan-900 bg-slate-950/40 p-4">
                <h2 className="font-semibold">Data quality audit</h2>
                <p className="mt-1 text-sm text-slate-400">Rows are filtered in order to protect campaign quality.</p>
                <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
                  <div><dt className="text-slate-400">Input rows</dt><dd className="font-semibold">{segmentation.quality.input_rows}</dd></div>
                  <div><dt className="text-slate-400">Accepted rows</dt><dd className="font-semibold text-emerald-300">{segmentation.quality.accepted_rows}</dd></div>
                  <div><dt className="text-slate-400">Duplicate rows removed</dt><dd className="font-semibold">{segmentation.quality.excluded_duplicate_rows}</dd></div>
                  <div><dt className="text-slate-400">Invalid dates excluded</dt><dd className="font-semibold">{segmentation.quality.excluded_invalid_dates}</dd></div>
                  <div><dt className="text-slate-400">Missing identities excluded</dt><dd className="font-semibold">{segmentation.quality.excluded_missing_identity}</dd></div>
                  <div><dt className="text-slate-400">Unclassified services excluded</dt><dd className="font-semibold">{segmentation.quality.excluded_unclassified_service}</dd></div>
                </dl>
              </div>
            )}
            <button className="mt-6 rounded-lg bg-cyan-300 px-5 py-3 font-semibold text-slate-950 disabled:opacity-60" disabled={isCreatingCampaigns} onClick={createCampaigns} type="button">
              {isCreatingCampaigns ? "Drafting campaigns…" : "Draft win-back campaigns"}
            </button>
          </section>
        )}

        {campaigns.length > 0 && (
          <section className="mt-8 rounded-2xl border border-amber-800 bg-amber-950/20 p-6">
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-300">Approve & send</p>
            <p className="mt-2 text-sm text-slate-300">Every sequence remains a draft until you explicitly approve it. Sends are mocked in demo mode.</p>
            <div className="mt-5 space-y-4">
              {campaigns.map((campaign) => (
                <article className="rounded-xl border border-amber-900 bg-slate-950/40 p-4" key={campaign.id}>
                  <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="font-semibold">{label(campaign.segment_name)}</h2><p className="mt-1 text-sm text-slate-400">{campaign.recipient_count} clients · ${campaign.projected_revenue.toLocaleString()} projected</p></div><span className="rounded-full bg-slate-800 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-200">{label(campaign.status)}</span></div>
                  <p className="mt-4 font-medium text-slate-100">{campaign.subject}</p><p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-300">{campaign.body}</p>
                  {campaign.status === "draft" && <button className="mt-4 rounded-lg bg-amber-300 px-4 py-2 text-sm font-semibold text-slate-950" onClick={() => approveCampaign(campaign.id)} type="button">Approve & mock send</button>}
                </article>
              ))}
            </div>
          </section>
        )}
      </section>
    </main>
  );
}
